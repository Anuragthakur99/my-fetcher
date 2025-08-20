"""Base Exception Classes"""


class ModuleException(Exception):
    """Base exception for all module errors"""
    pass


class BaseModuleException(ModuleException):
    """Base exception for module-specific errors"""
    pass


class ConfigurationException(ModuleException):
    """Base exception for configuration-related errors"""
    pass
