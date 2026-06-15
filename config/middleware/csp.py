"""WP-A2 — Content Security Policy (report-only first).

A dependency-free middleware that emits a CSP header built from
``settings.CSP_POLICY``. It starts in **report-only** mode
(``settings.CSP_REPORT_ONLY = True``) so it never blocks a workflow — the browser
only POSTs a violation report to ``settings.CSP_REPORT_PATH``. Flip
``CSP_REPORT_ONLY`` to ``False`` (separate enforcement milestone) once inline
scripts are migrated/nonced and CDN deps are self-hosted or SRI-pinned.

See ``csp_report`` for the violation sink.
"""
from __future__ import annotations

import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger("csp")
_MAX_REPORT_BYTES = 64 * 1024


def _safe_log_value(value, limit=500):
    text = str(value or "").replace("\r", " ").replace("\n", " ")
    return text[:limit]


def _build_policy() -> str:
    policy = getattr(settings, "CSP_POLICY", None) or {}
    parts = []
    for directive, sources in policy.items():
        if not sources:
            continue
        parts.append(f"{directive} {' '.join(sources)}")
    report_path = getattr(settings, "CSP_REPORT_PATH", "")
    if report_path:
        # report-uri is still the most widely supported sink directive.
        parts.append(f"report-uri {report_path}")
    return "; ".join(parts)


class ContentSecurityPolicyMiddleware:
    """Attach the CSP (report-only by default) header to every response."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._policy = _build_policy()
        self._header = (
            "Content-Security-Policy-Report-Only"
            if getattr(settings, "CSP_REPORT_ONLY", True)
            else "Content-Security-Policy"
        )
        # If no policy configured, disable the middleware cheaply.
        self._enabled = bool(self._policy)

    def __call__(self, request):
        response = self.get_response(request)
        # Don't clobber a header a view may have set deliberately.
        if self._enabled and self._header not in response:
            response[self._header] = self._policy
        return response


@csrf_exempt
def csp_report(request):
    """Violation sink: log CSP reports for the report-only inventory (WP-A2).

    Browsers POST ``application/csp-report`` (or ``application/reports+json``).
    Always returns 204 and never raises — it must not affect any workflow.
    """
    if request.method != "POST":
        return HttpResponse(status=405)
    content_length = request.META.get("CONTENT_LENGTH")
    try:
        if content_length and int(content_length) > _MAX_REPORT_BYTES:
            logger.warning("CSP report dropped: payload too large")
            return HttpResponse(status=204)
    except (TypeError, ValueError):
        pass
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = {"_unparsed": True}
    # Reporting API commonly sends application/reports+json as a list whose
    # first entry contains the violation under "body".
    if isinstance(payload, list):
        payload = payload[0] if payload and isinstance(payload[0], dict) else {}
    if not isinstance(payload, dict):
        payload = {"_unparsed": True}
    report = payload.get("csp-report") or payload.get("body") or payload
    if not isinstance(report, dict):
        report = {"_unparsed": True}
    logger.warning(
        "CSP violation: blocked=%s directive=%s document=%s",
        _safe_log_value(report.get("blocked-uri") or report.get("blockedURL")),
        _safe_log_value(
            report.get("violated-directive")
            or report.get("effective-directive")
            or report.get("effectiveDirective")
        ),
        _safe_log_value(report.get("document-uri") or report.get("documentURL")),
        extra={"csp_report": report},
    )
    return HttpResponse(status=204)
