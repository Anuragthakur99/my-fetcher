#!/usr/bin/env python3
"""
Test Script for Module System - Single Job Demo
Demonstrates single job execution with production-ready flow
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.cli_init import CLIInit


def test_single_job():
    """Test single job execution"""
    print("\n" + "="*60)
    print("TESTING SINGLE JOB EXECUTION")
    print("="*60)
    
    sys.argv = [
        "test_system.py",
        "--job-config", "job_config_details.json",
        "--environment", "local"
    ]
    
    # Set environment variable for global access
    # os.environ['ENVIRONMENT'] = "local"
    
    cli = CLIInit()
    success = cli.run()
    print(f"Single job test result: {'SUCCESS' if success else 'FAILED'}")
    return success


def main():
    """Run single job test"""
    print("MODULE SYSTEM SINGLE JOB DEMO")
    print("="*60)
    print("This script demonstrates single job execution")
    print("of the module orchestration system.")
    print("All operations use dummy data for demonstration.")
    print("="*60)
    
    try:
        success = test_single_job()
        
        print("\n" + "="*60)
        print("SINGLE JOB DEMO SUMMARY")
        print("="*60)
        
        status = "PASSED" if success else "FAILED"
        print(f"Single Job Execution: {status}")
        
        print("="*60)
        overall_status = "DEMO COMPLETED SUCCESSFULLY" if success else "DEMO FAILED"
        print(f"Overall Result: {overall_status}")
        print("="*60)
        
        return success
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
        return False
    except Exception as e:
        print(f"\nDemo execution failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
