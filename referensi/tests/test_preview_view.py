from decimal import Decimal
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from referensi.services.ahsp_parser import AHSPPreview, ParseResult, RincianPreview
from referensi.services.import_writer import ImportSummary
from referensi.views import (
    PENDING_IMPORT_SESSION_KEY,
    _cleanup_pending_import,
    admin_portal,
    commit_import,
    preview_import,
)


class DummyUser(SimpleNamespace):
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
            "referensi.views.render",
            wraps=lambda req, template, context=None, **kwargs: HttpResponse(),
        ) as mocked_render:
            admin_portal(request)

        mocked_render.assert_called_once()
        self.assertEqual(mocked_render.call_args[0][1], "referensi/admin_portal.html")

    def test_staff_user_allowed(self):
        request = self.factory.get("/referensi/admin-portal/")
        request.user = self.staff_user
        with mock.patch(
            "referensi.views.render",
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

    def test_preview_requires_superuser(self):
        request = self._prepare_request("get", "/import/preview/", user=self.regular_user)
        with self.assertRaises(PermissionDenied):
            preview_import(request)

    def test_preview_allows_staff(self):
        staff_user = DummyUser(is_superuser=False, is_staff=True)
        request = self._prepare_request("get", "/import/preview/", user=staff_user)
        with mock.patch(
            "referensi.views.render",
            wraps=lambda req, template, context=None, **kwargs: HttpResponse(),
        ) as mocked_render:
            preview_import(request)

        mocked_render.assert_called_once()

    def test_preview_stores_pending_result(self):
        parse_result = self._build_parse_result()
        upload = SimpleNamespace(name="data.xlsx")
        form = mock.Mock()
        form.is_valid.return_value = True
        form.cleaned_data = {"excel_file": upload}

        request = self._prepare_request("post", "/import/preview/")

        with mock.patch("referensi.views.AHSPPreviewUploadForm", return_value=form), mock.patch(
            "referensi.views.load_preview_from_file", return_value=parse_result
        ), mock.patch(
            "referensi.views.render", wraps=lambda req, template, context: HttpResponse()
        ) as mocked_render:
            preview_import(request)

        mocked_render.assert_called_once()
        context = mocked_render.call_args[0][2]
        self.assertIs(context["parse_result"], parse_result)
        self.assertEqual(context["uploaded_name"], "data.xlsx")
        self.assertTrue(context["import_token"])

        pending = request.session[PENDING_IMPORT_SESSION_KEY]
        self.assertEqual(pending["uploaded_name"], "data.xlsx")

    def test_commit_import_uses_writer_and_clears_session(self):
        parse_result = self._build_parse_result()

        upload = SimpleNamespace(name="data.xlsx")
        form = mock.Mock()
        form.is_valid.return_value = True
        form.cleaned_data = {"excel_file": upload}

        request_preview = self._prepare_request("post", "/import/preview/")

        with mock.patch("referensi.views.AHSPPreviewUploadForm", return_value=form), mock.patch(
            "referensi.views.load_preview_from_file", return_value=parse_result
        ), mock.patch(
            "referensi.views.render", wraps=lambda req, template, context: HttpResponse()
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

        with mock.patch("referensi.views.write_parse_result_to_db", return_value=summary) as mocked_writer:
            response = commit_import(request_commit)

        self.assertEqual(response.status_code, 302)
        mocked_writer.assert_called_once()
        self.assertNotIn(PENDING_IMPORT_SESSION_KEY, request_commit.session)
