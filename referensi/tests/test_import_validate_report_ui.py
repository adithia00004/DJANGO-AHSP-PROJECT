from pathlib import Path

from django.test import SimpleTestCase


class ImportValidateReportUiTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.source = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "referensi"
            / "import_validate_report.html"
        ).read_text(encoding="utf-8")

    def test_save_waits_for_persist_before_marking_success(self):
        handler_start = self.source.index("saveBtn.addEventListener('click', async function")
        persist_index = self.source.index("await persistCurrentEdits();", handler_start)
        success_index = self.source.index(
            "changesCounter.innerText = 'Perubahan tersimpan untuk export';",
            handler_start,
        )

        self.assertLess(persist_index, success_index)
        self.assertIn("if (!response.ok || body.ok !== true)", self.source)
        self.assertIn("throw error;", self.source)

    def test_unsaved_changes_block_unload_and_failed_pagination(self):
        self.assertIn("window.addEventListener('beforeunload'", self.source)
        self.assertIn(
            "changes.modified.length + changes.deleted.length === 0",
            self.source,
        )
        self.assertIn("Perubahan belum tersimpan, sehingga perpindahan halaman dibatalkan.", self.source)
        self.assertNotIn(
            "persistCurrentEdits().finally(() => { window.location.href = href; });",
            self.source,
        )
