from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.urls import reverse

from referensi.models import AHSPReferensi, RincianReferensi
from referensi.models_staging import AHSPImportBatch, AHSPImportStaging
from referensi.views.import_views import _commit_preflight, staging_commit


class ImportBatchCommitPolicyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="batch-admin",
            email="batch-admin@example.com",
            password="Secret123!",
        )
        self.factory = RequestFactory()

    def _commit(self, data):
        request = self.factory.post(reverse("referensi:import_staging_commit"), data)
        request.user = self.user
        SessionMiddleware(lambda req: None).process_request(request)
        request.session.save()
        request._messages = FallbackStorage(request)
        return staging_commit(request)

    def _stage_parent(self, *, sumber="AHSP 2026", batch=None, parent="1.2.3.4"):
        batch = batch or AHSPImportBatch.objects.create(
            user=self.user,
            file_name="batch.xlsx",
            sumber=sumber,
        )
        AHSPImportStaging.objects.create(
            user=self.user,
            batch=batch,
            file_name=batch.file_name,
            sumber=sumber,
            segment_type="HEADING",
            kode_item=parent,
            uraian_item="Pekerjaan Batch",
            is_valid=True,
        )
        AHSPImportStaging.objects.create(
            user=self.user,
            batch=batch,
            file_name=batch.file_name,
            sumber=sumber,
            parent_ahsp_code=parent,
            segment_type="A",
            kode_item="L.01",
            uraian_item="Pekerja",
            satuan_item="OH",
            koefisien=1,
            is_valid=True,
        )
        return batch

    def test_abort_duplicate_refuses_existing_source_code(self):
        AHSPReferensi.objects.create(
            kode_ahsp="1.2.3.4",
            nama_ahsp="Existing",
            sumber="AHSP 2026",
        )
        batch = self._stage_parent()

        response = self._commit(
            {
                "batch_id": batch.id,
                "sumber": "AHSP 2026",
                "commit_mode": AHSPImportBatch.CommitMode.ABORT_DUPLICATE,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            AHSPImportStaging.objects.filter(user=self.user, batch=batch).exists()
        )
        batch.refresh_from_db()
        self.assertEqual(batch.status, AHSPImportBatch.Status.STAGED)
        self.assertEqual(
            AHSPReferensi.objects.get(kode_ahsp="1.2.3.4", sumber="AHSP 2026").rincian.count(),
            0,
        )

    def test_replace_removes_old_rincian_missing_from_batch(self):
        ahsp = AHSPReferensi.objects.create(
            kode_ahsp="1.2.3.4",
            nama_ahsp="Existing",
            sumber="AHSP 2026",
        )
        RincianReferensi.objects.create(
            ahsp=ahsp,
            kategori="TK",
            kode_item="L.01",
            uraian_item="Pekerja",
            satuan_item="OH",
            koefisien=0.5,
        )
        RincianReferensi.objects.create(
            ahsp=ahsp,
            kategori="BHN",
            kode_item="B.OLD",
            uraian_item="Bahan Lama",
            satuan_item="kg",
            koefisien=2,
        )
        batch = self._stage_parent()

        response = self._commit(
            {
                "batch_id": batch.id,
                "sumber": "AHSP 2026",
                "commit_mode": AHSPImportBatch.CommitMode.REPLACE,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("referensi:admin_portal"))
        ahsp.refresh_from_db()
        self.assertEqual(ahsp.nama_ahsp, "Pekerjaan Batch")
        rincian = {
            (item.kategori, item.kode_item, item.uraian_item, item.satuan_item, item.koefisien)
            for item in ahsp.rincian.all()
        }
        self.assertEqual(len(rincian), 1)
        only_item = next(iter(rincian))
        self.assertEqual(only_item[:4], ("TK", "L.01", "Pekerja", "OH"))
        self.assertEqual(str(only_item[4]), "1.000000")
        batch.refresh_from_db()
        self.assertEqual(batch.status, AHSPImportBatch.Status.COMMITTED)
        self.assertEqual(batch.commit_mode, AHSPImportBatch.CommitMode.REPLACE)
        self.assertEqual(batch.summary["deleted_rincian"], 1)

    def test_preflight_counts_distinct_parent_ahsp_not_detail_rows(self):
        batch = self._stage_parent(parent="1.2.3.4")
        AHSPImportStaging.objects.create(
            user=self.user,
            batch=batch,
            file_name=batch.file_name,
            sumber="AHSP 2026",
            parent_ahsp_code="1.2.3.4",
            segment_type="B",
            kode_item="B.01",
            uraian_item="Semen",
            satuan_item="kg",
            koefisien=2,
            is_valid=True,
        )

        staging_items = AHSPImportStaging.objects.filter(
            user=self.user,
            batch=batch,
            is_valid=True,
            segment_type__in=["A", "B", "C", "LAIN"],
        )
        preflight = _commit_preflight(
            staging_items,
            "AHSP 2026",
            AHSPImportBatch.CommitMode.MERGE,
        )

        self.assertEqual(staging_items.count(), 2)
        self.assertEqual(preflight["parent_total"], 1)
