"""Local Environment Configuration"""

from .base_config import BaseConfig


class LocalConfig(BaseConfig):
    """Local development environment configuration"""
    
    def __init__(self):
        super().__init__()
        self.config.update(self._load_local_config())
    
    def _load_local_config(self):
        """Load local environment specific infrastructure settings"""
        return {
            # AWS Bedrock Configuration for local development
            "AWSBEDROCK": {
                "profile": "ai-shared-sandbox-nonprod-/AI-DEVELOPER",
                "region": "us-east-1"
            },
            
            # AWS S3 - Where all validated files get uploaded
            "AWSS3": {
                "target_bucket": "local-dev-fetcher-bucket",
                "region": "us-east-1"
            },
            
            # Database API - For job configuration and status updates
            "DB": {
                "api_url": "http://localhost:8080/api/v1"
            },
            
            # Override system paths for local development
            "SYSTEM": {
                "temp_path": "./temp/",
                "max_workers": 5  # Lower for local development
            },
            
            "LOGGING": {
                "log_path": "./temp/logs/"
            },
            
            # Git Configuration for code generation and deployment
            "GIT": {
                "base_repo_path": "/Users/bab2402/PycharmProjects/fetchers",
                "default_branch": "main",
                "auto_sync": True,
                "modules": {
                    "web": "web",
                    "api": "api",
                    "s3": "s3", 
                    "ftp": "ftp"
                }
            }
        }
