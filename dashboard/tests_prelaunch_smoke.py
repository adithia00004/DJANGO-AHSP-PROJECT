from datetime import timedelta
import json
from io import BytesIO
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from openpyxl import Workbook

from dashboard.forms import UploadProjectForm
from dashboard.models import Project
from detail_project.models import Klasifikasi, SubKlasifikasi, Pekerjaan, VolumePekerjaan


User = get_user_model()
TEST_MIDDLEWARE = [
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware != "config.middleware.timeout.TimeoutMiddleware"
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class PrelaunchFunctionalSmokeTests(TestCase):
    def setUp(self):
        self.password = "StrongPass123!@#"
        self.owner = User.objects.create_user(
            username="owner_smoke",
            email="owner_smoke@example.com",
            password=self.password,
            is_staff=False,
            subscription_status=User.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        self.non_owner = User.objects.create_user(
            username="non_owner_smoke",
            email="non_owner_smoke@example.com",
            password=self.password,
            subscription_status=User.SubscriptionStatus.TRIAL,
            trial_end_date=timezone.now() + timedelta(days=14),
        )

    def _build_upload_file(self, headers, rows, filename="projects_upload.xlsx"):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(headers)
        for row in rows:
            sheet.append(row)

        buff = BytesIO()
        workbook.save(buff)
        buff.seek(0)
        return SimpleUploadedFile(
            filename,
            buff.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_login_logout_and_dashboard_access(self):
        login_url = reverse("account_login")
        dashboard_url = reverse("dashboard:dashboard")
        logout_url = reverse("account_logout")

        self.assertEqual(self.client.get(login_url).status_code, 200)

        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        self.assertEqual(self.client.get(dashboard_url).status_code, 200)

        logout_response = self.client.post(logout_url)
        self.assertIn(logout_response.status_code, {200, 302, 303})

        dashboard_after_logout = self.client.get(dashboard_url)
        self.assertIn(dashboard_after_logout.status_code, {301, 302})

    def test_signup_page_available_and_creates_user(self):
        signup_url = reverse("account_signup")
        self.assertEqual(self.client.get(signup_url).status_code, 200)

        response = self.client.post(
            signup_url,
            {
                "username": "signup_smoke",
                "email": "signup_smoke@example.com",
                "password1": self.password,
                "password2": self.password,
            },
        )
        self.assertIn(response.status_code, {200, 302, 303})

    def test_owner_edit_delete_project(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))

        create_response = self.client.post(
            reverse("dashboard:dashboard"),
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-MIN_NUM_FORMS": "0",
                "form-MAX_NUM_FORMS": "1000",
                "form-0-nama": "Project Smoke",
                "form-0-tanggal_mulai": "2026-01-01",
                "form-0-sumber_dana": "APBD",
                "form-0-lokasi_project": "Jakarta",
                "form-0-nama_client": "Client Smoke",
                "form-0-anggaran_owner": "1000000",
            },
        )
        self.assertIn(create_response.status_code, {302, 303})
        project = Project.objects.get(owner=self.owner, nama="Project Smoke")

        edit_response = self.client.post(
            reverse("dashboard:project_edit", kwargs={"pk": project.pk}),
            {
                "nama": "Project Smoke Updated",
                "tanggal_mulai": "2026-01-01",
                "sumber_dana": "APBD",
                "lokasi_project": "Bandung",
                "nama_client": "Client Smoke Updated",
                "anggaran_owner": "2000000",
                "next": reverse("dashboard:dashboard"),
            },
        )
        self.assertEqual(edit_response.status_code, 302)
        project.refresh_from_db()
        self.assertEqual(project.nama, "Project Smoke Updated")
        self.assertEqual(project.lokasi_project, "Bandung")

        delete_response = self.client.post(
            reverse("dashboard:project_delete", kwargs={"pk": project.pk}),
            {"next": reverse("dashboard:dashboard")},
        )
        self.assertEqual(delete_response.status_code, 302)
        project.refresh_from_db()
        self.assertFalse(project.is_active)

    def test_project_delete_confirmation_preserves_next_and_soft_delete(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        project = Project.objects.create(
            owner=self.owner,
            nama="Delete Confirm Smoke",
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBD",
            lokasi_project="Bogor",
            nama_client="Client Delete",
            anggaran_owner=888888,
        )

        next_url = reverse("dashboard:dashboard") + "?page=3&is_active=true"
        delete_url = reverse("dashboard:project_delete", kwargs={"pk": project.pk})

        confirm_response = self.client.get(f"{delete_url}?next={next_url}")
        self.assertEqual(confirm_response.status_code, 200)
        self.assertContains(confirm_response, 'name="csrfmiddlewaretoken"')
        self.assertContains(confirm_response, 'name="next"')
        self.assertContains(confirm_response, "diarsipkan (soft delete)")
        self.assertContains(confirm_response, "Delete Confirm Smoke")

        project.refresh_from_db()
        self.assertTrue(project.is_active)

        delete_response = self.client.post(delete_url, {"next": next_url})
        self.assertEqual(delete_response.status_code, 302)
        self.assertEqual(delete_response.url, next_url)

        project.refresh_from_db()
        self.assertFalse(project.is_active)

    def test_expired_owner_blocked_on_project_delete_post(self):
        expired_owner = User.objects.create_user(
            username="expired_delete_smoke",
            email="expired_delete_smoke@example.com",
            password=self.password,
            subscription_status=User.SubscriptionStatus.EXPIRED,
            trial_end_date=timezone.now() - timedelta(days=1),
            subscription_end_date=timezone.now() - timedelta(days=1),
        )
        project = Project.objects.create(
            owner=expired_owner,
            nama="Expired Delete",
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBN",
            lokasi_project="Depok",
            nama_client="Client Expired",
            anggaran_owner=777777,
        )

        self.assertTrue(self.client.login(username=expired_owner.username, password=self.password))
        response = self.client.post(
            reverse("dashboard:project_delete", kwargs={"pk": project.pk}),
            {"next": reverse("dashboard:dashboard")},
        )
        self.assertIn(response.status_code, {302, 303})
        self.assertIn("/pricing/", response.url)
        self.assertIn("reason=subscription_expired", response.url)

        project.refresh_from_db()
        self.assertTrue(project.is_active)

    def test_non_owner_blocked_from_project_pages(self):
        project = Project.objects.create(
            owner=self.owner,
            nama="Private Project",
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBN",
            lokasi_project="Surabaya",
            nama_client="Private Client",
            anggaran_owner=123456,
        )
        self.assertTrue(self.client.login(username=self.non_owner.username, password=self.password))

        detail_status = self.client.get(reverse("dashboard:project_detail", kwargs={"pk": project.pk})).status_code
        edit_status = self.client.get(reverse("dashboard:project_edit", kwargs={"pk": project.pk})).status_code
        delete_status = self.client.get(reverse("dashboard:project_delete", kwargs={"pk": project.pk})).status_code
        duplicate_status = self.client.get(reverse("dashboard:project_duplicate", kwargs={"pk": project.pk})).status_code

        self.assertIn(detail_status, {302, 403, 404})
        self.assertIn(edit_status, {302, 403, 404})
        self.assertIn(delete_status, {302, 403, 404})
        self.assertIn(duplicate_status, {302, 403, 404})

    def test_project_duplicate_deep_copy_preserves_related_data_and_next(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        project = Project.objects.create(
            owner=self.owner,
            nama="Project Deep Copy",
            tanggal_mulai=timezone.now().date(),
            tanggal_selesai=timezone.now().date() + timedelta(days=30),
            durasi_hari=31,
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client Copy",
            anggaran_owner=123456789,
        )
        klasifikasi = Klasifikasi.objects.create(project=project, name="Klasifikasi A")
        sub = SubKlasifikasi.objects.create(project=project, klasifikasi=klasifikasi, name="Sub A")
        pekerjaan = Pekerjaan.objects.create(
            project=project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-0001",
            snapshot_uraian="Pekerjaan Uji",
            snapshot_satuan="m3",
        )
        VolumePekerjaan.objects.create(project=project, pekerjaan=pekerjaan, quantity="10")

        duplicate_url = reverse("dashboard:project_duplicate", kwargs={"pk": project.pk})
        next_url = reverse("dashboard:dashboard") + "?page=2&is_active=true"

        response_get = self.client.get(f"{duplicate_url}?next={next_url}")
        self.assertEqual(response_get.status_code, 200)
        self.assertContains(response_get, 'name="next"')
        self.assertContains(response_get, "Project Deep Copy")

        response_post = self.client.post(
            duplicate_url,
            {
                "nama": "Project Deep Copy (Smoke)",
                "tanggal_mulai": "2026-02-10",
                "tanggal_selesai": "2026-03-15",
                "durasi_hari": "35",
                "sumber_dana": "APBN",
                "lokasi_project": "Bandung",
                "nama_client": "Client Copy 2",
                "anggaran_owner": "9999999",
                "next": next_url,
            },
        )
        self.assertEqual(response_post.status_code, 302)
        self.assertEqual(response_post.url, next_url)

        duplicated = Project.objects.get(owner=self.owner, nama="Project Deep Copy (Smoke)")
        self.assertNotEqual(duplicated.pk, project.pk)
        self.assertEqual(duplicated.lokasi_project, "Bandung")
        self.assertEqual(duplicated.nama_client, "Client Copy 2")
        self.assertEqual(duplicated.anggaran_owner, Decimal("9999999"))

        self.assertEqual(Pekerjaan.objects.filter(project=duplicated).count(), 1)
        self.assertEqual(VolumePekerjaan.objects.filter(project=duplicated).count(), 1)

    def test_project_duplicate_get_prefills_incremented_copy_name(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        project = Project.objects.create(
            owner=self.owner,
            nama="Project Increment",
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBD",
            lokasi_project="Bogor",
            nama_client="Client Inc",
            anggaran_owner=111111,
        )
        Project.objects.create(
            owner=self.owner,
            nama="Project Increment (Copy)",
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBD",
            lokasi_project="Bogor",
            nama_client="Client Inc",
            anggaran_owner=111111,
        )

        response = self.client.get(reverse("dashboard:project_duplicate", kwargs={"pk": project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"]["nama"].value(), "Project Increment (Copy 2)")

    def test_project_duplicate_validation_errors_rendered(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        project = Project.objects.create(
            owner=self.owner,
            nama="Project Validation",
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBD",
            lokasi_project="Bandung",
            nama_client="Client Validation",
            anggaran_owner=2000000,
        )

        response = self.client.post(
            reverse("dashboard:project_duplicate", kwargs={"pk": project.pk}),
            {
                "nama": "ab",
                "tanggal_mulai": "2026-03-10",
                "tanggal_selesai": "2026-03-01",
                "sumber_dana": "APBD",
                "lokasi_project": "Bandung",
                "nama_client": "Client Validation",
                "anggaran_owner": "2000000",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Periksa kembali input form")
        self.assertContains(response, "Nama project minimal 3 karakter.")
        self.assertContains(response, "Tanggal selesai harus setelah tanggal mulai.")

    def test_expired_owner_blocked_on_project_duplicate_post(self):
        expired_owner = User.objects.create_user(
            username="expired_duplicate_smoke",
            email="expired_duplicate_smoke@example.com",
            password=self.password,
            subscription_status=User.SubscriptionStatus.EXPIRED,
            trial_end_date=timezone.now() - timedelta(days=1),
            subscription_end_date=timezone.now() - timedelta(days=1),
        )
        project = Project.objects.create(
            owner=expired_owner,
            nama="Expired Duplicate",
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBN",
            lokasi_project="Depok",
            nama_client="Client Expired",
            anggaran_owner=654321,
        )
        self.assertTrue(self.client.login(username=expired_owner.username, password=self.password))

        response = self.client.post(
            reverse("dashboard:project_duplicate", kwargs={"pk": project.pk}),
            {
                "nama": "Expired Duplicate Copy",
                "tanggal_mulai": "2026-02-10",
                "sumber_dana": "APBN",
                "lokasi_project": "Depok",
                "nama_client": "Client Expired",
                "anggaran_owner": "654321",
            },
        )
        self.assertIn(response.status_code, {302, 303})
        self.assertIn("/pricing/", response.url)
        self.assertIn("reason=subscription_expired", response.url)
        self.assertFalse(
            Project.objects.filter(owner=expired_owner, nama="Expired Duplicate Copy").exists()
        )

    def test_project_detail_shows_core_fields_and_navigation(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        project = Project.objects.create(
            owner=self.owner,
            nama="Detail Smoke",
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBN",
            lokasi_project="Semarang",
            nama_client="Client Detail",
            jabatan_client="Direktur",
            instansi_client="Instansi Detail",
            nama_kontraktor="Kontraktor A",
            nama_konsultan_perencana="Konsultan Plan",
            nama_konsultan_pengawas="Konsultan Awas",
            kategori="Infrastruktur",
            anggaran_owner=987654321,
        )

        response = self.client.get(reverse("dashboard:project_detail", kwargs={"pk": project.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Data Inti Project")
        self.assertContains(response, "Client & Stakeholder")
        self.assertContains(response, "APBN")
        self.assertContains(response, "Semarang")
        self.assertContains(response, "Client Detail")
        self.assertContains(response, "Kontraktor A")
        self.assertContains(response, reverse("dashboard:project_edit", kwargs={"pk": project.pk}))
        self.assertContains(response, reverse("dashboard:project_delete", kwargs={"pk": project.pk}))
        self.assertContains(response, reverse("dashboard:export_project_pdf", kwargs={"pk": project.pk}))
        self.assertContains(response, reverse("detail_project:list_pekerjaan", kwargs={"project_id": project.pk}))
        self.assertContains(response, reverse("detail_project:volume_pekerjaan", kwargs={"project_id": project.pk}))

    def test_project_detail_timeline_status_matrix(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        today = timezone.now().date()

        selesai = Project.objects.create(
            owner=self.owner,
            nama="Timeline Selesai",
            tanggal_mulai=today - timedelta(days=40),
            tanggal_selesai=today - timedelta(days=1),
            sumber_dana="APBN",
            lokasi_project="Bandung",
            nama_client="Client S",
            anggaran_owner=1000,
        )
        deadline = Project.objects.create(
            owner=self.owner,
            nama="Timeline Deadline",
            tanggal_mulai=today - timedelta(days=10),
            tanggal_selesai=today + timedelta(days=7),
            sumber_dana="APBD",
            lokasi_project="Jakarta",
            nama_client="Client D",
            anggaran_owner=2000,
        )
        belum_mulai = Project.objects.create(
            owner=self.owner,
            nama="Timeline Belum Mulai",
            tanggal_mulai=today + timedelta(days=20),
            tanggal_selesai=today + timedelta(days=60),
            sumber_dana="APBD",
            lokasi_project="Surabaya",
            nama_client="Client BM",
            anggaran_owner=3000,
        )
        berjalan = Project.objects.create(
            owner=self.owner,
            nama="Timeline Berjalan",
            tanggal_mulai=today - timedelta(days=5),
            tanggal_selesai=today + timedelta(days=45),
            sumber_dana="APBN",
            lokasi_project="Medan",
            nama_client="Client B",
            anggaran_owner=4000,
        )

        resp_selesai = self.client.get(reverse("dashboard:project_detail", kwargs={"pk": selesai.pk}))
        resp_deadline = self.client.get(reverse("dashboard:project_detail", kwargs={"pk": deadline.pk}))
        resp_belum_mulai = self.client.get(reverse("dashboard:project_detail", kwargs={"pk": belum_mulai.pk}))
        resp_berjalan = self.client.get(reverse("dashboard:project_detail", kwargs={"pk": berjalan.pk}))

        self.assertContains(resp_selesai, "Selesai")
        self.assertNotContains(resp_selesai, "Terlambat")
        self.assertContains(resp_deadline, "Deadline")
        self.assertContains(resp_belum_mulai, "Belum Mulai")
        self.assertContains(resp_berjalan, "Sedang Berjalan")

    def test_project_edit_form_validation_csrf_and_xss_escape(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        project = Project.objects.create(
            owner=self.owner,
            nama='<script>alert(7)</script>',
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client XSS",
            anggaran_owner=100000,
        )

        edit_url = reverse("dashboard:project_edit", kwargs={"pk": project.pk})
        response_get = self.client.get(f"{edit_url}?next={reverse('dashboard:dashboard')}")
        self.assertEqual(response_get.status_code, 200)
        self.assertContains(response_get, 'name="csrfmiddlewaretoken"')
        self.assertContains(response_get, "&lt;script&gt;alert(7)&lt;/script&gt;")
        self.assertNotContains(response_get, '<script>alert(7)</script>')

        response_post = self.client.post(
            edit_url,
            {
                "nama": "ab",
                "tanggal_mulai": "2026-02-10",
                "tanggal_selesai": "2026-02-01",
                "sumber_dana": "APBN",
                "lokasi_project": "Jakarta",
                "nama_client": "Client XSS",
                "anggaran_owner": "100000",
                "next": reverse("dashboard:dashboard"),
            },
        )
        self.assertEqual(response_post.status_code, 200)
        self.assertContains(response_post, "Periksa kembali input form")
        self.assertContains(response_post, "Nama project minimal 3 karakter.")
        self.assertContains(response_post, "Tanggal selesai harus setelah tanggal mulai.")

    def test_project_edit_parses_currency_and_redirects_to_next(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        project = Project.objects.create(
            owner=self.owner,
            nama="Currency Edit",
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBD",
            lokasi_project="Bandung",
            nama_client="Client Cur",
            anggaran_owner=1,
        )

        target_next = reverse("dashboard:dashboard") + "?page=2"
        response = self.client.post(
            reverse("dashboard:project_edit", kwargs={"pk": project.pk}),
            {
                "nama": "Currency Edit Updated",
                "tanggal_mulai": "2026-02-10",
                "tanggal_selesai": "2026-03-10",
                "sumber_dana": "APBD",
                "lokasi_project": "Bandung",
                "nama_client": "Client Cur",
                "anggaran_owner": "Rp 1.500.000,50",
                "next": target_next,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, target_next)

        project.refresh_from_db()
        self.assertEqual(project.nama, "Currency Edit Updated")
        self.assertEqual(project.anggaran_owner, Decimal("1500000.50"))

    def test_expired_owner_blocked_on_project_edit_post(self):
        expired_owner = User.objects.create_user(
            username="expired_owner_smoke",
            email="expired_owner_smoke@example.com",
            password=self.password,
            subscription_status=User.SubscriptionStatus.EXPIRED,
            trial_end_date=timezone.now() - timedelta(days=1),
            subscription_end_date=timezone.now() - timedelta(days=1),
        )
        project = Project.objects.create(
            owner=expired_owner,
            nama="Expired Edit",
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBN",
            lokasi_project="Yogyakarta",
            nama_client="Client Exp",
            anggaran_owner=12345,
        )

        self.assertTrue(self.client.login(username=expired_owner.username, password=self.password))
        response = self.client.post(
            reverse("dashboard:project_edit", kwargs={"pk": project.pk}),
            {
                "nama": "Expired Edit Updated",
                "tanggal_mulai": "2026-02-10",
                "sumber_dana": "APBN",
                "lokasi_project": "Yogyakarta",
                "nama_client": "Client Exp",
                "anggaran_owner": "50000",
            },
        )
        self.assertIn(response.status_code, {302, 303})
        self.assertIn("/pricing/", response.url)
        self.assertIn("reason=subscription_expired", response.url)

    def test_dashboard_has_active_filter_and_bulk_controls(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))

        response = self.client.get(reverse("dashboard:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="is_active"')
        self.assertContains(response, 'id="bulkArchiveBtn"')
        self.assertContains(response, 'id="bulkUnarchiveBtn"')
        self.assertContains(response, 'id="bulkDeleteBtn"')

    def test_bulk_archive_and_unarchive_owner_projects(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        p1 = Project.objects.create(
            owner=self.owner,
            nama="Bulk Archive A",
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBD",
            lokasi_project="Bandung",
            nama_client="Client A",
            anggaran_owner=1000000,
        )
        p2 = Project.objects.create(
            owner=self.owner,
            nama="Bulk Archive B",
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client B",
            anggaran_owner=2000000,
        )

        archive_response = self.client.post(
            reverse("dashboard:bulk_archive"),
            data=json.dumps({"project_ids": [p1.pk, p2.pk]}),
            content_type="application/json",
        )
        self.assertEqual(archive_response.status_code, 200)
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertFalse(p1.is_active)
        self.assertFalse(p2.is_active)

        unarchive_response = self.client.post(
            reverse("dashboard:bulk_unarchive"),
            data=json.dumps({"project_ids": [p1.pk, p2.pk]}),
            content_type="application/json",
        )
        self.assertEqual(unarchive_response.status_code, 200)
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertTrue(p1.is_active)
        self.assertTrue(p2.is_active)

    def test_dashboard_export_gating_and_real_file_behavior(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        project = Project.objects.create(
            owner=self.owner,
            nama="Export Probe",
            tanggal_mulai=timezone.now().date(),
            sumber_dana="APBD",
            lokasi_project="Bandung",
            nama_client="Client Export",
            anggaran_owner=5000000,
        )

        excel_response = self.client.get(reverse("dashboard:export_excel"))
        self.assertEqual(excel_response.status_code, 200)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            excel_response.get("Content-Type", ""),
        )

        csv_response = self.client.get(reverse("dashboard:export_csv"))
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("text/csv", csv_response.get("Content-Type", ""))

        pdf_response = self.client.get(reverse("dashboard:export_project_pdf", kwargs={"pk": project.pk}))
        self.assertEqual(pdf_response.status_code, 200)
        self.assertIn("application/pdf", pdf_response.get("Content-Type", ""))
        self.assertTrue(pdf_response.content.startswith(b"%PDF"))

        self.client.logout()
        self.assertTrue(self.client.login(username=self.non_owner.username, password=self.password))
        trial_excel = self.client.get(reverse("dashboard:export_excel"))
        self.assertEqual(trial_excel.status_code, 403)

    def test_project_upload_excel_valid_creates_projects(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        upload_file = self._build_upload_file(
            headers=[
                "nama",
                "tanggal_mulai",
                "sumber_dana",
                "lokasi_project",
                "nama_client",
                "anggaran_owner",
                "kategori",
            ],
            rows=[
                ["Project Upload A", "2026-02-01", "APBD", "Bandung", "Client A", "1000000", "Infrastruktur"],
                ["Project Upload B", "2026-02-02", "APBN", "Jakarta", "Client B", "2000000", "Gedung"],
            ],
        )

        response = self.client.post(
            reverse("dashboard:project_upload"),
            {"file": upload_file},
        )

        self.assertIn(response.status_code, {302, 303})
        self.assertEqual(Project.objects.filter(owner=self.owner, nama="Project Upload A").count(), 1)
        self.assertEqual(Project.objects.filter(owner=self.owner, nama="Project Upload B").count(), 1)

    def test_project_upload_page_contains_csrf_and_file_input(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        response = self.client.get(reverse("dashboard:project_upload"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'type="file"')

    def test_project_upload_rejects_non_xlsx_file(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        txt_file = SimpleUploadedFile(
            "invalid.txt",
            b"nama,tanggal_mulai",
            content_type="text/plain",
        )
        response = self.client.post(
            reverse("dashboard:project_upload"),
            {"file": txt_file},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Format file tidak didukung. Gunakan file .xlsx.")

    def test_project_upload_missing_required_header_shows_error(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        upload_file = self._build_upload_file(
            headers=["nama", "tanggal_mulai", "sumber_dana", "lokasi_project", "anggaran_owner"],
            rows=[["Project Header", "2026-01-10", "APBD", "Bandung", "1000000"]],
        )
        response = self.client.post(
            reverse("dashboard:project_upload"),
            {"file": upload_file},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kolom wajib belum ada")
        self.assertContains(response, "nama_client")

    def test_project_upload_rejects_formula_cell(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        upload_file = self._build_upload_file(
            headers=["nama", "tanggal_mulai", "sumber_dana", "lokasi_project", "nama_client", "anggaran_owner"],
            rows=[["=NOW()", "2026-01-10", "APBD", "Bandung", "Client F", "1000000"]],
        )
        response = self.client.post(
            reverse("dashboard:project_upload"),
            {"file": upload_file},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Formula tidak diizinkan")
        self.assertFalse(Project.objects.filter(owner=self.owner, nama="=NOW()").exists())

    def test_project_upload_duplicate_name_in_file_is_skipped(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        upload_file = self._build_upload_file(
            headers=["nama", "tanggal_mulai", "sumber_dana", "lokasi_project", "nama_client", "anggaran_owner"],
            rows=[
                ["Project Duplicate Upload", "2026-02-01", "APBD", "Bandung", "Client A", "1000000"],
                ["Project Duplicate Upload", "2026-02-05", "APBN", "Jakarta", "Client B", "2000000"],
            ],
        )
        response = self.client.post(
            reverse("dashboard:project_upload"),
            {"file": upload_file},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "baris dilewati karena tidak valid")
        self.assertEqual(Project.objects.filter(owner=self.owner, nama="Project Duplicate Upload").count(), 1)

    def test_project_upload_row_limit_enforced(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        rows = [
            [f"Project Row {i}", "2026-01-01", "APBD", "Bandung", "Client", "1000000"]
            for i in range(1, 2002)
        ]
        upload_file = self._build_upload_file(
            headers=["nama", "tanggal_mulai", "sumber_dana", "lokasi_project", "nama_client", "anggaran_owner"],
            rows=rows,
        )
        response = self.client.post(
            reverse("dashboard:project_upload"),
            {"file": upload_file},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Baris data melebihi batas 2000")

    def test_project_upload_file_size_limit_enforced(self):
        self.assertTrue(self.client.login(username=self.owner.username, password=self.password))
        upload_file = self._build_upload_file(
            headers=["nama", "tanggal_mulai", "sumber_dana", "lokasi_project", "nama_client", "anggaran_owner"],
            rows=[["Project Size Test", "2026-01-10", "APBD", "Bandung", "Client S", "1000000"]],
        )

        original_limit = UploadProjectForm.MAX_UPLOAD_SIZE_BYTES
        UploadProjectForm.MAX_UPLOAD_SIZE_BYTES = 100
        try:
            response = self.client.post(
                reverse("dashboard:project_upload"),
                {"file": upload_file},
            )
        finally:
            UploadProjectForm.MAX_UPLOAD_SIZE_BYTES = original_limit

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ukuran file maksimal 10 MB.")

    def test_expired_owner_blocked_on_project_upload_post(self):
        expired_owner = User.objects.create_user(
            username="expired_upload_smoke",
            email="expired_upload_smoke@example.com",
            password=self.password,
            subscription_status=User.SubscriptionStatus.EXPIRED,
            trial_end_date=timezone.now() - timedelta(days=1),
            subscription_end_date=timezone.now() - timedelta(days=1),
        )
        self.assertTrue(self.client.login(username=expired_owner.username, password=self.password))

        upload_file = self._build_upload_file(
            headers=["nama", "tanggal_mulai", "sumber_dana", "lokasi_project", "nama_client", "anggaran_owner"],
            rows=[["Project Expired Upload", "2026-01-10", "APBD", "Bandung", "Client X", "1000000"]],
        )
        response = self.client.post(
            reverse("dashboard:project_upload"),
            {"file": upload_file},
        )
        self.assertIn(response.status_code, {302, 303})
        self.assertIn("/pricing/", response.url)
        self.assertIn("reason=subscription_expired", response.url)
        self.assertFalse(Project.objects.filter(owner=expired_owner, nama="Project Expired Upload").exists())
