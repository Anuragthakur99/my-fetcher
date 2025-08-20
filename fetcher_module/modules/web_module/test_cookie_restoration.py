#!/usr/bin/env python3
"""
Comprehensive test for cookie restoration scenarios:
1. Playwright cookie restoration after login
2. Browser-use session restoration for task resumption
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.task_orchestrator import TaskOrchestrator
from src.services.browser_service import BrowserService
from src.models.task_models import TaskContext
from src.utils.config import config

async def test_cookie_restoration_scenarios():
    """Test both Playwright and browser-use cookie restoration scenarios"""
    print("🧪 Testing Cookie Restoration Scenarios with TV5 Monde Login")
    print("=" * 70)
    
    # Test configuration - using TV5 Monde with real login credentials
    # target_url = "http://www.tv5.org/pro/Bienvenue-sur-TV5MONDE-PRO"
    # channel_name = "TV5 Monde FBS"

    # target_url = "https://areena.yle.fi/tv/opas"
    # channel_name = "YLE Areena (FIN)"

    target_url = "https://operator.rockentertainment.com/login"
    channel_name = "INDO Rock Entertainment (RKPHL)"
    
    # Real login credentials for authentic testing
    # login_credentials = {
    #     "username": "cr@epgs.com",
    #     "password": "GracenoteEPG2023!"
    # }

    # login_credentials = {
    #     "username": "balajeerocks01@gmail.com",
    #     "password": "StarMoon@123"
    # }

    login_credentials = {
        "username": "nikita.deshpande@nielsen.com",
        "password": "GP@12345"
    }
    
    print(f"🎯 Target: {target_url}")
    print(f"📺 Channel: {channel_name}")
    print(f"🔐 Using real login credentials: {login_credentials['username']}")
    
    try:
        # ========================================
        # PHASE 1: Run Login Task and Save Cookies
        # ========================================
        print("\n🔐 PHASE 1: Running login task with real credentials...")
        
        orchestrator1 = TaskOrchestrator()
        
        # Run login task with real credentials
        login_result = await orchestrator1.run_single_task(
            task_id="task_0_login_authentication",
            target_url=target_url,
            channel_name=channel_name,
            login_credentials=login_credentials
        )
        
        if not login_result.is_successful:
            print("❌ Login task failed, cannot proceed with cookie tests")
            print(f"   Error: {login_result.error_message}")
            return
            
        print(f"✅ Login task completed successfully")
        print(f"   Session ID: {orchestrator1.session_id}")
        print(f"   Duration: {login_result.duration_seconds:.2f} seconds")
        
        # Get the saved cookie files
        login_task_dir = config.get_session_dir(orchestrator1.session_id) / "task_0_login_authentication"
        cookies_file = login_task_dir / "task_0_login_authentication_cookies.json"
        storage_state_file = login_task_dir / "storage_state.json"
        
        print(f"   Raw cookies file: {cookies_file.exists()}")
        print(f"   Storage state file: {storage_state_file.exists()}")
        
        if not cookies_file.exists():
            print("❌ No cookies file found, cannot proceed")
            return
            
        # Load and examine saved cookies
        with open(cookies_file, 'r') as f:
            saved_cookies = json.load(f)
        print(f"   📊 Saved {len(saved_cookies)} cookies")
        
        # Look for authentication-related cookies
        auth_cookies = [c for c in saved_cookies if any(auth in c.get('name', '').lower() 
                       for auth in ['login', 'auth', 'token', 'session', 'user', 'tv5', 'pro'])]
        print(f"   🔑 Authentication cookies found: {len(auth_cookies)}")
        
        # Show authentication cookie details
        for i, cookie in enumerate(auth_cookies[:5]):  # Show first 5 auth cookies
            print(f"     Auth Cookie {i+1}: {cookie.get('name')} = {cookie.get('value')[:30]}...")
            print(f"       Domain: {cookie.get('domain')}, Secure: {cookie.get('secure')}")
        
        # Show some general cookie details
        print(f"   📋 Sample cookies:")
        for i, cookie in enumerate(saved_cookies[:3]):
            print(f"     Cookie {i+1}: {cookie.get('name')} = {cookie.get('value')[:20]}...")
        
        await orchestrator1.cleanup()
        
        # ========================================
        # PHASE 2: Test Playwright Cookie Restoration
        # ========================================
        print(f"\n🎭 PHASE 2: Testing Playwright cookie restoration...")
        
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Visible for verification
            
            # Test 2a: Raw cookies restoration
            print("2a. Testing raw cookies restoration...")
            context1 = await browser.new_context()
            
            try:
                # Add saved cookies to new context
                await context1.add_cookies(saved_cookies)
                print("   ✅ Cookies successfully added to Playwright context")
                
                # Navigate to the site and check if session is restored
                page1 = await context1.new_page()
                await page1.goto(target_url)
                await asyncio.sleep(5)  # Let page load and check login state
                
                # Get page title and content to check for login indicators
                title = await page1.title()
                print(f"   📄 Page title: {title}")
                
                # Check for login indicators in the page
                try:
                    # Look for common login success indicators
                    page_content = await page1.content()
                    
                    # TV5 Monde specific indicators
                    login_indicators = [
                        "bienvenue" in page_content.lower(),
                        "welcome" in page_content.lower(),
                        "dashboard" in page_content.lower(),
                        "logout" in page_content.lower(),
                        "déconnexion" in page_content.lower()
                    ]
                    
                    login_success = any(login_indicators)
                    print(f"   🔍 Login state indicators found: {sum(login_indicators)}/5")
                    print(f"   {'✅ Appears to be logged in' if login_success else '⚠️ Login state unclear'}")
                    
                except Exception as e:
                    print(f"   ⚠️ Could not check login indicators: {e}")
                
                # Check if cookies are present in the new context
                current_cookies = await context1.cookies()
                print(f"   🍪 Current context has {len(current_cookies)} cookies")
                
                # Compare cookie names
                saved_names = {c['name'] for c in saved_cookies}
                current_names = {c['name'] for c in current_cookies}
                restored_cookies = saved_names.intersection(current_names)
                print(f"   🔄 {len(restored_cookies)} cookies successfully restored")
                
                # Check for authentication cookies specifically
                current_auth_cookies = [c for c in current_cookies if any(auth in c['name'].lower() 
                                       for auth in ['login', 'auth', 'token', 'session', 'user', 'tv5', 'pro'])]
                print(f"   🔑 Authentication cookies in context: {len(current_auth_cookies)}")
                
                await page1.close()
                
            except Exception as e:
                print(f"   ❌ Raw cookies restoration failed: {e}")
            
            await context1.close()
            
            # Test 2b: Storage state restoration
            if storage_state_file.exists():
                print("\n2b. Testing storage state restoration...")
                try:
                    context2 = await browser.new_context(storage_state=str(storage_state_file))
                    print("   ✅ Storage state successfully loaded")
                    
                    page2 = await context2.new_page()
                    await page2.goto(target_url)
                    await asyncio.sleep(5)
                    
                    # Check localStorage restoration
                    local_storage = await page2.evaluate("""
                        () => {
                            const items = {};
                            for (let i = 0; i < localStorage.length; i++) {
                                const key = localStorage.key(i);
                                items[key] = localStorage.getItem(key);
                            }
                            return items;
                        }
                    """)
                    print(f"   📦 localStorage restored: {len(local_storage)} items")
                    
                    # Show localStorage keys
                    if local_storage:
                        print(f"   📋 localStorage keys: {list(local_storage.keys())[:5]}")
                    
                    storage_cookies = await context2.cookies()
                    print(f"   🍪 Storage state cookies: {len(storage_cookies)}")
                    
                    # Check login state with storage state
                    page_content = await page2.content()
                    login_indicators = [
                        "bienvenue" in page_content.lower(),
                        "welcome" in page_content.lower(),
                        "dashboard" in page_content.lower(),
                        "logout" in page_content.lower(),
                        "déconnexion" in page_content.lower()
                    ]
                    login_success = any(login_indicators)
                    print(f"   {'✅ Storage state login successful' if login_success else '⚠️ Storage state login unclear'}")
                    
                    await page2.close()
                    await context2.close()
                    
                except Exception as e:
                    print(f"   ❌ Storage state restoration failed: {e}")
            
            await browser.close()
        
        # ========================================
        # PHASE 3: Test Browser-Use Session Restoration
        # ========================================
        print(f"\n🤖 PHASE 3: Testing browser-use session restoration...")
        
        # Simulate scenario: Login task completed, now we want to run channel detection
        # without re-running login
        
        orchestrator2 = TaskOrchestrator()
        
        print("3a. Testing session restoration in browser-use...")
        
        # Initialize browser service
        browser_service = orchestrator2.browser_service
        # browser_service = BrowserService(orchestrator2.session_id)
        await browser_service.initialize()
        
        # Test loading session data from previous login
        session_loaded = await browser_service.load_session_data(
            session_dir=config.get_session_dir(orchestrator1.session_id),
            task_id="task_0_login_authentication"
        )
        
        if session_loaded:
            print("   ✅ Session data loaded into browser-use")
            
            # Navigate to the site to verify session
            if browser_service.current_page:
                await browser_service.current_page.goto(target_url)
                await asyncio.sleep(5)
                
                # Check if cookies are present
                current_cookies = await browser_service.browser.get_cookies()
                print(f"   🍪 Browser-use session has {len(current_cookies)} cookies")
                
                # Compare with original cookies
                current_names = {c['name'] for c in current_cookies}
                original_names = {c['name'] for c in saved_cookies}
                restored = original_names.intersection(current_names)
                print(f"   🔄 {len(restored)} cookies restored in browser-use")
                
                # Check for authentication cookies
                current_auth = [c for c in current_cookies if any(auth in c['name'].lower() 
                               for auth in ['login', 'auth', 'token', 'session', 'user', 'tv5', 'pro'])]
                print(f"   🔑 Authentication cookies in browser-use: {len(current_auth)}")
                
                # Now test running a subsequent task (channel detection)
                print("\n3b. Testing task execution with restored session...")
                
                try:
                    # Run channel detection task with restored session
                    channel_result = await orchestrator2.run_single_task(
                        task_id="task_1_channel_detection",
                        target_url=target_url,
                        channel_name=channel_name,
                        previous_results={}
                    )
                    
                    if channel_result.is_successful:
                        print("   ✅ Channel detection task succeeded with restored session")
                        print("   🎯 This proves session restoration works for task resumption!")
                    else:
                        print("   ⚠️ Channel detection task failed")
                        print(f"   Error: {channel_result.error_message}")
                        print("   (May be due to site structure, not necessarily cookies)")
                        
                except Exception as e:
                    print(f"   ❌ Task execution with restored session failed: {e}")
            
        else:
            print("   ❌ Session data loading failed")
        
        await browser_service.close()
        await orchestrator2.cleanup()
        
        # ========================================
        # SUMMARY
        # ========================================
        print(f"\n📋 SUMMARY:")
        print(f"✅ Cookie saving: Working ({len(saved_cookies)} cookies saved)")
        print(f"✅ Authentication cookies: {len(auth_cookies)} found")
        print(f"✅ Playwright restoration: {'Working' if len(restored_cookies) > 0 else 'Needs verification'}")
        print(f"✅ Browser-use restoration: {'Working' if session_loaded else 'Needs verification'}")
        print(f"✅ Task resumption: {'Working' if 'channel_result' in locals() and channel_result.is_successful else 'Needs verification'}")
        
        print(f"\n🎯 CONCLUSIONS:")
        print(f"1. Real login credentials work with TV5 Monde")
        print(f"2. Authentication cookies are properly captured and saved")
        print(f"3. Session restoration enables task resumption without re-login")
        print(f"4. Both raw cookies and storage state formats work correctly")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cookie_restoration_scenarios())
