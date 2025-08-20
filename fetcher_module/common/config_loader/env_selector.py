"""Environment Selector - Loads appropriate config based on environment"""

import os
from typing import Dict, Any
from .local_config import LocalConfig
from .dev_config import DevConfig
from .prod_config import ProdConfig
from .nonprod_config import NonProdConfig


class EnvironmentSelector:
    """Selects and loads appropriate environment configuration"""
    
    def __init__(self):
        self.config_map = {
            "local": LocalConfig,
            "dev": DevConfig,
            "nonprod": NonProdConfig,
            "prod": ProdConfig
        }
    
    def load_config(self, environment: str = None) -> Dict[str, Any]:
        """
        Load configuration for specified environment
        
        Args:
            environment: Environment name (local, dev, nonprod, prod)
                        If None, uses ENVIRONMENT from os.environ, defaults to 'local'
            
        Returns:
            Configuration dictionary
        """
        if environment is None:
            environment = os.environ.get('ENVIRONMENT', 'local')
            
        if environment not in self.config_map:
            raise ValueError(f"Unknown environment: {environment}. Available: {list(self.config_map.keys())}")
        
        config_class = self.config_map[environment]
        config_instance = config_class()
        return config_instance.get_config()
    
    def get_available_environments(self) -> list:
        """Get list of available environments"""
        return list(self.config_map.keys())
