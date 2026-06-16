"""WP-B9 — bundle expansion limits (D-10).

Locks MAX_BUNDLE_LEVELS=4 (A->B->C->D valid, A->B->C->D->E rejected) and the
MAX_EXPANDED_COMPONENTS cap, on the pekerjaan-bundle expansion path.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from dashboard.models import Project

from .models import (
    DetailAHSPProject,
    HargaItemProject,
    Klasifikasi,
    Pekerjaan,
    SubKlasifikasi,
)
from . import services
from .services import expand_bundle_to_components


class BundleDepthLimitTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("b9-owner", password="x")
        self.project = Project.objects.create(owner=self.owner, nama="B9")
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1
        )
        self._order = 0

    def _pekerjaan(self, kode):
        self._order += 1
        return Pekerjaan.objects.create(
            project=self.project, sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM, snapshot_kode=kode,
            snapshot_uraian=f"P {kode}", snapshot_satuan="m2", ordering_index=self._order,
        )

    def _hip(self, kode, kategori="TK"):
        return HargaItemProject.objects.create(
            project=self.project, kode_item=kode, kategori=kategori,
            uraian=f"Item {kode}", satuan="OH", harga_satuan=Decimal("100"),
        )

    def _base(self, pekerjaan, kode):
        return DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=pekerjaan, harga_item=self._hip(kode),
            kategori="TK", kode=kode, uraian=f"Item {kode}", satuan="OH",
            koefisien=Decimal("1"),
        )

    def _bundle(self, pekerjaan, ref_pekerjaan, kode):
        return DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=pekerjaan,
            harga_item=self._hip(kode, kategori="LAIN"),
            kategori="LAIN", kode=kode, uraian=f"Bundle {kode}", satuan="ls",
            koefisien=Decimal("1"), ref_pekerjaan=ref_pekerjaan,
        )

    def _chain(self, n):
        """Build a chain P1 -> P2 -> ... -> Pn; the deepest holds a base component."""
        jobs = [self._pekerjaan(f"P{i+1}") for i in range(n)]
        self._base(jobs[-1], "L.01")  # deepest = base component
        for i in range(n - 1):
            self._bundle(jobs[i], jobs[i + 1], f"BND-{i+1}")
        return jobs

    def _expand_from(self, job_with_bundle, ref_job):
        return expand_bundle_to_components(
            detail_data={
                "kategori": "LAIN", "kode": "TOP", "koefisien": Decimal("1"),
                "ref_pekerjaan_id": ref_job.id,
            },
            project=self.project, base_koef=Decimal("1"), depth=1,
        )

    def test_four_levels_allowed(self):
        # B -> C -> D -> E (4 pekerjaan levels) expands without error.
        jobs = self._chain(5)  # P1..P5
        # Expanding P2's bundle (ref P3) covers P2->P3->P4->P5 = 4 levels.
        result = self._expand_from(jobs[1], jobs[2])
        self.assertTrue(result)
        self.assertEqual(result[0]["kategori"], "TK")

    def test_five_levels_rejected(self):
        # A -> B -> C -> D -> E (5 pekerjaan levels) must be rejected.
        jobs = self._chain(5)
        with self.assertRaises(ValueError) as ctx:
            self._expand_from(jobs[0], jobs[1])  # P1->P2->P3->P4->P5
        self.assertIn("kedalaman", str(ctx.exception).lower())

    def test_component_cap_enforced(self):
        # A bundle referencing a pekerjaan with more base components than the cap
        # must be rejected immediately.
        target = self._pekerjaan("BIG")
        for i in range(4):
            self._base(target, f"C-{i}")
        host = self._pekerjaan("HOST")
        with patch.object(services, "MAX_EXPANDED_COMPONENTS", 2):
            with self.assertRaises(ValueError) as ctx:
                self._expand_from(host, target)
        self.assertIn("batas", str(ctx.exception).lower())

    def test_max_bundle_levels_is_four(self):
        self.assertEqual(services.MAX_BUNDLE_LEVELS, 4)
        self.assertEqual(services.MAX_BUNDLE_DEPTH, 3)
