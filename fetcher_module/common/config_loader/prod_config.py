"""Production Environment Configuration"""

from .base_config import BaseConfig


class ProdConfig(BaseConfig):
    """Production environment configuration"""
    
    def __init__(self):
        super().__init__()
        self.config.update(self._load_prod_config())
    
    def _load_prod_config(self):
        """Load production environment specific infrastructure settings"""
        return {
            # AWS Bedrock Configuration for production environment (empty for now)
            "AWSBEDROCK": {
                "profile": "",
                "region": ""
            },
            
            # AWS S3 - Where all validated files get uploaded
            "AWSS3": {
                "target_bucket": "prod-fetcher-bucket",
                "region": "us-east-1"
            },
            
            # Database API - For job configuration and status updates
            "DB": {
                "api_url": "http://api.company.com/api/v1"
            },
            
            # System paths for production environment
            "SYSTEM": {
                "temp_path": "/var/fetcher/temp/",
                "max_workers": 50  # Higher capacity for prod
            },
            
            "LOGGING": {
                "log_path": "/var/logs/fetcher/",
                "log_level": "WARN"  # Less verbose in prod
            }
        }
