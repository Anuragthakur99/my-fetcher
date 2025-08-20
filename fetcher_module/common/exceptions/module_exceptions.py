"""Module-specific exceptions for better error handling"""

from .base_exception import BaseModuleException


class ModuleInitializationError(BaseModuleException):
    """Raised when module initialization fails"""
    pass


class DataFetchError(BaseModuleException):
    """Raised when data fetching fails"""
    pass


class DataProcessingError(BaseModuleException):
    """Raised when data processing fails"""
    pass


class ConfigurationError(BaseModuleException):
    """Raised when configuration is invalid"""
    pass


class S3UploadError(BaseModuleException):
    """Raised when S3 upload fails"""
    pass


class JobExecutionError(BaseModuleException):
    """Raised when job execution fails"""
    pass


class RetryableError(BaseModuleException):
    """Base class for errors that can be retried"""
    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class NetworkError(RetryableError):
    """Network-related errors that can be retried"""
    pass


class RateLimitError(RetryableError):
    """Rate limiting errors that can be retried"""
    pass
