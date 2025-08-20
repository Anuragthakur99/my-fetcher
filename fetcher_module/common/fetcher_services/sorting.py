#!/usr/bin/env python3
"""
File sorting service.
"""
import logging
import re
import os
import datetime
from typing import Dict, List, Any, Callable, Optional

def to_naive_datetime(dt):
    """Convert datetime to naive (no timezone) for comparison."""
    if dt and hasattr(dt, 'tzinfo') and dt.tzinfo:
        return dt.replace(tzinfo=None)
    return dt



logger = logging.getLogger(__name__)

def detect_date_location(files: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Auto-detect whether dates are in filenames or paths when user requests sorting by date
    without specifying the location.
    
    Args:
        files: List of file information dictionaries
        config: Configuration dictionary
        
    Returns:
        Updated config with appropriate date location flags set
    """
    # If user already specified a location, respect that choice
    if config.get('sortByDateInPath') or config.get('sortByDateInFilename'):
        return config
    
    # Check if user explicitly wants to sort by date using the new parameter
    if config.get('sortByDate'):
        logger.info("User requested sortByDate - auto-detecting date location (filename vs path)")
        
        # Sample a subset of files for efficiency
        sample_size = min(len(files), 10)
        sample_files = files[:sample_size]
        
        # Use user-provided format if available, otherwise use common formats
        user_format = config.get('dateFormat')
        filename_formats = [user_format] if user_format else ['%Y-%m-%d', '%Y%m%d', '%d-%m-%Y', '%Y_%m_%d']
        path_formats = [user_format] if user_format else ['%Y/%m/%d', '%Y/%b/%d', '%Y-%m-%d']
        
        # Count successful date extractions from filenames
        filename_matches = 0
        best_filename_format = None
        for file in sample_files:
            for fmt in filename_formats:
                try:
                    # Convert format to regex pattern
                    regex_pattern = fmt
                    regex_pattern = regex_pattern.replace('%Y', r'(\d{4})')
                    regex_pattern = regex_pattern.replace('%y', r'(\d{2})')
                    regex_pattern = regex_pattern.replace('%m', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%d', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%H', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%M', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%S', r'(\d{1,2})')
                    
                    # Find date pattern in filename (just the basename, not the full path)
                    if re.search(regex_pattern, file['name']):
                        filename_matches += 1
                        best_filename_format = fmt
                        break
                except Exception:
                    continue
        
        # Count successful date extractions from paths
        path_matches = 0
        best_path_format = None
        for file in sample_files:
            # Get the directory part of the path, excluding the filename
            file_path = file.get('path', '')
            if not file_path or file_path == file['name']:
                # If there's no separate path or path is same as filename, skip
                continue
                
            # Remove the filename from the path to ensure we're only checking the directory part
            dir_path = os.path.dirname(file_path)
            
            for fmt in path_formats:
                try:
                    # Convert format to regex pattern
                    regex_pattern = fmt
                    regex_pattern = regex_pattern.replace('%Y', r'(\d{4})')
                    regex_pattern = regex_pattern.replace('%y', r'(\d{2})')
                    regex_pattern = regex_pattern.replace('%m', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%d', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%b', r'([A-Z]{3})')
                    regex_pattern = regex_pattern.replace('%B', r'([A-Za-z]+)')
                    regex_pattern = regex_pattern.replace('%H', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%M', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%S', r'(\d{1,2})')
                    
                    # Find date pattern in directory path only
                    if re.search(regex_pattern, dir_path):
                        path_matches += 1
                        best_path_format = fmt
                        break
                except Exception:
                    continue
        
        # Determine best location based on match counts
        if filename_matches > path_matches:
            logger.info(f"Auto-detected dates in filenames ({filename_matches}/{sample_size} matches)")
            config['sortByDateInFilename'] = True
            config['dateFormatInFilename'] = best_filename_format or '%Y-%m-%d'  # Use detected format or default
        elif path_matches > 0:
            logger.info(f"Auto-detected dates in directory paths ({path_matches}/{sample_size} matches)")
            config['sortByDateInPath'] = True
            config['dateFormatInPath'] = best_path_format or '%Y/%m/%d'  # Use detected format or default
        else:
            logger.info("Could not auto-detect dates in filenames or directory paths, defaulting to filename sorting")
            config['sortOnFileName'] = True
    
    return config

def sort_files(files: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Sort files based on configuration options.
    
    Args:
        files: List of file information dictionaries
        config: Configuration with sorting criteria
                - getLatestFileOnly: Get only the file(s) with the latest modification time
                - sortByDateInPath: Sort by date extracted from file path
                - dateFormatInPath: Date format in path (e.g., '%Y/%m/%d', '%Y/%b/%d')
                - sortByDateInFilename: Sort by date extracted from filename
                - dateFormatInFilename: Date format in filename (e.g., '%Y-%m-%d', '%Y%m%d')
                - sortFilesByModifiedTime: Sort by modification time
                - sortOnFileName: Sort by filename
                - sortDescending: Sort in descending order
                - caseSensitive: Case-sensitive filename sorting
                - num_files: Limit number of files (ignored if getLatestFileOnly is True)
        
    Returns:
        Sorted list of files
    """
    if not files:
        logger.info("No files to sort")
        return []
    
    sorted_files = files.copy()
    
    # Check for the new sortByDate parameter
    if config.get('sortByDate'):
        # Auto-detect date location if user wants to sort by date
        config = detect_date_location(files, config)
    else:
        # For backward compatibility, try to auto-detect if no specific sorting method is specified
        if not any([config.get('sortByDateInPath'), config.get('sortByDateInFilename'), 
                   config.get('sortFilesByModifiedTime'), config.get('sortOnFileName'), 
                   config.get('getLatestFileOnly')]):
            config = detect_date_location(files, config)
    
    logger.info(f"Sorting {len(files)} files")
    
    print(f"🔍 CHECKING SORTING CONDITIONS:")
    print(f"   sortFilesByModifiedTime: {config.get('sortFilesByModifiedTime')}")
    print(f"   sortByDateInPath: {config.get('sortByDateInPath')}")
    print(f"   sortByDateInFilename: {config.get('sortByDateInFilename')}")
    print(f"   getLatestFileOnly: {config.get('getLatestFileOnly')}")
    print(f"   sortOnFileName: {config.get('sortOnFileName')}")
    print(f"   sortDescending: {config.get('sortDescending')}")
    
    # Sort by modification time
    if config.get('sortFilesByModifiedTime'):
        print(f"✅ APPLYING MODIFICATION TIME SORTING")
        reverse = config.get('sortDescending', False)
        logger.info(f"Sorting files by modification time ({'descending' if reverse else 'ascending'})")
        logger.info(f"Sort reverse parameter: {reverse}")
        
        try:
            # Debug: log before sorting
            logger.debug("Files before sorting:")
            for file in sorted_files[:5]:
                logger.debug(f"  {file['name']} - {file['mtime']} ({file['mtime'].timestamp()})")
            
            sorted_files.sort(key=lambda x: x['mtime'], reverse=reverse)
            
            # Debug: log after sorting
            logger.debug("Files after sorting:")
            for file in sorted_files[:5]:
                logger.debug(f"  {file['name']} - {file['mtime']} ({file['mtime'].timestamp()})")
            logger.info(f"Files sorted by modification time (reverse={reverse})")
            
            # Log the sorted order with detailed timestamps
            for i, file in enumerate(sorted_files[:10], 1):  # Log first 10 files
                logger.info(f"  {i}. {file['name']} - Modified: {file['mtime']} ({file['mtime'].timestamp()})")
            
            if len(sorted_files) > 10:
                logger.info(f"  ... and {len(sorted_files) - 10} more files")
                
        except Exception as e:
            logger.error(f"Error sorting by modification time: {e}")
            logger.warning("Falling back to unsorted file list")
            sorted_files = files.copy()
    
    # Sort by date in path
    elif config.get('sortByDateInPath'):
        print(f"✅ APPLYING DATE IN PATH SORTING")
        date_format = config.get('dateFormatInPath', '%Y/%m/%d')
        reverse = config.get('sortDescending', False)
        logger.info(f"Sorting files by date in path using format: {date_format} ({'descending' if reverse else 'ascending'})")
        
        try:
            def extract_date_from_path(file_path):
                """Extract date from file path using the specified format."""
                try:
                    # Get the directory part of the path, excluding the filename
                    dir_path = os.path.dirname(file_path)
                    
                    # Convert strptime format to regex pattern
                    regex_pattern = date_format
                    regex_pattern = regex_pattern.replace('%Y', r'(\d{4})')
                    regex_pattern = regex_pattern.replace('%y', r'(\d{2})')
                    regex_pattern = regex_pattern.replace('%m', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%d', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%b', r'([A-Z]{3})')
                    regex_pattern = regex_pattern.replace('%B', r'([A-Za-z]+)')
                    regex_pattern = regex_pattern.replace('%H', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%M', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%S', r'(\d{1,2})')
                    
                    # Find date pattern in directory path only
                    match = re.search(regex_pattern, dir_path)
                    if match:
                        # Extract the matched date string
                        date_str = match.group(0)
                        # Parse using the original format
                        return datetime.datetime.strptime(date_str, date_format)
                    return None
                except Exception as e:
                    logger.debug(f"Could not extract date from path {file_path}: {e}")
                    return None
            
            # Extract dates and sort
            files_with_dates = []
            files_without_dates = []
            
            for file in sorted_files:
                file_path = file.get('path', file['name'])  # Use full path if available
                extracted_date = extract_date_from_path(file_path)
                if extracted_date:
                    file['extracted_path_date'] = extracted_date
                    files_with_dates.append(file)
                else:
                    files_without_dates.append(file)
            
            logger.info(f"Found dates in paths of {len(files_with_dates)} files, {len(files_without_dates)} files without recognizable date patterns")
            
            # Sort files with dates
            if files_with_dates:
                files_with_dates.sort(key=lambda x: x['extracted_path_date'], reverse=reverse)
                
                # Log sorted order
                logger.info("Files sorted by date in path:")
                for i, file in enumerate(files_with_dates[:10], 1):
                    logger.info(f"  {i}. {file['name']} - Path Date: {file['extracted_path_date'].strftime('%Y-%m-%d')}")
                
                if len(files_with_dates) > 10:
                    logger.info(f"  ... and {len(files_with_dates) - 10} more files")
            
            # Combine: files with dates first, then files without dates
            sorted_files = files_with_dates + files_without_dates
            
            if files_without_dates:
                logger.warning(f"{len(files_without_dates)} files could not be sorted by path date (no matching date pattern)")
                
        except Exception as e:
            logger.error(f"Error sorting by date in path: {e}")
            logger.warning("Falling back to unsorted file list")
            sorted_files = files.copy()
    
    # Sort by date in filename
    elif config.get('sortByDateInFilename'):
        print(f"✅ APPLYING DATE IN FILENAME SORTING")
        date_format = config.get('dateFormatInFilename', '%Y-%m-%d')
        reverse = config.get('sortDescending', False)
        logger.info(f"Sorting files by date in filename using format: {date_format} ({'descending' if reverse else 'ascending'})")
        
        try:
            def extract_date_from_filename(filename):
                """Extract date from filename using the specified format."""
                try:
                    # Convert strptime format to regex pattern
                    regex_pattern = date_format
                    regex_pattern = regex_pattern.replace('%Y', r'(\d{4})')
                    regex_pattern = regex_pattern.replace('%y', r'(\d{2})')
                    regex_pattern = regex_pattern.replace('%m', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%d', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%H', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%M', r'(\d{1,2})')
                    regex_pattern = regex_pattern.replace('%S', r'(\d{1,2})')
                    
                    # Find date pattern in filename
                    match = re.search(regex_pattern, filename)
                    if match:
                        # Extract the matched date string
                        date_str = match.group(0)
                        # Parse using the original format
                        return datetime.datetime.strptime(date_str, date_format)
                    return None
                except Exception as e:
                    logger.debug(f"Could not extract date from {filename}: {e}")
                    return None
            
            # Extract dates and sort
            files_with_dates = []
            files_without_dates = []
            
            for file in sorted_files:
                extracted_date = extract_date_from_filename(file['name'])
                if extracted_date:
                    file['extracted_date'] = extracted_date
                    files_with_dates.append(file)
                else:
                    files_without_dates.append(file)
            
            logger.info(f"Found dates in {len(files_with_dates)} files, {len(files_without_dates)} files without recognizable dates")
            
            # Sort files with dates
            if files_with_dates:
                files_with_dates.sort(key=lambda x: x['extracted_date'], reverse=reverse)
                
                # Log sorted order
                logger.info("Files sorted by date in filename:")
                for i, file in enumerate(files_with_dates[:10], 1):
                    logger.info(f"  {i}. {file['name']} - Date: {file['extracted_date'].strftime('%Y-%m-%d')}")
                
                if len(files_with_dates) > 10:
                    logger.info(f"  ... and {len(files_with_dates) - 10} more files")
            
            # Combine: files with dates first, then files without dates
            sorted_files = files_with_dates + files_without_dates
            
            if files_without_dates:
                logger.warning(f"{len(files_without_dates)} files could not be sorted by date (no matching date pattern)")
                
        except Exception as e:
            logger.error(f"Error sorting by date in filename: {e}")
            logger.warning("Falling back to unsorted file list")
            sorted_files = files.copy()
    
    # Get latest file only (automatically sorts by modification time descending)
    elif config.get('getLatestFileOnly'):
        logger.info("Getting latest file only - sorting by modification time (descending)")
        
        try:
            # Sort by modification time in descending order to get latest first
            sorted_files.sort(key=lambda x: x['mtime'], reverse=True)
            
            # Get only the latest file(s)
            if sorted_files:
                latest_mtime = sorted_files[0]['mtime']
                # Get all files with the same latest modification time
                latest_files = [f for f in sorted_files if f['mtime'] == latest_mtime]
                sorted_files = latest_files
                
                logger.info(f"Found {len(latest_files)} file(s) with latest modification time: {latest_mtime}")
                for i, file in enumerate(latest_files, 1):
                    logger.info(f"  {i}. {file['name']} - Modified: {file['mtime']}")
            else:
                logger.warning("No files available for latest file selection")
                
        except Exception as e:
            logger.error(f"Error getting latest file: {e}")
            logger.warning("Falling back to unsorted file list")
            sorted_files = files.copy()
    
    # Sort by filename
    elif config.get('sortOnFileName'):
        case_sensitive = config.get('caseSensitive', False)
        logger.info(f"Sorting files by filename (case {'sensitive' if case_sensitive else 'insensitive'})")
        
        try:
            reverse = config.get('sortDescending', False)
            logger.info(f"Sort direction: {'descending' if reverse else 'ascending'}")
            
            if case_sensitive:
                sorted_files.sort(key=lambda x: x['name'], reverse=reverse)
            else:
                sorted_files.sort(key=lambda x: x['name'].lower(), reverse=reverse)
                
            logger.info(f"Files sorted by filename")
            
            # Log the sorted order
            for i, file in enumerate(sorted_files[:10], 1):  # Log first 10 files
                logger.info(f"  {i}. {file['name']}")
                
            if len(sorted_files) > 10:
                logger.info(f"  ... and {len(sorted_files) - 10} more files")
                
        except Exception as e:
            logger.error(f"Error sorting by filename: {e}")
            logger.warning("Falling back to unsorted file list")
            sorted_files = files.copy()
    

    
    

    
    # Limit number of files if specified (skip if getLatestFileOnly is enabled)
    # This is done AFTER all filtering to ensure we get the right files
    num_files = config.get('num_files')
    if not config.get('getLatestFileOnly') and num_files and num_files > 0 and len(sorted_files) > num_files:
        logger.info(f"Limiting to {num_files} files (from {len(sorted_files)} total)")
        sorted_files = sorted_files[:num_files]
        
        # Log which files are selected with timestamps
        logger.info("Selected files:")
        for i, file in enumerate(sorted_files, 1):
            logger.info(f"  {i}. {file['name']} - Modified: {file['mtime']} ({file['mtime'].timestamp()})")
    elif config.get('getLatestFileOnly'):
        logger.info("Skipping num_files limit - getLatestFileOnly is enabled")
    
    logger.info(f"Sorted to {len(sorted_files)} files")
    
    # Print sorted files for debugging
    print(f"\n=== SORTED FILES ({len(sorted_files)} total) ===")
    for i, file in enumerate(sorted_files, 1):
        print(f"{i:3d}. {file['name']} - Size: {file['size']} bytes - Modified: {file['mtime']}")
    print("=" * 50)
    
    return sorted_files