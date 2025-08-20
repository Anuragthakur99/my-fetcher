"""
Intelligent TV Schedule Scraper - Enhanced base class for LLM-generated scrapers
Focuses on "Store First, Extract Later" approach with comprehensive data collection
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from playwright.async_api import async_playwright, Browser, Page
from abc import ABC, abstractmethod

class IntelligentTVScraper(ABC):
    """
    Enhanced base class for LLM-generated TV schedule scrapers
    Implements "Store First, Extract Later" approach with comprehensive data collection
    """

    def __init__(self, channel_name: str, base_url: str):
        self.channel_name = channel_name
        self.base_url = base_url

        # Enhanced setup with organized data storage
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = Path(f"scraped_data/{self._clean_name(channel_name)}_{timestamp}")
        self.html_storage_dir = self.output_dir / "html_pages"
        self.screenshots_dir = self.output_dir / "screenshots"

        # Create all necessary directories
        for directory in [self.output_dir, self.html_storage_dir, self.screenshots_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        self.logger = self._setup_logger()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

        # Enhanced data storage structure
        self.collected_data = {
            'available_dates': [],
            'date_html_files': {},
            'program_metadata': {},
            'program_detail_data': {},
            'navigation_logs': []
        }
        self.stats = {
            'dates_discovered': 0,
            'dates_scraped': 0,
            'programs_found': 0,
            'program_details_extracted': 0,
            'html_pages_saved': 0,
            'errors': 0
        }

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"TVScraper_{self._clean_name(self.channel_name)}")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _clean_name(self, name: str) -> str:
        import re
        return re.sub(r'[^\w\-_]', '_', str(name))

    # ==================== UTILITY METHODS (Used by LLM-generated code) ====================

    async def open_browser(self, headless: bool = True) -> bool:
        """Initialize browser with enhanced configuration"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.page = await self.browser.new_page()
            self.page.set_default_timeout(30000)

            # Set user agent to avoid bot detection
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            self.logger.info("Browser initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Browser initialization failed: {e}")
            self.stats['errors'] += 1
            return False

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

    async def close_browser(self) -> None:
        """Close browser with proper cleanup"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            self.logger.info("Browser closed successfully")
        except Exception as e:
            self.logger.error(f"Browser cleanup failed: {e}")

    async def navigate_to_url(self, url: str, wait_for: str = 'domcontentloaded') -> bool:
        """Navigate to URL with retry logic and comprehensive error handling"""
        for attempt in range(3):
            try:
                self.logger.info(f"Navigating to: {url} (attempt {attempt + 1})")
                await self.page.goto(url, wait_until=wait_for, timeout=30000)
                await self.page.wait_for_timeout(2000)  # Buffer for dynamic content

                # Log navigation success
                self.collected_data['navigation_logs'].append({
                    'timestamp': datetime.now().isoformat(),
                    'action': 'navigate',
                    'url': url,
                    'success': True,
                    'attempt': attempt + 1
                })

                return True
            except Exception as e:
                self.logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                self.collected_data['navigation_logs'].append({
                    'timestamp': datetime.now().isoformat(),
                    'action': 'navigate',
                    'url': url,
                    'success': False,
                    'attempt': attempt + 1,
                    'error': str(e)
                })

                if attempt < 2:
                    await asyncio.sleep(2)
                else:
                    self.stats['errors'] += 1

        return False

    async def click(self, selector: str, wait_timeout: int = 10000) -> bool:
        """Enhanced click method with comprehensive error handling"""
        try:
            await self.page.wait_for_selector(selector, timeout=wait_timeout)
            await self.page.click(selector)
            await self.page.wait_for_timeout(1000)  # Buffer wait

            self.logger.info(f"Successfully clicked: {selector}")
            return True
        except Exception as e:
            self.logger.error(f"Click failed for selector '{selector}': {e}")
            self.stats['errors'] += 1
            return False

    async def wait_for_element(self, selector: str, timeout: int = 10000) -> bool:
        """Wait for element with proper timeout handling"""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            self.logger.debug(f"Element found: {selector}")
            return True
        except Exception as e:
            self.logger.debug(f"Element not found: {selector} - {e}")
            return False

    async def save_page_html(self, filename: str, page_type: str = "general") -> str:
        """Save current page HTML with metadata"""
        try:
            html_content = await self.page.content()
            current_url = self.page.url

            # Create filename with timestamp if not provided
            if not filename.endswith('.html'):
                filename = f"{filename}_{datetime.now().strftime('%H%M%S')}.html"

            file_path = self.html_storage_dir / filename

            # Save HTML with metadata header
            html_with_metadata = f"""<!-- 
            SCRAPED PAGE METADATA:
            URL: {current_url}
            Page Type: {page_type}
            Timestamp: {datetime.now().isoformat()}
            Channel: {self.channel_name}
            -->
            {html_content}"""

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_with_metadata)

            self.stats['html_pages_saved'] += 1
            self.logger.info(f"HTML saved: {filename}")

            return str(file_path)
        except Exception as e:
            self.logger.error(f"Failed to save HTML {filename}: {e}")
            self.stats['errors'] += 1
            return ""

    # ==================== ABSTRACT METHODS (Implemented by LLM) ====================

    @abstractmethod
    async def prelogin(self) -> bool:
        """
        Open the base URL and handle initial page load
        Should handle: cookies, popups, initial page state
        Returns: True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def login(self, credentials: Optional[Dict[str, str]] = None) -> bool:
        """
        Handle login process if required
        Args: credentials dict with username/password if needed
        Returns: True if login successful or not required, False if failed
        """
        pass

    @abstractmethod
    async def channel_navigation(self) -> bool:
        """
        Navigate to the specific channel end-to-end
        Should handle: channel selection, dropdowns, search, verification
        Returns: True if channel navigation successful, False otherwise
        """
        pass

    @abstractmethod
    async def collect_available_dates(self) -> List[str]:
        """
        Discover and collect all available dates on the website
        Should handle: date navigation, pagination, date range detection
        Returns: List of date identifiers/strings found on the site
        """
        pass

    @abstractmethod
    async def collect_date_html_pages(self, dates: List[str]) -> Dict[str, str]:
        """
        Navigate to each date and save the complete HTML page after scrolling
        Should handle: date navigation, full page scrolling, HTML saving
        Args: dates - List of date identifiers to process
        Returns: Dict mapping date_id -> saved_html_file_path
        """
        pass

    @abstractmethod
    async def program_extraction(self, date_html_files: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract program metadata and details from saved HTML pages

        For URL-based detail access:
        - Extract program metadata + detail URLs from saved HTML
        - Navigate to detail URLs and extract additional data
        - Save detail page HTML

        For selector-based detail access:
        - Navigate back to each date page
        - Extract program metadata
        - Click on each program for details
        - Extract detail data and save HTML
        - Handle return navigation

        Args: date_html_files - Dict mapping date_id -> html_file_path
        Returns: Dict with complete program data including details
        """
        pass

    # ==================== DATA MANAGEMENT METHODS ====================

    def store_available_dates(self, dates: List[str]) -> None:
        """Store discovered available dates"""
        self.collected_data['available_dates'] = dates
        self.stats['dates_discovered'] = len(dates)
        self.logger.info(f"Stored {len(dates)} available dates")

    def store_date_html_file(self, date_id: str, html_file_path: str) -> None:
        """Store mapping of date to its saved HTML file"""
        self.collected_data['date_html_files'][date_id] = html_file_path
        self.stats['dates_scraped'] += 1
        self.logger.info(f"Stored HTML file for date {date_id}: {html_file_path}")

    def store_program_metadata(self, date_id: str, programs: List[Dict]) -> None:
        """Store program metadata extracted from date pages"""
        if date_id not in self.collected_data['program_metadata']:
            self.collected_data['program_metadata'][date_id] = []

        # Clean and validate program data
        cleaned_programs = []
        for program in programs:
            if program.get('title'):  # Must have title
                cleaned_program = {
                    'title': str(program.get('title', '')).strip(),
                    'start_time': str(program.get('start_time', '')).strip(),
                    'end_time': str(program.get('end_time', '')).strip(),
                    'description': str(program.get('description', '')).strip(),
                    'genre': str(program.get('genre', '')).strip(),
                    'detail_url': str(program.get('detail_url', '')).strip(),
                    'program_id': program.get('program_id', f"{date_id}_{len(cleaned_programs)}")
                }
                cleaned_programs.append(cleaned_program)

        self.collected_data['program_metadata'][date_id].extend(cleaned_programs)
        self.stats['programs_found'] += len(cleaned_programs)
        self.logger.info(f"Stored {len(cleaned_programs)} programs for date {date_id}")

    def store_program_detail_data(self, program_id: str, detail_data: Dict, detail_html_path: str = "") -> None:
        """Store detailed program information"""
        self.collected_data['program_detail_data'][program_id] = {
            'detail_data': detail_data,
            'detail_html_file': detail_html_path,
            'extracted_at': datetime.now().isoformat()
        }
        self.stats['program_details_extracted'] += 1
        self.logger.info(f"Stored detail data for program {program_id}")

    async def save_results(self) -> str:
        """Save comprehensive results with enhanced structure"""
        try:
            results = {
                'metadata': {
                    'channel': self.channel_name,
                    'base_url': self.base_url,
                    'scraping_timestamp': datetime.now().isoformat(),
                    'stats': self.stats,
                    'output_directories': {
                        'main': str(self.output_dir),
                        'html_storage': str(self.html_storage_dir),
                        'screenshots': str(self.screenshots_dir)
                    }
                },
                'collected_data': self.collected_data
            }

            # Save main results file
            results_file = self.output_dir / f"{self._clean_name(self.channel_name)}_complete_results.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            # Save summary file for quick overview
            summary = {
                'channel': self.channel_name,
                'stats': self.stats,
                'available_dates': self.collected_data['available_dates'],
                'total_programs': sum(len(programs) for programs in self.collected_data['program_metadata'].values())
            }

            summary_file = self.output_dir / f"{self._clean_name(self.channel_name)}_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Results saved: {results_file}")
            self.logger.info(f"Summary saved: {summary_file}")

            return str(results_file)
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            self.stats['errors'] += 1
            return ""

    def print_stats(self) -> None:
        """Print comprehensive final statistics"""
        self.logger.info("=" * 50)
        self.logger.info("INTELLIGENT TV SCRAPER - FINAL RESULTS")
        self.logger.info("=" * 50)
        self.logger.info(f"Channel: {self.channel_name}")
        self.logger.info(f"Base URL: {self.base_url}")
        self.logger.info(f"Output Directory: {self.output_dir}")
        self.logger.info("-" * 30)
        self.logger.info("COLLECTION STATISTICS:")
        self.logger.info(f"  • Available Dates Discovered: {self.stats['dates_discovered']}")
        self.logger.info(f"  • Date Pages Scraped: {self.stats['dates_scraped']}")
        self.logger.info(f"  • Programs Found: {self.stats['programs_found']}")
        self.logger.info(f"  • Program Details Extracted: {self.stats['program_details_extracted']}")
        self.logger.info(f"  • HTML Pages Saved: {self.stats['html_pages_saved']}")
        self.logger.info(f"  • Errors Encountered: {self.stats['errors']}")
        self.logger.info("-" * 30)
        self.logger.info("DATA STORAGE:")
        self.logger.info(f"  • HTML Files: {self.html_storage_dir}")
        self.logger.info(f"  • Screenshots: {self.screenshots_dir}")
        self.logger.info("=" * 50)

    # ==================== MAIN EXECUTION WORKFLOW ====================

    async def execute_complete_workflow(self) -> Dict[str, Any]:
        """
        Execute the complete scraping workflow using the abstract methods
        This is the main orchestration method that calls all abstract methods in sequence
        """
        try:
            self.logger.info("Starting complete TV schedule scraping workflow...")

            # Step 1: Pre-login (open URL, handle initial setup)
            self.logger.info("Step 1: Pre-login and initial setup...")
            if not await self.prelogin():
                raise Exception("Pre-login failed")

            # Step 2: Login if required
            self.logger.info("Step 2: Login process...")
            if not await self.login():
                raise Exception("Login failed")

            # Step 3: Navigate to specific channel
            self.logger.info("Step 3: Channel navigation...")
            if not await self.channel_navigation():
                raise Exception("Channel navigation failed")

            # Step 4: Collect all available dates
            self.logger.info("Step 4: Collecting available dates...")
            available_dates = await self.collect_available_dates()
            if not available_dates:
                raise Exception("No dates found")
            self.store_available_dates(available_dates)

            # Step 5: Collect HTML pages for each date
            self.logger.info("Step 5: Collecting HTML pages for all dates...")
            date_html_files = await self.collect_date_html_pages(available_dates)
            if not date_html_files:
                raise Exception("No HTML pages collected")

            # Store the HTML file mappings
            for date_id, html_path in date_html_files.items():
                self.store_date_html_file(date_id, html_path)

            # Step 6: Extract program data and details
            self.logger.info("Step 6: Extracting program metadata and details...")
            program_data = await self.program_extraction(date_html_files)

            self.logger.info("Complete workflow executed successfully!")
            return {
                'success': True,
                'available_dates': available_dates,
                'date_html_files': date_html_files,
                'program_data': program_data,
                'stats': self.stats
            }

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            self.stats['errors'] += 1
            return {
                'success': False,
                'error': str(e),
                'stats': self.stats
            }

    async def run(self, headless: bool = True, credentials: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Main runner method with proper browser lifecycle management
        Args:
            headless: Whether to run browser in headless mode
            credentials: Optional login credentials if required
        Returns:
            Dict with execution results and statistics
        """
        try:
            # Initialize browser
            if not await self.open_browser(headless):
                raise Exception("Failed to initialize browser")

            # Execute the complete workflow
            workflow_result = await self.execute_complete_workflow()

            # Save results
            results_file = await self.save_results()

            # Print final statistics
            self.print_stats()

            return {
                'success': workflow_result['success'],
                'results_file': results_file,
                'stats': self.stats,
                'workflow_data': workflow_result
            }

        except Exception as e:
            self.logger.error(f"Scraping execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'stats': self.stats
            }
        finally:
            # Always cleanup browser
            await self.close_browser()
