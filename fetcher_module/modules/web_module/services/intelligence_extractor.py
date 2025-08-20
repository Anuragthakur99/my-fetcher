"""Intelligence extraction from browser-use task execution results - Framework integrated"""

import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from langchain_core.messages import SystemMessage, HumanMessage

from ..models.task_models import TaskResult, TaskContext
from ..utils.history_cleaner import HistoryCleaner
from common.llms.llm_service import LLMService
from ..exceptions.web_exceptions import IntelligenceExtractionError


class IntelligenceExtractor:
    """Extract structured intelligence from browser-use execution results"""
    
    def __init__(self, session_id: str, logger):
        self.session_id = session_id
        self.logger = logger
        
        # Import web_config directly - always gets updated data
        from ..config.web_config import web_config
        self.web_config = web_config
        
        # Initialize framework services
        self.llm_service = LLMService(session_id)
        self.history_cleaner = HistoryCleaner(session_id, logger)
        
        # Create LLM instance with web config
        llm_config = web_config.get_llm_config()
        self.llm = self.llm_service.create_bedrock_llm(
            model_id=llm_config["model_id"],
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"],
            top_p=llm_config["top_p"]
        )
        
        self.logger.info("Intelligence extractor initialized with framework services")
    
    async def extract_task_intelligence(
        self, 
        task_result: TaskResult, 
        task_context: TaskContext
    ) -> Dict[str, Any]:
        """
        Extract intelligence from completed task using post-processing analysis
        
        Flow: raw_history → clean_history → website_intelligence (same as existing project)
        """
        
        self.logger.info(f"Starting intelligence extraction for {task_result.task_id}")
        
        try:
            # Step 1: Load consolidated history file (following promptwright pattern)
            # Look for the consolidated history file created by agent.save_history()
            history_path = task_context.task_dir / f"history_{task_result.task_id}.json"
            
            if not history_path.exists():
                # Fallback: try to find any history file in the task directory
                history_files = list(task_context.task_dir.glob("history_*.json"))
                if history_files:
                    history_path = history_files[0]
                    self.logger.info(f"Using fallback history file: {history_path}")
                else:
                    raise FileNotFoundError(f"No consolidated history file found for {task_result.task_id} in {task_context.task_dir}")
            
            self.logger.info(f"Using consolidated history file: {history_path}")
            
            # Step 2: Clean the history (remove screenshots, coordinates - same as existing)
            clean_history_path = task_context.task_dir / f'cleaned_history_{task_result.task_id}.json'
            self.history_cleaner.clean_history(
                input_path=str(history_path),
                output_path=str(clean_history_path)
            )
            
            # Step 3: Extract structured intelligence from clean history
            intelligence = await self._analyze_task_patterns(
                clean_history_path=clean_history_path,
                task_result=task_result,
                task_context=task_context
            )
            
            # Step 4: Save intelligence output (same naming pattern as existing)
            intelligence_path = task_context.task_dir / f'website_intelligence_{task_result.task_id}.json'
            with open(intelligence_path, 'w', encoding='utf-8') as f:
                json.dump(intelligence, f, indent=2, ensure_ascii=False)
            
            # Update task result outputs
            task_result.outputs['consolidated_history.json'] = history_path
            task_result.outputs['cleaned_history.json'] = clean_history_path
            task_result.outputs['website_intelligence.json'] = intelligence_path
            
            self.logger.info(f"Successfully extracted intelligence for {task_result.task_id}")
            return intelligence
            
        except Exception as e:
            self.logger.error(f"Failed to extract intelligence for {task_result.task_id}: {str(e)}")
            raise
    
    async def _analyze_task_patterns(
        self,
        clean_history_path: Path,
        task_result: TaskResult,
        task_context: TaskContext
    ) -> Dict[str, Any]:
        """Analyze task patterns using LLM with HTML content and screenshot support"""
        
        self.logger.info(f"Analyzing patterns for {task_result.task_id}")
        
        # Load clean history
        with open(clean_history_path, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        
        # Extract HTML content from task result
        html_content = self._extract_html_content(task_result)
        
        # Find screenshot file
        screenshot_path = self._find_screenshot_file(task_result)
        
        # Load task-specific intelligence extraction prompt
        intelligence_prompt = self._load_task_intelligence_prompt(task_result.task_id)
        
        # Prepare context for intelligence extraction
        context_data = {
            "history_data": json.dumps(history_data, indent=2),
            "html_content": html_content or "No HTML content available",
            "target_url": task_context.target_url,
            "channel_name": task_context.channel_name,
            "task_id": task_result.task_id,
            "previous_intelligence": json.dumps(task_context.previous_results, indent=2) if hasattr(task_context, 'previous_results') else "{}"
        }
        
        # Format the prompt with context data
        formatted_prompt = intelligence_prompt.format(**context_data)
        
        # Create messages for LLM with screenshot support
        messages = self._create_messages_with_screenshot(formatted_prompt, screenshot_path)
        
        self.logger.info("Calling LLM for task pattern analysis with HTML + screenshot context...")
        
        # Get intelligence using framework LLM service
        response = self.llm_service.stream_response(
            llm=self.llm,
            messages=messages,
            print_response=False
        )
        
        # Parse JSON response with enhanced extraction logic
        try:
            # Clean the response content - extract JSON from markdown or text
            response_content = response.strip()
            self.logger.info(f"Raw LLM response (first 200 chars): {response_content[:200]}")
            
            # Try to extract JSON from markdown code blocks
            import re
            
            # Look for JSON within ```json...``` blocks
            json_match = re.search(r'```json\s*\n(.*?)\n```', response_content, re.DOTALL)
            if json_match:
                response_content = json_match.group(1).strip()
                self.logger.info("Extracted JSON from ```json``` block")
            else:
                # Look for JSON within ```...``` blocks
                json_match = re.search(r'```\s*\n(.*?)\n```', response_content, re.DOTALL)
                if json_match:
                    potential_json = json_match.group(1).strip()
                    if potential_json.startswith('{') and potential_json.endswith('}'):
                        response_content = potential_json
                        self.logger.info("Extracted JSON from ``` block")
                else:
                    # Look for JSON object within the text (starts with { and ends with })
                    json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                    if json_match:
                        response_content = json_match.group(0).strip()
                        self.logger.info("Extracted JSON object from text")
            
            response_content = response_content.strip()
            self.logger.info(f"Cleaned response (first 200 chars): {response_content[:200]}")
            
            # Validate that we have what looks like JSON
            if not response_content.startswith('{'):
                self.logger.error(f"Response doesn't start with '{{': {response_content[:100]}")
                raise json.JSONDecodeError("Response doesn't start with '{'", response_content, 0)
            
            if not response_content.endswith('}'):
                self.logger.error(f"Response doesn't end with '}}': {response_content[-100:]}")
                # Try to fix incomplete JSON by adding closing brace
                response_content += '}'
                self.logger.info("Added missing closing brace")
            
            intelligence_data = json.loads(response_content)
            
            self.logger.info("Successfully extracted task intelligence with HTML + screenshot context")
            return intelligence_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse intelligence JSON: {str(e)}")
            self.logger.error(f"Full response content: {response}")
            # Return fallback structure
            return {
                "extraction_failed": True,
                "raw_response": response,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "task_id": task_result.task_id
            }
    
    def _extract_html_content(self, task_result: TaskResult) -> Optional[str]:
        """Extract HTML content from task result outputs"""
        try:
            task_dir = task_result.outputs.get('task_dir')
            if not task_dir or not isinstance(task_dir, Path):
                return None
            
            # Look for HTML files in task directory
            html_files = list(task_dir.glob('*.html'))
            if not html_files:
                return None
            
            # Use the most recent HTML file
            latest_html = max(html_files, key=lambda f: f.stat().st_mtime)
            
            with open(latest_html, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            self.logger.info(f"Extracted HTML content from: {latest_html}")
            return html_content
            
        except Exception as e:
            self.logger.warning(f"Failed to extract HTML content: {e}")
            return None
    
    def _find_screenshot_file(self, task_result: TaskResult) -> Optional[str]:
        """Find screenshot file from task result outputs"""
        try:
            task_dir = task_result.outputs.get('task_dir')
            if not task_dir or not isinstance(task_dir, Path):
                return None
            
            # Look for screenshot files
            screenshot_files = list(task_dir.glob('*.png'))
            if not screenshot_files:
                return None
            
            # Use the most recent screenshot
            latest_screenshot = max(screenshot_files, key=lambda f: f.stat().st_mtime)
            
            self.logger.info(f"Found screenshot: {latest_screenshot}")
            return str(latest_screenshot)
            
        except Exception as e:
            self.logger.warning(f"Failed to find screenshot: {e}")
            return None
    
    def _create_messages_with_screenshot(self, formatted_prompt: str, screenshot_path: Optional[str]):
        """Create LLM messages with optional screenshot support"""
        messages = [
            SystemMessage(
                content="You are a senior web scraping architect specializing in extracting website patterns for automated data collection. You can analyze both text-based exploration history and visual screenshots to provide comprehensive intelligence."
            )
        ]
        
        if screenshot_path and Path(screenshot_path).exists():
            # Add screenshot as image message (following existing pattern)
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
                self.logger.info("Added screenshot to LLM context for enhanced intelligence extraction")
            except Exception as e:
                self.logger.warning(f"Failed to add screenshot to context: {e}")
                # Fallback to text-only
                messages.append(HumanMessage(content=formatted_prompt))
        else:
            # Text-only message
            messages.append(HumanMessage(content=formatted_prompt))
        
        return messages
    
    def _load_task_intelligence_prompt(self, task_id: str) -> str:
        """Load task-specific intelligence extraction prompt from global prompts directory"""
        
        try:
            # Get prompts directory from web config
            prompts_dir = Path(self.web_config.get_prompts_dir()) / 'intelligence'
            
            # Load exact task ID prompt
            task_prompt_file = prompts_dir / f'{task_id}_intelligence.txt'
            
            if not task_prompt_file.exists():
                raise FileNotFoundError(f"Intelligence prompt not found: {task_prompt_file}")
            
            self.logger.debug(f"Loading intelligence prompt: {task_prompt_file}")
            return task_prompt_file.read_text(encoding='utf-8')
            
        except Exception as e:
            self.logger.error(f"Failed to load intelligence prompt for {task_id}: {str(e)}")
            raise IntelligenceExtractionError(f"Intelligence prompt loading failed: {str(e)}")
