"""Configuration Exception Classes"""


class ConfigException(Exception):
    """Base configuration exception"""
    pass


class ConfigLoadError(ConfigException):
    """Configuration loading errors"""
    pass


class ConfigParseError(ConfigException):
    """Configuration parsing errors"""
    pass


class EnvironmentConfigError(ConfigException):
    """Environment configuration errors"""
    pass
