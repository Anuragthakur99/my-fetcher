"""Common utilities for the TV Schedule Analyzer project"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Union


def save_json_file(data: Dict[str, Any], file_path: Union[str, Path], indent: int = 2) -> bool:
    """
    Save data to JSON file with error handling
    
    Args:
        data: Dictionary to save
        file_path: Path to save the file
        indent: JSON indentation level
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, default=str, ensure_ascii=False)
        return True
    except Exception:
        return False


def load_json_file(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Load data from JSON file with error handling
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dict or None if failed to load
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def generate_file_hash(file_path: Union[str, Path]) -> Optional[str]:
    """
    Generate SHA256 hash of a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: SHA256 hash or None if failed
    """
    try:
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception:
        return None


def ensure_directory(dir_path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if it doesn't
    
    Args:
        dir_path: Directory path
        
    Returns:
        Path: The directory path
    """
    dir_path = Path(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def format_duration(start_time: datetime, end_time: Optional[datetime] = None) -> str:
    """
    Format duration between two datetime objects
    
    Args:
        start_time: Start datetime
        end_time: End datetime (defaults to now)
        
    Returns:
        str: Formatted duration string
    """
    if end_time is None:
        end_time = datetime.now()
    
    duration = end_time - start_time
    total_seconds = int(duration.total_seconds())
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters
    
    Args:
        filename: Original filename
        
    Returns:
        str: Sanitized filename
    """
    import re
    # Remove invalid characters for filenames
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores and dots
    sanitized = sanitized.strip('_.')
    return sanitized


def get_file_size_human(file_path: Union[str, Path]) -> str:
    """
    Get human-readable file size
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: Human-readable file size
    """
    try:
        size = Path(file_path).stat().st_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    except Exception:
        return "Unknown"


class TaskTimer:
    """Context manager for timing operations"""
    
    def __init__(self, task_name: str = "Task"):
        self.task_name = task_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
    
    @property
    def duration(self) -> str:
        if self.start_time and self.end_time:
            return format_duration(self.start_time, self.end_time)
        return "Unknown"
    
    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


def create_session_metadata(session_id: str, **kwargs) -> Dict[str, Any]:
    """
    Create standardized session metadata
    
    Args:
        session_id: Session identifier
        **kwargs: Additional metadata fields
        
    Returns:
        Dict: Session metadata
    """
    metadata = {
        'session_id': session_id,
        'created_at': datetime.now().isoformat(),
        'version': '1.0',
        'browser_use_version': '0.5.5',
        **kwargs
    }
    return metadata
