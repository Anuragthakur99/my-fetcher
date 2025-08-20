"""
Example: Generate code from existing intelligence data
Run this after a successful intelligence gathering session to generate code without re-running tasks
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

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
    from src.models.task_models import TaskResult, TaskStatus
except ImportError:
    from core.task_orchestrator import TaskOrchestrator
    from models.task_models import TaskResult, TaskStatus

async def main():
    """Generate code from existing intelligence session"""
    # Configuration - Update these values
    # EXISTING_SESSION_ID = "20250630_113133_974801"  # Change to your session ID
    # EXISTING_SESSION_ID = "20250721_224112_767789"  # Change to your session ID
    EXISTING_SESSION_ID = "20250727_231106_132588"
    TARGET_URL = "http://www.tv5.org/pro/Bienvenue-sur-TV5MONDE-PRO"
    # TARGET_URL = "https://www.yourtv.com.au/guide/"
    CHANNEL_NAME = "TV5 Monde FBS"
    # CHANNEL_NAME = "Channel 9 (AUS)"
    
    # NEW: Choose code generation approach
    USE_ITERATIVE_APPROACH = True  # Set to False for original conversational approach

    print(f"🤖 TV Schedule Code Generator - From Existing Intelligence")
    print(f"Session ID: {EXISTING_SESSION_ID}")
    print(f"Target: {TARGET_URL}")
    print(f"Channel: {CHANNEL_NAME}")
    print(f"Approach: {'Iterative Step-by-Step' if USE_ITERATIVE_APPROACH else 'Original Conversational'}")
    print(f"🔍 Current working directory: {Path.cwd()}")
    print("="*80)
    
    try:
        login_credentials = {
            "username": "cr@epgs.com",
            "password": "GracenoteEPG2023!"
        }
        # Create orchestrator
        orchestrator = TaskOrchestrator(login_credentials)
        
        # Load existing intelligence data
        print("📂 Loading existing intelligence data...")
        
        # Try multiple possible paths for the session directory
        possible_paths = [
            # Absolute path from script location
            Path(__file__).parent.parent / "output" / EXISTING_SESSION_ID,
            # Relative path from current working directory
            Path("output") / EXISTING_SESSION_ID,
            # Direct path if user provided full path
            Path(EXISTING_SESSION_ID) if "/" in EXISTING_SESSION_ID else None
        ]
        
        session_dir = None
        for path in possible_paths:
            if path and path.exists():
                session_dir = path
                break
        
        print(f"🔍 Checked paths:")
        for i, path in enumerate(possible_paths):
            if path:
                exists = "✅" if path.exists() else "❌"
                print(f"  {i+1}. {exists} {path}")
        
        if not session_dir:
            print(f"❌ Session directory not found for ID: {EXISTING_SESSION_ID}")
            print("\n📁 Available sessions:")
            
            # Check multiple output directory locations
            output_dirs = [
                Path(__file__).parent.parent / "output",
                Path("output"),
                Path.cwd() / "output"
            ]
            
            for output_dir in output_dirs:
                if output_dir.exists():
                    print(f"\n📂 In {output_dir}:")
                    sessions = [d for d in output_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
                    if sessions:
                        for session in sorted(sessions):
                            print(f"  - {session.name}")
                    else:
                        print("  (no session directories found)")
                    break
            return
        
        print(f"✅ Found session directory: {session_dir}")
        
        # Load intelligence from each task
        task_ids = ["task_0_login_authentication","task_1_channel_detection", "task_2_date_navigation", "task_3_program_extraction"]
        # task_ids = ["task_0_login_authentication"]

        accumulated_intelligence = {}
        task_results = {}
        
        for task_id in task_ids:
            task_dir = session_dir / task_id
            intelligence_file = task_dir / f"website_intelligence_{task_id}.json"
            
            if intelligence_file.exists():
                print(f"✅ Loading intelligence for {task_id}")
                with open(intelligence_file, 'r', encoding='utf-8') as f:
                    intelligence_data = json.load(f)
                accumulated_intelligence[task_id] = intelligence_data
                
                # Create mock task result for code generation
                task_results[task_id] = TaskResult(
                    task_id=task_id,
                    status=TaskStatus.SUCCESS,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    outputs={'task_dir': task_dir},
                    intelligence_data=intelligence_data
                )
            else:
                print(f"⚠️ Intelligence file not found: {intelligence_file}")
        
        if not accumulated_intelligence:
            print("❌ No intelligence data found in session directory")
            return
        
        print(f"📊 Loaded intelligence for {len(accumulated_intelligence)} tasks")
        
        # Set up orchestrator with loaded data
        orchestrator.session_id = EXISTING_SESSION_ID
        orchestrator.session_dir = session_dir
        orchestrator.accumulated_intelligence = accumulated_intelligence
        orchestrator.task_results = task_results
        
        # Initialize analysis session
        try:
            from src.models.result_models import AnalysisSession
        except ImportError:
            from models.result_models import AnalysisSession
        orchestrator.analysis_session = AnalysisSession(
            session_id=EXISTING_SESSION_ID,
            target_url=TARGET_URL,
            channel_name=CHANNEL_NAME,
            start_time=datetime.now()
        )
        
        # Run code generation based on selected approach
        if USE_ITERATIVE_APPROACH:
            print("🔄 Starting iterative step-by-step code generation...")
            await orchestrator._execute_iterative_code_generation(TARGET_URL, CHANNEL_NAME)
        else:
            print("💬 Starting original conversational code generation...")
            await orchestrator._execute_conversational_code_generation(TARGET_URL, CHANNEL_NAME)
        
        # Finalize session
        orchestrator.analysis_session.end_time = datetime.now()
        
        print("✅ Code generation completed successfully!")
        print(f"📁 Results saved to: {session_dir}")
        
        # Look for generated scraper file
        scraper_files = list(session_dir.glob("*_scraper.py"))
        if scraper_files:
            print(f"🐍 Generated scraper: {scraper_files[0]}")
        
    except KeyboardInterrupt:
        print("\n⏹️ Code generation interrupted by user")
    except Exception as e:
        print(f"\n❌ Code generation failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
