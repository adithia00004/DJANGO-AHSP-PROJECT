from django.test import SimpleTestCase

from referensi.services.import_error_analyzer import ErrorAnalysis, format_error_as_html


class ImportErrorHtmlSafetyTests(SimpleTestCase):
    def test_untrusted_analysis_values_are_rendered_as_text(self):
        analysis = ErrorAnalysis(
            error_type='<svg onload=alert(1)>',
            error_message='raw error',
            user_message='<img src=x onerror=alert(1)>',
            suggestions=['<script>alert(1)</script>'],
            affected_rows=['<a href=x>1</a>'],
            affected_fields=[],
            severity='critical',
            technical_details='private traceback',
        )

        html = format_error_as_html(analysis)

        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', html)
        self.assertIn('&lt;svg onload=alert(1)&gt;', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertIn('&lt;a href=x&gt;1&lt;/a&gt;', html)
        self.assertNotIn('<img src=x', html)
        self.assertNotIn('<svg', html)
        self.assertNotIn('<script', html)
        self.assertNotIn('private traceback', html)

