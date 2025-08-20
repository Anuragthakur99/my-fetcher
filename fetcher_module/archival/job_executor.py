"""Job Executor with Concurrency Management"""

import asyncio
import concurrent.futures
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import threading
import time

from common.logger import StructuredLogger
from common.job_config import JobConfigManager, JobConfig
from common.module_factory import ModuleFactory


@dataclass
class JobRequest:
    """Job request data structure"""
    job_id: str
    service_id: str
    submitted_at: datetime = None
    
    def __post_init__(self):
        if self.submitted_at is None:
            self.submitted_at = datetime.utcnow()


@dataclass
class JobResult:
    """Job execution result data structure"""
    job_id: str
    service_id: str
    success: bool
    start_time: datetime
    end_time: datetime
    execution_duration: float
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class JobExecutor:
    """Manages concurrent job execution with worker pool"""
    
    def __init__(self, max_workers: int = 20, environment: str = "local", logger_name: str = "job_executor"):
        self.max_workers = max_workers
        self.environment = environment
        self.logger = StructuredLogger("system", "orchestrator", logger_name)
        self.job_config_manager = JobConfigManager(environment, self.logger)
        
        # Concurrency management
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.active_jobs: Dict[str, concurrent.futures.Future] = {}
        self.job_queue: List[JobRequest] = []
        self.completed_jobs: List[JobResult] = []
        
        # Thread safety locks
        self.queue_lock = threading.Lock()
        self.active_jobs_lock = threading.Lock()
        self.stats_lock = threading.Lock()  # NEW: Dedicated stats lock
        
        # Execution statistics - now thread-safe
        self.stats = {
            "total_submitted": 0,
            "total_completed": 0,
            "total_failed": 0,
            "currently_running": 0,
            "queue_size": 0
        }
        
        self.logger.info("Job executor initialized", {
            "max_workers": max_workers,
            "executor_type": "ThreadPoolExecutor"
        })
    
    def _update_stats(self, **updates):
        """Thread-safe statistics update method"""
        with self.stats_lock:
            for key, value in updates.items():
                if key.endswith('_increment'):
                    # Handle increment operations
                    actual_key = key.replace('_increment', '')
                    if actual_key in self.stats:
                        self.stats[actual_key] += value
                else:
                    # Handle direct assignments
                    if key in self.stats:
                        self.stats[key] = value
    
    def _get_stats_snapshot(self) -> Dict[str, Any]:
        """Get thread-safe snapshot of current statistics"""
        with self.stats_lock:
            return self.stats.copy()
    
    def submit_job(self, job_id: str, service_id: str) -> bool:
        """
        Submit a job for execution with thread-safe operations
        
        Args:
            job_id: Unique job identifier
            service_id: Service identifier
            
        Returns:
            True if job submitted successfully, False otherwise
        """
        try:
            job_request = JobRequest(job_id, service_id)
            
            # Thread-safe job submission and stats update
            with self.queue_lock:
                # Check if job already exists
                if any(job.job_id == job_id and job.service_id == service_id 
                      for job in self.job_queue):
                    self.logger.warning(f"Job already in queue", {
                        "job_id": job_id,
                        "service_id": service_id
                    })
                    return False
                
                # Add to queue (FIFO order)
                self.job_queue.append(job_request)
                queue_size = len(self.job_queue)
            
            # Update stats atomically
            self._update_stats(
                total_submitted_increment=1,
                queue_size=queue_size
            )
            
            self.logger.info(f"Job submitted to queue", {
                "job_id": job_id,
                "service_id": service_id,
                "queue_position": queue_size
            })
            
            # Try to process queue
            self._process_queue()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to submit job: {str(e)}", {
                "job_id": job_id,
                "service_id": service_id,
                "exception": str(e)
            })
            return False
    
    def _process_queue(self):
        """Process jobs from queue if workers are available - completely thread-safe"""
        job_request = None
        job_key = None
        future = None
        current_stats = None
        
        # Atomic check and job assignment
        with self.queue_lock:
            with self.active_jobs_lock:
                # Check if we have capacity and jobs in queue
                if len(self.active_jobs) >= self.max_workers or not self.job_queue:
                    return
                
                # Get next job from queue
                job_request = self.job_queue.pop(0)
                job_key = f"{job_request.job_id}_{job_request.service_id}"
                
                # Submit job to executor immediately while holding locks
                future = self.executor.submit(self._execute_job, job_request)
                
                # Track the job immediately
                self.active_jobs[job_key] = future
                
                # Get current counts for stats update
                queue_size = len(self.job_queue)
                currently_running = len(self.active_jobs)
        
        # Update stats atomically
        self._update_stats(
            queue_size=queue_size,
            currently_running=currently_running
        )
        
        # Add completion callback outside of locks to prevent deadlock
        future.add_done_callback(lambda f: self._job_completed(job_key, f))
        
        # Log with current stats
        current_stats = self._get_stats_snapshot()
        self.logger.info(f"Job started execution", {
            "job_id": job_request.job_id,
            "service_id": job_request.service_id,
            "active_jobs": current_stats["currently_running"],
            "queue_size": current_stats["queue_size"]
        })
    
    def _execute_job(self, job_request: JobRequest) -> JobResult:
        """
        Execute a single job
        
        Args:
            job_request: Job request to execute
            
        Returns:
            JobResult with execution details
        """
        start_time = datetime.utcnow()
        job_logger = StructuredLogger(job_request.job_id, job_request.service_id, "job_execution")
        
        try:
            job_logger.log_execution_start("job_execution", {
                "submitted_at": job_request.submitted_at.isoformat()
            })
            
            # Step 1: Fetch job configuration
            job_config = self.job_config_manager.fetch_job_config(
                job_request.job_id, job_request.service_id
            )
            
            if not job_config:
                raise Exception("Failed to fetch job configuration")
            
            # Step 2: Update job status to RUNNING
            self.job_config_manager.update_job_status(
                job_request.job_id, job_request.service_id, "RUNNING"
            )
            
            # Step 3: Create and execute module
            module = self._create_module(job_config, job_logger)
            if not module:
                raise Exception(f"Failed to create module for source type: {job_config.source_type}")
            
            # Step 4: Execute async module
            # Get or create event loop for this worker thread
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop in this thread, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Execute async module
            execution_result = loop.run_until_complete(module.execute())
            
            end_time = datetime.utcnow()
            execution_duration = (end_time - start_time).total_seconds()
            
            if execution_result.get("success", False):
                # Success
                self.job_config_manager.update_job_status(
                    job_request.job_id, job_request.service_id, "COMPLETED",
                    {"execution_duration": execution_duration}
                )
                
                job_logger.log_execution_end("job_execution", True, {
                    "execution_duration": execution_duration,
                    "result_summary": execution_result.get("data", {})
                })
                
                return JobResult(
                    job_id=job_request.job_id,
                    service_id=job_request.service_id,
                    success=True,
                    start_time=start_time,
                    end_time=end_time,
                    execution_duration=execution_duration,
                    result_data=execution_result
                )
            else:
                # Failure
                error_message = execution_result.get("error", "Unknown error")
                self.job_config_manager.update_job_status(
                    job_request.job_id, job_request.service_id, "FAILED",
                    {"error": error_message, "execution_duration": execution_duration}
                )
                
                job_logger.log_execution_end("job_execution", False, {
                    "error": error_message,
                    "execution_duration": execution_duration
                })
                
                return JobResult(
                    job_id=job_request.job_id,
                    service_id=job_request.service_id,
                    success=False,
                    start_time=start_time,
                    end_time=end_time,
                    execution_duration=execution_duration,
                    error_message=error_message
                )
                
        except Exception as e:
            end_time = datetime.utcnow()
            execution_duration = (end_time - start_time).total_seconds()
            error_message = f"Job execution failed: {str(e)}"
            
            job_logger.error(error_message, {
                "exception": str(e),
                "execution_duration": execution_duration
            })
            
            self.job_config_manager.update_job_status(
                job_request.job_id, job_request.service_id, "FAILED",
                {"error": error_message, "execution_duration": execution_duration}
            )
            
            return JobResult(
                job_id=job_request.job_id,
                service_id=job_request.service_id,
                success=False,
                start_time=start_time,
                end_time=end_time,
                execution_duration=execution_duration,
                error_message=error_message
            )
    
    def _create_module(self, job_config: JobConfig, job_logger):
        """
        Create appropriate module based on source type
        
        Args:
            job_config: Job configuration
            job_logger: Logger instance
            
        Returns:
            Module instance or None if creation fails
        """
        try:
            # Use factory to create module
            module = ModuleFactory.create_module(job_config)
            
            if module is None:
                job_logger.error(f"Unknown source type: {job_config.source_type}")
                return None
            
            return module
                
        except Exception as e:
            job_logger.error(f"Failed to create module: {str(e)}", {
                "source_type": job_config.source_type,
                "exception": str(e)
            })
            return None
    
    def _job_completed(self, job_key: str, future: concurrent.futures.Future):
        """Handle job completion callback with thread-safe operations"""
        try:
            result = future.result()
            current_stats = None
            
            # Atomic job removal and stats update
            with self.active_jobs_lock:
                # Remove job from active tracking
                if job_key in self.active_jobs:
                    del self.active_jobs[job_key]
                else:
                    # Job already removed - this shouldn't happen but handle gracefully
                    self.logger.warning(f"Job completion callback for already removed job", {
                        "job_key": job_key
                    })
                    return
                
                currently_running = len(self.active_jobs)
            
            # Update completion statistics atomically
            if result.success:
                self._update_stats(
                    total_completed_increment=1,
                    currently_running=currently_running
                )
            else:
                self._update_stats(
                    total_failed_increment=1,
                    currently_running=currently_running
                )
            
            # Store result in completed jobs list
            self.completed_jobs.append(result)
            
            # Get current stats for logging
            current_stats = self._get_stats_snapshot()
            
            self.logger.info(f"Job completed", {
                "job_id": result.job_id,
                "service_id": result.service_id,
                "success": result.success,
                "execution_duration": result.execution_duration,
                "active_jobs": current_stats["currently_running"],
                "queue_size": current_stats["queue_size"],
                "total_completed": current_stats["total_completed"],
                "total_failed": current_stats["total_failed"]
            })
            
            # Try to process more jobs from queue
            # This is safe because _process_queue() has its own locking
            self._process_queue()
            
        except Exception as e:
            self.logger.error(f"Error in job completion callback: {str(e)}", {
                "job_key": job_key,
                "exception": str(e)
            })
            
            # Even on error, try to clean up and continue processing
            with self.active_jobs_lock:
                if job_key in self.active_jobs:
                    del self.active_jobs[job_key]
                    self._update_stats(
                        total_failed_increment=1,
                        currently_running=len(self.active_jobs)
                    )
            
            # Continue processing queue even after error
            self._process_queue()
    
    def get_job_status(self, job_id: str, service_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a job with thread-safe access"""
        job_key = f"{job_id}_{service_id}"
        
        # Check if job is currently running
        with self.active_jobs_lock:
            if job_key in self.active_jobs:
                return {
                    "status": "RUNNING",
                    "job_id": job_id,
                    "service_id": service_id
                }
        
        # Check if job is in queue
        with self.queue_lock:
            for i, job_request in enumerate(self.job_queue):
                if job_request.job_id == job_id and job_request.service_id == service_id:
                    return {
                        "status": "QUEUED",
                        "job_id": job_id,
                        "service_id": service_id,
                        "queue_position": i + 1
                    }
        
        # Check completed jobs (no lock needed as this is append-only)
        for result in self.completed_jobs:
            if result.job_id == job_id and result.service_id == service_id:
                return {
                    "status": "COMPLETED" if result.success else "FAILED",
                    "job_id": job_id,
                    "service_id": service_id,
                    "execution_duration": result.execution_duration,
                    "error_message": result.error_message,
                    "start_time": result.start_time.isoformat(),
                    "end_time": result.end_time.isoformat()
                }
        
        # Job not found
        return None
    
    def get_executor_stats(self) -> Dict[str, Any]:
        """Get executor statistics with thread-safe access"""
        # Get base stats snapshot
        stats_snapshot = self._get_stats_snapshot()
        
        # Get real-time counts with proper locking
        with self.queue_lock:
            with self.active_jobs_lock:
                # Ensure real-time accuracy by getting fresh counts
                current_queue_size = len(self.job_queue)
                current_running = len(self.active_jobs)
                completed_jobs_count = len(self.completed_jobs)
        
        # Update the snapshot with real-time data
        stats_snapshot.update({
            "max_workers": self.max_workers,
            "currently_running": current_running,
            "queue_size": current_queue_size,
            "completed_jobs": completed_jobs_count
        })
        
        return stats_snapshot
    
    def shutdown(self, wait: bool = True, timeout: int = 30):
        """Shutdown the executor with proper cleanup and final statistics"""
        final_stats = self.get_executor_stats()
        
        self.logger.info("Shutting down job executor", {
            "wait_for_completion": wait,
            "timeout_seconds": timeout,
            "final_stats": final_stats
        })
        
        try:
            # Shutdown the thread pool executor
            self.executor.shutdown(wait=wait, timeout=timeout if wait else None)
            
            # Log final execution summary
            self.logger.info("Job executor shutdown completed", {
                "final_statistics": final_stats,
                "shutdown_successful": True
            })
            
        except Exception as e:
            self.logger.error(f"Error during executor shutdown: {str(e)}", {
                "exception": str(e),
                "final_stats": final_stats
            })
