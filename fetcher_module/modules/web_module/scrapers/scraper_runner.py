"""
TV Scraper Runner - Step-by-Step Testing and Orchestration

This class manages the complete scraping workflow and provides
step-by-step testing capabilities for iterative development.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Type

from .iterative_tv_scraper import IterativeTVScraper, ScraperConfig, TVScraperError


class ScraperRunner:
    """
    Orchestrates the complete TV scraping workflow with step-by-step testing.
    
    Supports iterative development:
    1. Test login functionality
    2. Test channel enumeration and navigation
    3. Test date navigation
    4. Test program data collection
    """
    
    def __init__(self, scraper_class: Type[IterativeTVScraper], config: ScraperConfig):
        self.scraper_class = scraper_class
        self.config = config
        self.results = {
            "login_test": None,
            "channel_test": None,
            "date_test": None,
            "program_test": None,
            "full_workflow": None
        }
    
    # ==================== STEP 1: LOGIN TESTING ====================
    
    async def test_login_functionality(self) -> Dict[str, Any]:
        """
        Test Step 1: Login functionality with REAL website testing
        
        Returns:
            Dict with test results and any errors
        """
        print("🔐 Testing Step 1: Login Functionality")
        
        scraper = self.scraper_class(self.config)
        test_result = {
            "step": "login",
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "login_required": None,
            "login_success": None,
            "error": None,
            "error_details": None,
            "page_url": None,
            "page_title": None
        }
        
        try:
            async with scraper.browser_session() as page:
                # Test requires_login with real website - pass page object
                print("  ↳ Testing requires_login() with real website...")
                login_required = await scraper.requires_login(page)
                test_result["login_required"] = login_required
                test_result["page_url"] = page.url
                test_result["page_title"] = await page.title()
                print(f"    Login required: {login_required}")
                
                # Test login if required - pass page object
                if login_required:
                    print("  ↳ Testing login() with real website...")
                    
                    # Check if credentials are available
                    if not self.config.credentials:
                        test_result["error"] = "Login required but no credentials provided in config"
                        test_result["error_details"] = {
                            "error_type": "MISSING_CREDENTIALS",
                            "message": "Set credentials in ScraperConfig for testing"
                        }
                        return test_result
                    
                    login_success = await scraper.login(page)
                    test_result["login_success"] = login_success
                    test_result["page_url"] = page.url
                    test_result["page_title"] = await page.title()
                    print(f"    Login success: {login_success}")
                    
                    if not login_success:
                        test_result["error"] = "Login failed"
                        test_result["error_details"] = {
                            "error_type": "LOGIN_FAILED",
                            "final_url": page.url,
                            "final_title": await page.title()
                        }
                        return test_result
                else:
                    print("    No login required - skipping login test")
                    test_result["login_success"] = True
                
                test_result["success"] = True
                print("✅ Step 1: Login functionality working")
                
        except Exception as e:
            test_result["error"] = str(e)
            test_result["error_details"] = {
                "error_type": type(e).__name__,
                "message": str(e),
                "page_url": None,  # Page might not be available in error case
                "page_title": None
            }
            print(f"❌ Step 1: Login test failed - {str(e)}")
        
        self.results["login_test"] = test_result
        return test_result
    
    # ==================== STEP 2: CHANNEL TESTING ====================
    
    async def test_channel_functionality(self) -> Dict[str, Any]:
        """
        Test Step 2: Channel enumeration and navigation
        
        Returns:
            Dict with test results and any errors
        """
        print("📺 Testing Step 2: Channel Functionality")
        
        scraper = self.scraper_class(self.config)
        test_result = {
            "step": "channel",
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "available_channels": None,
            "channel_navigation_tests": [],
            "error": None
        }
        
        try:
            async with scraper.browser_session() as page:
                # Handle login if required - pass page object
                if await scraper.requires_login(page):
                    await scraper.login(page)
                
                # Test channel enumeration - pass page object
                print("  ↳ Testing enumerate_channels()...")
                available_channels = await scraper.enumerate_channels(page)
                test_result["available_channels"] = available_channels
                print(f"    Available channels: {available_channels}")
                
                # Test channel navigation for first 2 channels
                test_channels = available_channels[:2] if len(available_channels) > 1 else available_channels
                
                for channel in test_channels:
                    print(f"  ↳ Testing navigate_to_channel('{channel}')...")
                    
                    channel_test = {
                        "channel": channel,
                        "success": False,
                        "error": None
                    }
                    
                    try:
                        # Pass page object to navigate_to_channel
                        success = await scraper.navigate_to_channel(page, channel)
                        channel_test["success"] = success
                        print(f"    Channel '{channel}' navigation: {success}")
                    except Exception as e:
                        channel_test["error"] = str(e)
                        print(f"    Channel '{channel}' navigation failed: {str(e)}")
                    
                    test_result["channel_navigation_tests"].append(channel_test)
                
                # Check if all channel tests passed
                all_passed = all(test["success"] for test in test_result["channel_navigation_tests"])
                test_result["success"] = all_passed
                
                if all_passed:
                    print("✅ Step 2: Channel functionality working")
                else:
                    print("❌ Step 2: Some channel navigation tests failed")
                
        except Exception as e:
            test_result["error"] = str(e)
            print(f"❌ Step 2: Channel test failed - {str(e)}")
        
        self.results["channel_test"] = test_result
        return test_result
    
    # ==================== STEP 3: DATE TESTING ====================
    
    async def test_date_functionality(self) -> Dict[str, Any]:
        """
        Test Step 3: Date navigation
        
        Returns:
            Dict with test results and any errors
        """
        print("📅 Testing Step 3: Date Functionality")
        
        scraper = self.scraper_class(self.config)
        test_result = {
            "step": "date",
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "date_navigation_tests": [],
            "error": None
        }
        
        # Test with 3 dates: yesterday, today, tomorrow
        today = datetime.now()
        test_dates = [
            (today - timedelta(days=1)).strftime("%m/%d/%Y"),
            today.strftime("%m/%d/%Y"),
            (today + timedelta(days=1)).strftime("%m/%d/%Y")
        ]
        
        try:
            async with scraper.browser_session():
                # Handle login if required
                if await scraper.requires_login():
                    await scraper.login()
                
                # Navigate to first available channel
                channels = await scraper.enumerate_channels()
                if channels:
                    await scraper.navigate_to_channel(channels[0])
                
                # Test date navigation
                for date in test_dates:
                    print(f"  ↳ Testing navigate_to_date('{date}')...")
                    
                    date_test = {
                        "date": date,
                        "success": False,
                        "error": None,
                        "page_dump_saved": False
                    }
                    
                    try:
                        success = await scraper.navigate_to_date(date)
                        date_test["success"] = success
                        
                        # Check if page dump was saved
                        expected_dump = scraper.output_dir / f"date_{date.replace('/', '_')}.html"
                        date_test["page_dump_saved"] = expected_dump.exists()
                        
                        print(f"    Date '{date}' navigation: {success}, Page dump: {date_test['page_dump_saved']}")
                        
                    except NotImplementedError as e:
                        date_test["error"] = f"Method not implemented: {str(e)}"
                        print(f"    Date '{date}' navigation: Not implemented")
                    except Exception as e:
                        date_test["error"] = str(e)
                        print(f"    Date '{date}' navigation failed: {str(e)}")
                    
                    test_result["date_navigation_tests"].append(date_test)
                
                # Check if all date tests passed
                all_passed = all(test["success"] for test in test_result["date_navigation_tests"])
                test_result["success"] = all_passed
                
                if all_passed:
                    print("✅ Step 3: Date functionality working")
                else:
                    print("❌ Step 3: Some date navigation tests failed")
                
        except Exception as e:
            test_result["error"] = str(e)
            print(f"❌ Step 3: Date test failed - {str(e)}")
        
        self.results["date_test"] = test_result
        return test_result
    
    # ==================== STEP 4: PROGRAM TESTING ====================
    
    async def test_program_functionality(self) -> Dict[str, Any]:
        """
        Test Step 4: Program data collection
        
        Returns:
            Dict with test results and any errors
        """
        print("🎬 Testing Step 4: Program Functionality")
        
        scraper = self.scraper_class(self.config)
        test_result = {
            "step": "program",
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "has_program_details": None,
            "has_downloads": None,
            "program_tests": [],
            "error": None
        }
        
        try:
            async with scraper.browser_session():
                # Handle login if required
                if await scraper.requires_login():
                    await scraper.login()
                
                # Navigate to first available channel
                channels = await scraper.enumerate_channels()
                if channels:
                    await scraper.navigate_to_channel(channels[0])
                
                # Navigate to today's date
                today = datetime.now().strftime("%m/%d/%Y")
                await scraper.navigate_to_date(today)
                
                # Test program functionality flags
                print("  ↳ Testing has_program_details()...")
                has_details = await scraper.has_program_details()
                test_result["has_program_details"] = has_details
                print(f"    Has program details: {has_details}")
                
                print("  ↳ Testing has_downloads()...")
                has_downloads = await scraper.has_downloads()
                test_result["has_downloads"] = has_downloads
                print(f"    Has downloads: {has_downloads}")
                
                # Test program details if available
                if has_details:
                    print("  ↳ Testing program detail functionality...")
                    
                    # Get current page HTML
                    page_html = await scraper._page.content()
                    
                    # Get program selectors
                    program_selectors = await scraper.get_program_selectors(page_html, today)
                    print(f"    Found {len(program_selectors)} program selectors")
                    
                    # Test navigation to first 2 programs
                    test_programs = program_selectors[:2]
                    
                    for i, program in enumerate(test_programs):
                        print(f"  ↳ Testing program {i+1} navigation...")
                        
                        program_test = {
                            "program_index": i,
                            "program_data": program,
                            "navigation_success": False,
                            "error": None
                        }
                        
                        try:
                            success = await scraper.navigate_to_program(
                                program.get('selector', ''),
                                program.get('url'),
                                today
                            )
                            program_test["navigation_success"] = success
                            print(f"    Program {i+1} navigation: {success}")
                            
                        except Exception as e:
                            program_test["error"] = str(e)
                            print(f"    Program {i+1} navigation failed: {str(e)}")
                        
                        test_result["program_tests"].append(program_test)
                
                # Test downloads if available
                if has_downloads:
                    print("  ↳ Testing download functionality...")
                    
                    try:
                        downloaded_files = await scraper.download_files(today)
                        print(f"    Downloaded {len(downloaded_files)} files")
                        test_result["downloaded_files"] = downloaded_files
                    except Exception as e:
                        print(f"    Download test failed: {str(e)}")
                        test_result["download_error"] = str(e)
                
                test_result["success"] = True
                print("✅ Step 4: Program functionality tested")
                
        except Exception as e:
            test_result["error"] = str(e)
            print(f"❌ Step 4: Program test failed - {str(e)}")
        
        self.results["program_test"] = test_result
        return test_result
    
    # ==================== FULL WORKFLOW TESTING ====================
    
    async def run_full_workflow(self) -> Dict[str, Any]:
        """
        Run the complete scraping workflow for production testing
        
        Returns:
            Dict with workflow results
        """
        print("🚀 Running Full Workflow")
        
        workflow_result = {
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "channels_processed": 0,
            "dates_processed": 0,
            "programs_collected": 0,
            "files_downloaded": 0,
            "error": None
        }
        
        try:
            scraper = self.scraper_class(self.config)
            
            async with scraper.browser_session():
                # Step 1: Authentication
                if await scraper.requires_login():
                    await scraper.login()
                
                # Step 2: Get target channels
                available_channels = await scraper.enumerate_channels()
                target_channels = self.config.target_channels or available_channels[:1]
                
                # Step 3: Process each channel
                for channel in target_channels:
                    print(f"  📺 Processing channel: {channel}")
                    await scraper.navigate_to_channel(channel)
                    
                    # Step 4: Process date range
                    date_range = self._generate_date_range()
                    
                    for date in date_range:
                        print(f"    📅 Processing date: {date}")
                        
                        # Navigate to date
                        await scraper.navigate_to_date(date)
                        workflow_result["dates_processed"] += 1
                        
                        # Collect program data based on website capabilities
                        if await scraper.has_program_details():
                            page_html = await scraper._page.content()
                            programs = await scraper.get_program_selectors(page_html, date)
                            
                            for program in programs:
                                await scraper.navigate_to_program(
                                    program.get('selector', ''),
                                    program.get('url'),
                                    date
                                )
                                workflow_result["programs_collected"] += 1
                        
                        # Download files if available
                        if await scraper.has_downloads():
                            files = await scraper.download_files(date)
                            workflow_result["files_downloaded"] += len(files)
                    
                    workflow_result["channels_processed"] += 1
                
                workflow_result["success"] = True
                print("✅ Full workflow completed successfully")
                
        except Exception as e:
            workflow_result["error"] = str(e)
            print(f"❌ Full workflow failed: {str(e)}")
        
        self.results["full_workflow"] = workflow_result
        return workflow_result
    
    def _generate_date_range(self) -> List[str]:
        """Generate date range from config"""
        if not self.config.from_date or not self.config.to_date:
            # Default to today only
            return [datetime.now().strftime("%m/%d/%Y")]
        
        start_date = datetime.strptime(self.config.from_date, "%m/%d/%Y")
        end_date = datetime.strptime(self.config.to_date, "%m/%d/%Y")
        
        dates = []
        current_date = start_date
        
        while current_date <= end_date:
            dates.append(current_date.strftime("%m/%d/%Y"))
            current_date += timedelta(days=1)
        
        return dates
    
    def save_test_results(self, output_file: str = None):
        """Save all test results to JSON file"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"test_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Test results saved to: {output_file}")
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*50)
        print("TEST RESULTS SUMMARY")
        print("="*50)
        
        for step, result in self.results.items():
            if result:
                status = "✅ PASS" if result.get("success") else "❌ FAIL"
                print(f"{step.upper()}: {status}")
                if result.get("error"):
                    print(f"  Error: {result['error']}")
        
        print("="*50)
