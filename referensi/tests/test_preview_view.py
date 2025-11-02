from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect
from django.test import RequestFactory, SimpleTestCase, override_settings

from referensi.services.ahsp_parser import AHSPPreview, ParseResult, RincianPreview
from referensi.services.import_writer import ImportSummary
from referensi.views import admin_portal, commit_import, preview_import
from referensi.views.constants import TAB_ITEMS, TAB_JOBS, PENDING_IMPORT_SESSION_KEY
from referensi.views.preview import (
    _cleanup_pending_import,
    _load_pending_result,
    _store_pending_import,
)


class DummyUser(SimpleNamespace):
    def __init__(self, **kwargs):
        kwargs.setdefault("username", "tester")
        super().__init__(**kwargs)

    @property
    def is_authenticated(self) -> bool:  # pragma: no cover - property access only
        return True


class AdminPortalViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = DummyUser(is_superuser=True, is_staff=True)
        self.staff_user = DummyUser(is_superuser=False, is_staff=True)
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
class PreviewImportViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = DummyUser(is_superuser=True, is_staff=True)
        self.regular_user = DummyUser(is_superuser=False, is_staff=False)
        self._requests: list = []

    def tearDown(self):
        for request in self._requests:
            _cleanup_pending_import(getattr(request, "session", {}))

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
        staff_user = DummyUser(is_superuser=False, is_staff=True)
        request = self._prepare_request("get", "/import/preview/", user=staff_user)
        with mock.patch(
            "referensi.views.preview.render",
            wraps=lambda req, template, context=None, **kwargs: HttpResponse(),
        ) as mocked_render:
            preview_import(request)

        mocked_render.assert_called_once()

    def test_preview_stores_pending_result(self):
        parse_result = self._build_parse_result()
        upload = SimpleNamespace(name="data.xlsx")
        form = self._build_upload_form_mock(upload)

        request = self._prepare_request("post", "/import/preview/")

        with mock.patch("referensi.views.preview.AHSPPreviewUploadForm", return_value=form), mock.patch(
            "referensi.views.preview.load_preview_from_file", return_value=parse_result
        ), mock.patch("referensi.views.preview.assign_item_codes") as mocked_assign, mock.patch(
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

        upload = SimpleNamespace(name="data.xlsx")
        form = self._build_upload_form_mock(upload)

        request_preview = self._prepare_request("post", "/import/preview/")

        with mock.patch("referensi.views.preview.AHSPPreviewUploadForm", return_value=form), mock.patch(
            "referensi.views.preview.load_preview_from_file", return_value=parse_result
        ), mock.patch("referensi.views.preview.assign_item_codes"), mock.patch(
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
            "referensi.views.preview.write_parse_result_to_db", return_value=summary
        ) as mocked_writer:
            response = commit_import(request_commit)

        self.assertEqual(response.status_code, 302)
        mocked_writer.assert_called_once()
        self.assertNotIn(PENDING_IMPORT_SESSION_KEY, request_commit.session)

    def test_preview_update_applies_form_changes(self):
        parse_result = self._build_parse_result()
        base_request = self._prepare_request("get", "/import/preview/")
        _store_pending_import(base_request.session, parse_result, "data.xlsx")

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
        jobs_request.session[PENDING_IMPORT_SESSION_KEY] = base_request.session[PENDING_IMPORT_SESSION_KEY]

        with mock.patch("referensi.views.preview.assign_item_codes", side_effect=fake_assign), mock.patch(
            "referensi.views.preview.redirect", wraps=redirect
        ):
            response = preview_import(jobs_request)

        self.assertEqual(response.status_code, 302)
        pending = jobs_request.session[PENDING_IMPORT_SESSION_KEY]
        updated_result, _, _ = _load_pending_result(pending)
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
        detail_request.session[PENDING_IMPORT_SESSION_KEY] = pending

        with mock.patch("referensi.views.preview.assign_item_codes", side_effect=fake_assign), mock.patch(
            "referensi.views.preview.redirect", wraps=redirect
        ):
            response = preview_import(detail_request)

        self.assertEqual(response.status_code, 302)
        pending = detail_request.session[PENDING_IMPORT_SESSION_KEY]
        updated_result, _, _ = _load_pending_result(pending)
        detail = updated_result.jobs[0].rincian[0]
        self.assertEqual(detail.koefisien, Decimal("1.50"))
        self.assertEqual(detail.kode_item, "TK-0001")
