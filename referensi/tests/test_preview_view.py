from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from referensi.services.ahsp_parser import AHSPPreview, ParseResult, RincianPreview
from referensi.services.preview_service import ImportSessionManager
from referensi.services.import_writer import ImportSummary
from referensi.views import admin_portal, commit_import, preview_import
from referensi.views.constants import TAB_ITEMS, TAB_JOBS, PENDING_IMPORT_SESSION_KEY


class DummyUser(SimpleNamespace):
    def __init__(self, perms=None, **kwargs):
        kwargs.setdefault("username", "tester")
        self._perms = set(perms or [])
        super().__init__(**kwargs)

    @property
    def is_authenticated(self) -> bool:  # pragma: no cover - property access only
        return True

    def has_perm(self, perm: str) -> bool:
        if getattr(self, "is_superuser", False):
            return True
        return perm in self._perms

    def has_perms(self, perms) -> bool:
        return all(self.has_perm(perm) for perm in perms)


class AdminPortalViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = DummyUser(is_superuser=True, is_staff=True)
        self.staff_user = DummyUser(
            is_superuser=False,
            is_staff=True,
            perms={
                "referensi.view_ahspreferensi",
                "referensi.change_ahspreferensi",
            },
        )
        self.regular_user = DummyUser(is_superuser=False, is_staff=False)

    def test_requires_superuser(self):
        request = self.factory.get("/referensi/admin-portal/")
        request.user = self.regular_user
        with self.assertRaises(PermissionDenied):
            admin_portal(request)

    def test_renders_template(self):
        request = self.factory.get("/referensi/admin-portal/")
        request.user = self.superuser
        with mock.patch(
            "referensi.views.admin_portal.render",
            wraps=lambda req, template, context=None, **kwargs: HttpResponse(),
        ) as mocked_render:
            admin_portal(request)

        mocked_render.assert_called_once()
        self.assertEqual(mocked_render.call_args[0][1], "referensi/admin_portal.html")

    def test_staff_user_allowed(self):
        request = self.factory.get("/referensi/admin-portal/")
        request.user = self.staff_user
        with mock.patch(
            "referensi.views.admin_portal.render",
            wraps=lambda req, template, context=None, **kwargs: HttpResponse(),
        ) as mocked_render:
            admin_portal(request)

        mocked_render.assert_called_once()


@override_settings(SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies")
class PreviewImportViewTests(TestCase):
    """
    Tests for preview import functionality.

    Note: Uses TestCase instead of SimpleTestCase because the view code
    may trigger database queries through signals or middleware.
    """
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = DummyUser(is_superuser=True, is_staff=True)
        self.staff_user = DummyUser(
            is_superuser=False,
            is_staff=True,
            perms={
                "referensi.view_ahspreferensi",
                "referensi.import_ahsp_data",
            },
        )
        self.regular_user = DummyUser(is_superuser=False, is_staff=False)
        self._requests: list = []
        self.session_manager = ImportSessionManager()

    def tearDown(self):
        for request in self._requests:
            session = getattr(request, "session", None)
            if session is not None:
                try:
                    self.session_manager.cleanup(session)
                except Exception:
                    # Session may have been cleaned already inside view
                    pass

    def _prepare_request(self, method: str, path: str, data=None, user=None):
        if method.lower() == "post":
            request = self.factory.post(path, data=data or {})
        else:
            request = self.factory.get(path, data=data or {})

        session_middleware = SessionMiddleware(lambda req: HttpResponse())
        session_middleware.process_request(request)
        request.session.save()

        message_middleware = MessageMiddleware(lambda req: HttpResponse())
        message_middleware.process_request(request)

        request.user = user or self.superuser
        self._requests.append(request)
        return request

    def _build_parse_result(self) -> ParseResult:
        rincian = RincianPreview(
            kategori="TK",
            kode_item="001",
            uraian_item="Pekerja",
            satuan_item="OH",
            koefisien=Decimal("1"),
            row_number=3,
        )
        job = AHSPPreview(
            sumber="SNI 2025",
            kode_ahsp="1.1.1",
            nama_ahsp="Pekerjaan Tanah",
            row_number=2,
            rincian=[rincian],
        )
        return ParseResult(jobs=[job])

    def _build_upload_form_mock(self, upload, *, is_valid=True):
        widget = mock.Mock()
        widget.attrs = {}
        field = mock.Mock()
        field.widget = widget
        form = mock.Mock()
        form.is_valid.return_value = is_valid
        form.cleaned_data = {"excel_file": upload}
        form.fields = {"excel_file": field}
        return form

    def test_preview_requires_superuser(self):
        request = self._prepare_request("get", "/import/preview/", user=self.regular_user)
        with self.assertRaises(PermissionDenied):
            preview_import(request)

    def test_preview_allows_staff(self):
        request = self._prepare_request("get", "/import/preview/", user=self.staff_user)
        with mock.patch(
            "referensi.views.preview.render",
            wraps=lambda req, template, context=None, **kwargs: HttpResponse(),
        ) as mocked_render:
            preview_import(request)

        mocked_render.assert_called_once()

    def test_preview_stores_pending_result(self):
        parse_result = self._build_parse_result()
        upload = mock.Mock()
        upload.name = "data.xlsx"
        upload.size = 1024
        upload.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        upload.seek = mock.Mock(return_value=0)
        form = self._build_upload_form_mock(upload)

        request = self._prepare_request("post", "/import/preview/")

        with mock.patch("referensi.views.preview.AHSPPreviewUploadForm", return_value=form), mock.patch(
            "referensi.views.preview.load_preview_from_file", return_value=parse_result
        ), mock.patch("referensi.views.preview.assign_item_codes") as mocked_assign, mock.patch(
            "referensi.services.preview_service.assign_item_codes"
        ), mock.patch(
            "referensi.views.preview.validate_ahsp_file"
        ), mock.patch(
            "referensi.views.preview.render", wraps=lambda req, template, context: HttpResponse()
        ) as mocked_render:
            preview_import(request)

        mocked_render.assert_called_once()
        context = mocked_render.call_args[0][2]
        self.assertIs(context["parse_result"], parse_result)
        self.assertEqual(context["uploaded_name"], "data.xlsx")
        self.assertTrue(context["import_token"])
        mocked_assign.assert_called_once_with(parse_result)

        pending = request.session[PENDING_IMPORT_SESSION_KEY]
        self.assertEqual(pending["uploaded_name"], "data.xlsx")

    def test_commit_import_uses_writer_and_clears_session(self):
        parse_result = self._build_parse_result()

        upload = mock.Mock()
        upload.name = "data.xlsx"
        upload.size = 1024
        upload.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        upload.seek = mock.Mock(return_value=0)
        form = self._build_upload_form_mock(upload)

        request_preview = self._prepare_request("post", "/import/preview/")

        with mock.patch("referensi.views.preview.AHSPPreviewUploadForm", return_value=form), mock.patch(
            "referensi.views.preview.load_preview_from_file", return_value=parse_result
        ), mock.patch("referensi.views.preview.assign_item_codes"), mock.patch(
            "referensi.services.preview_service.assign_item_codes"
        ), mock.patch(
            "referensi.views.preview.validate_ahsp_file"
        ), mock.patch(
            "referensi.views.preview.render", wraps=lambda req, template, context: HttpResponse()
        ):
            preview_import(request_preview)

        pending = request_preview.session[PENDING_IMPORT_SESSION_KEY]
        token = pending["token"]

        request_commit = self._prepare_request(
            "post",
            "/import/commit/",
            data={"token": token},
        )
        # Gunakan session yang sama untuk memastikan view membaca data pending
        request_commit.session[PENDING_IMPORT_SESSION_KEY] = pending

        summary = ImportSummary(jobs_created=1, jobs_updated=0, rincian_written=1)

        with mock.patch("referensi.views.preview.assign_item_codes"), mock.patch(
            "referensi.services.preview_service.assign_item_codes"
        ), mock.patch(
            "referensi.views.preview.write_parse_result_to_db", return_value=summary
        ) as mocked_writer:
            response = commit_import(request_commit)

        self.assertEqual(response.status_code, 302)
        mocked_writer.assert_called_once()
        self.assertNotIn(PENDING_IMPORT_SESSION_KEY, request_commit.session)

    def test_preview_update_applies_form_changes(self):
        parse_result = self._build_parse_result()

        def fake_assign(result):
            for job in result.jobs:
                for detail in job.rincian:
                    if not detail.kode_item:
                        detail.kode_item = "TK-0001"
                        detail.kode_item_source = "generated"

        job_payload = {
            "action": "update_jobs",
            "jobs_page": "1",
            "details_page": "1",
            "jobs-TOTAL_FORMS": "1",
            "jobs-INITIAL_FORMS": "1",
            "jobs-MIN_NUM_FORMS": "0",
            "jobs-MAX_NUM_FORMS": "1000",
            "jobs-0-job_index": "0",
            "jobs-0-sumber": "Sumber Baru",
            "jobs-0-kode_ahsp": "1.1.1",
            "jobs-0-nama_ahsp": "Pekerjaan Tanah Direvisi",
            "jobs-0-klasifikasi": "Sipil",
            "jobs-0-sub_klasifikasi": "Tanah",
            "jobs-0-satuan": "m3",
        }

        jobs_request = self._prepare_request("post", "/import/preview/", data=job_payload)
        self.session_manager.store(jobs_request.session, parse_result, "data.xlsx")

        with mock.patch(
            "referensi.views.preview.assign_item_codes", side_effect=fake_assign
        ), mock.patch(
            "referensi.services.preview_service.assign_item_codes", side_effect=fake_assign
        ), mock.patch("referensi.views.preview.redirect", wraps=redirect):
            response = preview_import(jobs_request)

        self.assertEqual(response.status_code, 302)
        updated_result, _, _ = self.session_manager.retrieve(jobs_request.session)
        self.assertEqual(updated_result.jobs[0].sumber, "Sumber Baru")
        self.assertEqual(updated_result.jobs[0].nama_ahsp, "Pekerjaan Tanah Direvisi")

        detail_payload = {
            "action": "update_details",
            "jobs_page": "1",
            "details_page": "1",
            "details-TOTAL_FORMS": "1",
            "details-INITIAL_FORMS": "1",
            "details-MIN_NUM_FORMS": "0",
            "details-MAX_NUM_FORMS": "1000",
            "details-0-job_index": "0",
            "details-0-detail_index": "0",
            "details-0-kategori": "TK",
            "details-0-kode_item": "",
            "details-0-uraian_item": "Pekerja",
            "details-0-satuan_item": "OH",
            "details-0-koefisien": "1.50",
        }

        detail_request = self._prepare_request("post", "/import/preview/", data=detail_payload)
        detail_request.session[PENDING_IMPORT_SESSION_KEY] = jobs_request.session[
            PENDING_IMPORT_SESSION_KEY
        ].copy()

        with mock.patch(
            "referensi.views.preview.assign_item_codes", side_effect=fake_assign
        ), mock.patch(
            "referensi.services.preview_service.assign_item_codes", side_effect=fake_assign
        ), mock.patch("referensi.views.preview.redirect", wraps=redirect):
            response = preview_import(detail_request)

        self.assertEqual(response.status_code, 302)
        updated_result, _, _ = self.session_manager.retrieve(detail_request.session)
        detail = updated_result.jobs[0].rincian[0]
        self.assertEqual(detail.koefisien, Decimal("1.50"))
        self.assertEqual(detail.kode_item, "TK-0001")
