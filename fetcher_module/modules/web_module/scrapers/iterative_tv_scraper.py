"""
Iterative TV Scraper Base Class

This base class supports step-by-step code generation and testing.
All methods have default implementations that can be overridden.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, Page


class TVScraperError(Exception):
    """Base exception with LLM-friendly messages"""
    def __init__(self, message: str, error_code: str, context: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(f"[{error_code}] {message}")


class ScraperConfig:
    """Centralized configuration for all scrapers"""
    def __init__(self, config_dict: Dict[str, Any] = None):
        config = config_dict or {}
        
        # Browser settings
        self.headless = config.get('headless', True)
        self.timeout = config.get('timeout', 30000)
        
        # Credentials
        self.credentials = config.get('credentials', {})
        
        # Date range for crawling
        self.from_date = config.get('from_date')  # MM/DD/YYYY
        self.to_date = config.get('to_date')      # MM/DD/YYYY
        
        # Channel configuration
        self.target_channels = config.get('target_channels', [])
        
        # Output settings
        self.output_dir = config.get('output_dir', './output')
        self.save_page_dumps = config.get('save_page_dumps', True)


class IterativeTVScraper:
    """
    Base class for iterative TV scraper development.
    
    All methods have default implementations that can be overridden
    during step-by-step code generation and testing.
    """
    
    def __init__(self, website_name: str, base_url: str, config: ScraperConfig = None):
        self.website_name = website_name
        self.base_url = base_url
        self.config = config or ScraperConfig()
        
        # Setup output directory
        self.output_dir = Path(self.config.output_dir) / website_name.lower().replace(' ', '_')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Browser session
        self._page = None
        
        # Setup logging
        self._setup_logging()
        
        self.logger.info(f"Initialized {self.__class__.__name__} for {website_name}")
    
    def _setup_logging(self):
        """Setup logging for the scraper"""
        log_file = self.output_dir / "scraper.log"
        
        # Clear existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @asynccontextmanager
    async def browser_session(self):
        """Browser session management with config settings"""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=self.config.headless)
        context = await browser.new_context()
        page = await context.new_page()
        page.set_default_timeout(self.config.timeout)
        
        try:
            self._page = page
            self.logger.info(f"Browser session started for {self.website_name}")
            yield page
        finally:
            await page.close()
            await context.close()
            await browser.close()
            await playwright.stop()
            self.logger.info("Browser session closed")
    
    async def save_page_dump(self, filename: str, metadata: Dict[str, Any] = None):
        """Save current page as HTML dump for later processing"""
        if not self.config.save_page_dumps or not self._page:
            return
        
        try:
            html_content = await self._page.content()
            html_file = self.output_dir / f"{filename}.html"
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            if metadata:
                metadata_file = self.output_dir / f"{filename}_metadata.json"
                metadata.update({
                    "timestamp": datetime.now().isoformat(),
                    "url": self._page.url,
                    "title": await self._page.title()
                })
                
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Page dump saved: {html_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save page dump: {str(e)}")
    
    # ==================== STEP 1: LOGIN METHODS ====================
    
    async def requires_login(self, page: Page) -> bool:
        """
        Check if website requires authentication.
        
        Args:
            page: Playwright Page object for browser operations
            
        DEFAULT IMPLEMENTATION: No login required
        OVERRIDE: When website needs authentication
        """
        self.logger.info("Default implementation: No login required")
        return False
    
    async def login(self, page: Page, credentials: Dict[str, str] = None) -> bool:
        """
        Handle website authentication.
        
        Args:
            page: Playwright Page object for browser operations
            credentials: Optional credentials dict. If None, uses self.config.credentials
            
        DEFAULT IMPLEMENTATION: No login needed
        OVERRIDE: When website requires authentication
        """
        if not await self.requires_login(page):
            self.logger.info("Login not required")
            return True
        
        self.logger.warning("Login required but not implemented")
        return False
    
    # ==================== STEP 2: CHANNEL METHODS ====================
    
    async def enumerate_channels(self, page: Page) -> List[str]:
        """
        Get all available channels on this website.
        
        Args:
            page: Playwright Page object for browser operations
            
        DEFAULT IMPLEMENTATION: Single channel (website name)
        OVERRIDE: When website has multiple channels
        """
        self.logger.info(f"Default implementation: Single channel [{self.website_name}]")
        return [self.website_name]
    
    async def navigate_to_channel(self, page: Page, channel_name: str) -> bool:
        """
        Navigate to a specific channel.
        
        Args:
            page: Playwright Page object for browser operations
            channel_name: Channel name from enumerate_channels() result
            
        DEFAULT IMPLEMENTATION: No navigation needed (single channel)
        OVERRIDE: When website has multiple channels
        """
        self.logger.info(f"Default implementation: No channel navigation needed for {channel_name}")
        return True
    
    # ==================== STEP 3: DATE METHODS ====================
    
    async def navigate_to_date(self, page: Page, date: str) -> bool:
        """
        Navigate to a specific date and save page dump.
        
        Args:
            page: Playwright Page object for browser operations
            date: Target date in MM/DD/YYYY format
            
        DEFAULT IMPLEMENTATION: Not implemented (must be overridden)
        OVERRIDE: Always (every website needs date navigation)
        """
        raise NotImplementedError(
            f"navigate_to_date must be implemented for {self.website_name}. "
            f"This method should navigate to date {date} (MM/DD/YYYY format) and save page dump."
        )
    
    # ==================== STEP 4: PROGRAM METHODS ====================
    
    async def has_program_details(self, page: Page) -> bool:
        """
        Check if website has clickable program details.
        
        Args:
            page: Playwright Page object for browser operations
            
        DEFAULT IMPLEMENTATION: No program details available
        OVERRIDE: When website has program detail pages
        """
        self.logger.info("Default implementation: No program details available")
        return False
    
    async def get_program_selectors(self, page: Page, date_html: str, date: str) -> List[Dict[str, str]]:
        """
        Extract program selectors/URLs from date page HTML.
        
        Args:
            page: Playwright Page object for browser operations
            date_html: HTML content of the date page
            date: Date in MM/DD/YYYY format
            
        Returns:
            List of program selectors/URLs
            
        DEFAULT IMPLEMENTATION: Empty list (no program details)
        OVERRIDE: When website has program detail pages
        """
        if not await self.has_program_details(page):
            self.logger.info("No program details available")
            return []
        
        self.logger.warning("Program details available but get_program_selectors not implemented")
        return []
    
    async def navigate_to_program(self, page: Page, program_selector: str, program_url: str = None, date: str = None) -> bool:
        """
        Navigate to individual program and save page dump.
        
        Args:
            page: Playwright Page object for browser operations
            program_selector: CSS selector for the program
            program_url: Direct URL to program (if available)
            date: Original date to return to after program navigation
            
        DEFAULT IMPLEMENTATION: Not implemented
        OVERRIDE: When website has program detail pages
        """
        if not await self.has_program_details(page):
            self.logger.info("No program details available")
            return False
        
        raise NotImplementedError(
            f"navigate_to_program must be implemented for {self.website_name} "
            f"when has_program_details() returns True"
        )
    
    async def has_downloads(self, page: Page) -> bool:
        """
        Check if website has downloadable program files.
        
        Args:
            page: Playwright Page object for browser operations
            
        DEFAULT IMPLEMENTATION: No downloads available
        OVERRIDE: When website has download functionality
        """
        self.logger.info("Default implementation: No downloads available")
        return False
    
    async def download_files(self, page: Page, date: str, date_html: str = None) -> List[str]:
        """
        Download program files for a specific date.
        
        Args:
            page: Playwright Page object for browser operations
            date: Date in MM/DD/YYYY format
            date_html: HTML content of the date page (optional)
            
        Returns:
            List of downloaded file paths
            
        DEFAULT IMPLEMENTATION: Empty list (no downloads)
        OVERRIDE: When website has download functionality
        """
        if not await self.has_downloads(page):
            self.logger.info("No downloads available")
            return []
        
        self.logger.warning("Downloads available but download_files not implemented")
        return []
