"""Enhanced HAR Recording Service for Complete Network Capture"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List


class EnhancedHARRecorder:
    """Enhanced HAR recorder that ensures complete network capture across all tasks"""
    
    def __init__(self, session_id: str, logger):
        self.session_id = session_id
        self.logger = logger
        
        # Import web_config directly - always gets updated data
        from ..config.web_config import web_config
        self.web_config = web_config
        
        # Global session tracking
        self.global_requests = []
        self.task_requests = {}
        self.session_start_time = datetime.now()
        
        # Recording state
        self.is_recording = False
        self.browser_context = None
        
    async def start_global_recording(self, browser_context):
        """Start comprehensive global HAR recording"""
        self.browser_context = browser_context
        self.is_recording = True
        self.global_requests = []
        
        try:
            # Get the current page from browser context
            page = await browser_context.get_current_page()
            if page:
                # Set up comprehensive network monitoring
                async def handle_request(request):
                    try:
                        request_data = {
                            'url': request.url,
                            'method': request.method,
                            'headers': dict(request.headers),
                            'timestamp': datetime.now().isoformat(),
                            'type': 'request',
                            'resource_type': request.resource_type,
                            'post_data': None
                        }
                        
                        # Capture POST data if available
                        if request.method in ['POST', 'PUT', 'PATCH']:
                            try:
                                request_data['post_data'] = request.post_data
                            except:
                                pass
                        
                        self.global_requests.append(request_data)
                        
                    except Exception as e:
                        self.logger.debug(f"Error capturing request: {e}")
                
                async def handle_response(response):
                    try:
                        response_data = {
                            'url': response.url,
                            'status': response.status,
                            'status_text': response.status_text,
                            'headers': dict(response.headers),
                            'timestamp': datetime.now().isoformat(),
                            'type': 'response',
                            'size': 0,
                            'body': None
                        }
                        
                        # Try to get response size and body for certain content types
                        try:
                            content_type = response.headers.get('content-type', '').lower()
                            content_length = response.headers.get('content-length')
                            
                            if content_length:
                                response_data['size'] = int(content_length)
                            
                            # Capture response body for JSON/text responses (limited size)
                            if any(ct in content_type for ct in ['json', 'text', 'xml']) and response.status < 400:
                                try:
                                    body = await response.text()
                                    if len(body) < 10000:  # Limit to 10KB
                                        response_data['body'] = body[:5000]  # Truncate to 5KB
                                except:
                                    pass
                        except:
                            pass
                        
                        self.global_requests.append(response_data)
                        
                    except Exception as e:
                        self.logger.debug(f"Error capturing response: {e}")
                
                # Set up event listeners
                page.on("request", handle_request)
                page.on("response", handle_response)
                
                self.logger.info("🌐 Enhanced global HAR recording started")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to start global HAR recording: {e}")
            return False
    
    async def start_task_recording(self, task_id: str):
        """Start task-specific network recording"""
        if not self.is_recording:
            self.logger.warning(f"Global recording not active, cannot start task recording for {task_id}")
            return False
        
        # Initialize task-specific request tracking
        self.task_requests[task_id] = {
            'start_time': datetime.now(),
            'requests': [],
            'start_index': len(self.global_requests)
        }
        
        self.logger.info(f"📋 Task-specific recording started for: {task_id}")
        return True
    
    async def stop_task_recording(self, task_id: str, task_dir: Path) -> Optional[Path]:
        """Stop task-specific recording and save task HAR file"""
        if task_id not in self.task_requests:
            self.logger.warning(f"No task recording found for {task_id}")
            return None
        
        try:
            task_info = self.task_requests[task_id]
            end_index = len(self.global_requests)
            
            # Extract requests that occurred during this task
            task_specific_requests = self.global_requests[task_info['start_index']:end_index]
            
            # Create task-specific HAR data
            task_har_data = {
                'log': {
                    'version': '1.2',
                    'creator': {
                        'name': 'tv-schedule-analyzer-enhanced',
                        'version': '2.0'
                    },
                    'entries': task_specific_requests,
                    'task_info': {
                        'task_id': task_id,
                        'start_time': task_info['start_time'].isoformat(),
                        'end_time': datetime.now().isoformat(),
                        'total_requests': len(task_specific_requests),
                        'request_range': f"{task_info['start_index']}-{end_index}"
                    }
                }
            }
            
            # Save task HAR file
            task_har_path = task_dir / f"{task_id}_network.har"
            with open(task_har_path, 'w') as f:
                json.dump(task_har_data, f, indent=2)
            
            # Update task info
            task_info['end_time'] = datetime.now()
            task_info['requests'] = task_specific_requests
            task_info['har_file'] = task_har_path
            
            self.logger.info(f"💾 Task HAR saved: {task_har_path} ({len(task_specific_requests)} requests)")
            return task_har_path
            
        except Exception as e:
            self.logger.error(f"Failed to save task HAR for {task_id}: {e}")
            return None
    
    async def save_comprehensive_session_har(self, session_dir: Path) -> Dict[str, Any]:
        """Save comprehensive session HAR with all requests and task breakdowns"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create comprehensive HAR data
            comprehensive_har = {
                'log': {
                    'version': '1.2',
                    'creator': {
                        'name': 'tv-schedule-analyzer-comprehensive',
                        'version': '2.0'
                    },
                    'entries': self.global_requests,
                    'session_info': {
                        'session_id': self.session_id,
                        'start_time': self.session_start_time.isoformat(),
                        'end_time': datetime.now().isoformat(),
                        'total_requests': len(self.global_requests),
                        'total_tasks': len(self.task_requests),
                        'recording_duration_seconds': (datetime.now() - self.session_start_time).total_seconds()
                    },
                    'task_breakdown': {
                        task_id: {
                            'start_time': info['start_time'].isoformat(),
                            'end_time': info.get('end_time', datetime.now()).isoformat(),
                            'request_count': len(info.get('requests', [])),
                            'request_range': f"{info['start_index']}-{info['start_index'] + len(info.get('requests', []))}"
                        }
                        for task_id, info in self.task_requests.items()
                    }
                }
            }
            
            # Save comprehensive HAR file
            comprehensive_har_path = session_dir / f"comprehensive_session_{timestamp}.har"
            with open(comprehensive_har_path, 'w') as f:
                json.dump(comprehensive_har, f, indent=2)
            
            # Create HAR analysis summary
            har_summary = {
                'session_id': self.session_id,
                'timestamp': timestamp,
                'files_created': {
                    'comprehensive_har': str(comprehensive_har_path),
                    'task_specific_hars': {
                        task_id: str(info.get('har_file', 'Not created'))
                        for task_id, info in self.task_requests.items()
                    }
                },
                'statistics': {
                    'total_requests': len(self.global_requests),
                    'total_tasks': len(self.task_requests),
                    'recording_duration_seconds': (datetime.now() - self.session_start_time).total_seconds(),
                    'average_requests_per_task': len(self.global_requests) / max(len(self.task_requests), 1)
                },
                'request_types': self._analyze_request_types(),
                'domains': self._analyze_domains(),
                'status_codes': self._analyze_status_codes()
            }
            
            # Save HAR summary
            summary_path = session_dir / f"har_analysis_summary_{timestamp}.json"
            with open(summary_path, 'w') as f:
                json.dump(har_summary, f, indent=2)
            
            self.logger.info(f"📊 Comprehensive HAR recording completed:")
            self.logger.info(f"   📁 Main HAR: {comprehensive_har_path} ({len(self.global_requests)} requests)")
            self.logger.info(f"   📋 Task HARs: {len(self.task_requests)} files")
            self.logger.info(f"   📈 Summary: {summary_path}")
            
            return har_summary
            
        except Exception as e:
            self.logger.error(f"Failed to save comprehensive session HAR: {e}")
            return {}
    
    def _analyze_request_types(self) -> Dict[str, int]:
        """Analyze request types in captured data"""
        types = {}
        for request in self.global_requests:
            req_type = request.get('type', 'unknown')
            types[req_type] = types.get(req_type, 0) + 1
        return types
    
    def _analyze_domains(self) -> Dict[str, int]:
        """Analyze domains in captured requests"""
        domains = {}
        for request in self.global_requests:
            try:
                from urllib.parse import urlparse
                domain = urlparse(request.get('url', '')).netloc
                if domain:
                    domains[domain] = domains.get(domain, 0) + 1
            except:
                pass
        return dict(sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10])  # Top 10
    
    def _analyze_status_codes(self) -> Dict[str, int]:
        """Analyze HTTP status codes in responses"""
        status_codes = {}
        for request in self.global_requests:
            if request.get('type') == 'response':
                status = str(request.get('status', 'unknown'))
                status_codes[status] = status_codes.get(status, 0) + 1
        return status_codes
    
    async def stop_global_recording(self):
        """Stop global HAR recording"""
        if self.is_recording:
            self.is_recording = False
            self.logger.info(f"🛑 Global HAR recording stopped - {len(self.global_requests)} requests captured")
        else:
            self.logger.info("🛑 Global HAR recording was already stopped")
    
    def get_recording_stats(self) -> Dict[str, Any]:
        """Get current recording statistics"""
        return {
            'is_recording': self.is_recording,
            'total_requests': len(self.global_requests),
            'active_tasks': len(self.task_requests),
            'recording_duration': (datetime.now() - self.session_start_time).total_seconds(),
            'last_request_time': self.global_requests[-1]['timestamp'] if self.global_requests else None
        }
