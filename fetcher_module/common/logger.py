"""Common Structured Logger with Job Context"""

import logging
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any


class StructuredLogger:
    """Enhanced structured logger with job context for all modules"""
    
    def __init__(self, job_id: str, service_id: str, module_name: str, log_dir: str = "temp/logs"):
        self.job_id = job_id
        self.service_id = service_id
        self.module_name = module_name
        self.log_dir = log_dir
        self.logger = None
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup structured logger with file and console handlers"""
        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create logger
        logger_name = f"{self.job_id}_{self.service_id}_{self.module_name}"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if self.logger.handlers:
            return
        
        # File handler
        log_filename = f"{self.job_id}_{self.service_id}_{self.module_name}.log"
        log_filepath = os.path.join(self.log_dir, log_filename)
        file_handler = logging.FileHandler(log_filepath)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Custom formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _create_log_entry(self, level: str, message: str, extra_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create structured log entry with job context"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "job_id": self.job_id,
            "service_id": self.service_id,
            "module_name": self.module_name,
            "level": level,
            "message": message,
            "thread_id": os.getpid(),  # Process ID for now, can be enhanced with actual thread ID
        }
        
        if extra_data:
            log_entry.update(extra_data)
        
        return log_entry
    
    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log info level message with structured data"""
        log_entry = self._create_log_entry("INFO", message, extra_data)
        self.logger.info(json.dumps(log_entry))
    
    def error(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log error level message with structured data"""
        log_entry = self._create_log_entry("ERROR", message, extra_data)
        self.logger.error(json.dumps(log_entry))
    
    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log debug level message with structured data"""
        log_entry = self._create_log_entry("DEBUG", message, extra_data)
        self.logger.debug(json.dumps(log_entry))
    
    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log warning level message with structured data"""
        log_entry = self._create_log_entry("WARNING", message, extra_data)
        self.logger.warning(json.dumps(log_entry))
    
    def log_execution_start(self, operation: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log start of operation execution"""
        data = {"operation": operation, "status": "STARTED"}
        if extra_data:
            data.update(extra_data)
        self.info(f"Starting {operation}", data)
    
    def log_execution_end(self, operation: str, success: bool = True, extra_data: Optional[Dict[str, Any]] = None):
        """Log end of operation execution"""
        status = "COMPLETED" if success else "FAILED"
        data = {"operation": operation, "status": status}
        if extra_data:
            data.update(extra_data)
        
        if success:
            self.info(f"Completed {operation}", data)
        else:
            self.error(f"Failed {operation}", data)
    
    def get_log_file_path(self) -> str:
        """Get the path to the log file for this job"""
        log_filename = f"{self.job_id}_{self.service_id}_{self.module_name}.log"
        return os.path.join(self.log_dir, log_filename)
