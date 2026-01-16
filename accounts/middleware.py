"""
Middleware for subscription-based access control.

This middleware blocks write operations (POST, PUT, PATCH, DELETE)
for users with expired subscriptions.
"""
import json
import re
from django.http import JsonResponse


class SubscriptionMiddleware:
    """
    Middleware that enforces subscription requirements for write operations.
    
    - GET requests: Always allowed (read-only access)
    - POST/PUT/PATCH/DELETE: Requires active subscription
    
    Excluded paths:
    - /accounts/* (login, signup, etc.)
    - /admin/*
    - /health/*
    - /static/*
    - /media/*
    """
    
    EXCLUDED_PATH_PATTERNS = [
        r'^/accounts/',
        r'^/admin/',
        r'^/health/',
        r'^/static/',
        r'^/media/',
        r'^/$',  # Landing page
        r'^/pricing/',
    ]
    
    WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_patterns = [re.compile(p) for p in self.EXCLUDED_PATH_PATTERNS]
    
    def __call__(self, request):
        # Skip for non-authenticated users (let auth handle it)
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip for GET/HEAD/OPTIONS (read operations)
        if request.method not in self.WRITE_METHODS:
            return self.get_response(request)
        
        # Skip excluded paths
        path = request.path
        if any(pattern.match(path) for pattern in self.excluded_patterns):
            return self.get_response(request)
        
        # Check subscription
        if not request.user.is_subscription_active:
            # Check if this is an API request (expects JSON)
            if self._is_api_request(request):
                return JsonResponse({
                    'success': False,
                    'error': 'Langganan Anda telah berakhir. Anda hanya memiliki akses baca.',
                    'code': 'SUBSCRIPTION_EXPIRED',
                    'upgrade_url': '/pricing/'
                }, status=403)
            else:
                # For regular form submissions, redirect or show message
                # Let the view handle it (decorator/mixin will catch it)
                pass
        
        return self.get_response(request)
    
    def _is_api_request(self, request) -> bool:
        """Check if request expects JSON response."""
        content_type = request.content_type or ''
        accept = request.headers.get('Accept', '')
        
        return (
            'application/json' in content_type or
            'application/json' in accept or
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        )
