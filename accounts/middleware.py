"""
Middleware for subscription-based access control.

This middleware blocks write operations (POST, PUT, PATCH, DELETE)
for users with expired subscriptions.
"""
import json
import re
from urllib.parse import urlencode

from django.http import HttpResponseRedirect, JsonResponse
from subscriptions.entitlements import FEATURE_WRITE_ACCESS, get_feature_access


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
        
        # Check write entitlement via centralized policy engine.
        decision = get_feature_access(request.user, FEATURE_WRITE_ACCESS)
        if not decision.allowed:
            # Check if this is an API request (expects JSON)
            if self._is_api_request(request):
                return JsonResponse({
                    'success': False,
                    'error': decision.message,
                    'code': decision.code,
                    'upgrade_url': decision.upgrade_url,
                }, status=403)
            else:
                # Block non-API write and redirect users to upgrade page.
                query = urlencode({
                    'reason': 'subscription_expired',
                    'next': request.get_full_path(),
                })
                return HttpResponseRedirect(f"/pricing/?{query}")

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
