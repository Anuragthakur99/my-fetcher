"""
Example: Run complete TV schedule analysis workflow
"""

import asyncio
import sys
from pathlib import Path

# Add project root and src to path for robust import resolution
project_root = Path(__file__).parent.parent
src_path = project_root / 'src'

# Add both project root and src to path
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Try importing with fallback for different environments
try:
    from src.core.task_orchestrator import TaskOrchestrator
    from src.services.universal_har_filter import UniversalHARNoiseFilter
except ImportError:
    from core.task_orchestrator import TaskOrchestrator
    from services.universal_har_filter import UniversalHARNoiseFilter

async def filter_session_har_file(orchestrator):
    """
    Filter the global HAR file after analysis completes.
    Uses the same logger as the orchestrator for consistent logging.
    """
    logger = orchestrator.logger
    session_dir = orchestrator.session_dir
    
    try:
        logger.info("🧹 Starting HAR file filtering...")
        
        # Find global HAR files in session directory
        har_files = list(session_dir.glob("network_traffic_*.har"))
        
        if not har_files:
            logger.warning("⚠️ No HAR files found in session directory for filtering")
            return
        
        if len(har_files) > 1:
            logger.info(f"📁 Found {len(har_files)} HAR files, filtering all of them")
        
        # Filter each HAR file found
        total_filtered = 0
        for har_file in har_files:
            try:
                # Generate filtered filename
                filtered_har_file = har_file.with_name(har_file.stem + "_FILTERED.har")
                
                logger.info(f"🔧 Filtering HAR file: {har_file.name}")
                
                # Create filter instance and process file
                filter_instance = UniversalHARNoiseFilter()
                result = filter_instance.filter_har_file(str(har_file), str(filtered_har_file))
                
                if result['success']:
                    logger.info(f"✅ HAR filtering completed: {har_file.name}")
                    logger.info(f"📊 Noise removed: {result['noise_removed']}/{result['original_count']} entries ({result['improvement_percentage']}%)")
                    logger.info(f"🎯 Golden APIs preserved: {result['filtered_count']} entries")
                    logger.info(f"📁 Filtered file saved: {filtered_har_file.name}")
                    
                    # Log categories filtered for debugging
                    if result['categories_filtered']:
                        categories_summary = ", ".join([f"{cat}: {count}" for cat, count in result['categories_filtered'].items()])
                        logger.debug(f"📋 Categories filtered: {categories_summary}")
                    
                    total_filtered += 1
                    
                else:
                    logger.error(f"❌ HAR filtering failed for {har_file.name}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"❌ Error filtering HAR file {har_file.name}: {str(e)}")
                logger.debug(f"HAR filtering error details: {str(e)}", exc_info=True)
        
        if total_filtered > 0:
            logger.info(f"🎉 HAR filtering completed successfully: {total_filtered}/{len(har_files)} files filtered")
        else:
            logger.warning("⚠️ No HAR files were successfully filtered")
            
    except Exception as e:
        logger.error(f"❌ HAR filtering process failed: {str(e)}")
        logger.debug(f"HAR filtering process error details: {str(e)}", exc_info=True)

async def main():
    """Run complete TV schedule analysis"""
    
    # Example TV schedule websites
    test_cases = [
        {
            "name": "Channel 9 Australia",
            "url": "https://www.yourtv.com.au/guide/",
            "channel": "Channel 9 (AUS)"
        },
        {
            "name": "BBC iPlayer",
            "url": "https://www.bbc.co.uk/iplayer/guide",
            "channel": "BBC One"
        },
        {
            "name" : "YLE Areena",
            "url": "https://areena.yle.fi/tv/opas",
            "channel": "YLE Areena (FIN)"
        },
        {
            "name" : "Reshet 13",
            "url": "https://reshet.tv/general/tv-guide/",
            "channel": "Reshet 13 (ISR)"
        },
        {
            "name" : "gatotv",
            "url": "https://www.gatotv.com/canal/37_republica_dominicana",
            "channel": "CDN (DOM)"
        },
        {
            "name" : "BBC Scotland",
            "url": "https://www.bbc.co.uk/iplayer/guide/bbcscotland",
            "channel": "BBC Scotland (GBR)"
        },
        {
            "name": "TV5 Monde",
            "url": "http://www.tv5.org/pro/Bienvenue-sur-TV5MONDE-PRO",
            "channel": "TV5 Monde FBS"
        },
        {
            "name": "SPOTV",
            "url": "https://www.spotvprime.co.kr/schedule",
            "channel": "SPOTV Prime 2"
        },
        {
            "name":"INDO Rock",
            "url": "https://operator.rockentertainment.com/login",
            "channel":"INDO Rock Entertainment (RKPHL)"
        },
        {
            "name":"TV Mail",
            "url":"https://tv.mail.ru/tashkent/channel/980/",
            "channel":"Futbol TV (UZB)"
        },
        {
            "name":"Idnes",
            "url":"https://tvprogram.idnes.cz/tvprogram.aspx?dt=***DATE***&cat=cz",
            "channel":"CT 2 (CZE)"
        }
    ]
    
    # Select test case
    test_case = test_cases[-5]  # Change index to test different sites
    
    # Optional: Login credentials (set to None if not needed)
    login_credentials = None
    # Example with login:

    # login_credentials = {
    #     "username": "balajeerocks01@gmail.com",
    #     "password": "StarMoon@123"
    # }

    login_credentials = {
        "username": "cr@epgs.com",
        "password": "GracenoteEPG2023!"
    }

    # login_credentials = {
    #     "username": "nikita.deshpande@nielsen.com",
    #     "password": "GP@12345"
    # }
    
    print(f"🎭 TV Schedule Analyzer - Task-Based Architecture")
    print(f"Target: {test_case['name']}")
    print(f"URL: {test_case['url']}")
    print(f"Channel: {test_case['channel']}")
    if login_credentials:
        print(f"🔐 Login: Enabled (username: {login_credentials['username']})")
    else:
        print(f"🔓 Login: Disabled")
    
    # Show profile configuration status
    try:
        from src.utils.config import config
    except ImportError:
        from utils.config import config
    if config.browser_profile_name:
        print(f"👤 Browser Profile: {config.browser_profile_name} (cleanup: {config.browser_profile_cleanup})")
    else:
        print(f"👤 Browser Profile: Default (set BROWSER_PROFILE_NAME in .env for persistent sessions)")
    
    print("="*80)
    
    try:
        # Create task orchestrator
        orchestrator = TaskOrchestrator()
        
        # Run complete analysis with optional login
        session = await orchestrator.run_full_analysis(
            target_url=test_case['url'],
            channel_name=test_case['channel'],
            login_credentials=login_credentials
        )
        
        # Filter HAR file after analysis completes
        await filter_session_har_file(orchestrator)
        
        # Print results
        orchestrator.print_session_summary()
        
        # Print file locations
        print(f"\n📁 Results saved to: {orchestrator.session_dir}")
        print(f"📊 Session ID: {session.session_id}")
        
        if session.is_complete:
            print("✅ Analysis completed successfully!")
        else:
            print("⚠️ Analysis completed with some failures")
            
    except KeyboardInterrupt:
        print("\n⏹️ Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Analysis failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
