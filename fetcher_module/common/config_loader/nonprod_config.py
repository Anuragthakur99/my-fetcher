"""Non-Production Environment Configuration"""

from .base_config import BaseConfig


class NonProdConfig(BaseConfig):
    """Non-production environment configuration"""
    
    def __init__(self):
        super().__init__()
        self.config.update(self._load_nonprod_config())
    
    def _load_nonprod_config(self):
        """Load non-prod environment specific infrastructure settings"""
        return {
            # AWS Bedrock Configuration for non-prod environment (empty for now)
            "AWSBEDROCK": {
                "profile": "",
                "region": ""
            },
            
            # AWS S3 - Where all validated files get uploaded
            "AWSS3": {
                "target_bucket": "nonprod-fetcher-bucket",
                "region": "us-west-2"
            },
            
            # Database API - For job configuration and status updates
            "DB": {
                "api_url": "http://nonprod-api.company.com/api/v1"
            },
            
            # System paths for non-prod environment
            "SYSTEM": {
                "temp_path": "/opt/fetcher/temp/",
            },
            
            "LOGGING": {
                "log_path": "/opt/fetcher/logs/"
            }
        }
