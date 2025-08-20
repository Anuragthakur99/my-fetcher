"""Generic capture service for HTML and screenshot capture across all tasks"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from ..models.task_models import CaptureData


class CaptureService:
    """Service for capturing HTML and screenshots during task execution"""
    
    def __init__(self, session_id: str, logger):
        self.session_id = session_id
        self.logger = logger
        
        # Import web_config directly - always gets updated data
        from ..config.web_config import web_config
        self.web_config = web_config
    
    async def capture_element(
        self,
        browser_context,  # browser_use Agent's browser_context
        element_index: int,
        capture_type: str,
        output_dir: Path
    ) -> CaptureData:
        """
        Capture HTML and screenshot for specified element
        Generic version of capture_date_information for all task types
        
        Args:
            browser_context: Browser context from browser-use Agent
            element_index: Index of element to capture
            capture_type: Type of capture (date_navigation, program_list, etc.)
            output_dir: Directory to save capture files
            
        Returns:
            CaptureData: Captured HTML and screenshot information
        """
        try:
            self.logger.info(f"Starting element capture - Index: {element_index}, Type: {capture_type}")
            
            # Get current page and URL
            page = await browser_context.get_current_page()
            current_url = page.url
            
            # Get the element details from selector map
            selector_map = await browser_context.get_selector_map()
            if element_index not in selector_map:
                raise ValueError(f"Element index {element_index} not found in selector map")

            # Start with the selected element and move up to parent until HTML < 10,000
            current_node = selector_map[element_index]
            final_element = None
            final_html = ""
            
            while current_node is not None:
                try:
                    element_handle = await browser_context.get_locate_element(current_node)
                    inner_html = await element_handle.inner_html()
                    html_length = len(inner_html)
                    
                    self.logger.debug(f"Current element HTML length: {html_length}")
                    
                    if html_length <= 20000:
                        final_element = element_handle
                        final_html = inner_html
                    else:
                        break
                    
                    # Move to parent
                    current_node = current_node.parent
                    
                except Exception as e:
                    self.logger.debug(f"Error processing element: {str(e)}")
                    break
            
            # Handle case where no suitable parent found or no parent exists
            if final_element is None:
                # Use the original element as fallback
                final_element = await browser_context.get_locate_element(selector_map[element_index])
                final_html = await final_element.inner_html()
                self.logger.info("No parent with HTML < 10,000 found, using original element")
            
            # Generate file names based on capture type
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_filename = f"{capture_type}_{timestamp}.html"
            screenshot_filename = f"{capture_type}_{timestamp}.png"
            
            # Save HTML and screenshot to output directory
            html_file_path = output_dir / html_filename
            screenshot_file_path = output_dir / screenshot_filename
            
            # Capture screenshot
            final_screenshot = await final_element.screenshot()
            
            # Save files
            with open(html_file_path, "w", encoding="utf-8") as html_file:
                html_file.write(final_html)
            
            with open(screenshot_file_path, "wb") as screenshot_file:
                screenshot_file.write(final_screenshot)
            
            # Create capture data
            capture_data = CaptureData(
                html_content=final_html,
                screenshot_path=screenshot_file_path,
                element_selector=str(selector_map[element_index]),
                capture_timestamp=datetime.now(),
                additional_data={
                    "url": current_url,
                    "element_index": element_index,
                    "capture_type": capture_type,
                    "html_file_path": str(html_file_path),
                    "html_length": len(final_html)
                }
            )
            
            self.logger.info(f"Successfully captured {capture_type} element - HTML: {len(final_html)} chars")
            return capture_data
            
        except Exception as e:
            self.logger.error(f"Failed to capture element: {str(e)}")
            raise
