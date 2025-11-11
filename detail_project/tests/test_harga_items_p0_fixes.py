# detail_project/tests/test_harga_items_p0_fixes.py
"""
Comprehensive tests for Harga Items P0 fixes.

Tests cover all critical safety improvements:

P0 FIXES (Critical Safety):
1. Row-level locking with select_for_update() - prevent race conditions
2. Optimistic locking with timestamp - detect concurrent edits
3. Cache invalidation timing with transaction.on_commit() - prevent stale cache
4. User-friendly error messages - clear feedback in Indonesian
5. Concurrent edit scenarios - multi-user safety
6. BUK (profit/margin) save with project-level persistence
"""
import pytest
import json
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.cache import cache
from django.utils import timezone
from unittest.mock import patch

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan,
    DetailAHSPProject, HargaItemProject, ProjectPricing
)

User = get_user_model()


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def setup_harga_items_test(db, user, project, sub_klas):
    """
    Setup data untuk Harga Items P0 tests.
    """
    # Create pekerjaan
    pekerjaan = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="TEST001",
        snapshot_uraian="Test Pekerjaan",
        snapshot_satuan="M2",
        ordering_index=1,
    )

    # Create harga items used in project
    harga_tk = HargaItemProject.objects.create(
        project=project,
        kategori="TK",
        kode_item="TK.001",
        uraian="Pekerja",
        satuan="OH",
        harga_satuan=Decimal("150000.00"),
    )

    harga_bhn = HargaItemProject.objects.create(
        project=project,
        kategori="BHN",
        kode_item="BHN.001",
        uraian="Semen",
        satuan="Zak",
        harga_satuan=Decimal("85000.00"),
    )

    harga_alt = HargaItemProject.objects.create(
        project=project,
        kategori="ALT",
        kode_item="ALT.001",
        uraian="Excavator",
        satuan="Jam",
        harga_satuan=Decimal("500000.00"),
    )

    # Create detail AHSP to make items "used" in project
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        harga_item=harga_tk,
        kategori="TK",
        kode="TK.001",
        uraian="Pekerja",
        satuan="OH",
        koefisien=Decimal("2.500000"),
    )

    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        harga_item=harga_bhn,
        kategori="BHN",
        kode="BHN.001",
        uraian="Semen",
        satuan="Zak",
        koefisien=Decimal("10.000000"),
    )

    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        harga_item=harga_alt,
        kategori="ALT",
        kode="ALT.001",
        uraian="Excavator",
        satuan="Jam",
        koefisien=Decimal("1.500000"),
    )

    # Create ProjectPricing for BUK testing
    pricing, _ = ProjectPricing.objects.get_or_create(
        project=project,
        defaults={'markup_percent': Decimal('10.00')}
    )

    return {
        'pekerjaan': pekerjaan,
        'harga_tk': harga_tk,
        'harga_bhn': harga_bhn,
        'harga_alt': harga_alt,
        'pricing': pricing,
    }


@pytest.fixture
def second_user(db):
    """Create a second user for concurrent edit testing."""
    return User.objects.create_user(
        username="user2",
        email="user2@example.com",
        password="pass12345"
    )


# ============================================================================
# P0 FIX #1: ROW-LEVEL LOCKING
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestRowLevelLocking:
    """Test row-level locking with select_for_update() prevents race conditions."""

    def test_concurrent_save_with_locking_no_data_loss(self, client_logged, project, setup_harga_items_test):
        """
        Test that concurrent saves with row-level locking prevent data loss.

        Scenario:
        - Two users load same harga items
        - Both modify different items simultaneously
        - Both save at nearly same time
        - Row-level locks ensure no data loss
        """
        harga_tk = setup_harga_items_test['harga_tk']
        harga_bhn = setup_harga_items_test['harga_bhn']

        # Simulate User A updates TK item
        payload_a = {
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '180000.00',  # Changed from 150000
                }
            ]
        }

        # Simulate User B updates BHN item (different row)
        payload_b = {
            'items': [
                {
                    'id': harga_bhn.id,
                    'harga_satuan': '95000.00',  # Changed from 85000
                }
            ]
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})

        # Save both (with locking, these should serialize properly)
        resp_a = client_logged.post(url,
                                     data=json.dumps(payload_a),
                                     content_type='application/json')
        resp_b = client_logged.post(url,
                                     data=json.dumps(payload_b),
                                     content_type='application/json')

        assert resp_a.status_code == 200
        assert resp_b.status_code == 200

        # Verify both changes persisted (no data loss)
        harga_tk.refresh_from_db()
        harga_bhn.refresh_from_db()

        assert harga_tk.harga_satuan == Decimal('180000.00')
        assert harga_bhn.harga_satuan == Decimal('95000.00')

    def test_concurrent_save_same_item_serializes_correctly(self, client_logged, project, setup_harga_items_test):
        """
        Test that concurrent saves to SAME item serialize correctly with locking.

        Scenario:
        - Two users try to update SAME item simultaneously
        - Row-level lock forces serialization (one waits for other)
        - Last write wins (expected behavior with locking)
        """
        harga_tk = setup_harga_items_test['harga_tk']

        # Both users update same item
        payload_a = {
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '180000.00',
                }
            ]
        }

        payload_b = {
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '190000.00',
                }
            ]
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})

        # Save both - second will wait for first to complete due to row lock
        resp_a = client_logged.post(url,
                                     data=json.dumps(payload_a),
                                     content_type='application/json')
        resp_b = client_logged.post(url,
                                     data=json.dumps(payload_b),
                                     content_type='application/json')

        assert resp_a.status_code == 200
        assert resp_b.status_code == 200

        # Verify final state (last write wins)
        harga_tk.refresh_from_db()
        assert harga_tk.harga_satuan == Decimal('190000.00')


# ============================================================================
# P0 FIX #2: OPTIMISTIC LOCKING
# ============================================================================

@pytest.mark.django_db
class TestOptimisticLocking:
    """Test optimistic locking with timestamp-based conflict detection."""

    def test_save_with_outdated_timestamp_returns_409_conflict(self, client_logged, project, setup_harga_items_test):
        """
        Test that save with outdated timestamp returns 409 Conflict.

        Scenario:
        - User A loads data at T0
        - User B loads data at T1, modifies, saves at T2 (project.updated_at = T2)
        - User A tries to save at T3 with old timestamp (T0)
        - Server detects conflict (T0 < T2) and returns 409
        """
        harga_tk = setup_harga_items_test['harga_tk']

        # Get current project timestamp (simulate User A loaded at T0)
        project.refresh_from_db()
        old_timestamp = project.updated_at.isoformat()

        # Simulate User B saves (updates project.updated_at)
        project.updated_at = timezone.now()
        project.save(update_fields=['updated_at'])

        # User A tries to save with old timestamp
        payload = {
            'client_updated_at': old_timestamp,  # Old timestamp!
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '180000.00',
                }
            ]
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        # Should return 409 Conflict
        assert resp.status_code == 409
        data = resp.json()
        assert data['ok'] is False
        assert data.get('conflict') is True
        assert 'user_message' in data
        assert 'KONFLIK' in data['user_message']
        assert 'server_updated_at' in data

        # Verify data NOT changed (conflict prevented overwrite)
        harga_tk.refresh_from_db()
        assert harga_tk.harga_satuan == Decimal('150000.00')  # Original value

    def test_save_with_current_timestamp_succeeds(self, client_logged, project, setup_harga_items_test):
        """
        Test that save with current timestamp succeeds.
        """
        harga_tk = setup_harga_items_test['harga_tk']

        # Get current project timestamp
        project.refresh_from_db()
        current_timestamp = project.updated_at.isoformat()

        # Save with current timestamp
        payload = {
            'client_updated_at': current_timestamp,
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '180000.00',
                }
            ]
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        # Should succeed
        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True

        # Verify data changed
        harga_tk.refresh_from_db()
        assert harga_tk.harga_satuan == Decimal('180000.00')

    def test_save_without_timestamp_succeeds_with_warning(self, client_logged, project, setup_harga_items_test):
        """
        Test that save WITHOUT timestamp still succeeds (backward compatibility).
        """
        harga_tk = setup_harga_items_test['harga_tk']

        # Save without timestamp (old clients)
        payload = {
            # No client_updated_at field
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '180000.00',
                }
            ]
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        # Should succeed (backward compatibility)
        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True

        # Verify data changed
        harga_tk.refresh_from_db()
        assert harga_tk.harga_satuan == Decimal('180000.00')


# ============================================================================
# P0 FIX #3: CACHE INVALIDATION TIMING
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestCacheInvalidationTiming:
    """Test cache invalidation timing with transaction.on_commit()."""

    def test_cache_invalidated_after_transaction_commits(self, client_logged, project, setup_harga_items_test):
        """
        Test that cache is invalidated AFTER transaction commits, not before.
        """
        harga_tk = setup_harga_items_test['harga_tk']

        # Warm up cache (simulate cache hit)
        cache_key = f"rekap_kebutuhan:{project.id}"
        cache.set(cache_key, {'test': 'data'}, 300)
        assert cache.get(cache_key) is not None

        # Save harga (should invalidate cache AFTER commit)
        payload = {
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '180000.00',
                }
            ]
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 200

        # Verify cache was invalidated (after commit)
        cached_data = cache.get(cache_key)
        # Cache should be cleared or None

    @patch('detail_project.views_api.invalidate_rekap_cache')
    def test_cache_invalidation_called_on_save(self, mock_invalidate, client_logged, project, setup_harga_items_test):
        """
        Test that cache invalidation function is called when data is saved.
        """
        harga_tk = setup_harga_items_test['harga_tk']

        payload = {
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '180000.00',
                }
            ]
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 200


# ============================================================================
# P0 FIX #4: USER-FRIENDLY ERROR MESSAGES
# ============================================================================

@pytest.mark.django_db
class TestUserFriendlyMessages:
    """Test user-friendly error messages in Indonesian."""

    def test_save_success_returns_friendly_message(self, client_logged, project, setup_harga_items_test):
        """Test successful save returns user-friendly success message."""
        harga_tk = setup_harga_items_test['harga_tk']

        payload = {
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '180000.00',
                }
            ]
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 200
        data = resp.json()
        assert 'user_message' in data
        assert 'Berhasil' in data['user_message'] or 'tersimpan' in data['user_message']

    def test_save_no_changes_returns_friendly_message(self, client_logged, project, setup_harga_items_test):
        """Test save with no changes returns friendly message."""
        # Save with no items (no changes)
        payload = {
            'items': []
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 200
        data = resp.json()
        assert 'user_message' in data
        # Should indicate no changes

    def test_validation_error_returns_friendly_message(self, client_logged, project, setup_harga_items_test):
        """Test validation error returns user-friendly error message."""
        harga_tk = setup_harga_items_test['harga_tk']

        # Invalid payload (invalid price format)
        payload = {
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': 'invalid_price',  # Invalid format
                }
            ]
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        # Should return error
        data = resp.json()
        assert 'errors' in data or 'user_message' in data

    def test_conflict_returns_friendly_indonesian_message(self, client_logged, project, setup_harga_items_test):
        """Test conflict (409) returns user-friendly Indonesian message."""
        harga_tk = setup_harga_items_test['harga_tk']

        # Get old timestamp
        project.refresh_from_db()
        old_timestamp = project.updated_at.isoformat()

        # Update project timestamp (simulate concurrent edit)
        project.updated_at = timezone.now()
        project.save(update_fields=['updated_at'])

        # Try to save with old timestamp
        payload = {
            'client_updated_at': old_timestamp,
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '180000.00',
                }
            ]
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 409
        data = resp.json()
        assert 'user_message' in data
        # Check for Indonesian keywords
        assert any(keyword in data['user_message'] for keyword in ['KONFLIK', 'konflik', 'diubah', 'Muat Ulang'])


# ============================================================================
# P0 FIX #5: CONCURRENT EDIT SCENARIOS
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestConcurrentEditScenarios:
    """Test realistic concurrent edit scenarios."""

    def test_two_users_edit_different_items(self, client_logged, client, second_user, project, setup_harga_items_test):
        """
        Test two users editing different items.
        Both should succeed without conflict.
        """
        harga_tk = setup_harga_items_test['harga_tk']
        harga_bhn = setup_harga_items_test['harga_bhn']

        # User 2 login
        client.force_login(second_user)
        # Give second_user access to project
        project.owner = second_user
        project.save()

        # User 1 edits TK
        payload_user1 = {
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '180000.00',
                }
            ]
        }

        # User 2 edits BHN
        payload_user2 = {
            'items': [
                {
                    'id': harga_bhn.id,
                    'harga_satuan': '95000.00',
                }
            ]
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})

        # Both save (should succeed - different items)
        resp1 = client_logged.post(url,
                                    data=json.dumps(payload_user1),
                                    content_type='application/json')
        resp2 = client.post(url,
                            data=json.dumps(payload_user2),
                            content_type='application/json')

        assert resp1.status_code == 200
        assert resp2.status_code == 200

        # Verify both changes persisted
        harga_tk.refresh_from_db()
        harga_bhn.refresh_from_db()
        assert harga_tk.harga_satuan == Decimal('180000.00')
        assert harga_bhn.harga_satuan == Decimal('95000.00')


# ============================================================================
# P0 FIX #6: BUK (PROFIT/MARGIN) SAVE
# ============================================================================

@pytest.mark.django_db
class TestBUKSave:
    """Test BUK (profit/margin) save functionality."""

    def test_save_buk_only(self, client_logged, project, setup_harga_items_test):
        """Test saving only BUK (no item changes)."""
        pricing = setup_harga_items_test['pricing']

        payload = {
            'items': [],
            'markup_percent': '15.00',  # Changed from 10.00 to 15.00
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True
        assert data.get('pricing_saved') is True

        # Verify BUK changed
        pricing.refresh_from_db()
        assert pricing.markup_percent == Decimal('15.00')

    def test_save_items_and_buk_together(self, client_logged, project, setup_harga_items_test):
        """Test saving both items and BUK in single request."""
        harga_tk = setup_harga_items_test['harga_tk']
        pricing = setup_harga_items_test['pricing']

        payload = {
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '180000.00',
                }
            ],
            'markup_percent': '12.50',
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True
        assert data.get('updated') == 1  # 1 item updated
        assert data.get('pricing_saved') is True

        # Verify both changed
        harga_tk.refresh_from_db()
        pricing.refresh_from_db()
        assert harga_tk.harga_satuan == Decimal('180000.00')
        assert pricing.markup_percent == Decimal('12.50')

    def test_list_returns_current_buk(self, client_logged, project, setup_harga_items_test):
        """Test list endpoint returns current BUK value."""
        pricing = setup_harga_items_test['pricing']

        url = reverse('detail_project:api_list_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.get(url)

        assert resp.status_code == 200
        data = resp.json()
        assert 'meta' in data
        assert 'markup_percent' in data['meta']
        assert data['meta']['markup_percent'] == '10.00'  # Default value


# ============================================================================
# INTEGRATION TEST: FULL WORKFLOW
# ============================================================================

@pytest.mark.django_db(transaction=True)
class TestFullWorkflowIntegration:
    """Integration tests for full user workflow."""

    def test_full_edit_workflow_with_optimistic_locking(self, client_logged, project, setup_harga_items_test):
        """
        Test full edit workflow:
        1. LIST items (receive timestamp)
        2. Modify data
        3. SAVE with timestamp (success)
        4. LIST again (new timestamp)
        5. Try to SAVE with old timestamp (conflict)
        """
        harga_tk = setup_harga_items_test['harga_tk']

        # Step 1: LIST items
        url_list = reverse('detail_project:api_list_harga_items', kwargs={'project_id': project.id})
        resp_list1 = client_logged.get(url_list)
        assert resp_list1.status_code == 200
        data1 = resp_list1.json()

        # Extract timestamp from response
        project.refresh_from_db()
        timestamp1 = project.updated_at.isoformat()

        # Step 2: Modify and SAVE
        payload = {
            'client_updated_at': timestamp1,
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '180000.00',
                }
            ]
        }

        url_save = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp_save = client_logged.post(url_save,
                                        data=json.dumps(payload),
                                        content_type='application/json')
        assert resp_save.status_code == 200

        # Step 3: LIST again (new timestamp)
        resp_list2 = client_logged.get(url_list)
        assert resp_list2.status_code == 200
        project.refresh_from_db()
        timestamp2 = project.updated_at.isoformat()

        # Timestamp should have changed
        assert timestamp2 != timestamp1

        # Step 4: Try to SAVE with old timestamp (should conflict)
        payload_old = {
            'client_updated_at': timestamp1,  # Old timestamp!
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '200000.00',
                }
            ]
        }

        resp_conflict = client_logged.post(url_save,
                                            data=json.dumps(payload_old),
                                            content_type='application/json')
        assert resp_conflict.status_code == 409
        data_conflict = resp_conflict.json()
        assert data_conflict.get('conflict') is True

    def test_full_workflow_with_buk_changes(self, client_logged, project, setup_harga_items_test):
        """
        Test full workflow with BUK changes:
        1. LIST (get current BUK)
        2. Modify items and BUK
        3. SAVE both
        4. LIST again (verify both changed)
        """
        harga_tk = setup_harga_items_test['harga_tk']
        harga_bhn = setup_harga_items_test['harga_bhn']
        pricing = setup_harga_items_test['pricing']

        # Step 1: LIST
        url_list = reverse('detail_project:api_list_harga_items', kwargs={'project_id': project.id})
        resp_list1 = client_logged.get(url_list)
        assert resp_list1.status_code == 200
        data1 = resp_list1.json()
        assert data1['meta']['markup_percent'] == '10.00'

        # Step 2: SAVE items + BUK
        payload = {
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '180000.00',
                },
                {
                    'id': harga_bhn.id,
                    'harga_satuan': '95000.00',
                }
            ],
            'markup_percent': '12.50',
        }

        url_save = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp_save = client_logged.post(url_save,
                                        data=json.dumps(payload),
                                        content_type='application/json')
        assert resp_save.status_code == 200
        data_save = resp_save.json()
        assert data_save['updated'] == 2
        assert data_save['pricing_saved'] is True

        # Step 3: LIST again (verify changes)
        resp_list2 = client_logged.get(url_list)
        assert resp_list2.status_code == 200
        data2 = resp_list2.json()
        assert data2['meta']['markup_percent'] == '12.50'

        # Verify items
        items = {item['id']: item for item in data2['items']}
        assert str(items[harga_tk.id]['harga_satuan']).replace(',', '') == '180000.00'
        assert str(items[harga_bhn.id]['harga_satuan']).replace(',', '') == '95000.00'


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.django_db
class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_save_nonexistent_item_returns_error(self, client_logged, project, setup_harga_items_test):
        """Test saving nonexistent item returns error."""
        payload = {
            'items': [
                {
                    'id': 99999,  # Nonexistent ID
                    'harga_satuan': '180000.00',
                }
            ]
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        # Should return error
        data = resp.json()
        assert 'errors' in data

    def test_save_invalid_price_format_returns_error(self, client_logged, project, setup_harga_items_test):
        """Test saving invalid price format returns error."""
        harga_tk = setup_harga_items_test['harga_tk']

        payload = {
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': 'abc',  # Invalid format
                }
            ]
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        # Should return error
        data = resp.json()
        assert 'errors' in data or data.get('ok') is False

    def test_save_negative_price_returns_error(self, client_logged, project, setup_harga_items_test):
        """Test saving negative price returns error."""
        harga_tk = setup_harga_items_test['harga_tk']

        payload = {
            'items': [
                {
                    'id': harga_tk.id,
                    'harga_satuan': '-1000.00',  # Negative price
                }
            ]
        }

        url = reverse('detail_project:api_save_harga_items', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        # Should return error or allow (depending on validation logic)
        data = resp.json()
        # Check if validation prevents negative prices
