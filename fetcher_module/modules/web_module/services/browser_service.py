"""Browser automation service with single session and task-specific storage - Clean Architecture"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Browser-use 0.5.5 imports
from browser_use import Browser, Controller
from browser_use.browser.session import BrowserSession

from ..models.task_models import TaskContext, TaskResult, TaskStatus, CaptureData
from .capture_service import CaptureService
from .enhanced_har_recorder import EnhancedHARRecorder
from .file_based_har_recorder import FileBasedHARRecorder
from .browser_compatibility import BrowserConfigBuilder, BrowserAgentWrapper, get_screen_resolution
from ..utils.common import save_json_file, create_session_metadata, TaskTimer, format_duration
from ..config.web_config import web_config


class BrowserService:
    """
    Browser automation service with configurable HAR recording
    
    Features:
    - Composition-based architecture (no inheritance)
    - Browser-use version compatibility layer
    - Configurable HAR recording modes (task-based vs global traditional)
    - Comprehensive error handling and fallbacks
    - Clean separation of concerns
    """
    
    def __init__(self, session_id: str, logger=None):
        self.session_id = session_id
        
        # Use provided logger or create default
        if logger:
            self.logger = logger
        else:
            from common.logger import StructuredLogger
            self.logger = StructuredLogger("web", f"session_{self.session_id}", "browser_service")
        
        # Import web_config directly - always gets updated data
        self.web_config = web_config
        
        # Core services
        self.capture_service = CaptureService(session_id, self.logger)
        
        # Session management
        self.session_timestamp = session_id
        output_dir = Path(self.web_config.get_config()["STORAGE"]["output_dir"])
        self.session_dir = output_dir / f"session_{session_id}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_histories = []
        
        # HAR recording setup
        self._initialize_har_recorders()
        
        # Browser state
        self.browser: Optional[BrowserSession] = None
        self.browser_context = None
        self.current_page = None
        self.is_initialized = False
        self._cleanup_completed = False
        self.task_results = {}
        self.global_page = None
        self._temp_profile_path = None
    
    def _initialize_har_recorders(self):
        """Initialize HAR recorders based on configuration"""
        self.har_recorder = None
        self.file_har_recorder = None
        self.global_har_path = None
        
        recording_mode = self.web_config.get_config()["RECORDING"]["har_recording_mode"]
        
        if recording_mode == "task_based":
            self.logger.info("🔧 Initializing task-based HAR recording")
            self.har_recorder = EnhancedHARRecorder(self.session_id, self.logger)
            self.file_har_recorder = FileBasedHARRecorder(self.session_id, str(self.session_dir), self.logger)
        elif recording_mode == "global_traditional":
            self.logger.info("🔧 Initializing global traditional HAR recording")
            self.global_har_path = str(self.session_dir / f"network_traffic_{self.session_timestamp}.har")
    
    def _get_profile_path(self) -> Optional[str]:
        """Get temporary browser profile path if configured"""
        browser_config = self.web_config.get_config()["BROWSER"]
        profile_name = browser_config.get("profile_name")
        
        if not profile_name:
            return None
        
        import tempfile
        from pathlib import Path
        
        # Create temporary profile directory
        temp_profile = Path(tempfile.mkdtemp(prefix=f"{profile_name}_{self.session_id}_"))
        
        self.logger.info(f"✅ Using temporary profile: {temp_profile}")
        
        # Store for cleanup later
        self._temp_profile_path = temp_profile
        
        return str(temp_profile)

    async def initialize(self):
        """Initialize the shared browser session with configurable HAR recording"""
        if self.is_initialized:
            return
        
        try:
            browser_config = self.web_config.get_config()["BROWSER"]
            recording_config = self.web_config.get_config()["RECORDING"]
            
            recording_mode = recording_config["har_recording_mode"]
            self.logger.info(f"Initializing persistent browser session with {recording_mode} HAR recording")
            
            # Get screen resolution
            screen_width, screen_height = get_screen_resolution()
            self.logger.info(f"Detected screen resolution: {screen_width}x{screen_height}")
            
            # Create downloads directory
            downloads_dir = self.session_dir / "downloads"
            downloads_dir.mkdir(parents=True, exist_ok=True)
            
            # Build browser profile using the compatibility layer
            config_builder = BrowserConfigBuilder()
            config_builder.set_headless(browser_config["headless"])
            config_builder.set_security(disable_security=True)
            config_builder.add_chrome_args([
                '--start-maximized',
                '--disable-web-security',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ])
            config_builder.set_downloads_path(str(downloads_dir))
            config_builder.set_viewport(no_viewport=True)
            config_builder.set_https_errors(ignore=True)
            config_builder.set_highlight_elements(browser_config["highlight_elements"])
            
            # Set custom profile if configured
            profile_path = self._get_profile_path()
            if profile_path:
                config_builder.set_user_data_dir(profile_path)
            
            # Add HAR recording for global traditional mode
            if recording_config["har_recording_mode"] == "global_traditional":
                self.global_har_path = str(self.session_dir / f"network_traffic_{self.session_timestamp}.har")
                config_builder.set_har_recording(self.global_har_path)
                self.logger.info(f"🌐 Global traditional HAR recording configured: {self.global_har_path}")
            
            # Add optional recording features
            if recording_config["enable_global_video_recording"]:
                video_quality = recording_config["video_recording_quality"]
                # Map quality to size (you may need to adjust these values)
                video_size = {"low": (640, 480), "medium": (1280, 720), "high": (1920, 1080)}.get(video_quality, (1280, 720))
                config_builder.set_video_recording(str(self.session_dir), video_size)
                self.logger.info(f"📹 Global video recording enabled (quality: {video_quality}, size: {video_size})")
            else:
                self.logger.info("📹 Global video recording disabled")
            
            if recording_config["enable_global_trace_recording"]:
                config_builder.set_trace_recording(str(self.session_dir))
                self.logger.info("🔍 Global trace recording enabled")
            else:
                self.logger.info("🔍 Global trace recording disabled")
            
            # Build browser profile
            browser_profile = config_builder.build()
            
            # Create BrowserSession with keep_alive=True (following browser-use best practices)
            from browser_use.browser.session import BrowserSession
            
            # Extract parameters for BrowserSession
            session_params = browser_profile.model_dump()
            session_params['keep_alive'] = True  # KEY: Keep session alive between agents
            
            self.logger.info(f"🔧 BrowserSession params: {list(session_params.keys())}")
            self.logger.info(f"🔧 keep_alive: {session_params.get('keep_alive')}")
            
            self.browser = BrowserSession(**session_params)
            
            # Start the browser session
            await self.browser.start()
            
            # Get the current page and keep it for all tasks (to maintain login state)
            self.current_page = await self.browser.get_current_page()
            self.browser_context = self.browser  # For compatibility with existing code
            
            self.logger.info(f"🔧 Shared page created for all tasks: {self.current_page}")
            
            # Start HAR recording based on mode
            await self._start_har_recording()
            
            self.is_initialized = True
            self.logger.info(f"✅ Browser session initialized with {recording_mode} HAR recording")
            
            # Log final status
            self._log_initialization_status()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize browser session: {str(e)}")
            raise
    
    async def _start_har_recording(self):
        """Start HAR recording based on configuration mode"""
        recording_config = self.web_config.get_config()["RECORDING"]
        
        if recording_config["har_recording_mode"] == "task_based":
            # Start both enhanced and file-based HAR recording
            if self.har_recorder:
                await self.har_recorder.start_global_recording(self.browser_context)
            
            if self.file_har_recorder and self.current_page:
                await self.file_har_recorder.start_global_recording(self.current_page)
                self.global_page = self.current_page  # Store reference for task recordings
            else:
                self.logger.warning("Could not get current page for file-based HAR recording")
        
        # For global traditional mode, HAR recording is handled automatically by browser-use
    
    def _log_initialization_status(self):
        """Log the final initialization status"""
        recording_config = self.web_config.get_config()["RECORDING"]
        
        if recording_config["enable_global_video_recording"]:
            video_quality = recording_config["video_recording_quality"]
            self.logger.info(f"📹 Global recording will be saved to: {self.session_dir} (quality: {video_quality})")
        if recording_config["enable_global_trace_recording"]:
            self.logger.info(f"🔍 Global trace will be saved to: {self.session_dir}")
        
        if recording_config["har_recording_mode"] == "global_traditional":
            self.logger.info(f"🌐 Global HAR recording: {self.global_har_path}")
        else:
            self.logger.info(f"🌐 Task-based HAR recording: Active")
    
    def _create_task_controller(self, task_context: TaskContext) -> Controller:
        """Create a task-specific controller with capture capabilities"""
        from browser_use import ActionResult
        
        controller = Controller()
        
        # Add capture service integration
        # controller.capture_service = self.capture_service
        # controller.task_context = task_context
        
        # 🔑 KEY: Add the missing custom action that task prompts expect
        @controller.action('Capture element information')
        async def capture_element_information(element_index: int, browser_session, capture_type: str = "element_analysis") -> ActionResult:
            """
            Capture HTML and screenshot of specified element for intelligence extraction.
            This is the custom action that task prompts reference.
            
            Args:
                element_index: Index of element to capture from selector map
                browser_session: Browser session from browser-use
                capture_type: Type of capture (channel_detection, date_navigation, etc.)
            """
            try:
                self.logger.info(f"🔍 Capturing element {element_index} for {capture_type}")
                
                # Use the capture service to do the actual work
                capture_data = await self.capture_service.capture_element(
                    browser_context=browser_session,
                    element_index=element_index,
                    capture_type=capture_type,
                    output_dir=task_context.task_dir
                )
                
                success_msg = f"✅ Captured {capture_type} element {element_index}"
                self.logger.info(success_msg)
                return ActionResult(
                    extracted_content=success_msg,
                    include_in_memory=False
                )
                
            except Exception as e:
                error_msg = f"❌ Failed to capture {capture_type} element {element_index}: {str(e)}"
                self.logger.error(error_msg)
                return ActionResult(error=error_msg)
        
        return controller
    
    async def execute_task(
        self, 
        task_context: TaskContext,
        task_prompt: str,
        time_limit_seconds: int
    ) -> TaskResult:
        """Execute a single task using persistent browser session with configurable HAR recording"""
        
        if not self.is_initialized:
            await self.initialize()
        
        start_time = datetime.now()
        task_id = task_context.task_dir.name
        
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            start_time=start_time,
            outputs={'task_dir': task_context.task_dir}
        )
        
        try:
            self.logger.info(f"🚀 Starting task execution: {task_id}")
            
            # Start task-specific HAR recording
            await self._start_task_har_recording(task_id, task_context)
            
            # Create controller with capture capabilities
            controller = self._create_task_controller(task_context)
            
            # Create task-specific agent wrapper
            agent_wrapper = BrowserAgentWrapper(
                task_name=task_id,
                task_dir=task_context.task_dir,
                task=task_prompt,
                browser=self.browser,
                page=self.current_page,
                controller=controller,
                logger=self.logger
            )
            
            # Execute task with timeout and comprehensive recording
            history = await agent_wrapper.run_with_recording(
                max_steps=30,
                timeout_seconds=time_limit_seconds
            )
            
            # Store history for session GIF if needed
            recording_config = self.web_config.get_config()["RECORDING"]
            if recording_config["gif_recording_mode"] == "session":
                self.session_histories.append(history)
            
            # Stop task-specific HAR recording
            task_har_path = await self._stop_task_har_recording(task_id, task_context)
            
            # Save consolidated history
            history_path = task_context.task_dir / f"history_{task_id}.json"
            agent_wrapper.save_history(str(history_path))
            
            # Update task result
            task_result.status = TaskStatus.SUCCESS
            task_result.end_time = datetime.now()
            
            # Extract and save cookies after task completion (especially important for login tasks)
            cookies_path = await self._extract_and_save_cookies(task_id, task_context)
            
            # Record all generated files
            task_result.outputs.update({
                'conversation_directory': task_context.task_dir / "conversation.json",
                'consolidated_history': history_path,
                'task_metadata.json': task_context.task_dir / "task_metadata.json",
                'browser_trace': task_context.task_dir / f"{task_id}_trace.zip",
                'gif_recording': task_context.task_dir / f"{task_id}_recording.gif",
                'cookies_file': cookies_path
            })
            
            # Add HAR files only if task-based recording is enabled
            recording_config = self.web_config.get_config()["RECORDING"]
            if recording_config["har_recording_mode"] == "task_based" and task_har_path:
                task_result.outputs['network_har'] = task_har_path
            
            # Store task result for session summary
            self.task_results[task_id] = {
                'success': True,
                'timestamp': start_time.isoformat(),
                'directory': task_context.task_dir,
                'har_file': task_har_path if task_har_path else 'Not created'
            }
            
            self.logger.info(f"✅ Task completed successfully: {task_id}")
            return task_result
            
        except Exception as e:
            # Update task result with error
            task_result.status = TaskStatus.FAILED
            task_result.end_time = datetime.now()
            task_result.error = str(e)
            
            # Store failed task result
            self.task_results[task_id] = {
                'success': False,
                'timestamp': start_time.isoformat(),
                'directory': task_context.task_dir,
                'error': str(e),
                'har_file': 'Not created due to error'
            }
            
            self.logger.error(f"❌ Task failed: {task_id} - {e}")
            raise
    
    def _get_gif_path(self, task_id: str, task_context: TaskContext) -> Optional[str]:
        """Get GIF path based on recording mode"""
        recording_config = self.web_config.get_config()["RECORDING"]
        
        if recording_config["gif_recording_mode"] == "session":
            # For session mode, we'll create GIF after all tasks complete
            return None  # Don't generate individual GIFs
        else:
            # Individual task GIFs (current behavior)
            return str(task_context.task_dir / f"{task_id}_recording.gif")
    
    def _combine_histories(self, histories: list) -> 'AgentHistoryList':
        """Combine multiple AgentHistoryList objects into one"""
        try:
            from browser_use.agent.views import AgentHistoryList
            
            combined_history_items = []
            for history in histories:
                if hasattr(history, 'history') and history.history:
                    combined_history_items.extend(history.history)
            
            if not combined_history_items:
                self.logger.warning("No history items found to combine")
                return None
            
            # Create new combined history
            return AgentHistoryList(history=combined_history_items)
            
        except Exception as e:
            self.logger.error(f"Failed to combine histories: {e}")
            return None
    
    async def create_session_gif(self):
        """Create single GIF from all task histories with improved styling"""
        recording_config = self.web_config.get_config()["RECORDING"]
        
        if recording_config["gif_recording_mode"] != "session" or not self.session_histories:
            return
        
        try:
            # Combine all histories
            combined_history = self._combine_histories(self.session_histories)
            if not combined_history:
                self.logger.warning("No combined history available for session GIF")
                return
            
            # Create session-wide GIF with improved styling
            from browser_use.agent.gif import create_history_gif
            session_gif_path = str(self.session_dir / "session_recording.gif")
            
            create_history_gif(
                task="🎭 TV Schedule Analysis - Complete Session",  # Emoji for visual appeal
                history=combined_history,
                output_path=session_gif_path,
                
                # Timing optimizations
                duration=1500,  # Faster transitions (1.5s vs 3s default)
                
                # Visual improvements
                show_goals=True,     # Show step goals for understanding
                show_task=True,      # Show initial task frame
                show_logo=False,     # Skip logo to reduce clutter
                
                # Font sizing for better readability
                font_size=36,        # Slightly smaller regular text
                title_font_size=48,  # Smaller step numbers
                goal_font_size=40,   # Smaller goal text
                
                # Layout improvements
                margin=50,           # More margin from edges
                line_spacing=1.3     # Tighter line spacing
            )
            
            self.logger.info(f"📹 Session GIF created: {session_gif_path}")
            
        except Exception as e:
            self.logger.error(f"❌ Session GIF creation failed: {e}")

    async def _start_task_har_recording(self, task_id: str, task_context: TaskContext):
        """Start task-specific HAR recording based on mode"""
        recording_config = self.web_config.get_config()["RECORDING"]
        
        if recording_config["har_recording_mode"] == "task_based":
            # Start both enhanced and file-based task HAR recording
            if self.har_recorder:
                await self.har_recorder.start_task_recording(task_id)
            
            if self.file_har_recorder and self.global_page:
                await self.file_har_recorder.start_task_recording(task_id, task_context.task_dir, self.global_page)
        
        # For global traditional mode, no task-specific recording needed
    
    async def _extract_and_save_cookies(self, task_id: str, task_context: TaskContext) -> Optional[str]:
        """Extract and save raw cookies + full storage state"""
        try:
            if not self.browser or not self.is_initialized:
                return None
            
            cookies = await self.browser.get_cookies()
            if not cookies:
                return None
            
            # Save raw cookies (exact format from browser)
            cookies_file = task_context.task_dir / f"{task_id}_cookies.json"
            # Use proper naming for storage state to get full format (cookies + localStorage + sessionStorage)
            storage_state_file = task_context.task_dir / "storage_state.json"
            
            success_count = 0
            
            # 1. Save raw cookies
            try:
                with open(cookies_file, 'w') as f:
                    import json
                    json.dump(cookies, f, indent=2)
                success_count += 1
            except Exception as e:
                self.logger.error(f"Failed to save cookies: {e}")
            
            # 2. Save full storage state
            try:
                if hasattr(self.browser, 'save_storage_state'):
                    await self.browser.save_storage_state(storage_state_file)  # Pass Path object directly
                    success_count += 1
            except Exception as e:
                self.logger.warning(f"Storage state save failed: {e}")
            
            # Log results
            auth_cookies = [c for c in cookies if any(auth in c.get('name', '').lower() 
                           for auth in ['login', 'auth', 'token', 'session'])]
            
            self.logger.info(f"🍪 {task_id}: {len(cookies)} cookies, {len(auth_cookies)} auth, {success_count}/2 files saved")
            
            return str(cookies_file) if success_count > 0 else None
                
        except Exception as e:
            self.logger.error(f"Cookie extraction failed for {task_id}: {e}")
            return None
    
    async def load_session_data(self, session_dir: Path, task_id: str = "task_0_login_authentication") -> bool:
        """Load session data - try storage state first, fallback to raw cookies"""
        if not self.browser or not self.is_initialized:
            return False
        
        # Look for storage state file (proper format with localStorage + sessionStorage)
        storage_state_file = session_dir / task_id / "storage_state.json"
        cookies_file = session_dir / task_id / f"{task_id}_cookies.json"
        
        # Try storage state first (includes cookies + localStorage + sessionStorage)
        if storage_state_file.exists():
            try:
                # Browser-use expects the storage state file to be configured in the profile
                # We need to temporarily set it and then call load_storage_state()
                if hasattr(self.browser, 'browser_profile') and hasattr(self.browser, 'load_storage_state'):
                    # Store original storage state setting
                    original_storage_state = getattr(self.browser.browser_profile, 'storage_state', None)
                    
                    # Set the storage state file path
                    self.browser.browser_profile.storage_state = storage_state_file
                    
                    # Load the storage state (no parameters)
                    await self.browser.load_storage_state()
                    
                    # Restore original setting
                    self.browser.browser_profile.storage_state = original_storage_state
                    
                    self.logger.info(f"🍪 Storage state loaded successfully from {storage_state_file}")
                    return True
                    
            except Exception as e:
                self.logger.warning(f"Storage state loading failed: {e}")
        
        # Fallback to raw cookies only
        if cookies_file.exists():
            try:
                import json
                with open(cookies_file, 'r') as f:
                    cookies = json.load(f)
                
                if hasattr(self.browser, 'context') and self.browser.context:
                    await self.browser.context.add_cookies(cookies)
                    self.logger.info(f"🍪 {len(cookies)} cookies loaded (storage data may be missing)")
                    return True
            except Exception as e:
                self.logger.error(f"Cookie loading failed: {e}")
        
        self.logger.warning("No session data found to load")
        return False

    async def _stop_task_har_recording(self, task_id: str, task_context: TaskContext) -> Optional[str]:
        """Stop task-specific HAR recording and return HAR file path"""
        task_har_path = None
        recording_config = self.web_config.get_config()["RECORDING"]
        
        if recording_config["har_recording_mode"] == "task_based":
            if self.har_recorder:
                task_har_path = await self.har_recorder.stop_task_recording(task_id, task_context.task_dir)
            
            if self.file_har_recorder:
                file_har_path = await self.file_har_recorder.stop_task_recording(task_id, task_context.task_dir)
                # Use file HAR path if enhanced HAR path is not available
                if not task_har_path:
                    task_har_path = file_har_path
        
        return task_har_path
    
    async def save_global_har_now(self):
        """Save global HAR immediately after intelligence gathering without closing browser"""
        recording_config = self.web_config.get_config()["RECORDING"]
        
        try:
            if recording_config["har_recording_mode"] == "task_based":
                self.logger.info("🌐 Saving task-based HAR after intelligence gathering phase...")
                
                # Stop global HAR recording and save comprehensive HAR
                har_summary = {}
                if self.har_recorder:
                    await self.har_recorder.stop_global_recording()
                    har_summary = await self.har_recorder.save_comprehensive_session_har(self.session_dir)
                
                # Save file-based global HAR
                if self.file_har_recorder:
                    await self.file_har_recorder.stop_global_recording()
                
                # Print HAR statistics
                if self.har_recorder:
                    har_stats = self.har_recorder.get_recording_stats()
                    self.logger.info(f"✅ Task-based HAR saved successfully!")
                    self.logger.info(f"🌐 Total network requests captured: {har_stats['total_requests']}")
                    self.logger.info(f"📋 Task-specific HARs created: {har_stats['active_tasks']}")
                    self.logger.info(f"⏱️ Recording duration: {har_stats['recording_duration']:.2f}s")
                
                return har_summary
                
            elif recording_config["har_recording_mode"] == "global_traditional":
                self.logger.info("🌐 Global traditional HAR recording - file will be saved automatically on browser close")
                return {
                    'session_id': self.session_id,
                    'timestamp': self.session_timestamp,
                    'recording_mode': 'global_traditional',
                    'har_file_path': self.global_har_path,
                    'message': 'HAR file will be created automatically by browser-use'
                }
            
            else:
                self.logger.warning("Unknown HAR recording mode")
                return {}
            
        except Exception as e:
            self.logger.error(f"❌ Error saving global HAR: {e}")
            return {}
    
    async def save_session_summary(self):
        """Save comprehensive session summary with configurable HAR recording"""
        recording_config = self.web_config.get_config()["RECORDING"]
        
        try:
            # Handle HAR saving based on recording mode
            har_summary = {}
            
            if recording_config["har_recording_mode"] == "task_based":
                # If HAR hasn't been saved yet, save it now
                if self.har_recorder and self.har_recorder.is_recording:
                    har_summary = await self.save_global_har_now()
                else:
                    # HAR already saved, just get the summary
                    har_summary = {}
            elif recording_config["har_recording_mode"] == "global_traditional":
                # For global traditional mode, just create a summary
                har_summary = {
                    'recording_mode': 'global_traditional',
                    'har_file_path': self.global_har_path,
                    'message': 'HAR file created automatically by browser-use'
                }
            
            # Create session summary using common utilities
            session_summary = create_session_metadata(
                session_id=self.session_id,
                timestamp=self.session_timestamp,
                session_duration=datetime.now().isoformat(),
                tasks_completed=len(self.task_results),
                har_recording_mode=recording_config["har_recording_mode"],
                har_recording_summary=har_summary,
                tasks_summary={
                    task_name: {
                        'success': result['success'],
                        'timestamp': result['timestamp'],
                        'directory': str(result['directory']),
                        'har_file': str(result.get('har_file', 'Not created'))
                    }
                    for task_name, result in self.task_results.items()
                }
            )
            
            summary_path = self.session_dir / f"session_summary_{self.session_timestamp}.json"
            if save_json_file(session_summary, summary_path):
                self.logger.info(f"📊 Enhanced session summary saved: {summary_path}")
            else:
                self.logger.error(f"❌ Failed to save session summary: {summary_path}")
            
        except Exception as e:
            self.logger.error(f"❌ Error saving enhanced session summary: {e}")
    
    async def close(self):
        """Close browser session after all tasks complete with configurable HAR recording"""
        if self._cleanup_completed:
            self.logger.debug("Browser cleanup already completed, skipping")
            return
            
        if self.browser and self.is_initialized:
            try:
                self.logger.info("🧹 Cleaning up browser session...")
                
                # Save session summary (HAR may already be saved)
                await self.save_session_summary()
                
                # Close browser session properly (following browser-use example)
                if hasattr(self.browser, 'kill'):
                    await self.browser.kill()
                    self.logger.info("🧹 Browser session killed")
                elif hasattr(self.browser, 'stop'):
                    await self.browser.stop()
                    self.logger.info("🧹 Browser session stopped")
                elif hasattr(self.browser, 'close'):
                    await self.browser.close()
                    self.logger.info("🧹 Browser closed")
                
                self.browser = None
                self.browser_context = None
                self.is_initialized = False
                
                # Clean up temporary profile if created
                self._cleanup_temp_profile()
                
                # Print final statistics
                self._print_final_statistics()
                
            except Exception as e:
                # Suppress common cleanup errors that happen after successful completion
                if any(error_type in str(e).lower() for error_type in ['keyerror', 'targetclosederror', 'browser has been closed']):
                    self.logger.debug(f"Suppressed non-critical cleanup error: {str(e)}")
                else:
                    self.logger.error(f"Error closing browser session: {str(e)}")
            finally:
                self._cleanup_completed = True
        else:
            self.logger.debug("Browser session was not initialized or already closed")
            self._cleanup_completed = True
    
    def _cleanup_temp_profile(self):
        """Clean up temporary profile directory"""
        if self._temp_profile_path and self._temp_profile_path.exists():
            try:
                import shutil
                self.logger.info(f"🧹 Cleaning up temporary profile: {self._temp_profile_path}")
                shutil.rmtree(self._temp_profile_path)
                self.logger.info("✅ Temporary profile cleaned up")
            except Exception as e:
                self.logger.warning(f"⚠️ Failed to cleanup temporary profile: {e}")
            finally:
                self._temp_profile_path = None
    
    def _print_final_statistics(self):
        """Print final statistics based on recording mode"""
        recording_config = self.web_config.get_config()["RECORDING"]
        
        if recording_config["har_recording_mode"] == "task_based":
            # Print task-based HAR statistics
            if self.har_recorder and self.file_har_recorder:
                har_stats = self.har_recorder.get_recording_stats()
                file_har_stats = self.file_har_recorder.get_recording_stats()
                
                self.logger.info("✅ Browser session closed successfully")
                if recording_config["enable_global_video_recording"]:
                    self.logger.info(f"📹 Global recording: {self.session_dir}")
                if recording_config["enable_global_trace_recording"]:
                    self.logger.info(f"🔍 Global trace: {self.session_dir}")
                self.logger.info(f"🌐 Enhanced HAR requests captured: {har_stats['total_requests']}")
                self.logger.info(f"📋 Task-specific HARs: {har_stats['active_tasks']}")
                self.logger.info(f"📁 File-based HAR requests captured: {file_har_stats['global_recording']['total_requests']}")
        
        elif recording_config["har_recording_mode"] == "global_traditional":
            # Print global traditional HAR statistics
            self.logger.info("✅ Browser session closed successfully")
            if recording_config["enable_global_video_recording"]:
                self.logger.info(f"📹 Global recording: {self.session_dir}")
            if recording_config["enable_global_trace_recording"]:
                self.logger.info(f"🔍 Global trace: {self.session_dir}")
            self.logger.info(f"🌐 Global traditional HAR file: {self.global_har_path}")
            
            # Check if HAR file was created
            if Path(self.global_har_path).exists():
                har_size = Path(self.global_har_path).stat().st_size
                self.logger.info(f"📄 HAR file size: {har_size} bytes")
            else:
                self.logger.warning(f"⚠️ HAR file not found: {self.global_har_path}")
    
    def print_session_summary(self):
        """Print comprehensive summary of all completed tasks with configurable HAR recording info"""
        recording_config = self.web_config.get_config()["RECORDING"]
        
        self.logger.info("="*80)
        recording_mode = "TASK-BASED" if recording_config["har_recording_mode"] == "task_based" else "GLOBAL TRADITIONAL"
        self.logger.info(f"COMPREHENSIVE TASK EXECUTION SUMMARY WITH {recording_mode} HAR RECORDING")
        self.logger.info("="*80)
        
        self.logger.info(f"Session ID: {self.session_id}")
        self.logger.info(f"Session timestamp: {self.session_timestamp}")
        self.logger.info(f"HAR Recording Mode: {recording_config['har_recording_mode']}")
        self.logger.info(f"Browser-use Version: 0.5.5")
        
        # HAR recording statistics based on mode
        if recording_config["har_recording_mode"] == "task_based":
            if self.har_recorder and self.file_har_recorder:
                har_stats = self.har_recorder.get_recording_stats()
                file_har_stats = self.file_har_recorder.get_recording_stats()
                
                self.logger.info(f"Task-Based HAR Recording Statistics:")
                self.logger.info(f"   🌐 Enhanced HAR total requests: {har_stats['total_requests']}")
                self.logger.info(f"   📋 Enhanced HAR task recordings: {har_stats['active_tasks']}")
                self.logger.info(f"   ⏱️ Enhanced HAR recording duration: {har_stats['recording_duration']:.2f}s")
                self.logger.info(f"   📁 File-based HAR global requests: {file_har_stats['global_recording']['total_requests']}")
                self.logger.info(f"   🗂️ File-based HAR task requests: {file_har_stats['task_recording']['total_requests']}")
        
        elif recording_config["har_recording_mode"] == "global_traditional":
            self.logger.info(f"Global Traditional HAR Recording Statistics:")
            self.logger.info(f"   🌐 Global HAR file: {self.global_har_path}")
            
            # Check if HAR file exists and get size
            if Path(self.global_har_path).exists():
                har_size = Path(self.global_har_path).stat().st_size
                self.logger.info(f"   📄 HAR file size: {har_size} bytes")
            else:
                self.logger.info(f"   ⚠️ HAR file not found")
        
        self.logger.info("INDIVIDUAL TASK RESULTS:")
        for task_name, result in self.task_results.items():
            status = "SUCCESS" if result['success'] else "FAILED"
            har_file = result.get('har_file', 'Not created')
            self.logger.info(f"{status} {task_name}")
            self.logger.info(f"   📁 Directory: {result['directory']}")
            if recording_config["har_recording_mode"] == "task_based":
                self.logger.info(f"   🌐 HAR file: {har_file}")
            self.logger.info(f"   ⏰ Timestamp: {result['timestamp']}")
        
        # Summary statistics
        successful = sum(1 for result in self.task_results.values() if result['success'])
        self.logger.info("SUMMARY:")
        self.logger.info(f"   Total tasks: {len(self.task_results)}")
        self.logger.info(f"   Successful: {successful}")
        self.logger.info(f"   Failed: {len(self.task_results) - successful}")
        
        if recording_config["har_recording_mode"] == "task_based":
            self.logger.info(f"   HAR files created: {len([r for r in self.task_results.values() if r.get('har_file')])}")
        elif recording_config["har_recording_mode"] == "global_traditional":
            self.logger.info(f"   Global HAR file: {self.global_har_path}")
        
        self.logger.info("="*80)
