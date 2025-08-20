#!/usr/bin/env python3
"""
Connection service for file transfers using fsspec.
"""
import logging
import fsspec
import s3fs
import time
import os
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

def create_connection(config: Dict[str, Any]) -> Tuple[Optional[fsspec.AbstractFileSystem], Dict[str, Any]]:
    """
    Create a connection to a remote file system using fsspec.
    
    Args:
        config: Configuration dictionary with connection details
        
    Returns:
        Tuple of (filesystem object, connection options)
    """
    import socket
    import errno
    conn_type = config.get('type', '').lower()
    print(config.get('type', ''))
    connection_timeout = config.get('connection_timeout', 30)  # Default 30 seconds
    
    if not conn_type:
        logger.error("Connection type not specified in config")
        return None, {}
    
    try:
        logger.info(f"Creating {conn_type} connection")
        
        # Common connection options
        conn_options = {}
        
        if conn_type == 'ftp':
            conn_options = {
                'host': config.get('host'),
                'username': config.get('user'),
                'password': config.get('pass'),
                'port': config.get('port', 21),
                'use_passive_mode': config.get('use_passive_mode', True),
                'timeout': connection_timeout
            }
            
        elif conn_type == 'sftp':
            conn_options = {
                'host': config.get('host'),
                'username': config.get('user'),
                'password': config.get('pass'),
                'port': config.get('port', 22),
                'timeout': connection_timeout
            }
            
        elif conn_type == 's3':
            # Use s3fs directly for better credential handling
            conn_options = {}
            
            # Create s3fs filesystem directly
            try:
                fs = s3fs.S3FileSystem(
                    key=config['aws_access_key_id'],
                    secret=config['aws_secret_access_key'],
                    client_kwargs={'region_name': config.get('region', 'us-east-1')}
                )
                
                # Test connection by listing bucket contents
                bucket_name = config.get('bucket', '')
                if bucket_name:
                    # List bucket contents, not the bucket itself
                    fs.ls(f"{bucket_name}/")
                    logger.info(f"Successfully connected to S3 bucket: {bucket_name}")
                else:
                    logger.error("No bucket specified in S3 configuration")
                    return None, {}
                
                return fs, {'bucket': bucket_name, 'region': config.get('region', 'us-east-1')}
                
            except Exception as e:
                error_msg = _handle_s3_error(e, config.get('bucket', 'unknown'))
                logger.error(f"S3 connection failed: {error_msg}")
                return None, {}
        
        elif conn_type == 'local':
            # Local filesystem doesn't need any special options
            conn_options = {}
                
        else:
            logger.error(f"Unsupported connection type: {conn_type}")
            return None, {}
            
        # Create the filesystem with timeout handling (skip for s3 as it's handled above)
        if conn_type != 's3':
            try:
                fs = fsspec.filesystem(conn_type, **conn_options)
                # Store connection reference in conn_options for later use
                conn_options['fs_connection'] = fs
            except Exception as e:
                error_msg = _handle_connection_error(e, config.get('host', 'unknown'))
                logger.error(error_msg)
                return None, {}
        
        # Test the connection (skip for s3 as it's handled above)
        if conn_type == 'local':
            # For local filesystem, ensure the path exists
            path = config.get('path', './')
            if not fs.exists(path):
                logger.warning(f"Local path does not exist: {path}")
                # Create the directory if it doesn't exist
                fs.makedirs(path, exist_ok=True)
            fs.ls(path)
        else:
            # For FTP/SFTP, list the root or specified path
            path = config.get('path', '/')
            fs.ls(path)
            
        logger.info(f"Successfully connected to {conn_type}")
        return fs, conn_options
        
    except Exception as e:
        error_msg = _handle_connection_error(e, config.get('host', 'unknown'))
        logger.error(f"Failed to connect to {conn_type}: {error_msg}")
        return None, {}

def _handle_connection_error(error: Exception, host: str) -> str:
    """
    Handle and categorize connection errors with specific messages.
    
    Args:
        error: The exception that occurred
        host: The host being connected to
        
    Returns:
        Specific error message
    """
    import socket
    import errno
    
    error_str = str(error).lower()
    
    # Connection timeout
    if 'timeout' in error_str or 'timed out' in error_str:
        return f"Connection Timeout: Unable to connect to {host} within the specified timeout period"
    
    # Host not found / DNS resolution failure
    if 'name or service not known' in error_str or 'nodename nor servname provided' in error_str or 'getaddrinfo failed' in error_str:
        return f"Host Not Found: Unable to resolve hostname {host}. Please check the hostname and network connectivity"
    
    # Connection refused
    if 'connection refused' in error_str or 'refused' in error_str:
        return f"Connection Refused: The server at {host} refused the connection. Please check if the service is running and the port is correct"
    
    # Network unreachable
    if 'network is unreachable' in error_str or 'unreachable' in error_str:
        return f"Network Unreachable: Cannot reach {host}. Please check your network connectivity"
    
    # Authentication failure
    if 'authentication failed' in error_str or 'login incorrect' in error_str or 'access denied' in error_str or 'login failed' in error_str:
        return f"Authentication Failed: Invalid credentials for {host}. Please check username and password"
    
    # FTP-specific errors
    if 'passive mode' in error_str or 'pasv' in error_str:
        return f"FTP Passive Mode Error: Data connection failed for {host}. Try disabling passive mode"
    
    if 'data connection' in error_str:
        return f"FTP Data Connection Failed: Unable to establish data channel to {host}"
    
    # SFTP/SSH-specific errors
    if 'ssh' in error_str and ('handshake' in error_str or 'protocol' in error_str):
        return f"SSH Protocol Error: SSH handshake failed with {host}. Check SSH version compatibility"
    
    if 'key' in error_str and 'authentication' in error_str:
        return f"SSH Key Authentication Failed: Invalid SSH key for {host}. Falling back to password authentication"
    
    # Permission denied
    if 'permission denied' in error_str:
        return f"Permission Denied: Insufficient permissions to access {host}"
    
    # Socket errors
    if isinstance(error, socket.error):
        if error.errno == errno.ECONNREFUSED:
            return f"Connection Refused: The server at {host} refused the connection"
        elif error.errno == errno.EHOSTUNREACH:
            return f"Host Unreachable: Cannot reach {host}"
        elif error.errno == errno.ENETUNREACH:
            return f"Network Unreachable: Cannot reach network for {host}"
        elif error.errno == errno.ETIMEDOUT:
            return f"Connection Timeout: Connection to {host} timed out"
    
    # Generic error
    return f"Connection Error: {str(error)}"

def _handle_s3_error(error: Exception, bucket: str) -> str:
    """
    Handle S3-specific errors.
    
    Args:
        error: The exception that occurred
        bucket: The S3 bucket being accessed
        
    Returns:
        Specific S3 error message
    """
    error_str = str(error).lower()
    
    # Access denied / Invalid credentials
    if 'access denied' in error_str or 'invalid access key' in error_str or 'signature does not match' in error_str:
        return f"S3 Authentication Failed: Invalid AWS credentials or insufficient permissions for bucket {bucket}"
    
    # Bucket not found
    if 'no such bucket' in error_str or 'bucket does not exist' in error_str:
        return f"S3 Bucket Not Found: Bucket '{bucket}' does not exist or you don't have access to it"
    
    # Region mismatch
    if 'incorrect region' in error_str or 'region' in error_str:
        return f"S3 Region Error: Bucket '{bucket}' is in a different region. Please check the region configuration"
    
    # Network/timeout issues
    if 'timeout' in error_str or 'timed out' in error_str:
        return f"S3 Connection Timeout: Unable to connect to S3 service"
    
    # Generic S3 error
    return f"S3 Error: {str(error)}"