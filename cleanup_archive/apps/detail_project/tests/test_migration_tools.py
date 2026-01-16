import json
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from detail_project.models import DetailAHSPProject, HargaItemProject, DetailAHSPExpanded
from detail_project.services import (
    validate_project_data,
    fix_project_data,
)


@pytest.mark.django_db
def test_validate_project_data_detects_invalid_bundle(project, pekerjaan_custom):
    # Create LAIN item without reference
    harga = HargaItemProject.objects.create(
        project=project,
        kode_item="LAIN.001",
        kategori="LAIN",
        uraian="Bundle",
        satuan="SET",
    )
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan_custom,
        harga_item=harga,
        kategori="LAIN",
        kode="LAIN.EMPTY",
        uraian="Invalid bundle",
        satuan="SET",
        koefisien=Decimal("1.0"),
    )

    report = validate_project_data(project)
    assert report["invalid_bundles"]
    assert report["passed"] is False


@pytest.mark.django_db
def test_fix_project_data_reexpand(project, pekerjaan_custom):
    harga = HargaItemProject.objects.create(
        project=project,
        kode_item="TK.FIX",
        kategori="TK",
        uraian="Fix Item",
        satuan="OH",
        harga_satuan=Decimal("100"),
    )
    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan_custom,
        harga_item=harga,
        kategori="TK",
        kode="TK.FIX",
        uraian="Fix Item",
        satuan="OH",
        koefisien=Decimal("1.0"),
    )
    DetailAHSPExpanded.objects.filter(project=project, pekerjaan=pekerjaan_custom).delete()

    summary = fix_project_data(project, reexpand=True, cleanup_orphans=False, dry_run=False)
    assert summary["reexpanded"] > 0
    assert DetailAHSPExpanded.objects.filter(
        project=project, pekerjaan=pekerjaan_custom
    ).exists()


@pytest.mark.django_db
def test_validate_command_output(project, pekerjaan_custom):
    out = StringIO()
    call_command(
        "validate_ahsp_data",
        "--project-id",
        str(project.id),
        stdout=out,
    )
    assert "Validating project" in out.getvalue()


@pytest.mark.django_db
def test_fix_command_dry_run(project, pekerjaan_custom):
    out = StringIO()
    call_command(
        "fix_ahsp_data",
        "--project-id",
        str(project.id),
        "--dry-run",
        stdout=out,
    )
    assert "DRY-RUN" in out.getvalue()
