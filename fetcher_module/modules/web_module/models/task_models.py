"""Data models for task definitions and execution"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

class TaskType(Enum):
    """Types of analysis tasks"""
    LOGIN_AUTHENTICATION = "login_authentication"
    CHANNEL_DETECTION = "channel_detection"
    DATE_NAVIGATION = "date_navigation"
    PROGRAM_EXTRACTION = "program_extraction"
    SITE_BEHAVIOR = "site_behavior"
    INTELLIGENCE_EXTRACTION = "intelligence_extraction"
    FINAL_MERGE = "final_merge"

class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class TaskDefinition:
    """Definition of a single analysis task"""
    task_id: str
    task_type: TaskType
    name: str
    description: str
    prompt_template: str
    time_limit_seconds: int
    expected_outputs: List[str]
    dependencies: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    capture_enabled: bool = True  # Whether this task supports HTML/screenshot capture

@dataclass
class TaskContext:
    """Context information for task execution"""
    session_id: str
    target_url: str
    channel_name: str
    task_dir: Path
    previous_results: Dict[str, Any] = field(default_factory=dict)
    login_credentials: Optional[Dict[str, str]] = None  # Optional login credentials

@dataclass
class CaptureData:
    """Data captured during task execution"""
    html_content: str
    screenshot_path: Path
    element_selector: str
    capture_timestamp: datetime
    additional_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskResult:
    """Result of task execution"""
    task_id: str
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    outputs: Dict[str, Path] = field(default_factory=dict)
    captured_data: Optional[CaptureData] = None
    error_message: Optional[str] = None
    intelligence_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate task duration in seconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def is_successful(self) -> bool:
        """Check if task completed successfully"""
        return self.status == TaskStatus.SUCCESS
