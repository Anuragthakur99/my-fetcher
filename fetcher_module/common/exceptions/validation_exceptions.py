"""Validation Exception Classes"""


class ValidationException(Exception):
    """Base validation exception"""
    pass


class ConfigValidationError(ValidationException):
    """Configuration validation errors"""
    pass


class DataValidationError(ValidationException):
    """Data validation errors"""
    pass


class ParameterValidationError(ValidationException):
    """Parameter validation errors"""
    pass
