"""S3 Module Specific Exceptions"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class S3ModuleException(Exception):
    """Base exception for S3 Module"""
    def __init__(self, message: str, error_code: str = None, context: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        logger.error(f"S3ModuleException: {message} (code: {error_code})")

class S3ConnectionError(S3ModuleException):
    """S3 connection related errors"""
    def __init__(self, message: str, bucket: str = None, region: str = None):
        super().__init__(message, "CONNECTION_ERROR", {"bucket": bucket, "region": region})
        logger.error(f"S3 Connection Error - Bucket: {bucket}, Region: {region}, Message: {message}")

class S3DownloadError(S3ModuleException):
    """S3 download related errors"""
    def __init__(self, message: str, remote_path: str = None, local_path: str = None):
        super().__init__(message, "DOWNLOAD_ERROR", {"remote_path": remote_path, "local_path": local_path})
        logger.error(f"S3 Download Error - Remote: {remote_path}, Local: {local_path}, Message: {message}")

class S3ConfigurationError(S3ModuleException):
    """S3 configuration related errors"""
    def __init__(self, message: str, missing_fields: list = None):
        super().__init__(message, "CONFIG_ERROR", {"missing_fields": missing_fields or []})
        logger.error(f"S3 Configuration Error - Missing: {missing_fields}, Message: {message}")

def handle_s3_exception(e: Exception, operation: str, **kwargs) -> S3ModuleException:
    """Convert generic exceptions to S3-specific exceptions"""
    try:
        import botocore.exceptions
        if isinstance(e, botocore.exceptions.ClientError):
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            
            if error_code in ['AccessDenied', 'InvalidAccessKeyId', 'SignatureDoesNotMatch']:
                return S3ConnectionError(f"Authentication failed: {error_msg}", **kwargs)
            elif error_code in ['NoSuchBucket', 'BucketNotFound']:
                return S3ConnectionError(f"Bucket not found: {error_msg}", **kwargs)
            elif error_code in ['NoSuchKey', 'KeyNotFound']:
                return S3DownloadError(f"File not found: {error_msg}", **kwargs)
            else:
                return S3ModuleException(f"S3 API error ({error_code}): {error_msg}")
    except ImportError:
        pass
    
    # Handle network/connection errors
    error_str = str(e).lower()
    if any(keyword in error_str for keyword in ['timeout', 'connection', 'network']):
        return S3ConnectionError(f"Network error: {str(e)}", **kwargs)
    elif 'permission' in error_str or 'access denied' in error_str:
        return S3ConnectionError(f"Permission denied: {str(e)}", **kwargs)
    elif operation == 'download':
        return S3DownloadError(f"Download failed: {str(e)}", **kwargs)
    elif operation == 'connection':
        return S3ConnectionError(f"Connection failed: {str(e)}", **kwargs)
    else:
        return S3ModuleException(f"Operation '{operation}' failed: {str(e)}")
