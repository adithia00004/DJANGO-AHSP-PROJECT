"""T-6 (docs/RENCANA_PERAPIAN_PROYEK_20261001.md): pesan server sukses/info
tampil sebagai toast, jadi js/core/toast.js harus dimuat sebelum
messages_modal.js di templates/base.html (keduanya `defer`, urutan dokumen)."""
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class BaseTemplateToastOrderTests(SimpleTestCase):
    def test_toast_core_loads_before_messages_modal(self):
        html = (Path(settings.BASE_DIR) / 'templates' / 'base.html').read_text(encoding='utf-8')
        toast = html.index("detail_project/js/core/toast.js")
        modal = html.index("detail_project/js/messages_modal.js")
        self.assertLess(toast, modal)
