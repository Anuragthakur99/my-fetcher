"""Common S3 Upload Logic with Proper Method Signatures"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime


class S3Uploader:
    """Common S3 upload functionality for all modules"""
    
    def __init__(self, job_id: str, channel_id: str, module_name: str, logger=None):
        self.job_id = job_id
        self.channel_id = channel_id
        self.module_name = module_name
        self.logger = logger
        self.bucket_name = self._get_bucket_name()  # TODO: Get from config
    
    def _get_bucket_name(self) -> str:
        """Get S3 bucket name from configuration"""
        # TODO: Replace with actual config loading
        return "dummy-module-bucket"
    
    def _generate_s3_key(self, file_path: str, key_prefix: Optional[str] = None) -> str:
        """Generate S3 key for file upload"""
        timestamp = datetime.utcnow().strftime("%Y/%m/%d/%H")
        filename = os.path.basename(file_path)
        
        if key_prefix:
            s3_key = f"{key_prefix}/{self.module_name}/{self.job_id}_{self.channel_id}/{timestamp}/{filename}"
        else:
            s3_key = f"module-data/{self.module_name}/{self.job_id}_{self.channel_id}/{timestamp}/{filename}"
        
        return s3_key
    
    def upload_file(self, local_file_path: str, s3_key: Optional[str] = None, 
                   metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Upload a single file to S3
        
        Args:
            local_file_path: Path to local file to upload
            s3_key: Optional custom S3 key, if not provided will be auto-generated
            metadata: Optional metadata to attach to S3 object
            
        Returns:
            Dict with upload result information
        """
        if not s3_key:
            s3_key = self._generate_s3_key(local_file_path)
        
        # TODO: Replace with actual S3 upload logic
        if self.logger:
            self.logger.info(f"DUMMY: Uploading file to S3", {
                "local_file": local_file_path,
                "s3_bucket": self.bucket_name,
                "s3_key": s3_key,
                "metadata": metadata
            })
        
        # Simulate upload result
        result = {
            "success": True,
            "s3_bucket": self.bucket_name,
            "s3_key": s3_key,
            "local_file": local_file_path,
            "upload_timestamp": datetime.utcnow().isoformat(),
            "file_size": os.path.getsize(local_file_path) if os.path.exists(local_file_path) else 0
        }
        
        return result
    
    def upload_directory(self, local_dir_path: str, s3_key_prefix: Optional[str] = None,
                        exclude_patterns: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Upload entire directory to S3
        
        Args:
            local_dir_path: Path to local directory to upload
            s3_key_prefix: Optional S3 key prefix for all files
            exclude_patterns: Optional list of file patterns to exclude
            
        Returns:
            List of upload results for each file
        """
        if not os.path.exists(local_dir_path):
            if self.logger:
                self.logger.error(f"Directory not found: {local_dir_path}")
            return []
        
        upload_results = []
        
        # TODO: Replace with actual directory traversal and S3 upload logic
        for root, dirs, files in os.walk(local_dir_path):
            for file in files:
                # Skip excluded patterns
                if exclude_patterns and any(pattern in file for pattern in exclude_patterns):
                    continue
                
                local_file_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_file_path, local_dir_path)
                
                if s3_key_prefix:
                    s3_key = f"{s3_key_prefix}/{relative_path}"
                else:
                    s3_key = self._generate_s3_key(local_file_path, "directory-upload")
                
                result = self.upload_file(local_file_path, s3_key)
                upload_results.append(result)
        
        if self.logger:
            self.logger.info(f"DUMMY: Directory upload completed", {
                "local_directory": local_dir_path,
                "files_uploaded": len(upload_results),
                "s3_key_prefix": s3_key_prefix
            })
        
        return upload_results
    
    def upload_logs(self, log_file_path: str) -> Dict[str, Any]:
        """
        Upload log file to S3 with specific naming convention
        
        Args:
            log_file_path: Path to log file to upload
            
        Returns:
            Upload result information
        """
        log_s3_key = f"logs/{self.module_name}/{self.job_id}_{self.channel_id}/{datetime.utcnow().strftime('%Y/%m/%d')}/{os.path.basename(log_file_path)}"
        
        metadata = {
            "job_id": self.job_id,
            "channel_id": self.channel_id,
            "module_name": self.module_name,
            "log_type": "execution_log"
        }
        
        return self.upload_file(log_file_path, log_s3_key, metadata)
    
    def upload_results(self, results_data: Any, file_format: str = "json") -> Dict[str, Any]:
        """
        Upload module results to S3
        
        Args:
            results_data: Data to upload (will be serialized based on format)
            file_format: Format to save data in (json, csv, txt, etc.)
            
        Returns:
            Upload result information
        """
        import json
        import tempfile
        
        # Create temporary file with results
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        temp_filename = f"results_{self.job_id}_{self.channel_id}_{timestamp}.{file_format}"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{file_format}', delete=False) as temp_file:
            if file_format == "json":
                json.dump(results_data, temp_file, indent=2)
            else:
                # TODO: Add support for other formats
                temp_file.write(str(results_data))
            
            temp_file_path = temp_file.name
        
        try:
            # Upload the temporary file
            results_s3_key = f"results/{self.module_name}/{self.job_id}_{self.channel_id}/{datetime.utcnow().strftime('%Y/%m/%d')}/{temp_filename}"
            
            metadata = {
                "job_id": self.job_id,
                "channel_id": self.channel_id,
                "module_name": self.module_name,
                "data_type": "module_results",
                "format": file_format
            }
            
            result = self.upload_file(temp_file_path, results_s3_key, metadata)
            return result
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
