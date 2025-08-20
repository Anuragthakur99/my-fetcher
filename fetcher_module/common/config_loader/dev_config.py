"""Dev Environment Configuration"""

from .base_config import BaseConfig


class DevConfig(BaseConfig):
    """Development environment configuration"""
    
    def __init__(self):
        super().__init__()
        self.config.update(self._load_dev_config())
    
    def _load_dev_config(self):
        """Load dev environment specific infrastructure settings"""
        return {
            # AWS Bedrock Configuration for dev environment (empty for now)
            "AWSBEDROCK": {
                "profile": "",
                "region": ""
            },
            
            # AWS S3 - Where all validated files get uploaded
            "AWSS3": {
                "target_bucket": "dev-fetcher-bucket",
                "region": "us-west-2"
            },
            
            # Database API - For job configuration and status updates
            "DB": {
                "api_url": "http://dev-api.company.com/api/v1"
            },
            
            # System paths for dev environment
            "SYSTEM": {
                "temp_path": "/opt/fetcher/temp/",
            },
            
            "LOGGING": {
                "log_path": "/opt/fetcher/logs/"
            }
        }
