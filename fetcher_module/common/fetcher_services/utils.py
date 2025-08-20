#!/usr/bin/env python3
"""
Utility functions for formatting and parsing.
"""
import re
import datetime
import os
import logging
from typing import Optional, Union, Any, Dict

logger = logging.getLogger(__name__)

def parse_size(size_str: Optional[Union[str, int, float]]) -> Optional[int]:
    """Convert human-readable size string to bytes."""
    if not size_str:
        return None
        
    size_str = str(size_str).strip().upper()
    units = {"KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    
    for unit, multiplier in units.items():
        if size_str.endswith(unit):
            try:
                return int(float(size_str.replace(unit, '')) * multiplier)
            except (ValueError, TypeError):
                return None
    
    try:
        return int(size_str)
    except (ValueError, TypeError):
        return None


def format_date_placeholders(pattern_str: Optional[str]) -> Optional[str]:
    """Replace date placeholders with actual date values."""
    if not pattern_str:
        return None
    
    today = datetime.datetime.now()
    processed_pattern = pattern_str
    
    protected_parts = {}
    
    for i, match in enumerate(re.finditer(r'\\[dswbDSWB]\{[0-9,]+\}', pattern_str)):
        token = f"__REGEX_TOKEN_{i}__"
        protected_parts[token] = match.group(0)
        processed_pattern = processed_pattern.replace(match.group(0), token)
    
    format_mapping = {
        # Year
        'Y': '%Y',  # 4-digit year (2025)
        'y': '%y',  # 2-digit year (25)
        
        # Month
        'm': '%m',  # 2-digit month with leading zero (06)
        'n': '%-m',  # Month without leading zero (6) - Note: Windows uses %#m
        'M': '%b',  # 3-letter month abbreviation (Jun)
        'F': '%B',  # Full month name (June)
        
        # Day
        'd': '%d',  # 2-digit day with leading zero (02)
        'j': '%-d',  # Day without leading zero (2) - Note: Windows uses %#d
        'D': '%a',  # 3-letter day abbreviation (Thu)
        'l': '%A',  # Full day name (Thursday)
        'S': '',    # Ordinal suffix - handled separately
        
        # Hour
        'H': '%H',  # 24-hour with leading zero (08)
        'G': '%-H',  # 24-hour without leading zero (8) - Note: Windows uses %#H
        'h': '%I',  # 12-hour with leading zero (08)
        'g': '%-I',  # 12-hour without leading zero (8) - Note: Windows uses %#I
        
        # AM/PM
        'a': '%p',  # Lowercase am/pm - handled separately
        'A': '%p',  # Uppercase AM/PM
        
        # Minute and Second
        'i': '%M',  # 2-digit minute with leading zero (05)
        's': '%S',  # 2-digit second with leading zero (09)
        
        # Week
        'W': '%W',  # Week number (01-53)
    }
    
    # Handle platform-specific format differences (Windows vs Unix)
    if os.name == 'nt':  # Windows
        format_mapping['n'] = '%#m'
        format_mapping['j'] = '%#d'
        format_mapping['G'] = '%#H'
        format_mapping['g'] = '%#I'
    
    # Now find and process date placeholders
    placeholders = re.findall(r'\{([^}]+)\}', processed_pattern)
    
    for placeholder in placeholders:
        if placeholder in format_mapping:
            if placeholder == 'S':
                # Handle ordinal suffix
                day = int(today.strftime('%d'))
                if 4 <= day <= 20 or 24 <= day <= 30:
                    suffix = 'th'
                else:
                    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                date_string = suffix
            elif placeholder == 'a':
                # Handle lowercase am/pm
                date_string = today.strftime('%p').lower()
            else:
                # Use the mapping for other placeholders
                try:
                    date_string = today.strftime(format_mapping[placeholder])
                except ValueError:
                    # If format is invalid, skip this placeholder
                    continue
        else:
            # For compound placeholders like 'Y-m-d'
            try:
                # Replace each character with its strftime equivalent
                strftime_format = ''
                for char in placeholder:
                    if char in format_mapping:
                        strftime_format += format_mapping[char]
                    else:
                        strftime_format += char
                
                date_string = today.strftime(strftime_format)
            except ValueError:
                # If format is invalid, skip this placeholder
                continue
                
        processed_pattern = processed_pattern.replace(f'{{{placeholder}}}', date_string)
    
    # Handle special case for week number format (KW{W})
    if 'KW{W}' in processed_pattern:
        week_num = today.strftime('%W')
        processed_pattern = processed_pattern.replace('KW{W}', f'KW{week_num}')
    
    # Restore protected regex quantifiers
    for token, original in protected_parts.items():
        processed_pattern = processed_pattern.replace(token, original)
    
    logger.info(f"Formatted pattern '{pattern_str}' to: '{processed_pattern}'")
    return processed_pattern


def format_file_size(size_in_bytes: int) -> str:
    """Format file size in bytes to human-readable string."""
    if size_in_bytes >= 1024*1024:
        return f"{size_in_bytes / (1024*1024):.2f} MB"
    elif size_in_bytes >= 1024:
        return f"{size_in_bytes / 1024:.2f} KB"
    else:
        return f"{size_in_bytes} Bytes"


def escape_special_characters(text: str, chars_to_escape: str) -> str:
    """
    Escape specified special characters in a string.
    
    Args:
        text: The original string
        chars_to_escape: String containing characters to escape
        
    Returns:
        String with specified characters escaped
    """
    if not text or not chars_to_escape:
        return text
        
    result = ""
    for char in text:
        if char in chars_to_escape:
            result += '\\' + char
        else:
            result += char
    
    return result


def prepare_regex_pattern(pattern: str, config: Dict[str, Any]) -> str:
    """
    Prepare a regex pattern based on configuration options.
    
    Args:
        pattern: The original pattern string
        config: Configuration dictionary with options
        
    Returns:
        Processed pattern string ready for regex compilation
    """
    if not pattern:
        return pattern
        
    # Process date placeholders first
    pattern = format_date_placeholders(pattern) or pattern
    
    # Handle special character escaping
    escape_chars = config.get('escapeSpecialCharacters', '')
    if escape_chars:
        pattern = escape_special_characters(pattern, escape_chars)
        logger.debug(f"After escaping special characters: '{pattern}'")
    
    # Handle bracket escaping based on configuration
    dont_escape_brackets = config.get('dontEscapeBrackets', False)
    
    if not dont_escape_brackets:
        # Escape square brackets to treat them as literal characters
        # But don't escape already escaped brackets
        processed = ""
        i = 0
        while i < len(pattern):
            if pattern[i] == '\\' and i + 1 < len(pattern) and pattern[i+1] in '[]':
                # Already escaped bracket, keep as is
                processed += pattern[i:i+2]
                i += 2
            elif pattern[i] in '[]':
                # Escape unescaped bracket
                processed += '\\' + pattern[i]
                i += 1
            else:
                # Keep other characters as is
                processed += pattern[i]
                i += 1
        pattern = processed
        
    logger.debug(f"Prepared regex pattern: '{pattern}'")
    return pattern


# State management functions
def save_state(config: Dict[str, Any], processed_files: list, remaining_files: list, 
               all_files: list = None, filtered_files: list = None) -> None:
    """Save transfer state for resuming."""
    try:
        import json
        import tempfile
        
        instance_id = config.get('instance_id', 'default')
        channel_id = config.get('channel_id', 'default')
        
        state_file = os.path.join(tempfile.gettempdir(), f"transfer_state_{instance_id}_{channel_id}.json")
        
        state = {
            'processed_files': processed_files,
            'remaining_files': [f['path'] for f in remaining_files] if remaining_files else [],
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
            
        logger.debug(f"State saved to {state_file}")
    except Exception as e:
        logger.error(f"Failed to save state: {e}")


def load_state(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Load transfer state for resuming."""
    try:
        import json
        import tempfile
        
        instance_id = config.get('instance_id', 'default')
        channel_id = config.get('channel_id', 'default')
        
        state_file = os.path.join(tempfile.gettempdir(), f"transfer_state_{instance_id}_{channel_id}.json")
        
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
            logger.debug(f"State loaded from {state_file}")
            return state
        
        return None
    except Exception as e:
        logger.error(f"Failed to load state: {e}")
        return None


def clear_state(config: Dict[str, Any]) -> None:
    """Clear saved transfer state."""
    try:
        import tempfile
        
        instance_id = config.get('instance_id', 'default')
        channel_id = config.get('channel_id', 'default')
        
        state_file = os.path.join(tempfile.gettempdir(), f"transfer_state_{instance_id}_{channel_id}.json")
        
        if os.path.exists(state_file):
            os.remove(state_file)
            logger.debug(f"State cleared: {state_file}")
    except Exception as e:
        logger.error(f"Failed to clear state: {e}")