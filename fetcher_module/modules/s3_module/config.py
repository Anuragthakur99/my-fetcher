"""S3 Module Configuration"""

from typing import Dict, Any, List


class S3ModuleConfig:
    """Configuration class for S3 Module"""
    
    def __init__(self, job_config):
        self.job_config = job_config
        self.config = {}
    
    def load_config(self) -> Dict[str, Any]:
        """Load S3-specific configuration from job_config"""
        try:
            if not self.job_config:
                raise ValueError("Job configuration is required")
            
            # Check if using new structured format
            if 's3' in self.job_config:
                from common.config_mapper import ConfigMapper
                job_config = ConfigMapper.map_s3_config(self.job_config)
            else:
                job_config = self.job_config
            
            self.config = {
                # Connection settings
                'type': 's3',
                'bucket': job_config.get('bucket'),
                'region': job_config.get('region', 'us-east-1'),
                'aws_access_key_id': job_config.get('aws_access_key_id'),
                'aws_secret_access_key': job_config.get('aws_secret_access_key'),
                'aws_session_token': job_config.get('aws_session_token'),
                'profile': job_config.get('profile'),
            
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
            'connection_timeout': job_config.get('connection_timeout', 60),
            'max_reconnect_attempts': job_config.get('max_reconnect_attempts', 3)
            }
            return self.config
        
        except Exception as e:
            from .exceptions.s3_exceptions import S3ConfigurationError
            raise S3ConfigurationError(f"Failed to load S3 configuration: {str(e)}")
    
    def validate_config(self) -> List[str]:
        """Validate S3 configuration and return list of errors"""
        errors = []
        
        try:
            if not self.config:
                errors.append('Configuration not loaded')
                return errors
            
            if not self.config.get('bucket'):
                errors.append('S3 bucket is required')
                
            # Check credentials
            has_keys = self.config.get('aws_access_key_id') and self.config.get('aws_secret_access_key')
            has_profile = self.config.get('profile')
            has_session_token = self.config.get('aws_session_token')
            
            if not has_keys and not has_profile and not has_session_token:
                errors.append('AWS credentials (keys, profile, or session token) are required')
                
        except Exception as e:
            errors.append(f'Configuration validation error: {str(e)}')
            
        return errors
