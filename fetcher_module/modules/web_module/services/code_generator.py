"""Smart Code Generator - Framework integrated"""

import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from common.llms.llm_service import LLMService
from ..exceptions.web_exceptions import CodeGenerationError


class SmartCodeGenerator:
    """Clean code generator using framework services"""
    
    def __init__(self, session_id: str, logger):
        self.session_id = session_id
        self.logger = logger
        
        # Import web_config directly - always gets updated data
        from ..config.web_config import web_config
        self.web_config = web_config
        
        # Initialize framework LLM service
        self.llm_service = LLMService(session_id)
        
        # Create LLM instance with web config
        llm_config = web_config.get_llm_config()
        self.llm = self.llm_service.create_bedrock_llm(
            model_id=llm_config["model_id"],
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"],
            top_p=llm_config["top_p"]
        )
        
        # Conversation state
        self.conversation_messages = []
        
        self.logger.info("Code generator initialized with framework services")
    
    def initialize_conversation(self) -> None:
        """Initialize conversation with system prompt"""
        try:
            system_prompt = self._load_system_prompt()
            self.conversation_messages = [SystemMessage(content=system_prompt)]
            self.logger.info("Initialized conversation with system prompt")
        except Exception as e:
            self.logger.error(f"Failed to initialize conversation: {e}")
            raise CodeGenerationError(f"System prompt initialization failed: {str(e)}")
    
    def add_ai_response(self, response: str) -> None:
        """Add AI response to conversation history"""
        from langchain_core.messages import AIMessage
        self.conversation_messages.append(AIMessage(content=response))
        self.logger.debug("Added AI response to conversation history")
    
    async def generate_conversational_step_with_history(
        self,
        step_number: int,
        task_id: str,
        intelligence: Dict[str, Any],
        html_content: Optional[str],
        screenshot_path: Optional[str],
        target_url: str,
        channel_name: str
    ) -> Optional[str]:
        """Generate code for a specific conversational step and add to message history"""
        
        self.logger.info(f"Generating conversational step {step_number} with message history")
        
        try:
            # Load step-specific prompt
            prompt_template = self._load_conversational_step_prompt(step_number)
            if not prompt_template:
                self.logger.error(f"Failed to load prompt for step {step_number}")
                return None
            
            # Prepare context data (removed accumulated_intelligence since we have conversation history)
            context_data = {
                "step_number": step_number,
                "task_id": task_id,
                "target_url": target_url,
                "channel_name": channel_name,
                "current_task_intelligence": json.dumps(intelligence, indent=2),
                "html_content": html_content or "No HTML content available",
                "class_name": self._generate_class_name(channel_name)
            }
            
            # Format the prompt with context
            formatted_prompt = prompt_template.format(**context_data)
            
            # Add human message to conversation history
            if screenshot_path and Path(screenshot_path).exists():
                # Add with screenshot
                human_message = self._create_human_message_with_screenshot(formatted_prompt, screenshot_path)
            else:
                # Text only
                human_message = HumanMessage(content=formatted_prompt)
            
            self.conversation_messages.append(human_message)
            
            # Generate response using full conversation history
            self.logger.info(f"🤖 Generating step {step_number} code with conversation context...")
            generated_code = self.llm_service.stream_response(
                llm=self.llm,
                messages=self.conversation_messages,
                print_response=True
            )
            
            # Clean and validate the generated code
            cleaned_code = self._clean_generated_code(generated_code)
            
            self.logger.info(f"✅ Step {step_number} code generation completed")
            return cleaned_code
            
        except Exception as e:
            self.logger.error(f"Failed to generate conversational step {step_number}: {str(e)}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    async def generate_final_scraper_with_history(
        self,
        target_url: str,
        channel_name: str
    ) -> Optional[str]:
        """Generate final complete scraper using full conversation history"""
        try:
            self.logger.info("Generating final scraper with conversation history")
            
            # Load final scraper prompt
            final_prompt_template = self._load_final_scraper_prompt()
            if not final_prompt_template:
                self.logger.error("Failed to load final scraper prompt")
                return None
            
            # Prepare context for final generation
            context_data = {
                "target_url": target_url,
                "channel_name": channel_name,
                "class_name": self._generate_class_name(channel_name)
            }
            
            # Format final prompt
            formatted_final_prompt = final_prompt_template.format(**context_data)
            
            # Add final human message to conversation
            self.conversation_messages.append(HumanMessage(content=formatted_final_prompt))
            
            # Generate final scraper using full conversation context
            self.logger.info("🤖 Generating final scraper with full conversation context...")
            final_scraper_code = self.llm_service.stream_response(
                llm=self.llm,
                messages=self.conversation_messages,
                print_response=True
            )
            
            # Clean final code
            cleaned_final_code = self._clean_generated_code(final_scraper_code)
            
            self.logger.info("✅ Final scraper generation completed")
            return cleaned_final_code
            
        except Exception as e:
            self.logger.error(f"Failed to generate final scraper: {e}")
            return None
    
    def _load_system_prompt(self) -> str:
        """Load system prompt for conversational generation"""
        try:
            prompts_dir = Path(self.web_config.get_prompts_dir()) / 'code_generation'
            system_prompt_file = prompts_dir / 'system_prompt_conversational.txt'
            
            if not system_prompt_file.exists():
                raise FileNotFoundError(f"System prompt not found: {system_prompt_file}")
            
            return system_prompt_file.read_text(encoding='utf-8')
            
        except Exception as e:
            self.logger.error(f"Failed to load system prompt: {str(e)}")
            raise CodeGenerationError(f"System prompt loading failed: {str(e)}")
    
    def _load_final_scraper_prompt(self) -> str:
        """Load final scraper assembly prompt"""
        try:
            prompts_dir = Path(self.web_config.get_prompts_dir()) / 'code_generation'
            final_prompt_file = prompts_dir / 'enhanced_scraper_generation.txt'
            
            if not final_prompt_file.exists():
                raise FileNotFoundError(f"Final scraper prompt not found: {final_prompt_file}")
            
            return final_prompt_file.read_text(encoding='utf-8')
            
        except Exception as e:
            self.logger.error(f"Failed to load final scraper prompt: {str(e)}")
            raise CodeGenerationError(f"Final scraper prompt loading failed: {str(e)}")
    
    def _create_human_message_with_screenshot(self, text_content: str, screenshot_path: str) -> HumanMessage:
        """Create human message with screenshot attachment"""
        try:
            with open(screenshot_path, 'rb') as f:
                screenshot_content = f.read()
            
            return HumanMessage(
                content=[
                    {"type": "text", "text": text_content},
                    {
                        "type": "image",
                        "image": {
                            "format": "png",
                            "source": {
                                "bytes": screenshot_content
                            }
                        }
                    }
                ]
            )
        except Exception as e:
            self.logger.warning(f"Failed to create message with screenshot: {e}")
            return HumanMessage(content=text_content)
    
    # Keep existing method for backward compatibility
    async def generate_conversational_step(
        self,
        step_number: int,
        task_id: str,
        intelligence: Dict[str, Any],
        html_content: Optional[str],
        screenshot_path: Optional[str],
        target_url: str,
        channel_name: str,
        accumulated_intelligence: Dict[str, Any]
    ) -> Optional[str]:
        """Generate code for a specific conversational step with HTML + screenshot context"""
        
        self.logger.info(f"Generating conversational step {step_number} code for {task_id}")
        
        try:
            # Load step-specific prompt
            prompt_template = self._load_conversational_step_prompt(step_number)
            if not prompt_template:
                self.logger.error(f"Failed to load prompt for step {step_number}")
                return None
            
            # Prepare context data
            context_data = {
                "step_number": step_number,
                "task_id": task_id,
                "target_url": target_url,
                "channel_name": channel_name,
                "current_task_intelligence": json.dumps(intelligence, indent=2),
                "html_content": html_content or "No HTML content available",
                "accumulated_intelligence": json.dumps(accumulated_intelligence, indent=2),
                "class_name": self._generate_class_name(channel_name)
            }
            
            # Format the prompt with context
            formatted_prompt = prompt_template.format(**context_data)
            
            # Create messages with screenshot support
            messages = self._create_messages_with_screenshot(formatted_prompt, screenshot_path)
            
            # Generate code
            self.logger.info(f"🤖 Generating step {step_number} code with HTML + screenshot context...")
            generated_code = self.llm_service.stream_response(
                messages=messages,
                print_response=True
            )
            
            # Clean and validate the generated code
            cleaned_code = self._clean_generated_code(generated_code)
            
            self.logger.info(f"✅ Step {step_number} code generation completed")
            return cleaned_code
            
        except Exception as e:
            self.logger.error(f"Failed to generate step {step_number} code: {str(e)}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def _load_conversational_step_prompt(self, step_number: int) -> Optional[str]:
        """Load conversational step-specific code generation prompt"""
        prompts_dir = Path(__file__).parent.parent.parent / 'prompts' / 'code_generation'
        
        # Map step numbers to prompt files
        step_prompt_files = {
            0: 'conversational_step_0_login_methods.txt',  # Login step
            1: 'conversational_step_1_channel_methods.txt',
            2: 'conversational_step_2_date_methods.txt', 
            3: 'conversational_step_3_program_methods.txt'
        }
        
        prompt_file = prompts_dir / step_prompt_files.get(step_number, '')
        
        if prompt_file.exists():
            self.logger.info(f"Loading step {step_number} prompt: {prompt_file}")
            return prompt_file.read_text(encoding='utf-8')
        
        self.logger.error(f"No prompt file found for step {step_number}: {prompt_file}")
        return None
    
    def _create_messages_with_screenshot(self, formatted_prompt: str, screenshot_path: Optional[str]):
        """Create LLM messages with optional screenshot support for code generation"""
        messages = [
            SystemMessage(
                content="You are a senior Python developer specializing in web scraping automation. Generate clean, production-ready code based on intelligence data and visual context. Focus on robust error handling and the 'Store First, Extract Later' approach."
            )
        ]
        
        if screenshot_path and Path(screenshot_path).exists():
            # Add screenshot as image message
            try:
                with open(screenshot_path, 'rb') as f:
                    screenshot_content = f.read()
                
                messages.append(HumanMessage(
                    content=[
                        {"type": "text", "text": formatted_prompt},
                        {
                            "type": "image",
                            "image": {
                                "format": "png",
                                "source": {
                                    "bytes": screenshot_content
                                }
                            }
                        }
                    ]
                ))
                self.logger.info("Added screenshot to code generation context")
            except Exception as e:
                self.logger.warning(f"Failed to add screenshot to code generation context: {e}")
                # Fallback to text-only
                messages.append(HumanMessage(content=formatted_prompt))
        else:
            # Text-only message
            messages.append(HumanMessage(content=formatted_prompt))
        
        return messages
    
    def _generate_class_name(self, channel_name: str) -> str:
        """Generate a clean class name from channel name"""
        import re
        # Clean channel name and convert to PascalCase
        clean_name = re.sub(r'[^\w\s]', '', channel_name)
        words = clean_name.split()
        class_name = ''.join(word.capitalize() for word in words) + 'Scraper'
        return class_name
    
    def _clean_generated_code(self, generated_code: str) -> str:
        """Clean and validate generated code"""
        try:
            # Remove markdown code fences if present
            code_content = generated_code.strip()
            if code_content.startswith('```python'):
                code_content = code_content[9:]  # Remove ```python
                if code_content.endswith('```'):
                    code_content = code_content[:-3]  # Remove ```
            elif code_content.startswith('```'):
                code_content = code_content[3:]
                if code_content.endswith('```'):
                    code_content = code_content[:-3]
            
            return code_content.strip()
            
        except Exception as e:
            self.logger.warning(f"Failed to clean generated code: {e}")
            return generated_code
            
            # Save to session directory
            from ..utils.config import config
            session_dir = config.get_session_dir(self.session_id)
            code_file = session_dir / f"cumulative_code_{task_id}.py"
            
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_code)
            
            self.logger.info(f"✅ Code saved: {code_file}")
            return cleaned_code
            
        except Exception as e:
            self.logger.error(f"Code generation failed for {task_id}: {str(e)}")
            return None
    
    def _load_prompt(self, task_id: str) -> Optional[str]:
        """Load minimal prompt"""
        prompts_dir = Path(__file__).parent.parent.parent / 'prompts' / 'code_generation'
        prompt_file = prompts_dir / f'{task_id}_code.txt'
        
        if prompt_file.exists():
            return prompt_file.read_text(encoding='utf-8')
        else:
            self.logger.warning(f"Prompt not found: {prompt_file}")
            return None
    
    def _get_system_prompt(self) -> str:
        """Minimal system prompt - trust the LLM"""
        return """You are a Senior Software Developer with 15+ years experience.

        Generate MINIMAL, CLEAN, WORKING code that:
        ✅ Analyzes intelligence patterns accurately
        ✅ Uses base class methods efficiently  
        ✅ Implements only required functionality
        ✅ Handles errors gracefully
        ✅ Follows Python best practices
        
        Focus on QUALITY over QUANTITY. Write code like a senior developer - concise and effective."""
    
    def _create_messages_with_png(self, formatted_prompt: str, png_file_path: Optional[str] = None) -> list:
        """Create messages with PNG screenshot support"""
        
        # Start with text content
        message_content = [{"type": "text", "text": formatted_prompt}]
        
        # Add PNG if available
        if png_file_path and Path(png_file_path).exists():
            try:
                with open(png_file_path, 'rb') as f:
                    png_content = f.read()
                
                message_content.append({
                    "type": "image",
                    "image": {
                        "format": "png",
                        "source": {"bytes": png_content}
                    }
                })
                
                self.logger.info(f"✅ Added PNG screenshot to code generation: {Path(png_file_path).name}")
                
            except Exception as e:
                self.logger.warning(f"Failed to add PNG screenshot: {str(e)}")
        else:
            self.logger.debug("No PNG screenshot available for code generation")
        
        return [
            SystemMessage(content=self._get_system_prompt()),
            HumanMessage(content=message_content)
        ]
    
    def _clean_code(self, code: str) -> str:
        """Clean generated code"""
        # Remove markdown fences
        if code.startswith('```python'):
            code = code[9:]
        elif code.startswith('```'):
            code = code[3:]
        
        if code.endswith('```'):
            code = code[:-3]
        
        code = code.strip()
        
        # Add minimal header
        header = f"""# Generated TV Schedule Scraper - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Generator: SmartCodeGenerator (Minimal Mode)

"""
        
        return header + code
    
    # Keep existing methods for backward compatibility
    async def generate_complete_scraper(
        self,
        all_intelligence: Dict[str, Any],
        target_url: str,
        channel_name: str,
        output_dir: Path,
        date_navigation_html: Optional[str] = None,
        date_navigation_screenshot: Optional[Path] = None
    ) -> str:
        """Generate complete scraper using enhanced approach"""
        
        self.logger.info("Generating complete scraper")
        
        # Use enhanced prompt for final generation
        prompt_template = self._load_enhanced_prompt()
        context = self._prepare_context(all_intelligence, target_url, channel_name, date_navigation_html)
        
        messages = self._create_messages_with_screenshot(
            prompt_template, 
            context, 
            date_navigation_screenshot
        )
        
        # Generate code
        self.logger.info("🤖 Generating complete scraper...")
        generated_code = self.llm_service.stream_response(
            messages=messages,
            print_response=True,
            temperature=0.1,
            max_tokens=8000
        )
        
        # Clean and save
        cleaned_code = self._clean_code(generated_code)
        scraper_file = output_dir / f"{self._clean_name(channel_name)}_scraper.py"
        
        with open(scraper_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_code)
        
        self.logger.info(f"✅ Complete scraper generated: {scraper_file}")
        return str(scraper_file)
    
    def _prepare_context(
        self, 
        all_intelligence: Dict[str, Any], 
        target_url: str, 
        channel_name: str,
        date_navigation_html: Optional[str] = None
    ) -> Dict[str, str]:
        """Prepare context for complete scraper generation"""
        
        context = {
            'target_url': target_url,
            'channel_name': channel_name,
            'class_name': self._generate_class_name(channel_name),
            'all_intelligence': json.dumps(all_intelligence, indent=2),
            'date_navigation_html': date_navigation_html or "# No HTML captured",
            'generation_timestamp': datetime.now().isoformat()
        }
        
        return context
    
    def _load_enhanced_prompt(self) -> str:
        """Load enhanced prompt for complete generation"""
        prompts_dir = Path(__file__).parent.parent.parent / 'prompts' / 'code_generation'
        prompt_file = prompts_dir / 'enhanced_scraper_generation.txt'
        
        if prompt_file.exists():
            return prompt_file.read_text(encoding='utf-8')
        else:
            return self._get_fallback_prompt()
    
    def _get_fallback_prompt(self) -> str:
        """Fallback prompt for complete generation"""
        return """Generate a complete TV schedule scraper for {target_url} (Channel: {channel_name}).

Intelligence: {all_intelligence}

Create a class that inherits from SmartTVScraper and implements execute_scraping_workflow().
Use intelligence patterns and base class methods efficiently."""
    
    def _generate_class_name(self, channel_name: str) -> str:
        """Generate clean class name"""
        clean_name = ''.join(c for c in channel_name if c.isalnum() or c.isspace())
        words = clean_name.split()
        return ''.join(word.capitalize() for word in words) + 'Scraper'
    
    def _clean_name(self, name: str) -> str:
        """Clean name for filesystem"""
        import re
        return re.sub(r'[^\w\-_]', '_', name)
