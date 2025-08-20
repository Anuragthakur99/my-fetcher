"""API Module Specific Exceptions"""


class APIModuleException(Exception):
    """Base exception for API Module"""
    pass


class APIConnectionError(APIModuleException):
    """API connection related errors"""
    pass


class APIResponseError(APIModuleException):
    """API response related errors"""
    pass


class APIConfigurationError(APIModuleException):
    """API configuration related errors"""
    pass
