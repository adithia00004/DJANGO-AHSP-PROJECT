import os
from pathlib import Path
from unittest import skipUnless

from django.test import SimpleTestCase


class SaveSyncUiRegressionGuardsTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        root = Path(__file__).resolve().parent
        static_js = root / "static" / "detail_project" / "js"
        cls.template_ahsp_js_source = (static_js / "template_ahsp.js").read_text(
            encoding="utf-8"
        )
        cls.harga_items_js_source = (static_js / "harga_items.js").read_text(
            encoding="utf-8"
        )

    def test_template_reload_acknowledges_pekerjaan_sync_led(self):
        self.assertIn(
            "function acknowledgePekerjaanSyncIfSettled()",
            self.template_ahsp_js_source,
        )
        self.assertIn("dp:sync-led-ack", self.template_ahsp_js_source)

    def test_template_auto_reloads_pending_jobs_on_open(self):
        source = self.template_ahsp_js_source
        self.assertIn(
            "function scheduleAutoReloadPendingJobs(reason = 'open')",
            source,
        )
        self.assertIn("scheduleAutoReloadPendingJobs('page-open');", source)
        self.assertIn("scheduleAutoReloadPendingJobs('source-change-sync');", source)
        self.assertIn("resolveReloadJob(id);", source)

    def test_template_active_header_uses_ascii_empty_placeholder(self):
        source = self.template_ahsp_js_source
        self.assertIn(
            "$('#ta-active-satuan').textContent = $('.satuan', li)?.textContent?.trim() || '-';",
            source,
        )
        self.assertIn("placeholder: 'Cari AHSP atau Pekerjaan...'", source)

    def _assert_token_not_actively_sent(self, source, label):
        for line in source.splitlines():
            if "payload.client_updated_at =" in line:
                self.assertTrue(
                    line.lstrip().startswith("//"),
                    f"{label}: client_updated_at tidak boleh dikirim aktif: {line!r}",
                )

    def test_template_save_is_last_save_wins_with_dormant_token(self):
        source = self.template_ahsp_js_source
        self._assert_token_not_actively_sent(source, "template_ahsp.js")
        self.assertIn("last-save-wins", source)
        self.assertIn("if (!js.ok && js.conflict)", source)

    def test_harga_save_is_last_save_wins_with_dormant_token(self):
        source = self.harga_items_js_source
        self._assert_token_not_actively_sent(source, "harga_items.js")
        self.assertIn("last-save-wins", source)
        self.assertIn("j.conflict", source)


@skipUnless(
    os.getenv("RUN_WIP_UI_GUARDS") == "1",
    "Guard Formula/Volume WIP hanya dijalankan bersama implementasi WIP lokal.",
)
class FormulaUiRegressionGuardsTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = Path(__file__).resolve().parent
        cls.js_path = (
            cls.root
            / "static"
            / "detail_project"
            / "js"
            / "volume_pekerjaan.js"
        )
        cls.export_manager_js_path = (
            cls.root
            / "static"
            / "detail_project"
            / "js"
            / "export"
            / "ExportManager.js"
        )
        cls.sync_led_js_path = (
            cls.root
            / "static"
            / "detail_project"
            / "js"
            / "sync_led.js"
        )
        cls.source_change_js_path = (
            cls.root
            / "static"
            / "detail_project"
            / "js"
            / "source_change_state.js"
        )
        cls.template_ahsp_js_path = (
            cls.root
            / "static"
            / "detail_project"
            / "js"
            / "template_ahsp.js"
        )
        cls.core_modal_js_path = (
            cls.root
            / "static"
            / "detail_project"
            / "js"
            / "core"
            / "modal.js"
        )
        cls.tpl_path = (
            cls.root
            / "templates"
            / "detail_project"
            / "volume_pekerjaan.html"
        )
        cls.js_source = cls.js_path.read_text(encoding="utf-8")
        cls.export_manager_js_source = cls.export_manager_js_path.read_text(encoding="utf-8")
        cls.sync_led_js_source = cls.sync_led_js_path.read_text(encoding="utf-8")
        cls.source_change_js_source = cls.source_change_js_path.read_text(encoding="utf-8")
        cls.template_ahsp_js_source = cls.template_ahsp_js_path.read_text(encoding="utf-8")
        cls.core_modal_js_source = cls.core_modal_js_path.read_text(encoding="utf-8")
        cls.harga_items_js_source = (
            cls.root / "static" / "detail_project" / "js" / "harga_items.js"
        ).read_text(encoding="utf-8")
        cls.tpl_source = cls.tpl_path.read_text(encoding="utf-8")

    def test_cursor_mapping_keeps_token_end_boundary(self):
        self.assertIn(
            "if (safePos === span.displayEnd) return span.rawEnd;",
            self.js_source,
        )
        self.assertIn(
            "if (safePos === span.rawEnd) return span.displayEnd;",
            self.js_source,
        )

    def test_autosave_block_does_not_force_focus(self):
        self.assertIn(
            "if (reason === 'manual') {",
            self.js_source,
        )
        self.assertIn(
            "suppressFormulaInputFocusOpen = true;",
            self.js_source,
        )
        self.assertIn(
            "input.focus();",
            self.js_source,
        )

    def test_autosave_queues_retry_while_save_in_flight(self):
        self.assertIn(
            "if (saving) {",
            self.js_source,
        )
        self.assertIn(
            "saveRetryRequested = true;",
            self.js_source,
        )
        self.assertIn(
            "if (saveRetryRequested) {",
            self.js_source,
        )
        self.assertIn(
            "scheduleAutosave(450);",
            self.js_source,
        )

    def test_autosave_defers_when_user_recently_typing_inline(self):
        self.assertIn(
            "const AUTOSAVE_TYPING_GRACE_MS = 900;",
            self.js_source,
        )
        self.assertIn(
            "lastQtyInputAt = Date.now();",
            self.js_source,
        )
        self.assertIn(
            "if (activeIsQtyInput && elapsedFromLastTyping < AUTOSAVE_TYPING_GRACE_MS) {",
            self.js_source,
        )

    def test_volume_autosave_default_interval_is_five_minutes(self):
        self.assertIn(
            "const DEFAULT_AUTOSAVE_MS = 5 * 60 * 1000;",
            self.js_source,
        )
        self.assertIn(
            "root.dataset.autosaveMs || DEFAULT_AUTOSAVE_MS",
            self.js_source,
        )

    def test_save_commit_uses_sent_snapshot_not_live_current_value(self):
        self.assertIn(
            "const sentQuantityById = {};",
            self.js_source,
        )
        self.assertIn(
            "originalValueById[id] = roundHalfUp(sentQty, STORE_PLACES);",
            self.js_source,
        )
        self.assertIn(
            "const stillDirty = dirtySet.has(id);",
            self.js_source,
        )

    def test_formula_state_snapshot_has_server_fallback_when_local_empty(self):
        self.assertIn(
            "if (!Object.keys(local).length) return server;",
            self.js_source,
        )

    def test_programmatic_focus_guard_exists(self):
        self.assertIn(
            "if (suppressFormulaInputFocusOpen) return;",
            self.js_source,
        )

    def test_editor_block_state_disables_apply_button(self):
        self.assertIn(
            "formulaEditorApplyBtn.disabled = formulaEditorHasBlockingError;",
            self.js_source,
        )

    def test_formula_mode_toggles_inputmode_for_mobile_keyboard(self):
        self.assertIn(
            "inputEl.setAttribute('inputmode', formulaMode ? 'text' : 'decimal');",
            self.js_source,
        )

    def test_fill_down_copies_raw_and_fx_state(self):
        self.assertIn(
            "rawInputById[id2] = sourceRaw;",
            self.js_source,
        )
        self.assertIn(
            "setFxState(id2, sourceFx);",
            self.js_source,
        )

    def test_suggestion_replaces_plain_keyword_query_without_redundant_tail(self):
        self.assertIn(
            "const keywordOnlyNoEq = noEqPrefix",
            self.js_source,
        )
        self.assertIn(
            ".test(displayValue.trim());",
            self.js_source,
        )
        self.assertIn(
            "setInputFormulaRaw(inputEl, `=${rawToken}`",
            self.js_source,
        )

    def test_formula_paste_support_resolves_label_aliases(self):
        self.assertIn(
            "function resolveDisplayFormulaAliases(rawExpr, scopeLabels = {}) {",
            self.js_source,
        )
        self.assertIn(
            "function insertPastedFormulaText(inputEl, pastedText, options = {}) {",
            self.js_source,
        )
        self.assertIn(
            "formulaEditorInputEl.addEventListener('paste', (ev) => {",
            self.js_source,
        )
        self.assertIn(
            "input && input.addEventListener('paste', (ev) => {",
            self.js_source,
        )

    def test_tutorial_link_is_not_empty(self):
        self.assertIn(
            'href="https://www.ahspkemenkeu.com/tutorial"',
            self.tpl_source,
        )

    def test_sidebar_has_parameter_formula_search_input(self):
        self.assertIn(
            'id="vp-sidebar-search"',
            self.tpl_source,
        )
        self.assertIn(
            'id="vp-sidebar-search-clear"',
            self.tpl_source,
        )

    def test_sidebar_search_filters_parameter_and_computed_tables(self):
        self.assertIn(
            "function matchesSidebarSearch(item = {}) {",
            self.js_source,
        )
        self.assertIn(
            "const filteredCodes = allCodes.filter((code) => matchesSidebarSearch({",
            self.js_source,
        )

    def test_formula_editor_has_computed_name_field(self):
        self.assertIn(
            'id="vp-fe-computed-name-wrap"',
            self.tpl_source,
        )
        self.assertIn(
            'id="vp-fe-computed-name"',
            self.tpl_source,
        )

    def test_cparam_edit_opens_modal_with_name_edit_enabled(self):
        self.assertIn(
            "openFormulaEditorForComputed(code, { enableNameEdit: true });",
            self.js_source,
        )
        self.assertIn(
            "formulaEditorContext.allowNameEdit",
            self.js_source,
        )

    def test_volume_modals_disable_bootstrap_backdrop_in_template(self):
        self.assertIn(
            'id="vpFormulaHelpModal"',
            self.tpl_source,
        )
        self.assertIn(
            'id="vpFormulaEditorModal"',
            self.tpl_source,
        )
        self.assertIn(
            'id="vpParamPaletteModal"',
            self.tpl_source,
        )
        self.assertIn(
            'data-bs-backdrop="false"',
            self.tpl_source,
        )

    def test_volume_page_installs_no_backdrop_enforcer(self):
        self.assertIn(
            "const VP_DISABLE_MODAL_BACKDROP = true;",
            self.js_source,
        )
        self.assertIn(
            "function installNoModalBackdropEnforcer() {",
            self.js_source,
        )
        self.assertIn(
            "installNoModalBackdropEnforcer();",
            self.js_source,
        )

    def test_core_modal_supports_volume_no_backdrop_mode(self):
        self.assertIn(
            "function isVolumePageNoBackdropMode() {",
            self.core_modal_js_source,
        )
        self.assertIn(
            "modalEl.setAttribute('data-bs-backdrop', noBackdrop ? 'false' : 'true');",
            self.core_modal_js_source,
        )

    def test_sync_led_supports_local_ack_event(self):
        self.assertIn(
            "window.addEventListener('dp:sync-led-ack', (event) => {",
            self.sync_led_js_source,
        )
        self.assertIn(
            "function acknowledgeLed(led, options = {}) {",
            self.sync_led_js_source,
        )

    def test_source_change_ack_survives_navigation_and_syncs_server_state(self):
        self.assertIn(
            "keepalive: true",
            self.source_change_js_source,
        )
        self.assertIn(
            "pending_reload_job_ids",
            self.source_change_js_source,
        )

    def test_template_reload_acknowledges_pekerjaan_sync_led(self):
        self.assertIn(
            "function acknowledgePekerjaanSyncIfSettled()",
            self.template_ahsp_js_source,
        )
        self.assertIn(
            "dp:sync-led-ack",
            self.template_ahsp_js_source,
        )

    def test_template_auto_reloads_pending_jobs_on_open(self):
        self.assertIn(
            "function scheduleAutoReloadPendingJobs(reason = 'open')",
            self.template_ahsp_js_source,
        )
        self.assertIn(
            "scheduleAutoReloadPendingJobs('page-open');",
            self.template_ahsp_js_source,
        )
        self.assertIn(
            "scheduleAutoReloadPendingJobs('source-change-sync');",
            self.template_ahsp_js_source,
        )
        self.assertIn(
            "resolveReloadJob(id);",
            self.template_ahsp_js_source,
        )

    def test_template_active_header_uses_ascii_empty_placeholder(self):
        self.assertIn(
            "$('#ta-active-satuan').textContent = $('.satuan', li)?.textContent?.trim() || '-';",
            self.template_ahsp_js_source,
        )
        self.assertIn(
            "placeholder: 'Cari AHSP atau Pekerjaan...'",
            self.template_ahsp_js_source,
        )

    def _assert_token_not_actively_sent(self, source, label):
        # POLICY single-user / last-save-wins: tiap assignment client_updated_at WAJIB dikomentari
        # (UI tidak memicu 409; handler konflik tetap ada sebagai kode dorman/reversibel).
        for line in source.splitlines():
            if "payload.client_updated_at =" in line:
                self.assertTrue(
                    line.lstrip().startswith("//"),
                    f"{label}: client_updated_at tidak boleh dikirim aktif (last-save-wins): {line!r}",
                )

    def test_template_save_is_last_save_wins_with_dormant_token(self):
        src = self.template_ahsp_js_source
        self._assert_token_not_actively_sent(src, "template_ahsp.js")
        self.assertIn("last-save-wins", src)
        # Handler konflik dipertahankan sebagai kode DORMAN (reversibel untuk multi-user).
        self.assertIn("if (!js.ok && js.conflict)", src)

    def test_harga_save_is_last_save_wins_with_dormant_token(self):
        src = self.harga_items_js_source
        self._assert_token_not_actively_sent(src, "harga_items.js")
        self.assertIn("last-save-wins", src)
        self.assertIn("j.conflict", src)

    def test_volume_save_acknowledges_global_sync_led(self):
        self.assertIn(
            "function acknowledgeGlobalSyncLed(flags = {}) {",
            self.js_source,
        )
        self.assertIn(
            "acknowledgeGlobalSyncLed({ volume: true });",
            self.js_source,
        )

    def test_modal_backdrop_cleanup_guard_exists(self):
        self.assertIn(
            "function cleanupOrphanModalBackdrops() {",
            self.js_source,
        )
        self.assertIn(
            "document.addEventListener('hidden.bs.modal', () => {",
            self.js_source,
        )
        self.assertIn(
            "paramPaletteModalEl.addEventListener('hidden.bs.modal', () => {",
            self.js_source,
        )

    def test_modal_backdrop_watchdog_exists(self):
        self.assertIn(
            "function installModalBackdropWatchdog() {",
            self.js_source,
        )
        self.assertIn(
            "document.addEventListener('pointerdown', checkAndClean, true);",
            self.js_source,
        )
        self.assertIn(
            "installModalBackdropWatchdog();",
            self.js_source,
        )

    def test_formula_editor_dirty_state_updates_backdrop_mode(self):
        self.assertIn(
            "function setFormulaEditorBackdropState(isStatic)",
            self.js_source,
        )
        self.assertIn(
            "setFormulaEditorBackdropState(isDirty);",
            self.js_source,
        )

    def test_csv_export_includes_computed_section(self):
        self.assertIn(
            "function csvFromVarsAndComputed(varsObj, labelsObj, computedObj = {})",
            self.js_source,
        )
        self.assertIn(
            "# Computed Parameters",
            self.js_source,
        )

    def test_xlsx_export_includes_computed_sheet(self):
        self.assertIn(
            "XLSX.utils.book_append_sheet(wb, wsComputed, 'Computed Parameter');",
            self.js_source,
        )

    def test_confirm_modal_has_native_browser_fallback(self):
        self.assertIn(
            "if (typeof window.confirm === 'function') {",
            self.js_source,
        )

    def test_volume_export_has_async_to_sync_fallback(self):
        self.assertIn(
            "allowSyncFallback: true,",
            self.js_source,
        )
        self.assertIn(
            "const asyncOk = await exporter.exportAsAsync(format, options);",
            self.js_source,
        )
        self.assertIn(
            "if (asyncOk === false) {",
            self.js_source,
        )
        self.assertIn(
            "await exporter.exportAs(format, options);",
            self.js_source,
        )

    def test_export_manager_async_uses_timeout_fetch_guard(self):
        self.assertIn(
            "const startResponse = await this._fetchWithTimeout(asyncUrl, {",
            self.export_manager_js_source,
        )
        self.assertIn(
            "async _fetchWithTimeout(url, options = {}, timeoutMs = 15000)",
            self.export_manager_js_source,
        )

    def test_summary_bar_targets_current_html_counter_ids(self):
        self.assertIn(
            "all: 'vp-stat-total',",
            self.js_source,
        )
        self.assertIn(
            "filled: 'vp-stat-filled',",
            self.js_source,
        )
        self.assertIn(
            "empty: 'vp-stat-empty',",
            self.js_source,
        )
        self.assertIn(
            "formula: 'vp-stat-formula',",
            self.js_source,
        )

    def test_summary_bar_treats_formula_rows_as_filled_by_raw_expression(self):
        self.assertIn(
            "const isFilled = hasFormula ? (rawVal.length > 0) : (displayVal.length > 0);",
            self.js_source,
        )

    def test_summary_bar_resync_called_after_prefill_and_input_change(self):
        self.assertIn(
            "syncSummaryBarWithCurrentFilter();",
            self.js_source,
        )
