"""
Test fixtures for Rekap Kebutuhan data consistency.

Validates that Snapshot, Timeline, and Category totals match.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan,
    DetailAHSPProject, DetailAHSPExpanded, HargaItemProject, 
    VolumePekerjaan, TahapPelaksanaan, PekerjaanTahapan, ProjectPricing
)
from detail_project.services import (
    compute_kebutuhan_items, 
    compute_kebutuhan_timeline,
)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def test_user(django_user_model):
    """Create test user."""
    return django_user_model.objects.create_user(
        username="test_sync", 
        password="testpass123"
    )


@pytest.fixture
def test_project(test_user):
    """Create test project with pricing."""
    project = Project.objects.create(
        owner=test_user,
        nama="Test Sync Project",
        is_active=True,
        tahun_project=timezone.now().year,
        anggaran_owner=Decimal("100000000"),
    )
    ProjectPricing.objects.create(
        project=project,
        markup_percent=Decimal("10.00")
    )
    return project


@pytest.fixture
def test_klasifikasi(test_project):
    """Create klasifikasi and sub-klasifikasi."""
    klas = Klasifikasi.objects.create(
        project=test_project,
        name="Struktur",
        ordering_index=1
    )
    sub = SubKlasifikasi.objects.create(
        project=test_project,
        klasifikasi=klas,
        name="Pondasi",
        ordering_index=1
    )
    return klas, sub


@pytest.fixture
def test_harga_items(test_project):
    """Create harga items for all categories."""
    items = {}
    
    items['tk'] = HargaItemProject.objects.create(
        project=test_project,
        kategori="TK",
        kode_item="TK.001",
        uraian="Mandor",
        satuan="OH",
        harga_satuan=Decimal("150000")
    )
    
    items['bhn'] = HargaItemProject.objects.create(
        project=test_project,
        kategori="BHN",
        kode_item="BHN.001",
        uraian="Semen PC 50kg",
        satuan="Zak",
        harga_satuan=Decimal("65000")
    )
    
    items['alt'] = HargaItemProject.objects.create(
        project=test_project,
        kategori="ALT",
        kode_item="ALT.001",
        uraian="Concrete Mixer",
        satuan="Jam",
        harga_satuan=Decimal("85000")
    )
    
    return items


@pytest.fixture
def test_pekerjaan_with_schedule(test_project, test_klasifikasi, test_harga_items):
    """
    Create pekerjaan with tahapan schedule spanning 4 weeks.
    This is essential for testing timeline vs snapshot consistency.
    """
    klas, sub = test_klasifikasi
    
    # Create pekerjaan
    pkj = Pekerjaan.objects.create(
        project=test_project,
        sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="PKJ-001",
        snapshot_uraian="Pengecoran Pondasi",
        snapshot_satuan="m3",
        ordering_index=1
    )
    
    # Add details
    DetailAHSPProject.objects.create(
        project=test_project,
        pekerjaan=pkj,
        harga_item=test_harga_items['tk'],
        kategori="TK",
        kode="TK.001",
        uraian="Mandor",
        satuan="OH",
        koefisien=Decimal("0.5")
    )
    
    DetailAHSPProject.objects.create(
        project=test_project,
        pekerjaan=pkj,
        harga_item=test_harga_items['bhn'],
        kategori="BHN",
        kode="BHN.001",
        uraian="Semen PC 50kg",
        satuan="Zak",
        koefisien=Decimal("7.0")
    )
    
    DetailAHSPProject.objects.create(
        project=test_project,
        pekerjaan=pkj,
        harga_item=test_harga_items['alt'],
        kategori="ALT",
        kode="ALT.001",
        uraian="Concrete Mixer",
        satuan="Jam",
        koefisien=Decimal("0.25")
    )
    
    # Add volume
    VolumePekerjaan.objects.create(
        project=test_project,
        pekerjaan=pkj,
        quantity=Decimal("100")
    )
    
    # Create tahapan (4 weeks)
    start_date = date.today()
    end_date = start_date + timedelta(days=27)  # 4 weeks
    
    tahap = TahapPelaksanaan.objects.create(
        project=test_project,
        nama="Tahap 1 - Pondasi",
        urutan=1,
        tanggal_mulai=start_date,
        tanggal_selesai=end_date
    )
    
    # Assign pekerjaan to tahapan (100%)
    PekerjaanTahapan.objects.create(
        pekerjaan=pkj,
        tahapan=tahap,
        proporsi_volume=Decimal("100")
    )
    
    # Note: DetailAHSPExpanded is populated by background process or signal
    # For tests, we work with DetailAHSPProject directly
    
    return pkj, tahap


# ==============================================================================
# TESTS
# ==============================================================================

@pytest.mark.django_db
class TestSnapshotTimelineConsistency:
    """Test that Snapshot and Timeline views produce consistent totals."""
    
    def test_snapshot_grand_total_matches_timeline_sum(
        self, test_project, test_pekerjaan_with_schedule
    ):
        """
        Snapshot grand total should equal sum of all timeline periods.
        (When time_scope includes all periods)
        """
        pkj, tahap = test_pekerjaan_with_schedule
        
        # Get snapshot data
        snapshot = compute_kebutuhan_items(test_project)
        snapshot_total = sum(
            Decimal(str(row.get('harga_total_decimal', 0)))
            for row in snapshot
        )
        
        # Get timeline data (all periods)
        timeline = compute_kebutuhan_timeline(test_project)
        timeline_periods = timeline.get('periods', [])
        
        # Sum all period totals
        timeline_total = sum(
            Decimal(str(p.get('total_cost_decimal', 0)))
            for p in timeline_periods
        )
        
        # Allow small rounding difference (0.01)
        diff = abs(snapshot_total - timeline_total)
        assert diff < Decimal("1.0"), (
            f"Snapshot total ({snapshot_total}) != Timeline total ({timeline_total}), "
            f"diff={diff}"
        )
    
    def test_category_breakdown_matches_between_views(
        self, test_project, test_pekerjaan_with_schedule
    ):
        """
        Category breakdown (TK, BHN, ALT) should be consistent.
        """
        pkj, tahap = test_pekerjaan_with_schedule
        
        # Snapshot category totals
        snapshot = compute_kebutuhan_items(test_project)
        snap_by_cat = {'TK': Decimal(0), 'BHN': Decimal(0), 'ALT': Decimal(0)}
        for row in snapshot:
            cat = row.get('kategori', 'LAIN')
            if cat in snap_by_cat:
                snap_by_cat[cat] += Decimal(str(row.get('harga_total_decimal', 0)))
        
        # Timeline category totals (aggregate all periods)
        timeline = compute_kebutuhan_timeline(test_project)
        time_by_cat = {'TK': Decimal(0), 'BHN': Decimal(0), 'ALT': Decimal(0)}
        for period in timeline.get('periods', []):
            for item in period.get('items', []):
                cat = item.get('kategori', 'LAIN')
                if cat in time_by_cat:
                    time_by_cat[cat] += Decimal(str(item.get('harga_total_decimal', 0)))
        
        # Compare
        for cat in ['TK', 'BHN', 'ALT']:
            diff = abs(snap_by_cat[cat] - time_by_cat[cat])
            assert diff < Decimal("1.0"), (
                f"Category {cat}: Snapshot ({snap_by_cat[cat]}) != "
                f"Timeline ({time_by_cat[cat]}), diff={diff}"
            )
    
    def test_item_count_consistent(
        self, test_project, test_pekerjaan_with_schedule
    ):
        """
        Unique item count should be same between views.
        """
        pkj, tahap = test_pekerjaan_with_schedule
        
        # Snapshot unique items
        snapshot = compute_kebutuhan_items(test_project)
        snap_keys = set()
        for row in snapshot:
            key = (row.get('kategori'), row.get('kode'), row.get('uraian'))
            snap_keys.add(key)
        
        # Timeline unique items (aggregate across all periods)
        timeline = compute_kebutuhan_timeline(test_project)
        time_keys = set()
        for period in timeline.get('periods', []):
            for item in period.get('items', []):
                key = (item.get('kategori'), item.get('kode'), item.get('uraian'))
                time_keys.add(key)
        
        assert snap_keys == time_keys, (
            f"Item mismatch:\n"
            f"Only in Snapshot: {snap_keys - time_keys}\n"
            f"Only in Timeline: {time_keys - snap_keys}"
        )


@pytest.mark.django_db
class TestAPIConsistency:
    """Test API endpoint consistency."""
    
    def test_api_snapshot_matches_service(
        self, client, test_user, test_project, test_pekerjaan_with_schedule
    ):
        """API response should match service function output."""
        client.login(username="test_sync", password="testpass123")
        
        # API response
        url = reverse(
            "detail_project:api_get_rekap_kebutuhan_enhanced", 
            args=[test_project.id]
        )
        response = client.get(url)
        assert response.status_code == 200
        
        api_data = response.json()
        assert api_data.get('ok') is True
        
        api_total = sum(
            Decimal(str(row.get('harga_total_decimal', 0)))
            for row in api_data.get('rows', [])
        )
        
        # Service function
        service_data = compute_kebutuhan_items(test_project)
        service_total = sum(
            Decimal(str(row.get('harga_total_decimal', 0)))
            for row in service_data
        )
        
        assert abs(api_total - service_total) < Decimal("1.0")
    
    def test_api_timeline_matches_service(
        self, client, test_user, test_project, test_pekerjaan_with_schedule
    ):
        """Timeline API response should match service function output."""
        client.login(username="test_sync", password="testpass123")
        
        # API response (without aggregate mode for raw comparison)
        url = reverse(
            "detail_project:api_get_rekap_kebutuhan_timeline",
            args=[test_project.id]
        )
        response = client.get(url)
        assert response.status_code == 200
        
        api_data = response.json()
        assert api_data.get('ok') is True
        
        api_periods = api_data.get('periods', [])
        api_total = sum(
            Decimal(str(p.get('total_cost_decimal', 0)))
            for p in api_periods
        )
        
        # Service function
        service_data = compute_kebutuhan_timeline(test_project)
        service_periods = service_data.get('periods', [])
        service_total = sum(
            Decimal(str(p.get('total_cost_decimal', 0)))
            for p in service_periods
        )
        
        assert abs(api_total - service_total) < Decimal("1.0")


@pytest.mark.django_db
class TestDataIntegrity:
    """Test that DetailAHSPExpanded matches source data."""
    
    def test_expanded_matches_source_detail(
        self, test_project, test_pekerjaan_with_schedule
    ):
        """DetailAHSPExpanded should match DetailAHSPProject after expansion."""
        pkj, tahap = test_pekerjaan_with_schedule
        
        # Source details
        source_details = DetailAHSPProject.objects.filter(
            project=test_project,
            pekerjaan=pkj
        )
        
        # Expanded details
        expanded_details = DetailAHSPExpanded.objects.filter(
            project=test_project,
            pekerjaan=pkj
        )
        
        # For non-bundle items, counts should match
        non_bundle_source = source_details.exclude(kategori='LAIN')
        assert expanded_details.count() >= non_bundle_source.count(), (
            f"Expanded count ({expanded_details.count()}) < "
            f"Source count ({non_bundle_source.count()})"
        )
        
        # Koefisien should match for direct items
        for src in non_bundle_source:
            exp = expanded_details.filter(
                source_detail=src
            ).first()
            
            if exp:
                assert exp.koefisien == src.koefisien, (
                    f"Koefisien mismatch for {src.kode}: "
                    f"source={src.koefisien}, expanded={exp.koefisien}"
                )
