"""Browser-use compatibility layer for version-agnostic operations"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from browser_use import Agent, Browser, BrowserConfig, BrowserContextConfig
from browser_use.browser.session import BrowserSession
from browser_use.llm import ChatAWSBedrock, ChatAnthropicBedrock


class BrowserConfigBuilder:
    """Builder pattern for creating browser configurations across different browser-use versions"""
    
    def __init__(self):
        self.config_params = {}
        self.context_params = {}
    
    def set_headless(self, headless: bool):
        self.config_params['headless'] = headless
        return self
    
    def set_security(self, disable_security: bool = True):
        self.config_params['disable_security'] = disable_security
        return self
    
    def add_chrome_args(self, args: List[str]):
        self.config_params['args'] = args
        return self
    
    def set_downloads_path(self, path: str):
        self.context_params['downloads_path'] = path
        return self
    
    def set_viewport(self, no_viewport: bool = True):
        self.context_params['no_viewport'] = no_viewport
        return self
    
    def set_https_errors(self, ignore: bool = True):
        self.context_params['ignore_https_errors'] = ignore
        return self
    
    def set_javascript(self, enabled: bool = True):
        self.context_params['java_script_enabled'] = enabled
        return self
    
    def set_har_recording(self, path: str, mode: str = 'full', content: str = 'embed'):
        self.context_params.update({
            'record_har_path': path,
            'record_har_mode': mode,
            'record_har_content': content,
            'record_har_omit_content': False
        })
        return self
    
    def set_video_recording(self, dir_path: str, video_size: Optional[tuple] = None):
        """Set video recording with optional quality/size configuration"""
        self.context_params['record_video_dir'] = dir_path
        
        # Set video recording size if provided
        if video_size:
            from playwright._impl._api_structures import ViewportSize
            self.context_params['record_video_size'] = ViewportSize(
                width=video_size[0], 
                height=video_size[1]
            )
        
        return self
    
    def set_trace_recording(self, dir_path: str):
        self.context_params['traces_dir'] = dir_path
        return self
    
    def set_user_data_dir(self, path: str):
        self.config_params['user_data_dir'] = path
        return self
    
    def set_highlight_elements(self, enabled: bool):
        self.config_params['highlight_elements'] = enabled
        return self
    
    def build(self):
        """Build browser profile with error handling"""
        try:
            # Import BrowserProfile from browser-use
            from browser_use import BrowserProfile
            
            # Merge all parameters into a single profile
            all_params = {**self.config_params, **self.context_params}
            
            # Create BrowserProfile with all parameters
            browser_profile = BrowserProfile(**all_params)
            return browser_profile
            
        except Exception as e:
            # Fallback to minimal profile
            from browser_use import BrowserProfile
            minimal_params = {
                'headless': self.config_params.get('headless', False),
                'downloads_path': self.context_params.get('downloads_path', '/tmp')
            }
            browser_profile = BrowserProfile(**minimal_params)
            return browser_profile


class BrowserAgentWrapper:
    """Wrapper around browser-use Agent for task-specific operations"""
    
    def __init__(self, task_name: str, task_dir: Path, task: str, browser: BrowserSession, 
                 page=None, controller=None, logger=None, **kwargs):
        self.task_name = task_name
        self.task_dir = task_dir
        self.task_dir.mkdir(parents=True, exist_ok=True)
        
        # Import web_config directly - always gets updated data
        from ..config.web_config import web_config
        self.web_config = web_config
        
        # Set up logger
        self.logger = logger if logger else None
        if not self.logger:
            from common.logger import StructuredLogger
            self.logger = StructuredLogger("web", f"task_{task_name}", "browser_agent")
        
        # Get config from web_config
        browser_config = self.web_config.get_config()["BROWSER"] if self.web_config else {}
        recording_config = self.web_config.get_config()["RECORDING"] if self.web_config else {}
        
        # Task-specific paths
        self.conversation_path = task_dir / "conversation.json"
        self.gif_path = task_dir / f"{task_name}_recording.gif"
        self.trace_path = task_dir / f"{task_name}_trace.zip"
        self.har_path = task_dir / f"{task_name}_network.har"
        
        # Create LLM from web_config
        self.llm = self._create_llm_from_config()
        
        # Get other config values
        self.use_vision = browser_config.get("use_vision", True)
        self.generate_gif = recording_config.get("gif_recording_enabled", True)
        
        # Initialize the underlying Agent
        self.agent = self._create_agent_safely(task, browser, page, controller, **kwargs)
        
        # Task execution state
        self.start_time = None
        self.end_time = None
        self.success = False
        self.error = None
    
    def _create_llm_from_config(self):
        """Create LLM from web_config"""
        if not self.web_config:
            raise ValueError("web_config is required")
            
        try:
            from common.llms.llm_service import LLMService
            llm_service = LLMService(self.task_name)
            llm_config = self.web_config.get_llm_config()
            
            llm = llm_service.create_browser_use_llm(
                model_id=llm_config["model_id"],
                temperature=llm_config["temperature"],
                max_tokens=llm_config["max_tokens"],
                top_p=llm_config["top_p"]
            )
            self.logger.info(f"✅ Created LLM from web_config")
            return llm
        except Exception as e:
            self.logger.error(f"❌ Could not create LLM from web_config: {e}")
            raise
    
    def _create_agent_safely(self, task: str, browser: BrowserSession, page=None, controller=None, **kwargs):
        """Create Agent using internal configuration"""
        
        # Agent parameters from config
        agent_params = {
            'task': task,
            'llm': self.llm,
            'browser_session': browser,
            'use_vision': self.use_vision,
            'save_conversation_path': str(self.conversation_path),
        }
        
        # Add GIF recording if enabled
        if self.generate_gif:
            agent_params['generate_gif'] = str(self.gif_path)
        
        # Add page parameter to share same tab across tasks
        if page is not None:
            agent_params['page'] = page
            self.logger.info(f"🔧 Using shared page for login persistence")
        
        # Add controller if provided
        if controller is not None:
            agent_params['controller'] = controller
        
        try:
            self.logger.info(f"🔧 Creating Agent with BrowserSession (keep_alive=True)")
            self.logger.info(f"🔧 Browser session type: {type(browser).__name__}")
            self.logger.info(f"🔧 Browser session started: {hasattr(browser, '_browser')}")
            self.logger.info(f"🔧 Task: {task[:100]}...")  # Log first 100 chars of task
            self.logger.info(f"🔧 Agent params: {list(agent_params.keys())}")
            
            agent = Agent(**agent_params)
            self.logger.info(f"✅ Agent created successfully for {self.task_name}")
            return agent
        except Exception as e:
            self.logger.error(f"❌ Agent creation failed with full params: {e}")
            self.logger.error(f"❌ Exception type: {type(e).__name__}")
            import traceback
            self.logger.error(f"❌ Traceback: {traceback.format_exc()}")
            
            # Try with minimal parameters (same as browser-use example)
            minimal_params = {
                'task': task,
                'llm': llm,
                'browser_session': browser,  # ✅ FIXED: Use browser_session, not browser
            }
            
            try:
                self.logger.info(f"🔄 Trying minimal params: {list(minimal_params.keys())}")
                agent = Agent(**minimal_params)
                self.logger.info(f"🔄 Agent created with minimal params for {self.task_name}")
                return agent
            except Exception as e2:
                self.logger.error(f"❌ Agent creation failed completely: {e2}")
                raise e2
    
    async def run_with_recording(self, max_steps: int = 30, timeout_seconds: int = 300):
        """Run the agent with comprehensive recording and error handling"""
        self.start_time = datetime.now()
        
        try:
            self.logger.info(f"🚀 Starting task execution: {self.task_name}")
            
            # Run the agent with timeout
            history = await asyncio.wait_for(
                self.agent.run(max_steps=max_steps),
                timeout=timeout_seconds
            )
            
            # Verify outputs
            self._verify_outputs()
            
            self.end_time = datetime.now()
            self.success = True
            
            # Save metadata
            self._save_task_metadata()
            
            self.logger.info(f"✅ Task completed successfully: {self.task_name}")
            return history
            
        except asyncio.TimeoutError:
            self.error = f"Task timed out after {timeout_seconds} seconds"
            self.logger.error(f"⏰ {self.error}")
            raise
        except Exception as e:
            self.error = str(e)
            self.logger.error(f"❌ Task execution failed: {self.task_name} - {e}")
            raise
        finally:
            self.end_time = datetime.now() if not self.end_time else self.end_time
            self._save_task_metadata()
    
    def _verify_outputs(self):
        """Verify that expected outputs were created"""
        if self.gif_path.exists():
            self.logger.info(f"✅ GIF recording created: {self.gif_path}")
        else:
            self.logger.warning(f"⚠️ GIF recording not found: {self.gif_path}")
        
        if self.conversation_path.exists():
            self.logger.info(f"✅ Conversation log created: {self.conversation_path}")
        else:
            self.logger.warning(f"⚠️ Conversation log not found: {self.conversation_path}")
    
    def _save_task_metadata(self):
        """Save task execution metadata using common utilities"""
        from ..utils.common import save_json_file, create_session_metadata
        
        metadata = create_session_metadata(
            session_id=f"task_{self.task_name}",
            task_name=self.task_name,
            start_time=self.start_time.isoformat() if self.start_time else None,
            end_time=self.end_time.isoformat() if self.end_time else None,
            duration_seconds=(self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else None,
            success=self.success,
            error=self.error,
            outputs={
                'conversation_path': str(self.conversation_path),
                'gif_path': str(self.gif_path),
                'trace_path': str(self.trace_path),
                'har_path': str(self.har_path),
            }
        )
        
        metadata_path = self.task_dir / "task_metadata.json"
        if save_json_file(metadata, metadata_path):
            self.logger.info(f"💾 Task metadata saved: {metadata_path}")
        else:
            self.logger.error(f"❌ Failed to save task metadata: {metadata_path}")
    
    def save_history(self, path: str):
        """Save conversation history using browser-use Agent's built-in save_history method"""
        try:
            # Use the Agent's built-in save_history method
            if hasattr(self.agent, 'save_history'):
                self.logger.info(f"Using Agent's built-in save_history method")
                self.agent.save_history(path)
                
                # Verify the file was created and has content
                from pathlib import Path
                history_file = Path(path)
                if history_file.exists():
                    file_size = history_file.stat().st_size
                    self.logger.info(f"✅ History saved using Agent.save_history(): {path} ({file_size} bytes)")
                    return
                else:
                    self.logger.warning(f"Agent.save_history() didn't create file: {path}")
            
            # Fallback: Try to access history attributes directly
            self.logger.info("Trying to access Agent history attributes directly")
            history_data = None
            
            # Check different possible attributes where browser-use stores history
            for attr_name in ['history', '_history', 'agent_history', 'conversation_history']:
                if hasattr(self.agent, attr_name):
                    attr_value = getattr(self.agent, attr_name)
                    if attr_value:
                        history_data = attr_value
                        self.logger.info(f"Found history in agent.{attr_name}")
                        break
            
            # If we found structured history, use it
            if history_data:
                from ..utils.common import save_json_file
                
                # Ensure it's in the expected format
                if isinstance(history_data, list):
                    final_history = {"history": history_data}
                else:
                    final_history = history_data
                
                if save_json_file(final_history, path):
                    self.logger.info(f"💾 Structured history saved: {path}")
                    return
            
            # Final fallback: Create basic history structure
            self.logger.warning("Could not access Agent history, creating basic structure")
            from ..utils.common import save_json_file
            
            fallback_history = {
                "history": [],
                "task_metadata": {
                    'task_name': self.task_name,
                    'task_directory': str(self.task_dir),
                    'start_time': self.start_time.isoformat() if self.start_time else None,
                    'end_time': self.end_time.isoformat() if self.end_time else None,
                    'success': self.success,
                    'error': self.error,
                    'browser_use_version': '0.5.5',
                    'note': 'Agent.save_history() and direct access failed - using fallback format'
                }
            }
            
            if save_json_file(fallback_history, path):
                self.logger.info(f"💾 Fallback history saved: {path}")
            else:
                self.logger.error(f"❌ Failed to save fallback history: {path}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to save history: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    async def close(self):
        """Agent cleanup - browser session stays alive due to keep_alive=True"""
        try:
            # With keep_alive=True, the browser session won't close when agent finishes
            # Just log that the agent task is complete
            self.logger.info(f"🎯 Agent task completed: {self.task_name} - browser session preserved")
        except Exception as e:
            self.logger.warning(f"⚠️ Error during agent cleanup: {e}")


def get_screen_resolution() -> tuple[int, int]:
    """Get screen resolution with fallback"""
    try:
        import tkinter as tk
        root = tk.Tk()
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.destroy()
        return width, height
    except Exception:
        return 1920, 1080  # Fallback resolution
