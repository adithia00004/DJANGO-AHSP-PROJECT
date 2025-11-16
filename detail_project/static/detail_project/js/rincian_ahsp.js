/**
 * @file rincian_ahsp.js - Rincian AHSP Detail Module
 * @description Two-panel layout: left panel shows pekerjaan list, right panel shows detail AHSP items
 *
 * @features
 * - TIER 1 (Critical): Backend validation for override BUK (0-100%), cache invalidation
 * - TIER 2 (High UX): Toast notifications, reactive Grand Total, toolbar alignment
 * - TIER 3 (Polish): Keyboard navigation (Ctrl+K, Shift+O, Arrow keys), granular loading states, improved resizer
 *
 * @architecture
 * - IIFE pattern for encapsulation
 * - Fetch API with AbortController for request cancellation
 * - Map-based caching for detail data
 * - DocumentFragment for efficient DOM updates
 * - Token-based race condition prevention (selectToken)
 *
 * @performance
 * - Granular loading states (list/detail/global) for non-blocking UI
 * - Cached detail data to avoid redundant fetches
 * - Debounced search (120ms) to prevent excessive renders
 * - RequestAnimationFrame for smooth resizer dragging
 *
 * @accessibility
 * - ARIA attributes (role="option", tabindex) for keyboard navigation
 * - Screen reader friendly error messages
 * - Keyboard shortcuts with visual feedback
 * - Resizer opacity improved for low vision users
 *
 * @dependencies
 * - Bootstrap 5 (modals, icons)
 * - ExportManager (optional, for CSV/PDF/Word export)
 * - DP.core.toast (optional, fallback to inline implementation)
 *
 * @author Claude (AI Assistant)
 * @version TIER 3 Complete
 * @tested 22 test cases (pytest detail_project/tests/test_rincian_ahsp.py)
 */
(function(){
  const ROOT = document.getElementById('rekap-app');
  if (!ROOT) return;
  const projectId = Number(ROOT.dataset.projectId || '0');

  // ====== TIER 4: Constants (extracted magic numbers) ======
  const CONSTANTS = {
    // Formatting
    CURRENCY_DECIMAL_PLACES: 2,
    KOEFISIEN_DECIMAL_PLACES: 6,

    // Timing (milliseconds)
    SEARCH_DEBOUNCE_MS: 120,
    MODAL_FOCUS_DELAY_MS: 300,
    TOAST_DURATION_ERROR_MS: 8000,
    TOAST_DURATION_DEFAULT_MS: 5000,
    TOAST_DURATION_SHORT_MS: 2000,

    // UI States
    LOADING_OPACITY: 0.6,

    // Resizer
    RESIZER_MIN_WIDTH_PX: 240,
    RESIZER_MAX_WIDTH_PX: 640,
    RESIZER_DEFAULT_WIDTH_PX: 360,
    RESIZER_KEYBOARD_STEP_PX: 10,
    RESIZER_KEYBOARD_STEP_SHIFT_PX: 20,

    // Validation
    BUK_MIN_PERCENT: 0,
    BUK_MAX_PERCENT: 100,
  };

  // ====== Intl & endpoints ======
  const locale = ROOT.dataset.locale || 'id-ID';
  const fmtRp = new Intl.NumberFormat(locale, {
    style: 'currency', currency: 'IDR',
    minimumFractionDigits: CONSTANTS.CURRENCY_DECIMAL_PLACES,
    maximumFractionDigits: CONSTANTS.CURRENCY_DECIMAL_PLACES
  });

  const EP_REKAP    = ROOT.dataset.epRekap;
  const EP_PRICING  = ROOT.dataset.epPricing;
  const EP_DET_PREF = ROOT.dataset.epDetailPrefix;      // ex: ".../detail-ahsp/0/"
  const EP_POV_PREF = ROOT.dataset.epPricingItemPrefix; // ex: ".../pekerjaan/0/pricing/"

  // ====== URL helpers ======
  /**
   * Replace placeholder ID (0) in URL template with actual ID
   * @param {string} url - URL template with /0/ placeholder
   * @param {number|string} id - Pekerjaan ID to substitute
   * @returns {string} URL with ID substituted
   * @throws {Error} If ID is invalid (null, 0, or negative)
   * @example substId("/api/detail/0/", 123) => "/api/detail/123/"
   */
  function substId(url, id) {
    const n = Number(id);
    if (!n || n <= 0) throw new Error('invalid pekerjaan id');
    const clean = String(url || '').trim();
    return clean.replace(/\/0(?=\/|$)/, `/${n}`);
  }

  /**
   * Generate URL for fetching detail AHSP items for a pekerjaan
   * @param {number} id - Pekerjaan ID
   * @returns {string} Detail endpoint URL
   */
  const urlDetail      = (id) => substId(EP_DET_PREF, id);

  /**
   * Generate URL for fetching/updating pricing data for a pekerjaan
   * @param {number} id - Pekerjaan ID
   * @returns {string} Pricing endpoint URL
   */
  const urlPricingItem = (id) => substId(EP_POV_PREF, id);

  // ====== DOM refs ======
  const $grid     = ROOT.querySelector('.ra-body'); // grid container - independent dari Template AHSP
  // Toolbar
  const $badgeBUK = ROOT.querySelector('#rk-badge-buk');
  const $search   = ROOT.querySelector('#ra-job-search'); // Updated: rk-search → ra-job-search
  const $grand    = ROOT.querySelector('#rk-grand');
  // Sidebar
  const $list     = ROOT.querySelector('#rk-list');
  // Kanan (header)
  const $kode     = ROOT.querySelector('#rk-pkj-kode');
  const $uraian   = ROOT.querySelector('#rk-pkj-uraian');
  const $sat      = ROOT.querySelector('#rk-pkj-sat');
  const $src      = ROOT.querySelector('#rk-pkj-source');
  const $ovrChip  = ROOT.querySelector('#rk-pkj-ovr-chip');
  const $eff      = ROOT.querySelector('#rk-eff');
  const $ovrInput = ROOT.querySelector('#rk-ovr-input');
  const $ovrApply = ROOT.querySelector('#rk-ovr-apply');
  const $ovrClear = ROOT.querySelector('#rk-ovr-clear');
  // Modal override controls (simple modal UI)
  const $modalInput = ROOT.querySelector('#ovr-buk-custom');
  const $modalApply = ROOT.querySelector('#ovr-apply-btn');
  const $modalClear = ROOT.querySelector('#ovr-clear-btn');
  // Kanan (tabel)
  const $tbody    = ROOT.querySelector('#rk-tbody-detail');
  // Resizer
  const $resizer  = ROOT.querySelector('.rk-resizer');
  const $leftPane = ROOT.querySelector('.rk-left');
  // Toast
  const $toast    = ROOT.querySelector('#rk-toast');
  const volumeAlertEl = document.getElementById('rk-volume-alert');
  const sourceChange = window.DP?.sourceChange || null;


  // ====== state ======
  let ctrlDetail = null, ctrlPricing = null; // AbortControllers
  let rows = [];
  let filtered = [];
  let selectedId = null;
  let projectBUK = 10.00;
  let projectPPN = 0.00;
  const cacheDetail = new Map();
  let selectToken = 0;
  let pendingVolumeJobs = new Set(
    sourceChange && projectId ? sourceChange.listVolumeJobs(projectId) : [],
  );

  // ====== utils ======
  /**
   * Escape HTML special characters to prevent XSS
   * @param {string} s - String to escape
   * @returns {string} HTML-safe string
   */
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, m => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[m]));

  /**
   * Parse numeric input with robust handling of Indonesian/international formats
   * Supports: "1.234,56", "1,234.56", "1234.56", "1234,56"
   * Mirrors backend parse_any() logic for consistency
   * @param {string|number} x - Input value (string with formatting or number)
   * @returns {number} Parsed number (always >= 0, defaults to 0 on invalid input)
   * @example parseNum("1.234,56") => 1234.56
   * @example parseNum("1,234.56") => 1234.56
   * @example parseNum("-100") => 0 (negatives rejected)
   */
  function parseNum(x){
    if (x == null) return 0;
    let s = String(x).trim();
    if (!s) return 0;
    s = s.replace(/_/g,'');
    const hasComma = s.includes(',');
    const hasDot   = s.includes('.');
    if (hasComma && hasDot){
      const lastComma = s.lastIndexOf(',');
      const lastDot   = s.lastIndexOf('.');
      if (lastComma > lastDot){
        const fracLen = s.length - lastComma - 1;
        if (fracLen === 3){ s = s.replace(/,/g,''); }
        else { s = s.replace(/\./g,'').replace(',', '.'); }
      } else {
        const fracLen = s.length - lastDot - 1;
        if (fracLen === 3){ s = s.replace(/\./g,'').replace(',', '.'); }
        else { s = s.replace(/,/g,''); }
      }
    } else {
      if (!hasDot && (s.match(/,/g)||[]).length === 1){ s = s.replace(',', '.'); }
      else if (!hasComma && (s.match(/\./g)||[]).length === 1){ /* ok */ }
      else { s = s.replace(/\./g,'').replace(',', '.'); }
    }
    const n = Number(s);
    return Number.isFinite(n) && n >= 0 ? n : 0;
  }
  const num = parseNum;

  /**
   * Format number as Indonesian Rupiah currency
   * @param {number|string} x - Amount to format
   * @returns {string} Formatted currency string (e.g., "Rp 1.234,56")
   */
  const fmt = (x) => fmtRp.format(num(x));

  /**
   * Get CSRF token from cookies for POST requests
   * @returns {string} CSRF token value or empty string
   */
  const csrf = () => (document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)?.[1] || '');

  // ====== UI polish: icons/classes/placeholder alignment ======
  /**
   * Apply initial UI fixes and icon standardization on page load
   * - Ensures consistent chip styling
   * - Updates icons to filled variants
   * - Sets initial placeholder text
   * - Fixes loading text punctuation
   * @private
   */
  function applyIconAndUIFixes(){
    // Ensure chips use consistent styles
    const srcChip = ROOT.querySelector('#rk-pkj-source');
    srcChip?.classList.add('ux-chip','ux-mono','mono');
    // Update icons to consistent variants
    const effIcon = ROOT.querySelector('#rk-eff i');
    if (effIcon && effIcon.classList.contains('bi-lightning-charge')){
      effIcon.classList.remove('bi-lightning-charge');
      effIcon.classList.add('bi-lightning-charge-fill');
    }
    const ovrIcon = ROOT.querySelector('#rk-pkj-ovr-chip i');
    if (ovrIcon && ovrIcon.classList.contains('bi-sliders')){
      ovrIcon.classList.remove('bi-sliders');
      ovrIcon.classList.add('bi-sliders2');
    }
    // Table header style
    ROOT.querySelector('#ra-table')?.classList.add('ux-thead');
    // Initial placeholders clean
    if ($kode)   $kode.textContent = $kode.textContent && $kode.textContent.trim() ? $kode.textContent : '-';
    if ($sat)    $sat.textContent  = $sat.textContent  && $sat.textContent.trim()  ? $sat.textContent  : '-';
    if ($src)    $src.textContent  = $src.textContent  && $src.textContent.trim()  ? $src.textContent  : '-';
    if ($eff && !$eff.textContent.includes('%')) $eff.textContent = 'Profit: -%';
    // Loading note punctuation
    const rowNote = ROOT.querySelector('.ra-job-list .row-note, .ta-job-list .row-note');
    if (rowNote && /Memuat/.test(rowNote.textContent||'')) rowNote.textContent = 'Memuat…';
  }

  /**
   * Parse percentage input from UI (supports Indonesian decimal format)
   * Removes whitespace, trailing % signs, converts comma to dot
   * @param {string|null} s - Raw input string (e.g., "12,5%", "12.5", "12,500")
   * @returns {number|null} Parsed percentage value or null if invalid
   * @example parsePctUI("12,5%") => 12.5
   * @example parsePctUI("12.500,5") => 12500.5
   * @example parsePctUI("") => null
   */
  function parsePctUI(s){
    if (s == null) return null;
    s = String(s).trim().replace(/\s+/g,'');
    s = s.replace(/%+$/,'');
    if (s === '') return null;
    s = s.replace(/\./g,'').replace(',', '.'); // "12.500,5" -> "12500.5"
    const v = Number(s);
    return Number.isFinite(v) ? v : null;
  }

  /**
   * Enable or disable override BUK controls
   * Updates disabled state and placeholder text for inline/modal inputs
   * @param {boolean} enabled - Whether override controls should be enabled
   */
  function setOverrideUIEnabled(enabled){
    [$ovrInput, $ovrApply, $ovrClear].forEach(el => { if (el) el.disabled = !enabled; });
    if (!enabled && $ovrChip) $ovrChip.hidden = true;
    if ($ovrInput) $ovrInput.placeholder = enabled ? "Override %" : "Override tidak tersedia";
  }

  // Toast notification - aligned with Template AHSP pattern
  /**
   * Show toast notification with auto-dismiss
   * @param {string} msg - Message to display
   * @param {string} type - Type: 'success', 'error', 'warning', 'info'
   * @param {number} delay - Auto-dismiss delay in ms (default: based on type)
   */
  function showToast(msg, type = 'info', delay = null) {
    console.log(`[TOAST ${type.toUpperCase()}] ${msg}`);

    // Use global DP.core.toast if available (with correct z-index)
    if (window.DP && window.DP.core && window.DP.core.toast) {
      const defaultDelay = type === 'error' ? CONSTANTS.TOAST_DURATION_ERROR_MS : CONSTANTS.TOAST_DURATION_DEFAULT_MS;
      window.DP.core.toast.show(msg, type, delay || defaultDelay);
      return;
    }

    // Fallback to inline implementation
    if (!$toast) { console.log(`[${type}]`, msg); return; }

    const config = {
      success: { icon: 'bi-check-circle-fill', bg: '#28a745', color: '#fff' },
      error: { icon: 'bi-x-circle-fill', bg: '#dc3545', color: '#fff' },
      warning: { icon: 'bi-exclamation-triangle-fill', bg: '#ffc107', color: '#000' },
      info: { icon: 'bi-info-circle-fill', bg: '#17a2b8', color: '#fff' }
    };
    const cfg = config[type] || config.info;

    const div = document.createElement('div');
    div.className = `rk-toast rk-toast-${type}`;
    div.style.cssText = `
      background: ${cfg.bg};
      color: ${cfg.color};
      padding: 12px 16px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 10px;
      animation: slideInRight 0.3s ease-out;
      font-size: 14px;
      line-height: 1.4;
      min-width: 300px;
      max-width: 500px;
    `;
    div.innerHTML = `
      <i class="bi ${cfg.icon}" style="font-size: 20px; flex-shrink: 0;"></i>
      <span style="flex: 1; white-space: pre-wrap;">${esc(msg)}</span>
      <button type="button" style="
        background: none;
        border: none;
        color: inherit;
        font-size: 24px;
        line-height: 1;
        cursor: pointer;
        padding: 0;
        opacity: 0.7;
        flex-shrink: 0;
      " aria-label="Close">&times;</button>
    `;

    const closeBtn = div.querySelector('button');
    closeBtn.addEventListener('click', () => {
      div.style.animation = 'slideOutRight 0.3s ease-in';
      setTimeout(() => div.remove(), 300);
    });

    // Auto-dismiss (error stays longer)
    const defaultDelay = type === 'error' ? CONSTANTS.TOAST_DURATION_ERROR_MS : CONSTANTS.TOAST_DURATION_DEFAULT_MS;
    const duration = delay || defaultDelay;
    setTimeout(() => {
      if (div.parentNode) {
        div.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => div.remove(), 300);
      }
    }, duration);

    $toast.appendChild(div);
  }

  // Add animations via <style> if not exists
  if (!document.getElementById('rk-toast-animations')) {
    const style = document.createElement('style');
    style.id = 'rk-toast-animations';
    style.textContent = `
      @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
      }
    `;
    document.head.appendChild(style);
  }

  // ====== TIER 3: Granular Loading States ======
  /**
   * Show/hide loading state for specific UI scope (TIER 3 feature)
   * Allows independent loading indicators for list and detail panels
   * @param {boolean} on - Whether to show (true) or hide (false) loading state
   * @param {'global'|'list'|'detail'} scope - Which UI scope to affect:
   *   - 'global': Entire page (legacy, blocks all interaction)
   *   - 'list': Job list panel only (opacity 0.6, pointer-events: none)
   *   - 'detail': Detail panel only (opacity 0.6, pointer-events: none)
   * @example setLoading(true, 'list') // Show loading for list panel only
   * @example setLoading(false, 'detail') // Hide loading for detail panel
   */
  function setLoading(on, scope = 'global') {
    if (scope === 'global') {
      ROOT.classList.toggle('is-loading', !!on);
    } else if (scope === 'list') {
      if ($list) {
        $list.classList.toggle('is-loading', !!on);
        if (on) {
          $list.style.opacity = String(CONSTANTS.LOADING_OPACITY);
          $list.style.pointerEvents = 'none';
        } else {
          $list.style.opacity = '';
          $list.style.pointerEvents = '';
        }
      }
    } else if (scope === 'detail') {
      const $editor = ROOT.querySelector('.ra-editor');
      if ($editor) {
        $editor.classList.toggle('is-loading', !!on);
        if (on) {
          $editor.style.opacity = String(CONSTANTS.LOADING_OPACITY);
          $editor.style.pointerEvents = 'none';
        } else {
          $editor.style.opacity = '';
          $editor.style.pointerEvents = '';
        }
      }
    }
  }

  /**
   * Safely parse JSON response with content-type validation
   * Prevents errors when server returns HTML error pages instead of JSON
   * @param {Response} r - Fetch API Response object
   * @returns {Promise<Object>} Parsed JSON data
   * @throws {Error} If response is not JSON or parsing fails
   * @private
   */
  async function safeJson(r) {
    const ct = (r.headers.get('content-type') || '').toLowerCase();
    if (!ct.includes('application/json')) {
      const text = await r.text().catch(()=> '');
      throw new Error(`Non-JSON response (${r.status}): ${text.slice(0,120)}`);
    }
    return r.json();
  }

  // ====== server calls ======
  /**
   * Fetch project-level BUK (Profit/Margin) percentage from server
   * Updates global projectBUK state and toolbar badge display
   * @returns {Promise<void>}
   * @throws {Error} If API call fails or response is invalid
   */
  async function loadProjectBUK(){
    const r = await fetch(EP_PRICING, { credentials:'same-origin' });
    const j = await safeJson(r);
    if (!r.ok || !j.ok) throw new Error('pricing fail');
    projectBUK = Number(j.markup_percent);
    if ($badgeBUK) $badgeBUK.textContent = `Profit/Margin (BUK): ${j.markup_percent}%`;
  }

  /**
   * Load rekap (summary) data for all pekerjaan in project
   * Fetches job list with aggregated costs, renders list, updates Grand Total
   * Restores last selected job from localStorage if available
   * @returns {Promise<void>}
   * @throws {Error} If API call fails
   * @performance Uses granular loading (list scope only) to avoid blocking detail panel
   */
  async function loadRekap(){
    setLoading(true, 'list'); // TIER 3: Granular loading for list only
    try{
      if ($list) $list.innerHTML = `<li class="rk-item"><div class="row-note">Memuat…</div></li>`;
      const r = await fetch(EP_REKAP, { credentials:'same-origin' });
      const j = await safeJson(r);
      if (!r.ok || !j.ok) throw new Error('rekap fail');
      rows = j.rows || [];
      try { projectPPN = Number(j.meta?.ppn_percent ?? 0); } catch { projectPPN = 0; }
      renderList();
      updateGrandTotalFromRekap();

      const last = localStorage.getItem('rk-last-pkj-id');
      const firstId = filtered[0]?.pekerjaan_id;
      const target = (last && rows.some(x => String(x.pekerjaan_id)===last)) ? Number(last) : firstId;
      if (selectedId == null && target) selectItem(target);
    } finally {
      setLoading(false, 'list'); // TIER 3: Clear list loading
    }
  }

  /**
   * Fetch detail AHSP items for a specific pekerjaan
   * Aborts previous pending request to prevent race conditions
   * Caches result in memory for faster subsequent access
   * @param {number} id - Pekerjaan ID
   * @returns {Promise<Object>} Detail data with items array and pekerjaan metadata
   * @throws {Error} If API call fails or is aborted
   * @performance Uses AbortController to cancel stale requests
   * @performance Caches results in Map for instant re-selection
   */
  async function fetchDetail(id){
    ctrlDetail?.abort();
    ctrlDetail = new AbortController();
    const r = await fetch(urlDetail(id), { credentials:'same-origin', signal: ctrlDetail.signal });
    const j = await safeJson(r);
    if (!r.ok || !j.ok) throw new Error('detail fail');
    cacheDetail.set(id, j);
    return j;
  }

  /**
   * Fetch pricing data (effective and override BUK) for a specific pekerjaan
   * Aborts previous pending request to prevent race conditions
   * @param {number} id - Pekerjaan ID
   * @returns {Promise<Object>} Pricing data with project_markup, override_markup, effective_markup
   * @throws {Error} If API call fails, endpoint not configured, or is aborted
   * @performance Uses AbortController to cancel stale requests
   */
  async function getPricingItem(id){
    if (!EP_POV_PREF) throw new Error('pricing item endpoint not provided');
    ctrlPricing?.abort();
    ctrlPricing = new AbortController();
    const r = await fetch(urlPricingItem(id), { credentials:'same-origin', signal: ctrlPricing.signal });
    const j = await safeJson(r);
    if (!r.ok || !j.ok) throw new Error('pricing item fail');
    return j;
  }

  /**
   * Save or clear override BUK (Profit/Margin) for a specific pekerjaan
   * Sends POST request with override value or null to reset to project default
   * @param {number} id - Pekerjaan ID
   * @param {number|string|null} rawOrNull - Override percentage value (e.g., 15.5) or null to clear
   * @returns {Promise<Object>} Updated pricing data with saved override
   * @throws {Error} If API call fails, endpoint not configured, or validation fails
   * @tier1 Backend performs validation: range 0-100%, clear error messages (TIER 1 FIX)
   * @example saveOverride(123, 15.5) // Set override to 15.5%
   * @example saveOverride(123, null) // Clear override, use project default
   */
  async function saveOverride(id, rawOrNull){
    if (!EP_POV_PREF) throw new Error('pricing item endpoint not provided');
    const payload = (rawOrNull==null || rawOrNull==='') ? { override_markup: null }
                                                        : { override_markup: String(rawOrNull).replace('.',',') };
    const r = await fetch(urlPricingItem(id), {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRFToken': csrf()},
      body: JSON.stringify(payload)
    });
    const j = await safeJson(r);
    if (!r.ok || !j.ok) throw new Error('save override fail');
    return j;
  }

  // ====== kiri: list pekerjaan ======
  /**
   * Render job list in left panel with filtering and override indicators
   * Applies search filter, calculates totals with effective BUK, shows override chips
   * Updates DOM and applies keyboard navigation attributes (TIER 3)
   * @performance Uses DocumentFragment for efficient DOM updates
   * @tier3 Calls makeJobItemsFocusable() for keyboard navigation support
   */
  function renderList(){
    const q = ($search?.value || '').toLowerCase().trim();
    filtered = !q ? rows.slice() : rows.filter(r =>
      (r.kode || '').toLowerCase().includes(q) ||
      (r.uraian || '').toLowerCase().includes(q)
    );

    if (!filtered.length){
      if ($list) $list.innerHTML = `<li class="rk-item"><div class="row-note">Tidak ada hasil.</div></li>`;
      return;
    }

    const fr = document.createDocumentFragment();
    filtered.forEach(r => {
      const A = num(r.A), B = num(r.B), C = num(r.C), L = num(r.LAIN || 0);
      const E = A + B + C + L;
      const bukEff = (r.markup_eff != null ? Number(r.markup_eff) : projectBUK);
      const F = E * (bukEff/100);
      const G = E + F;
      // BUG FIX #1: Display G (HSP per satuan) instead of total (G × volume)

      const li = document.createElement('li');
      const needsVolumeUpdate = pendingVolumeJobs.has(Number(r.pekerjaan_id));
      li.className = 'rk-item' + (needsVolumeUpdate ? ' rk-item-volume' : '');
      li.dataset.id = r.pekerjaan_id;
      li.innerHTML = `
        <div class="rk-item-title">${esc(r.uraian || '')}</div>
        <div class="rk-item-meta">
          <span class="mono">${esc(r.kode || '')}</span>
          ${Math.abs(bukEff - projectBUK) > 1e-6 ? `<span class="rk-chip rk-chip-warn mono">${bukEff.toFixed(2)}%</span>` : ''}
          <span class="rk-chip mono">${esc(r.satuan || '')}</span>
          <span class="row-note">HSP:</span><span class="mono">${fmt(G)}</span>
          ${needsVolumeUpdate ? '<span class="rk-volume-pill">Perlu update volume</span>' : ''}
        </div>
      `;
      li.addEventListener('click', () => selectItem(r.pekerjaan_id));
      fr.appendChild(li);
    });

    if ($list){
      $list.innerHTML = '';
      $list.appendChild(fr);
    }

    highlightActive();
    updateVolumeAlertForSelection(selectedId);
  }

  /**
   * Highlight currently selected job item in list
   * Adds/removes 'active' class based on selectedId
   */
  function highlightActive(){
    if (!$list) return;
    const items = $list.querySelectorAll('.rk-item');
    items.forEach(el => el.classList.toggle('active', String(el.dataset.id) === String(selectedId)));
  }


  /**
   * Calculate and display Grand Total for entire project (not filtered)
   * Formula: Grand Total = D + (D × PPN%)
   * where D = sum of all pekerjaan totals (with effective BUK)
   * Updates toolbar Grand Total display
   */
  function updateGrandTotalFromRekap(){
    if (!$grand) return;
    try{
      let D = 0;
      for (const r of (rows || [])){
        D += num(r.total);
      }
      const grand = D + (D * (Number(projectPPN||0)/100));
      $grand.textContent = `Grand Total: ${fmt(grand)}`;
    }catch{
      $grand.textContent = `Grand Total: ${fmt(0)}`;
    }
  }

  if (projectId && sourceChange) {
    window.addEventListener('dp:source-change', (event) => {
      const detail = event.detail || {};
      if (Number(detail.projectId) !== projectId) return;
      if (detail.state && detail.state.volume) {
        pendingVolumeJobs = new Set(
          Object.keys(detail.state.volume).map((key) => Number(key)).filter((id) => Number.isFinite(id)),
        );
        renderList();
        if (selectedId) {
          updateVolumeAlertForSelection(selectedId);
        }
      }
    });
  }

  // ====== kanan: detail satu pekerjaan ======
  /**
   * Select a pekerjaan and load its detail in right panel
   * Fetches pricing (override BUK) and detail AHSP items, renders detail table
   * Saves selection to localStorage for persistence across refreshes
   * @param {number} id - Pekerjaan ID to select
   * @returns {Promise<void>}
   * @performance Uses selectToken to prevent race conditions when rapid clicking
   * @performance Uses cached detail if available to avoid re-fetching
   * @tier3 Uses granular loading (detail scope only) to keep list interactive
   */
  async function selectItem(id){
    if (!id || Number(id) <= 0) { console.warn('skip selectItem invalid id:', id); return; }
    selectedId = id;
    localStorage.setItem('rk-last-pkj-id', String(id));
    highlightActive();
    updateVolumeAlertForSelection(id);
    const myToken = ++selectToken;

    setLoading(true, 'detail'); // TIER 3: Granular loading for detail panel only
    try{
      // header awal dari rows
      const r = rows.find(x => x.pekerjaan_id === id);
      if ($kode)   $kode.textContent   = r?.kode   || '—';
      if ($uraian) $uraian.textContent = r?.uraian || '—';
      if ($sat)    $sat.textContent    = r?.satuan || '—';

      // pricing item (optional)
      let effPct = projectBUK;
      if (!EP_POV_PREF) {
        setOverrideUIEnabled(false);
        if ($eff) $eff.textContent = `Profit: ${projectBUK.toFixed(2)}%`;
      } else {
        setOverrideUIEnabled(true);
        try{
          const pp = await getPricingItem(id);
          if (myToken !== selectToken) return;
          effPct = Number(pp.effective_markup);
          if ($ovrInput) $ovrInput.value = (pp.override_markup ?? '');
          if ($ovrChip)  $ovrChip.hidden = !(pp.override_markup != null);
          if ($eff)      $eff.textContent = `Profit: ${pp.effective_markup}%`;
          if ($modalInput) $modalInput.value = (pp.override_markup ?? ''); // Sync modal input
        }catch{
          if (myToken !== selectToken) return;
          if ($ovrInput) $ovrInput.value = '';
          if ($ovrChip)  $ovrChip.hidden = true;
          if ($eff)      $eff.textContent = `Profit: ${projectBUK.toFixed(2)}%`;
          if ($modalInput) $modalInput.value = '';
        }
      }

      // detail
      let detail = cacheDetail.get(id);
      if (!detail){
        detail = await fetchDetail(id);
      }
      if (myToken !== selectToken) return;

      const items = detail.items || [];
      renderDetailTable(items, effPct);
      if ($src) $src.textContent = (detail.pekerjaan?.source_type || '—').toUpperCase();
    } finally {
      setLoading(false, 'detail'); // TIER 3: Clear detail loading
    }
  }

  /**
   * Render detail AHSP table with items grouped by category (TK, BHN, ALT, LAIN)
   * Calculates subtotals per category and totals E, F, G with effective BUK
   * Formula: E = A+B+C+D, F = E × (effPct/100), G = E + F
   * @param {Array<Object>} items - Detail AHSP items with kategori, uraian, koefisien, harga_satuan
   * @param {number} effPct - Effective BUK percentage to apply (may be project or override)
   * @performance Uses DocumentFragment for efficient DOM updates
   */
  function renderDetailTable(items, effPct){
    if (!$tbody) return;
    const group = {TK:[],BHN:[],ALT:[],LAIN:[]};
    for (const it of items){
      const k = (it.kategori || '').toUpperCase();
      if (group[k]) group[k].push(it);
    }

    const fr = document.createDocumentFragment();
    let no = 1;

    function addSec(title, arr){
      const trh = document.createElement('tr');
      trh.className='sec-head';
      trh.innerHTML = `<td colspan="7">${esc(title)}</td>`;
      fr.appendChild(trh);

      let subtotal = 0;
      arr.forEach((it) => {
        const kf = num(it.koefisien);
        const hr = num(it.harga_satuan);
        const jm = kf * hr;
        subtotal += jm;
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="mono">${no++}</td>
          <td>${esc(it.uraian || '')}</td>
          <td class="mono">${esc(it.kode || '')}</td>
          <td class="mono">${esc(it.satuan || '')}</td>
          <td class="mono">${kf.toLocaleString(locale,{minimumFractionDigits:CONSTANTS.KOEFISIEN_DECIMAL_PLACES, maximumFractionDigits:CONSTANTS.KOEFISIEN_DECIMAL_PLACES})}</td>
          <td class="mono">${fmt(hr)}</td>
          <td class="mono">${fmt(jm)}</td>
        `;
        fr.appendChild(tr);
      });

      const trs = document.createElement('tr');
      trs.className='sec-sum';
      trs.innerHTML = `<td colspan="6">Subtotal ${esc(title.split('—')[0].trim())}</td><td class="mono">${fmt(subtotal)}</td>`;
      fr.appendChild(trs);
      return subtotal;
    }

    $tbody.innerHTML = '';
    const sA = addSec('A — Tenaga Kerja', group.TK);
    const sB = addSec('B — Bahan',        group.BHN);
    const sC = addSec('C — Peralatan',    group.ALT);
    const sD = addSec('D — Lainnya',      group.LAIN);

    const E = sA+sB+sC+sD;
    const F = E * (num(effPct)/100);
    const G = E + F;

    const tre = document.createElement('tr');
    tre.className='tot-row';
    tre.innerHTML = `<td colspan="6">E — Jumlah (A+B+C+D)</td><td class="mono">${fmt(E)}</td>`;
    const trf = document.createElement('tr');
    trf.className='tot-row';
    trf.innerHTML = `<td colspan="6">F — Profit/Margin × E</td><td class="mono">${fmt(F)}</td>`;
    const trg = document.createElement('tr');
    trg.className='tot-row';
    trg.innerHTML = `<td colspan="6">G — HSP = E + F</td><td class="mono">${fmt(G)}</td>`;

    fr.appendChild(tre); fr.appendChild(trf); fr.appendChild(trg);
    $tbody.appendChild(fr);
  }

  // ====== events ======
  /**
   * Debounce function calls to limit execution frequency
   * Useful for expensive operations triggered by rapid events (e.g., search input)
   * @param {Function} fn - Function to debounce
   * @param {number} ms - Delay in milliseconds
   * @returns {Function} Debounced function
   * @example const debouncedSearch = debounce(search, 300)
   */
  function debounce(fn, ms){ let t; return (...args)=>{ clearTimeout(t); t=setTimeout(()=>fn(...args), ms); }; }
  if ($search) {
    $search.addEventListener('input', debounce(() => {
      renderList();
      highlightActive();
    }, CONSTANTS.SEARCH_DEBOUNCE_MS));
  }

  // REMOVED: Inline override controls (deprecated - use modal only to avoid duplication)

  // Modal Apply handler - TIER 1 & 2 FIX
  if ($modalApply) {
    $modalApply.addEventListener('click', async () => {
      if (selectedId == null) {
        showToast('⚠️ Pilih pekerjaan terlebih dahulu', 'warning');
        return;
      }

      const rawValue = $modalInput?.value?.trim();
      if (!rawValue) {
        showToast('⚠️ Masukkan nilai Profit/Margin (BUK) atau kosongkan untuk reset', 'warning');
        return;
      }

      const v = parsePctUI(rawValue);
      if (v == null) {
        showToast('❌ Format angka tidak valid', 'error');
        return;
      }
      if (v < 0 || v > 100) {
        showToast('❌ Profit/Margin (BUK) harus antara 0-100%', 'error');
        return;
      }

      $modalApply.disabled = true;
      const originalText = $modalApply.textContent;
      $modalApply.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Menyimpan...';

      try {
        // Save override
        const saveResp = await saveOverride(selectedId, v);

        // TIER 1 FIX: Clear cache to force reload
        cacheDetail.delete(selectedId);

        // Get updated pricing
        const pp = await getPricingItem(selectedId);
        const effMarkup = Number(pp.effective_markup);

        // Update UI indicators
        if ($eff) $eff.textContent = `Profit: ${pp.effective_markup}%`;
        if ($ovrChip) $ovrChip.hidden = !(pp.override_markup != null);
        if ($modalInput) $modalInput.value = pp.override_markup || '';

        // Update rows data with new effective markup
        const idx = rows.findIndex(r => r.pekerjaan_id === selectedId);
        if (idx >= 0) rows[idx].markup_eff = effMarkup;

        // Re-render list to show updated override chip
        renderList();

        // TIER 2 FIX: Reload rekap to update Grand Total
        try {
          await loadRekap();
        } catch (rekapErr) {
          console.warn('[OVERRIDE] Failed to reload rekap, but override saved:', rekapErr);
        }

        // Re-fetch and render detail with new markup
        const detail = await fetchDetail(selectedId);
        renderDetailTable(detail?.items || [], effMarkup);

        // Close modal
        if (window.bootstrap) {
          const modalEl = document.getElementById('raOverrideModal');
          window.bootstrap.Modal.getOrCreateInstance(modalEl)?.hide();
        }

        // Success notification
        showToast(`✅ Override Profit/Margin (BUK) berhasil diterapkan: ${pp.effective_markup}%`, 'success');
        console.log('[OVERRIDE] Applied successfully:', { pekerjaanId: selectedId, override: v, effective: effMarkup });

      } catch (e) {
        console.error('[OVERRIDE] Apply failed:', e);

        // Show backend error message if available
        let errorMsg = 'Gagal menerapkan override';
        if (e.message) {
          errorMsg = e.message;
        } else if (typeof e === 'string') {
          errorMsg = e;
        }

        showToast(`❌ ${errorMsg}`, 'error');

      } finally {
        $modalApply.disabled = false;
        $modalApply.innerHTML = originalText;
      }
    });
  }

  // Modal Clear handler - TIER 1 & 2 FIX
  if ($modalClear) {
    $modalClear.addEventListener('click', async () => {
      if (selectedId == null) {
        showToast('⚠️ Pilih pekerjaan terlebih dahulu', 'warning');
        return;
      }

      if (!confirm('Hapus override dan kembali ke Profit/Margin (BUK) default proyek?')) {
        return;
      }

      $modalClear.disabled = true;
      const originalText = $modalClear.textContent;
      $modalClear.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Menghapus...';

      try {
        // Clear override
        await saveOverride(selectedId, null);

        // TIER 1 FIX: Clear cache to force reload
        cacheDetail.delete(selectedId);

        // Get updated pricing (should return to default)
        const pp = await getPricingItem(selectedId);
        const effMarkup = Number(pp.effective_markup);

        // Update UI indicators
        if ($modalInput) $modalInput.value = '';
        if ($eff) $eff.textContent = `Profit: ${pp.effective_markup}%`;
        if ($ovrChip) $ovrChip.hidden = true;

        // Update rows data with default markup
        const idx = rows.findIndex(r => r.pekerjaan_id === selectedId);
        if (idx >= 0) rows[idx].markup_eff = effMarkup;

        // Re-render list
        renderList();

        // TIER 2 FIX: Reload rekap to update Grand Total
        try {
          await loadRekap();
        } catch (rekapErr) {
          console.warn('[OVERRIDE] Failed to reload rekap, but override cleared:', rekapErr);
        }

        // Re-fetch and render detail with default markup
        const detail = await fetchDetail(selectedId);
        renderDetailTable(detail?.items || [], effMarkup);

        // Close modal
        if (window.bootstrap) {
          const modalEl = document.getElementById('raOverrideModal');
          window.bootstrap.Modal.getOrCreateInstance(modalEl)?.hide();
        }

        // Success notification
        showToast(`✅ Override dihapus. Kembali ke default: ${pp.effective_markup}%`, 'info');
        console.log('[OVERRIDE] Cleared successfully:', { pekerjaanId: selectedId, effectiveMarkup: effMarkup });

      } catch (e) {
        console.error('[OVERRIDE] Clear failed:', e);

        let errorMsg = 'Gagal menghapus override';
        if (e.message) {
          errorMsg = e.message;
        } else if (typeof e === 'string') {
          errorMsg = e;
        }

        showToast(`❌ ${errorMsg}`, 'error');

      } finally {
        $modalClear.disabled = false;
        $modalClear.innerHTML = originalText;
      }
    });
  }

  // ====== TIER 3: Enhanced Keyboard Navigation ======
  document.addEventListener('keydown', (e) => {
    // Ctrl+K / Cmd+K: Focus search
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      $search?.focus();
      $search?.select();
      return;
    }

    // Shift+O: Toggle Override Modal (only if pekerjaan selected)
    if (e.shiftKey && e.key.toLowerCase() === 'o' && !e.ctrlKey && !e.metaKey) {
      if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') {
        return; // Don't trigger if typing in input
      }
      e.preventDefault();
      if (selectedId && window.bootstrap) {
        const modalEl = document.getElementById('raOverrideModal');
        if (modalEl) {
          const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
          modal.show();
          // Focus input after modal opens
          setTimeout(() => {
            if ($modalInput) {
              $modalInput.focus();
              $modalInput.select();
            }
          }, CONSTANTS.MODAL_FOCUS_DELAY_MS);
        }
      } else if (!selectedId) {
        showToast('⚠️ Pilih pekerjaan terlebih dahulu', 'warning', CONSTANTS.TOAST_DURATION_SHORT_MS);
      }
      return;
    }

    // Escape: Close modals
    if (e.key === 'Escape') {
      if (window.bootstrap) {
        const modalEl = document.getElementById('raOverrideModal');
        if (modalEl && modalEl.classList.contains('show')) {
          window.bootstrap.Modal.getOrCreateInstance(modalEl)?.hide();
        }
      }
      return;
    }

    // Arrow Up/Down: Navigate job list (only when not in input)
    if ((e.key === 'ArrowUp' || e.key === 'ArrowDown') &&
        document.activeElement?.tagName !== 'INPUT' &&
        document.activeElement?.tagName !== 'TEXTAREA') {

      if (filtered.length === 0) return;

      e.preventDefault();

      const currentIdx = filtered.findIndex(r => r.pekerjaan_id === selectedId);
      let nextIdx;

      if (e.key === 'ArrowUp') {
        nextIdx = currentIdx <= 0 ? filtered.length - 1 : currentIdx - 1;
      } else {
        nextIdx = currentIdx >= filtered.length - 1 ? 0 : currentIdx + 1;
      }

      const nextItem = filtered[nextIdx];
      if (nextItem) {
        selectItem(nextItem.pekerjaan_id);

        // Scroll into view
        const listItem = $list?.querySelector(`[data-id="${nextItem.pekerjaan_id}"]`);
        if (listItem) {
          listItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }
      return;
    }

    // Enter: Select focused job item (if hovering over list)
    if (e.key === 'Enter' && document.activeElement?.classList.contains('rk-item')) {
      e.preventDefault();
      const id = document.activeElement.dataset.id;
      if (id) selectItem(Number(id));
      return;
    }
  });

  /**
   * Make job list items focusable for keyboard navigation (TIER 3 feature)
   * Adds tabindex and ARIA attributes to support keyboard selection
   * @tier3 Part of enhanced keyboard navigation implementation
   * @accessibility Adds role="option" for screen reader support
   */
  function makeJobItemsFocusable() {
    if (!$list) return;
    const items = $list.querySelectorAll('.rk-item');
    items.forEach(item => {
      if (!item.hasAttribute('tabindex')) {
        item.setAttribute('tabindex', '0');
        item.setAttribute('role', 'option');
      }
    });
  }

  // Call after rendering list
  const originalRenderList = renderList;
  renderList = function(...args) {
    originalRenderList.apply(this, args);
    makeJobItemsFocusable();
  };

  // ====== init ======
  (async () => {
    try{
      applyIconAndUIFixes();
      if (!EP_POV_PREF) setOverrideUIEnabled(false);
      await loadProjectBUK();
      await loadRekap();
    }catch(e){
      console.error(e);
      if ($list) $list.innerHTML = `<li class="rk-item"><div class="row-note">Gagal memuat.</div></li>`;
    }
  })();

  // ====== Resizer: drag/keyboard untuk ubah lebar panel kiri ======
  (function initResizer(){
    if (!$resizer || !$leftPane || !$grid) return;

    const setLeftW = (px) => { ROOT.style.setProperty('--rk-left-w', `${px}px`); };
    const getLeftW = () => {
      const v = getComputedStyle(ROOT).getPropertyValue('--rk-left-w').trim();
      const n = parseInt(v, 10);
      return Number.isFinite(n) ? n : CONSTANTS.RESIZER_DEFAULT_WIDTH_PX;
    };

    // restore
    const saved = parseInt(localStorage.getItem('rk-left-w') || '', 10);
    if (saved) setLeftW(saved);

    let startX = 0, startW = 0;
    const MIN = CONSTANTS.RESIZER_MIN_WIDTH_PX;
    const MAX = CONSTANTS.RESIZER_MAX_WIDTH_PX;

    let raf = null;
    const onMove = (e) => {
      const dx = e.clientX - startX;
      const w = Math.max(MIN, Math.min(MAX, startW + dx));
      if (raf) return;
      raf = requestAnimationFrame(() => {
        setLeftW(w);
        raf = null;
      });
    };

    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      document.body.style.userSelect = '';
      const cur = getLeftW();
      if (!Number.isNaN(cur)) localStorage.setItem('rk-left-w', String(cur));
    };

    $resizer.addEventListener('mousedown', (e) => {
      e.preventDefault();
      startX = e.clientX;
      startW = getLeftW();
      document.body.style.userSelect = 'none';
      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
    });

    // keyboard support
    $resizer.addEventListener('keydown', (e) => {
      const step = e.shiftKey ? CONSTANTS.RESIZER_KEYBOARD_STEP_SHIFT_PX : CONSTANTS.RESIZER_KEYBOARD_STEP_PX;
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        const cur = getLeftW();
        const next = Math.max(MIN, Math.min(MAX, cur + (e.key === 'ArrowRight' ? step : -step)));
        setLeftW(next);
        localStorage.setItem('rk-left-w', String(next));
      }
      if (e.key.toLowerCase() === 'r') { // reset
        setLeftW(CONSTANTS.RESIZER_DEFAULT_WIDTH_PX);
        localStorage.setItem('rk-left-w', String(CONSTANTS.RESIZER_DEFAULT_WIDTH_PX));
      }
    });

    // double-click resizer => reset
    $resizer.addEventListener('dblclick', () => {
      setLeftW(CONSTANTS.RESIZER_DEFAULT_WIDTH_PX);
      localStorage.setItem('rk-left-w', String(CONSTANTS.RESIZER_DEFAULT_WIDTH_PX));
    });
  })();

  // ===== EXPORT INITIALIZATION =====
  /**
   * Initialize export buttons (CSV/PDF/Word) using ExportManager
   * Binds click handlers to export buttons with proper error handling
   * Requires ExportManager to be loaded globally
   * @tier3 Full test coverage for export functionality
   */
  function initExportButtons() {
    if (typeof ExportManager === 'undefined') {
      console.warn('[RincianAHSP] ⚠️ ExportManager not loaded - export buttons disabled');
      return;
    }

    try {
      // Get project ID from data attribute
      const projectId = ROOT.dataset.projectId || ROOT.dataset.pid;
      if (!projectId) {
        console.error('[RincianAHSP] Project ID not found');
        return;
      }

      const exporter = new ExportManager(projectId, 'rincian-ahsp');

      const btnCSV = document.getElementById('btn-export-csv') || document.getElementById('ra-btn-export');
      const btnPDF = document.getElementById('btn-export-pdf') || document.getElementById('ra-btn-export-pdf');
      const btnWord = document.getElementById('btn-export-word') || document.getElementById('ra-btn-export-word');

      if (btnCSV) {
        btnCSV.addEventListener('click', async (e) => {
          e.preventDefault();
          console.log('[RincianAHSP] 📥 CSV export requested');
          await exporter.exportAs('csv');
        });
      }

      if (btnPDF) {
        btnPDF.addEventListener('click', async (e) => {
          e.preventDefault();
          console.log('[RincianAHSP] 📄 PDF export requested');
          await exporter.exportAs('pdf');
        });
      }

      if (btnWord) {
        btnWord.addEventListener('click', async (e) => {
          e.preventDefault();
          console.log('[RincianAHSP] 📝 Word export requested');
          await exporter.exportAs('word');
        });
      }

      console.log('[RincianAHSP] ✓ Export buttons initialized');
    } catch (err) {
      console.error('[RincianAHSP] Export initialization failed:', err);
    }
  }

  function updateVolumeAlertForSelection(id) {
    if (!volumeAlertEl) return;
    const needsWarning = pendingVolumeJobs.has(Number(id));
    volumeAlertEl.classList.toggle('d-none', !needsWarning);
  }

  // Run export initialization after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initExportButtons);
  } else {
    initExportButtons();
  }

})();
