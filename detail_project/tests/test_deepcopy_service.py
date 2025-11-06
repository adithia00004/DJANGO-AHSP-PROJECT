"""
Tests for DeepCopyService - FASE 3.1

Test coverage:
1. Basic copy functionality
2. FK remapping correctness
3. Data integrity
4. Transaction rollback on error
5. Optional parameters (copy_jadwal)
6. Edge cases (empty project, no pricing, etc.)
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi,
    SubKlasifikasi,
    Pekerjaan,
    VolumePekerjaan,
    DetailAHSPProject,
    HargaItemProject,
    ProjectPricing,
    ProjectParameter,
    TahapPelaksanaan,
    PekerjaanTahapan,
)
from detail_project.services import DeepCopyService


User = get_user_model()


@pytest.fixture
def sample_project(user):
    """Create a sample project with minimal data for testing."""
    return Project.objects.create(
        owner=user,
        nama="Test Project Original",
        sumber_dana="APBN",
        lokasi_project="Jakarta",
        nama_client="Client Test",
        anggaran_owner=Decimal("1000000000"),
        tanggal_mulai=date(2025, 1, 1),
        durasi_hari=90,
        is_active=True,
    )


@pytest.fixture
def full_project(user):
    """Create a fully populated project with all related data."""
    # Create project
    project = Project.objects.create(
        owner=user,
        nama="Full Test Project",
        sumber_dana="APBN",
        lokasi_project="Bandung",
        nama_client="Client Full Test",
        anggaran_owner=Decimal("5000000000"),
        tanggal_mulai=date(2025, 2, 1),
        durasi_hari=120,
        is_active=True,
    )

    # Create pricing
    ProjectPricing.objects.create(
        project=project,
        ppn_percent=Decimal("11.00"),
        markup_percent=Decimal("12.50"),
        rounding_base=10000,
    )

    # Create parameters
    ProjectParameter.objects.create(
        project=project,
        name="panjang",
        value=Decimal("100.000"),
        label="Panjang (m)",
        unit="meter",
    )
    ProjectParameter.objects.create(
        project=project,
        name="lebar",
        value=Decimal("50.000"),
        label="Lebar (m)",
        unit="meter",
    )

    # Create klasifikasi
    klas = Klasifikasi.objects.create(
        project=project,
        name="Pekerjaan Tanah",
    )

    # Create subklasifikasi
    subklas = SubKlasifikasi.objects.create(
        project=project,
        klasifikasi=klas,
        name="Galian Tanah",
    )

    # Create pekerjaan
    pekerjaan = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=subklas,
        snapshot_kode="1.1.1",
        snapshot_uraian="Galian Tanah Biasa",
        snapshot_satuan="m3",
        source_type="custom",
        ordering_index=1,
    )

    # Create volume
    VolumePekerjaan.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        quantity=Decimal("10000.000"),
    )

    # Create harga item
    harga_item = HargaItemProject.objects.create(
        project=project,
        kode_item="TK-001",
        kategori="TK",
        uraian="Pekerja",
        satuan="OH",
        harga_satuan=Decimal("150000.00"),
    )

    # Create detail AHSP
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        harga_item=harga_item,
        kategori="TK",
        kode="TK-001",
        uraian="Pekerja",
        satuan="OH",
        koefisien=Decimal("0.5"),
    )

    # Create tahapan
    tahapan = TahapPelaksanaan.objects.create(
        project=project,
        nama="Tahap 1",
        urutan=1,
        tanggal_mulai=date(2025, 2, 1),
        tanggal_selesai=date(2025, 3, 1),
    )

    # Create pekerjaan tahapan
    PekerjaanTahapan.objects.create(
        pekerjaan=pekerjaan,
        tahapan=tahapan,
        proporsi_volume=Decimal("100.00"),
    )

    return project


@pytest.mark.django_db
class TestDeepCopyServiceInit:
    """Test DeepCopyService initialization."""

    def test_init_with_valid_project(self, sample_project):
        """Test initialization with valid project."""
        service = DeepCopyService(sample_project)

        assert service.source == sample_project
        assert 'project' in service.mappings
        assert 'parameter' in service.mappings
        assert service.stats['parameter_copied'] == 0

    def test_init_with_none(self):
        """Test initialization with None raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DeepCopyService(None)

        assert "Source project must be a saved instance" in str(exc_info.value)

    def test_init_with_unsaved_project(self, user):
        """Test initialization with unsaved project raises ValidationError."""
        unsaved_project = Project(
            owner=user,
            nama="Unsaved",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Test Client",
            anggaran_owner=Decimal("1000000"),
            tanggal_mulai=date(2025, 1, 1),
        )

        with pytest.raises(ValidationError) as exc_info:
            DeepCopyService(unsaved_project)

        assert "Source project must be a saved instance" in str(exc_info.value)


@pytest.mark.django_db
class TestDeepCopyBasic:
    """Test basic copy functionality."""

    def test_copy_minimal_project(self, sample_project, other_user):
        """Test copying project with minimal data."""
        service = DeepCopyService(sample_project)

        new_project = service.copy(
            new_owner=other_user,
            new_name="Test Project Copy",
        )

        # Verify new project created
        assert new_project.id != sample_project.id
        assert new_project.owner == other_user
        assert new_project.nama == "Test Project Copy"
        assert new_project.lokasi_project == sample_project.lokasi_project
        assert new_project.durasi_hari == sample_project.durasi_hari

    def test_copy_with_new_tanggal_mulai(self, sample_project, other_user):
        """Test copying with new start date."""
        new_date = date(2025, 6, 1)
        service = DeepCopyService(sample_project)

        new_project = service.copy(
            new_owner=other_user,
            new_name="Copy with New Date",
            new_tanggal_mulai=new_date,
        )

        assert new_project.tanggal_mulai == new_date
        assert new_project.tanggal_mulai != sample_project.tanggal_mulai

    def test_copy_same_owner(self, sample_project, user):
        """Test copying to same owner."""
        service = DeepCopyService(sample_project)

        new_project = service.copy(
            new_owner=user,
            new_name="Same Owner Copy",
        )

        assert new_project.owner == user
        assert new_project.owner == sample_project.owner
        assert new_project.id != sample_project.id


@pytest.mark.django_db
class TestDeepCopyProjectPricing:
    """Test ProjectPricing copy functionality."""

    def test_copy_project_with_pricing(self, full_project, other_user):
        """Test that pricing is copied correctly."""
        service = DeepCopyService(full_project)

        new_project = service.copy(
            new_owner=other_user,
            new_name="Copy with Pricing",
        )

        old_pricing = ProjectPricing.objects.get(project=full_project)
        new_pricing = ProjectPricing.objects.get(project=new_project)

        assert new_pricing.id != old_pricing.id
        assert new_pricing.ppn_percent == old_pricing.ppn_percent
        assert new_pricing.markup_percent == old_pricing.markup_percent
        assert new_pricing.rounding_base == old_pricing.rounding_base

    def test_copy_project_without_pricing(self, sample_project, other_user):
        """Test copying project without pricing (should not fail)."""
        service = DeepCopyService(sample_project)

        new_project = service.copy(
            new_owner=other_user,
            new_name="Copy without Pricing",
        )

        # Verify no pricing exists
        assert not ProjectPricing.objects.filter(project=new_project).exists()


@pytest.mark.django_db
class TestDeepCopyParameters:
    """Test ProjectParameter copy functionality."""

    def test_copy_parameters(self, full_project, other_user):
        """Test that parameters are copied correctly."""
        service = DeepCopyService(full_project)

        new_project = service.copy(
            new_owner=other_user,
            new_name="Copy with Parameters",
        )

        old_params = ProjectParameter.objects.filter(project=full_project).order_by('name')
        new_params = ProjectParameter.objects.filter(project=new_project).order_by('name')

        assert old_params.count() == 2
        assert new_params.count() == 2
        assert service.stats['parameter_copied'] == 2

        # Verify each parameter
        for old_param, new_param in zip(old_params, new_params):
            assert new_param.id != old_param.id
            assert new_param.project == new_project
            assert new_param.name == old_param.name
            assert new_param.value == old_param.value
            assert new_param.label == old_param.label
            assert new_param.unit == old_param.unit

    def test_copy_project_without_parameters(self, sample_project, other_user):
        """Test copying project without parameters."""
        service = DeepCopyService(sample_project)

        new_project = service.copy(
            new_owner=other_user,
            new_name="Copy without Parameters",
        )

        assert service.stats['parameter_copied'] == 0
        assert not ProjectParameter.objects.filter(project=new_project).exists()


@pytest.mark.django_db
class TestDeepCopyHierarchy:
    """Test Klasifikasi > SubKlasifikasi > Pekerjaan hierarchy copy."""

    def test_copy_hierarchy(self, full_project, other_user):
        """Test that hierarchy is copied with correct FK remapping."""
        service = DeepCopyService(full_project)

        new_project = service.copy(
            new_owner=other_user,
            new_name="Copy with Hierarchy",
        )

        # Verify counts
        assert Klasifikasi.objects.filter(project=new_project).count() == 1
        assert SubKlasifikasi.objects.filter(project=new_project).count() == 1
        assert Pekerjaan.objects.filter(project=new_project).count() == 1

        # Verify FK relationships
        new_klas = Klasifikasi.objects.get(project=new_project)
        new_subklas = SubKlasifikasi.objects.get(project=new_project)
        new_pekerjaan = Pekerjaan.objects.get(project=new_project)

        assert new_subklas.klasifikasi == new_klas
        assert new_pekerjaan.sub_klasifikasi == new_subklas

        # Verify data integrity
        old_klas = Klasifikasi.objects.get(project=full_project)
        old_subklas = SubKlasifikasi.objects.get(project=full_project)
        old_pekerjaan = Pekerjaan.objects.get(project=full_project)

        assert new_klas.name == old_klas.name
        assert new_subklas.name == old_subklas.name
        assert new_pekerjaan.snapshot_kode == old_pekerjaan.snapshot_kode
        assert new_pekerjaan.snapshot_uraian == old_pekerjaan.snapshot_uraian


@pytest.mark.django_db
class TestDeepCopyVolume:
    """Test VolumePekerjaan copy functionality."""

    def test_copy_volume(self, full_project, other_user):
        """Test that volume data is copied correctly."""
        service = DeepCopyService(full_project)

        new_project = service.copy(
            new_owner=other_user,
            new_name="Copy with Volume",
        )

        old_volume = VolumePekerjaan.objects.get(project=full_project)
        new_volume = VolumePekerjaan.objects.get(project=new_project)

        # Verify volume copied
        assert new_volume.id != old_volume.id
        assert new_volume.quantity == old_volume.quantity

        # Verify FK remapped correctly
        assert new_volume.pekerjaan.project == new_project
        assert new_volume.pekerjaan.snapshot_kode == old_volume.pekerjaan.snapshot_kode


@pytest.mark.django_db
class TestDeepCopyHargaAndAHSP:
    """Test HargaItem and DetailAHSP copy functionality."""

    def test_copy_harga_and_detail(self, full_project, other_user):
        """Test that harga items and AHSP details are copied correctly."""
        service = DeepCopyService(full_project)

        new_project = service.copy(
            new_owner=other_user,
            new_name="Copy with Harga & AHSP",
        )

        # Verify harga item copied
        old_harga = HargaItemProject.objects.get(project=full_project)
        new_harga = HargaItemProject.objects.get(project=new_project)

        assert new_harga.id != old_harga.id
        assert new_harga.kode_item == old_harga.kode_item
        assert new_harga.kategori == old_harga.kategori
        assert new_harga.harga_satuan == old_harga.harga_satuan

        # Verify detail AHSP copied
        old_detail = DetailAHSPProject.objects.get(project=full_project)
        new_detail = DetailAHSPProject.objects.get(project=new_project)

        assert new_detail.id != old_detail.id
        assert new_detail.koefisien == old_detail.koefisien
        assert new_detail.kategori == old_detail.kategori

        # Verify FK remapping
        assert new_detail.pekerjaan.project == new_project
        assert new_detail.harga_item.project == new_project


@pytest.mark.django_db
class TestDeepCopyTahapan:
    """Test Tahapan and JadwalPekerjaan copy functionality."""

    def test_copy_with_jadwal_true(self, full_project, other_user):
        """Test copying with copy_jadwal=True (default)."""
        service = DeepCopyService(full_project)

        new_project = service.copy(
            new_owner=other_user,
            new_name="Copy with Jadwal",
            copy_jadwal=True,
        )

        # Verify tahapan copied
        old_tahapan = TahapPelaksanaan.objects.get(project=full_project)
        new_tahapan = TahapPelaksanaan.objects.get(project=new_project)

        assert new_tahapan.id != old_tahapan.id
        assert new_tahapan.nama == old_tahapan.nama
        assert new_tahapan.urutan == old_tahapan.urutan
        assert new_tahapan.tanggal_mulai == old_tahapan.tanggal_mulai

        # Verify jadwal pekerjaan copied
        old_jadwal = PekerjaanTahapan.objects.get(tahapan__project=full_project)
        new_jadwal = PekerjaanTahapan.objects.get(tahapan__project=new_project)

        assert new_jadwal.id != old_jadwal.id
        assert new_jadwal.proporsi_volume == old_jadwal.proporsi_volume

        # Verify FK remapping
        assert new_jadwal.pekerjaan.project == new_project
        assert new_jadwal.tahapan.project == new_project

        # Verify stats
        assert service.stats['tahapan_copied'] == 1
        assert service.stats['jadwal_copied'] == 1

    def test_copy_with_jadwal_false(self, full_project, other_user):
        """Test copying with copy_jadwal=False."""
        service = DeepCopyService(full_project)

        new_project = service.copy(
            new_owner=other_user,
            new_name="Copy without Jadwal",
            copy_jadwal=False,
        )

        # Verify tahapan NOT copied
        assert not TahapPelaksanaan.objects.filter(project=new_project).exists()
        assert not PekerjaanTahapan.objects.filter(tahapan__project=new_project).exists()

        # Verify stats
        assert service.stats['tahapan_copied'] == 0
        assert service.stats['jadwal_copied'] == 0


@pytest.mark.django_db
class TestDeepCopyStats:
    """Test copy statistics tracking."""

    def test_get_stats(self, full_project, other_user):
        """Test that get_stats returns correct counts."""
        service = DeepCopyService(full_project)

        new_project = service.copy(
            new_owner=other_user,
            new_name="Copy for Stats",
        )

        stats = service.get_stats()

        assert stats['parameter_copied'] == 2
        assert stats['klasifikasi_copied'] == 1
        assert stats['subklasifikasi_copied'] == 1
        assert stats['pekerjaan_copied'] == 1
        assert stats['volume_copied'] == 1
        assert stats['harga_item_copied'] == 1
        assert stats['ahsp_template_copied'] == 1
        assert stats['tahapan_copied'] == 1
        assert stats['jadwal_copied'] == 1

    def test_stats_are_copy(self, full_project, other_user):
        """Test that get_stats returns a copy, not reference."""
        service = DeepCopyService(full_project)

        stats1 = service.get_stats()
        stats1['parameter_copied'] = 999

        stats2 = service.get_stats()

        assert stats2['parameter_copied'] == 0  # Original unchanged


@pytest.mark.django_db
class TestDeepCopyComplexScenarios:
    """Test complex copy scenarios."""

    def test_copy_multiple_times(self, full_project, other_user):
        """Test copying same project multiple times."""
        service1 = DeepCopyService(full_project)
        copy1 = service1.copy(other_user, "Copy 1")

        service2 = DeepCopyService(full_project)
        copy2 = service2.copy(other_user, "Copy 2")

        service3 = DeepCopyService(full_project)
        copy3 = service3.copy(other_user, "Copy 3")

        # Verify all copies are independent
        assert copy1.id != copy2.id != copy3.id
        assert Project.objects.filter(owner=other_user).count() == 3

    def test_copy_of_copy(self, full_project, other_user, user):
        """Test creating a copy of a copy."""
        # First copy
        service1 = DeepCopyService(full_project)
        copy1 = service1.copy(other_user, "Copy 1")

        # Second copy (copy of copy)
        service2 = DeepCopyService(copy1)
        copy2 = service2.copy(user, "Copy of Copy")

        # Verify second copy has same data structure
        assert Pekerjaan.objects.filter(project=copy2).count() == 1
        assert ProjectParameter.objects.filter(project=copy2).count() == 2

        # Verify FKs are correct
        new_pekerjaan = Pekerjaan.objects.get(project=copy2)
        assert new_pekerjaan.sub_klasifikasi.project == copy2

    def test_copy_project_with_multiple_pekerjaan(self, user, other_user):
        """Test copying project with multiple pekerjaan."""
        # Create project with multiple pekerjaan
        project = Project.objects.create(
            owner=user,
            nama="Multi Pekerjaan Project",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client Multi",
            anggaran_owner=Decimal("2000000000"),
            tanggal_mulai=date(2025, 1, 1),
        )

        klas = Klasifikasi.objects.create(project=project, name="Klas 1")
        subklas = SubKlasifikasi.objects.create(project=project, klasifikasi=klas, name="SubKlas 1")

        for i in range(5):
            Pekerjaan.objects.create(
                project=project,
                sub_klasifikasi=subklas,
                snapshot_kode=f"1.1.{i+1}",
                snapshot_uraian=f"Pekerjaan {i+1}",
                snapshot_satuan="m3",
                source_type="custom",
                ordering_index=i+1,
            )

        # Copy project
        service = DeepCopyService(project)
        new_project = service.copy(other_user, "Multi Pekerjaan Copy")

        # Verify all pekerjaan copied
        assert Pekerjaan.objects.filter(project=new_project).count() == 5
        assert service.stats['pekerjaan_copied'] == 5

        # Verify ordering preserved
        new_pekerjaan_list = list(Pekerjaan.objects.filter(project=new_project).order_by('ordering_index'))
        for i, pkj in enumerate(new_pekerjaan_list):
            assert pkj.ordering_index == i + 1
            assert pkj.snapshot_kode == f"1.1.{i+1}"


@pytest.mark.django_db
class TestDeepCopyEdgeCases:
    """Test edge cases and error handling."""

    def test_copy_empty_project(self, sample_project, other_user):
        """Test copying project with no related data."""
        service = DeepCopyService(sample_project)

        new_project = service.copy(
            new_owner=other_user,
            new_name="Empty Copy",
        )

        # Verify project copied but no related data
        assert new_project.id != sample_project.id
        assert not ProjectParameter.objects.filter(project=new_project).exists()
        assert not Klasifikasi.objects.filter(project=new_project).exists()

    def test_copy_preserves_original(self, full_project, other_user):
        """Test that original project is unchanged after copy."""
        # Count original data
        original_counts = {
            'parameters': ProjectParameter.objects.filter(project=full_project).count(),
            'klasifikasi': Klasifikasi.objects.filter(project=full_project).count(),
            'pekerjaan': Pekerjaan.objects.filter(project=full_project).count(),
        }

        # Perform copy
        service = DeepCopyService(full_project)
        service.copy(other_user, "Preserve Original Test")

        # Verify original unchanged
        assert ProjectParameter.objects.filter(project=full_project).count() == original_counts['parameters']
        assert Klasifikasi.objects.filter(project=full_project).count() == original_counts['klasifikasi']
        assert Pekerjaan.objects.filter(project=full_project).count() == original_counts['pekerjaan']

    def test_id_mappings_correct(self, full_project, other_user):
        """Test that ID mappings dictionary is populated correctly."""
        service = DeepCopyService(full_project)
        new_project = service.copy(other_user, "ID Mapping Test")

        # Verify mappings exist
        assert len(service.mappings['project']) == 1
        assert len(service.mappings['parameter']) == 2
        assert len(service.mappings['klasifikasi']) == 1
        assert len(service.mappings['pekerjaan']) == 1

        # Verify mapping values are correct
        old_project_id = full_project.id
        new_project_id = service.mappings['project'][old_project_id]
        assert new_project_id == new_project.id
