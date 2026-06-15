"""WP-A2 — CSP report-only middleware + violation sink tests."""
import json

from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from config.middleware.csp import ContentSecurityPolicyMiddleware, csp_report


def _ok(request):
    return HttpResponse("ok")


class CSPMiddlewareTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_report_only_header_by_default(self):
        mw = ContentSecurityPolicyMiddleware(_ok)
        resp = mw(self.rf.get("/"))
        self.assertIn("Content-Security-Policy-Report-Only", resp)
        self.assertNotIn("Content-Security-Policy", resp)  # not enforcing yet
        value = resp["Content-Security-Policy-Report-Only"]
        self.assertIn("default-src 'self'", value)
        self.assertIn("script-src 'self'", value)
        self.assertIn("https://cdn.jsdelivr.net", value)
        self.assertIn("object-src 'none'", value)
        self.assertIn("report-uri /csp-report/", value)

    def test_script_src_omits_unsafe_inline_to_surface_inline(self):
        mw = ContentSecurityPolicyMiddleware(_ok)
        value = mw(self.rf.get("/"))["Content-Security-Policy-Report-Only"]
        directives = dict(
            part.strip().split(" ", 1) for part in value.split(";") if " " in part.strip()
        )
        self.assertNotIn("'unsafe-inline'", directives.get("script-src", ""))
        # style-src keeps the documented inline exception.
        self.assertIn("'unsafe-inline'", directives.get("style-src", ""))

    @override_settings(CSP_REPORT_ONLY=False)
    def test_enforcing_header_when_flag_off(self):
        mw = ContentSecurityPolicyMiddleware(_ok)  # reads flag at init
        resp = mw(self.rf.get("/"))
        self.assertIn("Content-Security-Policy", resp)
        self.assertNotIn("Content-Security-Policy-Report-Only", resp)

    def test_does_not_clobber_existing_header(self):
        def _with_header(request):
            r = HttpResponse("ok")
            r["Content-Security-Policy-Report-Only"] = "default-src 'none'"
            return r

        resp = ContentSecurityPolicyMiddleware(_with_header)(self.rf.get("/"))
        self.assertEqual(
            resp["Content-Security-Policy-Report-Only"], "default-src 'none'"
        )


class CSPReportSinkTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_post_report_returns_204(self):
        body = json.dumps({
            "csp-report": {
                "blocked-uri": "inline",
                "violated-directive": "script-src",
                "document-uri": "/dashboard/",
            }
        })
        resp = csp_report(
            self.rf.post("/csp-report/", data=body, content_type="application/csp-report")
        )
        self.assertEqual(resp.status_code, 204)

    def test_malformed_body_still_204(self):
        resp = csp_report(
            self.rf.post("/csp-report/", data="not-json", content_type="application/csp-report")
        )
        self.assertEqual(resp.status_code, 204)

    def test_non_object_json_still_204(self):
        resp = csp_report(
            self.rf.post(
                "/csp-report/",
                data='["not", "an", "object"]',
                content_type="application/csp-report",
            )
        )
        self.assertEqual(resp.status_code, 204)

    def test_reporting_api_array_returns_204(self):
        body = json.dumps([
            {
                "type": "csp-violation",
                "body": {
                    "blockedURL": "inline",
                    "effectiveDirective": "script-src-elem",
                    "documentURL": "https://example.test/dashboard/",
                },
            }
        ])
        resp = csp_report(
            self.rf.post(
                "/csp-report/",
                data=body,
                content_type="application/reports+json",
            )
        )
        self.assertEqual(resp.status_code, 204)

    def test_oversized_report_is_dropped_with_204(self):
        resp = csp_report(
            self.rf.post(
                "/csp-report/",
                data="x" * (64 * 1024 + 1),
                content_type="application/csp-report",
            )
        )
        self.assertEqual(resp.status_code, 204)

    def test_get_not_allowed(self):
        self.assertEqual(csp_report(self.rf.get("/csp-report/")).status_code, 405)

    def test_report_url_is_routed_and_csrf_exempt(self):
        url = reverse("csp_report")
        self.assertEqual(url, "/csp-report/")
        # No CSRF token → must still be accepted (browsers can't send one).
        resp = self.client.post(
            url, data="{}", content_type="application/csp-report"
        )
        self.assertEqual(resp.status_code, 204)
