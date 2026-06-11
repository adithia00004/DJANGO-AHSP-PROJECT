from pathlib import Path

from django.test import SimpleTestCase


class DetailAhspGabunganUiRegressionTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.js_source = (
            Path(__file__).resolve().parent
            / "static"
            / "detail_project"
            / "js"
            / "detail_ahsp_gabungan.js"
        ).read_text(encoding="utf-8")

    def test_unsaved_rows_are_guarded_before_selection_change(self):
        self.assertIn("let dirty = false;", self.js_source)
        self.assertIn("tbody?.addEventListener('input', () => setDirty(true));", self.js_source)
        self.assertIn("window.addEventListener('beforeunload'", self.js_source)
        self.assertIn("if (dirty) {", self.js_source)
        self.assertIn("restoreSelection(lastSelectedIds);", self.js_source)

    def test_successful_save_clears_dirty_state(self):
        self.assertIn("setDirty(false);", self.js_source)
        save_idx = self.js_source.index("document.getElementById('btn-save-dag').onclick")
        success_idx = self.js_source.index("setDirty(false);", save_idx)
        alert_idx = self.js_source.index("Disimpan:", success_idx)
        self.assertLess(success_idx, alert_idx)
