"""Web Module Configuration - Production-ready web scraping settings"""

from pathlib import Path
from typing import Dict, Any, Optional


class WebModuleConfig:
    """Configuration class for web scraping specific settings"""
    
    def __init__(self):
        self._project_root = self._get_project_root()
        self.config = self._load_web_config()
        self.job_config_data = {}
    
    def _get_project_root(self) -> Path:
        """Get project root directory using module path"""
        # Get the fetcher_module root directory
        # This file is at: fetcher_module/modules/web_module/config/web_config.py
        # So go up 3 levels to get to fetcher_module
        return Path(__file__).parent.parent.parent.parent
    
    def _load_web_config(self) -> Dict[str, Any]:
        """Load web scraping specific configuration"""
        web_module_dir = Path(__file__).parent.parent
        
        return {
            "FLOW": {
                "flow_type": "web_full_analysis",
                "available_flows": [
                    "web_full_analysis",
                    "web_single_task",
                    "web_generate_from_existing"
                ]
            },
            
            "WEBSITE": {
                "target_url": "",
                "channel_name": "",
                "login_credentials": None
            },
            
            "BEDROCK": {
                "model_id": "arn:aws:bedrock:us-east-1:536697239187:application-inference-profile/6d1roc10vvuc"
            },
            
            "LLM": {
                "temperature": 0.2,
                "max_tokens": 15000,
                "top_p": 0.9
            },
            
            "BROWSER": {
                "headless": False,
                "timeout": 30000,
                "highlight_elements": False,
                "anonymized_telemetry": False,
                "logging_level": "info",
                "profile_name": "tv_analyzer_temp",
                "profile_cleanup": True,
                "use_vision": True
            },
            
            "STORAGE": {
                "output_dir": str(web_module_dir / "output"),
                "prompts_dir": str(self._project_root / "prompts" / "global" / "web")
            },
            
            "RECORDING": {
                "har_recording_mode": "global_traditional",
                "enable_global_video_recording": True,
                "video_recording_quality": "medium",
                "enable_global_trace_recording": False,
                "gif_recording_mode": "task",
                "gif_recording_enabled": True
            },
            
            "TASKS": {
                "task_0_login_authentication": {
                    "timeout_seconds": 500,
                    "max_steps": 30
                },
                "task_1_channel_detection": {
                    "timeout_seconds": 1000,
                    "max_steps": 30
                },
                "task_2_date_navigation": {
                    "timeout_seconds": 1000,
                    "max_steps": 30
                },
                "task_3_program_extraction": {
                    "timeout_seconds": 1000,
                    "max_steps": 30
                }
            },
            
            "WAIT_TIMES": {
                "short_wait": 500,
                "medium_wait": 1000,
                "long_wait": 2000,
                "extra_long_wait": 5000
            },
            
            "UI": {
                "regular_font_size": 36,
                "title_font_size": 48,
                "goal_font_size": 40
            },
            
            "HTTP": {
                "read_timeout": 600,
                "connect_timeout": 60
            }
        }
    
    def initialize_from_job_config(self, job_config) -> None:
        """Initialize configuration from job_config"""
        try:
            # Extract configuration from job_config
            target_url = self._get_job_config_value(job_config, "url")
            channel_name = self._get_job_config_value(job_config, "channel_name")
            login_username = self._get_job_config_value(job_config, "username")
            login_password = self._get_job_config_value(job_config, "password")
            flow_type = self._get_job_config_value(job_config, "flow_type", "web_full_analysis")
            
            # Build login credentials if provided
            login_credentials = None
            if login_username and login_password:
                login_credentials = {
                    "username": login_username,
                    "password": login_password
                }
            
            # Update configuration safely
            if target_url:
                self.config["WEBSITE"]["target_url"] = target_url
            if channel_name:
                self.config["WEBSITE"]["channel_name"] = channel_name
            if login_credentials:
                self.config["WEBSITE"]["login_credentials"] = login_credentials
            if flow_type and self.is_valid_flow_type(flow_type):
                self.config["FLOW"]["flow_type"] = flow_type
            
            # Store job_config reference
            self.job_config_data = {
                "target_url": target_url,
                "channel_name": channel_name,
                "login_credentials": login_credentials,
                "flow_type": flow_type
            }
            
        except Exception as e:
            # Log error but don't fail - use defaults
            print(f"Warning: Failed to initialize from job_config: {e}")
            self.job_config_data = {}
    
    def _get_job_config_value(self, job_config, key: str, default: Any = None) -> Any:
        """Safely extract value from job_config"""
        try:
            if hasattr(job_config, 'raw_config'):
                return job_config.raw_config.get(key, default)
            elif hasattr(job_config, 'get_config_value'):
                return job_config.get_config_value(key, default)
            else:
                return default
        except Exception:
            return default
    
    def get_config(self) -> Dict[str, Any]:
        """Get complete web module configuration"""
        return self.config
    
    def get_flow_type(self) -> str:
        """Get current flow type"""
        return self.config["FLOW"]["flow_type"]
    
    def get_website_config(self) -> Dict[str, Any]:
        """Get website-specific configuration"""
        return self.config["WEBSITE"]
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration for framework integration"""
        return {
            "model_id": self.config["BEDROCK"]["model_id"],
            "temperature": self.config["LLM"]["temperature"],
            "max_tokens": self.config["LLM"]["max_tokens"],
            "top_p": self.config["LLM"]["top_p"]
        }
    
    def get_task_config(self, task_id: str) -> Dict[str, Any]:
        """Get configuration for specific task"""
        return self.config["TASKS"].get(task_id, {
            "timeout_seconds": 1000,
            "max_steps": 30
        })
    
    def get_wait_time(self, wait_type: str) -> int:
        """Get wait time by type"""
        return self.config["WAIT_TIMES"].get(wait_type, 1000)
    
    def get_prompts_dir(self) -> str:
        """Get prompts directory path"""
        return self.config["STORAGE"]["prompts_dir"]
    
    def is_valid_flow_type(self, flow_type: str) -> bool:
        """Validate flow type"""
        return flow_type in self.config["FLOW"]["available_flows"]
    
    def is_task_based_har_recording(self) -> bool:
        """Check if task-based HAR recording is enabled"""
        return self.config["RECORDING"]["har_recording_mode"] == "task_based"
    
    def get_task_dir(self, session_id: str, task_id: str) -> Path:
        """Get task-specific directory path"""
        base_dir = Path(self.config["STORAGE"]["output_dir"])
        return base_dir / f"session_{session_id}" / task_id
    
    def get_session_dir(self, session_id: str) -> Path:
        """Get session directory path"""
        base_dir = Path(self.config["STORAGE"]["output_dir"])
        return base_dir / f"session_{session_id}"


# Global instance
web_config = WebModuleConfig()
