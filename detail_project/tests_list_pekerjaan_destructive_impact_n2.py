"""N2 tests: destructive-impact preview must surface SOURCE-CHANGE resets.

Bug N2: changing a surviving pekerjaan's source_type/ref_id silently resets its
derived data (Volume/Detail/Jadwal/formula) at save time, but the destructive-impact
preview only counted DELETED pekerjaan. The preview now also returns a
`to_reset` / `has_reset` category for surviving rows whose source changes AND that
actually own derived data (proportional confirmation).
"""
import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dashboard.models import Project
from detail_project.models import (
    Pekerjaan,
    PekerjaanProgressWeekly,
    VolumePekerjaan,
)
from detail_project.views_api import (
    api_upsert_list_pekerjaan,
    api_list_pekerjaan_destructive_impact,
)


class ListPekerjaanDestructiveImpactN2Tests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_destructive_n2",
            email="owner-destructive-n2@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project N2",
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

    def _seed_custom_with_volume(self, uraian="Lama", qty="100.000"):
        resp = self._call(api_upsert_list_pekerjaan, self.upsert_url, {
            "klasifikasi": [{
                "name": "Klas 1", "ordering_index": 1,
                "sub": [{
                    "name": "Sub 1", "ordering_index": 1,
                    "pekerjaan": [{
                        "source_type": "custom", "ordering_index": 1,
                        "snapshot_uraian": uraian, "snapshot_satuan": "m2",
                    }],
                }],
            }]
        })
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))
        job = Pekerjaan.objects.get(project=self.project, snapshot_uraian=uraian)
        VolumePekerjaan.objects.create(
            project=self.project, pekerjaan=job, quantity=Decimal(qty)
        )
        PekerjaanProgressWeekly.objects.create(
            project=self.project, pekerjaan=job, week_number=1,
            week_start_date=date(2026, 1, 1),
            week_end_date=date(2026, 1, 1) + timedelta(days=6),
            planned_proportion=Decimal("40.00"),
        )
        return job

    def _impact(self, job, new_source_type, ref_id=None):
        pekerjaan = {
            "id": job.id, "source_type": new_source_type, "ordering_index": 1,
        }
        if ref_id is not None:
            pekerjaan["ref_id"] = ref_id
        if new_source_type == "custom":
            pekerjaan["snapshot_uraian"] = job.snapshot_uraian or "Lama"
        payload = {
            "klasifikasi": [{
                "id": job.sub_klasifikasi.klasifikasi_id,
                "name": "Klas 1", "ordering_index": 1,
                "sub": [{
                    "id": job.sub_klasifikasi_id,
                    "name": "Sub 1", "ordering_index": 1,
                    "pekerjaan": [pekerjaan],
                }],
            }]
        }
        resp = self._call(api_list_pekerjaan_destructive_impact, self.impact_url, payload)
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))
        return json.loads(resp.content.decode("utf-8"))

    def test_source_change_is_flagged_for_reset_with_derived_counts(self):
        """custom -> ref (source_type change) on a row with volume/jadwal => reset preview."""
        job = self._seed_custom_with_volume()
        body = self._impact(job, "ref", ref_id=999)  # ref_id need not exist for a read-only preview

        self.assertTrue(body["has_reset"], body)
        self.assertFalse(body["has_destructive"], body)  # nothing deleted
        self.assertEqual(body["reset_totals"]["pekerjaan"], 1)
        self.assertEqual(body["reset_totals"]["volume"], 1)
        self.assertEqual(body["reset_totals"]["jadwal"], 1)
        ids = [r["id"] for r in body["to_reset"]]
        self.assertIn(job.id, ids)

    def test_same_source_is_not_flagged(self):
        """custom -> custom (no source change) must NOT raise a reset warning."""
        job = self._seed_custom_with_volume()
        body = self._impact(job, "custom")

        self.assertFalse(body["has_reset"], body)
        self.assertEqual(body["to_reset"], [])

    def test_source_change_without_derived_data_is_not_flagged(self):
        """A source change that destroys nothing must stay silent (proportional)."""
        resp = self._call(api_upsert_list_pekerjaan, self.upsert_url, {
            "klasifikasi": [{
                "name": "Klas 1", "ordering_index": 1,
                "sub": [{
                    "name": "Sub 1", "ordering_index": 1,
                    "pekerjaan": [{
                        "source_type": "custom", "ordering_index": 1,
                        "snapshot_uraian": "Kosong", "snapshot_satuan": "m2",
                    }],
                }],
            }]
        })
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))
        job = Pekerjaan.objects.get(project=self.project, snapshot_uraian="Kosong")
        # No Volume / weekly / detail attached.
        body = self._impact(job, "ref", ref_id=999)
        self.assertFalse(body["has_reset"], body)
        self.assertEqual(body["to_reset"], [])
