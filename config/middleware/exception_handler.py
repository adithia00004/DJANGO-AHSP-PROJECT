"""
Global Exception Handler Middleware

Catches all unhandled exceptions and provides user-friendly responses.
Also integrates with Sentry for error tracking.

Usage:
    Add to MIDDLEWARE in settings:
    'config.middleware.exception_handler.ExceptionHandlerMiddleware',
"""

import logging
import traceback
import sys

from django.conf import settings
from django.http import JsonResponse, HttpResponse, Http404

logger = logging.getLogger(__name__)


class ExceptionHandlerMiddleware:
    """
    Middleware that catches all unhandled exceptions and provides
    appropriate error responses.
    
    Features:
    - Returns JSON for API/AJAX requests
    - Returns HTML error page for browser requests
    - Logs detailed error information
    - Integrates with Sentry if configured
    
    Note: Http404 and PermissionDenied are NOT caught here - they are
    passed through to Django's default handlers for proper status codes.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        return self.get_response(request)
    
    def process_exception(self, request, exception):
        """
        Handle exceptions that bubble up to the middleware layer.
        
        Args:
            request: The Django request object
            exception: The exception that was raised
            
        Returns:
            HttpResponse or JsonResponse with error details,
            or None to let Django handle the exception (e.g., Http404)
        """
        # Let Django handle Http404 and PermissionDenied natively
        # This ensures proper 404/403 status codes are returned
        from django.core.exceptions import PermissionDenied
        if isinstance(exception, (Http404, PermissionDenied)):
            return None  # Let Django's default handler process this
        
        # Get exception info
        exc_type, exc_value, exc_tb = sys.exc_info()
        error_id = self._generate_error_id()
        
        # Log the exception
        # IMPORTANT: Use _cached_user to avoid triggering lazy user load during exception handling
        # This prevents cascade database locks when original error is DB-related
        user_info = 'unknown'
        if hasattr(request, '_cached_user') and request._cached_user is not None:
            user_info = getattr(request._cached_user, 'username', 'anonymous')
        elif hasattr(request, 'user'):
            # Only try to access user if it's already loaded (won't trigger DB query)
            try:
                user_obj = request.user._wrapped if hasattr(request.user, '_wrapped') else None
                if user_obj is not None:
                    user_info = getattr(user_obj, 'username', 'anonymous')
            except Exception:
                user_info = 'error-accessing-user'

        logger.error(
            f"Unhandled exception [{error_id}]: {exception}",
            exc_info=True,
            extra={
                'error_id': error_id,
                'path': request.path,
                'method': request.method,
                'user': user_info,
            }
        )
        
        # Send to Sentry if available
        self._send_to_sentry(exception, request, error_id)
        
        # Determine response type
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        accepts_json = 'application/json' in request.headers.get('Accept', '')
        is_api = request.path.startswith('/api/') or is_ajax or accepts_json
        
        if is_api:
            return self._json_error_response(exception, error_id)
        else:
            return self._html_error_response(exception, error_id)
    
    def _generate_error_id(self):
        """Generate a unique error ID for tracking."""
        import uuid
        return str(uuid.uuid4())[:8].upper()
    
    def _send_to_sentry(self, exception, request, error_id):
        """Send exception to Sentry if configured."""
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                scope.set_tag('error_id', error_id)
                scope.set_context('request', {
                    'path': request.path,
                    'method': request.method,
                })
                sentry_sdk.capture_exception(exception)
        except ImportError:
            pass  # Sentry not installed
        except Exception as e:
            logger.warning(f"Failed to send to Sentry: {e}")
    
    def _json_error_response(self, exception, error_id):
        """Generate JSON error response for API requests."""
        # Don't expose details in production
        is_debug = getattr(settings, 'DEBUG', False)
        
        response_data = {
            'success': False,
            'error': {
                'code': 'SERVER_ERROR',
                'message': 'Terjadi kesalahan server. Tim kami sudah diberitahu.',
                'error_id': error_id,
                'recoverable': True,
                'actions': ['reload', 'report'],
            }
        }
        
        if is_debug:
            response_data['error']['debug'] = {
                'type': type(exception).__name__,
                'message': str(exception),
                'traceback': traceback.format_exc(),
            }
        
        return JsonResponse(response_data, status=500)
    
    def _html_error_response(self, exception, error_id):
        """Generate HTML error page for browser requests."""
        is_debug = getattr(settings, 'DEBUG', False)
        
        debug_info = ''
        if is_debug:
            debug_info = f"""
            <details style="margin-top: 2rem; text-align: left; background: #1f2937; color: #f3f4f6; padding: 1rem; border-radius: 0.5rem; max-width: 800px; margin-left: auto; margin-right: auto;">
                <summary style="cursor: pointer; font-weight: 600;">Debug Info (Development Only)</summary>
                <pre style="overflow-x: auto; font-size: 0.8rem; margin-top: 1rem;">{traceback.format_exc()}</pre>
            </details>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html lang="id">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Terjadi Kesalahan - Error {error_id}</title>
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
                    width: 100%;
                }}
                h1 {{
                    font-size: 4rem;
                    margin: 0;
                    color: #dc3545;
                }}
                h2 {{
                    font-size: 1.5rem;
                    margin: 1rem 0;
                }}
                p {{
                    color: #6b7280;
                    margin-bottom: 1rem;
                }}
                .error-id {{
                    font-family: monospace;
                    background: #e5e7eb;
                    padding: 0.25rem 0.5rem;
                    border-radius: 0.25rem;
                    font-size: 0.875rem;
                }}
                .btn {{
                    display: inline-block;
                    padding: 0.75rem 1.5rem;
                    background: #0d6efd;
                    color: white;
                    text-decoration: none;
                    border-radius: 0.5rem;
                    margin: 0.25rem;
                    border: none;
                    cursor: pointer;
                    font-size: 1rem;
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
                <h1>⚠️</h1>
                <h2>Terjadi Kesalahan Server</h2>
                <p>
                    Maaf, terjadi kesalahan yang tidak terduga.<br>
                    Tim kami sudah diberitahu dan sedang menangani masalah ini.
                </p>
                <p>
                    <span class="error-id">Error ID: {error_id}</span>
                </p>
                <div style="margin-top: 1.5rem;">
                    <a href="javascript:location.reload()" class="btn">Coba Lagi</a>
                    <a href="/" class="btn btn-secondary">Kembali ke Dashboard</a>
                </div>
                {debug_info}
            </div>
        </body>
        </html>
        """
        
        return HttpResponse(content=html, status=500, content_type='text/html')
