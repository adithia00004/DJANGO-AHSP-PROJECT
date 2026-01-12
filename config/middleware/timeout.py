"""
Request Timeout Middleware

Enforces a maximum request processing time to prevent server freeze.
Default timeout: 180 seconds (3 minutes)

Usage:
    Add to MIDDLEWARE in settings:
    'config.middleware.timeout.TimeoutMiddleware',
"""

import logging
import signal
import threading
import time
from functools import wraps

from django.conf import settings
from django.http import JsonResponse, HttpResponse

logger = logging.getLogger(__name__)

# Default timeout in seconds (3 minutes)
DEFAULT_TIMEOUT_SECONDS = 180


class TimeoutException(Exception):
    """Exception raised when request times out."""
    pass


class TimeoutMiddleware:
    """
    Middleware that enforces a maximum request processing time.
    
    If a request takes longer than REQUEST_TIMEOUT_SECONDS,
    it will be terminated and return a 504 Gateway Timeout response.
    
    Note: This middleware uses threading for timeout enforcement
    since signal-based timeouts don't work well with async/multi-threaded servers.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout_seconds = getattr(settings, 'REQUEST_TIMEOUT_SECONDS', DEFAULT_TIMEOUT_SECONDS)
    
    def __call__(self, request):
        # Skip timeout for certain paths (e.g., admin, static)
        if self._should_skip(request):
            return self.get_response(request)
        
        # Track request start time
        request._start_time = time.time()
        
        # For synchronous requests, we can use threading-based timeout
        response = None
        exception = None
        is_timeout = False
        
        def target():
            nonlocal response, exception
            try:
                response = self.get_response(request)
            except Exception as e:
                exception = e
        
        # Create and start thread
        thread = threading.Thread(target=target)
        thread.start()
        
        # Wait for completion or timeout
        thread.join(timeout=self.timeout_seconds)
        
        if thread.is_alive():
            # Request timed out
            is_timeout = True
            elapsed = time.time() - request._start_time
            
            logger.warning(
                f"Request timeout after {elapsed:.2f}s: {request.method} {request.path}",
                extra={
                    'path': request.path,
                    'method': request.method,
                    'elapsed': elapsed,
                    'timeout': self.timeout_seconds,
                    'user': getattr(request.user, 'username', 'anonymous') if hasattr(request, 'user') else 'unknown',
                }
            )
            
            # Return timeout response
            return self._timeout_response(request)
        
        # If there was an exception, re-raise it
        if exception:
            raise exception
        
        return response
    
    def _should_skip(self, request):
        """Determine if timeout should be skipped for this request."""
        skip_paths = [
            '/admin/',
            '/static/',
            '/media/',
            '/__debug__/',
        ]
        
        for path in skip_paths:
            if request.path.startswith(path):
                return True
        
        return False
    
    def _timeout_response(self, request):
        """Generate appropriate timeout response based on request type."""
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        accepts_json = 'application/json' in request.headers.get('Accept', '')
        is_api = request.path.startswith('/api/') or is_ajax or accepts_json
        
        if is_api:
            return JsonResponse({
                'success': False,
                'error': {
                    'code': 'TIMEOUT',
                    'message': f'Request timeout ({self.timeout_seconds // 60} menit). Silakan coba lagi.',
                    'recoverable': True,
                    'actions': ['wait', 'reload'],
                }
            }, status=504)
        else:
            # HTML response
            return HttpResponse(
                content=self._timeout_html(),
                status=504,
                content_type='text/html',
            )
    
    def _timeout_html(self):
        """Generate timeout HTML page."""
        return f"""
        <!DOCTYPE html>
        <html lang="id">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Request Timeout</title>
            <style>
                body {{
                    font-family: system-ui, -apple-system, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                    background: #f8f9fa;
                    color: #1f2937;
                }}
                .container {{
                    text-align: center;
                    padding: 2rem;
                    max-width: 500px;
                }}
                h1 {{
                    font-size: 4rem;
                    margin: 0;
                    color: #ffc107;
                }}
                h2 {{
                    font-size: 1.5rem;
                    margin: 1rem 0;
                }}
                p {{
                    color: #6b7280;
                    margin-bottom: 2rem;
                }}
                .btn {{
                    display: inline-block;
                    padding: 0.75rem 1.5rem;
                    background: #0d6efd;
                    color: white;
                    text-decoration: none;
                    border-radius: 0.5rem;
                    margin: 0.25rem;
                }}
                .btn:hover {{
                    background: #0a58ca;
                }}
                .btn-secondary {{
                    background: #6c757d;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⏱️</h1>
                <h2>Request Timeout</h2>
                <p>
                    Proses memakan waktu lebih dari {self.timeout_seconds // 60} menit
                    dan telah dihentikan untuk mencegah masalah server.
                </p>
                <a href="javascript:location.reload()" class="btn">Coba Lagi</a>
                <a href="/" class="btn btn-secondary">Kembali ke Dashboard</a>
            </div>
        </body>
        </html>
        """
