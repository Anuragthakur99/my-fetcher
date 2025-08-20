#!/usr/bin/env python3
"""
Simple test script to verify cookie saving functionality using YLE Areena
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.browser_service import BrowserService
from src.models.task_models import TaskContext
from src.utils.config import config

async def test_cookie_saving():
    """Test cookie saving functionality with YLE Areena"""
    print("🧪 Testing Cookie Saving Functionality with YLE Areena")
    print("=" * 60)
    
    # Create a test session
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S_test")
    browser_service = BrowserService(session_id)
    
    try:
        # Initialize browser
        print("1. Initializing browser...")
        await browser_service.initialize()
        print("✅ Browser initialized")
        
        # Navigate to YLE Areena TV guide (real website with cookies)
        print("\n2. Navigating to YLE Areena TV guide...")
        if browser_service.current_page:
            await browser_service.current_page.goto("https://areena.yle.fi/tv/opas", timeout=60000)
            print("✅ Navigation to YLE Areena complete")
            
            # Wait for page to load and cookies to be set
            await asyncio.sleep(3)
            
            # Get page title to confirm we're on the right page
            title = await browser_service.current_page.title()
            print(f"   Page title: {title}")
            
        else:
            print("❌ No current page available")
            return
        
        # Test cookie extraction
        print("\n3. Testing cookie extraction...")
        
        # Create a test task context
        session_dir = config.get_session_dir(session_id)
        task_dir = session_dir / "test_task"
        task_dir.mkdir(parents=True, exist_ok=True)
        
        task_context = TaskContext(
            session_id=session_id,
            target_url="https://areena.yle.fi/tv/opas",
            channel_name="YLE Areena Test",
            task_dir=task_dir,
            previous_results={},
            login_credentials=None
        )
        
        # Extract and save cookies
        cookies_path = await browser_service._extract_and_save_cookies("test_task", task_context)
        
        if cookies_path:
            print(f"✅ Cookies saved to: {cookies_path}")
            
            # Verify files exist
            cookies_file = task_dir / "test_task_cookies.json"
            storage_state_file = task_dir / "storage_state.json"  # Updated to correct filename
            
            print(f"\n4. Verifying saved files...")
            print(f"   Raw cookies file exists: {cookies_file.exists()}")
            print(f"   Storage state file exists: {storage_state_file.exists()}")
            
            # Check raw cookies content
            if cookies_file.exists():
                with open(cookies_file, 'r') as f:
                    cookies_data = json.load(f)
                print(f"   Raw cookies count: {len(cookies_data)}")
                
                if cookies_data:
                    print("   Sample cookies from YLE Areena:")
                    for i, cookie in enumerate(cookies_data[:3]):  # Show first 3 cookies
                        print(f"     Cookie {i+1}: {cookie.get('name', 'unnamed')} = {cookie.get('value', '')[:50]}...")
                        print(f"       Domain: {cookie.get('domain', 'N/A')}")
                        print(f"       Path: {cookie.get('path', 'N/A')}")
                        print(f"       Secure: {cookie.get('secure', False)}")
                        print(f"       HttpOnly: {cookie.get('httpOnly', False)}")
                        print()
                        
                    # Look for authentication-related cookies
                    auth_cookies = [c for c in cookies_data if any(auth in c.get('name', '').lower() 
                                   for auth in ['login', 'auth', 'token', 'session', 'user'])]
                    print(f"   Authentication-related cookies found: {len(auth_cookies)}")
                    for auth_cookie in auth_cookies:
                        print(f"     Auth cookie: {auth_cookie.get('name', 'unnamed')}")
            
            # Check storage state content
            if storage_state_file.exists():
                try:
                    with open(storage_state_file, 'r') as f:
                        storage_data = json.load(f)
                    print(f"   Storage state keys: {list(storage_data.keys())}")
                    
                    if 'cookies' in storage_data:
                        print(f"   Storage state cookies count: {len(storage_data['cookies'])}")
                        
                    if 'origins' in storage_data:
                        print(f"   Storage origins count: {len(storage_data['origins'])}")
                        for origin in storage_data['origins'][:2]:  # Show first 2 origins
                            print(f"     Origin: {origin.get('origin', 'N/A')}")
                            if 'localStorage' in origin:
                                print(f"       localStorage items: {len(origin['localStorage'])}")
                            if 'sessionStorage' in origin:
                                print(f"       sessionStorage items: {len(origin['sessionStorage'])}")
                                
                except Exception as e:
                    print(f"   Storage state read error: {e}")
            
            print(f"\n✅ Cookie saving test completed successfully!")
            print(f"   Files saved in: {task_dir}")
            print(f"   This demonstrates that cookies from YLE Areena are properly captured")
            print(f"   and saved in both raw format and storage state format.")
            
        else:
            print("❌ Cookie saving failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        print("\n5. Cleaning up...")
        await browser_service.close()
        print("✅ Browser closed")

if __name__ == "__main__":
    asyncio.run(test_cookie_saving())
