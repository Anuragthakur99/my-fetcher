"""Base Module Interface - Clean Implementation with Async Support"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import tempfile
import os
import asyncio

from common.logger import StructuredLogger
from common.s3_uploader import S3Uploader


class BaseModule(ABC):
    """Base class for all data modules: Fetch → Validate → Upload"""
    
    def __init__(self, job_config):
        self.job_config = job_config
        self.job_id = job_config.job_id
        self.channel_number = job_config.channel_number
        self.source_type = job_config.source_type
        
        # Initialize components
        module_name = self._get_module_name()
        self.logger = StructuredLogger(self.job_id, f"ch_{self.channel_number}", module_name)
        self.s3_uploader = S3Uploader(self.job_id, f"ch_{self.channel_number}", module_name, self.logger)
        
        # Create temp directory
        self.temp_dir = tempfile.mkdtemp(prefix=f"{self.job_id}_ch{self.channel_number}_")
    
    @abstractmethod
    def _get_module_name(self) -> str:
        """Return module name (e.g., 's3', 'ftp', 'web', 'api')"""
        pass
    
    @abstractmethod
    def _get_required_config_fields(self) -> List[str]:
        """Return list of required configuration fields"""
        pass
    
    @abstractmethod
    async def _initialize_module(self) -> bool:
        """Initialize module-specific resources (async)"""
        pass
    
    @abstractmethod
    async def fetch_data(self) -> Dict[str, Any]:
        """
        Fetch data and save to temp directory (async)
        Returns: {"success": bool, "files_downloaded": List[str], "metadata": Dict}
        """
        pass
    
    @abstractmethod
    async def validate_data(self, fetch_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate fetched files (async)
        Returns: {"success": bool, "valid_files": List[str], "invalid_files": List[str], 
                 "validation_errors": List[str], "upload_folder": str}
        """
        pass
    
    def get_config_value(self, key: str, default=None):
        """Get config value from job_config (channel → fetcher → environment priority)"""
        if key in self.job_config.channel_config:
            return self.job_config.channel_config[key]
        elif key in self.job_config.fetcher_config:
            return self.job_config.fetcher_config[key]
        elif key in self.job_config.environment_config:
            return self.job_config.environment_config[key]
        else:
            return default
    
    def validate_config(self) -> bool:
        """Validate required configuration fields"""
        try:
            required_fields = self._get_required_config_fields()
            
            # TODO: Implement proper validation logic
            # Check if all required fields are available in any config source
            # Log missing fields and return False if any are missing
            
            # Simple check for now
            for field in required_fields:
                if self.get_config_value(field) is None:
                    self.logger.error(f"Missing required config field: {field}")
                    return False
            
            self.logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {str(e)}")
            return False
    
    async def execute(self) -> Dict[str, Any]:
        """Main execution: Initialize → Fetch → Validate → Upload (async)"""
        try:
            # Initialize
            if not await self._initialize_module():
                return {"success": False, "error": "Initialization failed"}
            
            # Validate config
            if not self.validate_config():
                return {"success": False, "error": "Config validation failed"}
            
            # Fetch data
            fetch_result = await self.fetch_data()
            if not fetch_result.get("success"):
                return {"success": False, "error": "Fetch failed", "details": fetch_result}
            
            # Validate data
            validation_result = await self.validate_data(fetch_result)
            if not validation_result.get("success"):
                return {"success": False, "error": "Validation failed", "details": validation_result}
            
            # Upload files
            upload_result = await self._upload_files(validation_result)
            if not upload_result.get("success"):
                return {"success": False, "error": "Upload failed", "details": upload_result}
            
            # Cleanup
            self._cleanup()
            
            return {
                "success": True,
                "fetch_result": fetch_result,
                "validation_result": validation_result,
                "upload_result": upload_result
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _upload_files(self, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Upload valid files to S3 (async)"""
        try:
            valid_files = validation_result.get("valid_files", [])
            upload_folder = validation_result.get("upload_folder", "")
            
            # TODO: Implement actual S3 upload
            # For each file in valid_files:
            #   - Generate S3 key: f"{upload_folder}/{filename}"
            #   - Call self.s3_uploader.upload_file(file_path, s3_key, metadata)
            
            return {
                "success": True,
                "uploaded_files": valid_files,
                "upload_folder": upload_folder
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _cleanup(self):
        """Clean up temp directory"""
        try:
            if os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
        except:
            pass
