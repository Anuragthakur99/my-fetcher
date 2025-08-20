"""Web Module Implementation - Integrated with TaskOrchestrator"""

import os
import sys
import asyncio
from typing import Dict, Any, List
from pathlib import Path

from common.interfaces.base_module import BaseModule
from .config.web_config import web_config


class WebModule(BaseModule):
    """Web data module implementation with TaskOrchestrator integration"""
    
    def __init__(self, job_config):
        super().__init__(job_config)
        
        # Initialize web_config with job_config data
        web_config.initialize_from_job_config(job_config)
        
        # Set output directory to web_module/output
        self.output_dir = Path(__file__).parent / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components that will be set during initialization
        self.task_orchestrator = None
        self.analysis_session = None
    
    def _get_module_name(self) -> str:
        return "web"
    
    def _get_required_config_fields(self) -> List[str]:
        """Required configuration fields for web module"""
        return ["channel_number"]
    
    async def _initialize_module(self) -> bool:
        """Initialize web scraping tools and TaskOrchestrator"""
        try:
            # Validate flow type
            flow_type = web_config.get_flow_type()
            if not web_config.is_valid_flow_type(flow_type):
                self.logger.error(f"Invalid flow type: {flow_type}")
                return False
            
            # Import TaskOrchestrator
            from .core.task_orchestrator import TaskOrchestrator
            
            # Get website configuration
            website_config = web_config.get_website_config()
            login_credentials = website_config.get("login_credentials")
            
            # Initialize TaskOrchestrator with login credentials if provided
            self.task_orchestrator = TaskOrchestrator(login_credentials=login_credentials)
            
            self.logger.info(f"Web module initialized with flow type: {flow_type}")
            self.logger.info(f"Target URL: {website_config.get('target_url')}")
            self.logger.info(f"Channel: {website_config.get('channel_name')}")
            if login_credentials:
                self.logger.info(f"Login enabled for user: {login_credentials.get('username')}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Web initialization failed: {str(e)}")
            return False
    
    async def fetch_data(self) -> Dict[str, Any]:
        """Execute web scraping based on configured flow type"""
        try:
            flow_type = web_config.get_flow_type()
            website_config = web_config.get_website_config()
            
            target_url = website_config["target_url"]
            channel_name = website_config["channel_name"]
            login_credentials = website_config.get("login_credentials")
            
            self.logger.info(f"Starting web scraping with flow: {flow_type}")
            
            if flow_type == "web_full_analysis":
                return await self._execute_full_analysis(target_url, channel_name, login_credentials)
            
            elif flow_type == "web_single_task":
                # For single task, we need task_id from job_config
                task_id = self.get_config_value("task_id", "task_3_program_extraction")
                return await self._execute_single_task(target_url, channel_name, login_credentials, task_id)
            
            elif flow_type == "web_generate_from_existing":
                # For existing intelligence, we need session_id from job_config
                session_id = self.get_config_value("existing_session_id")
                if not session_id:
                    return {"success": False, "error": "existing_session_id required for web_generate_from_existing flow"}
                return await self._execute_generate_from_existing(target_url, channel_name, session_id)
            
            else:
                return {"success": False, "error": f"Unsupported flow type: {flow_type}"}
                
        except Exception as e:
            self.logger.error(f"Web scraping failed: {str(e)}")
            return {"success": False, "error": str(e), "files_downloaded": []}
    
    async def _execute_full_analysis(self, target_url: str, channel_name: str, login_credentials: dict) -> Dict[str, Any]:
        """Execute complete TV schedule analysis workflow"""
        try:
            self.logger.info("Executing full analysis workflow")
            
            # Run complete analysis
            self.analysis_session = await self.task_orchestrator.run_full_analysis(
                target_url=target_url,
                channel_name=channel_name,
                login_credentials=login_credentials
            )
            
            # Collect output files from session directory
            session_dir = Path(self.task_orchestrator.session_dir)
            output_files = self._collect_output_files(session_dir)
            
            # Copy files to our output directory for consistency
            copied_files = self._copy_files_to_output(output_files)
            
            return {
                "success": self.analysis_session.is_complete,
                "files_downloaded": copied_files,
                "metadata": {
                    "session_id": self.analysis_session.session_id,
                    "target_url": target_url,
                    "channel_name": channel_name,
                    "duration_seconds": self.analysis_session.duration_seconds,
                    "successful_tasks": len(self.analysis_session.successful_tasks),
                    "failed_tasks": len(self.analysis_session.failed_tasks),
                    "session_dir": str(session_dir)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Full analysis execution failed: {str(e)}")
            return {"success": False, "error": str(e), "files_downloaded": []}
    
    async def _execute_single_task(self, target_url: str, channel_name: str, login_credentials: dict, task_id: str) -> Dict[str, Any]:
        """Execute single task for debugging"""
        try:
            self.logger.info(f"Executing single task: {task_id}")
            
            # Run single task
            task_result = await self.task_orchestrator.run_single_task(
                task_id=task_id,
                target_url=target_url,
                channel_name=channel_name,
                login_credentials=login_credentials
            )
            
            # Collect output files from task
            output_files = []
            if task_result.outputs:
                for output_name, output_path in task_result.outputs.items():
                    if output_path and os.path.exists(output_path):
                        output_files.append(output_path)
            
            # Copy files to our output directory
            copied_files = self._copy_files_to_output(output_files)
            
            return {
                "success": task_result.is_successful,
                "files_downloaded": copied_files,
                "metadata": {
                    "task_id": task_id,
                    "target_url": target_url,
                    "channel_name": channel_name,
                    "duration_seconds": task_result.duration_seconds,
                    "error_message": task_result.error_message,
                    "task_outputs": task_result.outputs
                }
            }
            
        except Exception as e:
            self.logger.error(f"Single task execution failed: {str(e)}")
            return {"success": False, "error": str(e), "files_downloaded": []}
    
    async def _execute_generate_from_existing(self, target_url: str, channel_name: str, session_id: str) -> Dict[str, Any]:
        """Generate code from existing intelligence session"""
        try:
            self.logger.info(f"Generating code from existing session: {session_id}")
            
            # Import the generate from existing functionality
            # This would need to be adapted from the example
            # For now, return a placeholder
            
            return {
                "success": False,
                "error": "web_generate_from_existing flow not yet implemented",
                "files_downloaded": []
            }
            
        except Exception as e:
            self.logger.error(f"Generate from existing execution failed: {str(e)}")
            return {"success": False, "error": str(e), "files_downloaded": []}
    
    def _collect_output_files(self, session_dir: Path) -> List[str]:
        """Collect all output files from session directory"""
        output_files = []
        
        if not session_dir.exists():
            return output_files
        
        # Collect various file types
        file_patterns = [
            "*.har",           # HAR files
            "*.json",          # JSON intelligence files
            "*.py",            # Generated Python code
            "*.gif",           # GIF recordings
            "*.png",           # Screenshots
            "*.html",          # HTML captures
            "*.log",           # Log files
            "**/task_*/*",     # Task-specific outputs
        ]
        
        for pattern in file_patterns:
            files = list(session_dir.glob(pattern))
            output_files.extend([str(f) for f in files if f.is_file()])
        
        return output_files
    
    def _copy_files_to_output(self, source_files: List[str]) -> List[str]:
        """Copy files to web_module output directory"""
        copied_files = []
        
        for source_file in source_files:
            try:
                source_path = Path(source_file)
                if not source_path.exists():
                    continue
                
                # Create destination path maintaining relative structure
                dest_path = self.output_dir / source_path.name
                
                # Copy file
                import shutil
                shutil.copy2(source_path, dest_path)
                copied_files.append(str(dest_path))
                
            except Exception as e:
                self.logger.warning(f"Failed to copy file {source_file}: {str(e)}")
        
        return copied_files
    
    async def validate_data(self, fetch_result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate scraped web data"""
        try:
            files = fetch_result.get("files_downloaded", [])
            
            # Validate files exist and have content
            valid_files = []
            invalid_files = []
            validation_errors = []
            
            for file_path in files:
                if not os.path.exists(file_path):
                    invalid_files.append(file_path)
                    validation_errors.append(f"File not found: {file_path}")
                    continue
                
                # Check file size
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    invalid_files.append(file_path)
                    validation_errors.append(f"Empty file: {file_path}")
                    continue
                
                # Basic validation passed
                valid_files.append(file_path)
            
            # Set upload folder based on flow type
            flow_type = web_config.get_flow_type()
            upload_folder = f"data/web/ch_{self.channel_number}/{flow_type}"
            
            return {
                "success": len(valid_files) > 0,
                "valid_files": valid_files,
                "invalid_files": invalid_files,
                "validation_errors": validation_errors,
                "upload_folder": upload_folder
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "valid_files": [],
                "invalid_files": files,
                "validation_errors": [str(e)],
                "upload_folder": ""
            }
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.task_orchestrator:
                await self.task_orchestrator.cleanup()
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {str(e)}")


# Wrapper function to handle async execution in sync context
def create_web_module(job_config):
    """Factory function to create WebModule instance"""
    return WebModule(job_config)
