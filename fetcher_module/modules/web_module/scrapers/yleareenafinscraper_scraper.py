import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

from smart_tv_scraper import IntelligentTVScraper

class YleAreenaFinScraper(IntelligentTVScraper):
    """
    Production-ready TV schedule scraper for YLE Areena (FIN)
    Auto-generated using intelligent analysis of https://areena.yle.fi/tv/opas
    
    This scraper runs daily in production to collect:
    - All available dates on the website
    - All programs for each date
    - Detailed information for each program
    """
    
    def __init__(self):
        super().__init__("YLE Areena (FIN)", "https://areena.yle.fi/tv/opas")
        self.logger.info(f"Initialized scraper for {self.channel_name}")
    
    # ==================== STEP 1: FOUNDATION & CHANNEL NAVIGATION ====================
    
    async def prelogin(self) -> bool:
        """
        Open the YLE Areena TV guide website and handle initial setup.
        
        This method:
        1. Navigates to the TV guide URL
        2. Handles cookie consent dialog if present
        3. Ensures the page is ready for channel navigation
        
        Returns:
            bool: True if prelogin is successful, False otherwise
        """
        try:
            self.logger.info("Starting prelogin process for YLE Areena TV guide")
            
            # Navigate directly to the TV guide URL (URL-first approach)
            tv_guide_url = "https://areena.yle.fi/tv/opas"
            self.logger.info(f"Navigating to TV guide URL: {tv_guide_url}")
            
            success = await self.navigate_to_url(tv_guide_url)
            if not success:
                self.logger.error("Failed to navigate to TV guide URL")
                return False
            
            # Wait for the page to load properly
            try:
                # Wait for channel sections to be visible (from intelligence data)
                await self.wait_for_element(".Channel_channelRoot__QG36Q", 5000)
                self.logger.info("TV guide page loaded successfully")
            except Exception as e:
                self.logger.warning(f"Channel sections not immediately visible: {e}")
                # Try refreshing the page once if elements aren't visible
                self.logger.info("Attempting page refresh")
                await self.page.reload()
                try:
                    await self.wait_for_element(".Channel_channelRoot__QG36Q", 5000)
                except Exception as refresh_error:
                    self.logger.error(f"Channel sections still not visible after refresh: {refresh_error}")
                    return False
            
            # Handle cookie consent dialog if present
            try:
                cookie_consent = await self.page.query_selector("button[name='accept-all-consents']")
                if cookie_consent:
                    self.logger.info("Cookie consent dialog detected, accepting cookies")
                    await self.click("button[name='accept-all-consents']")
                    await self.page.wait_for_timeout(1000)  # Wait for dialog to disappear
            except Exception as e:
                self.logger.warning(f"Error handling cookie consent: {e}")
                # Continue anyway as this is not critical
            
            self.logger.info("Prelogin completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Prelogin failed: {e}")
            return False

    async def login(self, credentials: Optional[Dict[str, str]] = None) -> bool:
        """
        Handle authentication for YLE Areena if required.
        
        This method implements the login flow based on the intelligence data:
        1. Navigate to the TV guide page
        2. Accept cookies if prompted
        3. Click the login button to open the login form
        4. Enter email and password
        5. Submit the login form
        6. Verify successful login
        
        Args:
            credentials (Optional[Dict[str, str]]): Dictionary containing 'username' and 'password'
                                                   keys for authentication
        
        Returns:
            bool: True if login successful or not required, False otherwise
        """
        try:
            # Check if login is actually needed
            if not await self.requires_login():
                self.logger.info("No login required for YLE Areena TV guide")
                return True
            
            # Validate credentials
            if not credentials or 'username' not in credentials or 'password' not in credentials:
                self.logger.error("Login required but no valid credentials provided")
                return False
            
            self.logger.info("Starting login process for YLE Areena...")
            
            # Step 1: Navigate to the site if not already there
            current_url = await self.page.url()
            if "areena.yle.fi/tv/opas" not in current_url:
                await self.navigate_to_url("https://areena.yle.fi/tv/opas")
            
            # Step 2: Accept cookies if the dialog is present
            try:
                cookie_consent = await self.page.query_selector("button[name='accept-all-consents']")
                if cookie_consent:
                    self.logger.info("Accepting cookies...")
                    await self.click("button[name='accept-all-consents']")
                    await self.wait_for_element("button span:contains('Kirjaudu')", 2000)
            except Exception as e:
                self.logger.warning(f"Error handling cookie consent: {e}")
            
            # Step 3: Open login form
            self.logger.info("Opening login form...")
            await self.click("button:has(span:contains('Kirjaudu'))")
            
            # Wait for login form to appear
            await self.wait_for_element("input#emailAddress", 3000)
            
            # Step 4: Enter email
            self.logger.info("Entering email address...")
            await self.page.fill("input#emailAddress", credentials['username'])
            
            # Step 5: Enter password
            self.logger.info("Entering password...")
            await self.page.fill("input#password", credentials['password'])
            
            # Step 6: Submit login form
            self.logger.info("Submitting login form...")
            await self.click("button[aria-label='Kirjaudu sisään']")
            
            # Wait for login process to complete and verify
            await self.page.wait_for_timeout(5000)  # Give time for login to process
            
            # Verify login success
            return await self.verify_login_status()
            
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    async def verify_login_status(self) -> bool:
        """
        Check if the user is currently logged in to YLE Areena.
        
        This method verifies the login status by looking for user-specific elements
        that indicate a successful login, such as user initials or profile elements.
        
        Returns:
            bool: True if logged in, False otherwise
        """
        try:
            self.logger.info("Verifying login status...")
            
            # According to intelligence data, after successful login,
            # user initials 'BA' appear in the interface
            try:
                # Look for user initials button that appears after login
                user_button = await self.page.query_selector("button:has(span:contains('BA'))")
                if user_button:
                    self.logger.info("User is logged in - user initials found")
                    return True
            except Exception:
                pass
            
            # Alternative check: look for any user profile indicators
            try:
                # Check for any user profile elements that would indicate logged-in state
                profile_elements = await self.page.query_selector(
                    "[data-testid='user-menu'], .user-profile, .logged-in-indicator"
                )
                if profile_elements:
                    self.logger.info("User is logged in - profile elements found")
                    return True
            except Exception:
                pass
            
            # Check for login button - if present, user is not logged in
            login_button = await self.page.query_selector("button:has(span:contains('Kirjaudu'))")
            if login_button:
                self.logger.info("User is not logged in - login button is present")
                return False
            
            self.logger.info("Could not definitively determine login status, assuming not logged in")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to verify login status: {e}")
            return False

    async def requires_login(self) -> bool:
        """
        Determine if the website requires authentication to access TV schedule data.
        
        This method checks if login is required by examining the page content and
        structure based on intelligence data. For YLE Areena, login is not strictly
        required to access the TV schedule, but the method is implemented to handle
        potential future changes.
        
        Returns:
            bool: True if login is required, False otherwise
        """
        try:
            self.logger.info("Checking if login is required for YLE Areena TV guide...")
            
            # Navigate to the TV guide page if not already there
            current_url = await self.page.url()
            if "areena.yle.fi/tv/opas" not in current_url:
                await self.navigate_to_url("https://areena.yle.fi/tv/opas")
            
            # Check if we need to handle cookie consent first
            try:
                cookie_consent = await self.page.query_selector("button[name='accept-all-consents']")
                if cookie_consent:
                    self.logger.info("Cookie consent dialog detected, accepting cookies...")
                    await self.click("button[name='accept-all-consents']")
                    await self.page.wait_for_timeout(1000)  # Wait for dialog to disappear
            except Exception as e:
                self.logger.warning(f"Error handling cookie consent: {e}")
            
            # Check if TV guide content is accessible without login
            # For YLE Areena, the TV guide is publicly accessible without login
            try:
                # Check if TV guide content is visible
                guide_content = await self.page.query_selector(".guide-content, .tv-guide, [data-testid='tv-guide']")
                if guide_content:
                    self.logger.info("TV guide content is accessible without login")
                    return False
            except Exception as e:
                self.logger.warning(f"Error checking TV guide content: {e}")
            
            # If we can't determine for sure, default to not requiring login
            # Most TV schedule sites don't require login
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to check login requirement: {e}")
            return False

    async def channel_navigation(self) -> bool:
        """
        Navigate to the YLE Areena channel in the TV guide.
        
        Based on intelligence data, YLE Areena channel is already visible on the TV guide page,
        so this method primarily verifies the channel's presence and confirms we're looking
        at the correct channel.
        
        Returns:
            bool: True if channel navigation is successful, False otherwise
        """
        try:
            self.logger.info("Starting channel navigation for YLE Areena")
            
            # According to intelligence data, the channel is already visible on the page load
            # No additional navigation is required, just verification
            
            # Verify the AREENA channel section is present
            try:
                # Look for the channel section with the Yle Areena logo
                channel_section = await self.wait_for_element(
                    "section.Channel_channelRoot__QG36Q img[alt='Yle Areena']", 
                    3000
                )
                
                if not channel_section:
                    self.logger.error("Could not find YLE Areena channel section")
                    return False
                    
                self.logger.info("YLE Areena channel section found")
                
            except Exception as e:
                self.logger.error(f"Failed to find YLE Areena channel section: {e}")
                return False
            
            # Verify program listings are present to confirm complete channel load
            try:
                program_listings = await self.page.query_selector(
                    "div.Channel_programsRoot__sBbcG li.Channel_programWrapper__ok16Y"
                )
                
                if not program_listings:
                    self.logger.warning("Program listings not found for YLE Areena")
                    # Try scrolling to the channel section to ensure it's in view
                    await self.page.evaluate("""
                        document.querySelector("img[alt='Yle Areena']").scrollIntoView();
                    """)
                    await self.page.wait_for_timeout(1000)
                    
                    # Check again after scrolling
                    program_listings = await self.page.query_selector(
                        "div.Channel_programsRoot__sBbcG li.Channel_programWrapper__ok16Y"
                    )
                    if not program_listings:
                        self.logger.error("Program listings still not found after scrolling")
                        return False
                
                self.logger.info("YLE Areena program listings verified")
                
            except Exception as e:
                self.logger.error(f"Failed to verify program listings: {e}")
                return False
            
            # Save the channel page HTML for potential future use
            try:
                await self.save_page_html("yle_areena_channel", "channel_page")
                self.logger.info("Saved YLE Areena channel page HTML")
            except Exception as e:
                self.logger.warning(f"Failed to save channel page HTML: {e}")
                # Continue anyway as this is not critical
            
            self.logger.info("Channel navigation completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Channel navigation failed: {e}")
            return False
    
    # ==================== STEP 2: DATE DISCOVERY & HTML COLLECTION ====================
    
    async def collect_available_dates(self) -> List[str]:
        """
        Discover all available dates for the YLE Areena TV schedule.
        
        This method analyzes the date picker element to determine the available date range
        and returns a list of date identifiers in YYYY-MM-DD format that can be used for
        navigation.
        
        Returns:
            List[str]: List of available dates in YYYY-MM-DD format
        """
        try:
            self.logger.info("Discovering available dates for YLE Areena TV schedule")
            available_dates = []
            
            # Wait for the date picker element to be visible
            try:
                await self.wait_for_element(".DatePicker_root__SfAXx", 5000)
            except Exception as e:
                self.logger.warning(f"Date picker not immediately visible: {e}")
                # Try refreshing the page once if date picker isn't visible
                await self.page.reload()
                try:
                    await self.wait_for_element(".DatePicker_root__SfAXx", 5000)
                except Exception as refresh_error:
                    self.logger.error(f"Date picker still not visible after refresh: {refresh_error}")
                    return self._generate_fallback_dates()
            
            # According to intelligence data, the date range is defined by min/max attributes on the date input
            try:
                # Get the date input element
                date_input = await self.page.query_selector("input[type='date']")
                if not date_input:
                    date_input = await self.page.query_selector(".DatePicker_input__GOQBq")
                
                if not date_input:
                    self.logger.warning("Date input element not found, using fallback dates")
                    return self._generate_fallback_dates()
                
                # Extract min and max date attributes
                min_date = await date_input.get_attribute("min")
                max_date = await date_input.get_attribute("max")
                
                if not min_date or not max_date:
                    self.logger.warning("Min/max date attributes not found, using fallback dates")
                    return self._generate_fallback_dates()
                
                self.logger.info(f"Found date range: {min_date} to {max_date}")
                
                # Generate all dates in the range
                start_date = datetime.strptime(min_date, "%Y-%m-%d")
                end_date = datetime.strptime(max_date, "%Y-%m-%d")
                
                current_date = start_date
                while current_date <= end_date:
                    date_str = current_date.strftime("%Y-%m-%d")
                    available_dates.append(date_str)
                    current_date += timedelta(days=1)
                
            except Exception as e:
                self.logger.error(f"Error extracting date range: {e}")
                return self._generate_fallback_dates()
            
            if available_dates:
                self.store_available_dates(available_dates)
                self.logger.info(f"Found {len(available_dates)} available dates from {available_dates[0]} to {available_dates[-1]}")
                return available_dates
            else:
                self.logger.warning("No dates discovered, using fallback")
                return self._generate_fallback_dates()
                
        except Exception as e:
            self.logger.error(f"Date discovery failed: {e}")
            return self._generate_fallback_dates()
    
    async def collect_date_html_pages(self, dates: List[str]) -> Dict[str, str]:
        """
        Navigate to each date in the provided list and save the complete HTML pages.
        
        This method uses a URL-first approach to navigate directly to each date's TV schedule
        page, scrolls to ensure all content is loaded, and saves the complete HTML for later
        processing.
        
        Args:
            dates (List[str]): List of dates in YYYY-MM-DD format to collect
            
        Returns:
            Dict[str, str]: Mapping of date_id to saved HTML file path
        """
        self.logger.info(f"Collecting HTML pages for {len(dates)} dates")
        date_html_files = {}
        
        # Base URL for the TV guide
        base_url = "https://areena.yle.fi/tv/opas"
        
        for date_id in dates:
            try:
                self.logger.info(f"Processing date: {date_id}")
                
                # URL-first approach: Navigate directly to the date using URL parameter
                # According to intelligence data, the URL pattern is https://areena.yle.fi/tv/opas?t=YYYY-MM-DD
                date_url = f"{base_url}?t={date_id}"
                
                self.logger.info(f"Navigating to date URL: {date_url}")
                success = await self.navigate_to_url(date_url)
                
                if not success:
                    self.logger.error(f"Failed to navigate to date {date_id}")
                    continue
                
                # Wait for the page to load with the new date
                try:
                    # Wait for channel sections to be visible
                    await self.wait_for_element(".Channel_channelRoot__QG36Q", 5000)
                    
                    # Verify the date was loaded correctly by checking the URL
                    current_url = await self.page.url()
                    if date_id not in current_url:
                        self.logger.warning(f"URL doesn't contain target date {date_id}: {current_url}")
                        
                    # Also verify the date input shows the correct date
                    date_input = await self.page.query_selector("input[type='date']")
                    if date_input:
                        input_value = await date_input.get_attribute("value")
                        if input_value != date_id:
                            self.logger.warning(f"Date input value ({input_value}) doesn't match target date ({date_id})")
                    
                except Exception as e:
                    self.logger.warning(f"Error verifying date navigation: {e}")
                
                # Scroll to load all content (handle lazy loading)
                try:
                    # Scroll to bottom to load all content
                    await self.scroll_page("bottom")
                    await self.page.wait_for_timeout(2000)  # Wait for lazy content to load
                    
                    # Scroll back to top
                    await self.scroll_page("top")
                    await self.page.wait_for_timeout(500)
                except Exception as e:
                    self.logger.warning(f"Error during page scrolling: {e}")
                
                # Save the complete HTML page
                try:
                    html_file_path = await self.save_page_html(f"date_{date_id}", "date_page")
                    if html_file_path:
                        self.store_date_html_file(date_id, html_file_path)
                        date_html_files[date_id] = html_file_path
                        self.logger.info(f"Saved HTML for date {date_id}")
                    else:
                        self.logger.error(f"Failed to save HTML for date {date_id}")
                except Exception as e:
                    self.logger.error(f"Error saving HTML for date {date_id}: {e}")
                
            except Exception as e:
                self.logger.error(f"Failed to collect HTML for date {date_id}: {e}")
                continue  # Continue with next date
        
        self.logger.info(f"Successfully collected {len(date_html_files)} HTML pages")
        return date_html_files

    def _generate_fallback_dates(self) -> List[str]:
        """
        Generate fallback date range if date discovery fails.
        
        Creates a list of dates starting from today and extending for the next 14 days,
        which is a reasonable range for most TV schedule sites.
        
        Returns:
            List[str]: List of dates in YYYY-MM-DD format
        """
        self.logger.info("Generating fallback dates (today + 14 days)")
        dates = []
        today = datetime.now()
        
        # Generate dates for today and the next 14 days
        for i in range(15):
            date = today + timedelta(days=i)
            dates.append(date.strftime('%Y-%m-%d'))
        
        self.logger.info(f"Generated {len(dates)} fallback dates from {dates[0]} to {dates[-1]}")
        return dates
    
    # ==================== STEP 3: PROGRAM EXTRACTION & DETAILS ====================
    
    async def program_extraction(self, date_html_files: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract program metadata and details from saved HTML pages for YLE Areena TV schedule.
        
        This method processes the saved HTML files from previous steps to extract program data.
        Based on intelligence data, YLE Areena uses an inline expansion method for program details,
        so this implementation focuses on extracting data from the saved HTML files and simulating
        the expansion of program details when needed.
        
        Args:
            date_html_files (Dict[str, str]): Mapping of date_id to saved HTML file path
            
        Returns:
            Dict[str, Any]: Extraction results containing programs by date, program details,
                           and summary statistics
        """
        try:
            self.logger.info(f"Starting program extraction for {len(date_html_files)} dates")
            
            extraction_results = {
                'programs_by_date': {},
                'program_details': {},
                'total_programs': 0,
                'total_details': 0
            }
            
            # Based on intelligence data, YLE Areena uses inline expansion for program details
            # We'll primarily use offline processing with fallback to live navigation if needed
            detail_strategy = self._determine_detail_strategy()
            self.logger.info(f"Using detail access strategy: {detail_strategy}")
            
            # Process each date's HTML file
            for date_id, html_file_path in date_html_files.items():
                self.logger.info(f"Processing programs for date: {date_id}")
                
                try:
                    # Extract programs from saved HTML file
                    programs = await self._extract_programs_from_html(html_file_path, date_id)
                    
                    if not programs:
                        self.logger.warning(f"No programs found in HTML for date {date_id}")
                        continue
                    
                    self.logger.info(f"Found {len(programs)} programs for date {date_id}")
                    
                    # Store basic program metadata
                    self.store_program_metadata(date_id, programs)
                    extraction_results['programs_by_date'][date_id] = programs
                    extraction_results['total_programs'] += len(programs)
                    
                    # Process program details based on strategy
                    if detail_strategy == "offline_processing":
                        await self._process_details_offline(programs, html_file_path, extraction_results)
                    else:
                        await self._process_details_live(programs, date_id, extraction_results)
                    
                except Exception as e:
                    self.logger.error(f"Error processing date {date_id}: {e}")
                    continue
            
            self.logger.info(f"Program extraction completed: {extraction_results['total_programs']} programs, "
                             f"{extraction_results['total_details']} details")
            return extraction_results
            
        except Exception as e:
            self.logger.error(f"Program extraction failed: {e}")
            return {
                'programs_by_date': {},
                'program_details': {},
                'total_programs': 0,
                'total_details': 0,
                'error': str(e)
            }

    async def _extract_programs_from_html(self, html_file_path: str, date_id: str) -> List[Dict[str, Any]]:
        """
        Extract program data from saved HTML file.
        
        Args:
            html_file_path (str): Path to saved HTML file
            date_id (str): Date identifier (YYYY-MM-DD)
            
        Returns:
            List[Dict[str, Any]]: List of program dictionaries with metadata
        """
        try:
            # Read the HTML file
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            programs = []
            
            # Based on intelligence data, find all program containers
            # Primary selector: div[role='listitem']
            program_containers = soup.select("div[role='listitem']")
            if not program_containers:
                # Fallback selector
                program_containers = soup.select("div.Program_programRoot__tIOJ3")
            
            self.logger.info(f"Found {len(program_containers)} program containers for date {date_id}")
            
            for idx, container in enumerate(program_containers):
                try:
                    # Generate a unique program ID
                    program_id = self._generate_program_id(container, date_id, idx)
                    
                    # Extract basic program metadata using selectors from intelligence data
                    title_element = container.select_one("h3.Program_programTitle__FWUCG")
                    time_element = container.select_one("time.Program_programTime__pdkfW")
                    
                    # Skip if essential elements are missing
                    if not title_element or not time_element:
                        continue
                    
                    title = title_element.get_text(strip=True)
                    start_time = time_element.get_text(strip=True)
                    
                    # Extract datetime attribute for precise timing
                    start_datetime = time_element.get('datetime', '')
                    
                    # Check for on-demand availability icon
                    on_demand = bool(container.select_one(".Program_onDemandStatusIcon__vK6MX"))
                    
                    # Extract rating from title if present (in parentheses)
                    import re
                    rating_match = re.search(r'\(([0-9]+|S)\)', title)
                    rating = rating_match.group(1) if rating_match else None
                    
                    # Clean title if it contains rating
                    if rating_match:
                        title = title.replace(rating_match.group(0), '').strip()
                    
                    # Create program dictionary
                    program = {
                        'program_id': program_id,
                        'title': title,
                        'start_time': start_time,
                        'start_datetime': start_datetime,
                        'date': date_id,
                        'on_demand': on_demand,
                        'rating': rating,
                        'channel': 'YLE Areena',
                        # Store element identifiers for potential live interaction
                        'aria_controls': container.select_one('button').get('aria-controls', '') if container.select_one('button') else '',
                        'aria_expanded': container.select_one('button').get('aria-expanded', 'false') if container.select_one('button') else 'false',
                        'data_state': container.get('data-state', 'closed')
                    }
                    
                    programs.append(program)
                    
                except Exception as e:
                    self.logger.warning(f"Error extracting program {idx} for date {date_id}: {e}")
                    continue
            
            return programs
            
        except Exception as e:
            self.logger.error(f"Failed to extract programs from HTML: {e}")
            return []

    async def _process_details_offline(self, programs: List[Dict[str, Any]], html_file_path: str, 
                                      extraction_results: Dict[str, Any]) -> None:
        """
        Process program details using offline HTML processing.
        
        This method simulates the expansion of program details by analyzing the HTML structure
        and extracting details that would be visible when a program is expanded.
        
        Args:
            programs (List[Dict[str, Any]]): List of programs to process
            html_file_path (str): Path to HTML file containing programs
            extraction_results (Dict[str, Any]): Results dictionary to update
        """
        try:
            self.logger.info(f"Processing details offline for {len(programs)} programs")
            
            # Read the HTML file
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            for program in programs:
                try:
                    program_id = program['program_id']
                    
                    # Find the program container using identifiers
                    aria_controls = program.get('aria_controls', '')
                    if aria_controls:
                        # Find the hidden details container
                        detail_container = soup.select_one(f"div#{aria_controls}")
                        
                        if detail_container:
                            # Extract details from the container
                            description = self._safe_extract_text(detail_container, "p")
                            duration = self._safe_extract_text(detail_container, "span:contains('min')")
                            genre = self._safe_extract_text(detail_container, "em")
                            
                            # Create details dictionary
                            details = {
                                'description': description,
                                'duration': duration,
                                'genre': genre,
                                'extracted_method': 'offline'
                            }
                            
                            # Save details to HTML file
                            detail_html_path = await self._save_detail_html(
                                f"program_detail_{program_id}", 
                                str(detail_container)
                            )
                            
                            # Store program details
                            self.store_program_detail_data(program_id, details, detail_html_path)
                            extraction_results['program_details'][program_id] = details
                            extraction_results['total_details'] += 1
                        else:
                            self.logger.warning(f"Detail container not found for program {program_id}")
                    
                except Exception as e:
                    self.logger.warning(f"Error processing details for program {program.get('program_id', 'unknown')}: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Failed to process details offline: {e}")

    async def _process_details_live(self, programs: List[Dict[str, Any]], date_id: str, 
                                   extraction_results: Dict[str, Any]) -> None:
        """
        Process program details using live page navigation and interaction.
        
        This method navigates to the date page and clicks on each program to expand its details.
        
        Args:
            programs (List[Dict[str, Any]]): List of programs to process
            date_id (str): Date identifier (YYYY-MM-DD)
            extraction_results (Dict[str, Any]): Results dictionary to update
        """
        try:
            self.logger.info(f"Processing details live for {len(programs)} programs on date {date_id}")
            
            # Navigate to the date page
            date_url = f"https://areena.yle.fi/tv/opas?t={date_id}"
            success = await self.navigate_to_url(date_url)
            
            if not success:
                self.logger.error(f"Failed to navigate to date page for {date_id}")
                return
            
            # Wait for program listings to load
            await self.wait_for_element("div[role='listitem']", 5000)
            
            # Process each program
            for program in programs:
                try:
                    program_id = program['program_id']
                    title = program['title']
                    start_time = program['start_time']
                    
                    self.logger.info(f"Processing details for program: {start_time} - {title}")
                    
                    # Find the program button using time and title
                    # This is more reliable than using IDs which might change
                    program_selector = f"button:has(time:text-is('{start_time}')):has(h3:contains('{title}'))"
                    
                    # Wait for the program button
                    program_button = await self.wait_for_element(program_selector, 3000)
                    
                    if not program_button:
                        self.logger.warning(f"Program button not found for {title} at {start_time}")
                        continue
                    
                    # Click to expand program details
                    await self.click(program_selector)
                    
                    # Wait for expanded state
                    await self.page.wait_for_timeout(500)  # Short wait for expansion
                    
                    # Check if expansion was successful
                    expanded = await self.page.evaluate(f"""
                        document.querySelector("{program_selector}").getAttribute("aria-expanded") === "true"
                    """)
                    
                    if not expanded:
                        self.logger.warning(f"Program details did not expand for {title}")
                        continue
                    
                    # Extract details from expanded program
                    description = await self._extract_text_from_page("div[data-state='open'] p")
                    duration = await self._extract_text_from_page("div[data-state='open'] span:has-text(/min/)")
                    genre = await self._extract_text_from_page("div[data-state='open'] em")
                    
                    # Create details dictionary
                    details = {
                        'description': description,
                        'duration': duration,
                        'genre': genre,
                        'extracted_method': 'live'
                    }
                    
                    # Save expanded HTML
                    detail_html_path = await self.save_page_html(f"program_detail_{program_id}", "program_detail")
                    
                    # Store program details
                    self.store_program_detail_data(program_id, details, detail_html_path)
                    extraction_results['program_details'][program_id] = details
                    extraction_results['total_details'] += 1
                    
                    # Click again to collapse (clean up)
                    await self.click(program_selector)
                    await self.page.wait_for_timeout(300)  # Short wait for collapse
                    
                except Exception as e:
                    self.logger.warning(f"Error processing live details for program {program.get('title', 'unknown')}: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"Failed to process details live: {e}")

    def _determine_detail_strategy(self) -> str:
        """
        Determine the best strategy for accessing program details based on intelligence data.
        
        Returns:
            str: Strategy to use - 'offline_processing' or 'live_navigation'
        """
        try:
            # Based on intelligence data, YLE Areena uses inline expansion for program details
            # The detail_access_strategy shows "access_method": "inline_expansion"
            # This means we can try offline processing first
            
            # Default to offline processing as it's more efficient
            return "offline_processing"
            
        except Exception as e:
            self.logger.warning(f"Error determining detail strategy: {e}")
            # Fall back to live navigation if we can't determine
            return "live_navigation"

    def _generate_program_id(self, container, date_id: str, index: int) -> str:
        """
        Generate a unique program ID from container attributes or fallback to date and index.
        
        Args:
            container: BeautifulSoup element representing the program
            date_id (str): Date identifier
            index (int): Program index
            
        Returns:
            str: Unique program identifier
        """
        try:
            # Try to get a stable ID from the container
            aria_labelledby = container.get('aria-labelledby', '')
            if aria_labelledby:
                return aria_labelledby.replace('program-', '').replace('-time', '').replace('-title', '')
            
            # Fallback to using time and title
            time_element = container.select_one("time.Program_programTime__pdkfW")
            title_element = container.select_one("h3.Program_programTitle__FWUCG")
            
            if time_element and title_element:
                time_text = time_element.get_text(strip=True)
                title_text = title_element.get_text(strip=True)
                import hashlib
                return hashlib.md5(f"{date_id}_{time_text}_{title_text}".encode()).hexdigest()
            
            # Last resort fallback
            return f"{date_id}_program_{index}"
            
        except Exception:
            # Ultimate fallback
            return f"{date_id}_program_{index}"

    def _safe_extract_text(self, container, selector: str) -> str:
        """
        Safely extract text from an element using a selector.
        
        Args:
            container: BeautifulSoup element to search within
            selector (str): CSS selector to find the target element
            
        Returns:
            str: Extracted text or empty string if not found
        """
        try:
            element = container.select_one(selector)
            return element.get_text(strip=True) if element else ""
        except Exception:
            return ""

    async def _extract_text_from_page(self, selector: str) -> str:
        """
        Safely extract text from the current page using a selector.
        
        Args:
            selector (str): CSS selector to find the target element
            
        Returns:
            str: Extracted text or empty string if not found
        """
        try:
            element = await self.page.query_selector(selector)
            if element:
                return await element.text_content()
            return ""
        except Exception:
            return ""

    async def _save_detail_html(self, filename: str, html_content: str) -> str:
        """
        Save program detail HTML content to a file.
        
        Args:
            filename (str): Base filename to use
            html_content (str): HTML content to save
            
        Returns:
            str: Path to saved HTML file
        """
        try:
            import os
            import tempfile
            
            # Create a temporary file
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, f"{filename}.html")
            
            # Write HTML content to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"<html><body>{html_content}</body></html>")
            
            return file_path
            
        except Exception as e:
            self.logger.error(f"Failed to save detail HTML: {e}")
            return ""
    
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
                self.logger.warning("Login failed or not required, continuing without authentication")
                # Continue anyway as login is not required for YLE Areena TV guide
            
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
            total_details = program_data.get('total_details', 0)
            
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
                'program_details_extracted': total_details,
                'available_dates': available_dates,
                'program_data': program_data
            }
            
            self.logger.info(f"Workflow completed successfully in {workflow_duration:.2f} seconds")
            self.logger.info(f"Results: {len(date_html_files)} dates, {total_programs} programs, {total_details} details")
            
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
    scraper = YleAreenaFinScraper()
    
    try:
        # Run the complete workflow
        result = await scraper.execute_complete_workflow()
        
        if result['success']:
            print("✅ SCRAPING COMPLETED SUCCESSFULLY!")
            print(f"📺 Channel: {result.get('channel', 'Unknown')}")
            print(f"📅 Dates processed: {result.get('dates_processed', 0)}")
            print(f"📋 Programs found: {result.get('programs_found', 0)}")
            print(f"🔍 Program details: {result.get('program_details_extracted', 0)}")
            print(f"⏱️  Duration: {result.get('workflow_duration_seconds', 0):.2f} seconds")
            
            # Save results to file
            try:
                output_dir = Path("results")
                output_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = output_dir / f"yle_areena_results_{timestamp}.json"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                print(f"📁 Results saved to: {output_file}")
                result['results_file'] = str(output_file)
            except Exception as e:
                print(f"⚠️ Failed to save results to file: {e}")
        else:
            print("❌ SCRAPING FAILED!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            
        return result
        
    except Exception as e:
        print(f"❌ EXECUTION FAILED: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())