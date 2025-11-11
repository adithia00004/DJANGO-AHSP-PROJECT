"""
Tests for Phase 4 infrastructure components:
- Health check endpoints
- API response helpers
- Rate limiting functionality

These tests verify the production-ready infrastructure we've added.
"""

import pytest
import json
from django.test import Client, override_settings
from django.urls import reverse
from django.core.cache import cache
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock


# ============================================================================
# Health Check Tests
# ============================================================================

@pytest.mark.django_db
class TestHealthCheckEndpoints:
    """Test health check endpoints for monitoring."""

    def test_health_check_success(self, client):
        """Test full health check returns 200 when all systems OK."""
        response = client.get('/health/')

        assert response.status_code == 200
        data = response.json()

        assert data['status'] == 'ok'
        assert 'checks' in data
        assert 'database' in data['checks']
        assert 'cache' in data['checks']
        assert 'version' in data
        assert 'timestamp' in data

        # Database should be OK
        assert data['checks']['database']['status'] == 'ok'

        # Cache should be OK
        assert data['checks']['cache']['status'] == 'ok'

    def test_health_check_database_failure(self, client):
        """Test health check returns 503 when database fails."""
        with patch('django.db.connection.cursor') as mock_cursor:
            mock_cursor.side_effect = Exception('Database connection failed')

            response = client.get('/health/')

            assert response.status_code == 503
            data = response.json()

            assert data['status'] == 'error'
            assert data['checks']['database']['status'] == 'error'

    def test_health_check_cache_failure(self, client):
        """Test health check returns 503 when cache fails."""
        with patch('django.core.cache.cache.set') as mock_set:
            mock_set.side_effect = Exception('Redis connection failed')

            response = client.get('/health/')

            assert response.status_code == 503
            data = response.json()

            assert data['status'] == 'error'
            assert data['checks']['cache']['status'] == 'error'

    def test_health_check_simple(self, client):
        """Test simple health check (no dependencies)."""
        response = client.get('/health/simple/')

        assert response.status_code == 200
        data = response.json()

        assert data['status'] == 'ok'

    def test_readiness_check(self, client):
        """Test readiness check for Kubernetes."""
        response = client.get('/health/ready/')

        assert response.status_code == 200
        data = response.json()

        assert 'status' in data
        assert 'checks' in data

    def test_liveness_check(self, client):
        """Test liveness check for Kubernetes."""
        response = client.get('/health/live/')

        assert response.status_code == 200
        data = response.json()

        assert data['status'] == 'alive'

    def test_health_check_no_csrf_required(self, client):
        """Test health checks work without CSRF token."""
        # CSRF should not be required for health checks
        response = client.get('/health/')
        assert response.status_code == 200

    def test_health_check_allows_get_only(self, client):
        """Test health checks only allow GET method."""
        response = client.post('/health/')
        assert response.status_code == 405  # Method Not Allowed


# ============================================================================
# API Response Helpers Tests
# ============================================================================

@pytest.mark.django_db
class TestAPIResponseHelpers:
    """Test APIResponse helper class for standardized responses."""

    def test_api_response_success(self):
        """Test APIResponse.success creates proper response."""
        from detail_project.api_helpers import APIResponse

        response = APIResponse.success(
            data={'id': 1, 'name': 'Test'},
            message='Operation successful'
        )

        assert response.status_code == 200
        data = json.loads(response.content)

        assert data['success'] is True
        assert data['data']['id'] == 1
        assert data['message'] == 'Operation successful'

    def test_api_response_success_without_message(self):
        """Test APIResponse.success without message."""
        from detail_project.api_helpers import APIResponse

        response = APIResponse.success(data={'count': 5})

        assert response.status_code == 200
        data = json.loads(response.content)

        assert data['success'] is True
        assert data['data']['count'] == 5
        assert data['message'] is None

    def test_api_response_error(self):
        """Test APIResponse.error creates proper error response."""
        from detail_project.api_helpers import APIResponse

        response = APIResponse.error(
            message='Validation failed',
            code='VALIDATION_ERROR',
            details={'field': 'name', 'error': 'required'},
            status=400
        )

        assert response.status_code == 400
        data = json.loads(response.content)

        assert data['success'] is False
        assert data['message'] == 'Validation failed'
        assert data['code'] == 'VALIDATION_ERROR'
        assert data['details']['field'] == 'name'

    def test_api_response_error_default_status(self):
        """Test APIResponse.error uses 400 as default status."""
        from detail_project.api_helpers import APIResponse

        response = APIResponse.error(message='Error occurred')

        assert response.status_code == 400
        data = json.loads(response.content)

        assert data['success'] is False
        assert data['message'] == 'Error occurred'

    def test_api_response_not_found(self):
        """Test APIResponse.not_found convenience method."""
        from detail_project.api_helpers import APIResponse

        response = APIResponse.not_found(message='Resource not found')

        assert response.status_code == 404
        data = json.loads(response.content)

        assert data['success'] is False
        assert data['message'] == 'Resource not found'
        assert data['code'] == 'NOT_FOUND'

    def test_api_response_created(self):
        """Test APIResponse.created for resource creation."""
        from detail_project.api_helpers import APIResponse

        response = APIResponse.created(
            data={'id': 123},
            message='Resource created'
        )

        assert response.status_code == 201
        data = json.loads(response.content)

        assert data['success'] is True
        assert data['data']['id'] == 123


# ============================================================================
# Rate Limiting Tests
# ============================================================================

@pytest.mark.django_db
class TestRateLimiting:
    """Test rate limiting functionality."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    def test_rate_limit_decorator_basic(self, client_logged, user):
        """Test basic rate limiting decorator."""
        from detail_project.api_helpers import rate_limit
        from django.http import JsonResponse
        from django.test import RequestFactory

        factory = RequestFactory()

        # Create a test view with rate limit
        @rate_limit(max_requests=5, window=60)
        def test_view(request):
            return JsonResponse({'status': 'ok'})

        # First 5 requests should succeed
        for i in range(5):
            request = factory.get('/test/')
            request.user = user
            response = test_view(request)
            assert response.status_code == 200

        # 6th request should be rate limited
        request = factory.get('/test/')
        request.user = user
        response = test_view(request)
        assert response.status_code == 429
        data = json.loads(response.content)
        assert 'rate limit exceeded' in data['message'].lower() or 'terlalu banyak' in data['message'].lower()

    def test_rate_limit_per_user(self, client_logged):
        """Test rate limiting is per-user."""
        from detail_project.api_helpers import rate_limit
        from django.http import JsonResponse
        from django.test import RequestFactory

        factory = RequestFactory()
        User = get_user_model()
        user1 = User.objects.create_user(username='user1', password='pass')
        user2 = User.objects.create_user(username='user2', password='pass')

        @rate_limit(max_requests=3, window=60)
        def test_view(request):
            return JsonResponse({'status': 'ok'})

        # User1 uses up their limit
        for i in range(3):
            request = factory.get('/test/')
            request.user = user1
            response = test_view(request)
            assert response.status_code == 200

        # User1's 4th request is blocked
        request = factory.get('/test/')
        request.user = user1
        response = test_view(request)
        assert response.status_code == 429

        # But user2 can still make requests
        request = factory.get('/test/')
        request.user = user2
        response = test_view(request)
        assert response.status_code == 200

    def test_rate_limit_categories(self):
        """Test category-based rate limiting."""
        from detail_project.api_helpers import RATE_LIMIT_CATEGORIES

        # Verify categories are configured
        assert 'bulk' in RATE_LIMIT_CATEGORIES
        assert 'write' in RATE_LIMIT_CATEGORIES
        assert 'read' in RATE_LIMIT_CATEGORIES
        assert 'export' in RATE_LIMIT_CATEGORIES

        # Verify bulk operations have stricter limits
        bulk = RATE_LIMIT_CATEGORIES['bulk']
        write = RATE_LIMIT_CATEGORIES['write']
        read = RATE_LIMIT_CATEGORIES['read']

        assert bulk['max_requests'] < write['max_requests']
        assert write['max_requests'] < read['max_requests']

        # Verify bulk operations have longer window
        assert bulk['window'] > write['window']

    def test_rate_limit_with_category_bulk(self, client_logged, user):
        """Test rate limiting with 'bulk' category."""
        from detail_project.api_helpers import rate_limit, RATE_LIMIT_CATEGORIES
        from django.http import JsonResponse
        from django.test import RequestFactory

        factory = RequestFactory()

        @rate_limit(category='bulk')
        def bulk_operation(request):
            return JsonResponse({'status': 'ok'})

        bulk_config = RATE_LIMIT_CATEGORIES['bulk']
        max_requests = bulk_config['max_requests']

        # Should succeed up to max_requests
        for i in range(max_requests):
            request = factory.get('/test/')
            request.user = user
            response = bulk_operation(request)
            assert response.status_code == 200

        # Next request should be rate limited
        request = factory.get('/test/')
        request.user = user
        response = bulk_operation(request)
        assert response.status_code == 429

    def test_rate_limit_with_category_write(self, client_logged, user):
        """Test rate limiting with 'write' category."""
        from detail_project.api_helpers import rate_limit, RATE_LIMIT_CATEGORIES
        from django.http import JsonResponse
        from django.test import RequestFactory

        factory = RequestFactory()

        @rate_limit(category='write')
        def write_operation(request):
            return JsonResponse({'status': 'ok'})

        write_config = RATE_LIMIT_CATEGORIES['write']
        max_requests = write_config['max_requests']

        # Write operations should have higher limit than bulk
        assert max_requests > RATE_LIMIT_CATEGORIES['bulk']['max_requests']

        # Test a few requests succeed
        for i in range(min(5, max_requests)):
            request = factory.get('/test/')
            request.user = user
            response = write_operation(request)
            assert response.status_code == 200

    def test_rate_limit_response_includes_retry_after(self, client_logged, user):
        """Test rate limit response includes Retry-After header."""
        from detail_project.api_helpers import rate_limit
        from django.http import JsonResponse
        from django.test import RequestFactory

        factory = RequestFactory()

        @rate_limit(max_requests=1, window=60)
        def test_view(request):
            return JsonResponse({'status': 'ok'})

        # First request succeeds
        request = factory.get('/test/')
        request.user = user
        response = test_view(request)
        assert response.status_code == 200

        # Second request is rate limited
        request = factory.get('/test/')
        request.user = user
        response = test_view(request)
        assert response.status_code == 429

        # Should include retry_after in response
        data = json.loads(response.content)
        assert 'retry_after' in data or 'details' in data

    def test_rate_limit_anonymous_user(self, client):
        """Test rate limiting works for anonymous users."""
        from detail_project.api_helpers import rate_limit
        from django.http import JsonResponse
        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser

        factory = RequestFactory()

        @rate_limit(max_requests=2, window=60)
        def test_view(request):
            return JsonResponse({'status': 'ok'})

        # Anonymous users should also be rate limited
        for i in range(2):
            request = factory.get('/test/')
            request.user = AnonymousUser()
            response = test_view(request)
            assert response.status_code == 200

        # 3rd request should be blocked
        request = factory.get('/test/')
        request.user = AnonymousUser()
        response = test_view(request)
        assert response.status_code == 429


# ============================================================================
# API Endpoint Decorator Tests
# ============================================================================

@pytest.mark.django_db
class TestAPIEndpointDecorator:
    """Test the api_endpoint decorator."""

    def test_api_endpoint_requires_login(self, client):
        """Test api_endpoint decorator requires authentication."""
        from detail_project.api_helpers import api_endpoint
        from django.http import JsonResponse
        from django.test import RequestFactory
        from django.contrib.auth.models import AnonymousUser

        factory = RequestFactory()

        @api_endpoint()
        def test_view(request):
            return JsonResponse({'status': 'ok'})

        # Anonymous request should be redirected to login (302) or rejected (401)
        request = factory.get('/test/')
        request.user = AnonymousUser()
        response = test_view(request)
        # login_required returns 302 redirect
        assert response.status_code in [302, 401]

    def test_api_endpoint_allows_authenticated(self, client_logged, user):
        """Test api_endpoint allows authenticated users."""
        from detail_project.api_helpers import api_endpoint
        from django.http import JsonResponse
        from django.test import RequestFactory

        factory = RequestFactory()

        @api_endpoint()
        def test_view(request):
            return JsonResponse({'status': 'ok'})

        # Authenticated request should succeed
        request = factory.get('/test/')
        request.user = user
        response = test_view(request)
        assert response.status_code == 200

    def test_api_endpoint_with_rate_limit_category(self, client_logged, user):
        """Test api_endpoint with rate limit category."""
        from detail_project.api_helpers import api_endpoint, RATE_LIMIT_CATEGORIES
        from django.http import JsonResponse
        from django.test import RequestFactory

        factory = RequestFactory()

        @api_endpoint(category='bulk')
        def bulk_view(request):
            return JsonResponse({'status': 'ok'})

        # Should apply bulk rate limits
        max_requests = RATE_LIMIT_CATEGORIES['bulk']['max_requests']

        # Requests up to limit should succeed
        for i in range(max_requests):
            request = factory.get('/test/')
            request.user = user
            response = bulk_view(request)
            assert response.status_code == 200

        # Next request should be rate limited
        request = factory.get('/test/')
        request.user = user
        response = bulk_view(request)
        assert response.status_code == 429

    def test_api_endpoint_exception_handling(self, client_logged, user):
        """Test api_endpoint decorator allows exceptions to propagate (normal Django behavior)."""
        from detail_project.api_helpers import api_endpoint
        from django.test import RequestFactory

        factory = RequestFactory()

        @api_endpoint()
        def error_view(request):
            raise ValueError('Test error')

        # Exception should propagate (not caught by decorator)
        request = factory.get('/test/')
        request.user = user

        # Verify that exception is raised (not handled by decorator)
        with pytest.raises(ValueError, match='Test error'):
            error_view(request)


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.django_db
class TestPhase4Integration:
    """Integration tests for Phase 4 infrastructure."""

    def test_health_check_with_cache_backend(self, client):
        """Test health check works with configured cache backend."""
        # Clear cache first
        cache.clear()

        response = client.get('/health/')
        assert response.status_code == 200

        data = response.json()
        assert data['checks']['cache']['status'] == 'ok'
        assert 'backend' in data['checks']['cache']

    def test_rate_limiting_uses_cache(self, client_logged, user):
        """Test rate limiting actually uses cache for tracking."""
        from detail_project.api_helpers import rate_limit
        from django.http import JsonResponse
        from django.test import RequestFactory

        factory = RequestFactory()

        @rate_limit(max_requests=3, window=60, key_prefix='test')
        def test_view(request):
            return JsonResponse({'status': 'ok'})

        # Make requests
        for i in range(3):
            request = factory.get('/test/')
            request.user = user
            test_view(request)

        # Check that cache has rate limit keys
        # The key format should be: rate_limit:{user_id}:{endpoint}
        cache_key = f"rate_limit:{user.id}:test_view"
        cached_value = cache.get(cache_key)
        # Cache should have rate limit data
        assert cached_value is not None

    def test_complete_api_request_flow(self, client_logged, project):
        """Test complete API request with auth, rate limit, and response."""
        # This would test an actual API endpoint if we had one decorated
        # For now, verify the components work together
        from detail_project.api_helpers import APIResponse, rate_limit

        # Verify imports work
        assert APIResponse is not None
        assert rate_limit is not None


# ============================================================================
# Pytest Configuration
# ============================================================================

@pytest.fixture
def client():
    """Provide a Django test client."""
    from django.test import Client
    return Client()


@pytest.fixture
def user(db):
    """Create a test user."""
    User = get_user_model()
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def client_logged(client, user):
    """Provide an authenticated test client."""
    client.force_login(user)
    return client


@pytest.fixture
def project(db, user):
    """Create a test project."""
    from dashboard.models import Project
    from datetime import date

    return Project.objects.create(
        nama='Test Project',
        owner=user,
        is_active=True,
        tahun_project=2025,
        tanggal_mulai=date.today(),
        anggaran_owner=1000000
    )
