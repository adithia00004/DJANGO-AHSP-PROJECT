import pytest
from decimal import Decimal
from django.db import models

from detail_project.models import (
    Pekerjaan,
    DetailAHSPProject,
    HargaItemProject,
    DetailAHSPExpanded,
    VolumePekerjaan,
)
from detail_project.services import (
    expand_bundle_to_components,
    _populate_expanded_from_raw,
    compute_rekap_for_project,
    compute_kebutuhan_items,
)


def _create_job(project, sub_klas, kode, uraian):
    next_order = (
        Pekerjaan.objects.filter(project=project).aggregate(models.Max("ordering_index"))["ordering_index__max"] or 0
    ) + 1
    return Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub_klas,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode=kode,
        snapshot_uraian=uraian,
        snapshot_satuan="LS",
        ordering_index=next_order,
    )


def _create_harga(project, kategori, kode, uraian, satuan, harga):
    return HargaItemProject.objects.create(
        project=project,
        kategori=kategori,
        kode_item=kode,
        uraian=uraian,
        satuan=satuan,
        harga_satuan=Decimal(harga),
    )


@pytest.mark.django_db
class TestBundleQuantitySemantic:
    def _setup_bundle(self, project, sub_klas, *, component_koef="0.750000", bundle_koef="4.000000", component_price="100000", volume="2.000"):
        base = _create_job(project, sub_klas, "BND-COMP", "Component Job")
        harga = _create_harga(project, "TK", "TK.COMP", "Comp", "OH", component_price)
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=base,
            harga_item=harga,
            kategori="TK",
            kode="TK.COMP",
            uraian="Comp",
            satuan="OH",
            koefisien=Decimal(component_koef),
        )

        bundle = _create_job(project, sub_klas, "BND-AGG", "Bundle Agg")
        placeholder = _create_harga(project, "LAIN", "LAIN.AGG", "Bundle Agg", "set", "0")
        detail_bundle = DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=bundle,
            harga_item=placeholder,
            kategori="LAIN",
            kode="LAIN.AGG",
            uraian="Bundle Agg",
            satuan="set",
            koefisien=Decimal(bundle_koef),
            ref_pekerjaan=base,
        )

        _populate_expanded_from_raw(project, bundle)
        VolumePekerjaan.objects.create(
            project=project,
            pekerjaan=bundle,
            quantity=Decimal(volume),
        )

        return bundle, harga, detail_bundle

    def test_expand_bundle_returns_original_component_koef(self, project, sub_klas):
        base_job = _create_job(project, sub_klas, "BND-BASE", "Base Job")
        tk = _create_harga(project, "TK", "TK.001", "Pekerja", "OH", "100000")
        bhn = _create_harga(project, "BHN", "BHN.001", "Semen", "Zak", "50000")

        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=base_job,
            harga_item=tk,
            kategori="TK",
            kode="TK.001",
            uraian="Pekerja",
            satuan="OH",
            koefisien=Decimal("1.500000"),
        )
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=base_job,
            harga_item=bhn,
            kategori="BHN",
            kode="BHN.001",
            uraian="Semen",
            satuan="Zak",
            koefisien=Decimal("2.000000"),
        )

        parent = _create_job(project, sub_klas, "BND-PARENT", "Parent Bundle")
        placeholder = _create_harga(project, "LAIN", "LAIN.BND", "Bundle", "set", "0")
        detail_bundle = DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=parent,
            harga_item=placeholder,
            kategori="LAIN",
            kode="LAIN.BND",
            uraian="Bundle Ref",
            satuan="set",
            koefisien=Decimal("5.000000"),
            ref_pekerjaan=base_job,
        )

        detail_data = {
            "kategori": detail_bundle.kategori,
            "kode": detail_bundle.kode,
            "koefisien": detail_bundle.koefisien,
            "ref_pekerjaan_id": base_job.id,
        }

        comps = expand_bundle_to_components(detail_data, project)
        assert sorted((c["kategori"], c["koefisien"]) for c in comps) == [
            ("BHN", Decimal("2.000000")),
            ("TK", Decimal("1.500000")),
        ]
        assert all(c["bundle_multiplier"] == detail_bundle.koefisien for c in comps)

    def test_populate_expanded_stores_original_koef(self, project, sub_klas):
        leaf = _create_job(project, sub_klas, "BND-LEAF", "Leaf Job")
        harga = _create_harga(project, "TK", "TK.002", "Mandor", "OH", "120000")
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=leaf,
            harga_item=harga,
            kategori="TK",
            kode="TK.002",
            uraian="Mandor",
            satuan="OH",
            koefisien=Decimal("0.500000"),
        )

        nested = _create_job(project, sub_klas, "BND-NEST", "Nested Job")
        placeholder_nested = _create_harga(project, "LAIN", "LAIN.NEST", "Nested", "set", "0")
        DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=nested,
            harga_item=placeholder_nested,
            kategori="LAIN",
            kode="LAIN.NEST",
            uraian="Nested Ref",
            satuan="set",
            koefisien=Decimal("2.000000"),
            ref_pekerjaan=leaf,
        )

        parent = _create_job(project, sub_klas, "BND-PARENT2", "Parent Job 2")
        placeholder_parent = _create_harga(project, "LAIN", "LAIN.PARENT", "Parent", "set", "0")
        detail_parent = DetailAHSPProject.objects.create(
            project=project,
            pekerjaan=parent,
            harga_item=placeholder_parent,
            kategori="LAIN",
            kode="LAIN.PARENT",
            uraian="Parent Ref",
            satuan="set",
            koefisien=Decimal("3.000000"),
            ref_pekerjaan=nested,
        )

        _populate_expanded_from_raw(project, parent)

        expanded = list(
            DetailAHSPExpanded.objects.filter(
                project=project,
                pekerjaan=parent,
                source_detail=detail_parent,
            ).values_list("kategori", "koefisien")
        )
        # Each parent unit should capture nested structure per unit (leaf koef 0.5 * nested koef 2)
        assert expanded == [("TK", Decimal("1.000000"))]

    def test_rekap_uses_bundle_multiplier(self, project, sub_klas):
        bundle, harga, _ = self._setup_bundle(project, sub_klas, component_koef="0.750000", bundle_koef="4.000000", component_price="100000", volume="1.0")

        rows = compute_rekap_for_project(project)
        row = next((r for r in rows if r.get("kode") == bundle.snapshot_kode), None)
        assert row, "Bundle row not found in rekap"

        expected_a = float(Decimal("0.75") * Decimal("100000") * Decimal("4"))
        assert pytest.approx(row.get("A", 0.0), rel=1e-6) == expected_a

    def test_kebutuhan_quantities_multiply_bundle_multiplier(self, project, sub_klas):
        self._setup_bundle(project, sub_klas, component_koef="0.750000", bundle_koef="4.000000", component_price="100000", volume="2.0")

        rows = compute_kebutuhan_items(project)
        tk_row = next((r for r in rows if r["kode"] == "TK.COMP"), None)
        assert tk_row, "TK component not found in kebutuhan rows"

        expected_qty = Decimal("0.75") * Decimal("4") * Decimal("2.0")
        assert Decimal(str(tk_row["quantity_decimal"])) == expected_qty
