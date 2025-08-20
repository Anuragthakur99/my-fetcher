#!/usr/bin/env python3
"""
File listing service for remote file systems.
"""
import logging
import datetime
import fsspec
import os
import re
import time
from typing import Dict, List, Any, Optional

# Import botocore for S3-specific error handling
try:
    import botocore.exceptions
    BOTOCORE_AVAILABLE = True
except ImportError:
    BOTOCORE_AVAILABLE = False

from .utils import format_file_size

logger = logging.getLogger(__name__)

def _should_skip_folder(folder_path: str, config: Dict[str, Any]) -> bool:
    """
    Check if a folder should be skipped based on configuration.
    
    Args:
        folder_path: Path to the folder
        config: Configuration dictionary
        
    Returns:
        True if the folder should be skipped, False otherwise
    """
    # Extract folder name from path
    folder_name = os.path.basename(folder_path.rstrip('/'))
    
    # Check exclude folders list
    if 'excludeFolders' in config and config['excludeFolders']:
        exclude_folders = config['excludeFolders']
        # Handle both string and list formats
        if isinstance(exclude_folders, str):
            exclude_folders = [f.strip() for f in exclude_folders.split(',')]
        elif isinstance(exclude_folders, list):
            exclude_folders = [str(f).strip() for f in exclude_folders]
        
        if folder_name in exclude_folders:
            logger.info(f"SKIP FOLDER: {folder_path} (matches excluded folder name: {folder_name})")
            return True
    
    return False

def _list_directory_recursive(fs: fsspec.AbstractFileSystem, path: str, config: Dict[str, Any], 
                         file_list: List[Dict[str, Any]], skipped_folders: List[str], depth: int = 0) -> None:
    """
    Recursively list files in a directory and its subdirectories.
    
    Args:
        fs: fsspec filesystem object
        path: Path to list
        config: Configuration dictionary
        file_list: List to append file information to
        skipped_folders: List to append skipped folder paths to
        depth: Current recursion depth
    """
    indent = "  " * depth
    try:
        logger.info(f"{indent}Scanning directory: {path}")
        
        # List files in the directory with retry for S3
        max_retries = config.get('max_reconnect_attempts', 3)
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                dir_contents = fs.ls(path, detail=True)
                logger.info(f"{indent}Found {len(dir_contents)} items in {path}")
                break  # Success, exit retry loop
            except Exception as e:
                # Handle connection errors inline
                error_msg = f"Failed to list directory {path}: {str(e)}"
                
                logger.error(f"{indent}{error_msg}")
                
                retry_count += 1
                if retry_count <= max_retries:
                    sleep_time = (2 ** (retry_count - 1)) * 0.5  # 0.5, 1, 2 seconds
                    logger.info(f"{indent}Retrying listing in {sleep_time:.1f} seconds... (Attempt {retry_count}/{max_retries})")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"{indent}Maximum retry attempts reached. Listing failed for {path}.")
                    raise
        
        for file_info in dir_contents:
            # Handle directories
            if file_info.get('type') == 'directory':
                dir_path = file_info.get('name', '')
                dir_name = os.path.basename(dir_path.rstrip('/'))
                
                # Check if this directory should be skipped
                if _should_skip_folder(dir_path, config):
                    skipped_folders.append(dir_path)
                    continue
                
                # Skip subfolders if configured, otherwise recurse
                skip_subfolders = config.get('skipSubFolders', False)
                if skip_subfolders:
                    logger.info(f"{indent}SKIP SUBFOLDER: {dir_path} (skipSubFolders=true)")
                else:
                    logger.info(f"{indent}ENTER SUBFOLDER: {dir_path}")
                    _list_directory_recursive(fs, dir_path, config, file_list, skipped_folders, depth + 1)
                continue
                
            # Extract file information
            name = file_info.get('name', '').split('/')[-1]
            size = file_info.get('size', 0)
            
            # Handle different timestamp formats
            mtime = None
            if 'mtime' in file_info:
                # Some fsspec implementations return datetime objects
                if isinstance(file_info['mtime'], datetime.datetime):
                    mtime = file_info['mtime']
                # Others return timestamps
                else:
                    try:
                        mtime = datetime.datetime.fromtimestamp(file_info['mtime'])
                    except (TypeError, ValueError):
                        mtime = datetime.datetime.now()
            else:
                # Default to current time if no timestamp available
                mtime = datetime.datetime.now()
            
            # Create standardized file info
            file_entry = {
                'name': name,
                'path': file_info.get('name', ''),
                'size': size,
                'mtime': mtime,
                'type': 'file'
            }
            
            logger.info(f"{indent}FOUND FILE: {name} - Size: {format_file_size(size)} - Modified: {mtime}")
            file_list.append(file_entry)
            
    except Exception as e:
        error_msg = f"Failed to access directory {path}: {str(e)}"
        logger.error(f"{indent}{error_msg}")

def list_files(fs: fsspec.AbstractFileSystem, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    List files from a remote file system.
    
    Args:
        fs: fsspec filesystem object
        config: Configuration dictionary
        
    Returns:
        List of file information dictionaries
    """
    if not fs:
        logger.error("No filesystem provided")
        return []
    
    try:
        path = config.get('path', '/')
        
        if config.get('type') == 's3' and 'bucket' in config:
            if not path.startswith('/'):
                path = f"{config['bucket']}/{path}"
            else:
                path = f"{config['bucket']}{path}"
        
        logger.info(f"Listing files from: {path}")
        
        # Get file listing
        file_list = []
        skipped_folders = []
        
        # Use recursive function to list files
        _list_directory_recursive(fs, path, config, file_list, skipped_folders)
        
        # Log skipped items
        if skipped_folders:
            logger.info("Folders skipped during listing:")
            for folder in skipped_folders:
                logger.info(f"  - {folder}")
        
        logger.info(f"Found {len(file_list)} files")
        
        # Print all files found for debugging
        print(f"\n=== ALL FILES FOUND IN BUCKET ({len(file_list)} total) ===")
        for i, file in enumerate(file_list, 1):
            print(f"{i:3d}. {file['name']} - Size: {format_file_size(file['size'])} - Modified: {file['mtime']}")
        print("=" * 50)
        
        return file_list
        
    except Exception as e:
        error_msg = f"File listing failed for {path}: {str(e)}"
        logger.error(error_msg)
        return []