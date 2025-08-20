"""Data models for analysis results and outputs"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from .task_models import TaskResult

@dataclass
class AnalysisSession:
    """Complete analysis session information"""
    session_id: str
    target_url: str
    channel_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    task_results: List[TaskResult] = field(default_factory=list)
    final_outputs: Dict[str, Path] = field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate total session duration"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def successful_tasks(self) -> List[TaskResult]:
        """Get list of successful tasks"""
        return [task for task in self.task_results if task.is_successful]
    
    @property
    def failed_tasks(self) -> List[TaskResult]:
        """Get list of failed tasks"""
        return [task for task in self.task_results if not task.is_successful]
    
    @property
    def is_complete(self) -> bool:
        """Check if all tasks completed successfully"""
        return len(self.failed_tasks) == 0 and len(self.task_results) > 0
