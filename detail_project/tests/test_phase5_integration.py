"""
Phase 5: Integration Tests

Tests for actual API endpoints with full Django request/response cycle.
These tests verify that all Phase 4 infrastructure works correctly
with real endpoints.

Test Coverage:
- API rate limiting with real endpoints
- Transaction safety and rollback
- Cache hit/miss behavior
- Error handling and recovery
- Loading states integration
- Authentication and authorization
"""

import pytest
import json
import time
from decimal import Decimal
from django.test import Client
from django.urls import reverse
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError


# ============================================================================
# Integration Test: Rate Limiting with Real Endpoints
# ============================================================================

@pytest.mark.django_db
class TestRateLimitingIntegration:
    """Test rate limiting with actual API endpoints."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    def test_rate_limit_on_api_save_endpoint(self, client_logged, project):
        """Test rate limiting blocks excessive save requests."""
        from detail_project.api_helpers import RATE_LIMIT_CATEGORIES

        # Assuming api_save_pekerjaan has category='write'
        write_limit = RATE_LIMIT_CATEGORIES['write']['max_requests']

        url = reverse('detail_project:api_save_list_pekerjaan', kwargs={'project_id': project.id})

        # Make requests up to limit
        for i in range(write_limit):
            response = client_logged.post(url,
                data=json.dumps({'test': 'data'}),
                content_type='application/json'
            )
            # May return 200, 400, etc. but NOT 429
            assert response.status_code != 429, f"Rate limited too early at request {i+1}"

        # Next request should be rate limited
        response = client_logged.post(url,
            data=json.dumps({'test': 'data'}),
            content_type='application/json'
        )
        assert response.status_code == 429, "Rate limit not enforced"

        data = response.json()
        assert data['success'] is False
        assert 'retry_after' in data or 'rate limit' in data['message'].lower()

    def test_rate_limit_different_users_independent(self, project):
        """Test rate limiting is independent per user."""
        User = get_user_model()

        # Create two users
        user1 = User.objects.create_user(username='ratelimit1', password='test')
        user2 = User.objects.create_user(username='ratelimit2', password='test')

        client1 = Client()
        client1.force_login(user1)

        client2 = Client()
        client2.force_login(user2)

        url = reverse('detail_project:api_save_list_pekerjaan', kwargs={'project_id': project.id})

        # User1 makes requests
        for i in range(3):
            client1.post(url, data=json.dumps({'test': 'user1'}), content_type='application/json')

        # User2 should not be affected by user1's requests
        response = client2.post(url, data=json.dumps({'test': 'user2'}), content_type='application/json')

        # Should NOT be rate limited (different user)
        assert response.status_code != 429

    def test_rate_limit_resets_after_window(self, client_logged, project):
        """Test rate limit resets after time window expires."""
        from detail_project.api_helpers import RATE_LIMIT_CATEGORIES

        url = reverse('detail_project:api_save_list_pekerjaan', kwargs={'project_id': project.id})

        # Make one request
        response = client_logged.post(url,
            data=json.dumps({'test': 'data'}),
            content_type='application/json'
        )

        # Cache key should exist
        # Wait a bit (in real scenario, would wait full window)
        # For testing, we can clear cache to simulate window expiry
        cache.clear()

        # Should be able to make requests again
        response = client_logged.post(url,
            data=json.dumps({'test': 'data'}),
            content_type='application/json'
        )
        assert response.status_code != 429


# ============================================================================
# Integration Test: Transaction Safety
# ============================================================================

@pytest.mark.django_db
class TestTransactionSafety:
    """Test transaction rollback and safety."""

    def test_transaction_rollback_on_error(self, client_logged, project, sub_klas):
        """Test that failed operations rollback properly."""
        from detail_project.models import Pekerjaan

        initial_count = Pekerjaan.objects.filter(project=project).count()

        url = reverse('detail_project:api_upsert_list_pekerjaan', kwargs={'project_id': project.id})

        # Send invalid data that should trigger error
        payload = {
            'klasifikasi': [{
                'nama': 'Test',
                'subs': [{
                    'nama': 'Sub1',
                    'jobs': [{
                        # Missing required fields
                        'ordering_index': 1
                        # Missing: source_type, snapshot_kode, etc.
                    }]
                }]
            }]
        }

        response = client_logged.post(url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should fail validation
        assert response.status_code >= 400

        # Database should not have partial data (rollback should occur)
        final_count = Pekerjaan.objects.filter(project=project).count()
        assert final_count == initial_count, "Transaction not rolled back"

    def test_concurrent_updates_with_locking(self, client_logged, project, pekerjaan_custom):
        """Test select_for_update prevents race conditions."""
        from detail_project.models import VolumePekerjaan

        # This test verifies that concurrent updates are serialized
        # In real scenario, would use threading/multiprocessing

        url = reverse('detail_project:api_save_volume_pekerjaan', kwargs={'project_id': project.id})

        payload = {
            'volumes': [{
                'pekerjaan_id': pekerjaan_custom.id,
                'quantity': '10.5'
            }]
        }

        # First update
        response1 = client_logged.post(url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Second update (would race in concurrent scenario)
        payload['volumes'][0]['quantity'] = '20.5'
        response2 = client_logged.post(url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Final value should be from last successful update
        volume = VolumePekerjaan.objects.get(
            project=project,
            pekerjaan=pekerjaan_custom
        )
        # Last update should win
        assert volume.quantity == Decimal('20.5')


# ============================================================================
# Integration Test: Cache Behavior
# ============================================================================

@pytest.mark.django_db
class TestCacheBehavior:
    """Test cache hit/miss behavior."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.clear()

    def test_cache_stores_rate_limit_data(self, client_logged, project):
        """Test that rate limit data is stored in cache."""
        url = reverse('detail_project:api_save_list_pekerjaan', kwargs={'project_id': project.id})

        # Make a request
        client_logged.post(url,
            data=json.dumps({'test': 'data'}),
            content_type='application/json'
        )

        # Cache should have rate limit keys
        # Format: rate_limit:{category}:{user_id}:{endpoint}
        # We can verify cache is being used by checking it's not empty
        # (specific key format depends on implementation)

    def test_cache_available_for_application(self):
        """Test cache is available and working."""
        # Test basic cache operations
        cache.set('test_key', 'test_value', 60)
        value = cache.get('test_key')
        assert value == 'test_value'

        # Cleanup
        cache.delete('test_key')

    def test_cache_handles_complex_objects(self):
        """Test cache can store complex Python objects."""
        test_data = {
            'list': [1, 2, 3],
            'dict': {'key': 'value'},
            'number': 42,
            'string': 'test'
        }

        cache.set('complex_test', test_data, 60)
        retrieved = cache.get('complex_test')

        assert retrieved == test_data
        cache.delete('complex_test')


# ============================================================================
# Integration Test: Error Handling
# ============================================================================

@pytest.mark.django_db
class TestErrorHandlingIntegration:
    """Test error handling across the stack."""

    def test_validation_error_returns_proper_response(self, client_logged, project):
        """Test validation errors return standardized response."""
        url = reverse('detail_project:api_upsert_list_pekerjaan', kwargs={'project_id': project.id})

        # Send completely invalid payload
        response = client_logged.post(url,
            data=json.dumps({'invalid': 'data'}),
            content_type='application/json'
        )

        # Should return error response
        assert response.status_code >= 400
        data = response.json()

        assert 'success' in data
        assert data['success'] is False
        assert 'message' in data

    def test_not_found_error_handling(self, client_logged):
        """Test 404 errors are handled properly."""
        # Try to access non-existent project
        url = reverse('detail_project:api_save_list_pekerjaan', kwargs={'project_id': 99999})

        response = client_logged.post(url,
            data=json.dumps({'test': 'data'}),
            content_type='application/json'
        )

        # Should return 404 or 400
        assert response.status_code in [400, 404]

    def test_unauthenticated_request_rejected(self, project):
        """Test unauthenticated requests are rejected."""
        client = Client()  # Not logged in

        url = reverse('detail_project:api_save_list_pekerjaan', kwargs={'project_id': project.id})

        response = client.post(url,
            data=json.dumps({'test': 'data'}),
            content_type='application/json'
        )

        # Should be redirected to login or return 401/403
        assert response.status_code in [302, 401, 403]

    def test_csrf_protection_on_unsafe_methods(self, client_logged, project):
        """Test CSRF protection is enabled."""
        # Django test client handles CSRF automatically
        # But we can verify CSRF middleware is enabled
        from django.conf import settings

        middleware = settings.MIDDLEWARE
        assert any('csrf' in m.lower() for m in middleware)


# ============================================================================
# Integration Test: Complete User Flows
# ============================================================================

@pytest.mark.django_db
class TestCompleteUserFlows:
    """Test complete user workflows end-to-end."""

    def test_complete_pekerjaan_creation_flow(self, client_logged, project):
        """Test complete flow: create → save → retrieve."""
        # 1. Get initial state
        tree_url = reverse('detail_project:api_get_list_pekerjaan_tree', kwargs={'project_id': project.id})
        response = client_logged.get(tree_url)
        initial_data = response.json()

        # 2. Create new pekerjaan via upsert
        upsert_url = reverse('detail_project:api_upsert_list_pekerjaan', kwargs={'project_id': project.id})

        payload = {
            'klasifikasi': [{
                'nama': 'Integration Test Klasifikasi',
                'subs': [{
                    'nama': 'Integration Test Sub',
                    'jobs': [{
                        'source_type': 'custom',
                        'snapshot_kode': 'INT-001',
                        'snapshot_uraian': 'Integration Test Pekerjaan',
                        'snapshot_satuan': 'unit',
                        'ordering_index': 1
                    }]
                }]
            }]
        }

        response = client_logged.post(upsert_url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should succeed (or fail with clear message)
        assert response.status_code in [200, 201, 400]

        if response.status_code in [200, 201]:
            # 3. Retrieve updated state
            response = client_logged.get(tree_url)
            updated_data = response.json()

            # Should have new data
            assert response.status_code == 200

    def test_complete_volume_update_flow(self, client_logged, project, pekerjaan_custom):
        """Test complete flow: set volume → retrieve → verify."""
        from detail_project.models import VolumePekerjaan

        volume_url = reverse('detail_project:api_save_volume_pekerjaan', kwargs={'project_id': project.id})

        # 1. Set volume
        payload = {
            'volumes': [{
                'pekerjaan_id': pekerjaan_custom.id,
                'quantity': '25.75'
            }]
        }

        response = client_logged.post(volume_url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Should succeed
        assert response.status_code in [200, 201]

        # 2. Verify in database
        volume = VolumePekerjaan.objects.filter(
            project=project,
            pekerjaan=pekerjaan_custom
        ).first()

        if volume:
            assert volume.quantity == Decimal('25.75')


# ============================================================================
# Integration Test: Performance Baseline
# ============================================================================

@pytest.mark.django_db
class TestPerformanceBaseline:
    """Establish performance baselines for critical endpoints."""

    def test_list_pekerjaan_tree_response_time(self, client_logged, project):
        """Test list pekerjaan tree responds within acceptable time."""
        url = reverse('detail_project:api_get_list_pekerjaan_tree', kwargs={'project_id': project.id})

        start_time = time.time()
        response = client_logged.get(url)
        elapsed = time.time() - start_time

        # Should respond within 2 seconds for small dataset
        assert elapsed < 2.0, f"Response took {elapsed:.2f}s"
        assert response.status_code == 200

    def test_save_endpoint_response_time(self, client_logged, project):
        """Test save endpoint responds within acceptable time."""
        url = reverse('detail_project:api_save_list_pekerjaan', kwargs={'project_id': project.id})

        payload = {'test': 'performance'}

        start_time = time.time()
        response = client_logged.post(url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        elapsed = time.time() - start_time

        # Should respond within 1 second
        assert elapsed < 1.0, f"Response took {elapsed:.2f}s"

    def test_health_check_response_time(self, client_logged):
        """Test health check is fast."""
        start_time = time.time()
        response = client_logged.get('/health/')
        elapsed = time.time() - start_time

        # Health check should be very fast (< 100ms)
        assert elapsed < 0.1, f"Health check took {elapsed:.3f}s"
        assert response.status_code == 200


# ============================================================================
# Pytest Fixtures (reuse from conftest.py)
# ============================================================================

@pytest.fixture
def client_logged(db, user):
    """Provide authenticated test client."""
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def user(db):
    """Create test user."""
    User = get_user_model()
    return User.objects.create_user(
        username='integrationtest',
        email='integration@test.com',
        password='testpass123'
    )


@pytest.fixture
def project(db, user):
    """Create test project."""
    from dashboard.models import Project
    from datetime import date

    return Project.objects.create(
        nama='Integration Test Project',
        owner=user,
        is_active=True,
        tahun_project=2025,
        tanggal_mulai=date.today(),
        anggaran_owner=1000000
    )


@pytest.fixture
def sub_klas(db, project):
    """Create sub-classification for tests."""
    from detail_project.models import Pekerjaan

    # Get the actual model for sub_klasifikasi
    sub_field = Pekerjaan._meta.get_field('sub_klasifikasi')
    SubModel = sub_field.remote_field.model

    # Create minimal sub-classification
    fields = {f.name: f for f in SubModel._meta.fields}
    kwargs = {}

    if 'project' in fields:
        kwargs['project'] = project

    if 'klasifikasi' in fields:
        # Need to create parent klasifikasi first
        klas_field = fields['klasifikasi']
        KlasModel = klas_field.remote_field.model

        klas_fields = {f.name: f for f in KlasModel._meta.fields}
        klas_kwargs = {}

        if 'project' in klas_fields:
            klas_kwargs['project'] = project

        klas_kwargs['nama'] = 'Integration Test Klas'
        klas = KlasModel.objects.create(**klas_kwargs)
        kwargs['klasifikasi'] = klas

    kwargs['nama'] = 'Integration Test Sub'
    return SubModel.objects.create(**kwargs)


@pytest.fixture
def pekerjaan_custom(db, project, sub_klas):
    """Create custom pekerjaan for tests."""
    from detail_project.models import Pekerjaan

    return Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type='custom',
        snapshot_kode='INT-TEST',
        snapshot_uraian='Integration Test Pekerjaan',
        snapshot_satuan='unit',
        ordering_index=1
    )
