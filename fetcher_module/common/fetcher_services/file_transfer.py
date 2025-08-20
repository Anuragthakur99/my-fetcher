"""Main file transfer orchestration"""

import asyncio
import os
from typing import Dict, Any
from .connection import create_connection
from .listing import list_files
from .filtering import filter_files
from .sorting import sort_files
from .download import download_files


async def run_file_transfer(job_config: Dict[str, Any], temp_dir: str) -> Dict[str, Any]:
    """
    Main file transfer function that integrates all services.
    
    Args:
        job_config: Job configuration dictionary
        temp_dir: Temporary directory for downloads
        
    Returns:
        Dict with success status and downloaded files
    """
    try:
        # Update config with temp directory
        config = dict(job_config)
        config['local_download_path'] = temp_dir
        
        # Create connection
        fs, conn_options = create_connection(config)
        if not fs:
            return {"success": False, "error": "Failed to create connection", "files_downloaded": []}
        
        try:
            # List files
            file_list = list_files(fs, config)
            if not file_list:
                return {"success": True, "files_downloaded": [], "metadata": {"message": "No files found"}}
            
            # Filter files
            print(f"\n=== FILTERING ({len(file_list)} files) ===")
            filtered_files = filter_files(file_list, config)
            print(f"=== AFTER FILTERING: {len(filtered_files)} files remain ===")
            if not filtered_files:
                return {"success": True, "files_downloaded": [], "metadata": {"message": "No files match filters"}}
            
            # Sort files
            print(f"\n=== SORTING ({len(filtered_files)} files) ===")
            sorted_files = sort_files(filtered_files, config)
            print(f"=== AFTER SORTING: {len(sorted_files)} files ===")
            
            # Download files with detailed logging
            print(f"\n=== STARTING DOWNLOAD ({len(sorted_files)} files) ===")
            success_count, total_count = download_files(fs, sorted_files, config)
            print(f"=== DOWNLOAD COMPLETE: {success_count} success, {total_count - success_count} failed ===")
            
            # Get list of downloaded files
            downloaded_files = []
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        downloaded_files.append(os.path.join(root, file))
            
            return {
                "success": success_count > 0,
                "files_downloaded": downloaded_files,
                "metadata": {
                    "total_found": len(file_list),
                    "after_filtering": len(filtered_files),
                    "after_sorting": len(sorted_files),
                    "downloaded": success_count,
                    "failed": total_count - success_count
                }
            }
            
        finally:
            # Close connection
            if hasattr(fs, 'close'):
                fs.close()
                
    except Exception as e:
        return {"success": False, "error": str(e), "files_downloaded": []}