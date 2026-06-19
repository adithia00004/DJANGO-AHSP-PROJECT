"""Regression tests for N1 (List Pekerjaan upsert reuse-pool).

Bug N1: ``reuse_pool`` was keyed by the OLD ``ordering_index`` and never excluded
pekerjaan carried explicitly by id in the payload. A brand-new payload row (no id)
could "claim" an existing pekerjaan, either:

  * inheriting its derived data (Volume / Detail / Jadwal / formula) when the
    source_type was unchanged (custom -> custom data-bleed), or
  * colliding with a row that is ALSO updated via its id, collapsing two DOM rows
    into a single DB object (silent row loss).

These tests pin both behaviours.
"""
import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dashboard.models import Project
from detail_project.models import (
    DetailAHSPProject,
    HargaItemProject,
    Pekerjaan,
    PekerjaanProgressWeekly,
    VolumePekerjaan,
)
from detail_project.views_api import api_upsert_list_pekerjaan


class ListPekerjaanUpsertReuseN1Tests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_upsert_reuse_n1",
            email="owner-upsert-reuse-n1@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project Reuse N1",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client A",
            anggaran_owner=1000,
        )
        self.factory = RequestFactory()
        self.url = reverse(
            "detail_project:api_upsert_list_pekerjaan",
            kwargs={"project_id": self.project.id},
        )

    def _post_upsert(self, payload):
        request = self.factory.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.owner
        return api_upsert_list_pekerjaan(request, self.project.id)

    def _seed_single_custom(self, uraian, order=1):
        payload = {
            "klasifikasi": [
                {
                    "name": "Klas 1",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "name": "Sub 1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "source_type": "custom",
                                    "ordering_index": order,
                                    "snapshot_uraian": uraian,
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        resp = self._post_upsert(payload)
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))

    def _seed_custom_rows(self, *names):
        pekerjaan = []
        payload = {
            "klasifikasi": [
                {
                    "name": "Klas 1",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "name": "Sub 1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "source_type": "custom",
                                    "ordering_index": idx,
                                    "snapshot_uraian": name,
                                    "snapshot_satuan": "m2",
                                }
                                for idx, name in enumerate(names, start=1)
                            ],
                        }
                    ],
                }
            ]
        }
        resp = self._post_upsert(payload)
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))
        for name in names:
            pekerjaan.append(Pekerjaan.objects.get(project=self.project, snapshot_uraian=name))
        return pekerjaan

    def _bundle(self, pekerjaan, ref_pekerjaan, kode="BND"):
        item = HargaItemProject.objects.create(
            project=self.project,
            kode_item=kode,
            kategori="LAIN",
            uraian=f"Bundle {kode}",
            satuan="ls",
            harga_satuan=Decimal("100.00"),
        )
        return DetailAHSPProject.objects.create(
            project=self.project,
            pekerjaan=pekerjaan,
            harga_item=item,
            kategori="LAIN",
            kode=kode,
            uraian=f"Bundle {kode}",
            satuan="ls",
            koefisien=Decimal("1.00"),
            ref_pekerjaan=ref_pekerjaan,
        )

    def test_new_custom_row_does_not_inherit_deleted_row_volume(self):
        """Delete-one + add-one (custom->custom) must NOT carry over Volume."""
        self._seed_single_custom("Lama")
        job_lama = Pekerjaan.objects.get(project=self.project, snapshot_uraian="Lama")
        VolumePekerjaan.objects.create(
            project=self.project, pekerjaan=job_lama, quantity=Decimal("100.000")
        )
        # Canonical jadwal/progress (SSOT) — must NOT survive into the new row.
        PekerjaanProgressWeekly.objects.create(
            project=self.project,
            pekerjaan=job_lama,
            week_number=1,
            week_start_date=date(2026, 1, 1),
            week_end_date=date(2026, 1, 1) + timedelta(days=6),
            planned_proportion=Decimal("50.00"),
        )

        klas = job_lama.sub_klasifikasi.klasifikasi
        sub = job_lama.sub_klasifikasi
        # "Lama" is omitted (deleted); a brand-new custom row "Baru" takes its slot.
        payload = {
            "klasifikasi": [
                {
                    "id": klas.id,
                    "name": "Klas 1",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "id": sub.id,
                            "name": "Sub 1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "source_type": "custom",
                                    "ordering_index": 1,
                                    "snapshot_uraian": "Baru",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        resp = self._post_upsert(payload)
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))

        survivors = list(Pekerjaan.objects.filter(project=self.project))
        self.assertEqual(len(survivors), 1)
        self.assertEqual(survivors[0].snapshot_uraian, "Baru")
        # The deleted row's Volume must NOT bleed into the new row.
        self.assertEqual(
            VolumePekerjaan.objects.filter(project=self.project).count(),
            0,
            "Volume of the deleted pekerjaan bled into the new row (N1 data-bleed)",
        )
        # Nor the canonical weekly progress (jadwal SSOT).
        self.assertEqual(
            PekerjaanProgressWeekly.objects.filter(project=self.project).count(),
            0,
            "Weekly progress of the deleted pekerjaan bled into the new row (N1/jadwal)",
        )

    def test_kept_row_and_new_row_do_not_collapse(self):
        """Delete P1, keep P2, add new N whose order matches P2's old order.

        With the bug, N would reuse P2's object (P2's old ordering_index == 2),
        collapsing the two rows into one DB object.
        """
        payload_initial = {
            "klasifikasi": [
                {
                    "name": "Klas 1",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "name": "Sub 1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "source_type": "custom",
                                    "ordering_index": 1,
                                    "snapshot_uraian": "P1",
                                    "snapshot_satuan": "m2",
                                },
                                {
                                    "source_type": "custom",
                                    "ordering_index": 2,
                                    "snapshot_uraian": "P2",
                                    "snapshot_satuan": "m2",
                                },
                            ],
                        }
                    ],
                }
            ]
        }
        resp = self._post_upsert(payload_initial)
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))

        p2 = Pekerjaan.objects.get(project=self.project, snapshot_uraian="P2")
        sub = p2.sub_klasifikasi
        klas = sub.klasifikasi

        # Delete P1; keep P2 (now first, order 1); add brand-new "N" at order 2,
        # which equals P2's ORIGINAL ordering_index -> reuse collision in the bug.
        payload_move = {
            "klasifikasi": [
                {
                    "id": klas.id,
                    "name": "Klas 1",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "id": sub.id,
                            "name": "Sub 1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "id": p2.id,
                                    "source_type": "custom",
                                    "ordering_index": 1,
                                    "snapshot_uraian": "P2",
                                    "snapshot_satuan": "m2",
                                },
                                {
                                    "source_type": "custom",
                                    "ordering_index": 2,
                                    "snapshot_uraian": "N",
                                    "snapshot_satuan": "m2",
                                },
                            ],
                        }
                    ],
                }
            ]
        }
        resp = self._post_upsert(payload_move)
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))

        uraians = sorted(
            Pekerjaan.objects.filter(project=self.project).values_list(
                "snapshot_uraian", flat=True
            )
        )
        self.assertEqual(uraians, ["N", "P2"], "Kept row collapsed into new row (N1)")
        # P2 keeps its identity/content.
        p2.refresh_from_db()
        self.assertEqual(p2.snapshot_uraian, "P2")

    def test_reuse_cannot_bypass_bundle_target_delete_guard(self):
        """A bundle target omitted from payload must not be reused as a new row.

        Without this guard, deleting A while keeping B (where B bundles A) and
        adding a new row at A's old ordering slot would reuse A's database id.
        The C1 delete guard would be bypassed and B would silently point at the
        brand-new row.
        """
        a, b = self._seed_custom_rows("A", "B")
        self._bundle(b, a)
        sub = b.sub_klasifikasi
        klas = sub.klasifikasi

        payload = {
            "klasifikasi": [
                {
                    "id": klas.id,
                    "name": "Klas 1",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "id": sub.id,
                            "name": "Sub 1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    "source_type": "custom",
                                    "ordering_index": 1,
                                    "snapshot_uraian": "N",
                                    "snapshot_satuan": "m2",
                                },
                                {
                                    "id": b.id,
                                    "source_type": "custom",
                                    "ordering_index": 2,
                                    "snapshot_uraian": "B",
                                    "snapshot_satuan": "m2",
                                },
                            ],
                        }
                    ],
                }
            ]
        }
        resp = self._post_upsert(payload)
        self.assertEqual(resp.status_code, 400, resp.content.decode("utf-8"))
        body = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(any("Pekerjaan Gabungan" in e["message"] for e in body["errors"]), body)
        self.assertTrue(Pekerjaan.objects.filter(id=a.id, snapshot_uraian="A").exists())
        self.assertTrue(Pekerjaan.objects.filter(id=b.id, snapshot_uraian="B").exists())
        self.assertFalse(Pekerjaan.objects.filter(project=self.project, snapshot_uraian="N").exists())
