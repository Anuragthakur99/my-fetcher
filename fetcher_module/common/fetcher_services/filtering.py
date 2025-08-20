#!/usr/bin/env python3
"""
File filtering service.
"""
import re
import logging
import datetime
import os
from typing import Dict, List, Any, Optional

from .utils import parse_size, format_date_placeholders, prepare_regex_pattern

logger = logging.getLogger(__name__)

# Helper function to safely convert datetime to naive datetime
def to_naive_datetime(dt):
    if dt is None:
        return None
    try:
        return dt.replace(tzinfo=None)
    except:
        return dt  # Return as is if conversion fails

def filter_files(files: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Filter files based on pattern, size, and date.
    
    Args:
        files: List of file information diactionaries
        config: Configuration with filter criteria
        
    Returns:
        Filtered list of files
    """
    filtered_files = files
    skipped_files = []
    
    print(f"🔍 CHECKING FILTERING CONDITIONS:")
    print(f"   sampleFiles: {config.get('sampleFiles')}")
    print(f"   pattern: {config.get('pattern')}")
    print(f"   extractedDateNextDays: {config.get('extractedDateNextDays')}")
    print(f"   sortByDateInFilename: {config.get('sortByDateInFilename')}")
    
    # Handle sample files with regex generation or exact matching
    if 'sampleFiles' in config and config['sampleFiles']:
        print(f"✅ APPLYING SAMPLE FILES FILTERING")
        if config.get('generateRegex', False):
            # TODO: Call regex generation service
            # generated_pattern, date_format = generate_regex_from_samples(config['sampleFiles'])
            # For now, use exact matching as fallback
            logger.info("Regex generation requested but not implemented yet. Using exact matching.")
            sample_files = config['sampleFiles']
            before_count = len(filtered_files)
            filtered_files = [f for f in filtered_files if f['name'] in sample_files]
            skipped = before_count - len(filtered_files)
            logger.info(f"Filtered by sample files {sample_files}: {len(filtered_files)} files match, {skipped} files skipped")
        else:
            # Exact file matching
            sample_files = config['sampleFiles']
            before_count = len(filtered_files)
            filtered_files = [f for f in filtered_files if f['name'] in sample_files]
            skipped = before_count - len(filtered_files)
            logger.info(f"Filtered by exact sample files {sample_files}: {len(filtered_files)} files match, {skipped} files skipped")
    
    # Filter by pattern if specified (existing logic)
    elif 'pattern' in config and config['pattern']:
        print(f"✅ APPLYING PATTERN FILTERING: {config['pattern']}")
        try:
            # Process pattern with date placeholders and handle bracket escaping
            pattern = prepare_regex_pattern(config['pattern'], config)
            regex = re.compile(pattern)
            before_count = len(filtered_files)
            
            # Check both filename and full path if appendFullPath is enabled
            if config.get('appendFullPath', False):
                filtered_files = [f for f in filtered_files if regex.search(f['name']) or regex.search(f['path'])]
            else:
                filtered_files = [f for f in filtered_files if regex.search(f['name'])]
                
            skipped = before_count - len(filtered_files)
            if skipped > 0:
                skipped_files.extend([f['name'] for f in files if f not in filtered_files])
            logger.info(f"Filtered by pattern '{pattern}': {len(filtered_files)} files match, {skipped} files skipped")
        except re.error as e:
            logger.error(f"Invalid regex pattern: {e}")
            return []
    
    # Filter by exclusion pattern if specified
    if 'exclude_pattern' in config and config['exclude_pattern']:
        try:
            # Process pattern with date placeholders and handle bracket escaping
            exclude_pattern = prepare_regex_pattern(config['exclude_pattern'], config)
            exclude_regex = re.compile(exclude_pattern)
            before_count = len(filtered_files)
            
            # Check both filename and full path if appendFullPath is enabled
            if config.get('appendFullPath', False):
                excluded_files = [f for f in filtered_files if exclude_regex.search(f['name']) or exclude_regex.search(f['path'])]
                filtered_files = [f for f in filtered_files if not (exclude_regex.search(f['name']) or exclude_regex.search(f['path']))]
            else:
                excluded_files = [f for f in filtered_files if exclude_regex.search(f['name'])]
                filtered_files = [f for f in filtered_files if not exclude_regex.search(f['name'])]
                
            skipped = before_count - len(filtered_files)
            if skipped > 0:
                skipped_files.extend([f['name'] for f in excluded_files])
            logger.info(f"Filtered by exclude pattern '{exclude_pattern}': {len(filtered_files)} files remain, {skipped} files skipped")
        except re.error as e:
            logger.error(f"Invalid exclude regex pattern: {e}")
            return []
            
    # Filter by skip patterns if specified
    if 'skipPatterns' in config and config['skipPatterns']:
        try:
            skip_patterns = [p.strip() for p in config['skipPatterns'].split(',')]
            before_count = len(filtered_files)
            
            for pattern in skip_patterns:
                try:
                    # Process pattern with date placeholders and handle bracket escaping
                    processed_pattern = prepare_regex_pattern(pattern, config)
                    logger.info(f"Processing skip pattern: '{pattern}' -> '{processed_pattern}'")
                    
                    skip_regex = re.compile(processed_pattern)
                    
                    # Check both filename and full path if appendFullPath is enabled
                    if config.get('appendFullPath', False):
                        skipped_by_pattern = [f for f in filtered_files if skip_regex.search(f['name']) or skip_regex.search(f['path'])]
                        filtered_files = [f for f in filtered_files if not (skip_regex.search(f['name']) or skip_regex.search(f['path']))]
                    else:
                        skipped_by_pattern = [f for f in filtered_files if skip_regex.search(f['name'])]
                        filtered_files = [f for f in filtered_files if not skip_regex.search(f['name'])]
                    
                    if skipped_by_pattern:
                        skipped_files.extend([f['name'] for f in skipped_by_pattern])
                        logger.info(f"Skipped {len(skipped_by_pattern)} files matching pattern '{processed_pattern}':")
                        for file in skipped_by_pattern[:5]:  # Log first 5 files
                            logger.info(f"  - {file['name']}")
                        if len(skipped_by_pattern) > 5:
                            logger.info(f"  ... and {len(skipped_by_pattern) - 5} more files")
                except re.error as e:
                    logger.warning(f"Invalid skip pattern '{pattern}': {e}")
            
            skipped = before_count - len(filtered_files)
            if skipped > 0:
                logger.info(f"Total files skipped by skip patterns: {skipped}")
        except Exception as e:
            logger.error(f"Error processing skip patterns: {e}")
            
    # Filter by exclude keywords if specified
    if 'excludeKeywords' in config and config['excludeKeywords']:
        try:
            keywords = [k.strip().lower() for k in config['excludeKeywords'].split(',')]
            before_count = len(filtered_files)
            
            # Track files excluded by each keyword
            excluded_by_keyword = {keyword: [] for keyword in keywords}
            
            # Filter out files containing any of the keywords
            remaining_files = []
            for file in filtered_files:
                filename_lower = file['name'].lower()
                excluded = False
                
                for keyword in keywords:
                    if keyword in filename_lower:
                        excluded_by_keyword[keyword].append(file['name'])
                        excluded = True
                        break
                
                if not excluded:
                    remaining_files.append(file)
            
            # Log files excluded by each keyword
            for keyword, excluded_files_list in excluded_by_keyword.items():
                if excluded_files_list:
                    logger.info(f"Excluded {len(excluded_files_list)} files containing keyword '{keyword}':")
                    for filename in excluded_files_list[:5]:  # Log first 5 files
                        logger.info(f"  - {filename}")
                    if len(excluded_files_list) > 5:
                        logger.info(f"  ... and {len(excluded_files_list) - 5} more files")
            
            skipped = before_count - len(remaining_files)
            filtered_files = remaining_files
            
            logger.info(f"Filtered by exclude keywords {keywords}: {len(filtered_files)} files remain, {skipped} files skipped")
        except Exception as e:
            logger.error(f"Error processing exclude keywords: {e}")
    
    # Filter by file extension if specified
    if 'extensions' in config and config['extensions']:
        extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                     for ext in config['extensions']]
        filtered_files = [f for f in filtered_files 
                         if os.path.splitext(f['name'])[1].lower() in extensions]
        logger.info(f"Filtered by extensions {extensions}: {len(filtered_files)} files match")
    
    # Filter by minimum size if specified
    if 'min_size' in config and config['min_size']:
        min_size = parse_size(config['min_size'])
        if min_size is not None:
            filtered_files = [f for f in filtered_files if f['size'] >= min_size]
            logger.info(f"Filtered by min size {min_size} bytes: {len(filtered_files)} files match")
    
    # Filter by maximum size if specified
    if 'max_size' in config and config['max_size']:
        max_size = parse_size(config['max_size'])
        if max_size is not None:
            filtered_files = [f for f in filtered_files if f['size'] <= max_size]
            logger.info(f"Filtered by max size {max_size} bytes: {len(filtered_files)} files match")
    
    # Filter by last modified date if specified
    if 'last_days' in config and config['last_days']:
        try:
            days = int(config['last_days'])
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
            # Handle timezone-aware datetimes by removing timezone info for comparison
            filtered_files = [f for f in filtered_files if to_naive_datetime(f['mtime']) >= cutoff_date]
            logger.info(f"Filtered by last {days} days: {len(filtered_files)} files match")
        except (ValueError, TypeError):
            logger.error(f"Invalid 'last_days' value: {config['last_days']}")
    

    
    # Filter by date range if specified
    if 'start_date' in config and config['start_date']:
        try:
            start_date = datetime.datetime.strptime(config['start_date'], '%Y-%m-%d')
            # Handle timezone-aware datetimes by removing timezone info for comparison
            filtered_files = [f for f in filtered_files if to_naive_datetime(f['mtime']) >= start_date]
            logger.info(f"Filtered by start date {start_date.date()}: {len(filtered_files)} files match")
        except ValueError:
            logger.error(f"Invalid 'start_date' format: {config['start_date']}. Use YYYY-MM-DD format.")
    
    if 'end_date' in config and config['end_date']:
        try:
            end_date = datetime.datetime.strptime(config['end_date'], '%Y-%m-%d')
            # Set to end of day
            end_date = end_date.replace(hour=23, minute=59, second=59)
            # Handle timezone-aware datetimes by removing timezone info for comparison
            filtered_files = [f for f in filtered_files if to_naive_datetime(f['mtime']) <= end_date]
            logger.info(f"Filtered by end date {end_date.date()}: {len(filtered_files)} files match")
        except ValueError:
            logger.error(f"Invalid 'end_date' format: {config['end_date']}. Use YYYY-MM-DD format.")
    
    # Filter by extracted dates from filename or path if configured
    if (config.get('extractedDateStart') or config.get('extractedDateEnd') or config.get('extractedDateNextDays')) and (config.get('sortByDateInFilename') or config.get('sortByDateInPath')):
        print(f"🔍 APPLYING EXTRACTED DATE FILTERING")
        print(f"   Condition: sortByDateInFilename={config.get('sortByDateInFilename')}, sortByDateInPath={config.get('sortByDateInPath')}")
        try:
            start_date = None
            end_date = None
            
            # Handle next N days first
            if config.get('extractedDateNextDays'):
                next_days = int(config['extractedDateNextDays'])
                today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                start_date = today
                end_date = today + datetime.timedelta(days=next_days)
                end_date = end_date.replace(hour=23, minute=59, second=59)
                print(f"DEBUG: Next {next_days} days range: {start_date.date()} to {end_date.date()}")
            
            # Handle last N days from end date
            if config.get('extractedDateLastDays'):
                last_days = int(config['extractedDateLastDays'])
                if config.get('extractedDateEnd'):
                    # Calculate from end date
                    end_date = datetime.datetime.strptime(config['extractedDateEnd'], '%Y-%m-%d')
                    start_date = end_date - datetime.timedelta(days=last_days - 1)
                    end_date = end_date.replace(hour=23, minute=59, second=59)
                    print(f"DEBUG: Last {last_days} days from end date: {start_date.date()} to {end_date.date()}")
                else:
                    # Calculate from today if no end date specified
                    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    start_date = today - datetime.timedelta(days=last_days - 1)
                    end_date = today.replace(hour=23, minute=59, second=59)
                    print(f"DEBUG: Last {last_days} days from today: {start_date.date()} to {end_date.date()}")
            
            # Override with explicit dates if provided
            if config.get('extractedDateStart'):
                start_date = datetime.datetime.strptime(config['extractedDateStart'], '%Y-%m-%d')
            if config.get('extractedDateEnd'):
                end_date = datetime.datetime.strptime(config['extractedDateEnd'], '%Y-%m-%d')
                end_date = end_date.replace(hour=23, minute=59, second=59)
            
            result_files = []
            skipped_count = 0
            
            for file in filtered_files:
                extracted_date = None
                
                # Try filename first
                if config.get('sortByDateInFilename'):
                    date_format = config.get('dateFormatInFilename', '%Y-%m-%d')
                    regex_pattern = date_format.replace('%Y', r'(\d{4})').replace('%m', r'(\d{1,2})').replace('%d', r'(\d{1,2})')
                    match = re.search(regex_pattern, file['name'])
                    if match:
                        try:
                            date_str = match.group(0)
                            extracted_date = datetime.datetime.strptime(date_str, date_format)
                        except ValueError:
                            pass
                
                # Try path if filename didn't work
                if not extracted_date and config.get('sortByDateInPath'):
                    date_format = config.get('dateFormatInPath', '%Y/%m/%d')
                    regex_pattern = date_format.replace('%Y', r'(\d{4})').replace('%m', r'(\d{1,2})').replace('%d', r'(\d{1,2})')
                    file_path = file.get('path', file['name'])
                    dir_path = os.path.dirname(file_path)
                    match = re.search(regex_pattern, dir_path)
                    if match:
                        try:
                            date_str = match.group(0)
                            extracted_date = datetime.datetime.strptime(date_str, date_format)
                        except ValueError:
                            pass
                
                if extracted_date:
                    if start_date and extracted_date < start_date:
                        print(f"   SKIPPED {file['name']}: date {extracted_date.date()} before start {start_date.date()}")
                        skipped_count += 1
                        continue
                    if end_date and extracted_date > end_date:
                        print(f"   SKIPPED {file['name']}: date {extracted_date.date()} after end {end_date.date()}")
                        skipped_count += 1
                        continue
                    print(f"   INCLUDED {file['name']}: date {extracted_date.date()} within range")
                    result_files.append(file)
                else:
                    print(f"   SKIPPED {file['name']}: no date extracted")
            
            filtered_files = result_files
            logger.info(f"Filtered by extracted dates: {len(filtered_files)} files match, {skipped_count} files skipped")
        except ValueError as e:
            logger.error(f"Invalid date format in extractedDateStart/End: {e}")
    
    # Print filtered files for debugging
    print(f"\n=== FILTERED FILES ({len(filtered_files)} total) ===")
    for i, file in enumerate(filtered_files, 1):
        print(f"{i:3d}. {file['name']} - Size: {file['size']} bytes - Modified: {file['mtime']}")
    print("=" * 50)
    
    return filtered_files