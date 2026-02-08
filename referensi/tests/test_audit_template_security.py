from pathlib import Path

from django.test import SimpleTestCase


class AuditTemplateSecurityTests(SimpleTestCase):
    def test_log_detail_metadata_uses_json_script_instead_of_safe(self):
        template_path = Path("referensi/templates/referensi/audit/log_detail.html")
        content = template_path.read_text(encoding="utf-8")

        self.assertNotIn("{{ log.metadata|safe }}", content)
        self.assertIn("{{ log.metadata|json_script:\"log-metadata-data\" }}", content)
