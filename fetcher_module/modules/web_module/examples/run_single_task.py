"""
Example: Run individual task for debugging/testing - ALL TASKS SUPPORTED
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from src.core.task_orchestrator import TaskOrchestrator

async def main():
    """Run single task for debugging - supports all tasks including login"""
    
    # ========== WEBSITE CONFIGURATION ==========
    # Uncomment the website you want to test:
    
    # YLE Areena (Finland) - with login
    # target_url = "https://areena.yle.fi/tv/opas"
    # channel_name = "YLE Areena (FIN)"

    # target_url = "http://www.tv5.org/pro/Bienvenue-sur-TV5MONDE-PRO"
    # channel_name = "TV5 Monde FBS"
    
    # # Channel 9 (Australia) - no login
    # target_url = "https://www.yourtv.com.au/guide/"
    # channel_name = "Channel 9 (AUS)"
    
    # # BBC iPlayer (UK) - no login  
    target_url = "https://www.bbc.co.uk/iplayer/guide"
    channel_name = "BBC One"
    
    # # BBC Scotland (UK) - no login
    # target_url = "https://www.bbc.co.uk/iplayer/guide/bbcscotland"
    # channel_name = "BBC Scotland (GBR)"
    
    # ========== TASK CONFIGURATION ==========
    # Uncomment the task you want to run:
    
    # LOGIN TASK - Run this first to debug login issues
    # task_id = "task_0_login_authentication"
    
    # # CHANNEL DETECTION TASK - Test channel navigation
    # task_id = "task_1_channel_detection"
    
    # # DATE NAVIGATION TASK - Test date navigation
    # task_id = "task_2_date_navigation"
    
    # # PROGRAM EXTRACTION TASK - Test program data extraction
    task_id = "task_3_program_extraction"
    
    # # SITE BEHAVIOR TASK - Test site behavior analysis
    # task_id = "task_4_site_behavior"
    
    # ========== LOGIN CREDENTIALS ==========
    # Set login credentials if running task_0_login_authentication
    # Comment out if running other tasks or testing sites without login
    
    # login_credentials = {
    #     "username": "balajeerocks01@gmail.com",
    #     "password": "StarMoon@123"
    # } if task_id == "task_0_login_authentication" else None

    login_credentials = {
        "username": "cr@epgs.com",
        "password": "GracenoteEPG2023!"
    } if task_id == "task_0_login_authentication" else None
    
    # ========== EXECUTION ==========
    print(f"🎯 Single Task Execution: {task_id}")
    print(f"Target: {target_url}")
    print(f"Channel: {channel_name}")
    if login_credentials:
        print(f"🔐 Login: {login_credentials['username']}")
    else:
        print(f"🔓 Login: Not required for this task")
    print("="*60)
    
    try:
        # Create task orchestrator
        orchestrator = TaskOrchestrator()
        
        # Run single task with login credentials if needed
        task_result = await orchestrator.run_single_task(
            task_id=task_id,
            target_url=target_url,
            channel_name=channel_name,
            login_credentials=login_credentials
        )
        
        # Print results
        print(f"\n📋 Task Result:")
        print(f"Status: {'✅ SUCCESS' if task_result.is_successful else '❌ FAILED'}")
        print(f"Duration: {task_result.duration_seconds:.2f} seconds")
        
        if task_result.error_message:
            print(f"❌ Error: {task_result.error_message}")
        
        print(f"\n📁 Task outputs:")
        for output_name, output_path in task_result.outputs.items():
            print(f"  {output_name}: {output_path}")
        
        print(f"\n📊 Task Directory: {task_result.outputs.get('task_dir', 'N/A')}")
        
        # Task-specific debugging information
        if task_id == "task_0_login_authentication":
            print(f"\n🔐 Login Task Debug Info:")
            print(f"  - Check conversation logs for login form detection issues")
            print(f"  - Check GIF recording to see visual login process")
            print(f"  - Check HAR files for authentication network requests")
            print(f"  - Look for form filling errors in browser logs")
        elif task_id == "task_1_channel_detection":
            print(f"\n📺 Channel Detection Debug Info:")
            print(f"  - Check if channel navigation was found and tested")
            print(f"  - Look for popup/consent banner handling")
            print(f"  - Verify channel selectors in intelligence output")
        elif task_id == "task_2_date_navigation":
            print(f"\n📅 Date Navigation Debug Info:")
            print(f"  - Check if date navigation patterns were discovered")
            print(f"  - Look for calendar/date picker interactions")
            print(f"  - Verify date selectors work correctly")
        elif task_id == "task_3_program_extraction":
            print(f"\n📋 Program Extraction Debug Info:")
            print(f"  - Check if program data was successfully extracted")
            print(f"  - Look for program detail access patterns")
            print(f"  - Verify program selectors and data structure")
        elif task_id == "task_4_site_behavior":
            print(f"\n⚡ Site Behavior Debug Info:")
            print(f"  - Check performance analysis results")
            print(f"  - Look for error handling patterns")
            print(f"  - Verify optimization recommendations")
        
    except KeyboardInterrupt:
        print("\n⏹️ Task execution interrupted by user")
    except Exception as e:
        print(f"\n❌ Task execution failed: {str(e)}")
        print(f"\n🔍 Full error traceback:")
        import traceback
        traceback.print_exc()
        
        # Additional debugging suggestions
        print(f"\n💡 Debugging Suggestions:")
        print(f"  1. Check if the website is accessible: {target_url}")
        print(f"  2. Verify AWS credentials are configured correctly")
        print(f"  3. Check browser-use and Playwright installation")
        print(f"  4. Look at the session logs in output directory")
        if task_id == "task_0_login_authentication":
            print(f"  5. Verify login credentials are correct")
            print(f"  6. Check if the website requires different login flow")
        raise

if __name__ == "__main__":
    asyncio.run(main())
