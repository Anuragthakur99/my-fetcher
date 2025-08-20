"""Protocol-specific exception handling utility"""

def get_protocol_from_config(config):
    """Detect protocol from configuration"""
    protocol_type = config.get('type', '').lower()
    if 's3' in protocol_type:
        return 's3'
    elif 'sftp' in protocol_type:
        return 'sftp'
    elif 'ftp' in protocol_type:
        return 'ftp'
    return None

def get_protocol_from_fs(fs):
    """Detect protocol from filesystem object"""
    if hasattr(fs, 'protocol'):
        protocol = str(fs.protocol).lower()
        if 's3' in protocol:
            return 's3'
        elif 'sftp' in protocol:
            return 'sftp'
        elif 'ftp' in protocol:
            return 'ftp'
    return None

def raise_protocol_exception(e, operation, config=None, fs=None, **kwargs):
    """Raise appropriate protocol-specific exception"""
    protocol = get_protocol_from_config(config) if config else get_protocol_from_fs(fs)
    
    if protocol == 's3':
        from modules.s3_module.exceptions.s3_exceptions import handle_s3_exception
        raise handle_s3_exception(e, operation, **kwargs)
    elif protocol in ['ftp', 'sftp']:
        from modules.ftp_module.exceptions.ftp_exceptions import handle_ftp_exception
        raise handle_ftp_exception(e, operation, protocol=protocol, **kwargs)
    else:
        # Generic exception for unknown protocols
        raise Exception(f"{operation} failed: {str(e)}")