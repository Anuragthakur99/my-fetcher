"""Base Configuration - Common infrastructure settings"""

from typing import Dict, Any


class BaseConfig:
    """Base configuration class with common infrastructure settings"""
    
    def __init__(self):
        self.config = self._load_base_config()
    
    def _load_base_config(self) -> Dict[str, Any]:
        """Load common infrastructure settings used by all fetchers"""
        return {
            # AWS Bedrock Configuration - Base structure (values set per environment)
            "AWSBEDROCK": {
                "profile": "",  # Set in environment-specific configs
                "region": ""    # Set in environment-specific configs
            },
            
            # System Settings
            "SYSTEM": {
                "max_workers": 20,  # Default worker count
                "job_timeout": 3600,
                "log_level": "INFO",
                "temp_path": "/tmp/fetcher_temp/"
            },
            
            # Logging Settings
            "LOGGING": {
                "log_path": "/var/logs/fetcher/",
                "max_log_size": "10MB",
                "backup_count": 5
            }
        }
    
    def get_config(self) -> Dict[str, Any]:
        """Get the complete base configuration"""
        return self.config
