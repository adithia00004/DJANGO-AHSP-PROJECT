from pathlib import Path

from django.test import SimpleTestCase


class TemplateAhspUiRegressionGuardsTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(__file__).resolve().parent
        cls.template_path = (
            cls.root
            / "templates"
            / "detail_project"
            / "template_ahsp.html"
        )
        cls.js_path = (
            cls.root
            / "static"
            / "detail_project"
            / "js"
            / "template_ahsp.js"
        )
        cls.css_path = (
            cls.root
            / "static"
            / "detail_project"
            / "css"
            / "template_ahsp.css"
        )
        cls.template_source = cls.template_path.read_text(encoding="utf-8")
        cls.js_source = cls.js_path.read_text(encoding="utf-8")
        cls.css_source = cls.css_path.read_text(encoding="utf-8")

    def test_template_has_read_only_parameter_sidebar_slot(self):
        self.assertIn('id="ta-param-sidebar"', self.template_source)
        self.assertIn('id="ta-btn-param-sidebar-toggle"', self.template_source)
        self.assertIn('ta-param-overlay-hotspot', self.template_source)
        self.assertIn('id="ta-sidebar-search"', self.template_source)
        self.assertIn('id="ta-var-table"', self.template_source)
        self.assertIn('id="ta-cparam-table"', self.template_source)

    def test_template_has_parameter_refresh_action(self):
        self.assertIn('id="ta-param-sync-status"', self.template_source)
        self.assertIn('id="ta-var-add"', self.template_source)
        self.assertIn('id="ta-var-import-btn"', self.template_source)
        self.assertIn('id="ta-var-export-btn"', self.template_source)

    def test_js_refreshes_parameter_snapshot_and_reevaluates_formula_rows(self):
        self.assertIn("async function refreshParamSnapshot(options = {})", self.js_source)
        self.assertIn("async function reevaluateAllKoefFormulaRows(options = {})", self.js_source)
        self.assertIn("function notifyFormulaDiffIfNeeded(jobId, latestParamSnapshot)", self.js_source)
        self.assertIn("rememberFormulaEvalSnapshot(id", self.js_source)
        self.assertIn("function initParamOverlay()", self.js_source)
        self.assertIn("refreshParamSnapshot({ force: true", self.js_source)
        self.assertIn("tr.dataset.koefIsFx === '1'", self.js_source)

    def test_js_applies_fx_badge_and_inline_state(self):
        self.assertIn("function ensureFxBadge(tr, show, rawFormula)", self.js_source)
        self.assertIn("tr.classList.add('ta-koef-warning')", self.js_source)
        self.assertIn("tr.classList.add('ta-koef-error')", self.js_source)
        self.assertIn("clearKoefFormulaState(tr)", self.js_source)
        self.assertIn("const hasInlineError = $$('tr.ta-row.ta-koef-error').length > 0;", self.js_source)
        self.assertIn("return Promise.reject(new Error('Formula row in error state'));", self.js_source)

    def test_js_handles_missing_parameter_warning_with_last_value_fallback(self):
        self.assertIn('if (result.code === "missing_identifier") {', self.js_source)
        self.assertIn("input.value = __koefToUI(fallbackCanon);", self.js_source)
        self.assertIn("Koefisien memakai nilai terakhir", self.js_source)
        self.assertIn('tr.dataset.koefFormulaLevel = "warning";', self.js_source)
        self.assertIn("warning: true,", self.js_source)

    def test_js_persists_formula_raw_metadata_on_reload_and_save(self):
        self.assertIn("const formulaRaw = String(r.koef_formula_raw || '').trim();", self.js_source)
        self.assertIn("tr.dataset.koefFormulaRaw = isFx ? formulaRaw : '';", self.js_source)
        self.assertIn("tr.dataset.koefIsFx = isFx ? '1' : '0';", self.js_source)
        self.assertIn("const formulaRaw = (tr.dataset.koefFormulaRaw || '').trim();", self.js_source)
        self.assertIn("koef_formula_raw: isFx ? formulaRaw : '',", self.js_source)
        self.assertIn("koef_is_fx: isFx,", self.js_source)

    def test_js_save_failure_rejects_for_job_switch_guard(self):
        catch_idx = self.js_source.index("}).catch((err) => {")
        finally_idx = self.js_source.index("}).finally(() => {", catch_idx)
        self.assertIn("throw err;", self.js_source[catch_idx:finally_idx])

    def test_js_row_key_contract_uses_kode_for_metadata_mapping(self):
        self.assertIn("$('input[data-field=\"kode\"]', tr).value = r.kode || '';", self.js_source)
        self.assertIn("kode: $('input[data-field=\"kode\"]', tr).value.trim(),", self.js_source)

    def test_js_uses_debounced_formula_evaluation_and_lazy_reload_mode(self):
        self.assertIn("const KOEF_INPUT_DEBOUNCE_MS = 300;", self.js_source)
        self.assertIn("function scheduleKoefFormulaEvaluate(inputEl, tr)", self.js_source)
        self.assertIn("clearKoefInputDebounce(el);", self.js_source)
        self.assertIn("const skipFormulaReeval = !!options.skipFormulaReeval;", self.js_source)
        self.assertIn("await selectJobInternal(li, id, true, { skipFormulaReeval });", self.js_source)

    def test_js_keeps_template_csv_export_handler(self):
        self.assertIn("$('#ta-btn-export').addEventListener('click', () => {", self.js_source)
        self.assertIn("const header = 'kategori;kode;uraian;satuan;koefisien';", self.js_source)

    def test_css_contains_fx_warning_error_styles(self):
        self.assertIn(".ta-param-overlay-hotspot", self.css_source)
        self.assertIn("#ta-param-sidebar .dp-sidebar-inner", self.css_source)
        self.assertIn(".ta-app .ta-row .ta-fx-badge", self.css_source)
        self.assertIn(".ta-app .ta-row.ta-koef-warning", self.css_source)
        self.assertIn(".ta-app .ta-row.ta-koef-error", self.css_source)
