"""Ensure application notifications use the shared DP.toast renderer."""

import re
from pathlib import Path

from django.test import SimpleTestCase


REPO_ROOT = Path(__file__).resolve().parent.parent
JS_ROOTS = (
    REPO_ROOT / "detail_project" / "static" / "detail_project" / "js",
    REPO_ROOT / "dashboard" / "static" / "dashboard" / "js",
    REPO_ROOT / "referensi" / "static" / "referensi" / "js",
)
EXCLUDED_DIRS = {"archive", "archives", "dist", "node_modules", "tests", "vendor"}
CANONICAL_RENDERER = Path("detail_project/static/detail_project/js/core/toast.js")

# These patterns describe independent DOM renderers and their auto-dismiss
# cleanup. Adapter functions named showToast remain allowed.
INDEPENDENT_RENDERER_PATTERNS = (
    ("Bootstrap Toast constructor", re.compile(r"\bnew\s+(?:window\.)?bootstrap\.Toast\s*\(")),
    (
        "page-specific toast container",
        re.compile(r"\b(?:rk-toast-wrap|rk-toast-animations|ta-toast-container|vp-toasts?|vp-toast-body)\b"),
    ),
    ("inline toast HTML renderer", re.compile(r"\btoastHTML?\s*=")),
    (
        "standalone toast timeout remover",
        re.compile(r"setTimeout\s*\(\s*\(\)\s*=>\s*(?:toast(?:El|Element)?|wrapper)\.remove\s*\("),
    ),
    (
        "standalone toast DOM append",
        re.compile(r"(?:document\.body|\w+)\.appendChild\s*\(\s*(?:toast(?:El|Element)?|toastArea)\s*\)"),
    ),
)


def production_js_files():
    for root in JS_ROOTS:
        for path in root.rglob("*.js"):
            relative_parts = path.relative_to(root).parts
            if any(part in EXCLUDED_DIRS for part in relative_parts):
                continue
            if path.name.endswith((".min.js", ".umd.js")):
                continue
            if path.relative_to(REPO_ROOT) == CANONICAL_RENDERER:
                continue
            yield path


class ToastRendererGovernanceTests(SimpleTestCase):
    def test_application_sources_do_not_own_toast_renderers(self):
        violations = []
        for path in production_js_files():
            source = path.read_text(encoding="utf-8")
            relative_path = path.relative_to(REPO_ROOT).as_posix()
            for label, pattern in INDEPENDENT_RENDERER_PATTERNS:
                if pattern.search(source):
                    violations.append(f"{relative_path}: {label}")

        self.assertEqual([], violations, "Gunakan DP.toast; renderer toast kanonik hanya ada di core/toast.js.")

    def test_old_page_specific_toast_containers_are_gone(self):
        active_templates = (
            REPO_ROOT / "detail_project" / "templates" / "detail_project" / "rincian_ahsp.html",
            REPO_ROOT / "detail_project" / "templates" / "detail_project" / "template_ahsp.html",
            REPO_ROOT / "detail_project" / "templates" / "detail_project" / "volume_pekerjaan.html",
        )
        forbidden_ids = ("rk-toast", "ta-toast-container", "vp-toast", "vp-toasts")
        for path in active_templates:
            source = path.read_text(encoding="utf-8")
            for forbidden_id in forbidden_ids:
                self.assertNotIn(forbidden_id, source, f"{path.relative_to(REPO_ROOT)} masih punya #{forbidden_id}")

    def test_server_messages_use_the_global_handler_without_duplicate_alert_partial(self):
        base_template = (REPO_ROOT / "templates" / "base.html").read_text(encoding="utf-8")
        self.assertIn("detail_project/js/messages_modal.js", base_template)

        page_templates = (
            REPO_ROOT / "detail_project" / "templates" / "detail_project" / "list_pekerjaan.html",
            REPO_ROOT / "detail_project" / "templates" / "detail_project" / "rekap_rab.html",
        )
        for path in page_templates:
            self.assertNotIn("detail_project/_alert.html", path.read_text(encoding="utf-8"))

    def test_removed_page_toast_renderers_have_no_active_styles(self):
        active_stylesheets = (
            REPO_ROOT / "dashboard" / "static" / "dashboard" / "css" / "dashboard.css",
            REPO_ROOT / "dashboard" / "static" / "dashboard" / "css" / "ux-enhancements.css",
            REPO_ROOT / "referensi" / "static" / "referensi" / "css" / "ahsp_database.css",
            REPO_ROOT / "referensi" / "static" / "referensi" / "css" / "preview_import.css",
        )
        obsolete_selectors = ("toast-container-modern", "toast-modern", ".alert.position-fixed")
        for path in active_stylesheets:
            source = path.read_text(encoding="utf-8")
            for selector in obsolete_selectors:
                self.assertNotIn(selector, source, f"{path.relative_to(REPO_ROOT)} masih menata renderer yang dihapus")
