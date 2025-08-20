#!/usr/bin/env python3
"""
File download service.
"""
import os
import logging
import time
import fsspec
from typing import Dict, List, Any, Optional, Union, Tuple

# Import botocore for S3-specific error handling
try:
    import botocore.exceptions
    BOTOCORE_AVAILABLE = True
except ImportError:
    BOTOCORE_AVAILABLE = False

from .utils import format_file_size, save_state, load_state, clear_state
from .connection import create_connection

logger = logging.getLogger(__name__)

def download_file(fs: fsspec.AbstractFileSystem, remote_path: str, local_path: str) -> bool:
    """
    Download a single file from remote to local path.
    
    Args:
        fs: fsspec filesystem object
        remote_path: Path to the file on the remote system
        local_path: Local path where the file should be saved
        
    Returns:
        True if download was successful, False otherwise
    """
    if not fs:
        logger.error("No filesystem provided")
        return False
    
    try:
        # Ensure the local directory exists
        local_dir = os.path.dirname(local_path)
        logger.info(f"Creating local directory: {local_dir}")
        os.makedirs(local_dir, exist_ok=True)
        
        logger.info(f"DOWNLOAD START: {remote_path} -> {local_path}")
        
        # Download the file with S3-specific error handling
        start_time = time.time()
        
        try:
            fs.get(remote_path, local_path)
        except Exception as e:
            # Handle S3-specific errors
            if BOTOCORE_AVAILABLE and isinstance(e, botocore.exceptions.ClientError):
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                
                # Log specific error types with helpful messages
                if error_code == 'AccessDenied':
                    logger.error(f"Access denied to S3 object: {remote_path}. Please check your credentials.")
                elif error_code == 'NoSuchBucket':
                    logger.error(f"The specified bucket does not exist in path: {remote_path}.")
                elif error_code == 'NoSuchKey':
                    logger.error(f"The specified file does not exist: {remote_path}.")
                else:
                    logger.error(f"S3 download failed with code {error_code}: {error_message}")
            raise  # Re-raise the exception for the outer try/except to handle
            
        elapsed = time.time() - start_time
        
        # Verify the download
        if os.path.exists(local_path):
            size = os.path.getsize(local_path)
            transfer_rate = size / elapsed if elapsed > 0 else 0
            logger.info(f"DOWNLOAD SUCCESS: {remote_path} ({format_file_size(size)})")
            logger.info(f"  Time: {elapsed:.2f} seconds")
            logger.info(f"  Rate: {format_file_size(transfer_rate)}/s")
            return True
        else:
            logger.error(f"DOWNLOAD FAILED: {local_path} does not exist after download attempt")
            return False
            
    except Exception as e:
        error_msg = f"Download failed: {str(e)}"
        logger.error(f"DOWNLOAD ERROR: {error_msg}")
        return False


def download_files(fs: fsspec.AbstractFileSystem, files: List[Dict[str, Any]], 
                  config: Dict[str, Any],
                  all_files: List[Dict[str, Any]] = None,
                  filtered_files: List[Dict[str, Any]] = None) -> Tuple[int, int]:
    """
    Download multiple files from remote to local path.
    
    Args:
        fs: fsspec filesystem object
        files: List of file information dictionaries
        config: Configuration dictionary
        
    Returns:
        Tuple of (number of successful downloads, total number of files)
    """
    if not files:
        logger.info("No files to download")
        return 0, 0
    
    local_path = config.get('local_download_path', './downloads')
    overwrite = config.get('overwrite_existing', False)
    append_full_path = config.get('appendFullPath', False)
    skip_front_slash = config.get('skipFrontSlashPath', False)
    add_front_slash = config.get('addFrontSlashPath', False)
    rename_after_fetching = config.get('renameAfterFetching', False)
    file_parsed_string = config.get('fileParsedString', 'Parsed')
    max_retries = config.get('max_reconnect_attempts', 3)
    retry_delay = config.get('reconnect_delay_seconds', 5)
    
    logger.info(f"Starting download: {len(files)} files to {local_path}")
    
    # Check for existing state
    state = None
    processed_files = []
    
    # Load state for resume capability
    state = load_state(config)
    
    if state and state.get('processed_files') and config.get('resume_transfer', True):
        processed_files = state.get('processed_files', [])
        files = [f for f in files if f['path'] not in processed_files]
        logger.info(f"Resuming: {len(processed_files)} done, {len(files)} remaining")
    
    # Ensure local directory exists
    os.makedirs(local_path, exist_ok=True)
    
    # Sort files by name for consistent processing
    files.sort(key=lambda x: x['name'])
    
    success_count = len(processed_files)
    skipped_count = 0
    failed_count = 0
    skipped_files = []
    failed_files = []
    
    # Save initial state
    save_state(config, processed_files, files)
    
    i = 0
    while i < len(files):
        file_info = files[i]
        remote_path = file_info['path']
        file_name = file_info['name']
        
        # Handle path formatting based on configuration
        if append_full_path:
            # Get the relative path from the remote path
            relative_path = remote_path
            
            # Apply path slash handling
            if skip_front_slash and relative_path.startswith('/'):
                relative_path = relative_path[1:]
            elif add_front_slash and not relative_path.startswith('/'):
                relative_path = '/' + relative_path
                
            # Use the full path for the local file, but ensure it's not treated as absolute
            # by removing any leading slash before joining with local_path
            if relative_path.startswith('/'):
                relative_path = relative_path[1:]
                
            local_file_path = os.path.join(local_path, relative_path)
        else:
            # Just use the filename without path
            local_file_path = os.path.join(local_path, file_name)
        
        logger.info(f"[{i+1}/{len(files)}] {file_name} ({format_file_size(file_info['size'])})")
        
        # Check if file already exists locally
        if os.path.exists(local_file_path):
            local_size = os.path.getsize(local_file_path)
            if not overwrite:
                logger.info(f"SKIPPED: {file_name} (exists)")
                skipped_count += 1
                skipped_files.append(file_name)
                i += 1
                continue
        
        # Try to download with reconnection logic
        download_success = False
        retries = 0
        
        while not download_success and retries <= max_retries:
            if retries > 0:
                logger.info(f"Retry {retries}/{max_retries}")
                if not fs or not hasattr(fs, 'ls'):
                    time.sleep(retry_delay)
                    fs, _ = create_connection(config)
                    if not fs:
                        logger.error("Reconnection failed")
                        retries += 1
                        continue
            
            try:
                # Download the file
                if download_file(fs, remote_path, local_file_path):
                    # Check file size after download
                    if os.path.exists(local_file_path):
                        local_size = os.path.getsize(local_file_path)
                        remote_size = file_info['size']
                        
                        if local_size == remote_size:
                            success_count += 1
                            processed_files.append(remote_path)
                            download_success = True
                            logger.info(f"SUCCESS: {file_name}")
                        else:
                            logger.error(f"SIZE MISMATCH: {file_name} - Expected: {format_file_size(remote_size)}, Got: {format_file_size(local_size)}")
                            os.remove(local_file_path)
                            retries += 1
                            if retries > max_retries:
                                failed_count += 1
                                failed_files.append(file_name)
                                logger.error(f"File {i+1}/{len(files)} failed after {max_retries} attempts")
                                i += 1  # Move to next file
                            continue
                    else:
                        logger.error(f"File not found after download: {file_name}")
                        retries += 1
                        if retries > max_retries:
                            failed_count += 1
                            failed_files.append(file_name)
                            logger.error(f"File {i+1}/{len(files)} failed after {max_retries} attempts")
                            i += 1  # Move to next file
                        continue
                    
                    # Rename file on server if configured
                    if rename_after_fetching:
                        try:
                            # Get directory and filename parts
                            remote_dir = os.path.dirname(remote_path)
                            remote_filename = os.path.basename(remote_path)
                            
                            # Create new filename with prefix
                            new_filename = f"{file_parsed_string}_{remote_filename}"
                            new_remote_path = os.path.join(remote_dir, new_filename) if remote_dir else new_filename
                            
                            # Rename the file on the server
                            logger.info(f"Renaming file on server: {remote_path} -> {new_remote_path}")
                            fs.mv(remote_path, new_remote_path)
                            logger.info(f"File renamed successfully on server")
                        except Exception as e:
                            logger.error(f"Failed to rename file on server: {e}")
                    
                    # Log detailed download success
                    print(f"✅ DOWNLOADED: {file_name} ({format_file_size(file_info['size'])}) -> {local_file_path}")
                    
                    # Save state after each successful download
                    save_state(config, processed_files, files[i+1:], all_files, filtered_files)
                    i += 1  # Move to next file
                    break
                else:
                    retries += 1
                    if retries > max_retries:
                        failed_count += 1
                        failed_files.append(file_name)
                        logger.error(f"File {i+1}/{len(files)} download failed after {max_retries} attempts")
                        i += 1  # Move to next file
            except Exception as e:
                logger.error(f"Error during download: {e}")
                retries += 1
                if retries > max_retries:
                    failed_count += 1
                    failed_files.append(file_name)
                    logger.error(f"File {i+1}/{len(files)} download failed after {max_retries} attempts")
                    i += 1  # Move to next file
    
    logger.info(f"Download complete: {success_count} success, {skipped_count} skipped, {failed_count} failed")
    
    if failed_count > 0:
        logger.error(f"Failed files: {', '.join(failed_files)}")
    
    if failed_count == 0 and skipped_count == 0:
        clear_state(config)
        logger.info("State cleared - all files processed")
    else:
        save_state(config, processed_files, [], all_files, filtered_files)
    
    return success_count, len(files) + len(processed_files) - success_count