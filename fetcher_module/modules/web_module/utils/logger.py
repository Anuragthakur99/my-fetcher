"""Logging configuration for TV Schedule Analyzer"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from .config import config

def setup_logger(name: str, session_id: str = None) -> logging.Logger:
    """Setup logger with file and console handlers"""
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.log_level))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if session_id provided)
    if session_id:
        log_file = config.get_session_dir(session_id) / 'analyzer.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# Default logger
default_logger = setup_logger('tv_schedule_analyzer')
