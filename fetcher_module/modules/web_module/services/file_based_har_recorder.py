"""File-Based HAR Recording Service - Framework integrated"""

import json
import base64
import time
import uuid
import os
import re
import chardet
import hashlib
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from playwright.async_api import Page, Request, Response


class FileBasedHARRecorder:
    """
    File-based HAR recorder that saves network traffic in separate files
    following the structure from collect_network_api.py inspiration code.
    
    Supports both global (session-wide) and task-specific recording.
    """
    
    def __init__(self, session_id: str, output_dir: str, logger):
        self.session_id = session_id
        self.output_dir = Path(output_dir)
        self.logger = logger
        
        # Import web_config directly - always gets updated data
        from ..config.web_config import web_config
        self.web_config = web_config
        
        # Global recording state
        self.global_request_counter = 0
        self.global_pending_requests = {}
        self.global_completed_pairs = []
        self.is_global_recording = False
        
        # Task-specific recording state
        self.current_task_id = None
        self.task_request_counter = 0
        self.task_pending_requests = {}
        self.task_completed_pairs = []
        self.is_task_recording = False
        
        # Create global directory structure
        self._create_global_directories()
        
        # Original HAR file tracking for compatibility
        self.original_har_entries = []  # Store all entries for traditional HAR format
        
    def _create_global_directories(self):
        """Create the global directory structure for file-based HAR storage"""
        try:
            global_dir = self.output_dir
            os.makedirs(f"{global_dir}/response_bodies", exist_ok=True)
            os.makedirs(f"{global_dir}/request_headers", exist_ok=True)
            os.makedirs(f"{global_dir}/response_headers", exist_ok=True)
            
            self.global_response_bodies_dir = f"{global_dir}/response_bodies"
            self.global_request_headers_dir = f"{global_dir}/request_headers"
            self.global_response_headers_dir = f"{global_dir}/response_headers"
            
            self.logger.info(f"📁 Global HAR directories created in: {global_dir}")
        except Exception as e:
            self.logger.error(f"Failed to create global directories: {e}")
            
    def _create_task_directories(self, task_dir: Path):
        """Create task-specific directory structure for file-based HAR storage"""
        try:
            os.makedirs(f"{task_dir}/response_bodies", exist_ok=True)
            os.makedirs(f"{task_dir}/request_headers", exist_ok=True)
            os.makedirs(f"{task_dir}/response_headers", exist_ok=True)
            
            self.task_response_bodies_dir = f"{task_dir}/response_bodies"
            self.task_request_headers_dir = f"{task_dir}/request_headers"
            self.task_response_headers_dir = f"{task_dir}/response_headers"
            
            self.logger.info(f"📁 Task HAR directories created in: {task_dir}")
        except Exception as e:
            self.logger.error(f"Failed to create task directories: {e}")

    def _create_short_id(self) -> str:
        """Create a short unique identifier (6 characters)"""
        return str(uuid.uuid4()).split('-')[0][:6]
    
    def _create_har_entry(self, completed_pair: Dict[str, Any]) -> Dict[str, Any]:
        """Convert internal request-response pair to standard HAR entry format"""
        try:
            request_data = completed_pair['request']
            response_data = completed_pair['response']
            
            # Calculate timing (simplified)
            start_time = request_data.get('timestamp', time.time())
            end_time = response_data.get('timestamp', time.time())
            total_time = max(0, (end_time - start_time) * 1000)  # Convert to milliseconds
            
            # Safely get headers - handle both dict and string formats
            request_headers = self._safe_get_headers(request_data.get('headers', {}))
            response_headers = self._safe_get_headers(response_data.get('headers', {}))
            
            # Create HAR entry
            har_entry = {
                "startedDateTime": datetime.fromtimestamp(start_time).isoformat() + "Z",
                "time": total_time,
                "request": {
                    "method": request_data.get('method', 'GET'),
                    "url": request_data.get('url', ''),
                    "httpVersion": "HTTP/1.1",
                    "headers": self._convert_headers_to_har_format(request_headers),
                    "queryString": self._parse_query_string(request_data.get('url', '')),
                    "cookies": [],  # Simplified for now
                    "headersSize": -1,
                    "bodySize": len(request_data.get('post_data', '') or '') if request_data.get('post_data') else 0,
                    "postData": {
                        "mimeType": request_headers.get('content-type', 'text/plain'),
                        "text": request_data.get('post_data', '') or ''
                    } if request_data.get('post_data') else None
                },
                "response": {
                    "status": response_data.get('status', 200),
                    "statusText": response_data.get('status_text', 'OK'),
                    "httpVersion": "HTTP/1.1",
                    "headers": self._convert_headers_to_har_format(response_headers),
                    "cookies": [],  # Simplified for now
                    "content": {
                        "size": response_data.get('body_size', 0),
                        "mimeType": response_data.get('content_type', 'text/html'),
                        "text": response_data.get('body', '') or '',
                        "encoding": "base64" if response_data.get('body_base64') else None
                    },
                    "redirectURL": "",
                    "headersSize": -1,
                    "bodySize": response_data.get('body_size', 0)
                },
                "cache": {},
                "timings": {
                    "blocked": -1,
                    "dns": -1,
                    "connect": -1,
                    "send": 0,
                    "wait": total_time,
                    "receive": 0,
                    "ssl": -1
                },
                "serverIPAddress": "",
                "connection": ""
            }
            
            # Remove postData if None
            if har_entry["request"]["postData"] is None:
                del har_entry["request"]["postData"]
                
            return har_entry
            
        except Exception as e:
            self.logger.error(f"Error creating HAR entry: {e}")
            self.logger.debug(f"Request data: {request_data}")
            self.logger.debug(f"Response data: {response_data}")
            return {}
    
    def _safe_get_headers(self, headers) -> Dict[str, str]:
        """Safely extract headers, handling both dict and string formats"""
        if isinstance(headers, dict):
            return headers
        elif isinstance(headers, str):
            # Try to parse string headers (might be JSON or other format)
            try:
                import json
                parsed = json.loads(headers)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            # If string parsing fails, return empty dict
            self.logger.debug(f"Could not parse headers string: {headers}")
            return {}
        else:
            # Handle other types (list, None, etc.)
            return {}
    
    def _convert_headers_to_har_format(self, headers: Dict[str, str]) -> List[Dict[str, str]]:
        """Convert headers dict to HAR format list"""
        if not isinstance(headers, dict):
            return []
        return [{"name": name, "value": str(value)} for name, value in headers.items()]
    
    def _parse_query_string(self, url: str) -> List[Dict[str, str]]:
        """Parse query string from URL to HAR format"""
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            return [
                {"name": name, "value": values[0] if values else ""}
                for name, values in query_params.items()
            ]
        except Exception:
            return []
    
    def _save_original_har_file(self) -> Optional[str]:
        """Save original HAR file in standard format for compatibility"""
        try:
            # Use session timestamp if available, otherwise current timestamp
            if hasattr(self, 'session_id') and '_' in self.session_id:
                # Extract timestamp from session_id format: YYYYMMDD_HHMMSS_randomid
                session_parts = self.session_id.split('_')
                if len(session_parts) >= 2:
                    timestamp = f"{session_parts[0]}_{session_parts[1]}"
                else:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
            har_filename = f"network_traffic_{timestamp}.har"
            har_path = self.output_dir / har_filename
            
            # Create standard HAR structure
            har_data = {
                "log": {
                    "version": "1.2",
                    "creator": {
                        "name": "TV Schedule Analyzer",
                        "version": "1.0"
                    },
                    "browser": {
                        "name": "Chromium",
                        "version": "unknown"
                    },
                    "pages": [],
                    "entries": self.original_har_entries
                }
            }
            
            # Save HAR file
            with open(har_path, 'w', encoding='utf-8') as f:
                json.dump(har_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📄 Original HAR file created with {len(self.original_har_entries)} entries")
            return str(har_path)
            
        except Exception as e:
            self.logger.error(f"Error saving original HAR file: {e}")
            return None

    def _determine_file_extension(self, content_type: str, data: Any) -> str:
        """
        Determine the appropriate file extension based on content type and data analysis.
        Follows the exact logic from the inspiration code.
        """
        if content_type:
            if 'json' in content_type: return 'json'
            elif 'javascript' in content_type: return 'js'
            elif 'html' in content_type: return 'html'
            elif 'xml' in content_type: return 'xml'
            elif 'css' in content_type: return 'css'
            elif 'text/plain' in content_type: return 'txt'
        
        if isinstance(data, (dict, list)):
            return 'json'
        
        if isinstance(data, str):
            if (data.strip().startswith('{') and data.strip().endswith('}')) or \
               (data.strip().startswith('[') and data.strip().endswith(']')):
                try:
                    json.loads(data)
                    return 'json'
                except:
                    pass
            
            if data.strip().startswith('<!DOCTYPE') or \
               data.strip().startswith('<html') or \
               ('<html' in data.lower() and '</html>' in data.lower()):
                return 'html'
            
            if 'function ' in data or 'var ' in data or 'const ' in data or 'let ' in data:
                return 'js'
            
            if data.strip().startswith('<?xml') or \
               (data.strip().startswith('<') and '></' in data):
                return 'xml'
        
        return 'txt'

    async def start_global_recording(self, page: Page):
        """Start global file-based HAR recording"""
        try:
            self.is_global_recording = True
            self.global_request_counter = 0
            self.global_pending_requests = {}
            self.global_completed_pairs = []
            
            # Set up request handler
            async def handle_global_request(request: Request):
                if not self.is_global_recording:
                    return
                    
                # Filter out common resource types that aren't relevant for API analysis
                if request.resource_type not in ["image", "media", "font"] and ".css" not in request.url:
                    await self._process_global_request(request)
            
            # Set up response handler
            async def handle_global_response(response: Response):
                if not self.is_global_recording:
                    return
                    
                request = response.request
                request_url = request.url
                
                # Only process responses for tracked requests
                if request_url in self.global_pending_requests:
                    await self._process_global_response(response)
            
            # Register event listeners
            page.on("request", handle_global_request)
            page.on("response", handle_global_response)
            
            self.logger.info("🌐 Global file-based HAR recording started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start global HAR recording: {e}")
            return False

    async def _process_global_request(self, request: Request):
        """Process a global request following inspiration code logic"""
        try:
            self.global_request_counter += 1
            short_id = self._create_short_id()
            counter_id = f"{self.global_request_counter:04d}"
            
            # Save request headers to file
            headers_filename = f"{self.global_request_headers_dir}/req_{counter_id}_{short_id}.json"
            try:
                with open(headers_filename, 'w', encoding='utf-8') as file:
                    json.dump(dict(request.headers), file, indent=2, ensure_ascii=False)
            except Exception as e:
                self.logger.debug(f"Error saving request headers to file: {str(e)}")
                headers_filename = None
            
            # Handle post_data
            post_data = None
            try:
                if request.method in ['POST', 'PUT', 'PATCH']:
                    post_data = request.post_data
            except Exception as e:
                self.logger.debug(f"Error accessing post_data for {request.url}: {str(e)}")
                post_data = None

            # Get cookies for this request (following inspiration code)
            request_cookies = []
            try:
                # In browser-use, we need to get cookies from the page context
                # This is different from the inspiration code's direct context access
                if hasattr(request, '_page') and request._page:
                    # Try to get cookies from the page context
                    page_cookies = await request._page.context.cookies(request.url)
                    request_cookies = [
                        {
                            'name': cookie.get('name', ''),
                            'value': cookie.get('value', ''),
                            'domain': cookie.get('domain', ''),
                            'path': cookie.get('path', ''),
                            'secure': cookie.get('secure', False),
                            'httpOnly': cookie.get('httpOnly', False)
                        }
                        for cookie in page_cookies
                    ]
                else:
                    # Fallback: try to extract cookies from request headers
                    cookie_header = request.headers.get('cookie', '')
                    if cookie_header:
                        # Parse cookie header into individual cookies
                        cookie_pairs = [c.strip() for c in cookie_header.split(';') if c.strip()]
                        request_cookies = [
                            {
                                'name': pair.split('=')[0].strip(),
                                'value': pair.split('=', 1)[1].strip() if '=' in pair else ''
                            }
                            for pair in cookie_pairs if '=' in pair
                        ]
            except Exception as e:
                self.logger.debug(f"Error getting cookies for {request.url}: {str(e)}")
                request_cookies = []

            # Build request data object (following inspiration code structure)
            request_data = {
                'id': f"{counter_id}_{short_id}",
                'url': request.url,
                'method': request.method,
                'headers': headers_filename,
                'post_data': post_data,
                'resource_type': request.resource_type,
                'timestamp': time.time(),
                'cookies': request_cookies  # Added missing cookie support
            }
            
            # Store request in pending dictionary
            self.global_pending_requests[request.url] = {
                'request': request_data,
                'response': None
            }
            
            self.logger.debug(f"Global Request: {counter_id} {request.method} {request.url} (cookies: {len(request_cookies)})")
            
        except Exception as e:
            self.logger.error(f"Error processing global request: {e}")

    async def _process_global_response(self, response: Response):
        """Process a global response following inspiration code logic"""
        try:
            request = response.request
            request_url = request.url
            
            if request_url not in self.global_pending_requests:
                return
                
            # Get response body
            raw_body = None
            try:
                raw_body = await response.body()
            except Exception as e:
                self.logger.debug(f"Error retrieving response body for {request_url}: {str(e)}")
            
            req_id = self.global_pending_requests[request_url]['request']['id']
            
            # Save response headers
            headers_filename = f"{self.global_response_headers_dir}/res_{req_id}.json"
            try:
                with open(headers_filename, 'w', encoding='utf-8') as file:
                    json.dump(dict(response.headers), file, indent=2, ensure_ascii=False)
            except Exception as e:
                self.logger.debug(f"Error saving response headers to file: {str(e)}")
                headers_filename = None
            
            content_type = response.headers.get('content-type', '')
            body_content = None
            body_size = None
            file_ext = "txt"
            body_filename = None
            
            if raw_body is not None:
                body_size = len(raw_body)
                
                # Determine if content is likely binary
                is_likely_binary = False
                if 'image/' in content_type or 'audio/' in content_type or 'video/' in content_type:
                    is_likely_binary = True
                elif 'octet-stream' in content_type or 'application/pdf' in content_type:
                    is_likely_binary = True
                else:
                    # Check for null bytes in first 1000 bytes
                    null_count = len([b for b in raw_body[:min(1000, len(raw_body))] if b == 0])
                    is_likely_binary = null_count > 0
                
                # Handle binary content
                if is_likely_binary:
                    # Determine file extension for binary content
                    if 'pdf' in content_type:
                        file_ext = "pdf"
                    elif 'image/' in content_type:
                        file_ext = content_type.split('/')[1].split(';')[0]
                    else:
                        file_ext = "bin"
                        
                    # Save binary content
                    body_filename = f"{self.global_response_bodies_dir}/body_{req_id}.{file_ext}"
                    with open(body_filename, 'wb') as file:
                        file.write(raw_body)
                else:
                    # Handle text content
                    content_encoding = None
                    charset_match = re.search(r'charset=([^\s;]+)', content_type)
                    if charset_match:
                        content_encoding = charset_match.group(1)
                    
                    if not content_encoding:
                        detected = chardet.detect(raw_body)
                        content_encoding = detected['encoding'] or 'utf-8'
                    
                    # Try to decode the content
                    try:
                        text_content = raw_body.decode(content_encoding)
                    except (UnicodeDecodeError, LookupError):
                        text_content = raw_body.decode('utf-8', errors='replace')
                    
                    body_content = text_content
                    
                    # Try to parse JSON if content appears to be JSON
                    if ('json' in content_type or 
                        (body_content and body_content.strip().startswith('{') and body_content.strip().endswith('}')) or \
                        (body_content and body_content.strip().startswith('[') and body_content.strip().endswith(']'))):
                        try:
                            body_content = json.loads(body_content)
                        except json.JSONDecodeError:
                            pass
                    
                    # Determine appropriate file extension
                    file_ext = self._determine_file_extension(content_type, body_content)
                    
                    # Save text content
                    body_filename = f"{self.global_response_bodies_dir}/body_{req_id}.{file_ext}"
                    with open(body_filename, 'w', encoding='utf-8') as file:
                        if isinstance(body_content, (dict, list)):
                            json.dump(body_content, file, indent=2, ensure_ascii=False)
                        else:
                            file.write(body_content or "")

            # Extract Set-Cookie headers (following inspiration code)
            set_cookie_headers = []
            try:
                set_cookie = response.headers.get('set-cookie')
                if set_cookie:
                    # Handle multiple set-cookie headers
                    if isinstance(set_cookie, list):
                        # Multiple set-cookie headers as list
                        set_cookie_headers = [cookie.strip() for cookie in set_cookie if cookie.strip()]
                    else:
                        # Single set-cookie header, split by newlines
                        set_cookie_headers = [cookie.strip() for cookie in set_cookie.split('\n') if cookie.strip()]
            except Exception as e:
                self.logger.debug(f"Error reading set-cookie headers for {request_url}: {e}")
                set_cookie_headers = []

            # Build response data object (following inspiration code structure)
            response_data = {
                'url': response.url,
                'status': response.status,
                'status_text': response.status_text,
                'headers': headers_filename,
                'body': body_filename,
                'body_size': body_size,
                'content_type': content_type,
                'file_extension': file_ext,
                'timestamp': time.time(),
                'set_cookies': set_cookie_headers  # Added missing set-cookie support
            }
            
            # Complete the request-response pair
            self.global_pending_requests[request_url]['response'] = response_data
            completed_pair = self.global_pending_requests[request_url]
            self.global_completed_pairs.append(completed_pair)
            
            # Add to original HAR entries for compatibility
            har_entry = self._create_har_entry(completed_pair)
            self.original_har_entries.append(har_entry)
            
            del self.global_pending_requests[request_url]
            
            self.logger.debug(f"Global Response: {req_id} {response.status} {response.url}")
            
        except Exception as e:
            self.logger.error(f"Error processing global response: {e}")

    async def start_task_recording(self, task_id: str, task_dir: Path, page: Page):
        """Start task-specific file-based HAR recording"""
        try:
            self.current_task_id = task_id
            self.is_task_recording = True
            self.task_request_counter = 0
            self.task_pending_requests = {}
            self.task_completed_pairs = []
            
            # Create task directories
            self._create_task_directories(task_dir)
            
            # Set up task-specific request handler
            async def handle_task_request(request: Request):
                if not self.is_task_recording or self.current_task_id != task_id:
                    return
                    
                # Filter out common resource types that aren't relevant for API analysis
                if request.resource_type not in ["image", "media", "font"] and ".css" not in request.url:
                    await self._process_task_request(request, task_id)
            
            # Set up task-specific response handler
            async def handle_task_response(response: Response):
                if not self.is_task_recording or self.current_task_id != task_id:
                    return
                    
                request = response.request
                request_url = request.url
                
                # Only process responses for tracked requests
                if request_url in self.task_pending_requests:
                    await self._process_task_response(response, task_id)
            
            # Register event listeners (these will be in addition to global listeners)
            page.on("request", handle_task_request)
            page.on("response", handle_task_response)
            
            self.logger.info(f"📋 Task-specific file-based HAR recording started for: {task_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start task HAR recording for {task_id}: {e}")
            return False

    async def _process_task_request(self, request: Request, task_id: str):
        """Process a task-specific request following inspiration code logic"""
        try:
            self.task_request_counter += 1
            short_id = self._create_short_id()
            counter_id = f"{self.task_request_counter:04d}"
            
            # Save request headers to file
            headers_filename = f"{self.task_request_headers_dir}/req_{counter_id}_{short_id}.json"
            try:
                with open(headers_filename, 'w', encoding='utf-8') as file:
                    json.dump(dict(request.headers), file, indent=2, ensure_ascii=False)
            except Exception as e:
                self.logger.debug(f"Error saving task request headers to file: {str(e)}")
                headers_filename = None
            
            # Handle post_data
            post_data = None
            try:
                if request.method in ['POST', 'PUT', 'PATCH']:
                    post_data = request.post_data
            except Exception as e:
                self.logger.debug(f"Error accessing post_data for {request.url}: {str(e)}")
                post_data = None

            # Get cookies for this request (same logic as global)
            request_cookies = []
            try:
                # In browser-use, we need to get cookies from the page context
                if hasattr(request, '_page') and request._page:
                    # Try to get cookies from the page context
                    page_cookies = await request._page.context.cookies(request.url)
                    request_cookies = [
                        {
                            'name': cookie.get('name', ''),
                            'value': cookie.get('value', ''),
                            'domain': cookie.get('domain', ''),
                            'path': cookie.get('path', ''),
                            'secure': cookie.get('secure', False),
                            'httpOnly': cookie.get('httpOnly', False)
                        }
                        for cookie in page_cookies
                    ]
                else:
                    # Fallback: try to extract cookies from request headers
                    cookie_header = request.headers.get('cookie', '')
                    if cookie_header:
                        # Parse cookie header into individual cookies
                        cookie_pairs = [c.strip() for c in cookie_header.split(';') if c.strip()]
                        request_cookies = [
                            {
                                'name': pair.split('=')[0].strip(),
                                'value': pair.split('=', 1)[1].strip() if '=' in pair else ''
                            }
                            for pair in cookie_pairs if '=' in pair
                        ]
            except Exception as e:
                self.logger.debug(f"Error getting cookies for {request.url}: {str(e)}")
                request_cookies = []

            # Build request data object (following inspiration code structure)
            request_data = {
                'id': f"{counter_id}_{short_id}",
                'url': request.url,
                'method': request.method,
                'headers': headers_filename,
                'post_data': post_data,
                'resource_type': request.resource_type,
                'timestamp': time.time(),
                'task_id': task_id,
                'cookies': request_cookies  # Added missing cookie support
            }
            
            # Store request in pending dictionary
            self.task_pending_requests[request.url] = {
                'request': request_data,
                'response': None
            }
            
            self.logger.debug(f"Task Request ({task_id}): {counter_id} {request.method} {request.url} (cookies: {len(request_cookies)})")
            
        except Exception as e:
            self.logger.error(f"Error processing task request: {e}")

    async def _process_task_response(self, response: Response, task_id: str):
        """Process a task-specific response following inspiration code logic"""
        try:
            request = response.request
            request_url = request.url
            
            if request_url not in self.task_pending_requests:
                return
                
            # Get response body
            raw_body = None
            try:
                raw_body = await response.body()
            except Exception as e:
                self.logger.debug(f"Error retrieving response body for {request_url}: {str(e)}")
            
            req_id = self.task_pending_requests[request_url]['request']['id']
            
            # Save response headers
            headers_filename = f"{self.task_response_headers_dir}/res_{req_id}.json"
            try:
                with open(headers_filename, 'w', encoding='utf-8') as file:
                    json.dump(dict(response.headers), file, indent=2, ensure_ascii=False)
            except Exception as e:
                self.logger.debug(f"Error saving task response headers to file: {str(e)}")
                headers_filename = None
            
            content_type = response.headers.get('content-type', '')
            body_content = None
            body_size = None
            file_ext = "txt"
            body_filename = None
            
            if raw_body is not None:
                body_size = len(raw_body)
                
                # Determine if content is likely binary (same logic as global)
                is_likely_binary = False
                if 'image/' in content_type or 'audio/' in content_type or 'video/' in content_type:
                    is_likely_binary = True
                elif 'octet-stream' in content_type or 'application/pdf' in content_type:
                    is_likely_binary = True
                else:
                    # Check for null bytes in first 1000 bytes
                    null_count = len([b for b in raw_body[:min(1000, len(raw_body))] if b == 0])
                    is_likely_binary = null_count > 0
                
                # Handle binary content
                if is_likely_binary:
                    # Determine file extension for binary content
                    if 'pdf' in content_type:
                        file_ext = "pdf"
                    elif 'image/' in content_type:
                        file_ext = content_type.split('/')[1].split(';')[0]
                    else:
                        file_ext = "bin"
                        
                    # Save binary content
                    body_filename = f"{self.task_response_bodies_dir}/body_{req_id}.{file_ext}"
                    with open(body_filename, 'wb') as file:
                        file.write(raw_body)
                else:
                    # Handle text content (same logic as global)
                    content_encoding = None
                    charset_match = re.search(r'charset=([^\s;]+)', content_type)
                    if charset_match:
                        content_encoding = charset_match.group(1)
                    
                    if not content_encoding:
                        detected = chardet.detect(raw_body)
                        content_encoding = detected['encoding'] or 'utf-8'
                    
                    # Try to decode the content
                    try:
                        text_content = raw_body.decode(content_encoding)
                    except (UnicodeDecodeError, LookupError):
                        text_content = raw_body.decode('utf-8', errors='replace')
                    
                    body_content = text_content
                    
                    # Try to parse JSON if content appears to be JSON
                    if ('json' in content_type or 
                        (body_content and body_content.strip().startswith('{') and body_content.strip().endswith('}')) or \
                        (body_content and body_content.strip().startswith('[') and body_content.strip().endswith(']'))):
                        try:
                            body_content = json.loads(body_content)
                        except json.JSONDecodeError:
                            pass
                    
                    # Determine appropriate file extension
                    file_ext = self._determine_file_extension(content_type, body_content)
                    
                    # Save text content
                    body_filename = f"{self.task_response_bodies_dir}/body_{req_id}.{file_ext}"
                    with open(body_filename, 'w', encoding='utf-8') as file:
                        if isinstance(body_content, (dict, list)):
                            json.dump(body_content, file, indent=2, ensure_ascii=False)
                        else:
                            file.write(body_content or "")

            # Extract Set-Cookie headers (following inspiration code)
            set_cookie_headers = []
            try:
                set_cookie = response.headers.get('set-cookie')
                if set_cookie:
                    # Handle multiple set-cookie headers
                    if isinstance(set_cookie, list):
                        # Multiple set-cookie headers as list
                        set_cookie_headers = [cookie.strip() for cookie in set_cookie if cookie.strip()]
                    else:
                        # Single set-cookie header, split by newlines
                        set_cookie_headers = [cookie.strip() for cookie in set_cookie.split('\n') if cookie.strip()]
            except Exception as e:
                self.logger.debug(f"Error reading set-cookie headers for {request_url}: {e}")
                set_cookie_headers = []

            # Build response data object (following inspiration code structure)
            response_data = {
                'url': response.url,
                'status': response.status,
                'status_text': response.status_text,
                'headers': headers_filename,
                'body': body_filename,
                'body_size': body_size,
                'content_type': content_type,
                'file_extension': file_ext,
                'timestamp': time.time(),
                'task_id': task_id,
                'set_cookies': set_cookie_headers  # Added missing set-cookie support
            }
            
            # Complete the request-response pair
            self.task_pending_requests[request_url]['response'] = response_data
            self.task_completed_pairs.append(self.task_pending_requests[request_url])
            del self.task_pending_requests[request_url]
            
            self.logger.debug(f"Task Response ({task_id}): {req_id} {response.status} {response.url}")
            
        except Exception as e:
            self.logger.error(f"Error processing task response: {e}")

    async def stop_task_recording(self, task_id: str, task_dir: Path) -> Optional[Path]:
        """Stop task-specific recording and save network_traffic.json"""
        try:
            if not self.is_task_recording or self.current_task_id != task_id:
                self.logger.warning(f"No active task recording found for {task_id}")
                return None
            
            self.is_task_recording = False
            self.current_task_id = None
            
            # Save the captured network data to network_traffic.json (following inspiration code)
            network_traffic_path = task_dir / 'network_traffic.json'
            with open(network_traffic_path, 'w', encoding='utf-8') as f:
                json.dump(self.task_completed_pairs, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"💾 Task network traffic saved: {network_traffic_path}")
            self.logger.info(f"📊 Captured {len(self.task_completed_pairs)} complete request-response pairs for {task_id}")
            self.logger.info(f"⏳ {len(self.task_pending_requests)} requests still pending with no response")
            
            if self.task_pending_requests:
                self.logger.debug("Pending request URLs:", list(self.task_pending_requests.keys()))
            
            return network_traffic_path
            
        except Exception as e:
            self.logger.error(f"Failed to stop task recording for {task_id}: {e}")
            return None

    async def save_global_network_traffic(self) -> Optional[Path]:
        """Save global network_traffic.json following inspiration code structure"""
        try:
            # Wait for any pending global requests to complete
            if self.global_pending_requests:
                self.logger.info("Waiting for pending global requests to complete...")
                await asyncio.sleep(2)  # Give some time for pending requests
            
            # Save the captured network data to network_traffic.json
            network_traffic_path = self.output_dir / 'network_traffic.json'
            with open(network_traffic_path, 'w', encoding='utf-8') as f:
                json.dump(self.global_completed_pairs, f, indent=2, ensure_ascii=False)
            
            # Save original HAR file for compatibility
            original_har_path = self._save_original_har_file()
            
            self.logger.info(f"💾 Global network traffic saved: {network_traffic_path}")
            if original_har_path:
                self.logger.info(f"📄 Original HAR file saved: {original_har_path}")
            self.logger.info(f"📊 Captured {len(self.global_completed_pairs)} complete request-response pairs globally")
            self.logger.info(f"⏳ {len(self.global_pending_requests)} requests still pending with no response")
            
            if self.global_pending_requests:
                self.logger.debug("Pending global request URLs:", list(self.global_pending_requests.keys()))
            
            return network_traffic_path
            
        except Exception as e:
            self.logger.error(f"Failed to save global network traffic: {e}")
            return None

    async def stop_global_recording(self):
        """Stop global HAR recording"""
        if self.is_global_recording:
            self.is_global_recording = False
            self.logger.info(f"🛑 Global file-based HAR recording stopped")
            
            # Save global network traffic
            await self.save_global_network_traffic()
        else:
            self.logger.info("🛑 Global file-based HAR recording was already stopped")

    def get_recording_stats(self) -> Dict[str, Any]:
        """Get current recording statistics"""
        return {
            'global_recording': {
                'is_recording': self.is_global_recording,
                'total_requests': len(self.global_completed_pairs),
                'pending_requests': len(self.global_pending_requests)
            },
            'task_recording': {
                'is_recording': self.is_task_recording,
                'current_task': self.current_task_id,
                'total_requests': len(self.task_completed_pairs),
                'pending_requests': len(self.task_pending_requests)
            }
        }
