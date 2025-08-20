"""Web Module Specific Exceptions - Production-ready error handling"""

from common.exceptions.base_exception import BaseModuleException


class WebModuleException(BaseModuleException):
    """Base exception for web module operations"""
    pass


class BrowserInitializationError(WebModuleException):
    """Raised when browser initialization fails"""
    def __init__(self, message: str = "Browser initialization failed"):
        super().__init__(message)
        self.error_type = "BROWSER_INIT_ERROR"


class TaskExecutionError(WebModuleException):
    """Raised when task execution fails"""
    def __init__(self, task_id: str, message: str = "Task execution failed"):
        super().__init__(f"Task {task_id}: {message}")
        self.task_id = task_id
        self.error_type = "TASK_EXECUTION_ERROR"


class TaskTimeoutError(WebModuleException):
    """Raised when task execution times out"""
    def __init__(self, task_id: str, timeout_seconds: int):
        super().__init__(f"Task {task_id} timed out after {timeout_seconds} seconds")
        self.task_id = task_id
        self.timeout_seconds = timeout_seconds
        self.error_type = "TASK_TIMEOUT_ERROR"


class LoginAuthenticationError(WebModuleException):
    """Raised when login authentication fails"""
    def __init__(self, message: str = "Login authentication failed"):
        super().__init__(message)
        self.error_type = "LOGIN_AUTH_ERROR"


class ChannelDetectionError(WebModuleException):
    """Raised when channel detection fails"""
    def __init__(self, channel_name: str, message: str = "Channel detection failed"):
        super().__init__(f"Channel '{channel_name}': {message}")
        self.channel_name = channel_name
        self.error_type = "CHANNEL_DETECTION_ERROR"


class DateNavigationError(WebModuleException):
    """Raised when date navigation fails"""
    def __init__(self, message: str = "Date navigation failed"):
        super().__init__(message)
        self.error_type = "DATE_NAVIGATION_ERROR"


class ProgramExtractionError(WebModuleException):
    """Raised when program extraction fails"""
    def __init__(self, message: str = "Program extraction failed"):
        super().__init__(message)
        self.error_type = "PROGRAM_EXTRACTION_ERROR"


class IntelligenceExtractionError(WebModuleException):
    """Raised when intelligence extraction fails"""
    def __init__(self, message: str = "Intelligence extraction failed"):
        super().__init__(message)
        self.error_type = "INTELLIGENCE_EXTRACTION_ERROR"


class CodeGenerationError(WebModuleException):
    """Raised when code generation fails"""
    def __init__(self, message: str = "Code generation failed"):
        super().__init__(message)
        self.error_type = "CODE_GENERATION_ERROR"


class NetworkTimeoutError(WebModuleException):
    """Raised when network operations timeout"""
    def __init__(self, url: str, timeout_seconds: int):
        super().__init__(f"Network timeout for {url} after {timeout_seconds} seconds")
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.error_type = "NETWORK_TIMEOUT_ERROR"


class BrowserCrashError(WebModuleException):
    """Raised when browser crashes during execution"""
    def __init__(self, message: str = "Browser crashed during execution"):
        super().__init__(message)
        self.error_type = "BROWSER_CRASH_ERROR"


class InvalidFlowTypeError(WebModuleException):
    """Raised when invalid flow type is specified"""
    def __init__(self, flow_type: str, valid_flows: list):
        super().__init__(f"Invalid flow type '{flow_type}'. Valid flows: {valid_flows}")
        self.flow_type = flow_type
        self.valid_flows = valid_flows
        self.error_type = "INVALID_FLOW_TYPE_ERROR"


class WebsiteConfigurationError(WebModuleException):
    """Raised when website configuration is invalid"""
    def __init__(self, message: str = "Website configuration error"):
        super().__init__(message)
        self.error_type = "WEBSITE_CONFIG_ERROR"
