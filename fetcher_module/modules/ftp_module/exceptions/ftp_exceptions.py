"""FTP Module Specific Exceptions"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class FTPModuleException(Exception):
    """Base exception for FTP Module"""
    def __init__(self, message: str, error_code: str = None, context: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        logger.error(f"FTPModuleException: {message} (code: {error_code})")

class FTPConnectionError(FTPModuleException):
    """FTP connection related errors"""
    def __init__(self, message: str, host: str = None, port: int = None):
        super().__init__(message, "CONNECTION_ERROR", {"host": host, "port": port})
        logger.error(f"FTP Connection Error - Host: {host}, Port: {port}, Message: {message}")

class FTPDownloadError(FTPModuleException):
    """FTP download related errors"""
    def __init__(self, message: str, remote_path: str = None, local_path: str = None):
        super().__init__(message, "DOWNLOAD_ERROR", {"remote_path": remote_path, "local_path": local_path})
        logger.error(f"FTP Download Error - Remote: {remote_path}, Local: {local_path}, Message: {message}")

class FTPConfigurationError(FTPModuleException):
    """FTP configuration related errors"""
    def __init__(self, message: str, missing_fields: list = None):
        super().__init__(message, "CONFIG_ERROR", {"missing_fields": missing_fields or []})
        logger.error(f"FTP Configuration Error - Missing: {missing_fields}, Message: {message}")

class SFTPConnectionError(FTPModuleException):
    """SFTP connection related errors"""
    def __init__(self, message: str, host: str = None, port: int = None):
        super().__init__(message, "SFTP_CONNECTION_ERROR", {"host": host, "port": port})
        logger.error(f"SFTP Connection Error - Host: {host}, Port: {port}, Message: {message}")

class SFTPDownloadError(FTPModuleException):
    """SFTP download related errors"""
    def __init__(self, message: str, remote_path: str = None, local_path: str = None):
        super().__init__(message, "SFTP_DOWNLOAD_ERROR", {"remote_path": remote_path, "local_path": local_path})
        logger.error(f"SFTP Download Error - Remote: {remote_path}, Local: {local_path}, Message: {message}")

def handle_ftp_exception(e: Exception, operation: str, **kwargs) -> FTPModuleException:
    """Convert generic exceptions to FTP-specific exceptions"""
    error_str = str(e).lower()
    
    # FTP-specific error handling
    if 'ftp' in error_str or kwargs.get('protocol') == 'ftp':
        if 'passive mode' in error_str or 'pasv' in error_str:
            return FTPConnectionError(f"FTP passive mode failed: {str(e)}", **kwargs)
        elif 'data connection' in error_str:
            return FTPConnectionError(f"FTP data connection failed: {str(e)}", **kwargs)
        elif operation == 'download':
            return FTPDownloadError(f"FTP download failed: {str(e)}", **kwargs)
        elif operation == 'connection':
            return FTPConnectionError(f"FTP connection failed: {str(e)}", **kwargs)
    
    # SFTP-specific error handling
    elif 'sftp' in error_str or 'ssh' in error_str or kwargs.get('protocol') == 'sftp':
        if 'handshake' in error_str or 'protocol' in error_str:
            return SFTPConnectionError(f"SSH handshake failed: {str(e)}", **kwargs)
        elif 'key' in error_str and 'authentication' in error_str:
            return SFTPConnectionError(f"SSH key authentication failed: {str(e)}", **kwargs)
        elif operation == 'download':
            return SFTPDownloadError(f"SFTP download failed: {str(e)}", **kwargs)
        elif operation == 'connection':
            return SFTPConnectionError(f"SFTP connection failed: {str(e)}", **kwargs)
    
    # Network/connection errors
    if any(keyword in error_str for keyword in ['timeout', 'connection', 'network']):
        protocol = kwargs.get('protocol', 'FTP/SFTP')
        if protocol == 'sftp':
            return SFTPConnectionError(f"Network error: {str(e)}", **kwargs)
        else:
            return FTPConnectionError(f"Network error: {str(e)}", **kwargs)
    
    elif 'permission' in error_str or 'access denied' in error_str:
        protocol = kwargs.get('protocol', 'FTP/SFTP')
        if protocol == 'sftp':
            return SFTPConnectionError(f"Permission denied: {str(e)}", **kwargs)
        else:
            return FTPConnectionError(f"Permission denied: {str(e)}", **kwargs)
    
    # Generic error
    return FTPModuleException(f"Operation '{operation}' failed: {str(e)}")