import asyncio
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from bs4 import BeautifulSoup

from smart_tv_scraper import IntelligentTVScraper

class SpotvPrime2Scraper(IntelligentTVScraper):
    """
    Production-ready TV schedule scraper for SPOTV Prime 2
    Auto-generated using intelligent analysis of https://www.spotvprime.co.kr/schedule
    
    This scraper runs daily in production to collect:
    - All available dates on the website
    - All programs for each date
    - Detailed information for each program
    """
    
    def __init__(self):
        super().__init__("SPOTV Prime 2", "https://www.spotvprime.co.kr/schedule")
        self.logger.info(f"Initialized scraper for {self.channel_name}")
    
    # ==================== STEP 1: FOUNDATION & CHANNEL NAVIGATION ====================
    
    async def prelogin(self) -> bool:
        """
        Open the SPOTV Prime website and prepare for channel navigation.
        
        This method navigates to the base schedule URL and ensures the page
        is properly loaded before proceeding to channel selection.
        
        Returns:
            bool: True if prelogin was successful, False otherwise
        """
        try:
            self.logger.info("Starting prelogin process for SPOTV Prime")
            
            # Navigate directly to the schedule page as per intelligence data
            schedule_url = "https://www.spotvprime.co.kr/schedule"
            self.logger.info(f"Navigating to schedule page: {schedule_url}")
            
            success = await self.navigate_to_url(schedule_url)
            if not success:
                self.logger.error("Failed to navigate to schedule page")
                return False
            
            # Wait for the page to fully load - ensure channel selection is available
            try:
                # Wait for channel selection area to be visible
                await self.wait_for_element("div.channel_type", 5000)
                self.logger.info("Schedule page loaded successfully with channel options visible")
                return True
            except Exception as e:
                self.logger.error(f"Failed to detect channel selection area: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"Prelogin process failed: {e}")
            return False

    async def login(self, credentials: Optional[Dict[str, str]] = None) -> bool:
        """
        Handle login process if required.
        
        For SPOTV Prime, no login is required to access the schedule.
        This method is implemented for compatibility with the base class.
        
        Args:
            credentials: Optional dictionary with login credentials
            
        Returns:
            bool: Always returns True as no login is required
        """
        # No login required for SPOTV Prime schedule
        self.logger.info("No login required for SPOTV Prime schedule")
        return True

    async def channel_navigation(self) -> bool:
        """
        Navigate to the SPOTV Prime 2 channel page.
        
        This method uses intelligence-driven approach to navigate to the target channel:
        1. First attempts URL-based navigation (adding ?ch=prime2 parameter)
        2. Falls back to clicking the channel logo if URL navigation fails
        
        Returns:
            bool: True if navigation to SPOTV Prime 2 was successful, False otherwise
        """
        try:
            self.logger.info("Starting navigation to SPOTV Prime 2 channel")
            
            # Check if we're already on the Prime 2 channel
            current_url = await self.page.url()
            if "?ch=prime2" in current_url:
                self.logger.info("Already on SPOTV Prime 2 channel page")
                return True
            
            # URL-FIRST APPROACH: Direct navigation with channel parameter
            direct_url = "https://www.spotvprime.co.kr/schedule?ch=prime2"
            self.logger.info(f"Attempting direct URL navigation to: {direct_url}")
            
            success = await self.navigate_to_url(direct_url)
            if success:
                # Verify we're on the correct channel page by checking URL
                current_url = await self.page.url()
                if "?ch=prime2" in current_url:
                    self.logger.info("Successfully navigated to SPOTV Prime 2 via direct URL")
                    return True
                else:
                    self.logger.warning("URL navigation didn't result in expected channel URL")
            
            # FALLBACK: Selector-based navigation
            self.logger.info("Falling back to selector-based navigation")
            
            # Primary selector from intelligence data
            prime2_logo_selector = "div.channel_type > div:nth-child(2) > p > img"
            
            # Fallback selectors if primary fails
            fallback_selectors = [
                "img[src*='Prime2_logo_channel']",
                "img[alt*='Prime2']",
                "//div[@class='channel_type']/div[2]/p/img"  # XPath selector
            ]
            
            # Try primary selector first
            try:
                await self.wait_for_element(prime2_logo_selector, 3000)
                await self.click(prime2_logo_selector)
                
                # Wait for URL to update with channel parameter
                await self.page.wait_for_url("**?ch=prime2**", timeout=5000)
                self.logger.info("Successfully navigated to SPOTV Prime 2 via logo click")
                return True
            except Exception as e:
                self.logger.warning(f"Primary selector navigation failed: {e}")
                
                # Try fallback selectors
                for selector in fallback_selectors:
                    try:
                        self.logger.info(f"Trying fallback selector: {selector}")
                        await self.wait_for_element(selector, 3000)
                        await self.click(selector)
                        
                        # Wait for URL to update with channel parameter
                        await self.page.wait_for_url("**?ch=prime2**", timeout=5000)
                        self.logger.info(f"Successfully navigated using fallback selector: {selector}")
                        return True
                    except Exception as fallback_error:
                        self.logger.warning(f"Fallback selector failed: {fallback_error}")
            
            self.logger.error("All navigation methods to SPOTV Prime 2 failed")
            return False
            
        except Exception as e:
            self.logger.error(f"Channel navigation failed: {e}")
            return False
    
    # ==================== STEP 2: DATE DISCOVERY & HTML COLLECTION ====================
    
    async def collect_available_dates(self) -> List[str]:
        """
        Discover all available dates on the SPOTV Prime 2 schedule website.
        
        This method uses multiple strategies to find available dates:
        1. First checks visible date tabs in the schedule header
        2. Then uses navigation arrows to discover additional weeks
        3. Finally uses the calendar picker to find all available dates in current month
        
        Returns:
            List[str]: List of date identifiers in 'YYYY-MM-DD' format
        """
        try:
            self.logger.info("Starting to collect available dates for SPOTV Prime 2")
            available_dates = set()  # Using set to avoid duplicates
            
            # First, collect visible dates from the date navigation bar
            try:
                self.logger.info("Collecting visible dates from date navigation bar")
                date_items = await self.page.query_selector_all("article.schedule_header > div.date_item")
                
                for date_item in date_items:
                    try:
                        # Extract date text (format: "M/DD")
                        date_text_element = await date_item.query_selector("div")
                        if date_text_element:
                            date_text = await date_text_element.text_content()
                            date_text = date_text.strip()
                            
                            # Get the current year from the date title
                            date_title_element = await self.page.query_selector("article.date_selector > div.date_title")
                            full_date = await date_title_element.text_content() if date_title_element else ""
                            
                            # Extract year from full date (format: "YYYY/MM/DD")
                            year = full_date.split('/')[0].strip() if full_date else str(datetime.now().year)
                            
                            # Convert M/DD format to YYYY-MM-DD
                            if '/' in date_text:
                                month, day = date_text.split('/')
                                formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                                available_dates.add(formatted_date)
                    except Exception as e:
                        self.logger.warning(f"Failed to extract date from tab: {e}")
                
                self.logger.info(f"Found {len(available_dates)} dates in visible date tabs")
            except Exception as e:
                self.logger.warning(f"Failed to collect dates from navigation bar: {e}")
            
            # Next, use date navigation arrows to discover more weeks
            # We'll navigate forward and backward up to 4 weeks each direction
            try:
                self.logger.info("Using navigation arrows to discover additional weeks")
                original_dates = set(available_dates)  # Remember initial dates
                
                # Navigate forward up to 4 weeks
                for _ in range(4):
                    try:
                        next_arrow = await self.page.query_selector("div.btn.date_next")
                        if next_arrow:
                            await next_arrow.click()
                            await self.page.wait_for_timeout(1000)  # Wait for AJAX update
                            
                            # Collect dates from the new week
                            date_items = await self.page.query_selector_all("article.schedule_header > div.date_item")
                            for date_item in date_items:
                                date_text_element = await date_item.query_selector("div")
                                if date_text_element:
                                    date_text = await date_text_element.text_content()
                                    date_text = date_text.strip()
                                    
                                    # Get current year from date title
                                    date_title_element = await self.page.query_selector("article.date_selector > div.date_title")
                                    full_date = await date_title_element.text_content() if date_title_element else ""
                                    year = full_date.split('/')[0].strip() if full_date else str(datetime.now().year)
                                    
                                    # Convert M/DD format to YYYY-MM-DD
                                    if '/' in date_text:
                                        month, day = date_text.split('/')
                                        formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                                        available_dates.add(formatted_date)
                    except Exception as e:
                        self.logger.warning(f"Failed during forward navigation: {e}")
                        break
                
                # Return to original view
                while True:
                    current_dates = set()
                    date_items = await self.page.query_selector_all("article.schedule_header > div.date_item")
                    
                    for date_item in date_items:
                        try:
                            date_text_element = await date_item.query_selector("div")
                            if date_text_element:
                                date_text = await date_text_element.text_content()
                                date_text = date_text.strip()
                                current_dates.add(date_text)
                        except Exception:
                            pass
                    
                    # Check if we're back to original dates
                    if any(date in original_dates for date in current_dates):
                        break
                        
                    prev_arrow = await self.page.query_selector("div.btn.date_prev")
                    if prev_arrow:
                        await prev_arrow.click()
                        await self.page.wait_for_timeout(1000)
                    else:
                        break
                
                # Navigate backward up to 4 weeks
                for _ in range(4):
                    try:
                        prev_arrow = await self.page.query_selector("div.btn.date_prev")
                        if prev_arrow:
                            await prev_arrow.click()
                            await self.page.wait_for_timeout(1000)  # Wait for AJAX update
                            
                            # Collect dates from the new week
                            date_items = await self.page.query_selector_all("article.schedule_header > div.date_item")
                            for date_item in date_items:
                                date_text_element = await date_item.query_selector("div")
                                if date_text_element:
                                    date_text = await date_text_element.text_content()
                                    date_text = date_text.strip()
                                    
                                    # Get current year from date title
                                    date_title_element = await self.page.query_selector("article.date_selector > div.date_title")
                                    full_date = await date_title_element.text_content() if date_title_element else ""
                                    year = full_date.split('/')[0].strip() if full_date else str(datetime.now().year)
                                    
                                    # Convert M/DD format to YYYY-MM-DD
                                    if '/' in date_text:
                                        month, day = date_text.split('/')
                                        formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                                        available_dates.add(formatted_date)
                    except Exception as e:
                        self.logger.warning(f"Failed during backward navigation: {e}")
                        break
                
                self.logger.info(f"Found {len(available_dates)} dates after using navigation arrows")
            except Exception as e:
                self.logger.warning(f"Failed to navigate through weeks: {e}")
            
            # Finally, use calendar picker to find all available dates in current month
            try:
                self.logger.info("Using calendar picker to discover additional dates")
                
                # Click calendar icon to open date picker
                calendar_icon = await self.page.query_selector("i.calender_icon")
                if calendar_icon:
                    await calendar_icon.click()
                    await self.page.wait_for_timeout(1000)  # Wait for calendar to appear
                    
                    # Get all day cells from calendar
                    day_cells = await self.page.query_selector_all("div.datepicker_calendar span.cell.day:not(.blank)")
                    
                    # Get current month/year from calendar header
                    month_year_text = await self.page.query_selector("span.day__month_btn")
                    month_year = await month_year_text.text_content() if month_year_text else ""
                    
                    # Parse month and year
                    if month_year:
                        try:
                            month_name, year = month_year.split()
                            month_map = {
                                "January": "01", "February": "02", "March": "03", "April": "04",
                                "May": "05", "June": "06", "July": "07", "August": "08",
                                "September": "09", "October": "10", "November": "11", "December": "12"
                            }
                            month = month_map.get(month_name, "01")
                            
                            # Extract dates from calendar
                            for day_cell in day_cells:
                                day_text = await day_cell.text_content()
                                day = day_text.strip().zfill(2)
                                formatted_date = f"{year}-{month}-{day}"
                                available_dates.add(formatted_date)
                        except Exception as e:
                            self.logger.warning(f"Failed to parse month/year from calendar: {e}")
                    
                    # Close calendar by clicking outside
                    await self.page.click("article.date_selector")
                    
                    self.logger.info(f"Found {len(available_dates)} dates after using calendar picker")
            except Exception as e:
                self.logger.warning(f"Failed to use calendar picker: {e}")
            
            # Convert set to sorted list
            available_dates_list = sorted(list(available_dates))
            
            if available_dates_list:
                self.logger.info(f"Successfully collected {len(available_dates_list)} unique dates")
                self.store_available_dates(available_dates_list)
                return available_dates_list
            else:
                self.logger.warning("No dates found, using fallback strategy")
                return self._generate_fallback_dates()
                
        except Exception as e:
            self.logger.error(f"Failed to collect available dates: {e}")
            return self._generate_fallback_dates()

    async def collect_date_html_pages(self, dates: List[str]) -> Dict[str, str]:
        """
        Navigate to each date and save complete HTML pages for SPOTV Prime 2 schedule.
        
        This method implements a STORE-FIRST approach:
        1. Navigate to each date using the most efficient method
        2. Save the complete HTML page for later processing
        3. Store the mapping between date and saved HTML file path
        
        Args:
            dates: List of date identifiers in 'YYYY-MM-DD' format
            
        Returns:
            Dict[str, str]: Mapping of date_id -> saved_html_file_path
        """
        self.logger.info(f"Starting to collect HTML pages for {len(dates)} dates")
        date_html_files = {}
        
        try:
            # First, navigate to the schedule page if not already there
            current_url = await self.page.url()
            if "schedule?ch=prime2" not in current_url:
                self.logger.info("Navigating to SPOTV Prime 2 schedule page")
                await self.navigate_to_url("https://www.spotvprime.co.kr/schedule?ch=prime2")
                await self.page.wait_for_timeout(3000)  # Wait for page to load
            
            # Process each date
            for date_id in dates:
                try:
                    self.logger.info(f"Processing date: {date_id}")
                    
                    # Convert YYYY-MM-DD to components
                    try:
                        year, month, day = date_id.split('-')
                        month = month.lstrip('0')  # Remove leading zero
                        day = day.lstrip('0')      # Remove leading zero
                        date_format_for_tab = f"{month}/{day}"  # Format for date tabs: M/DD
                        date_format_for_title = f"{year}/{month.zfill(2)}/{day.zfill(2)}"  # Format for date title: YYYY/MM/DD
                    except Exception as e:
                        self.logger.warning(f"Failed to parse date {date_id}: {e}")
                        continue
                    
                    # Strategy 1: Check if date is already visible in date tabs
                    date_found = False
                    try:
                        self.logger.info(f"Looking for date tab with text: {date_format_for_tab}")
                        date_items = await self.page.query_selector_all("article.schedule_header > div.date_item")
                        
                        for date_item in date_items:
                            date_text_element = await date_item.query_selector("div")
                            if date_text_element:
                                date_text = await date_text_element.text_content()
                                date_text = date_text.strip()
                                
                                if date_text == date_format_for_tab:
                                    self.logger.info(f"Found date tab for {date_format_for_tab}, clicking it")
                                    await date_item.click()
                                    await self.page.wait_for_timeout(2000)  # Wait for AJAX content update
                                    
                                    # Verify date selection was successful by checking date title
                                    date_title_element = await self.page.query_selector("article.date_selector > div.date_title")
                                    if date_title_element:
                                        title_text = await date_title_element.text_content()
                                        title_text = title_text.strip()
                                        
                                        if date_format_for_title in title_text:
                                            date_found = True
                                            self.logger.info(f"Successfully navigated to date {date_id}")
                                            break
                        
                        if not date_found:
                            self.logger.info(f"Date {date_format_for_tab} not found in visible tabs")
                    except Exception as e:
                        self.logger.warning(f"Error checking visible date tabs: {e}")
                    
                    # Strategy 2: If date not found in visible tabs, use calendar picker
                    if not date_found:
                        try:
                            self.logger.info(f"Using calendar picker to navigate to date {date_id}")
                            
                            # Click calendar icon
                            calendar_icon = await self.page.query_selector("i.calender_icon")
                            if calendar_icon:
                                await calendar_icon.click()
                                await self.page.wait_for_timeout(1000)  # Wait for calendar to appear
                                
                                # Navigate to correct month/year if needed
                                month_year_text = await self.page.query_selector("span.day__month_btn")
                                if month_year_text:
                                    current_month_year = await month_year_text.text_content()
                                    
                                    # Map month number to name
                                    month_names = {
                                        "1": "January", "2": "February", "3": "March", "4": "April",
                                        "5": "May", "6": "June", "7": "July", "8": "August",
                                        "9": "September", "10": "October", "11": "November", "12": "December"
                                    }
                                    
                                    target_month_year = f"{month_names.get(month, 'January')} {year}"
                                    
                                    # If we need to change month/year
                                    if current_month_year != target_month_year:
                                        # Click on month/year to open month selector
                                        await month_year_text.click()
                                        await self.page.wait_for_timeout(500)
                                        
                                        # Select target month
                                        month_cells = await self.page.query_selector_all("div.datepicker_calendar span.cell.month")
                                        for month_cell in month_cells:
                                            month_name = await month_cell.text_content()
                                            if month_name.strip() == month_names.get(month, "January"):
                                                await month_cell.click()
                                                await self.page.wait_for_timeout(500)
                                                break
                                
                                # Now select the day
                                day_cells = await self.page.query_selector_all("div.datepicker_calendar span.cell.day:not(.blank)")
                                for day_cell in day_cells:
                                    day_text = await day_cell.text_content()
                                    if day_text.strip() == day.lstrip('0'):  # Remove leading zero for comparison
                                        await day_cell.click()
                                        await self.page.wait_for_timeout(2000)  # Wait for content update
                                        
                                        # Verify date selection was successful
                                        date_title_element = await self.page.query_selector("article.date_selector > div.date_title")
                                        if date_title_element:
                                            title_text = await date_title_element.text_content()
                                            title_text = title_text.strip()
                                            
                                            if date_format_for_title in title_text:
                                                date_found = True
                                                self.logger.info(f"Successfully navigated to date {date_id} using calendar")
                                                break
                        except Exception as e:
                            self.logger.warning(f"Failed to use calendar picker for date {date_id}: {e}")
                    
                    # If we successfully navigated to the date, save the HTML
                    if date_found:
                        # Scroll to ensure all content is loaded
                        await self.page.evaluate("window.scrollTo(0, 0)")  # Start at top
                        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")  # Scroll to bottom
                        await self.page.wait_for_timeout(1000)  # Wait for any lazy-loaded content
                        
                        # Save the HTML page
                        html_file_path = await self.save_page_html(f"spotv_prime2_schedule_{date_id}", "date_page")
                        
                        if html_file_path:
                            self.store_date_html_file(date_id, html_file_path)
                            date_html_files[date_id] = html_file_path
                            self.logger.info(f"Successfully saved HTML for date {date_id}")
                        else:
                            self.logger.error(f"Failed to save HTML for date {date_id}")
                    else:
                        self.logger.error(f"Could not navigate to date {date_id}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to process date {date_id}: {e}")
                    continue
            
            self.logger.info(f"Successfully collected HTML for {len(date_html_files)} out of {len(dates)} dates")
            return date_html_files
            
        except Exception as e:
            self.logger.error(f"Error in collect_date_html_pages: {e}")
            return date_html_files
    
    def _generate_fallback_dates(self) -> List[str]:
        """
        Generate fallback date range if date discovery fails.
        
        Returns:
            List[str]: List of dates in YYYY-MM-DD format for the next 14 days
        """
        dates = []
        today = datetime.now()
        
        # Generate dates for current week and next week (14 days total)
        for i in range(14):
            date = today + timedelta(days=i)
            dates.append(date.strftime('%Y-%m-%d'))
        
        self.logger.info(f"Generated {len(dates)} fallback dates")
        return dates
    
    # ==================== STEP 3: PROGRAM EXTRACTION & DETAILS ====================
    
    async def program_extraction(self, date_html_files: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract program metadata from saved HTML pages for SPOTV Prime 2 schedule.
        
        This method processes the saved HTML files from the previous step to extract
        all program information. Based on intelligence data, this site does not have
        clickable program details, so we use a pure HTML parsing approach.
        
        Args:
            date_html_files: Dictionary mapping date IDs to saved HTML file paths
            
        Returns:
            Dict containing:
            - programs_by_date: Dictionary mapping date IDs to lists of program data
            - total_programs: Total number of programs extracted
        """
        try:
            self.logger.info(f"Starting program extraction for {len(date_html_files)} dates")
            
            extraction_results = {
                'programs_by_date': {},
                'total_programs': 0
            }
            
            # Process each date's HTML file
            for date_id, html_file_path in date_html_files.items():
                try:
                    self.logger.info(f"Processing programs for date {date_id} from {html_file_path}")
                    
                    # Read the HTML file
                    with open(html_file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    # Extract programs from the HTML content
                    programs = self._extract_programs_from_html(html_content, date_id)
                    
                    if programs:
                        # Store the programs for this date
                        extraction_results['programs_by_date'][date_id] = programs
                        extraction_results['total_programs'] += len(programs)
                        
                        # Store in the base class for persistence
                        self.store_program_metadata(date_id, programs)
                        
                        self.logger.info(f"Successfully extracted {len(programs)} programs for date {date_id}")
                    else:
                        self.logger.warning(f"No programs found for date {date_id}")
                
                except Exception as e:
                    self.logger.error(f"Failed to process HTML for date {date_id}: {e}")
                    continue
            
            self.logger.info(f"Program extraction completed: {extraction_results['total_programs']} total programs extracted")
            return extraction_results
            
        except Exception as e:
            self.logger.error(f"Program extraction failed: {e}")
            return {
                'programs_by_date': {},
                'total_programs': 0,
                'error': str(e)
            }

    def _extract_programs_from_html(self, html_content: str, date_id: str) -> List[Dict[str, Any]]:
        """
        Extract program data from HTML content for a specific date.
        
        Args:
            html_content: HTML content of the page
            date_id: Date identifier in YYYY-MM-DD format
            
        Returns:
            List of program dictionaries with extracted metadata
        """
        try:
            from bs4 import BeautifulSoup
            import hashlib
            import re
            
            soup = BeautifulSoup(html_content, 'html.parser')
            programs = []
            
            # Extract date information from the page
            date_title_element = soup.select_one("article.date_selector > div.date_title")
            page_date = date_title_element.text.strip() if date_title_element else ""
            
            # Find all program items in the schedule body
            program_items = soup.select("article.schedule_body > div.schedule_item")
            
            # Extract broadcast type legend for reference
            broadcast_types = self._extract_broadcast_types(soup)
            
            # Extract age rating legend for reference
            age_ratings = self._extract_age_ratings(soup)
            
            for index, item in enumerate(program_items):
                try:
                    # Extract basic program data
                    start_time = self._safe_extract_text(item, ".column1.cell")
                    title = self._safe_extract_text(item, ".column4.cell")
                    
                    # Skip if we don't have essential data
                    if not start_time or not title:
                        continue
                    
                    # Extract broadcast type (live/original/rebroadcast)
                    broadcast_type_element = item.select_one(".column2.cell")
                    broadcast_type = ""
                    if broadcast_type_element:
                        # Check which badge class is present
                        if "badge" in broadcast_type_element.get("class", []):
                            for badge_class in broadcast_type_element.get("class", []):
                                if badge_class in ["live", "air", "replay"]:
                                    broadcast_type = broadcast_types.get(badge_class, badge_class)
                                    break
                    
                    # Extract age rating
                    age_rating_element = item.select_one(".column3.cell")
                    age_rating = ""
                    if age_rating_element:
                        # Check which badge class is present
                        if "badge" in age_rating_element.get("class", []):
                            for badge_class in age_rating_element.get("class", []):
                                if badge_class.startswith("age_"):
                                    age_rating = age_ratings.get(badge_class, "")
                                    break
                    
                    # Calculate end time based on next program's start time
                    end_time = ""
                    if index < len(program_items) - 1:
                        next_start_time = self._safe_extract_text(program_items[index + 1], ".column1.cell")
                        if next_start_time:
                            end_time = next_start_time
                    
                    # Extract any episode or special information from the title
                    episode_info = ""
                    special_tags = []
                    
                    # Check for English commentary tag
                    if "[영어중계]" in title:
                        special_tags.append("English Commentary")
                        title = title.replace("[영어중계]", "").strip()
                    
                    # Check for season/episode pattern like "(7회 - ...)"
                    episode_match = re.search(r'\((\d+)회.*?\)', title)
                    if episode_match:
                        episode_info = f"Episode {episode_match.group(1)}"
                    
                    # Generate a unique program ID
                    program_id = hashlib.md5(f"{date_id}_{start_time}_{title}".encode()).hexdigest()
                    
                    # Create program dictionary
                    program = {
                        'program_id': program_id,
                        'date': date_id,
                        'start_time': start_time,
                        'end_time': end_time,
                        'title': title,
                        'broadcast_type': broadcast_type,
                        'age_rating': age_rating,
                        'episode_info': episode_info,
                        'special_tags': special_tags,
                        'is_now_playing': 'now' in item.get('class', [])
                    }
                    
                    programs.append(program)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to extract program at index {index}: {e}")
                    continue
            
            return programs
            
        except Exception as e:
            self.logger.error(f"Failed to parse HTML content: {e}")
            return []

    def _extract_broadcast_types(self, soup) -> Dict[str, str]:
        """
        Extract broadcast type definitions from the page footer.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Dictionary mapping badge classes to human-readable broadcast types
        """
        broadcast_types = {
            'live': 'Live',
            'air': 'Original Broadcast',
            'replay': 'Rebroadcast'
        }
        
        try:
            # Try to extract from the page footer
            type_info_divs = soup.select("div.type_info")
            
            for div in type_info_divs:
                badges = div.select("div.badge")
                
                for badge in badges:
                    badge_class = None
                    for cls in badge.get("class", []):
                        if cls in ["live", "air", "replay"]:
                            badge_class = cls
                            break
                    
                    if badge_class:
                        # Get the text that follows this badge
                        next_text = badge.find_next("span")
                        if next_text:
                            broadcast_types[badge_class] = next_text.text.strip()
        
        except Exception as e:
            self.logger.warning(f"Failed to extract broadcast type definitions: {e}")
        
        return broadcast_types

    def _extract_age_ratings(self, soup) -> Dict[str, str]:
        """
        Extract age rating definitions from the page footer.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Dictionary mapping badge classes to human-readable age ratings
        """
        age_ratings = {
            'age_null': 'All Ages',
            'age_12': '12+',
            'age_15': '15+',
            'age_19': '19+'
        }
        
        try:
            # Try to extract from the page footer
            type_info_divs = soup.select("div.type_info")
            
            for div in type_info_divs:
                badges = div.select("div.badge")
                
                for badge in badges:
                    badge_class = None
                    for cls in badge.get("class", []):
                        if cls.startswith("age_"):
                            badge_class = cls
                            break
                    
                    if badge_class:
                        # Get the text that follows this badge
                        next_text = badge.find_next("span")
                        if next_text:
                            age_ratings[badge_class] = next_text.text.strip()
        
        except Exception as e:
            self.logger.warning(f"Failed to extract age rating definitions: {e}")
        
        return age_ratings

    def _safe_extract_text(self, element, selector: str) -> str:
        """
        Safely extract text from an element using a CSS selector.
        
        Args:
            element: BeautifulSoup element to search within
            selector: CSS selector to find the target element
            
        Returns:
            Extracted text or empty string if not found
        """
        try:
            target = element.select_one(selector)
            return target.text.strip() if target else ""
        except Exception:
            return ""

    def _safe_extract_attribute(self, element, selector: str, attribute: str) -> str:
        """
        Safely extract an attribute from an element using a CSS selector.
        
        Args:
            element: BeautifulSoup element to search within
            selector: CSS selector to find the target element
            attribute: Name of the attribute to extract
            
        Returns:
            Extracted attribute value or empty string if not found
        """
        try:
            target = element.select_one(selector)
            return target.get(attribute, "") if target else ""
        except Exception:
            return ""

    def _calculate_program_duration(self, start_time: str, end_time: str) -> int:
        """
        Calculate program duration in minutes.
        
        Args:
            start_time: Program start time (HH:MM format)
            end_time: Program end time (HH:MM format)
            
        Returns:
            Duration in minutes or 0 if calculation fails
        """
        try:
            if not start_time or not end_time:
                return 0
                
            from datetime import datetime
            
            # Parse times
            start = datetime.strptime(start_time, "%H:%M")
            end = datetime.strptime(end_time, "%H:%M")
            
            # Handle overnight programs
            if end < start:
                end = end.replace(day=2)  # Add a day to end time
                
            # Calculate duration in minutes
            duration = (end - start).total_seconds() / 60
            return int(duration)
        except Exception:
            return 0
    
    # ==================== MAIN WORKFLOW ORCHESTRATION ====================
    
    async def execute_complete_workflow(self) -> Dict[str, Any]:
        """
        Main production workflow - orchestrates all scraping steps
        This method is called daily by the production scheduler
        """
        workflow_start = datetime.now()
        self.logger.info(f"Starting complete workflow for {self.channel_name}")
        
        try:
            # Step 1: Foundation & Channel Navigation
            self.logger.info("Phase 1: Foundation & Channel Navigation")
            
            if not await self.prelogin():
                raise Exception("Failed to initialize website")
            
            if not await self.login():
                raise Exception("Failed to handle authentication")
            
            if not await self.channel_navigation():
                raise Exception(f"Failed to navigate to channel: {self.channel_name}")
            
            # Step 2: Date Discovery & HTML Collection
            self.logger.info("Phase 2: Date Discovery & HTML Collection")
            
            available_dates = await self.collect_available_dates()
            if not available_dates:
                raise Exception("No available dates found")
            
            self.logger.info(f"Found {len(available_dates)} available dates")
            
            date_html_files = await self.collect_date_html_pages(available_dates)
            if not date_html_files:
                raise Exception("Failed to collect HTML pages")
            
            self.logger.info(f"Collected HTML for {len(date_html_files)} dates")
            
            # Step 3: Program Extraction & Details
            self.logger.info("Phase 3: Program Extraction & Details")
            
            program_data = await self.program_extraction(date_html_files)
            
            # Calculate final statistics
            total_programs = program_data.get('total_programs', 0)
            
            workflow_duration = (datetime.now() - workflow_start).total_seconds()
            
            # Prepare final results
            final_results = {
                'success': True,
                'channel': self.channel_name,
                'base_url': self.base_url,
                'scraping_timestamp': datetime.now().isoformat(),
                'workflow_duration_seconds': workflow_duration,
                'dates_processed': len(date_html_files),
                'programs_found': total_programs,
                'available_dates': available_dates,
                'program_data': program_data
            }
            
            self.logger.info(f"Workflow completed successfully in {workflow_duration:.2f} seconds")
            self.logger.info(f"Results: {len(date_html_files)} dates, {total_programs} programs")
            
            return final_results
            
        except Exception as e:
            workflow_duration = (datetime.now() - workflow_start).total_seconds()
            error_result = {
                'success': False,
                'error': str(e),
                'channel': self.channel_name,
                'base_url': self.base_url,
                'scraping_timestamp': datetime.now().isoformat(),
                'workflow_duration_seconds': workflow_duration
            }
            
            self.logger.error(f"Workflow failed after {workflow_duration:.2f} seconds: {e}")
            return error_result

# ==================== MAIN EXECUTION ====================

async def main():
    """Main execution function for testing and production use"""
    scraper = SpotvPrime2Scraper()
    
    try:
        # Run the complete workflow
        result = await scraper.execute_complete_workflow()
        
        if result['success']:
            print("✅ SCRAPING COMPLETED SUCCESSFULLY!")
            print(f"📺 Channel: {result.get('channel', 'Unknown')}")
            print(f"📅 Dates processed: {result.get('dates_processed', 0)}")
            print(f"📋 Programs found: {result.get('programs_found', 0)}")
            print(f"⏱️  Duration: {result.get('workflow_duration_seconds', 0):.2f} seconds")
            
            # Save results to file
            output_file = f"spotv_prime2_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"📁 Results saved to: {output_file}")
        else:
            print("❌ SCRAPING FAILED!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            
        return result
        
    except Exception as e:
        print(f"❌ EXECUTION FAILED: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())