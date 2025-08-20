"""CLI Initialization - Single Job Orchestrator Entry Point"""

import argparse
import sys
import os
import json
import asyncio
from common.logger import StructuredLogger
from common.config_loader.env_selector import EnvironmentSelector
from common.job_config import JobConfigManager
from common.module_factory import ModuleFactory


class CLIInit:
    """CLI to orchestrate single module job execution"""
    
    def __init__(self):
        self.logger = StructuredLogger("system", "cli", "orchestrator_cli")
        self.job_config_manager = None
    
    def parse_arguments(self):
        """Parse command line arguments"""
        parser = argparse.ArgumentParser(
            description="Module Orchestrator - Execute single data processing job"
        )
        
        parser.add_argument("--job-config", required=True,
                          help="JSON file containing job configuration")
        
        parser.add_argument("--environment", choices=["local", "dev", "nonprod", "prod"], 
                          default="local", help="Environment to run in (default: local)")
        
        return parser.parse_args()
    
    def setup_environment(self, environment: str = "local"):
        """Setup execution environment"""
        try:
            self.logger.info("Setting up orchestrator environment", {
                "environment": environment
            })
            
            self.job_config_manager = JobConfigManager(environment, self.logger)
            
            self.logger.info("Environment setup completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Environment setup failed: {str(e)}")
            return False
    
    async def execute_job(self, job_config_file: str) -> bool:
        """Execute single job from configuration file"""
        try:
            self.logger.info("Executing job", {"job_config_file": job_config_file})
            
            with open(job_config_file, 'r') as f:
                job_data = json.load(f)
            
            job_id = job_data.get("job_id")
            channel_number = job_data.get("channel_number")
            source_type = job_data.get("source_type")
            
            if not all([job_id, channel_number is not None, source_type]):
                self.logger.error("Invalid job configuration - missing required fields")
                return False
            
            self.logger.info("Job configuration loaded", {
                "job_id": job_id,
                "channel_number": channel_number,
                "source_type": source_type
            })
            
            job_config = self.job_config_manager.create_job_config(job_data)
            if not job_config:
                self.logger.error("Failed to create job configuration")
                return False
            
            module = ModuleFactory.create_module(job_config)
            if not module:
                self.logger.error(f"Failed to create module for source type: {source_type}")
                return False
            
            self.logger.info("Starting job execution")
            result = await module.execute()
            
            if result.get("success", False):
                self.logger.info("Job execution completed successfully", result)
                return True
            else:
                self.logger.error("Job execution failed", result)
                return False
            
        except Exception as e:
            self.logger.error(f"Job execution failed: {str(e)}")
            return False
    
    def run(self):
        """Main execution method"""
        try:
            args = self.parse_arguments()
            
            os.environ['ENVIRONMENT'] = args.environment
            
            self.logger.info("Starting job orchestrator", {
                "job_config_file": args.job_config,
                "environment": args.environment
            })
            
            if not self.setup_environment(args.environment):
                self.logger.error("Failed to setup environment")
                return False
            
            success = asyncio.run(self.execute_job(args.job_config))
            
            self.logger.info("Job orchestrator completed", {"success": success})
            return success
            
        except KeyboardInterrupt:
            self.logger.info("Execution interrupted by user")
            return False
            
        except Exception as e:
            self.logger.error(f"CLI execution failed: {str(e)}")
            return False


def main():
    """Entry point for CLI"""
    cli = CLIInit()
    success = cli.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
