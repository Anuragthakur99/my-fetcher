"""
Smart TV Scraper Base Class - Minimal, LLM-Orchestrated Design
Senior Software Architect Approach: Let LLM decide the flow, provide minimal utilities
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from playwright.async_api import async_playwright, Browser, Page
from abc import ABC, abstractmethod


class SmartTVScraper(ABC):
    """
    Minimal base class for LLM-generated TV schedule scrapers.
    Philosophy: Provide utilities, let LLM orchestrate the workflow.
    """
    
    def __init__(self, channel_name: str, base_url: str):
        self.channel_name = channel_name
        self.base_url = base_url
        
        # Minimal setup - let LLM decide structure
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_id = f"{self._clean_name(channel_name)}_{timestamp}"
        self.output_dir = Path(f"output/{self.session_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Simple data storage - LLM decides what to store
        self.data_store = {}
        self.logger = self._setup_logger()
        
        # Browser instances
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    def _setup_logger(self) -> logging.Logger:
        """Setup minimal logger"""
        logger = logging.getLogger(f"SmartTVScraper_{self.session_id}")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def _clean_name(self, name: str) -> str:
        """Clean name for filesystem usage"""
        import re
        return re.sub(r'[^\w\-_]', '_', str(name))
    
    # ==================== BROWSER UTILITIES ====================
    
    async def init_browser(self, headless: bool = True, **kwargs) -> bool:
        """Initialize browser with minimal configuration"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
            )
            
            # Create page with realistic settings
            self.page = await self.browser.new_page()
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            self.page.set_default_timeout(30000)
            self.logger.info("Browser initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Browser initialization failed: {e}")
            return False
    
    async def close_browser(self) -> None:
        """Clean browser shutdown"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.logger.info("Browser closed successfully")
        except Exception as e:
            self.logger.error(f"Browser cleanup error: {e}")
    
    # ==================== NAVIGATION UTILITIES ====================
    
    async def navigate(self, url: str, wait_for: str = 'domcontentloaded', timeout: int = 30000) -> bool:
        """Navigate to URL with retry logic"""
        for attempt in range(3):
            try:
                self.logger.info(f"Navigating to: {url} (attempt {attempt + 1})")
                await self.page.goto(url, wait_until=wait_for, timeout=timeout)
                await self.page.wait_for_timeout(2000)  # Buffer for dynamic content
                return True
            except Exception as e:
                self.logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    await asyncio.sleep(2)
        return False
    
    async def click_element(self, selector: str, timeout: int = 10000) -> bool:
        """Click element with error handling"""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            await self.page.click(selector)
            await self.page.wait_for_timeout(1000)
            self.logger.debug(f"Clicked: {selector}")
            return True
        except Exception as e:
            self.logger.debug(f"Click failed for '{selector}': {e}")
            return False
    
    async def fill_input(self, selector: str, text: str, timeout: int = 10000) -> bool:
        """Fill input field"""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            await self.page.fill(selector, text)
            self.logger.debug(f"Filled '{selector}' with: {text}")
            return True
        except Exception as e:
            self.logger.debug(f"Fill failed for '{selector}': {e}")
            return False
    
    async def wait_for_selector(self, selector: str, timeout: int = 10000) -> bool:
        """Wait for element to appear"""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False
    
    async def get_current_url(self) -> str:
        """Get current page URL"""
        return self.page.url if self.page else ""
    
    async def scroll_page(self, direction: str = "down", pixels: int = 1000) -> None:
        """Scroll page in specified direction"""
        try:
            if direction == "down":
                await self.page.evaluate(f"window.scrollBy(0, {pixels})")
            elif direction == "up":
                await self.page.evaluate(f"window.scrollBy(0, -{pixels})")
            elif direction == "bottom":
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            elif direction == "top":
                await self.page.evaluate("window.scrollTo(0, 0)")
            await self.page.wait_for_timeout(1000)
        except Exception as e:
            self.logger.debug(f"Scroll failed: {e}")
    
    # ==================== DATA UTILITIES ====================
    
    def store_data(self, key: str, data: Any) -> None:
        """Store data in the data store"""
        self.data_store[key] = data
        self.logger.debug(f"Stored data for key: {key}")
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Retrieve data from the data store"""
        return self.data_store.get(key, default)
    
    async def save_html(self, filename: str, metadata: Dict[str, Any] = None) -> str:
        """Save current page HTML with optional metadata"""
        try:
            html_content = await self.page.content()
            current_url = self.page.url
            
            # Add .html extension if not present
            if not filename.endswith('.html'):
                filename = f"{filename}.html"
            
            file_path = self.output_dir / filename
            
            # Create HTML with metadata header
            metadata_header = f"""<!--
            SCRAPER METADATA:
            URL: {current_url}
            Timestamp: {datetime.now().isoformat()}
            Channel: {self.channel_name}
            Session: {self.session_id}
            {f"Custom: {json.dumps(metadata, indent=2)}" if metadata else ""}
            -->
            """
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(metadata_header + html_content)
            
            self.logger.info(f"HTML saved: {filename}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save HTML '{filename}': {e}")
            return ""
    
    async def save_screenshot(self, filename: str) -> str:
        """Save screenshot of current page"""
        try:
            if not filename.endswith('.png'):
                filename = f"{filename}.png"
            
            file_path = self.output_dir / filename
            await self.page.screenshot(path=str(file_path), full_page=True)
            self.logger.info(f"Screenshot saved: {filename}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save screenshot '{filename}': {e}")
            return ""
    
    def save_json(self, filename: str, data: Any) -> str:
        """Save data as JSON file"""
        try:
            if not filename.endswith('.json'):
                filename = f"{filename}.json"
            
            file_path = self.output_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"JSON saved: {filename}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save JSON '{filename}': {e}")
            return ""
    
    # ==================== EXTRACTION UTILITIES ====================
    
    async def extract_elements(self, selector: str, attribute: str = "textContent") -> List[str]:
        """Extract data from multiple elements"""
        try:
            elements = await self.page.query_selector_all(selector)
            results = []
            
            for element in elements:
                if attribute == "textContent":
                    value = await element.text_content()
                elif attribute == "innerHTML":
                    value = await element.inner_html()
                else:
                    value = await element.get_attribute(attribute)
                
                if value and value.strip():
                    results.append(value.strip())
            
            return results
            
        except Exception as e:
            self.logger.debug(f"Element extraction failed for '{selector}': {e}")
            return []
    
    async def extract_element(self, selector: str, attribute: str = "textContent") -> Optional[str]:
        """Extract data from single element"""
        try:
            element = await self.page.query_selector(selector)
            if not element:
                return None
            
            if attribute == "textContent":
                value = await element.text_content()
            elif attribute == "innerHTML":
                value = await element.inner_html()
            else:
                value = await element.get_attribute(attribute)
            
            return value.strip() if value else None
            
        except Exception as e:
            self.logger.debug(f"Single element extraction failed for '{selector}': {e}")
            return None
    
    # ==================== ABSTRACT METHOD ====================
    
    @abstractmethod
    async def execute_scraping_workflow(self) -> Dict[str, Any]:
        """
        Main scraping workflow - implemented by LLM-generated code.
        
        This method should:
        1. Use the provided utilities to navigate and extract data
        2. Store data using store_data() method
        3. Save HTML/screenshots as needed using save_html()/save_screenshot()
        4. Return a results dictionary
        
        The LLM decides:
        - Navigation flow and sequence
        - What data to extract and when
        - How to handle different website structures
        - Error handling strategies
        - Data storage structure
        
        Returns:
            Dict containing scraping results and metadata
        """
        pass
    
    # ==================== MAIN RUNNER ====================
    
    async def run(self, headless: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Main execution method with proper lifecycle management
        """
        start_time = datetime.now()
        
        try:
            # Initialize browser
            if not await self.init_browser(headless=headless, **kwargs):
                raise Exception("Failed to initialize browser")
            
            # Execute the LLM-generated workflow
            self.logger.info("Starting scraping workflow...")
            workflow_result = await self.execute_scraping_workflow()
            
            # Save final results
            final_results = {
                'success': True,
                'channel': self.channel_name,
                'base_url': self.base_url,
                'session_id': self.session_id,
                'execution_time': str(datetime.now() - start_time),
                'timestamp': datetime.now().isoformat(),
                'workflow_result': workflow_result,
                'data_store': self.data_store,
                'output_directory': str(self.output_dir)
            }
            
            # Save results to file
            results_file = self.save_json('final_results', final_results)
            
            self.logger.info(f"Scraping completed successfully in {datetime.now() - start_time}")
            self.logger.info(f"Results saved to: {results_file}")
            
            return final_results
            
        except Exception as e:
            error_result = {
                'success': False,
                'error': str(e),
                'channel': self.channel_name,
                'base_url': self.base_url,
                'session_id': self.session_id,
                'execution_time': str(datetime.now() - start_time),
                'timestamp': datetime.now().isoformat(),
                'data_store': self.data_store,
                'output_directory': str(self.output_dir)
            }
            
            self.logger.error(f"Scraping failed: {e}")
            self.save_json('error_results', error_result)
            
            return error_result
            
        finally:
            await self.close_browser()
