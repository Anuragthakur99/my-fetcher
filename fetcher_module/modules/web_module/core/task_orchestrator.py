"""Task Orchestrator - Main coordinator for TV schedule analysis workflow"""

import asyncio
import glob
import json
import tempfile
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..models.task_models import TaskDefinition, TaskContext, TaskResult, TaskStatus, TaskType
from ..models.result_models import AnalysisSession
from ..services.browser_service import BrowserService
from ..services.intelligence_extractor import IntelligenceExtractor
from ..config.web_config import web_config

class TaskOrchestrator:
    """Main coordinator for task-based TV schedule analysis"""
    
    def __init__(self, login_credentials: Optional[Dict[str, str]] = None, logger=None):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        # Use provided logger or create default
        if logger:
            self.logger = logger
        else:
            from common.logger import StructuredLogger
            self.logger = StructuredLogger("web", f"session_{self.session_id}", "task_orchestrator")
        
        # Import web_config directly - always gets updated data
        self.web_config = web_config
        # Create session directory in web module output
        output_dir = Path(self.web_config.get_config()["STORAGE"]["output_dir"])
        self.session_dir = output_dir / f"session_{self.session_id}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize services
        self.browser_service = BrowserService(self.session_id, self.logger)
        self.intelligence_extractor = IntelligenceExtractor(self.session_id, self.logger)
        
        # Session tracking
        self.analysis_session = None
        self.task_results: Dict[str, TaskResult] = {}
        self.accumulated_intelligence: Dict[str, Any] = {}
        self.accumulated_code: str = ""
        self.login_credentials: Optional[Dict[str, str]] = login_credentials
    
    async def run_full_analysis(
        self, 
        target_url: str, 
        channel_name: str,
        login_credentials: Optional[Dict[str, str]] = None
    ) -> AnalysisSession:
        """
        Run complete TV schedule analysis workflow
        
        Args:
            target_url: Target TV schedule website URL
            channel_name: Target channel name to analyze
            login_credentials: Optional dict with 'username' and 'password' keys
            
        Returns:
            AnalysisSession: Complete analysis results
        """
        
        start_time = datetime.now()
        self.logger.info(f"Starting full TV schedule analysis")
        self.logger.info(f"Target URL: {target_url}")
        self.logger.info(f"Channel: {channel_name}")
        self.logger.info(f"Session ID: {self.session_id}")
        
        # Initialize analysis session
        self.analysis_session = AnalysisSession(
            session_id=self.session_id,
            target_url=target_url,
            channel_name=channel_name,
            start_time=start_time
        )
        
        # Store login credentials for tasks
        self.login_credentials = login_credentials
        
        try:
            # Initialize browser service
            await self.browser_service.initialize()
            
            # Get task definitions in execution order (only intelligence gathering tasks)
            task_definitions = self._get_intelligence_task_definitions()
            
            # PHASE 1: Execute all intelligence gathering tasks (including optional login)
            self.logger.info("🧠 PHASE 1: Intelligence Gathering - Executing all tasks")
            if self.login_credentials:
                self.logger.info("🔐 Login credentials provided - authentication will be performed first")
            
            for task_def in task_definitions:
                self.logger.info(f"Executing intelligence task: {task_def.task_id}")
                
                # Execute individual task
                task_result = await self._execute_single_task(
                    task_definition=task_def,
                    target_url=target_url,
                    channel_name=channel_name
                )
                
                # Store task result
                self.task_results[task_def.task_id] = task_result
                self.analysis_session.task_results.append(task_result)
                
                # Extract intelligence from task result (with HTML + screenshot)
                if task_result.is_successful:
                    await self._extract_and_accumulate_intelligence(task_result, target_url, channel_name)
                else:
                    self.logger.warning(f"Task {task_def.task_id} failed, continuing with next task")
            
            # 🆕 NEW: Save global HAR immediately after intelligence gathering
            self.logger.info("🌐 PHASE 1 COMPLETE: Saving global HAR after intelligence gathering")
            har_summary = await self.browser_service.save_global_har_now()
            
            # Store HAR summary in analysis session
            if hasattr(self.analysis_session, 'har_summary'):
                self.analysis_session.har_summary = har_summary
            
            self.logger.info("✅ Global HAR saved successfully - Intelligence phase complete!")
            
            # Create session GIF if configured (after all browser interactions)
            if hasattr(self.browser_service, 'create_session_gif'):
                await self.browser_service.create_session_gif()
            
            # PHASE 2: Code Generation
            # Option 1: Original Conversational Code Generation (3 steps) - COMMENTED OUT
            # self.logger.info("🤖 PHASE 2: Conversational Code Generation - 3 Steps")
            # await self._execute_conversational_code_generation(target_url, channel_name)
            
            # Option 2: NEW Iterative Step-by-Step Code Generation & Testing
            self.logger.info("🤖 PHASE 2: Iterative Step-by-Step Code Generation & Testing")
            await self._execute_iterative_code_generation(target_url, channel_name)
            
            # Finalize analysis session
            self.analysis_session.end_time = datetime.now()
            
            # Save session summary
            await self._save_session_summary()
            
            self.logger.info(f"Full analysis completed in {self.analysis_session.duration_seconds:.2f} seconds")
            self.logger.info(f"Successful tasks: {len(self.analysis_session.successful_tasks)}")
            self.logger.info(f"Failed tasks: {len(self.analysis_session.failed_tasks)}")
            
            return self.analysis_session
            
        except Exception as e:
            self.logger.error(f"Full analysis failed: {str(e)}")
            self.analysis_session.end_time = datetime.now()
            raise
        
        finally:
            # Clean up browser service
            await self.browser_service.close()
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.browser_service.close()
    
    def _get_intelligence_task_definitions(self) -> List[TaskDefinition]:
        """Get task definitions for intelligence gathering (including optional login)"""
        from ..models.task_models import TaskType
        
        task_definitions = []
        
        # Add login task if credentials are provided
        if self.login_credentials:
            task_definitions.append(
                TaskDefinition(
                    task_id="task_0_login_authentication",
                    name="Login Authentication Intelligence",
                    task_type=TaskType.LOGIN_AUTHENTICATION,
                    description="Authenticate with website and extract login patterns",
                    prompt_template="",  # Will be loaded from file
                    time_limit_seconds=500,
                    expected_outputs=["login_patterns", "authentication_selectors"],
                    dependencies=[]
                )
            )
        
        # Add main intelligence gathering tasks
        task_definitions.extend([
            TaskDefinition(
                task_id="task_1_channel_detection",
                name="Channel Detection Intelligence",
                task_type=TaskType.INTELLIGENCE_EXTRACTION,
                description="Navigate to target channel and extract navigation patterns",
                prompt_template="",  # Will be loaded from file
                time_limit_seconds=1000,
                expected_outputs=["navigation_patterns", "channel_selectors"],
                dependencies=["task_0_login_authentication"] if self.login_credentials else []
            ),
            TaskDefinition(
                task_id="task_2_date_navigation", 
                name="Date Navigation Intelligence",
                task_type=TaskType.INTELLIGENCE_EXTRACTION,
                description="Navigate through dates and extract date navigation patterns",
                prompt_template="",  # Will be loaded from file
                time_limit_seconds=1000,
                expected_outputs=["date_patterns", "navigation_selectors"],
                dependencies=["task_1_channel_detection"]
            ),
            TaskDefinition(
                task_id="task_3_program_extraction",
                name="Program Extraction Intelligence", 
                task_type=TaskType.INTELLIGENCE_EXTRACTION,
                description="Extract program data and detail access patterns",
                prompt_template="",  # Will be loaded from file
                time_limit_seconds=1000,
                expected_outputs=["program_patterns", "extraction_selectors"],
                dependencies=["task_2_date_navigation"]
            )
        ])
        
        return task_definitions
    
    # ==================== NEW ITERATIVE CODE GENERATION ====================
    
    async def _execute_iterative_code_generation(self, target_url: str, channel_name: str) -> None:
        """Execute iterative step-by-step code generation with testing using existing SmartCodeGenerator"""
        try:
            self.logger.info("Starting iterative step-by-step code generation...")
            
            # Import existing code generator (reuse existing infrastructure)
            from ..services.code_generator import SmartCodeGenerator
            
            # Initialize code generator (reuse existing)
            code_generator = SmartCodeGenerator(self.session_id, self.logger)
            
            # Step 1: Generate and Test Login (if needed)
            if 'task_0_login_authentication' in self.accumulated_intelligence:
                self.logger.info("🔐 Step 1: Generate and Test Login Methods")
                login_success = await self._generate_and_test_step(
                    code_generator, 0, "task_0_login_authentication", target_url, channel_name, "login"
                )
                if not login_success:
                    self.logger.warning("Step 1 (Login) failed - continuing with next steps")
            
            # Step 2: Generate and Test Channel Navigation
            self.logger.info("📺 Step 2: Generate and Test Channel Navigation")
            channel_success = await self._generate_and_test_step(
                code_generator, 1, "task_1_channel_detection", target_url, channel_name, "channel"
            )
            if not channel_success:
                self.logger.warning("Step 2 (Channel) failed - continuing with next steps")
            
            # Step 3: Generate and Test Date Navigation
            self.logger.info("📅 Step 3: Generate and Test Date Navigation")
            date_success = await self._generate_and_test_step(
                code_generator, 2, "task_2_date_navigation", target_url, channel_name, "date"
            )
            if not date_success:
                self.logger.warning("Step 3 (Date) failed - continuing with next steps")
            
            # Step 4: Generate and Test Program Collection
            self.logger.info("🎬 Step 4: Generate and Test Program Collection")
            program_success = await self._generate_and_test_step(
                code_generator, 3, "task_3_program_extraction", target_url, channel_name, "program"
            )
            if not program_success:
                self.logger.warning("Step 4 (Program) failed - continuing")
            
            # Generate final complete scraper (reuse existing method)
            self.logger.info("🚀 Step 5: Generate Final Complete Scraper")
            final_scraper_code = await self._generate_final_scraper_iterative(
                code_generator, target_url, channel_name
            )
            
            # Store the final scraper code (maintain compatibility)
            self.accumulated_code = final_scraper_code
            
            # Save final scraper (reuse existing method)
            await self._save_final_scraper(target_url, channel_name)
            
            self.logger.info("✅ Iterative code generation completed successfully!")
            
        except Exception as e:
            self.logger.error(f"Iterative code generation failed: {e}")
            raise
    
    async def _generate_and_test_step(
        self, 
        code_generator: 'SmartCodeGenerator', 
        step_number: int, 
        task_id: str, 
        target_url: str, 
        channel_name: str,
        step_type: str
    ) -> bool:
        """Generate code for a step and test it using existing infrastructure"""
        try:
            # Get task result and intelligence (reuse existing logic)
            task_result = self.task_results.get(task_id)
            if not task_result or not task_result.is_successful:
                self.logger.warning(f"No successful result for {task_id}, skipping step {step_number}")
                return False
            
            task_intelligence = self.accumulated_intelligence.get(task_id, {})
            
            # Get HTML content and screenshot (reuse existing method)
            html_content, screenshot_path = self._extract_html_and_screenshot(task_result)
            
            # Generate code using existing conversational approach but with iterative prompts
            generated_code = await self._generate_iterative_step_code(
                code_generator=code_generator,
                step_number=step_number,
                task_id=task_id,
                intelligence=task_intelligence,
                html_content=html_content,
                screenshot_path=screenshot_path,
                target_url=target_url,
                channel_name=channel_name,
                step_type=step_type
            )
            
            if not generated_code:
                self.logger.error(f"Failed to generate code for step {step_number}")
                return False
            
            # Test the generated code
            test_success = await self._test_generated_step(
                generated_code, step_type, target_url, channel_name
            )
            
            if test_success:
                # Add AI response to conversation history (same as conversational approach)
                code_generator.add_ai_response(generated_code)
                self.logger.info(f"✅ Step {step_number} ({step_type}) working correctly")
                return True
            else:
                self.logger.error(f"❌ Step {step_number} ({step_type}) test failed")
                # TODO: Implement fix loop here using existing infrastructure
                return False
                
        except Exception as e:
            self.logger.error(f"Step {step_number} generation/testing failed: {e}")
            return False
    
    async def _generate_iterative_step_code(
        self,
        code_generator: 'SmartCodeGenerator',
        step_number: int,
        task_id: str,
        intelligence: Dict[str, Any],
        html_content: Optional[str],
        screenshot_path: Optional[str],
        target_url: str,
        channel_name: str,
        step_type: str
    ) -> Optional[str]:
        """Generate code for iterative step using conversation messages like conversational approach"""
        
        self.logger.info(f"Generating iterative step {step_number} ({step_type}) code")
        
        try:
            # Initialize conversation if not already done
            if not hasattr(code_generator, 'conversation_messages') or not code_generator.conversation_messages:
                self._initialize_iterative_conversation(code_generator)
            
            # Load iterative step-specific prompt
            prompt_template = self._load_iterative_step_prompt(step_number, step_type)
            if not prompt_template:
                self.logger.error(f"Failed to load iterative prompt for step {step_number}")
                return None
            
            # Prepare context data (reuse existing format)
            context_data = {
                "step_number": step_number,
                "task_id": task_id,
                "target_url": target_url,
                "channel_name": channel_name,
                "website_name": self._extract_website_name(target_url),
                "current_task_intelligence": json.dumps(intelligence, indent=2),
                "html_content": html_content or "No HTML content available",
                "class_name": self._generate_class_name(channel_name),
                "step_type": step_type
            }
            
            # Format the prompt with context
            formatted_prompt = prompt_template.format(**context_data)
            
            # Create message with screenshot if available (same as conversational)
            if screenshot_path and Path(screenshot_path).exists():
                human_message = code_generator._create_human_message_with_screenshot(formatted_prompt, screenshot_path)
            else:
                from langchain_core.messages import HumanMessage
                human_message = HumanMessage(content=formatted_prompt)
            
            # Add human message to conversation history (same as conversational approach)
            code_generator.conversation_messages.append(human_message)
            
            # Generate response using full conversation history (same as conversational)
            self.logger.info(f"🤖 Generating step {step_number} ({step_type}) code with conversation context...")
            generated_code = code_generator.llm_service.stream_response(
                messages=code_generator.conversation_messages,  # Use full conversation history
                print_response=True
            )
            
            # Clean and validate the generated code (reuse existing method)
            cleaned_code = code_generator._clean_generated_code(generated_code)
            
            self.logger.info(f"✅ Step {step_number} ({step_type}) code generation completed")
            return cleaned_code
            
        except Exception as e:
            self.logger.error(f"Failed to generate iterative step {step_number}: {e}")
            return None
    
    def _initialize_iterative_conversation(self, code_generator: 'SmartCodeGenerator'):
        """Initialize conversation with iterative system prompt"""
        try:
            # Load iterative system prompt
            prompts_dir = Path(self.web_config.get_prompts_dir()) / 'code_generation'
            system_prompt_file = prompts_dir / "iterative_system_prompt.txt"
            
            if system_prompt_file.exists():
                system_prompt = system_prompt_file.read_text(encoding='utf-8')
            else:
                # Fallback system prompt
                system_prompt = """You are a Senior Python Developer building a production-ready TV schedule scraper through an iterative step-by-step process. 
                Generate clean, production-ready code based on intelligence data. Build upon previous steps in our conversation."""
            
            from langchain_core.messages import SystemMessage
            code_generator.conversation_messages = [SystemMessage(content=system_prompt)]
            self.logger.info("Initialized iterative conversation with system prompt")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize iterative conversation: {e}")
            # Fallback
            from langchain_core.messages import SystemMessage
            fallback_prompt = "You are a Senior Python Developer building TV schedule scrapers step by step. Build upon previous conversation."
            code_generator.conversation_messages = [SystemMessage(content=fallback_prompt)]
    
    def _load_iterative_step_prompt(self, step_number: int, step_type: str) -> Optional[str]:
        """Load iterative step-specific code generation prompt"""
        prompts_dir = Path(self.web_config.get_prompts_dir()) / 'code_generation'
        
        # Map step types to prompt files
        prompt_files = {
            "login": f"iterative_step_{step_number}_login.txt",
            "channel": f"iterative_step_{step_number}_channel.txt", 
            "date": f"iterative_step_{step_number}_date.txt",
            "program": f"iterative_step_{step_number}_program.txt"
        }
        
        prompt_file = prompts_dir / prompt_files.get(step_type, f"iterative_step_{step_number}_{step_type}.txt")
        
        try:
            if prompt_file.exists():
                return prompt_file.read_text(encoding='utf-8')
            else:
                self.logger.warning(f"Iterative prompt file not found: {prompt_file}")
                # Fallback to conversational prompt if iterative not available
                return self._load_conversational_step_prompt_fallback(step_number)
        except Exception as e:
            self.logger.error(f"Error loading iterative prompt: {e}")
            return None
    
    def _load_conversational_step_prompt_fallback(self, step_number: int) -> Optional[str]:
        """Fallback to existing conversational prompts"""
        prompts_dir = Path(self.web_config.get_prompts_dir()) / 'code_generation'
        
        # Find matching conversational prompt
        pattern = str(prompts_dir / f"conversational_step_{step_number}_*.txt")
        matching_files = glob.glob(pattern)
        
        if matching_files:
            try:
                return Path(matching_files[0]).read_text(encoding='utf-8')
            except Exception as e:
                self.logger.error(f"Error loading fallback prompt: {e}")
        
        self.logger.warning(f"No fallback prompt found for step {step_number}")
        return None
    
    async def _test_generated_step(self, generated_code: str, step_type: str, target_url: str, channel_name: str) -> bool:
        """Test the generated code step with REAL website testing and 3-attempt fix loop"""
        try:
            current_code = generated_code
            max_attempts = 3
            
            for attempt in range(1, max_attempts + 1):
                self.logger.info(f"Testing attempt {attempt}/{max_attempts} for {step_type}")
                
                # Test current code with real website
                test_result = await self._run_real_website_test(current_code, step_type, target_url, channel_name)
                
                if test_result["success"]:
                    self.logger.info(f"✅ {step_type} working after {attempt} attempt(s)")
                    return True
                
                # If failed and not last attempt, try to fix
                if attempt < max_attempts:
                    self.logger.info(f"❌ Attempt {attempt} failed, generating fix...")
                    
                    fixed_code = await self._generate_code_fix(
                        current_code, step_type, test_result, attempt
                    )
                    
                    if fixed_code:
                        current_code = fixed_code
                        self.logger.info(f"🔧 Generated fix for attempt {attempt}")
                    else:
                        self.logger.error(f"Failed to generate fix for attempt {attempt}")
                        break
                else:
                    self.logger.error(f"❌ {step_type} failed after {max_attempts} attempts")
            
            return False
            
        except Exception as e:
            self.logger.error(f"Testing failed for {step_type}: {e}")
            return False
    
    async def _run_real_website_test(self, code: str, step_type: str, target_url: str, channel_name: str) -> Dict[str, Any]:
        """Run real website test for generated code"""
        try:
            # Create scraper class from code
            scraper_class = self._create_scraper_class_from_code(code, step_type)
            
            if not scraper_class:
                return {
                    "success": False,
                    "error_type": "CODE_COMPILATION_ERROR",
                    "error_message": "Failed to create scraper class from generated code",
                    "error_details": {}
                }
            
            # Create test config
            from ..scrapers.iterative_tv_scraper import ScraperConfig
            test_config = ScraperConfig({
                'headless': False,  # For debugging
                'timeout': 30000,
                'credentials': self.login_credentials or {},
                'output_dir': str(self.session_dir),
                'save_page_dumps': True
            })
            
            # Test based on step type using ScraperRunner
            from ..scrapers.scraper_runner import ScraperRunner
            runner = ScraperRunner(scraper_class, test_config)
            
            if step_type == "login":
                return await runner.test_login_functionality()
            elif step_type == "channel":
                return await runner.test_channel_functionality()
            elif step_type == "date":
                return await runner.test_date_functionality()
            elif step_type == "program":
                return await runner.test_program_functionality()
            else:
                return {
                    "success": False,
                    "error_type": "UNKNOWN_STEP",
                    "error_message": f"Unknown step type: {step_type}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error_type": type(e).__name__,
                "error_message": str(e),
                "error_details": {"exception": str(e)}
            }
    
    def _create_scraper_class_from_code(self, code: str, step_type: str):
        """Create scraper class from generated code string"""
        try:
            # Create temporary file with the code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name
            
            # Load module from file
            spec = importlib.util.spec_from_file_location(f"temp_scraper_{step_type}", temp_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find scraper class in module
            from ..scrapers.iterative_tv_scraper import IterativeTVScraper
            for name in dir(module):
                obj = getattr(module, name)
                if (isinstance(obj, type) and 
                    issubclass(obj, IterativeTVScraper) and 
                    obj != IterativeTVScraper):
                    return obj
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to create scraper class: {e}")
            return None
        finally:
            # Clean up temp file
            try:
                Path(temp_file).unlink()
            except:
                pass
    
    async def _generate_code_fix(self, current_code: str, step_type: str, test_result: Dict[str, Any], attempt_number: int) -> Optional[str]:
        """Generate fix for failed code using LLM"""
        try:
            # Load fix generation prompt
            prompts_dir = Path(self.web_config.get_prompts_dir()) / 'code_fixing'
            fix_prompt_file = prompts_dir / "fix_generation.txt"
            
            if not fix_prompt_file.exists():
                self.logger.error("Fix generation prompt not found")
                return None
            
            prompt_template = fix_prompt_file.read_text(encoding='utf-8')
            
            # Get intelligence data for this step
            task_id_map = {
                "login": "task_0_login_authentication",
                "channel": "task_1_channel_detection", 
                "date": "task_2_date_navigation",
                "program": "task_3_program_extraction"
            }
            
            task_id = task_id_map.get(step_type)
            intelligence_data = self.accumulated_intelligence.get(task_id, {}) if task_id else {}
            
            # Prepare context data
            context_data = {
                "attempt_number": attempt_number,
                "step_type": step_type,
                "error_type": test_result.get("error_type", "Unknown"),
                "error_message": test_result.get("error_message", "Unknown error"),
                "page_url": test_result.get("page_url", "Unknown"),
                "page_title": test_result.get("page_title", "Unknown"),
                "current_code": current_code,
                "error_details": json.dumps(test_result.get("error_details", {}), indent=2),
                "intelligence_data": json.dumps(intelligence_data, indent=2)
            }
            
            # Format the prompt
            formatted_prompt = prompt_template.format(**context_data)
            
            # Generate fix using existing LLM service
            from ..services.code_generator import SmartCodeGenerator
            code_generator = SmartCodeGenerator(self.session_id, self.logger)
            
            from langchain_core.messages import HumanMessage
            human_message = HumanMessage(content=formatted_prompt)
            
            self.logger.info(f"🤖 Generating fix for {step_type} attempt {attempt_number}...")
            fixed_code = code_generator.llm_service.stream_response(
                messages=[human_message],
                print_response=True
            )
            
            # Clean the generated code
            cleaned_code = code_generator._clean_generated_code(fixed_code)
            
            return cleaned_code
            
        except Exception as e:
            self.logger.error(f"Failed to generate fix: {e}")
            return None
    
    async def _generate_final_scraper_iterative(
        self,
        code_generator: 'SmartCodeGenerator',
        target_url: str,
        channel_name: str
    ) -> Optional[str]:
        """Generate final scraper combining all iterative steps"""
        try:
            # Use existing final scraper generation approach
            # Load final scraper prompt (reuse existing)
            prompts_dir = Path(self.web_config.get_prompts_dir()) / 'code_generation'
            final_prompt_file = prompts_dir / "enhanced_scraper_generation.txt"
            
            if not final_prompt_file.exists():
                self.logger.error("Final scraper prompt not found")
                return None
            
            prompt_template = final_prompt_file.read_text(encoding='utf-8')
            
            # Prepare context data (reuse existing format)
            context_data = {
                "target_url": target_url,
                "channel_name": channel_name,
                "class_name": self._generate_class_name(channel_name),
                "website_name": self._extract_website_name(target_url),
                "accumulated_intelligence": json.dumps(self.accumulated_intelligence, indent=2)
            }
            
            # Format the prompt
            formatted_prompt = prompt_template.format(**context_data)
            
            # Generate final scraper using existing LLM service
            from langchain_core.messages import HumanMessage
            human_message = HumanMessage(content=formatted_prompt)
            
            self.logger.info("🤖 Generating final complete scraper...")
            final_scraper_code = code_generator.llm_service.stream_response(
                messages=[human_message],
                print_response=True
            )
            
            # Clean the generated code (reuse existing method)
            cleaned_code = code_generator._clean_generated_code(final_scraper_code)
            
            self.logger.info("✅ Final scraper generation completed")
            return cleaned_code
            
        except Exception as e:
            self.logger.error(f"Failed to generate final scraper: {e}")
            return None
    
    def _extract_website_name(self, target_url: str) -> str:
        """Extract website name from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(target_url)
            domain = parsed.netloc.replace('www.', '')
            return domain.split('.')[0].title()
        except:
            return "TVWebsite"

    async def _execute_conversational_code_generation(self, target_url: str, channel_name: str) -> None:        
        """Execute conversational code generation using message history approach"""
        try:
            self.logger.info("Starting conversational code generation with message history...")
            
            # Import enhanced code generator
            from ..services.code_generator import SmartCodeGenerator
            code_generator = SmartCodeGenerator(self.session_id, self.logger)
            
            # Initialize conversation with system prompt
            code_generator.initialize_conversation()
            
            # Step 0: Generate login methods (only if login intelligence is available)
            if 'task_0_login_authentication' in self.accumulated_intelligence:
                self.logger.info("🤖 Step 0: Generating login authentication methods...")
                step0_code = await self._generate_conversational_step(
                    code_generator, 0, "task_0_login_authentication", target_url, channel_name
                )
                
                if step0_code:
                    # Add step 0 response to conversation history
                    code_generator.add_ai_response(step0_code)
            
            # Step 1: Generate foundation & channel navigation methods
            self.logger.info("🤖 Step 1: Generating channel detection methods...")
            step1_code = await self._generate_conversational_step(
                code_generator, 1, "task_1_channel_detection", target_url, channel_name
            )
            
            if step1_code:
                # Add step 1 response to conversation history
                code_generator.add_ai_response(step1_code)
            
            # Step 2: Generate date discovery & HTML collection methods  
            self.logger.info("🤖 Step 2: Generating date navigation methods...")
            step2_code = await self._generate_conversational_step(
                code_generator, 2, "task_2_date_navigation", target_url, channel_name
            )
            
            if step2_code:
                # Add step 2 response to conversation history
                code_generator.add_ai_response(step2_code)
            
            # Step 3: Generate program extraction methods
            self.logger.info("🤖 Step 3: Generating program extraction methods...")
            step3_code = await self._generate_conversational_step(
                code_generator, 3, "task_3_program_extraction", target_url, channel_name
            )
            
            if step3_code:
                # Add step 3 response to conversation history
                code_generator.add_ai_response(step3_code)
            
            # Step 4: Generate final complete scraper using conversation history
            self.logger.info("🤖 Step 4: Generating final complete scraper...")
            final_scraper_code = await self._generate_final_scraper_conversational(
                code_generator, target_url, channel_name
            )
            
            # Store the final scraper code
            self.accumulated_code = final_scraper_code
            
            # Save final scraper
            await self._save_final_scraper(target_url, channel_name)
            
            self.logger.info("✅ Conversational code generation completed successfully!")
            
        except Exception as e:
            self.logger.error(f"Conversational code generation failed: {e}")
            raise
    
    async def _generate_conversational_step(
        self, 
        code_generator: 'SmartCodeGenerator', 
        step_number: int, 
        task_id: str, 
        target_url: str, 
        channel_name: str
    ) -> Optional[str]:
        """Generate code for a specific conversational step and add to message history"""
        try:
            # Get task result and intelligence
            task_result = self.task_results.get(task_id)
            if not task_result or not task_result.is_successful:
                self.logger.warning(f"No successful result for {task_id}, skipping step {step_number}")
                return None
            
            task_intelligence = self.accumulated_intelligence.get(task_id, {})
            
            # Get HTML content and screenshot from task result
            html_content, screenshot_path = self._extract_html_and_screenshot(task_result)
            
            # Generate code for this step using conversational approach
            generated_code = await code_generator.generate_conversational_step_with_history(
                step_number=step_number,
                task_id=task_id,
                intelligence=task_intelligence,
                html_content=html_content,
                screenshot_path=screenshot_path,
                target_url=target_url,
                channel_name=channel_name
            )
            
            return generated_code
            
        except Exception as e:
            self.logger.error(f"Failed to generate conversational step {step_number}: {e}")
            return None
    
    async def _generate_final_scraper_conversational(
        self,
        code_generator: 'SmartCodeGenerator',
        target_url: str,
        channel_name: str
    ) -> Optional[str]:
        """Generate final scraper using full conversation history"""
        try:
            # Generate final scraper using conversation history
            final_scraper_code = await code_generator.generate_final_scraper_with_history(
                target_url=target_url,
                channel_name=channel_name
            )
            
            return final_scraper_code
            
        except Exception as e:
            self.logger.error(f"Failed to generate final scraper: {e}")
            return None
    
    def _extract_html_and_screenshot(self, task_result: TaskResult) -> tuple[Optional[str], Optional[str]]:
        """Extract HTML content and screenshot path from task result"""
        html_content = None
        screenshot_path = None
        
        try:
            # Look for HTML files in task outputs
            task_dir = task_result.outputs.get('task_dir')
            if task_dir and isinstance(task_dir, Path):
                # Find HTML files
                html_files = list(task_dir.glob('*.html'))
                if html_files:
                    # Use the most recent HTML file
                    latest_html = max(html_files, key=lambda f: f.stat().st_mtime)
                    with open(latest_html, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    self.logger.info(f"Extracted HTML content from: {latest_html}")
                
                # Find screenshot files
                screenshot_files = list(task_dir.glob('*.png'))
                if screenshot_files:
                    # Use the most recent screenshot
                    latest_screenshot = max(screenshot_files, key=lambda f: f.stat().st_mtime)
                    screenshot_path = str(latest_screenshot)
                    self.logger.info(f"Found screenshot: {latest_screenshot}")
        
        except Exception as e:
            self.logger.warning(f"Failed to extract HTML/screenshot: {e}")
        
        return html_content, screenshot_path

    
    async def _save_final_scraper(self, target_url: str, channel_name: str) -> None:
        """Save the final generated scraper code to file"""
        try:
            if not self.accumulated_code:
                self.logger.warning("No accumulated code to save")
                return
            
            # Generate filename
            class_name = self._generate_class_name(channel_name)
            scraper_filename = f"{class_name.lower()}_scraper.py"
            scraper_path = self.session_dir / scraper_filename
            
            # Save the code
            with open(scraper_path, 'w', encoding='utf-8') as f:
                f.write(self.accumulated_code)
            
            # Store in session results
            self.analysis_session.final_outputs['scraper_code'] = scraper_path
            
            self.logger.info(f"✅ Final scraper saved: {scraper_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save final scraper: {e}")
    
    def _generate_class_name(self, channel_name: str) -> str:
        """Generate a clean class name from channel name"""
        import re
        # Clean channel name and convert to PascalCase
        clean_name = re.sub(r'[^\w\s]', '', channel_name)
        words = clean_name.split()
        class_name = ''.join(word.capitalize() for word in words) + 'Scraper'
        return class_name
    
    async def run_single_task(
        self,
        task_id: str,
        target_url: str,
        channel_name: str,
        previous_results: Optional[Dict[str, Any]] = None,
        login_credentials: Optional[Dict[str, str]] = None
    ) -> TaskResult:
        """
        Run a single task for debugging/testing purposes
        
        Args:
            task_id: ID of task to execute
            target_url: Target TV schedule website URL
            channel_name: Target channel name
            previous_results: Results from previous tasks (for context)
            login_credentials: Optional dict with 'username' and 'password' keys
            
        Returns:
            TaskResult: Single task execution result
        """
        
        self.logger.info(f"Running single task: {task_id}")
        
        # Store login credentials for task execution
        self.login_credentials = login_credentials
        
        # Get task definition
        task_def = self._get_task_definition_by_id(task_id)
        if not task_def:
            raise ValueError(f"Task definition not found: {task_id}")
        
        try:
            # Initialize browser service if not already initialized
            if not self.browser_service.is_initialized:
                await self.browser_service.initialize()
            
            # Execute single task
            task_result = await self._execute_single_task(
                task_definition=task_def,
                target_url=target_url,
                channel_name=channel_name,
                previous_results=previous_results or {}
            )
            
            self.logger.info(f"Single task completed: {task_id} - {'SUCCESS' if task_result.is_successful else 'FAILED'}")

            if task_result.is_successful:
                await self._extract_and_accumulate_intelligence(task_result, target_url, channel_name)

            return task_result
            
        finally:
            # Clean up browser service
            await self.browser_service.close()
    
    async def _execute_single_task(
        self,
        task_definition: TaskDefinition,
        target_url: str,
        channel_name: str,
        previous_results: Optional[Dict[str, Any]] = None
    ) -> TaskResult:
        """Execute a single task with proper context and error handling"""
        
        # Create task directory based on HAR recording mode
        if self.web_config.is_task_based_har_recording():
            # Create task-specific directory for task-based recording
            task_dir = self.web_config.get_task_dir(self.session_id, task_definition.task_id)
        else:
            # For global traditional recording, create a minimal task directory for conversation logs only
            task_dir = self.web_config.get_session_dir(self.session_id) / task_definition.task_id
            task_dir.mkdir(parents=True, exist_ok=True)
        
        # Create task context
        task_context = TaskContext(
            session_id=self.session_id,
            target_url=target_url,
            channel_name=channel_name,
            task_dir=task_dir,
            previous_results=previous_results or self.accumulated_intelligence,
            login_credentials=self.login_credentials  # Pass login credentials to task context
        )
        
        # Load task execution prompt
        task_prompt = self._load_task_execution_prompt(task_definition.task_id, task_context)
        
        # Execute task using browser service
        task_result = await self.browser_service.execute_task(
            task_context=task_context,
            task_prompt=task_prompt,
            time_limit_seconds=task_definition.time_limit_seconds
        )
        
        return task_result
    
    async def _extract_and_accumulate_intelligence(
        self,
        task_result: TaskResult,
        target_url: str,
        channel_name: str
    ) -> None:
        """Extract intelligence from task result and accumulate for next tasks"""
        
        try:
            # Create task context for intelligence extraction
            task_context = TaskContext(
                session_id=self.session_id,
                target_url=target_url,
                channel_name=channel_name,
                task_dir=task_result.outputs['task_dir'],
                previous_results=self.accumulated_intelligence
            )
            
            # Extract intelligence
            task_intelligence = await self.intelligence_extractor.extract_task_intelligence(
                task_result=task_result,
                task_context=task_context
            )
            
            # Accumulate intelligence for next tasks
            self.accumulated_intelligence[task_result.task_id] = task_intelligence
            
            # Store in task result
            task_result.intelligence_data = task_intelligence
            
            self.logger.info(f"Intelligence extracted and accumulated for {task_result.task_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to extract intelligence for {task_result.task_id}: {str(e)}")
            # Continue with workflow even if intelligence extraction fails
    
    def _load_task_execution_prompt(self, task_id: str, task_context: TaskContext) -> str:
        """Load task execution prompt from file"""
        
        # prompts_dir = Path(__file__).parent.parent.parent / 'prompts' / 'task_execution'
        prompts_dir = Path(self.web_config.get_prompts_dir()) / 'task_execution'
        prompt_file = prompts_dir / f'{task_id}.txt'
        
        if prompt_file.exists():
            prompt_template = prompt_file.read_text(encoding='utf-8')
            
            # Prepare format parameters
            format_params = {
                'target_url': task_context.target_url,
                'channel_name': task_context.channel_name,
                'session_id': task_context.session_id
            }
            
            # Add login credentials if this is a login task
            if task_id == "task_0_login_authentication" and task_context.login_credentials:
                format_params.update({
                    'username': task_context.login_credentials.get('username', ''),
                    'password': task_context.login_credentials.get('password', ''),
                    'login_url': task_context.login_credentials.get('login_url', 'Not specified')
                })
            
            # Format prompt with context
            return prompt_template.format(**format_params)
        else:
            self.logger.warning(f"Task execution prompt not found: {prompt_file}")
            return f"Analyze the TV schedule website {task_context.target_url} for channel {task_context.channel_name}. Focus on {task_id} requirements."
    
    def _get_task_definition_by_id(self, task_id: str) -> Optional[TaskDefinition]:
        """Get specific task definition by ID"""
        for task_def in self._get_intelligence_task_definitions():
            if task_def.task_id == task_id:
                return task_def
        return None
    
    async def _save_session_summary(self) -> None:
        """Save comprehensive session summary"""
        try:
            summary = {
                "session_info": {
                    "session_id": self.session_id,
                    "target_url": self.analysis_session.target_url,
                    "channel_name": self.analysis_session.channel_name,
                    "start_time": self.analysis_session.start_time.isoformat(),
                    "end_time": self.analysis_session.end_time.isoformat() if self.analysis_session.end_time else None,
                    "duration_seconds": self.analysis_session.duration_seconds,
                    "total_tasks": len(self.analysis_session.task_results),
                    "successful_tasks": len(self.analysis_session.successful_tasks),
                    "failed_tasks": len(self.analysis_session.failed_tasks)
                },
                "task_results": {
                    task_result.task_id: {
                        "status": task_result.status.value,
                        "duration_seconds": task_result.duration_seconds,
                        "outputs": {k: str(v) for k, v in task_result.outputs.items()},
                        "error_message": task_result.error_message
                    }
                    for task_result in self.analysis_session.task_results
                },
                "accumulated_intelligence": self.accumulated_intelligence
            }
            
            summary_path = self.session_dir / f"session_summary_{self.session_id}.json"
            
            import json
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Session summary saved: {summary_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save session summary: {str(e)}")
    
    
    def print_session_summary(self) -> None:
        """Print comprehensive session summary"""
        if not self.analysis_session:
            self.logger.warning("No analysis session to summarize")
            return
        
        self.logger.info("="*80)
        self.logger.info("TV SCHEDULE ANALYSIS SESSION SUMMARY")
        self.logger.info("="*80)
        
        self.logger.info(f"Session ID: {self.session_id}")
        self.logger.info(f"Target URL: {self.analysis_session.target_url}")
        self.logger.info(f"Channel: {self.analysis_session.channel_name}")
        self.logger.info(f"Duration: {self.analysis_session.duration_seconds:.2f} seconds")
        
        self.logger.info("\nTASK RESULTS:")
        for task_result in self.analysis_session.task_results:
            status = "✅ SUCCESS" if task_result.is_successful else "❌ FAILED"
            duration = f"{task_result.duration_seconds:.2f}s" if task_result.duration_seconds else "N/A"
            self.logger.info(f"  {status} {task_result.task_id} ({duration})")
            if task_result.error_message:
                self.logger.info(f"    Error: {task_result.error_message}")
        
        self.logger.info(f"\nSTATISTICS:")
        self.logger.info(f"  Total Tasks: {len(self.analysis_session.task_results)}")
        self.logger.info(f"  Successful: {len(self.analysis_session.successful_tasks)}")
        self.logger.info(f"  Failed: {len(self.analysis_session.failed_tasks)}")
        self.logger.info(f"  Success Rate: {len(self.analysis_session.successful_tasks)/len(self.analysis_session.task_results)*100:.1f}%")
        
        self.logger.info(f"\nOUTPUT DIRECTORY: {self.session_dir}")
        self.logger.info("="*80)
