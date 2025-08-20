"""Configuration management for TV Schedule Analyzer"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

class Config:
    """Centralized configuration management"""
    
    def __init__(self):
        # Load environment variables
        env_path = Path(__file__).parent.parent.parent / '.env'
        load_dotenv(env_path)
        
        # AWS Configuration
        self.aws_profile = os.getenv('AWS_PROFILE', 'default')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.bedrock_model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-5-sonnet-20241022-v2:0')
        
        # LLM Inference Parameters
        self.llm_temperature = float(os.getenv('LLM_TEMPERATURE', '0.1'))
        self.llm_max_tokens = int(os.getenv('LLM_MAX_TOKENS', '25000'))
        self.llm_top_p = float(os.getenv('LLM_TOP_P', '0.9'))
        
        # Browser Configuration
        self.browser_headless = os.getenv('BROWSER_HEADLESS', 'false').lower() == 'true'
        self.browser_timeout = int(os.getenv('BROWSER_TIMEOUT', '30000'))
        self.highlight_elements = os.getenv('HIGHLIGHT_ELEMENTS', 'false').lower() == 'true'
        
        # Browser Profile Configuration
        self.browser_profile_name = os.getenv('BROWSER_PROFILE_NAME', 'tv_analyzer_temp')
        self.browser_profile_cleanup = os.getenv('BROWSER_PROFILE_CLEANUP', 'true').lower() == 'true'
        self.browser_profile_base_dir = os.getenv('BROWSER_PROFILE_BASE_DIR', '~/.config/browseruse/profiles')
        
        # Storage Configuration
        self.output_dir = Path(os.getenv('OUTPUT_DIR', './output'))
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        
        # HAR Recording Configuration
        self.har_recording_mode = os.getenv('HAR_RECORDING_MODE', 'task_based').lower()
        
        # Video Recording Configuration
        self.enable_global_video_recording = os.getenv('ENABLE_GLOBAL_VIDEO_RECORDING', 'false').lower() == 'true'
        self.video_recording_quality = os.getenv('VIDEO_RECORDING_QUALITY', 'medium').lower()  # low, medium, high
        
        # GIF Recording Configuration
        self.gif_recording_mode = os.getenv('GIF_RECORDING_MODE', 'task').lower()  # 'session' or 'task'
        
        # Global Recording Features Configuration
        self.enable_global_trace_recording = os.getenv('ENABLE_GLOBAL_TRACE_RECORDING', 'false').lower() == 'true'
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_session_dir(self, session_id: str) -> Path:
        """Get session-specific output directory"""
        session_dir = self.output_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir
    
    def get_task_dir(self, session_id: str, task_id: str) -> Path:
        """Get task-specific output directory"""
        task_dir = self.get_session_dir(session_id) / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        return task_dir
    
    def is_task_based_har_recording(self) -> bool:
        """Check if task-based HAR recording is enabled"""
        return self.har_recording_mode == 'task_based'
    
    def is_global_traditional_har_recording(self) -> bool:
        """Check if global traditional HAR recording is enabled"""
        return self.har_recording_mode == 'global_traditional'
    
    def get_video_recording_size(self) -> Optional[tuple]:
        """Get video recording size based on quality setting"""
        if not self.enable_global_video_recording:
            return None
            
        # Define quality presets (width, height)
        quality_presets = {
            'low': (1280, 720),      # 720p - smaller file size
            'medium': (1920, 1080),  # 1080p - balanced quality/size
            'high': (2560, 1440),    # 1440p - high quality, larger files
        }
        
        return quality_presets.get(self.video_recording_quality, quality_presets['medium'])

# Global config instance
config = Config()
