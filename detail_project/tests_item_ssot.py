import json
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import RequestFactory, TestCase

from dashboard.models import Project
from detail_project.exports.harga_items_adapter import HargaItemsAdapter
from detail_project.models import (
    DetailAHSPExpanded,
    DetailAHSPProject,
    HargaItemProject,
    Klasifikasi,
    Pekerjaan,
    SubKlasifikasi,
)
from detail_project.services import (
    _upsert_harga_item,
    active_harga_items_queryset,
    compute_rekap_for_project,
    used_harga_items_queryset,
)
from detail_project.models import VolumePekerjaan
from detail_project.views_api import api_save_detail_ahsp_for_pekerjaan


class ItemSsotTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="item_ssot_owner",
            email="item-ssot@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Item SSOT",
            sumber_dana="APBN",
            lokasi_project="Makassar",
            nama_client="Client",
            anggaran_owner=1000,
        )
        klasifikasi = Klasifikasi.objects.create(
            project=self.project,
            name="K1",
            ordering_index=1,
        )
        self.sub = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=klasifikasi,
            name="S1",
            ordering_index=1,
        )
        self.pekerjaan = self._pekerjaan("CUST.001", 1)
        self.factory = RequestFactory()

    def _pekerjaan(self, kode, ordering_index):
        return Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode=kode,
            snapshot_uraian=kode,
            snapshot_satuan="m2",
            ordering_index=ordering_index,
        )

    def _item(self, kode, uraian="Uraian Lama", kategori="TK"):
        return HargaItemProject.objects.create(
            project=self.project,
            kode_item=kode,
            uraian=uraian,
            satuan="jam",
            kategori=kategori,
            harga_satuan=Decimal("100.00"),
        )

    def test_upsert_does_not_overwrite_different_semantic_item_by_source_code(self):
        item = self._item("TK.001")
        raw = DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            harga_item=item,
            kategori="TK",
            kode="TK.001",
            uraian="Uraian Lama",
            satuan="jam",
            koefisien=Decimal("1"),
        )
        expanded = DetailAHSPExpanded.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            source_detail=raw,
            harga_item=item,
            kategori="TK",
            kode="TK.001",
            uraian="Uraian Lama",
            satuan="jam",
            koefisien=Decimal("1"),
        )

        canonical = _upsert_harga_item(
            self.project,
            "TK",
            "TK.001",
            "Uraian Canonical",
            "OH",
        )

        raw.refresh_from_db()
        expanded.refresh_from_db()
        self.assertEqual(canonical.uraian, "Uraian Canonical")
        self.assertNotEqual(canonical.id, item.id)
        self.assertEqual(raw.uraian, "Uraian Lama")
        self.assertEqual(expanded.uraian, "Uraian Lama")

    def test_repair_command_is_dry_run_by_default(self):
        item = self._item("TK.REPAIR", uraian="Canonical")
        raw = DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            harga_item=item,
            kategori="TK",
            kode=item.kode_item,
            uraian="Stale",
            satuan=item.satuan,
            koefisien=Decimal("1"),
        )

        call_command(
            "repair_item_ssot",
            project_id=self.project.id,
            stdout=StringIO(),
        )
        raw.refresh_from_db()
        self.assertEqual(raw.uraian, "Stale")

        call_command(
            "repair_item_ssot",
            project_id=self.project.id,
            apply=True,
            stdout=StringIO(),
        )
        raw.refresh_from_db()
        self.assertEqual(raw.uraian, "Canonical")

    def test_active_item_contract_includes_raw_fallback_items(self):
        standalone = self._item("B.001", kategori="BHN")
        expanded_item = self._item("TK.002")
        raw_only_item = self._item("TK.003")

        expanded_raw = DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            harga_item=expanded_item,
            kategori="TK",
            kode=expanded_item.kode_item,
            uraian=expanded_item.uraian,
            satuan=expanded_item.satuan,
            koefisien=Decimal("1"),
        )
        DetailAHSPExpanded.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            source_detail=expanded_raw,
            harga_item=expanded_item,
            kategori="TK",
            kode=expanded_item.kode_item,
            uraian=expanded_item.uraian,
            satuan=expanded_item.satuan,
            koefisien=Decimal("1"),
        )
        raw_only_job = self._pekerjaan("CUST.RAW.ITEM", 2)
        DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=raw_only_job,
            harga_item=raw_only_item,
            kategori="TK",
            kode=raw_only_item.kode_item,
            uraian=raw_only_item.uraian,
            satuan=raw_only_item.satuan,
            koefisien=Decimal("1"),
        )

        active_ids = set(
            active_harga_items_queryset(self.project).values_list("id", flat=True)
        )
        self.assertEqual(
            active_ids,
            {standalone.id, expanded_item.id, raw_only_item.id},
        )

        used_ids = set(
            used_harga_items_queryset(self.project).values_list("id", flat=True)
        )
        self.assertEqual(used_ids, {expanded_item.id, raw_only_item.id})

        export_data = HargaItemsAdapter(self.project).get_export_data()
        exported_codes = {
            row[1]
            for row, row_type in zip(
                export_data["table_data"]["rows"],
                export_data["row_types"],
            )
            if row_type == "item"
        }
        self.assertEqual(exported_codes, {"TK.002", "TK.003"})

    def test_rekap_falls_back_per_job_when_project_has_mixed_storage(self):
        expanded_item = self._item("TK.EXPANDED")
        expanded_raw = DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            harga_item=expanded_item,
            kategori="TK",
            kode=expanded_item.kode_item,
            uraian=expanded_item.uraian,
            satuan=expanded_item.satuan,
            koefisien=Decimal("2"),
        )
        DetailAHSPExpanded.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            source_detail=expanded_raw,
            harga_item=expanded_item,
            kategori="TK",
            kode=expanded_item.kode_item,
            uraian=expanded_item.uraian,
            satuan=expanded_item.satuan,
            koefisien=Decimal("2"),
        )
        VolumePekerjaan.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            quantity=Decimal("1"),
        )

        raw_only_job = self._pekerjaan("CUST.RAW", 2)
        raw_only_item = self._item("TK.RAW")
        DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=raw_only_job,
            harga_item=raw_only_item,
            kategori="TK",
            kode=raw_only_item.kode_item,
            uraian=raw_only_item.uraian,
            satuan=raw_only_item.satuan,
            koefisien=Decimal("3"),
        )
        VolumePekerjaan.objects.create(
            project=self.project,
            pekerjaan=raw_only_job,
            quantity=Decimal("1"),
        )

        rows = {
            row["pekerjaan_id"]: row
            for row in compute_rekap_for_project(self.project)
        }

        self.assertEqual(rows[self.pekerjaan.id]["A"], 200.0)
        self.assertEqual(rows[raw_only_job.id]["A"], 300.0)

    def test_bundle_expansion_failure_rolls_back_replace_all_save(self):
        old_item = self._item("TK.OLD")
        old_raw = DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            harga_item=old_item,
            kategori="TK",
            kode=old_item.kode_item,
            uraian=old_item.uraian,
            satuan=old_item.satuan,
            koefisien=Decimal("1"),
        )
        DetailAHSPExpanded.objects.create(
            project=self.project,
            pekerjaan=self.pekerjaan,
            source_detail=old_raw,
            harga_item=old_item,
            kategori="TK",
            kode=old_item.kode_item,
            uraian=old_item.uraian,
            satuan=old_item.satuan,
            koefisien=Decimal("1"),
        )

        target = self._pekerjaan("CUST.TARGET", 2)
        target_item = self._item("TK.TARGET")
        target_raw = DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=target,
            harga_item=target_item,
            kategori="TK",
            kode=target_item.kode_item,
            uraian=target_item.uraian,
            satuan=target_item.satuan,
            koefisien=Decimal("1"),
        )
        DetailAHSPExpanded.objects.create(
            project=self.project,
            pekerjaan=target,
            source_detail=target_raw,
            harga_item=target_item,
            kategori="TK",
            kode=target_item.kode_item,
            uraian=target_item.uraian,
            satuan=target_item.satuan,
            koefisien=Decimal("1"),
        )

        request = self.factory.post(
            "/api/mock/",
            data=json.dumps({
                "rows": [{
                    "kategori": "LAIN",
                    "kode": "BUNDLE.FAIL",
                    "uraian": "Bundle gagal",
                    "satuan": "ls",
                    "koefisien": "1",
                    "ref_kind": "job",
                    "ref_id": target.id,
                }]
            }),
            content_type="application/json",
        )
        request.user = self.owner

        with patch(
            "detail_project.views_api.expand_bundle_to_components",
            side_effect=ValueError("forced expansion failure"),
        ):
            response = api_save_detail_ahsp_for_pekerjaan(
                request,
                self.project.id,
                self.pekerjaan.id,
            )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(
            DetailAHSPProject.objects.filter(pk=old_raw.pk, kode="TK.OLD").exists()
        )
        self.assertTrue(
            DetailAHSPExpanded.objects.filter(source_detail_id=old_raw.pk).exists()
        )
        self.assertFalse(
            HargaItemProject.objects.filter(
                project=self.project,
                kode_item="BUNDLE.FAIL",
            ).exists()
        )
