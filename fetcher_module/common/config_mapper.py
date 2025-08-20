"""Config Mapper - Maps new structured config to legacy flat config"""

from typing import Dict, Any

class ConfigMapper:
    """Maps structured config formats to legacy flat config"""
    
    @staticmethod
    def map_ftp_config(structured_config: Dict[str, Any]) -> Dict[str, Any]:
        """Map structured FTP config to flat config format"""
        ftp_config = structured_config.get('ftp', {})
        
        # Extract nested values
        connection = ftp_config.get('connection', {})
        auth = connection.get('auth', {})
        scope = ftp_config.get('scope', {})
        file_select = ftp_config.get('file_select', {})
        include = file_select.get('include', {})
        exclude = file_select.get('exclude', {})
        sorting = ftp_config.get('sorting', {})
        date_window = ftp_config.get('date_window', {})
        post_fetch = ftp_config.get('post_fetch', {})
        
        # Map to flat structure
        flat_config = {
            # Connection
            'source_type': connection.get('protocol', 'ftp'),
            'host': connection.get('host'),
            'port': connection.get('port'),
            'user': auth.get('username'),
            'pass': auth.get('password'),
            
            # Scope
            'path': scope.get('path', '/'),
            
            # File selection
            'pattern': include.get('patterns', [None])[0] if include.get('patterns') else None,
            'extensions': include.get('extensions', []),
            'caseSensitive': include.get('case_sensitive', False),
            'exclude_pattern': exclude.get('patterns', [None])[0] if exclude.get('patterns') else None,
            'excludeFolders': exclude.get('folders', []),
            'skipSubFolders': exclude.get('skip_subfolders', False),
            
            # Sorting
            'sortFilesByModifiedTime': sorting.get('by') == 'modified_time',
            'sortByDateInFilename': sorting.get('by') == 'date_in_filename',
            'sortByDateInPath': sorting.get('by') == 'date_in_path',
            'sortOnFileName': sorting.get('by') == 'filename',
            'sortDescending': sorting.get('descending', False),
            'dateFormatInFilename': sorting.get('date_format', '%Y-%m-%d'),
            'dateFormatInPath': sorting.get('date_format', '%Y/%m/%d'),
            
            # Date window - parse T+14 format
            'extractedDateNextDays': ConfigMapper._parse_date_range(date_window.get('range')),
            
            # File examples
            'sampleFiles': ftp_config.get('file_examples', []),
            
            # Post fetch
            'renameAfterFetching': post_fetch.get('rename_after_fetch', False),
            'fileParsedString': post_fetch.get('rename_template', 'Processed'),
        }
        
        # Copy other fields from original config
        for key, value in structured_config.items():
            if key not in ['ftp'] and key not in flat_config:
                flat_config[key] = value
        
        return flat_config
    
    @staticmethod
    def map_s3_config(structured_config: Dict[str, Any]) -> Dict[str, Any]:
        """Map structured S3 config to flat config format"""
        s3_config = structured_config.get('s3', {})
        
        # Extract nested values
        connection = s3_config.get('connection', {})
        credentials = connection.get('credentials', {})
        scope = s3_config.get('scope', {})
        file_select = s3_config.get('file_select', {})
        include = file_select.get('include', {})
        exclude = file_select.get('exclude', {})
        sorting = s3_config.get('sorting', {})
        date_window = s3_config.get('date_window', {})
        post_fetch = s3_config.get('post_fetch', {})
        
        # Map to flat structure
        flat_config = {
            # Connection
            'bucket': connection.get('bucket'),
            'region': connection.get('region', 'us-east-1'),
            'aws_access_key_id': credentials.get('access_key_id'),
            'aws_secret_access_key': credentials.get('secret_access_key'),
            
            # Scope
            'path': scope.get('path', '/'),
            
            # File selection
            'pattern': include.get('patterns', [None])[0] if include.get('patterns') else None,
            'extensions': include.get('extensions', []),
            'caseSensitive': include.get('case_sensitive', False),
            'exclude_pattern': exclude.get('patterns', [None])[0] if exclude.get('patterns') else None,
            
            # Sorting
            'sortFilesByModifiedTime': sorting.get('by') == 'modified_time',
            'sortByDateInFilename': sorting.get('by') == 'date_in_filename',
            'sortByDateInPath': sorting.get('by') == 'date_in_path',
            'sortOnFileName': sorting.get('by') == 'filename',
            'sortDescending': sorting.get('descending', False),
            'dateFormatInFilename': sorting.get('date_format', '%Y-%m-%d'),
            'dateFormatInPath': sorting.get('date_format', '%Y/%m/%d'),
            
            # Date window
            'extractedDateNextDays': ConfigMapper._parse_date_range(date_window.get('range')),
            
            # File examples
            'sampleFiles': s3_config.get('file_examples', []),
            
            # Post fetch
            'renameAfterFetching': post_fetch.get('rename_after_fetch', False),
            'fileParsedString': post_fetch.get('rename_template', 'Processed'),
        }
        
        # Copy other fields from original config
        for key, value in structured_config.items():
            if key not in ['s3'] and key not in flat_config:
                flat_config[key] = value
        
        return flat_config
    
    @staticmethod
    def _parse_date_range(range_str: str) -> int:
        """Parse date range like T+14 to extractedDateNextDays"""
        if not range_str:
            return None
        
        if range_str.startswith('T+'):
            try:
                return int(range_str[2:])
            except ValueError:
                return None
        
        return None