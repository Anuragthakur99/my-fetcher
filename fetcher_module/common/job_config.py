"""Job Configuration Manager"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from common.config_loader.env_selector import EnvironmentSelector


@dataclass
class JobConfig:
    """Job configuration data structure"""
    job_id: str
    channel_number: int
    source_type: str
    environment_config: Dict[str, Any]
    channel_config: Dict[str, Any]
    fetcher_config: Dict[str, Any]
    raw_config: Dict[str, Any]


class JobConfigManager:
    """Job configuration manager"""
    
    def __init__(self, environment: str = "local", logger=None):
        self.environment = environment
        self.logger = logger
        
        env_selector = EnvironmentSelector()
        self.environment_config = env_selector.load_config(environment)
        
        if self.logger:
            self.logger.info("JobConfigManager initialized", {
                "environment": environment
            })
    
    def create_job_config(self, job_data: Dict[str, Any]) -> Optional[JobConfig]:
        """Create job configuration from job data"""
        try:
            job_id = job_data.get("job_id")
            channel_number = job_data.get("channel_number")
            source_type = job_data.get("source_type")
            
            if not all([job_id, channel_number is not None, source_type]):
                if self.logger:
                    self.logger.error("Missing required job configuration fields")
                return None
            
            channel_config = self._get_channel_config(channel_number, source_type)
            fetcher_config = self._get_fetcher_config(source_type)
            
            job_config = JobConfig(
                job_id=job_id,
                channel_number=channel_number,
                source_type=source_type,
                environment_config=self.environment_config,
                channel_config=channel_config,
                fetcher_config=fetcher_config,
                raw_config=job_data
            )
            
            if self.logger:
                self.logger.info("Job configuration created successfully", {
                    "job_id": job_id,
                    "channel_number": channel_number,
                    "source_type": source_type
                })
            
            return job_config
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to create job configuration: {str(e)}")
            return None
    
    def update_job_status(self, job_id: str, channel_number: int, status: str, 
                         additional_data: Optional[Dict[str, Any]] = None):
        """Update job status via API"""
        try:
            if self.logger:
                self.logger.info("Updating job status", {
                    "job_id": job_id,
                    "channel_number": channel_number,
                    "status": status
                })
            
            # TODO: Replace with actual API call to update job status
            # api_url = self.environment_config["DB"]["api_url"]
            # payload = {"job_id": job_id, "channel_number": channel_number, "status": status}
            # response = requests.put(f"{api_url}/jobs/{job_id}/status", json=payload)
            
            if self.logger:
                self.logger.info(f"Job status updated to {status}")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to update job status: {str(e)}")
    
    def _get_channel_config(self, channel_number: int, source_type: str) -> Dict[str, Any]:
        """Get channel configuration - module will interpret this"""
        # TODO: Replace with actual channel configuration from API/database
        return {
            "channel_number": channel_number,
            "source_type": source_type,
            "is_active": True
        }
    
    def _get_fetcher_config(self, source_type: str) -> Dict[str, Any]:
        """Get fetcher configuration - module will interpret this"""
        # TODO: Replace with actual fetcher configuration from API/database
        return {
            "source_type": source_type,
            "timeout": 30,
            "retry_count": 3
        }
