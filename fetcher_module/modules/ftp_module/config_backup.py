"""FTP Module Configuration - Clean Version"""

from typing import Dict, Any, List


class FTPModuleConfig:
    """Configuration class for FTP Module"""
    
    def __init__(self, job_config):
        self.job_config = job_config
        self.config = {}
    
    def load_config(self) -> Dict[str, Any]:
        """Load FTP/SFTP-specific configuration from job_config"""
        # Check if using new structured format
        if 'ftp' in self.job_config:
            from common.config_mapper import ConfigMapper
            job_config = ConfigMapper.map_ftp_config(self.job_config)
        else:
            job_config = self.job_config
        
        # Determine connection type (ftp or sftp)
        source_type = job_config.get('source_type', 'ftp').lower()
        conn_type = 'sftp' if source_type in ['sftp', 'ssh'] else 'ftp'
        
        self.config = {
            # Connection settings
            'type': conn_type,
            'host': job_config.get('host'),
            'port': job_config.get('port', 22 if conn_type == 'sftp' else 21),
            'user': job_config.get('user'),
            'pass': job_config.get('pass'),
            'use_passive_mode': job_config.get('use_passive_mode', True),
            
            # File settings
            'path': job_config.get('path', '/'),
            'local_download_path': job_config.get('local_download_path', './downloads/'),
            
            # Filtering
            'pattern': job_config.get('pattern'),
            'sampleFiles': job_config.get('sampleFiles'),
            'generateRegex': job_config.get('generateRegex', False),
            'exclude_pattern': job_config.get('exclude_pattern'),
            'skipPatterns': job_config.get('skipPatterns'),
            'excludeFolders': job_config.get('excludeFolders'),
            'extensions': job_config.get('extensions'),
            'min_size': job_config.get('min_size'),
            'max_size': job_config.get('max_size'),
            'last_days': job_config.get('last_days'),
            'start_date': job_config.get('start_date'),
            'end_date': job_config.get('end_date'),
            
            # Sorting
            'sortByDate': job_config.get('sortByDate', False),
            'sortByDateInFilename': job_config.get('sortByDateInFilename', False),
            'dateFormatInFilename': job_config.get('dateFormatInFilename', '%Y-%m-%d'),
            'sortByDateInPath': job_config.get('sortByDateInPath', False),
            'dateFormatInPath': job_config.get('dateFormatInPath', '%Y/%m/%d'),
            'getLatestFileOnly': job_config.get('getLatestFileOnly', False),
            'sortFilesByModifiedTime': job_config.get('sortFilesByModifiedTime', False),
            'sortDescending': job_config.get('sortDescending', False),
            'sortOnFileName': job_config.get('sortOnFileName', False),
            'caseSensitive': job_config.get('caseSensitive', False),
            'num_files': job_config.get('num_files'),
            
            # Extracted date filtering
            'extractedDateStart': job_config.get('extractedDateStart'),
            'extractedDateEnd': job_config.get('extractedDateEnd'),
            'extractedDateLastDays': job_config.get('extractedDateLastDays'),
            'extractedDateNextDays': job_config.get('extractedDateNextDays'),
            'includeFilesWithoutDates': job_config.get('includeFilesWithoutDates', False),
            
            # Download settings
            'overwrite_existing': job_config.get('overwrite_existing', False),
            'appendFullPath': job_config.get('appendFullPath', False),
            'resume_transfer': job_config.get('resume_transfer', True),
            'connection_timeout': job_config.get('connection_timeout', 30),
            'max_reconnect_attempts': job_config.get('max_reconnect_attempts', 3)
        }
        return self.config
    
    def validate_config(self) -> List[str]:
        """Validate FTP/SFTP configuration and return list of errors"""
        errors = []
        
        if not self.config.get('host'):
            errors.append('FTP/SFTP host is required')
            
        if not self.config.get('user'):
            errors.append('FTP/SFTP username is required')
            
        if not self.config.get('pass'):
            errors.append('FTP/SFTP password is required')
            
        return errors