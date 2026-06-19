"""budgeted_cost (BAC) must be reset together with the other derived data.

When a pekerjaan's source/ref changes (N2) or its slot is reused by a brand-new
row (N1), the old Budget-At-Completion baseline is no longer valid for the new
work. `_reset_pekerjaan_related_data` now zeroes `budgeted_cost`, so:

  * reuse (N1) -> the new row never inherits the old BAC;
  * source change (N2) -> the changed pekerjaan loses its stale BAC, and the
    destructive-impact preview surfaces it (no silent wipe);
  * Kurva S falls back to the live rekap total once BAC == 0.
"""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dashboard.models import Project
from detail_project.models import Pekerjaan
from detail_project.views_api import (
    api_upsert_list_pekerjaan,
    api_list_pekerjaan_destructive_impact,
)
from referensi.models import AHSPReferensi, RincianReferensi


class ListPekerjaanBudgetedCostResetTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_bac_reset",
            email="owner-bac-reset@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project BAC",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client A",
            anggaran_owner=1000,
        )
        self.factory = RequestFactory()
        self.upsert_url = reverse(
            "detail_project:api_upsert_list_pekerjaan",
            kwargs={"project_id": self.project.id},
        )
        self.impact_url = reverse(
            "detail_project:api_list_pekerjaan_destructive_impact",
            kwargs={"project_id": self.project.id},
        )

    def _call(self, view, url, payload):
        request = self.factory.post(
            url, data=json.dumps(payload), content_type="application/json"
        )
        request.user = self.owner
        return view(request, self.project.id)

    def _seed_custom(self, uraian, order=1, budgeted_cost="0.00"):
        resp = self._call(api_upsert_list_pekerjaan, self.upsert_url, {
            "klasifikasi": [{
                "name": "Klas 1", "ordering_index": 1,
                "sub": [{
                    "name": "Sub 1", "ordering_index": 1,
                    "pekerjaan": [{
                        "source_type": "custom", "ordering_index": order,
                        "snapshot_uraian": uraian, "snapshot_satuan": "m2",
                    }],
                }],
            }]
        })
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))
        job = Pekerjaan.objects.get(project=self.project, snapshot_uraian=uraian)
        if Decimal(budgeted_cost) != 0:
            Pekerjaan.objects.filter(id=job.id).update(budgeted_cost=Decimal(budgeted_cost))
            job.refresh_from_db()
        return job

    def test_reused_slot_does_not_inherit_budgeted_cost(self):
        """N1: delete-one + add-one (custom) must not carry over BAC."""
        job = self._seed_custom("Lama", budgeted_cost="500000.00")
        sub = job.sub_klasifikasi
        klas = sub.klasifikasi
        resp = self._call(api_upsert_list_pekerjaan, self.upsert_url, {
            "klasifikasi": [{
                "id": klas.id, "name": "Klas 1", "ordering_index": 1,
                "sub": [{
                    "id": sub.id, "name": "Sub 1", "ordering_index": 1,
                    "pekerjaan": [{
                        "source_type": "custom", "ordering_index": 1,
                        "snapshot_uraian": "Baru", "snapshot_satuan": "m2",
                    }],
                }],
            }]
        })
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))
        survivors = list(Pekerjaan.objects.filter(project=self.project))
        self.assertEqual(len(survivors), 1)
        self.assertEqual(survivors[0].snapshot_uraian, "Baru")
        self.assertEqual(survivors[0].budgeted_cost, Decimal("0.00"))

    def test_source_change_save_clears_budgeted_cost(self):
        """N2: changing custom -> ref zeroes the stale BAC."""
        ahsp = AHSPReferensi.objects.create(
            kode_ahsp="A.1", nama_ahsp="Master A.1", sumber="AHSP 2025", satuan="m2",
        )
        RincianReferensi.objects.create(
            ahsp=ahsp, kategori="TK", kode_item="L.01", uraian_item="Pekerja",
            satuan_item="OH", koefisien=Decimal("5"),
        )
        job = self._seed_custom("Lama", budgeted_cost="750000.00")
        sub = job.sub_klasifikasi
        klas = sub.klasifikasi
        resp = self._call(api_upsert_list_pekerjaan, self.upsert_url, {
            "klasifikasi": [{
                "id": klas.id, "name": "Klas 1", "ordering_index": 1,
                "sub": [{
                    "id": sub.id, "name": "Sub 1", "ordering_index": 1,
                    "pekerjaan": [{
                        "id": job.id, "source_type": "ref", "ref_id": ahsp.id,
                        "ahsp_sumber": "AHSP 2025", "ordering_index": 1,
                    }],
                }],
            }]
        })
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))
        job.refresh_from_db()
        self.assertEqual(job.source_type, Pekerjaan.SOURCE_REF)
        self.assertEqual(job.budgeted_cost, Decimal("0.00"))
        # BAC == 0 => Kurva S takes the `else fallback_total` branch (live rekap),
        # so the chart still renders from the recomputed RAB instead of a stale BAC.

    def test_preview_surfaces_budgeted_cost_even_without_other_derived_data(self):
        """N2 preview: a source change that only loses BAC is still flagged."""
        job = self._seed_custom("Lama", budgeted_cost="900000.00")
        pekerjaan = {
            "id": job.id, "source_type": "ref", "ref_id": 999, "ordering_index": 1,
        }
        payload = {
            "klasifikasi": [{
                "id": job.sub_klasifikasi.klasifikasi_id, "name": "Klas 1", "ordering_index": 1,
                "sub": [{
                    "id": job.sub_klasifikasi_id, "name": "Sub 1", "ordering_index": 1,
                    "pekerjaan": [pekerjaan],
                }],
            }]
        }
        resp = self._call(api_list_pekerjaan_destructive_impact, self.impact_url, payload)
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))
        body = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(body["has_reset"], body)
        self.assertEqual(body["reset_totals"]["budgeted_cost"], 900000.0)
        self.assertEqual(body["to_reset"][0]["budgeted_cost"], 900000.0)
