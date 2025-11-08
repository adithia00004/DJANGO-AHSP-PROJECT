# detail_project/tests/test_list_pekerjaan_source_change.py
"""
Tests for List Pekerjaan source change behavior and cascade reset.

Scenario:
1. User has CUSTOM pekerjaan with uraian "Pekerjaan Balok latei"
2. User changes source from CUSTOM → REF or REF_MOD
3. When user SAVEs, system should:
   - Reset uraian/satuan to values from new reference
   - Trigger cascade reset (volume, jadwal, template AHSP, etc.)
"""
import pytest
import json
from decimal import Decimal
from django.urls import reverse
from django.contrib.auth import get_user_model

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan,
    DetailAHSPProject, HargaItemProject, VolumePekerjaan,
    PekerjaanTahapan, VolumeFormulaState, TahapPelaksanaan
)

User = get_user_model()


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def setup_source_change_test(db, user, project, sub_klas):
    """
    Setup untuk test source change behavior.
    Creates:
    - AHSP Referensi untuk testing
    - CUSTOM pekerjaan dengan data lengkap (volume, jadwal, detail AHSP)
    """
    from referensi.models import AHSPReferensi, RincianReferensi

    # Create AHSP Referensi
    ahsp_ref = AHSPReferensi.objects.create(
        kode_ahsp="TEST.001",
        nama_ahsp="Test AHSP - Pekerjaan Balok",
        satuan="m3",
    )

    # Create Rincian for AHSP (component items)
    rincian_tk = RincianReferensi.objects.create(
        ahsp=ahsp_ref,
        kategori="TK",
        kode_item="TK.REF",
        uraian_item="Pekerja Referensi",
        satuan_item="OH",
        koefisien=Decimal("1.500000"),
    )

    rincian_bhn = RincianReferensi.objects.create(
        ahsp=ahsp_ref,
        kategori="BHN",
        kode_item="BHN.REF",
        uraian_item="Semen Referensi",
        satuan_item="Zak",
        koefisien=Decimal("5.000000"),
    )

    # Create CUSTOM pekerjaan with full data
    pekerjaan_custom = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="CUST-001",
        snapshot_uraian="Pekerjaan Balok latei",  # User's custom uraian
        snapshot_satuan="unit",
        ordering_index=1,
        detail_ready=True,
    )

    # Create HargaItemProject for custom details
    harga_tk_custom = HargaItemProject.objects.create(
        project=project,
        kategori="TK",
        kode_item="TK.CUSTOM",
        uraian="Pekerja Custom",
        satuan="OH",
        harga_satuan=Decimal("120000"),
    )

    harga_bhn_custom = HargaItemProject.objects.create(
        project=project,
        kategori="BHN",
        kode_item="BHN.CUSTOM",
        uraian="Material Custom",
        satuan="kg",
        harga_satuan=Decimal("50000"),
    )

    # Add custom detail AHSP
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan_custom,
        harga_item=harga_tk_custom,
        kategori="TK",
        kode="TK.CUSTOM",
        uraian="Pekerja Custom",
        satuan="OH",
        koefisien=Decimal("2.000000"),
    )

    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan_custom,
        harga_item=harga_bhn_custom,
        kategori="BHN",
        kode="BHN.CUSTOM",
        uraian="Material Custom",
        satuan="kg",
        koefisien=Decimal("10.000000"),
    )

    # Add volume
    VolumePekerjaan.objects.create(
        project=project,
        pekerjaan=pekerjaan_custom,
        quantity=Decimal("50.000"),
    )

    # Add to tahapan (jadwal)
    tahapan = TahapPelaksanaan.objects.create(
        project=project,
        nama="Minggu 1",
        urutan=1,
    )

    PekerjaanTahapan.objects.create(
        tahapan=tahapan,
        pekerjaan=pekerjaan_custom,
        proporsi_volume=Decimal("100.00"),
    )

    # Add formula state
    VolumeFormulaState.objects.create(
        project=project,
        pekerjaan=pekerjaan_custom,
        formula_text="50",
        is_formula=False,
    )

    return {
        'ahsp_ref': ahsp_ref,
        'rincian_tk': rincian_tk,
        'rincian_bhn': rincian_bhn,
        'pekerjaan_custom': pekerjaan_custom,
        'tahapan': tahapan,
        'harga_tk_custom': harga_tk_custom,
        'harga_bhn_custom': harga_bhn_custom,
    }


# ============================================================================
# TESTS: Source Change from CUSTOM to REF
# ============================================================================

@pytest.mark.django_db
class TestSourceChangeCUSTOMtoREF:
    """Test behavior when user changes source from CUSTOM to REF."""

    def test_change_custom_to_ref_resets_fields(self, client_logged, project, sub_klas, setup_source_change_test):
        """
        Test that changing from CUSTOM to REF resets uraian/satuan to reference values.

        Expected behavior:
        1. User has CUSTOM pekerjaan with uraian="Pekerjaan Balok latei", satuan="unit"
        2. User changes to REF with ref_id pointing to AHSP with different uraian/satuan
        3. After save, uraian/satuan should match AHSP reference, NOT custom values
        """
        pekerjaan_custom = setup_source_change_test['pekerjaan_custom']
        ahsp_ref = setup_source_change_test['ahsp_ref']

        # Verify initial state (CUSTOM)
        assert pekerjaan_custom.source_type == Pekerjaan.SOURCE_CUSTOM
        assert pekerjaan_custom.snapshot_uraian == "Pekerjaan Balok latei"
        assert pekerjaan_custom.snapshot_satuan == "unit"
        assert pekerjaan_custom.detail_ready is True

        # Prepare payload: Change CUSTOM → REF
        payload = {
            "klasifikasi": [
                {
                    "name": "K1",
                    "ordering_index": 1,
                    "subs": [
                        {
                            "name": "S1",
                            "ordering_index": 1,
                            "jobs": [
                                {
                                    "id": pekerjaan_custom.id,
                                    "source_type": "ref",  # Changed from custom to ref
                                    "ref_id": ahsp_ref.id,
                                    "ordering_index": 1,
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        # Save via API
        url = reverse('detail_project:api_upsert_list_pekerjaan', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 200
        data = resp.json()
        assert data['ok'] is True

        # Refresh from database
        pekerjaan_custom.refresh_from_db()

        # Verify fields reset to reference values
        assert pekerjaan_custom.source_type == Pekerjaan.SOURCE_REF
        assert pekerjaan_custom.snapshot_kode == "TEST.001"  # From AHSP
        assert pekerjaan_custom.snapshot_uraian == "Test AHSP - Pekerjaan Balok"  # From AHSP, NOT "Pekerjaan Balok latei"
        assert pekerjaan_custom.snapshot_satuan == "m3"  # From AHSP, NOT "unit"
        assert pekerjaan_custom.ref_id == ahsp_ref.id

    def test_change_custom_to_ref_triggers_cascade_reset(self, client_logged, project, sub_klas, setup_source_change_test):
        """
        Test that changing from CUSTOM to REF triggers cascade reset.

        Expected cascade reset:
        - DetailAHSPProject: Old custom details deleted, new ref details loaded
        - VolumePekerjaan: Reset to NULL
        - PekerjaanTahapan: Deleted
        - VolumeFormulaState: Deleted
        - detail_ready: Reset to False initially, then True after auto-load
        """
        pekerjaan_custom = setup_source_change_test['pekerjaan_custom']
        ahsp_ref = setup_source_change_test['ahsp_ref']
        tahapan = setup_source_change_test['tahapan']

        # Verify initial state - has data
        assert DetailAHSPProject.objects.filter(project=project, pekerjaan=pekerjaan_custom).count() == 2  # TK + BHN custom
        assert VolumePekerjaan.objects.filter(project=project, pekerjaan=pekerjaan_custom).exists()
        assert PekerjaanTahapan.objects.filter(pekerjaan=pekerjaan_custom).exists()
        assert VolumeFormulaState.objects.filter(project=project, pekerjaan=pekerjaan_custom).exists()

        initial_volume = VolumePekerjaan.objects.get(project=project, pekerjaan=pekerjaan_custom)
        assert initial_volume.quantity == Decimal("50.000")

        # Change CUSTOM → REF
        payload = {
            "klasifikasi": [
                {
                    "name": "K1",
                    "ordering_index": 1,
                    "subs": [
                        {
                            "name": "S1",
                            "ordering_index": 1,
                            "jobs": [
                                {
                                    "id": pekerjaan_custom.id,
                                    "source_type": "ref",
                                    "ref_id": ahsp_ref.id,
                                    "ordering_index": 1,
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        url = reverse('detail_project:api_upsert_list_pekerjaan', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 200

        # Verify cascade reset occurred

        # 1. DetailAHSPProject: Old custom details deleted, new ref details loaded
        details = DetailAHSPProject.objects.filter(project=project, pekerjaan=pekerjaan_custom)
        # Should have new details from AHSP reference (TK.REF, BHN.REF)
        assert details.count() == 2  # Same count but DIFFERENT items
        detail_codes = set(details.values_list('kode', flat=True))
        assert 'TK.REF' in detail_codes  # From AHSP reference
        assert 'BHN.REF' in detail_codes  # From AHSP reference
        assert 'TK.CUSTOM' not in detail_codes  # Old custom detail deleted
        assert 'BHN.CUSTOM' not in detail_codes  # Old custom detail deleted

        # 2. VolumePekerjaan: Reset to NULL
        volume = VolumePekerjaan.objects.get(project=project, pekerjaan=pekerjaan_custom)
        assert volume.quantity is None  # Reset from 50.000 to NULL
        assert volume.formula is None

        # 3. PekerjaanTahapan: Deleted
        assert PekerjaanTahapan.objects.filter(pekerjaan=pekerjaan_custom).count() == 0

        # 4. VolumeFormulaState: Deleted
        assert VolumeFormulaState.objects.filter(project=project, pekerjaan=pekerjaan_custom).count() == 0

        # 5. Pekerjaan refreshed
        pekerjaan_custom.refresh_from_db()
        # detail_ready depends on auto_load_rincian behavior
        # Since REF has auto_load_rincian=True by default, details should be loaded

    def test_change_custom_to_ref_modified(self, client_logged, project, sub_klas, setup_source_change_test):
        """
        Test that changing from CUSTOM to REF_MODIFIED also works.

        REF_MODIFIED allows custom uraian override while keeping reference details.
        """
        pekerjaan_custom = setup_source_change_test['pekerjaan_custom']
        ahsp_ref = setup_source_change_test['ahsp_ref']

        # Change CUSTOM → REF_MODIFIED with custom uraian override
        payload = {
            "klasifikasi": [
                {
                    "name": "K1",
                    "ordering_index": 1,
                    "subs": [
                        {
                            "name": "S1",
                            "ordering_index": 1,
                            "jobs": [
                                {
                                    "id": pekerjaan_custom.id,
                                    "source_type": "ref_modified",
                                    "ref_id": ahsp_ref.id,
                                    "snapshot_uraian": "Custom Override Uraian",  # Override
                                    "snapshot_satuan": "meter",  # Override
                                    "ordering_index": 1,
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        url = reverse('detail_project:api_upsert_list_pekerjaan', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 200

        # Refresh
        pekerjaan_custom.refresh_from_db()

        # Verify fields
        assert pekerjaan_custom.source_type == Pekerjaan.SOURCE_REF_MOD
        assert pekerjaan_custom.snapshot_kode == "TEST.001"  # From AHSP
        assert pekerjaan_custom.snapshot_uraian == "Custom Override Uraian"  # Custom override
        assert pekerjaan_custom.snapshot_satuan == "meter"  # Custom override
        assert pekerjaan_custom.ref_id == ahsp_ref.id

        # Verify cascade reset still occurred
        volume = VolumePekerjaan.objects.get(project=project, pekerjaan=pekerjaan_custom)
        assert volume.quantity is None  # Reset
        assert PekerjaanTahapan.objects.filter(pekerjaan=pekerjaan_custom).count() == 0  # Reset


# ============================================================================
# TESTS: Source Change from REF to CUSTOM
# ============================================================================

@pytest.mark.django_db
class TestSourceChangeREFtoCUSTOM:
    """Test behavior when user changes source from REF to CUSTOM."""

    def test_change_ref_to_custom_resets_to_empty(self, client_logged, project, sub_klas, setup_source_change_test):
        """
        Test that changing from REF to CUSTOM resets uraian/satuan to empty/custom values.

        Expected behavior:
        1. User has REF pekerjaan with uraian from AHSP reference
        2. User changes to CUSTOM with new custom uraian
        3. After save, uraian/satuan should be custom values
        4. ref_id should be NULL
        """
        ahsp_ref = setup_source_change_test['ahsp_ref']

        # Create REF pekerjaan
        pekerjaan_ref = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klas,
            source_type=Pekerjaan.SOURCE_REF,
            ref=ahsp_ref,
            snapshot_kode="TEST.001",
            snapshot_uraian="Test AHSP - Pekerjaan Balok",
            snapshot_satuan="m3",
            ordering_index=2,
        )

        # Add some data
        harga_tk = HargaItemProject.objects.create(
            project=project,
            kategori="TK",
            kode_item="TK.001",
            uraian="Pekerja",
            satuan="OH",
            harga_satuan=Decimal("100000"),
        )

        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=pekerjaan_ref,
            harga_item=harga_tk,
            kategori="TK",
            kode="TK.001",
            uraian="Pekerja",
            satuan="OH",
            koefisien=Decimal("1.000000"),
        )

        VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=pekerjaan_ref,
            quantity=Decimal("25.000"),
        )

        # Verify initial state (REF)
        assert pekerjaan_ref.source_type == Pekerjaan.SOURCE_REF
        assert pekerjaan_ref.ref_id == ahsp_ref.id
        assert pekerjaan_ref.snapshot_uraian == "Test AHSP - Pekerjaan Balok"

        # Change REF → CUSTOM
        payload = {
            "klasifikasi": [
                {
                    "name": "K1",
                    "ordering_index": 1,
                    "subs": [
                        {
                            "name": "S1",
                            "ordering_index": 1,
                            "jobs": [
                                {
                                    "id": pekerjaan_ref.id,
                                    "source_type": "custom",
                                    "snapshot_uraian": "My Custom Pekerjaan",
                                    "snapshot_satuan": "piece",
                                    "ordering_index": 2,
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        url = reverse('detail_project:api_upsert_list_pekerjaan', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 200

        # Refresh
        pekerjaan_ref.refresh_from_db()

        # Verify fields changed to custom
        assert pekerjaan_ref.source_type == Pekerjaan.SOURCE_CUSTOM
        assert pekerjaan_ref.ref_id is None  # ref cleared
        assert pekerjaan_ref.snapshot_uraian == "My Custom Pekerjaan"
        assert pekerjaan_ref.snapshot_satuan == "piece"
        assert pekerjaan_ref.snapshot_kode.startswith("CUST-")  # Auto-generated custom code

        # Verify cascade reset occurred
        assert DetailAHSPProject.objects.filter(project=project, pekerjaan=pekerjaan_ref).count() == 0  # All deleted
        volume = VolumePekerjaan.objects.get(project=project, pekerjaan=pekerjaan_ref)
        assert volume.quantity is None  # Reset


# ============================================================================
# TESTS: Source Change with ref_id Change
# ============================================================================

@pytest.mark.django_db
class TestSourceChangeRefIDChange:
    """Test behavior when user changes ref_id within same source type."""

    def test_change_ref_id_resets_and_repopulates(self, client_logged, project, sub_klas, setup_source_change_test):
        """
        Test that changing ref_id while staying REF resets and re-populates.

        Expected behavior:
        1. User has REF pekerjaan pointing to AHSP #1
        2. User changes ref_id to AHSP #2
        3. After save, uraian/satuan from AHSP #2, cascade reset triggered
        """
        ahsp_ref_1 = setup_source_change_test['ahsp_ref']

        # Create second AHSP reference
        from referensi.models import AHSPReferensi
        ahsp_ref_2 = AHSPReferensi.objects.create(
            kode_ahsp="TEST.002",
            nama_ahsp="Different AHSP - Pekerjaan Kolom",
            satuan="unit",
        )

        # Create REF pekerjaan pointing to ahsp_ref_1
        pekerjaan_ref = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klas,
            source_type=Pekerjaan.SOURCE_REF,
            ref=ahsp_ref_1,
            snapshot_kode="TEST.001",
            snapshot_uraian="Test AHSP - Pekerjaan Balok",
            snapshot_satuan="m3",
            ordering_index=3,
        )

        # Add volume
        VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=pekerjaan_ref,
            quantity=Decimal("100.000"),
        )

        # Verify initial state
        assert pekerjaan_ref.ref_id == ahsp_ref_1.id
        assert pekerjaan_ref.snapshot_uraian == "Test AHSP - Pekerjaan Balok"
        assert pekerjaan_ref.snapshot_satuan == "m3"

        # Change ref_id from ahsp_ref_1 to ahsp_ref_2
        payload = {
            "klasifikasi": [
                {
                    "name": "K1",
                    "ordering_index": 1,
                    "subs": [
                        {
                            "name": "S1",
                            "ordering_index": 1,
                            "jobs": [
                                {
                                    "id": pekerjaan_ref.id,
                                    "source_type": "ref",
                                    "ref_id": ahsp_ref_2.id,  # Changed ref_id
                                    "ordering_index": 3,
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        url = reverse('detail_project:api_upsert_list_pekerjaan', kwargs={'project_id': project.id})
        resp = client_logged.post(url,
                                  data=json.dumps(payload),
                                  content_type='application/json')

        assert resp.status_code == 200

        # Refresh
        pekerjaan_ref.refresh_from_db()

        # Verify fields updated from ahsp_ref_2
        assert pekerjaan_ref.ref_id == ahsp_ref_2.id
        assert pekerjaan_ref.snapshot_kode == "TEST.002"  # From ahsp_ref_2
        assert pekerjaan_ref.snapshot_uraian == "Different AHSP - Pekerjaan Kolom"  # From ahsp_ref_2
        assert pekerjaan_ref.snapshot_satuan == "unit"  # From ahsp_ref_2, NOT "m3"

        # Verify cascade reset occurred
        volume = VolumePekerjaan.objects.get(project=project, pekerjaan=pekerjaan_ref)
        assert volume.quantity is None  # Reset from 100.000 to NULL


# ============================================================================
# TESTS: Integration - Full Workflow
# ============================================================================

@pytest.mark.django_db
class TestSourceChangeIntegration:
    """Integration tests for complete source change workflow."""

    def test_full_workflow_custom_to_ref_and_back(self, client_logged, project, sub_klas, setup_source_change_test):
        """
        Test complete workflow: CUSTOM → REF → CUSTOM

        Verify cascade reset happens at each transition.
        """
        pekerjaan = setup_source_change_test['pekerjaan_custom']
        ahsp_ref = setup_source_change_test['ahsp_ref']

        # Step 1: Initial state - CUSTOM with data
        assert pekerjaan.source_type == Pekerjaan.SOURCE_CUSTOM
        assert pekerjaan.snapshot_uraian == "Pekerjaan Balok latei"
        assert DetailAHSPProject.objects.filter(project=project, pekerjaan=pekerjaan).count() == 2
        assert VolumePekerjaan.objects.get(project=project, pekerjaan=pekerjaan).quantity == Decimal("50.000")

        # Step 2: Change to REF
        payload_ref = {
            "klasifikasi": [{
                "name": "K1",
                "ordering_index": 1,
                "subs": [{
                    "name": "S1",
                    "ordering_index": 1,
                    "jobs": [{
                        "id": pekerjaan.id,
                        "source_type": "ref",
                        "ref_id": ahsp_ref.id,
                        "ordering_index": 1,
                    }]
                }]
            }]
        }

        url = reverse('detail_project:api_upsert_list_pekerjaan', kwargs={'project_id': project.id})
        resp = client_logged.post(url, data=json.dumps(payload_ref), content_type='application/json')
        assert resp.status_code == 200

        pekerjaan.refresh_from_db()
        assert pekerjaan.source_type == Pekerjaan.SOURCE_REF
        assert pekerjaan.snapshot_uraian == "Test AHSP - Pekerjaan Balok"  # Changed
        assert VolumePekerjaan.objects.get(project=project, pekerjaan=pekerjaan).quantity is None  # Reset

        # Step 3: Change back to CUSTOM
        payload_custom = {
            "klasifikasi": [{
                "name": "K1",
                "ordering_index": 1,
                "subs": [{
                    "name": "S1",
                    "ordering_index": 1,
                    "jobs": [{
                        "id": pekerjaan.id,
                        "source_type": "custom",
                        "snapshot_uraian": "Back to Custom",
                        "snapshot_satuan": "new_unit",
                        "ordering_index": 1,
                    }]
                }]
            }]
        }

        resp = client_logged.post(url, data=json.dumps(payload_custom), content_type='application/json')
        assert resp.status_code == 200

        pekerjaan.refresh_from_db()
        assert pekerjaan.source_type == Pekerjaan.SOURCE_CUSTOM
        assert pekerjaan.snapshot_uraian == "Back to Custom"
        assert pekerjaan.ref_id is None
        assert DetailAHSPProject.objects.filter(project=project, pekerjaan=pekerjaan).count() == 0  # Reset
        assert VolumePekerjaan.objects.get(project=project, pekerjaan=pekerjaan).quantity is None  # Still reset

    def test_multiple_pekerjaan_source_change_isolated(self, client_logged, project, sub_klas, setup_source_change_test):
        """
        Test that changing source for one pekerjaan doesn't affect others.

        Cascade reset should be isolated to the modified pekerjaan only.
        """
        pekerjaan_1 = setup_source_change_test['pekerjaan_custom']
        ahsp_ref = setup_source_change_test['ahsp_ref']

        # Create second pekerjaan
        pekerjaan_2 = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub_klas,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-002",
            snapshot_uraian="Second Custom Pekerjaan",
            snapshot_satuan="unit",
            ordering_index=2,
        )

        VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=pekerjaan_2,
            quantity=Decimal("75.000"),
        )

        # Change ONLY pekerjaan_1 to REF
        payload = {
            "klasifikasi": [{
                "name": "K1",
                "ordering_index": 1,
                "subs": [{
                    "name": "S1",
                    "ordering_index": 1,
                    "jobs": [
                        {
                            "id": pekerjaan_1.id,
                            "source_type": "ref",
                            "ref_id": ahsp_ref.id,
                            "ordering_index": 1,
                        },
                        {
                            "id": pekerjaan_2.id,
                            "source_type": "custom",
                            "snapshot_uraian": "Second Custom Pekerjaan",
                            "snapshot_satuan": "unit",
                            "ordering_index": 2,
                        }
                    ]
                }]
            }]
        }

        url = reverse('detail_project:api_upsert_list_pekerjaan', kwargs={'project_id': project.id})
        resp = client_logged.post(url, data=json.dumps(payload), content_type='application/json')
        assert resp.status_code == 200

        # Verify pekerjaan_1 changed
        pekerjaan_1.refresh_from_db()
        assert pekerjaan_1.source_type == Pekerjaan.SOURCE_REF
        vol_1 = VolumePekerjaan.objects.get(project=project, pekerjaan=pekerjaan_1)
        assert vol_1.quantity is None  # Reset

        # Verify pekerjaan_2 NOT affected
        pekerjaan_2.refresh_from_db()
        assert pekerjaan_2.source_type == Pekerjaan.SOURCE_CUSTOM
        vol_2 = VolumePekerjaan.objects.get(project=project, pekerjaan=pekerjaan_2)
        assert vol_2.quantity == Decimal("75.000")  # NOT reset
