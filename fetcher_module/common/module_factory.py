"""Module Factory - Clean Factory Pattern Implementation"""

from typing import Optional
from common.interfaces.base_module import BaseModule


class ModuleFactory:
    """Factory for creating module instances based on source type"""
    
    @staticmethod
    def create_module(job_config) -> Optional[BaseModule]:
        """
        Create module instance based on source type
        
        Args:
            job_config: Job configuration object
            
        Returns:
            Module instance or None if unknown source type
        """
        source_type = job_config.source_type.lower()
        
        if source_type == "s3":
            from modules.s3_module.main import S3Module
            return S3Module(job_config)
        
        elif source_type in ["ftp", "sftp"]:
            from modules.ftp_module.main import FTPModule
            return FTPModule(job_config)
        
        elif source_type == "web":
            from modules.web_module.main import WebModule
            return WebModule(job_config)
        
        elif source_type == "api":
            from modules.api_module.main import APIModule
            return APIModule(job_config)
        
        else:
            return None
