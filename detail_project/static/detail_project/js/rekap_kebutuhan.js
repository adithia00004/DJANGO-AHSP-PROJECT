
// static/detail_project/js/rekap_kebutuhan.js
// Fully rebuilt client for Rekap Kebutuhan page with advanced filtering & insights

(function () {
  'use strict';

  console.log('📦 [Rekap Kebutuhan] Module loaded');

  const app = document.getElementById('rk-app');
  if (!app) {
    console.warn('[rk] rk-app element not found - script aborted');
    return;
  }

  const dataset = app.dataset || {};
  const projectId = Number(dataset.projectId || dataset.project_id || app.getAttribute('data-project-id')) || 0;
  const endpoint = dataset.endpoint;
  const filtersEndpoint = dataset.filterEndpoint;
  const timelineEndpoint = dataset.timelineEndpoint;
  const exportCsvUrl = dataset.exportCsv;
  const exportPdfUrl = dataset.exportPdf;
  const exportWordUrl = dataset.exportWord;

  if (!endpoint) {
    console.error('[rk] endpoint tidak tersedia pada data-page');
    return;
  }

  const $ = (selector, ctx = document) => ctx.querySelector(selector);
  const $$ = (selector, ctx = document) => Array.from(ctx.querySelectorAll(selector));

  const esc = (value) => {
    if (value === null || value === undefined) return '';
    return String(value).replace(/[&<>"']/g, (char) => {
      switch (char) {
        case '&': return '&amp;';
        case '<': return '&lt;';
        case '>': return '&gt;';
        case '"': return '&quot;';
        case '\'': return '&#39;';
        default: return char;
      }
    });
  };

  const qtyFormatter = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 4 });

  // Accounting format for currency: Rp 1.234.567,89
  const currencyFormatter = new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,  // No decimals for cleaner display
  });

  const formatQtyValue = (value) => {
    const num = Number(value);
    if (!Number.isFinite(num)) return '-';
    return qtyFormatter.format(num);
  };

  const formatCurrencyValue = (value) => {
    const num = Number(value);
    if (!Number.isFinite(num)) return 'Rp 0';
    // Round to nearest whole number for cleaner accounting display
    const rounded = Math.round(num);
    return currencyFormatter.format(rounded);
  };

  // PHASE 5 UI FIX 2.1: Smart number scaling for chart labels
  const detectScale = (values) => {
    const maxVal = Math.max(...values.map(v => Math.abs(Number(v) || 0)));
    if (maxVal >= 1_000_000_000) return { scale: 1_000_000_000, label: 'Milyar', unit: 'M' };
    if (maxVal >= 100_000_000) return { scale: 100_000_000, label: '100 Juta', unit: '100Jt' };
    if (maxVal >= 10_000_000) return { scale: 10_000_000, label: '10 Juta', unit: '10Jt' };
    if (maxVal >= 1_000_000) return { scale: 1_000_000, label: 'Juta', unit: 'Jt' };
    return { scale: 1, label: '', unit: '' };
  };

  const formatScaledValue = (value, scaleInfo) => {
    const num = Number(value);
    if (!Number.isFinite(num)) return '0';
    if (scaleInfo.scale === 1) return qtyFormatter.format(num);
    const scaled = num / scaleInfo.scale;
    return qtyFormatter.format(scaled);
  };

  const CATEGORY_LABELS = {
    TK: 'Tenaga Kerja',
    BHN: 'Bahan',
    ALT: 'Alat',
    LAIN: 'Lain-lain',
  };

  const defaultFilter = () => ({
    mode: 'all',
    tahapan_id: null,
    kategori: ['TK', 'BHN', 'ALT', 'LAIN'],
    klasifikasi_ids: [],
    sub_klasifikasi_ids: [],
    pekerjaan_ids: [],
    search: '',
    period_mode: 'all',
    period_start: '',
    period_end: '',
  });

  let currentFilter = defaultFilter();
  let currentViewMode = 'snapshot';
  let tahapanList = [];
  let filterMeta = {
    klasifikasi: [],
    pekerjaan: [],
    periods: { weeks: [], months: [] },
  };

  let tableRowsCache = [];
  let timelineCache = [];
  let lastData = null; // PHASE 5 TRACK 3.1: Store last fetched data for autocomplete

  let chartMixInstance = null;
  let chartCostInstance = null;
  let costChartMode = 'compact';
  const analyticsState = {
    mixSeries: [],
    costSeriesFull: [],
  };
  const refs = {
    tbody: $('#rk-tbody'),
    empty: $('#rk-empty'),
    loading: $('#rk-loading'),
    tableWrap: $('#rk-tablewrap'),
    timelineWrap: $('#rk-timeline'),
    timelineContent: $('#rk-timeline-content'),
    timelineLoading: $('#rk-timeline-loading'),
    timelineEmpty: $('#rk-timeline-empty'),
    scopeIndicator: $('#rk-scope-indicator'),
    filterIndicator: $('#rk-filter-indicator'),
    tahapanMenu: $('#rk-tahapan-menu'),
    tahapanLabel: $('#rk-tahapan-label'),
    klasifikasiMenu: $('#rk-klasifikasi-menu'),
    modalKlasifikasi: $('#rk-klasifikasi'),  // Modal select element
    subMenu: $('#rk-subklasifikasi-menu'),
    pekerjaanMenu: $('#rk-pekerjaan-menu'),
    pekerjaanSearch: $('#rk-pekerjaan-search'),
    periodMode: $('#rk-period-mode'),
    periodStart: $('#rk-period-start'),
    periodEnd: $('#rk-period-end'),
    searchInput: $('#rk-search'),
    applyBtn: $('#rk-btn-apply-filter'),
    resetBtn: $('#rk-btn-reset-filter'),
    countTK: $('#rk-count-TK'),
    countBHN: $('#rk-count-BHN'),
    countALT: $('#rk-count-ALT'),
    countLAIN: $('#rk-count-LAIN'),
    qtyTK: $('#rk-qty-TK'),
    qtyBHN: $('#rk-qty-BHN'),
    qtyALT: $('#rk-qty-ALT'),
    qtyLAIN: $('#rk-qty-LAIN'),
    nrows: $('#rk-nrows'),
    totalCost: $('#rk-total-cost'),
    tfoot: $('#rk-tfoot'),
    footerCount: $('#rk-footer-count'),
    footerTotal: $('#rk-footer-total'),
    // Scheduled/Unscheduled breakdown in footer
    tfootScheduledRow: $('.rk-tfoot-scheduled'),
    tfootUnscheduledRow: $('.rk-tfoot-unscheduled'),
    footerScheduledCount: $('#rk-footer-scheduled-count'),
    footerScheduledTotal: $('#rk-footer-scheduled-total'),
    footerUnscheduledCount: $('#rk-footer-unscheduled-count'),
    footerUnscheduledTotal: $('#rk-footer-unscheduled-total'),
    generatedAt: $('#rk-generated'),
    chartMix: $('#rk-chart-mix'),
    chartMixSummary: $('#rk-chart-mix-summary'),
    chartCost: $('#rk-chart-cost'),
    chartCostSummary: $('#rk-chart-cost-summary'),
    analyticsPeriod: $('#rk-analytics-period'),
    viewToggleButtons: $$('#rk-view-toggle [data-view]'),
    costModeToggle: $('#rk-cost-mode-toggle'),
    // Phase 1: UX Navigation refs
    jadwalLink: $('#rk-jadwal-link'),
    progressWarning: $('#rk-progress-warning'),
    progressWarningCount: $('#rk-progress-warning-count'),
  };

  const showToast = (message, type = 'info') => {
    if (window.DP && window.DP.core && window.DP.core.toast) {
      window.DP.core.toast.show(message, type);
      return;
    }
    console.log(`[${type}] ${message}`);
  };

  /**
   * Add ripple effect to buttons
   */
  const addRippleEffect = (button) => {
    if (!button) return;
    button.classList.add('btn-ripple');
  };

  /**
   * Initialize UX enhancements
   */
  const initializeUXEnhancements = () => {
    // Add ripple effects to all buttons
    $$('.btn').forEach(btn => addRippleEffect(btn));

    // Add tooltips to elements with title
    $$('[title]').forEach(el => {
      if (!el.hasAttribute('data-bs-toggle')) {
        el.setAttribute('data-bs-toggle', 'tooltip');
      }
    });

    // Initialize Bootstrap tooltips
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
      $$('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
      });
    }

    // Animate elements on scroll
    const observeElements = () => {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('animate-fade-in');
          }
        });
      }, { threshold: 0.1 });

      $$('.rk-chart-card, .rk-stat-badge').forEach(el => {
        observer.observe(el);
      });
    };

    observeElements();
    console.log('🎨 UX enhancements initialized');
  };

  const apiCall = async (url, options = {}) => {
    const response = await fetch(url, {
      credentials: 'same-origin',
      ...options,
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `HTTP ${response.status}`);
    }
    return response.json();
  };

  const setLoading = (isLoading) => {
    if (refs.loading) {
      refs.loading.classList.toggle('d-none', !isLoading);
    }
    if (refs.tableWrap) {
      refs.tableWrap.classList.toggle('rk-table-loading', isLoading);
    }
  };

  const setEmptyState = (isEmpty) => {
    if (refs.empty) {
      refs.empty.classList.toggle('d-none', !isEmpty);
    }
  };

  const setTimelineLoading = (isLoading) => {
    if (refs.timelineLoading) {
      refs.timelineLoading.classList.toggle('d-none', !isLoading);
    }
  };

  const setTimelineEmpty = (isEmpty) => {
    if (refs.timelineEmpty) {
      refs.timelineEmpty.classList.toggle('d-none', !isEmpty);
    }
  };

  const updateDropdownLabels = () => {
    const klasLabel = $('#rk-klasifikasi-label');
    const subLabel = $('#rk-subklasifikasi-label');
    const pekerjaanLabel = $('#rk-pekerjaan-label');
    const kategoriLabel = $('#rk-kategori-label');

    if (klasLabel) {
      klasLabel.textContent = currentFilter.klasifikasi_ids.length
        ? `${currentFilter.klasifikasi_ids.length} dipilih`
        : 'Semua Klasifikasi';
    }
    if (subLabel) {
      subLabel.textContent = currentFilter.sub_klasifikasi_ids.length
        ? `${currentFilter.sub_klasifikasi_ids.length} dipilih`
        : 'Semua Sub-Klasifikasi';
    }
    if (pekerjaanLabel) {
      if (!currentFilter.pekerjaan_ids.length) {
        pekerjaanLabel.textContent = 'Semua Pekerjaan';
      } else if (currentFilter.pekerjaan_ids.length === 1) {
        pekerjaanLabel.textContent = '1 pekerjaan dipilih';
      } else {
        pekerjaanLabel.textContent = `${currentFilter.pekerjaan_ids.length} pekerjaan dipilih`;
      }
    }
    if (kategoriLabel) {
      if (currentFilter.kategori.length === 4) {
        kategoriLabel.textContent = 'Semua Kategori';
      } else if (!currentFilter.kategori.length) {
        kategoriLabel.textContent = 'Tidak ada kategori';
      } else {
        kategoriLabel.textContent = currentFilter.kategori.join(', ');
      }
    }
  };

  const updateTahapanLabel = () => {
    if (!refs.tahapanLabel) return;
    if (currentFilter.mode === 'all' || !currentFilter.tahapan_id) {
      refs.tahapanLabel.innerHTML = '<i class="bi bi-globe"></i> Keseluruhan Project';
      return;
    }
    const found = tahapanList.find((item) => Number(item.tahapan_id) === Number(currentFilter.tahapan_id));
    if (found) {
      refs.tahapanLabel.textContent = `${found.nama || 'Tahapan'} (#${found.tahapan_id})`;
    }
  };
  const getPeriodOptionsForMode = (mode) => {
    if (!filterMeta || !filterMeta.periods) return [];
    if (mode.startsWith('week')) {
      return filterMeta.periods.weeks || [];
    }
    if (mode.startsWith('month')) {
      return filterMeta.periods.months || [];
    }
    return [];
  };

  const getPeriodLabel = (mode, value) => {
    if (!value) return '';
    const source = getPeriodOptionsForMode(mode);
    const found = source.find((item) => String(item.value) === String(value));
    return found ? found.label : value;
  };

  const describePeriodChip = () => {
    const mode = currentFilter.period_mode || 'all';
    if (mode === 'all') {
      return '';
    }
    const startLabel = getPeriodLabel(mode, currentFilter.period_start);
    if (!startLabel) {
      return '';
    }
    const endValue = currentFilter.period_end || currentFilter.period_start;
    const endLabel = getPeriodLabel(mode, endValue);
    if (mode.endsWith('range') && endLabel && endLabel !== startLabel) {
      return `${startLabel} – ${endLabel}`;
    }
    return startLabel;
  };

  const updatePeriodNotes = (label) => {
    const value = label || 'Seluruh waktu proyek';
    document.querySelectorAll('[data-period-note]').forEach((el) => {
      el.textContent = value;
    });
  };

  const updateAnalyticsPeriodLabel = () => {
    if (!refs.analyticsPeriod) return;
    const label = describePeriodChip() || 'Seluruh waktu proyek';
    refs.analyticsPeriod.textContent = label;
    updatePeriodNotes(label);
  };

  const buildQueryParams = () => {
    const params = { mode: currentFilter.mode };
    if (currentFilter.mode === 'tahapan' && currentFilter.tahapan_id) {
      params.tahapan_id = currentFilter.tahapan_id;
    }
    if (currentFilter.klasifikasi_ids.length) {
      params.klasifikasi = currentFilter.klasifikasi_ids.join(',');
    }
    if (currentFilter.sub_klasifikasi_ids.length) {
      params.sub_klasifikasi = currentFilter.sub_klasifikasi_ids.join(',');
    }
    if (currentFilter.pekerjaan_ids.length) {
      params.pekerjaan = currentFilter.pekerjaan_ids.join(',');
    }
    if (currentFilter.kategori.length && currentFilter.kategori.length < 4) {
      params.kategori = currentFilter.kategori.join(',');
    }
    if (currentFilter.search) {
      params.search = currentFilter.search;
    }
    if (currentFilter.period_mode && currentFilter.period_mode !== 'all') {
      params.period_mode = currentFilter.period_mode;
      if (currentFilter.period_start) {
        params.period_start = currentFilter.period_start;
      }
      if (currentFilter.period_end) {
        params.period_end = currentFilter.period_end;
      }
    }
    return params;
  };

  const renderRows = (rows = []) => {
    if (!refs.tbody) return;
    if (!rows.length) {
      refs.tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-3">Tidak ada data</td></tr>';
      setEmptyState(true);
      return;
    }
    setEmptyState(false);

    // DEBUG: Check if is_scheduled field is present
    console.log('[Keseluruhan Debug] First row sample:', rows[0]);
    console.log('[Keseluruhan Debug] is_scheduled field present:', 'is_scheduled' in (rows[0] || {}));

    // Separate scheduled and unscheduled items
    const scheduled = rows.filter(r => r.is_scheduled);
    const unscheduled = rows.filter(r => !r.is_scheduled);
    console.log('[Keseluruhan Debug] Scheduled:', scheduled.length, 'Unscheduled:', unscheduled.length);

    // Helper to render item rows
    const renderItemRow = (row) => {
      const qty = formatQtyValue(row.quantity_decimal ?? row.quantity);
      const hargaSatuan = formatCurrencyValue(row.harga_satuan_decimal ?? row.harga_satuan);
      const hargaTotal = formatCurrencyValue(row.harga_total_decimal ?? row.harga_total);
      const pekerjaanNama = row.pekerjaan || row.pekerjaan_nama || '';
      return `
        <tr>
          <td class="text-uppercase text-muted small fw-semibold">${esc(row.kategori || '-')}</td>
          <td class="text-nowrap">${esc(row.kode || '-')}</td>
          <td>
            <div class="fw-semibold">${esc(row.uraian || '-')}</div>
            ${pekerjaanNama ? `<div class="text-muted small">${esc(pekerjaanNama)}</div>` : ''}
          </td>
          <td>${esc(row.satuan || '-')}</td>
          <td class="text-end">${qty}</td>
          <td class="text-end">${hargaSatuan}</td>
          <td class="text-end fw-semibold">${hargaTotal}</td>
        </tr>`;
    };

    // Helper to calculate subtotal
    const calcSubtotal = (items) => items.reduce((sum, r) => sum + Math.round(r.harga_total_decimal ?? 0), 0);

    let html = '';

    // Scheduled group
    if (scheduled.length > 0) {
      const scheduledSubtotal = calcSubtotal(scheduled);
      html += `
        <tr class="rk-group-header">
          <td colspan="7" class="fw-bold">
            <i class="bi bi-calendar-check me-2"></i>Item Terjadwal (${scheduled.length} item)
          </td>
        </tr>`;
      html += scheduled.map(renderItemRow).join('');
      html += `
        <tr class="rk-subtotal-row">
          <td colspan="6" class="text-end fw-semibold">Subtotal Terjadwal</td>
          <td class="text-end fw-bold rk-text-success">${formatCurrencyValue(scheduledSubtotal)}</td>
        </tr>`;
    }

    // Unscheduled group
    if (unscheduled.length > 0) {
      const unscheduledSubtotal = calcSubtotal(unscheduled);
      html += `
        <tr class="rk-group-header">
          <td colspan="7" class="fw-bold">
            <i class="bi bi-clock-history me-2"></i>Item Belum Terjadwal (${unscheduled.length} item)
          </td>
        </tr>`;
      html += unscheduled.map(renderItemRow).join('');
      html += `
        <tr class="rk-subtotal-row">
          <td colspan="6" class="text-end fw-semibold">Subtotal Belum Terjadwal</td>
          <td class="text-end fw-bold rk-text-warning">${formatCurrencyValue(unscheduledSubtotal)}</td>
        </tr>`;
    }

    refs.tbody.innerHTML = html;

    // Update footer subtotals breakdown
    const scheduledSubtotalVal = scheduled.length > 0 ? calcSubtotal(scheduled) : 0;
    const unscheduledSubtotalVal = unscheduled.length > 0 ? calcSubtotal(unscheduled) : 0;
    const grandTotal = scheduledSubtotalVal + unscheduledSubtotalVal;

    // Show/hide scheduled subtotal row
    if (refs.tfootScheduledRow) {
      if (scheduled.length > 0) {
        refs.tfootScheduledRow.classList.remove('d-none');
        if (refs.footerScheduledCount) refs.footerScheduledCount.textContent = scheduled.length;
        if (refs.footerScheduledTotal) refs.footerScheduledTotal.textContent = formatCurrencyValue(scheduledSubtotalVal);
      } else {
        refs.tfootScheduledRow.classList.add('d-none');
      }
    }

    // Show/hide unscheduled subtotal row
    if (refs.tfootUnscheduledRow) {
      if (unscheduled.length > 0) {
        refs.tfootUnscheduledRow.classList.remove('d-none');
        if (refs.footerUnscheduledCount) refs.footerUnscheduledCount.textContent = unscheduled.length;
        if (refs.footerUnscheduledTotal) refs.footerUnscheduledTotal.textContent = formatCurrencyValue(unscheduledSubtotalVal);
      } else {
        refs.tfootUnscheduledRow.classList.add('d-none');
      }
    }

    // Update grand total
    if (refs.footerCount) refs.footerCount.textContent = scheduled.length + unscheduled.length;
    if (refs.footerTotal) refs.footerTotal.textContent = formatCurrencyValue(grandTotal);

    // Show tfoot if there are any rows
    if (refs.tfoot) {
      if (scheduled.length > 0 || unscheduled.length > 0) {
        refs.tfoot.classList.remove('d-none');
      } else {
        refs.tfoot.classList.add('d-none');
      }
    }
  };

  const updateStats = (meta = {}, rows = []) => {
    const counts = meta.counts_per_kategori || {};
    // Update item counts only (qty removed as not relevant for users)
    if (refs.countTK) refs.countTK.textContent = counts.TK || 0;
    if (refs.countBHN) refs.countBHN.textContent = counts.BHN || 0;
    if (refs.countALT) refs.countALT.textContent = counts.ALT || 0;
    if (refs.countLAIN) refs.countLAIN.textContent = counts.LAIN || 0;
    if (refs.nrows) refs.nrows.textContent = meta.n_rows || rows.length || 0;

    // Use numeric value for consistent accounting format
    // Try multiple sources: decimal field, parse from string, or calculate from rows
    let totalValue = meta.grand_total_cost_decimal ?? meta.grand_total_numeric ?? 0;

    if (!totalValue && meta.grand_total_cost) {
      let numStr = String(meta.grand_total_cost);

      // Detect format: if no "Rp" and no comma, it's decimal format (e.g., 523248870.82)
      // Indonesian format has: Rp prefix, dots for thousands, comma for decimal
      const isDecimalFormat = !numStr.includes('Rp') && !numStr.includes(',') && /^\d+\.?\d*$/.test(numStr.trim());

      if (isDecimalFormat) {
        // Direct parse - it's already in standard decimal format
        const parsed = parseFloat(numStr);
        if (Number.isFinite(parsed)) totalValue = parsed;
      } else {
        // Indonesian format: "Rp 100.000.000,00"
        numStr = numStr.replace(/[Rp\s]/gi, ''); // Remove Rp and spaces
        numStr = numStr.replace(/\./g, '');       // Remove thousand separators (dots)
        numStr = numStr.replace(',', '.');        // Convert decimal comma to dot
        const parsed = parseFloat(numStr);
        if (Number.isFinite(parsed)) totalValue = parsed;
      }
    }

    if (!totalValue && rows.length > 0) {
      // Calculate from rows as fallback - round each value
      totalValue = rows.reduce((sum, r) => sum + Math.round(r.harga_total_decimal ?? r.harga_total ?? 0), 0);
    }

    if (refs.totalCost) refs.totalCost.textContent = formatCurrencyValue(totalValue);
    if (refs.generatedAt) refs.generatedAt.textContent = meta.generated_at || '';

    // Show and populate tfoot grand total row
    const rowCount = meta.n_rows || rows.length || 0;
    if (refs.tfoot && rowCount > 0) {
      refs.tfoot.classList.remove('d-none');
      if (refs.footerCount) refs.footerCount.textContent = rowCount;
      if (refs.footerTotal) refs.footerTotal.textContent = formatCurrencyValue(totalValue);
    } else if (refs.tfoot) {
      refs.tfoot.classList.add('d-none');
    }
  };

  // Update toolbar stats from timeline data
  const updateStatsFromTimeline = (items, totalCost) => {
    const counts = { TK: 0, BHN: 0, ALT: 0, LAIN: 0 };
    items.forEach(item => {
      if (counts.hasOwnProperty(item.kategori)) counts[item.kategori]++;
    });
    if (refs.countTK) refs.countTK.textContent = counts.TK;
    if (refs.countBHN) refs.countBHN.textContent = counts.BHN;
    if (refs.countALT) refs.countALT.textContent = counts.ALT;
    if (refs.countLAIN) refs.countLAIN.textContent = counts.LAIN;
    if (refs.nrows) refs.nrows.textContent = items.length;
    if (refs.totalCost) refs.totalCost.textContent = formatCurrencyValue(totalCost);
  };

  const updateScopeIndicator = (meta = {}) => {
    if (!refs.scopeIndicator) return;
    const chips = [];

    // View mode indicator
    if (currentViewMode === 'timeline') {
      // Build period label for timeline
      const mode = timelineRangeState?.mode || 'week';
      const options = mode === 'week'
        ? (filterMeta.periods?.weeks || [])
        : (filterMeta.periods?.months || []);
      const startOpt = options[timelineRangeState?.startIdx || 0];
      const endOpt = options[timelineRangeState?.endIdx || 0];
      const periodLabel = startOpt && endOpt
        ? `${startOpt.label || startOpt.value} – ${endOpt.label || endOpt.value}`
        : 'Rentang Waktu';
      chips.push(`<span class="badge bg-info-subtle text-info"><i class="bi bi-calendar-range me-1"></i>Per Periode: ${esc(periodLabel)}</span>`);
    } else {
      chips.push('<span class="badge bg-success-subtle text-success"><i class="bi bi-list-check me-1"></i>Keseluruhan</span>');
    }

    // Tahapan mode (if active)
    if (currentFilter.mode === 'tahapan' && meta.tahapan) {
      chips.push(`<span class="badge bg-primary-subtle text-primary">Tahapan: ${esc(meta.tahapan.nama || '#')}</span>`);
    }

    refs.scopeIndicator.innerHTML = chips.join(' ');
  };
  const updateFilterIndicator = () => {
    if (!refs.filterIndicator) return;
    const chips = [];
    if (currentFilter.kategori.length && currentFilter.kategori.length < 4) {
      chips.push(`Kategori: ${currentFilter.kategori.join(', ')}`);
    }
    if (currentFilter.klasifikasi_ids.length) {
      chips.push(`Klasifikasi: ${currentFilter.klasifikasi_ids.length}`);
    }
    if (currentFilter.sub_klasifikasi_ids.length) {
      chips.push(`Sub: ${currentFilter.sub_klasifikasi_ids.length}`);
    }
    if (currentFilter.pekerjaan_ids.length) {
      chips.push(`Pekerjaan: ${currentFilter.pekerjaan_ids.length}`);
    }
    if (currentFilter.search) {
      chips.push(`Cari: “${esc(currentFilter.search)}”`);
    }
    const periodLabel = describePeriodChip();
    if (periodLabel) {
      chips.push(`Waktu: ${esc(periodLabel)}`);
    }
    refs.filterIndicator.innerHTML = chips.length
      ? `<span class="rk-filter-active-indicator"><i class="bi bi-funnel-fill me-1"></i>${chips.join(' · ')}</span>`
      : '';
    updateAnalyticsPeriodLabel();
    updateJadwalDeepLink(); // Phase 1: Update deep link when filter changes
  };

  // Phase 1.1: Update Jadwal Pekerjaan button href with active filters
  const updateJadwalDeepLink = () => {
    if (!refs.jadwalLink) return;

    const baseUrl = refs.jadwalLink.getAttribute('href').split('?')[0];
    const params = new URLSearchParams();

    // Include relevant filters for deep linking
    if (currentFilter.klasifikasi_ids.length) {
      params.set('klasifikasi', currentFilter.klasifikasi_ids.join(','));
    }
    if (currentFilter.pekerjaan_ids.length) {
      params.set('pekerjaan', currentFilter.pekerjaan_ids.join(','));
    }
    if (currentFilter.period_mode && currentFilter.period_mode !== 'all') {
      params.set('period_mode', currentFilter.period_mode);
      if (currentFilter.period_start) {
        params.set('period_start', currentFilter.period_start);
      }
      if (currentFilter.period_end) {
        params.set('period_end', currentFilter.period_end);
      }
    }

    const queryString = params.toString();
    refs.jadwalLink.href = queryString ? `${baseUrl}?${queryString}` : baseUrl;
  };

  // Phase 1.2: Update warning badge for pekerjaan without progress
  const updateProgressWarning = (pekerjaanWithoutProgress = []) => {
    if (!refs.progressWarning || !refs.progressWarningCount) return;

    const count = Array.isArray(pekerjaanWithoutProgress) ? pekerjaanWithoutProgress.length : 0;

    if (count > 0) {
      refs.progressWarningCount.textContent = count;
      refs.progressWarning.classList.remove('d-none');
      refs.progressWarning.title = `${count} pekerjaan belum memiliki progress rencana di Jadwal Pekerjaan`;
    } else {
      refs.progressWarning.classList.add('d-none');
    }
  };

  const ensureChartInstance = (el, currentInstance, setter) => {
    if (!el) return null;
    if (currentInstance) return currentInstance;
    if (!window.echarts) return null;
    const instance = window.echarts.init(el);
    setter(instance);
    return instance;
  };

  const renderMixChart = (data = []) => {
    if (!refs.chartMix) return;
    chartMixInstance = ensureChartInstance(refs.chartMix, chartMixInstance, (inst) => { chartMixInstance = inst; });
    if (!chartMixInstance) return;
    if (!data.length) {
      chartMixInstance.clear();
      chartMixInstance.setOption({
        title: { text: 'Belum ada data kategori', left: 'center', top: 'middle', textStyle: { color: '#9aa0ac', fontSize: 14 } },
      });
      return;
    }

    // PHASE 5 UI FIX 2.1: Detect scale for smart formatting
    const values = data.map(item => item.value);
    const scaleInfo = detectScale(values);

    const titleConfig = {
      text: 'Komposisi Biaya',
      left: 'center',
      top: 10,
      textStyle: { fontSize: 14, fontWeight: 'bold' },
    };

    chartMixInstance.setOption({
      title: titleConfig,
      tooltip: {
        trigger: 'item',
        formatter: (params) => `${params.name}: ${formatCurrencyValue(params.value)} (${params.percent}%)`,
      },
      legend: {
        bottom: 0,
        type: 'scroll',
      },
      series: [{
        type: 'pie',
        radius: ['45%', '70%'],
        top: scaleInfo.scale > 1 ? '15%' : '10%',
        data,
        label: {
          formatter: '{b}\n{d}%',
          textBorderWidth: 0,
          textShadowBlur: 0,
        },
      }],
    });
  };

  const renderCostChart = (data = []) => {
    if (!refs.chartCost) return;
    chartCostInstance = ensureChartInstance(refs.chartCost, chartCostInstance, (inst) => { chartCostInstance = inst; });
    if (!chartCostInstance) return;
    if (!data.length) {
      chartCostInstance.clear();
      chartCostInstance.setOption({
        title: { text: 'Belum ada data biaya', left: 'center', top: 'middle', textStyle: { color: '#9aa0ac', fontSize: 14 } },
      });
      return;
    }

    // PHASE 5 UI FIX 2.1: Detect scale for smart formatting
    const values = data.map(item => item.value);
    const scaleInfo = detectScale(values);

    const titleConfig = scaleInfo.scale > 1
      ? {
        text: `Top Biaya per Item`,
        subtext: `dalam ${scaleInfo.label}`,
        left: 'center',
        top: 5,
        textStyle: { fontSize: 14, fontWeight: 'bold' },
        subtextStyle: { fontSize: 11, color: '#6c757d' },
      }
      : {
        text: 'Top Biaya per Item',
        left: 'center',
        top: 5,
        textStyle: { fontSize: 14, fontWeight: 'bold' },
      };

    chartCostInstance.setOption({
      title: titleConfig,
      grid: {
        left: '3%',
        right: '6%',
        bottom: '5%',
        top: scaleInfo.scale > 1 ? '60px' : '40px',
        containLabel: true
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params) => {
          if (!params || !params.length) return '';
          const item = params[0];
          return `${item.name}<br>${formatCurrencyValue(item.value)}`;
        },
      },
      xAxis: {
        type: 'value',
        name: scaleInfo.scale > 1 ? scaleInfo.unit : '',
        nameLocation: 'end',
        nameGap: 5,
        nameTextStyle: { fontSize: 11, color: '#6c757d' },
        axisLabel: {
          formatter: (val) => {
            if (scaleInfo.scale > 1) {
              return formatScaledValue(val, scaleInfo);
            }
            return formatCurrencyValue(val);
          }
        },
      },
      yAxis: {
        type: 'category',
        data: data.map((item) => item.label),
        axisLabel: { width: 200, overflow: 'truncate' },
      },
      series: [{
        type: 'bar',
        data: data.map((item) => item.value),
        itemStyle: { color: '#0d6efd' },
      }],
    });
  };

  const renderSummaryList = (container, items, template) => {
    if (!container) return;
    if (!items.length) {
      container.innerHTML = '<li class="text-muted">Belum ada data</li>';
      return;
    }
    container.innerHTML = items.map(template).join('');
  };

  const updateAnalytics = (items = []) => {
    const categoryTotals = {
      TK: { cost: 0, qty: 0 },
      BHN: { cost: 0, qty: 0 },
      ALT: { cost: 0, qty: 0 },
      LAIN: { cost: 0, qty: 0 },
    };
    const costMap = new Map();

    items.forEach((item) => {
      const kategori = categoryTotals[item.kategori] ? item.kategori : 'LAIN';
      const qty = Number(item.quantity_decimal ?? item.quantity) || 0;
      const cost = Number(item.harga_total_decimal ?? item.harga_total) || 0;
      categoryTotals[kategori].qty += qty;
      categoryTotals[kategori].cost += cost;
      const label = `${item.kode || '-'} – ${item.uraian || '-'}`;
      costMap.set(label, (costMap.get(label) || 0) + cost);
    });

    const mixSeries = Object.entries(categoryTotals)
      .filter(([, info]) => info.cost > 0)
      .map(([key, info]) => ({ name: CATEGORY_LABELS[key] || key, value: info.cost, cost: info.cost, qty: info.qty }));

    const costSeriesFull = Array.from(costMap.entries())
      .map(([label, value]) => ({ label, value }))
      .filter((item) => item.value > 0)
      .sort((a, b) => b.value - a.value);

    analyticsState.mixSeries = mixSeries;
    analyticsState.costSeriesFull = costSeriesFull;

    const costSeries = costChartMode === 'compact' ? costSeriesFull.slice(0, 5) : costSeriesFull;
    renderMixChart(mixSeries);
    renderCostChart(costSeries);

    renderSummaryList(refs.chartMixSummary, mixSeries, (item) => {
      // Qty removed as not relevant for users - only show cost
      // Added title attribute for tooltip when text is truncated
      return `<li><span class="rk-chart-label" title="${esc(item.name)}">${esc(item.name)}</span><span class="rk-chart-value">${formatCurrencyValue(item.cost)}</span></li>`;
    });

    renderSummaryList(refs.chartCostSummary, costSeries, (item) => (
      // Added title attribute for tooltip when text is truncated
      `<li><span class="rk-chart-label" title="${esc(item.label)}">${esc(item.label)}</span><span class="rk-chart-value">${formatCurrencyValue(item.value)}</span></li>`
    ));
  };

  const updateAnalyticsFromRows = (rows = []) => {
    tableRowsCache = rows;
    updateAnalytics(rows);
  };

  const updateAnalyticsFromTimeline = (periods = []) => {
    timelineCache = periods;
    const flattened = [];
    periods.forEach((period) => {
      (period.items || []).forEach((item) => flattened.push(item));
    });
    updateAnalytics(flattened);
  };
  const renderTimeline = (periods = []) => {
    if (!refs.timelineContent) return;
    if (!periods.length) {
      refs.timelineContent.innerHTML = '';
      setTimelineEmpty(true);
      return;
    }
    setTimelineEmpty(false);
    // CATATAN: User request - tampilkan SEMUA item per week, bukan hanya 5
    const limit = null; // Always show all items in timeline
    const html = periods.map((period, idx) => {
      const source = period.items || [];
      const items = limit ? source.slice(0, limit) : source;

      // Determine period type (week or month)
      const periodLabel = period.label || period.value || '-';
      const isWeek = periodLabel.toLowerCase().includes('minggu') || periodLabel.toLowerCase().includes('week');
      const badgeClass = isWeek ? 'rk-period-badge--week' : 'rk-period-badge--month';
      const badgeIcon = isWeek ? 'bi-calendar-week' : 'bi-calendar-month';

      // Calculate stats
      const itemCount = source.length;
      const totalCost = period.total_cost_decimal || period.total_cost || 0;

      // Determine period status based on dates (simplified - can be enhanced with actual date comparison)
      const periodClass = 'rk-timeline-period';

      // Build item table - REDESIGNED per user request (3.4)
      const itemTable = items.length ? `
        <table class="rk-timeline-period__table table table-sm">
          <thead>
            <tr>
              <th>Uraian</th>
              <th>Satuan</th>
              <th class="text-end">Harga Satuan</th>
              <th class="text-end">Kuantitas</th>
              <th class="text-end">Total Harga</th>
            </tr>
          </thead>
          <tbody>
            ${items.map((item) => `
              <tr>
                <td>${esc(item.uraian || '-')}</td>
                <td>${esc(item.satuan || '-')}</td>
                <td class="text-end">${formatCurrencyValue(item.harga_satuan_decimal || item.harga_satuan)}</td>
                <td class="text-end">${formatQtyValue(item.quantity_decimal || item.quantity)}</td>
                <td class="text-end fw-bold">${formatCurrencyValue(item.harga_total_decimal || item.harga_total)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      ` : '<p class="text-muted text-center py-3">Tidak ada item</p>';

      return `
        <div class="${periodClass}" data-period="${esc(period.value || idx)}">
          <div class="rk-timeline-period__header">
            <div class="rk-timeline-period__badge"
                 data-bs-toggle="tooltip"
                 data-bs-placement="top"
                 title="Periode: ${esc(period.start_date || '')} s/d ${esc(period.end_date || '')}">
              <i class="bi ${badgeIcon}"></i>
              <span>${esc(periodLabel)}</span>
            </div>
            <div class="rk-timeline-period__dates">
              <small>${esc(period.start_date || '')} - ${esc(period.end_date || '')}</small>
            </div>
            <div class="rk-timeline-period__stats">
              <span class="badge bg-info"
                    data-bs-toggle="tooltip"
                    data-bs-placement="top"
                    title="Total ${itemCount} item dalam periode ini">
                <i class="bi bi-list-ul"></i> ${itemCount} items
              </span>
              <span class="badge bg-success"
                    data-bs-toggle="tooltip"
                    data-bs-placement="top"
                    title="Total biaya untuk periode ini">
                <i class="bi bi-currency-dollar"></i> ${formatCurrencyValue(totalCost)}
              </span>
            </div>
          </div>
          <div class="rk-timeline-period__content">
            ${itemTable}
          </div>
        </div>`;
    }).join('');
    refs.timelineContent.innerHTML = html;

    // Initialize tooltips after rendering
    initTimelineTooltips();
  };

  const initTimelineTooltips = () => {
    // Initialize Bootstrap tooltips for timeline elements
    const tooltipTriggerList = $$('[data-bs-toggle="tooltip"]', refs.timelineContent || document);
    tooltipTriggerList.forEach((el) => {
      // Dispose existing tooltip if any
      const existingTooltip = window.bootstrap?.Tooltip?.getInstance(el);
      if (existingTooltip) {
        existingTooltip.dispose();
      }
      // Initialize new tooltip
      if (window.bootstrap && window.bootstrap.Tooltip) {
        new window.bootstrap.Tooltip(el, {
          html: true,
          delay: { show: 300, hide: 100 },
          trigger: 'hover focus',
        });
      }
    });
  };

  // Phase 4: Render aggregated timeline as single table
  const renderAggregatedTimeline = (items = [], periodLabels = [], periodTotals = [], unscheduledTotal = 0) => {
    if (!refs.timelineContent) return;

    if (!items.length) {
      refs.timelineContent.innerHTML = '';
      setTimelineEmpty(true);
      return;
    }
    setTimelineEmpty(false);

    // Build period range label
    const periodLabel = periodLabels.length > 1
      ? `${periodLabels[0]} - ${periodLabels[periodLabels.length - 1]}`
      : (periodLabels[0] || 'Semua Periode');

    // Calculate totals - round each value to eliminate decimals
    const totalQty = items.reduce((sum, item) => sum + Math.round(item.quantity_decimal || 0), 0);
    const totalCost = items.reduce((sum, item) => sum + Math.round(item.harga_total_decimal || 0), 0);

    const html = `
      <div class="rk-aggregated-timeline">
        <div class="table-responsive dp-scrollbar">
          <table class="rk-table table table-sm table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th style="width:90px" class="text-nowrap">Kat</th>
                <th style="width:160px" class="text-nowrap">Kode</th>
                <th>Uraian</th>
                <th style="width:90px">Satuan</th>
                <th style="width:140px" class="text-end text-nowrap">Kuantitas</th>
                <th style="width:140px" class="text-end text-nowrap">Harga Satuan</th>
                <th style="width:160px" class="text-end text-nowrap">Total Harga</th>
              </tr>
            </thead>
            <tbody>
              ${items.map((item) => `
                <tr>
                  <td><span class="badge bg-${getCategoryColor(item.kategori)}">${item.kategori}</span></td>
                  <td class="text-nowrap">${esc(item.kode || '-')}</td>
                  <td>${esc(item.uraian || '-')}</td>
                  <td class="text-nowrap">${esc(item.satuan || '-')}</td>
                  <td class="text-end font-monospace">${formatQtyValue(item.quantity_decimal || item.quantity)}</td>
                  <td class="text-end font-monospace">${formatCurrencyValue(item.harga_satuan_decimal || item.harga_satuan)}</td>
                  <td class="text-end font-monospace fw-semibold">${formatCurrencyValue(item.harga_total_decimal || item.harga_total)}</td>
                </tr>
              `).join('')}
            </tbody>
            <tfoot>
              <tr class="table-light fw-bold">
                <td colspan="6" class="text-end">GRAND TOTAL (${items.length} item)</td>
                <td class="text-end font-monospace text-success">${formatCurrencyValue(totalCost)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    `;

    refs.timelineContent.innerHTML = html;

    // Sync toolbar stats with timeline data
    updateStatsFromTimeline(items, totalCost);
  };

  // Helper for category badge color
  const getCategoryColor = (kategori) => {
    const colors = {
      'TK': 'primary',
      'BHN': 'success',
      'ALT': 'warning',
      'LAIN': 'secondary'
    };
    return colors[kategori] || 'secondary';
  };

  const refreshAnalyticsCostMode = () => {
    const costSeries = costChartMode === 'compact'
      ? analyticsState.costSeriesFull.slice(0, 5)
      : analyticsState.costSeriesFull;
    renderCostChart(costSeries);
    renderSummaryList(refs.chartCostSummary, costSeries, (item) => (
      // Added title attribute for tooltip when text is truncated
      `<li><span class="rk-chart-label" title="${esc(item.label)}">${esc(item.label)}</span><span class="rk-chart-value">${formatCurrencyValue(item.value)}</span></li>`
    ));
    renderTimeline(timelineCache);
  };
  const loadTahapan = async () => {
    try {
      const url = `/detail_project/api/project/${projectId}/tahapan/`;
      const data = await apiCall(url);
      tahapanList = data.tahapan || [];
      if (!refs.tahapanMenu) return;
      const items = [`<button type="button" class="dropdown-item rk-tahapan-option${currentFilter.mode === 'all' ? ' active' : ''}" data-scope="all" data-tahapan-id="">` +
        '<i class="bi bi-check2-circle me-2"></i> Keseluruhan Project</button>'];
      tahapanList.forEach((item) => {
        const active = currentFilter.mode === 'tahapan' && Number(currentFilter.tahapan_id) === Number(item.tahapan_id);
        items.push(
          `<button type="button" class="dropdown-item rk-tahapan-option${active ? ' active' : ''}" data-scope="tahapan" data-tahapan-id="${item.tahapan_id}">` +
          `<i class="bi bi-bookmark me-2"></i>${esc(item.nama || '-')}` +
          ` <small class="text-muted">(${item.jumlah_pekerjaan || 0} pekerjaan)</small></button>`
        );
      });
      refs.tahapanMenu.innerHTML = items.join('');
      $$('.rk-tahapan-option', refs.tahapanMenu).forEach((btn) => {
        btn.addEventListener('click', (event) => {
          $$('.rk-tahapan-option', refs.tahapanMenu).forEach((el) => el.classList.remove('active'));
          event.currentTarget.classList.add('active');
          const scope = event.currentTarget.getAttribute('data-scope');
          if (scope === 'tahapan') {
            currentFilter.mode = 'tahapan';
            currentFilter.tahapan_id = Number(event.currentTarget.getAttribute('data-tahapan-id')) || null;
          } else {
            currentFilter.mode = 'all';
            currentFilter.tahapan_id = null;
          }
          updateTahapanLabel();
        });
      });
      updateTahapanLabel();
    } catch (error) {
      console.error('[rk] gagal memuat tahapan', error);
    }
  };

  const renderKlasifikasiOptions = () => {
    // Render to menu (legacy)
    if (refs.klasifikasiMenu) {
      if (!filterMeta.klasifikasi.length) {
        refs.klasifikasiMenu.innerHTML = '<div class="text-muted small px-2 py-1">Belum ada klasifikasi</div>';
      } else {
        const html = filterMeta.klasifikasi.map((row) => {
          const checked = currentFilter.klasifikasi_ids.includes(row.id);
          return `<label class="rk-dropdown-item">
            <input type="checkbox" class="form-check-input klasifikasi-check" value="${row.id}" ${checked ? 'checked' : ''}>
            <span>${esc(row.name)} <small class="text-muted">(${row.pekerjaan_count || 0})</small></span>
          </label>`;
        }).join('');
        refs.klasifikasiMenu.innerHTML = html;
      }
    }

    // Render to modal select element (#rk-klasifikasi)
    if (refs.modalKlasifikasi) {
      if (!filterMeta.klasifikasi.length) {
        refs.modalKlasifikasi.innerHTML = '<option value="">Tidak ada klasifikasi</option>';
      } else {
        const optionsHtml = filterMeta.klasifikasi.map((row) => {
          const selected = currentFilter.klasifikasi_ids.includes(row.id);
          const subCount = row.sub?.length || 0;
          return `<option value="${row.id}" ${selected ? 'selected' : ''}>${esc(row.name)} (${row.pekerjaan_count || 0} pekerjaan, ${subCount} sub)</option>`;
        }).join('');
        refs.modalKlasifikasi.innerHTML = optionsHtml;
      }
    }
  };

  const getSubOptions = () => {
    const subs = [];

    // PHASE 5 UI FIX 1.2: Only show subs for selected klasifikasi
    const selectedKlasifikasi = currentFilter.klasifikasi_ids.length > 0
      ? currentFilter.klasifikasi_ids
      : null;

    filterMeta.klasifikasi.forEach((row) => {
      // If klasifikasi filter is active, only include subs from selected klasifikasi
      if (selectedKlasifikasi === null || selectedKlasifikasi.includes(row.id)) {
        (row.sub || []).forEach((sub) => subs.push({ ...sub, klasifikasi_id: row.id }));
      }
    });
    return subs;
  };

  const renderSubOptions = () => {
    if (!refs.subMenu) return;
    const subs = getSubOptions();

    // PHASE 5 UI FIX 1.2: Show appropriate message when klasifikasi is selected
    if (!subs.length) {
      if (currentFilter.klasifikasi_ids.length > 0) {
        refs.subMenu.innerHTML = '<div class="text-muted small px-2 py-1">Tidak ada sub-klasifikasi untuk klasifikasi yang dipilih</div>';
      } else {
        refs.subMenu.innerHTML = '<div class="text-muted small px-2 py-1">Belum ada sub-klasifikasi</div>';
      }
      return;
    }

    const html = subs.map((sub) => {
      const checked = currentFilter.sub_klasifikasi_ids.includes(sub.id);
      const klasifikasi = filterMeta.klasifikasi.find(k => k.id === sub.klasifikasi_id);
      const klasifikasiName = klasifikasi ? klasifikasi.name : '';

      return `<label class="rk-dropdown-item">
        <input type="checkbox" class="form-check-input sub-check" value="${sub.id}" data-klasifikasi-id="${sub.klasifikasi_id}" ${checked ? 'checked' : ''}>
        <span>${esc(sub.name)} <small class="text-muted">(${klasifikasiName})</small></span>
      </label>`;
    }).join('');
    refs.subMenu.innerHTML = html;
  };

  const renderPekerjaanOptions = (keyword = '') => {
    if (!refs.pekerjaanMenu) return;
    const normalized = keyword.trim().toLowerCase();
    let list = filterMeta.pekerjaan || [];
    if (normalized) {
      list = list.filter((row) => (
        (row.kode || '').toLowerCase().includes(normalized)
        || (row.nama || '').toLowerCase().includes(normalized)
      ));
    }
    if (!list.length) {
      refs.pekerjaanMenu.innerHTML = '<div class="text-muted small px-2 py-1">Tidak ada pekerjaan cocok</div>';
      return;
    }
    const html = list.map((row) => {
      const checked = currentFilter.pekerjaan_ids.includes(row.id);
      return `<label class="rk-dropdown-item">
        <input type="checkbox" class="form-check-input pekerjaan-check" value="${row.id}" ${checked ? 'checked' : ''}>
        <span>${esc(row.kode)} – ${esc(row.nama)} <small class="text-muted">(Tahapan: ${row.tahapan_count || 0})</small></span>
      </label>`;
    }).join('');
    refs.pekerjaanMenu.innerHTML = html;
  };
  const renderPeriodControls = () => {
    if (!refs.periodMode || !refs.periodStart || !refs.periodEnd) return;
    const mode = currentFilter.period_mode || 'all';
    refs.periodMode.value = mode;

    // PHASE 5 UI FIX 1.1: Show/hide period details based on mode
    const periodDetails = $('#rk-period-details');
    const periodEndWrapper = $('#rk-period-end-wrapper');

    if (mode === 'all') {
      // Hide period details when mode is 'all'
      if (periodDetails) {
        periodDetails.style.display = 'none';
        periodDetails.classList.remove('show');
      }
    } else {
      // Show period details
      if (periodDetails) {
        periodDetails.style.display = 'flex';
        periodDetails.classList.add('show');
      }

      // Show/hide end date based on range mode
      if (periodEndWrapper) {
        periodEndWrapper.style.display = mode.endsWith('range') ? 'block' : 'none';
      }

      const options = getPeriodOptionsForMode(mode);
      const optionHtml = options.map((item) => `<option value="${item.value}">${esc(item.label)}</option>`).join('');

      refs.periodStart.innerHTML = `<option value="">Pilih salah satu</option>${optionHtml}`;
      refs.periodStart.value = currentFilter.period_start || '';

      if (mode.endsWith('range')) {
        refs.periodEnd.innerHTML = `<option value="">Sama seperti mulai</option>${optionHtml}`;
        refs.periodEnd.value = currentFilter.period_end || '';
      }
    }

    // Update visual active states
    updateFilterActiveStates();
  };

  // PHASE 5 UI FIX 1.1: Update visual active states for filter steps
  const updateFilterActiveStates = () => {
    const tahapanStep = $('.rk-filter-step[data-step="1"]');
    const periodStep = $('.rk-filter-step[data-step="2"]');

    if (tahapanStep) {
      tahapanStep.classList.toggle('filter-active', currentFilter.mode === 'tahapan' && currentFilter.tahapan_id);
    }

    if (periodStep) {
      periodStep.classList.toggle('filter-active', currentFilter.period_mode !== 'all');
    }
  };

  const syncFilterControls = () => {
    renderKlasifikasiOptions();
    renderSubOptions();
    renderPekerjaanOptions(refs.pekerjaanSearch ? refs.pekerjaanSearch.value : '');
    renderPeriodControls();
    updateDropdownLabels();
    updateTahapanLabel();
  };

  const loadFilterOptions = async () => {
    if (!filtersEndpoint) return;
    try {
      const data = await apiCall(filtersEndpoint);
      filterMeta = {
        klasifikasi: data.klasifikasi || [],
        pekerjaan: data.pekerjaan || [],
        periods: data.periods || { weeks: [], months: [] },
      };
      syncFilterControls();
    } catch (error) {
      console.error('[rk] gagal memuat metadata filter', error);
    }
  };

  const applyFilter = () => {
    updateDropdownLabels();
    updateFilterIndicator();
    updateScopeIndicator();
    renderActiveFilterChips(); // PHASE 5: Update filter chips
    refreshActiveView();
  };

  const resetFilter = () => {
    currentFilter = defaultFilter();
    if (refs.searchInput) refs.searchInput.value = '';
    if (refs.pekerjaanSearch) refs.pekerjaanSearch.value = '';
    syncFilterControls();
    updateFilterIndicator();
    updateScopeIndicator();
    renderActiveFilterChips(); // PHASE 5: Update filter chips
    refreshActiveView();
  };

  const buildQueryString = () => {
    const params = new URLSearchParams(buildQueryParams());
    const queryString = params.toString();
    return queryString ? `?${queryString}` : '';
  };

  const loadRekapKebutuhan = async () => {
    setLoading(true);
    try {
      const query = buildQueryString();

      // Fetch both Keseluruhan and Timeline data in parallel
      const [keseluruhanData, timelineData] = await Promise.all([
        apiCall(`${endpoint}${query}`),
        timelineEndpoint ? apiCall(`${timelineEndpoint}?aggregate=1&full_range=1`) : Promise.resolve(null)
      ]);

      lastData = keseluruhanData; // PHASE 5 TRACK 3.1: Store for autocomplete cache
      let rows = keseluruhanData.rows || [];

      // Cross-reference with Timeline data to determine is_scheduled
      if (timelineData && timelineData.aggregated_items) {
        const scheduledItemKeys = new Set(
          timelineData.aggregated_items.map(item =>
            `${item.kategori}|${item.kode}|${item.uraian}|${item.satuan}`
          )
        );

        // Mark each row as scheduled/unscheduled
        rows = rows.map(row => ({
          ...row,
          is_scheduled: scheduledItemKeys.has(
            `${row.kategori}|${row.kode}|${row.uraian}|${row.satuan}`
          )
        }));

        console.log('[Keseluruhan] Scheduled items from Timeline:', scheduledItemKeys.size);
      }

      renderRows(rows);
      updateStats(keseluruhanData.meta || {}, rows);  // Pass rows for fallback total calculation
      updateScopeIndicator(keseluruhanData.meta || {});
      updateFilterIndicator();
      updateAnalyticsFromRows(rows);
      // Phase 1.2: Update warning badge for pekerjaan without progress
      updateProgressWarning(keseluruhanData.meta?.pekerjaan_without_progress || []);
    } catch (error) {
      console.error('[rk] gagal memuat rekap kebutuhan', error);
      showToast('Gagal memuat data: ' + error.message, 'danger');
      renderRows([]);
      setEmptyState(true);
    } finally {
      setLoading(false);
    }
  };

  const loadTimelineData = async () => {
    if (!timelineEndpoint) return;
    setTimelineLoading(true);
    try {
      // Phase 4: Build query with aggregate mode and time scope from range picker
      let queryParams = buildQueryParams();

      // Add aggregate mode
      queryParams.aggregate = 'true';

      // Build time_scope from range picker state
      if (typeof timelineRangeState !== 'undefined') {
        const mode = timelineRangeState.mode || 'week';
        const options = mode === 'week'
          ? (filterMeta.periods?.weeks || [])
          : (filterMeta.periods?.months || []);

        const startOpt = options[timelineRangeState.startIdx || 0];
        const endOpt = options[timelineRangeState.endIdx || 0];

        if (startOpt && endOpt) {
          // Use correct parameter names that backend expects
          queryParams.period_mode = mode + '_range';
          queryParams.period_start = startOpt.value;
          queryParams.period_end = endOpt.value;
        }
      }

      const queryString = new URLSearchParams(queryParams).toString();
      const url = queryString ? `${timelineEndpoint}?${queryString}` : timelineEndpoint;

      const data = await apiCall(url);

      // Debug: log aggregation data
      console.log('[Timeline Debug]', {
        url,
        aggregated_total: data.aggregated_total,
        unscheduled_total: data.unscheduled_total,
        period_totals: data.period_totals,
        period_labels: data.period_labels,
        item_count: data.aggregated_items?.length
      });

      // Phase 4: Check for aggregated response
      if (data.aggregated_items) {
        renderAggregatedTimeline(data.aggregated_items, data.period_labels || [], data.period_totals || [], data.unscheduled_total || 0);
      } else {
        // Fallback to old per-period rendering
        let periods = data.periods || [];
        if (typeof timelineRangeState !== 'undefined' && periods.length > 0) {
          const start = timelineRangeState.startIdx || 0;
          const end = timelineRangeState.endIdx ?? Math.min(3, periods.length - 1);
          periods = periods.slice(start, end + 1);
        }
        renderTimeline(periods);
        updateAnalyticsFromTimeline(periods);
      }
    } catch (error) {
      console.error('[rk] gagal memuat timeline', error);
      showToast('Gagal memuat timeline: ' + error.message, 'danger');
      renderAggregatedTimeline([], []);
    } finally {
      setTimelineLoading(false);
    }
  };
  const refreshActiveView = () => {
    if (currentViewMode === 'timeline') {
      if (refs.tableWrap) refs.tableWrap.classList.add('d-none');
      if (refs.timelineWrap) refs.timelineWrap.classList.remove('d-none');
      loadTimelineData();
    } else {
      if (refs.tableWrap) refs.tableWrap.classList.remove('d-none');
      if (refs.timelineWrap) refs.timelineWrap.classList.add('d-none');
      loadRekapKebutuhan();
    }
  };

  const setViewMode = (mode) => {
    if (mode === currentViewMode) return;
    currentViewMode = mode;
    refs.viewToggleButtons.forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.view === mode);
    });

    // Toggle toolbar range picker visibility
    const toolbarRangePicker = $('#rk-toolbar-range-picker');
    if (toolbarRangePicker) {
      toolbarRangePicker.classList.toggle('d-none', mode !== 'timeline');
    }

    // Update scope indicator to reflect view mode change
    updateScopeIndicator();

    // Smooth transition between views
    if (mode === 'timeline') {
      // Fade out snapshot view
      if (refs.tableWrap) {
        refs.tableWrap.style.opacity = '0';
        refs.tableWrap.style.transform = 'translateY(10px)';
      }

      setTimeout(() => {
        if (refs.tableWrap) refs.tableWrap.classList.add('d-none');
        if (refs.timelineWrap) {
          refs.timelineWrap.classList.remove('d-none');
          // Trigger reflow to ensure animation
          void refs.timelineWrap.offsetWidth;
          refs.timelineWrap.style.opacity = '1';
          refs.timelineWrap.style.transform = 'translateY(0)';
        }
        loadTimelineData();
      }, 300);
    } else {
      // Fade out timeline view
      if (refs.timelineWrap) {
        refs.timelineWrap.style.opacity = '0';
        refs.timelineWrap.style.transform = 'translateY(10px)';
      }

      setTimeout(() => {
        if (refs.timelineWrap) refs.timelineWrap.classList.add('d-none');
        if (refs.tableWrap) {
          refs.tableWrap.classList.remove('d-none');
          // Trigger reflow to ensure animation
          void refs.tableWrap.offsetWidth;
          refs.tableWrap.style.opacity = '1';
          refs.tableWrap.style.transform = 'translateY(0)';
        }
        loadRekapKebutuhan();
      }, 300);
    }
  };

  // PHASE 5: Enhanced Export with State Fidelity & Progress Feedback
  const generateExportFilename = (format) => {
    const timestamp = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
    const parts = ['rekap-kebutuhan'];

    // Add view mode
    if (currentViewMode === 'timeline') {
      parts.push('timeline');
    }

    // Add scope
    if (currentFilter.mode === 'tahapan' && currentFilter.tahapan_id) {
      parts.push(`tahapan-${currentFilter.tahapan_id}`);
    }

    // Add kategori filter if not all
    if (currentFilter.kategori.length && currentFilter.kategori.length < 4) {
      parts.push(currentFilter.kategori.join('-'));
    }

    // Add period if specified
    if (currentFilter.period_mode && currentFilter.period_mode !== 'all') {
      parts.push(currentFilter.period_mode);
      if (currentFilter.period_start) {
        parts.push(currentFilter.period_start);
      }
    }

    parts.push(timestamp);
    return parts.join('_') + '.' + format;
  };

  const showExportProgress = () => {
    showToast(
      '<div class="d-flex align-items-center gap-2">' +
      '<div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div>' +
      '<span>Memproses export... Mohon tunggu.</span>' +
      '</div>',
      'info',
      3000
    );
  };

  const initExportButtons = () => {
    const exporter = window.ExportManager ? new window.ExportManager(projectId, 'rekap-kebutuhan') : null;
    const triggerExport = async (format) => {
      // Show progress feedback
      showExportProgress();

      const query = buildQueryParams();

      // PHASE 5: Add view mode and filename to query
      query.view_mode = currentViewMode;
      query.filename = generateExportFilename(format).replace('.' + format, ''); // Send without extension

      if (exporter) {
        try {
          await exporter.exportAs(format, { query });
          return;
        } catch (error) {
          showToast('Export gagal: ' + error.message, 'danger');
          return;
        }
      }
      const map = { csv: exportCsvUrl, pdf: exportPdfUrl, word: exportWordUrl };
      const base = map[format];
      if (!base) return;
      const params = new URLSearchParams(query).toString();
      const url = params ? `${base}?${params}` : base;
      window.open(url, '_blank');
    };

    const btnCsv = $('#btn-export-csv');
    const btnPdf = $('#btn-export-pdf');
    const btnWord = $('#btn-export-word');
    const btnCharts = $('#btn-export-charts');
    const btnExportModal = $('#btn-export-modal');

    if (btnCsv) btnCsv.addEventListener('click', () => triggerExport('csv'));
    if (btnPdf) btnPdf.addEventListener('click', () => triggerExport('pdf'));
    if (btnWord) btnWord.addEventListener('click', () => triggerExport('word'));
    if (btnCharts) btnCharts.addEventListener('click', exportChartsAsImages);
    if (btnExportModal) btnExportModal.addEventListener('click', openExportModal);

    // Initialize export modal
    initExportModal(triggerExport);
  };

  // Phase 2: Export Modal Logic
  const openExportModal = () => {
    const modal = $('#rk-export-modal');
    if (modal && typeof bootstrap !== 'undefined') {
      const bsModal = new bootstrap.Modal(modal);
      bsModal.show();
    }
  };

  const initExportModal = (triggerExport) => {
    const modal = $('#rk-export-modal');
    if (!modal) return;

    const periodRadios = $$('input[name="exportPeriod"]', modal);
    const periodDetails = $('#rk-export-period-details');
    const periodLabel = $('#rk-export-period-label');
    const periodStart = $('#rk-export-period-start');
    const periodEnd = $('#rk-export-period-end');
    const confirmBtn = $('#rk-export-confirm');
    const statusEl = $('#rk-export-status');
    const statusText = $('#rk-export-status-text');

    // Handle period type change
    periodRadios.forEach(radio => {
      radio.addEventListener('change', () => {
        const value = radio.value;
        if (value === 'all') {
          if (periodDetails) periodDetails.style.display = 'none';
        } else {
          if (periodDetails) periodDetails.style.display = 'block';
          if (periodLabel) periodLabel.textContent = value === 'week' ? 'Minggu' : 'Bulan';
          populateExportPeriodOptions(value);
        }
      });
    });

    // Populate period options based on filterMeta
    const populateExportPeriodOptions = (mode) => {
      if (!periodStart || !periodEnd) return;

      const options = mode === 'week' ? filterMeta.periods?.weeks || [] : filterMeta.periods?.months || [];

      const optionsHtml = options.map(opt =>
        `<option value="${opt.value}">${opt.label}</option>`
      ).join('');

      periodStart.innerHTML = optionsHtml;
      periodEnd.innerHTML = optionsHtml;

      // Set end to last option
      if (periodEnd.options.length > 0) {
        periodEnd.selectedIndex = periodEnd.options.length - 1;
      }
    };

    // Handle export confirm
    if (confirmBtn) {
      confirmBtn.addEventListener('click', async () => {
        const format = document.querySelector('input[name="rkExportFormat"]:checked')?.value || 'pdf';
        const periodType = document.querySelector('input[name="exportPeriod"]:checked')?.value || 'all';

        // Build export params
        const exportParams = { ...buildQueryParams() };

        if (periodType !== 'all') {
          exportParams.period_mode = periodType === 'week' ? 'week_range' : 'month_range';
          exportParams.period_start = periodStart?.value || '';
          exportParams.period_end = periodEnd?.value || '';
        }

        // Show status
        if (statusEl) statusEl.classList.remove('d-none');
        if (statusText) statusText.textContent = `Memproses export ${format.toUpperCase()}...`;
        confirmBtn.disabled = true;

        try {
          // Use same export logic but with custom params
          const exporter = window.ExportManager ? new window.ExportManager(projectId, 'rekap-kebutuhan') : null;
          exportParams.view_mode = currentViewMode;
          exportParams.filename = generateExportFilename(format).replace('.' + format, '');

          if (exporter) {
            await exporter.exportAs(format, { query: exportParams });
          } else {
            const map = { csv: exportCsvUrl, pdf: exportPdfUrl, word: exportWordUrl };
            const base = map[format];
            if (base) {
              const params = new URLSearchParams(exportParams).toString();
              const url = params ? `${base}?${params}` : base;
              window.open(url, '_blank');
            }
          }

          if (statusText) statusText.textContent = 'Export berhasil!';
          if (statusEl) statusEl.classList.replace('alert-info', 'alert-success');

          // Close modal after 1.5s
          setTimeout(() => {
            bootstrap.Modal.getInstance(modal)?.hide();
            // Reset status
            if (statusEl) {
              statusEl.classList.add('d-none');
              statusEl.classList.replace('alert-success', 'alert-info');
            }
          }, 1500);
        } catch (error) {
          if (statusText) statusText.textContent = 'Export gagal: ' + error.message;
          if (statusEl) statusEl.classList.replace('alert-info', 'alert-danger');
        } finally {
          confirmBtn.disabled = false;
        }
      });
    }
  };

  // PHASE 5 UI FIX 2: Export material mix diagram
  const exportChartsAsImages = () => {
    try {
      showToast('Memproses export chart...', 'info', 2000);

      // Export Mix Chart (Pie Chart)
      if (chartMixInstance) {
        const mixDataURL = chartMixInstance.getDataURL({
          type: 'png',
          pixelRatio: 2,
          backgroundColor: '#fff'
        });
        downloadImage(mixDataURL, 'komposisi-biaya-material-mix.png');
      }

      // Export Cost Chart (Bar Chart)
      if (chartCostInstance) {
        const costDataURL = chartCostInstance.getDataURL({
          type: 'png',
          pixelRatio: 2,
          backgroundColor: '#fff'
        });
        downloadImage(costDataURL, 'top-biaya-per-item.png');
      }

      if (!chartMixInstance && !chartCostInstance) {
        showToast('Tidak ada chart untuk di-export', 'warning');
        return;
      }

      showToast('Chart berhasil di-export!', 'success');
    } catch (error) {
      console.error('Chart export failed:', error);
      showToast('Export chart gagal: ' + error.message, 'danger');
    }
  };

  const downloadImage = (dataURL, filename) => {
    const link = document.createElement('a');
    link.download = filename;
    link.href = dataURL;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const parseInitialParams = () => {
    const params = new URLSearchParams(window.location.search);
    const toIds = (key) => {
      const raw = params.get(key);
      if (!raw) return [];
      return raw.split(',').map((val) => parseInt(val, 10)).filter(Number.isFinite);
    };
    if ((params.get('mode') || '').toLowerCase() === 'tahapan') {
      currentFilter.mode = 'tahapan';
      currentFilter.tahapan_id = parseInt(params.get('tahapan_id'), 10) || null;
    }
    currentFilter.klasifikasi_ids = toIds('klasifikasi');
    currentFilter.sub_klasifikasi_ids = toIds('sub_klasifikasi');
    currentFilter.pekerjaan_ids = toIds('pekerjaan');
    const kategoriRaw = params.get('kategori');
    if (kategoriRaw) {
      const allowed = ['TK', 'BHN', 'ALT', 'LAIN'];
      const selected = kategoriRaw.split(',').map((val) => val.trim().toUpperCase()).filter((val) => allowed.includes(val));
      if (selected.length) {
        currentFilter.kategori = selected;
      }
    }
    if (params.get('search')) {
      currentFilter.search = params.get('search') || '';
      if (refs.searchInput) refs.searchInput.value = currentFilter.search;
    }
    if (params.get('period_mode')) {
      currentFilter.period_mode = params.get('period_mode');
      currentFilter.period_start = params.get('period_start') || '';
      currentFilter.period_end = params.get('period_end') || '';
    }
  };

  const debounce = (fn, delay = 300) => {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(null, args), delay);
    };
  };
  // ============================================================================
  // PHASE 5 TRACK 3.1: SEARCH AUTOCOMPLETE
  // ============================================================================

  let autocompleteCache = new Set();
  let autocompleteDropdown = null;

  const initSearchAutocomplete = () => {
    if (!refs.searchInput) return;

    // Create autocomplete dropdown
    const dropdown = document.createElement('div');
    dropdown.className = 'rk-autocomplete-dropdown';
    dropdown.style.cssText = `
      position: absolute;
      z-index: 1050;
      background: white;
      border: 1px solid var(--bs-border-color);
      border-radius: 0.375rem;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      max-height: 300px;
      overflow-y: auto;
      display: none;
      min-width: 250px;
    `;

    refs.searchInput.parentElement.style.position = 'relative';
    refs.searchInput.parentElement.appendChild(dropdown);
    autocompleteDropdown = dropdown;

    // Build autocomplete cache from current data
    const buildAutocompleteCache = () => {
      autocompleteCache.clear();
      if (!lastData || !lastData.rows) return;

      lastData.rows.forEach(row => {
        if (row.kode) autocompleteCache.add(row.kode.toLowerCase());
        if (row.uraian) {
          // Add full uraian
          autocompleteCache.add(row.uraian.toLowerCase());
          // Add words from uraian (for partial matching)
          row.uraian.toLowerCase().split(/\s+/).forEach(word => {
            if (word.length > 3) autocompleteCache.add(word);
          });
        }
      });
    };

    const showAutocomplete = (suggestions) => {
      if (!suggestions || suggestions.length === 0) {
        autocompleteDropdown.style.display = 'none';
        return;
      }

      // Position dropdown
      const rect = refs.searchInput.getBoundingClientRect();
      autocompleteDropdown.style.top = `${refs.searchInput.offsetHeight}px`;
      autocompleteDropdown.style.left = '0';
      autocompleteDropdown.style.width = `${rect.width}px`;

      // Build dropdown HTML
      const html = suggestions.map((suggestion, index) => {
        const escaped = esc(suggestion);
        return `
          <div class="rk-autocomplete-item" data-index="${index}" data-value="${escaped}">
            <i class="bi bi-search me-2"></i>
            ${escaped}
          </div>
        `;
      }).join('');

      autocompleteDropdown.innerHTML = html;
      autocompleteDropdown.style.display = 'block';

      // Add hover and click handlers
      autocompleteDropdown.querySelectorAll('.rk-autocomplete-item').forEach(item => {
        item.style.cssText = `
          padding: 0.75rem 1rem;
          cursor: pointer;
          transition: background 0.2s ease;
          border-bottom: 1px solid var(--bs-border-color-translucent);
        `;

        item.addEventListener('mouseenter', () => {
          item.style.background = 'rgba(13, 110, 252, 0.1)';
        });

        item.addEventListener('mouseleave', () => {
          item.style.background = 'white';
        });

        item.addEventListener('click', () => {
          refs.searchInput.value = item.dataset.value;
          currentFilter.search = item.dataset.value;
          autocompleteDropdown.style.display = 'none';
          refreshActiveView();
        });
      });
    };

    const hideAutocomplete = () => {
      if (autocompleteDropdown) {
        autocompleteDropdown.style.display = 'none';
      }
    };

    const getSuggestions = (query) => {
      if (!query || query.length < 2) return [];

      const lowerQuery = query.toLowerCase();
      const matches = Array.from(autocompleteCache)
        .filter(item => item.includes(lowerQuery))
        .sort((a, b) => {
          // Prioritize items that start with query
          const aStarts = a.startsWith(lowerQuery);
          const bStarts = b.startsWith(lowerQuery);
          if (aStarts && !bStarts) return -1;
          if (!aStarts && bStarts) return 1;
          return a.length - b.length; // Shorter items first
        })
        .slice(0, 10); // Limit to 10 suggestions

      return matches;
    };

    // Rebuild cache when data changes
    const originalRefreshActiveView = refreshActiveView;
    window.refreshActiveView = async function () {
      await originalRefreshActiveView();
      buildAutocompleteCache();
    };

    // Hide autocomplete when clicking outside
    document.addEventListener('click', (e) => {
      if (!refs.searchInput.contains(e.target) && !autocompleteDropdown.contains(e.target)) {
        hideAutocomplete();
      }
    });

    // Keyboard navigation
    let selectedIndex = -1;
    refs.searchInput.addEventListener('keydown', (e) => {
      const items = autocompleteDropdown.querySelectorAll('.rk-autocomplete-item');

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
        updateSelection(items);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, -1);
        updateSelection(items);
      } else if (e.key === 'Enter' && selectedIndex >= 0) {
        e.preventDefault();
        items[selectedIndex].click();
      } else if (e.key === 'Escape') {
        hideAutocomplete();
        selectedIndex = -1;
      }
    });

    const updateSelection = (items) => {
      items.forEach((item, index) => {
        if (index === selectedIndex) {
          item.style.background = 'rgba(13, 110, 252, 0.2)';
          item.scrollIntoView({ block: 'nearest' });
        } else {
          item.style.background = 'white';
        }
      });
    };

    // Attach to search input
    refs.searchInput.addEventListener('input', debounce((event) => {
      const query = event.target.value || '';
      selectedIndex = -1;

      if (query.length >= 2) {
        const suggestions = getSuggestions(query);
        showAutocomplete(suggestions);
      } else {
        hideAutocomplete();
      }

      currentFilter.search = query.trim();
      refreshActiveView();
    }, 300));

    // Focus handler
    refs.searchInput.addEventListener('focus', () => {
      const query = refs.searchInput.value || '';
      if (query.length >= 2) {
        const suggestions = getSuggestions(query);
        showAutocomplete(suggestions);
      }
    });

    // Build initial cache
    buildAutocompleteCache();
  };

  // ============================================================================
  // PHASE 5 TRACK 3.2: QUICK FILTER CHIPS
  // ============================================================================

  const renderActiveFilterChips = () => {
    const chipsContainer = $('#rk-filter-chips');
    const activeFiltersContainer = $('#rk-active-filters');

    if (!chipsContainer || !activeFiltersContainer) return;

    const chips = [];

    // Kategori chips
    if (currentFilter.kategori.length > 0 && currentFilter.kategori.length < 4) {
      const kategoriMap = { TK: 'Tenaga Kerja', BHN: 'Bahan', ALT: 'Alat', LAIN: 'Lain-lain' };
      currentFilter.kategori.forEach(kat => {
        chips.push({
          type: 'kategori',
          value: kat,
          label: kategoriMap[kat] || kat,
          color: 'primary'
        });
      });
    }

    // Klasifikasi chips
    if (currentFilter.klasifikasi_ids.length > 0) {
      currentFilter.klasifikasi_ids.forEach(id => {
        const option = filterOptions.klasifikasi.find(k => k.id === id);
        if (option) {
          chips.push({
            type: 'klasifikasi',
            value: id,
            label: option.nama,
            color: 'success'
          });
        }
      });
    }

    // Sub-klasifikasi chips
    if (currentFilter.sub_klasifikasi_ids.length > 0) {
      currentFilter.sub_klasifikasi_ids.forEach(id => {
        const option = filterOptions.sub_klasifikasi.find(s => s.id === id);
        if (option) {
          chips.push({
            type: 'sub_klasifikasi',
            value: id,
            label: option.nama,
            color: 'info'
          });
        }
      });
    }

    // Pekerjaan chips
    if (currentFilter.pekerjaan_ids.length > 0) {
      currentFilter.pekerjaan_ids.forEach(id => {
        const option = filterOptions.pekerjaan.find(p => p.id === id);
        if (option) {
          chips.push({
            type: 'pekerjaan',
            value: id,
            label: option.nama,
            color: 'warning'
          });
        }
      });
    }

    // Period mode chip
    if (currentFilter.period_mode && currentFilter.period_mode !== 'all') {
      const periodLabels = {
        'weekly': 'Mode Mingguan',
        'monthly': 'Mode Bulanan',
        'weekly_range': 'Range Mingguan',
        'monthly_range': 'Range Bulanan'
      };
      chips.push({
        type: 'period_mode',
        value: currentFilter.period_mode,
        label: periodLabels[currentFilter.period_mode] || currentFilter.period_mode,
        color: 'secondary'
      });
    }

    // Search chip
    if (currentFilter.search && currentFilter.search.trim()) {
      chips.push({
        type: 'search',
        value: currentFilter.search,
        label: `Pencarian: "${currentFilter.search}"`,
        color: 'dark'
      });
    }

    // Render chips
    if (chips.length === 0) {
      activeFiltersContainer.style.display = 'none';
      return;
    }

    activeFiltersContainer.style.display = 'block';

    const html = chips.map(chip => `
      <span class="badge bg-${chip.color} d-inline-flex align-items-center gap-1 py-2 px-3 rk-filter-chip"
            data-type="${chip.type}"
            data-value="${esc(String(chip.value))}"
            style="cursor: pointer; transition: all 0.2s ease;">
        <span>${esc(chip.label)}</span>
        <i class="bi bi-x-circle" style="font-size: 0.875rem;"></i>
      </span>
    `).join('');

    chipsContainer.innerHTML = html;

    // Add click handlers to remove chips
    chipsContainer.querySelectorAll('.rk-filter-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const type = chip.dataset.type;
        const value = chip.dataset.value;

        removeFilterByChip(type, value);
      });

      // Add hover effect
      chip.addEventListener('mouseenter', () => {
        chip.style.opacity = '0.8';
        chip.style.transform = 'scale(0.95)';
      });

      chip.addEventListener('mouseleave', () => {
        chip.style.opacity = '1';
        chip.style.transform = 'scale(1)';
      });
    });
  };

  const removeFilterByChip = (type, value) => {
    switch (type) {
      case 'kategori':
        currentFilter.kategori = currentFilter.kategori.filter(k => k !== value);
        // Uncheck checkbox
        const katCheckbox = document.querySelector(`.kategori-check[value="${value}"]`);
        if (katCheckbox) katCheckbox.checked = false;
        break;

      case 'klasifikasi':
        const klasId = parseInt(value, 10);
        currentFilter.klasifikasi_ids = currentFilter.klasifikasi_ids.filter(id => id !== klasId);
        // Uncheck checkbox
        const klasCheckbox = document.querySelector(`.klasifikasi-check[value="${klasId}"]`);
        if (klasCheckbox) klasCheckbox.checked = false;
        break;

      case 'sub_klasifikasi':
        const subId = parseInt(value, 10);
        currentFilter.sub_klasifikasi_ids = currentFilter.sub_klasifikasi_ids.filter(id => id !== subId);
        // Uncheck checkbox
        const subCheckbox = document.querySelector(`.sub-check[value="${subId}"]`);
        if (subCheckbox) subCheckbox.checked = false;
        break;

      case 'pekerjaan':
        const pekId = parseInt(value, 10);
        currentFilter.pekerjaan_ids = currentFilter.pekerjaan_ids.filter(id => id !== pekId);
        // Uncheck checkbox
        const pekCheckbox = document.querySelector(`.pekerjaan-check[value="${pekId}"]`);
        if (pekCheckbox) pekCheckbox.checked = false;
        break;

      case 'period_mode':
        currentFilter.period_mode = 'all';
        currentFilter.period_start = '';
        currentFilter.period_end = '';
        if (refs.periodMode) refs.periodMode.value = 'all';
        renderPeriodControls();
        break;

      case 'search':
        currentFilter.search = '';
        if (refs.searchInput) refs.searchInput.value = '';
        break;
    }

    // Update UI
    updateDropdownLabels();
    updateFilterIndicator();
    renderActiveFilterChips();
    refreshActiveView();
  };

  const attachEventListeners = () => {
    if (refs.applyBtn) {
      refs.applyBtn.addEventListener('click', applyFilter);
    }
    if (refs.resetBtn) {
      refs.resetBtn.addEventListener('click', resetFilter);
    }

    // Search autocomplete initialized separately
    initSearchAutocomplete();
    if (refs.pekerjaanSearch) {
      refs.pekerjaanSearch.addEventListener('input', debounce((event) => {
        renderPekerjaanOptions(event.target.value || '');
      }, 200));
    }

    document.addEventListener('change', (event) => {
      const target = event.target;
      if (target.matches('.kategori-check')) {
        const selected = $$('.kategori-check').filter((cb) => cb.checked).map((cb) => cb.value);
        currentFilter.kategori = selected.length ? selected : [];
        updateDropdownLabels();
      }
      if (target.matches('.klasifikasi-check')) {
        const values = $$('.klasifikasi-check').filter((cb) => cb.checked).map((cb) => parseInt(cb.value, 10)).filter(Number.isFinite);
        currentFilter.klasifikasi_ids = values;

        // PHASE 5 UI FIX 1.2: Auto-clear invalid sub-klasifikasi selections
        if (values.length > 0) {
          const validSubs = getSubOptions();
          const validSubIds = validSubs.map(s => s.id);
          currentFilter.sub_klasifikasi_ids = currentFilter.sub_klasifikasi_ids.filter(id => validSubIds.includes(id));
        }

        // Re-render sub-klasifikasi dropdown to show filtered options
        renderSubOptions();
        updateDropdownLabels();
      }

      // Handle modal select element (#rk-klasifikasi)
      if (target.id === 'rk-klasifikasi') {
        const selectedOptions = Array.from(target.selectedOptions);
        const values = selectedOptions.map(opt => parseInt(opt.value, 10)).filter(Number.isFinite);
        currentFilter.klasifikasi_ids = values;

        // Sync with checkbox menu
        $$('.klasifikasi-check').forEach(cb => {
          cb.checked = values.includes(parseInt(cb.value, 10));
        });

        renderSubOptions();
        updateDropdownLabels();
      }
      if (target.matches('.sub-check')) {
        const values = $$('.sub-check').filter((cb) => cb.checked).map((cb) => parseInt(cb.value, 10)).filter(Number.isFinite);
        currentFilter.sub_klasifikasi_ids = values;
        updateDropdownLabels();
      }
      if (target.matches('.pekerjaan-check')) {
        const values = $$('.pekerjaan-check').filter((cb) => cb.checked).map((cb) => parseInt(cb.value, 10)).filter(Number.isFinite);
        currentFilter.pekerjaan_ids = values;
        updateDropdownLabels();
      }
      if (target === refs.periodMode) {
        currentFilter.period_mode = target.value || 'all';
        if (currentFilter.period_mode === 'all') {
          currentFilter.period_start = '';
          currentFilter.period_end = '';
        }
        renderPeriodControls();
      }
      if (target === refs.periodStart) {
        currentFilter.period_start = target.value;
        if (!currentFilter.period_mode || !currentFilter.period_mode.endsWith('range')) {
          currentFilter.period_end = '';
        }
      }
      if (target === refs.periodEnd) {
        currentFilter.period_end = target.value;
      }
    });

    if (refs.viewToggleButtons.length) {
      refs.viewToggleButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
          const view = btn.dataset.view || 'snapshot';
          setViewMode(view);
        });
      });
    }

    if (refs.costModeToggle) {
      refs.costModeToggle.addEventListener('click', () => {
        costChartMode = costChartMode === 'compact' ? 'full' : 'compact';
        refs.costModeToggle.dataset.mode = costChartMode;
        refs.costModeToggle.textContent = costChartMode === 'compact' ? 'Tampilkan lengkap' : 'Mode ringkas';
        refreshAnalyticsCostMode();
      });
    }

    window.addEventListener('resize', debounce(() => {
      if (chartMixInstance && chartMixInstance.resize) {
        chartMixInstance.resize();
      }
      if (chartCostInstance && chartCostInstance.resize) {
        chartCostInstance.resize();
      }
    }, 200));
  };

  // ============================================================================
  // PHASE 5 TRACK 2.1: DEBUG PANEL & VALIDATION
  // ============================================================================

  const showDebugPanel = async () => {
    showToast('Memuat validasi data...', 'info', 2000);

    try {
      const query = buildQueryParams();
      const response = await fetch(`/detail_project/api/project/${projectId}/rekap-kebutuhan/validate/?${query}`);
      const data = await response.json();

      if (data.status !== 'success') {
        throw new Error(data.message || 'Validation failed');
      }

      const validation = data.validation;

      // Build validation report
      const isValid = validation.valid;
      const statusIcon = isValid ? '✅' : '⚠️';
      const statusText = isValid ? 'VALID' : 'MISMATCH DETECTED';
      const statusClass = isValid ? 'text-success' : 'text-warning';

      // Format currency
      const fmt = (val) => new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(val);

      // Build kategori breakdown table
      let kategoriTable = '';
      if (validation.kategori_breakdown) {
        kategoriTable = '<table class="table table-sm mt-3"><thead><tr><th>Kategori</th><th>Snapshot</th><th>Timeline</th><th>Status</th></tr></thead><tbody>';

        for (const [kategori, breakdown] of Object.entries(validation.kategori_breakdown)) {
          const matchIcon = breakdown.match ? '✅' : '⚠️';
          kategoriTable += `
            <tr>
              <td><strong>${kategori}</strong></td>
              <td>${breakdown.snapshot.count} items<br><small>${fmt(breakdown.snapshot.total)}</small></td>
              <td>${breakdown.timeline.count} items<br><small>${fmt(breakdown.timeline.total)}</small></td>
              <td>${matchIcon} ${breakdown.match ? 'OK' : fmt(breakdown.difference)}</td>
            </tr>
          `;
        }
        kategoriTable += '</tbody></table>';
      }

      // Build warnings list
      let warningsList = '';
      if (validation.warnings && validation.warnings.length > 0) {
        warningsList = '<div class="alert alert-warning mt-3"><strong>Warnings:</strong><ul class="mb-0">';
        validation.warnings.forEach(warning => {
          warningsList += `<li>${esc(warning)}</li>`;
        });
        warningsList += '</ul></div>';
      }

      // Show modal
      const modalHtml = `
        <div class="modal fade" id="debugModal" tabindex="-1">
          <div class="modal-dialog modal-lg">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">🔍 Data Validation Report</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
              </div>
              <div class="modal-body">
                <div class="text-center mb-4">
                  <h3 class="${statusClass}">${statusIcon} ${statusText}</h3>
                  <small class="text-muted">Validated at ${new Date(validation.timestamp).toLocaleString('id-ID')}</small>
                </div>

                <div class="row mb-3">
                  <div class="col-md-6">
                    <div class="card">
                      <div class="card-body text-center">
                        <h6 class="text-muted">Snapshot Total</h6>
                        <h4>${fmt(validation.snapshot_total)}</h4>
                        <small>${validation.snapshot_count} items</small>
                      </div>
                    </div>
                  </div>
                  <div class="col-md-6">
                    <div class="card">
                      <div class="card-body text-center">
                        <h6 class="text-muted">Timeline Total</h6>
                        <h4>${fmt(validation.timeline_total)}</h4>
                        <small>${validation.timeline_count} unique items</small>
                      </div>
                    </div>
                  </div>
                </div>

                ${!isValid ? `
                  <div class="alert alert-info">
                    <strong>Difference:</strong> ${fmt(validation.difference)}<br>
                    <small>Tolerance: ${fmt(validation.tolerance)}</small>
                  </div>
                ` : ''}

                ${kategoriTable}
                ${warningsList}

                <div class="mt-3">
                  <h6>Current Filters:</h6>
                  <code class="d-block p-2 bg-light">${JSON.stringify({
        mode: currentFilter.mode,
        kategori: currentFilter.kategori,
        period_mode: currentFilter.period_mode,
      }, null, 2)}</code>
                </div>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
              </div>
            </div>
          </div>
        </div>
      `;

      // Remove existing modal if any
      const existingModal = document.getElementById('debugModal');
      if (existingModal) {
        existingModal.remove();
      }

      // Append and show modal
      document.body.insertAdjacentHTML('beforeend', modalHtml);
      const modal = new bootstrap.Modal(document.getElementById('debugModal'));
      modal.show();

      // Cleanup on close
      document.getElementById('debugModal').addEventListener('hidden.bs.modal', () => {
        document.getElementById('debugModal').remove();
      });

    } catch (error) {
      console.error('Debug panel error:', error);
      showToast(`Validation error: ${error.message}`, 'danger', 5000);
    }
  };

  // Register keyboard shortcut: Ctrl+Shift+D
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.shiftKey && e.key === 'D') {
      e.preventDefault();
      showDebugPanel();
    }
  });

  // Phase 3: Timeline Range Picker Initialization
  let timelineRangeState = {
    mode: 'week', // 'week' or 'month'
    startIdx: 0,
    endIdx: 3, // Default first 4 weeks
    weeks: [],
    months: []
  };

  const initTimelineRangePicker = () => {
    // Legacy in-timeline picker elements
    const startSelect = $('#rk-timeline-start');
    const endSelect = $('#rk-timeline-end');
    const applyBtn = $('#rk-timeline-apply');
    const weekRadio = $('#timelineWeek');
    const monthRadio = $('#timelineMonth');

    // NEW: Toolbar compact range picker elements
    const toolbarStartSelect = $('#rk-toolbar-range-start');
    const toolbarEndSelect = $('#rk-toolbar-range-end');
    const toolbarRangeTypeButtons = $$('#rk-toolbar-range-picker [data-range-type]');

    if (!startSelect && !toolbarStartSelect) return;

    // Populate from filterMeta periods
    const populateRangeOptions = (mode, syncToolbar = true) => {
      timelineRangeState.mode = mode;
      const options = mode === 'week'
        ? (filterMeta.periods?.weeks || [])
        : (filterMeta.periods?.months || []);

      // Store for later filtering
      if (mode === 'week') {
        timelineRangeState.weeks = options;
      } else {
        timelineRangeState.months = options;
      }

      const optionsHtml = options.map((opt, idx) =>
        `<option value="${idx}">${opt.label || opt.value}</option>`
      ).join('') || '<option value="">Tidak ada data</option>';

      // Populate legacy picker
      if (startSelect) startSelect.innerHTML = optionsHtml;
      if (endSelect) endSelect.innerHTML = optionsHtml;

      // Populate toolbar picker
      if (syncToolbar && toolbarStartSelect) toolbarStartSelect.innerHTML = optionsHtml;
      if (syncToolbar && toolbarEndSelect) toolbarEndSelect.innerHTML = optionsHtml;

      // Default: first 4 periods or all if less
      const defaultEnd = Math.min(3, options.length - 1);
      if (startSelect) startSelect.selectedIndex = 0;
      if (endSelect) endSelect.selectedIndex = Math.max(0, defaultEnd);
      if (toolbarStartSelect) toolbarStartSelect.selectedIndex = 0;
      if (toolbarEndSelect) toolbarEndSelect.selectedIndex = Math.max(0, defaultEnd);

      timelineRangeState.startIdx = 0;
      timelineRangeState.endIdx = defaultEnd;
    };

    // Initial populate
    populateRangeOptions('week');

    // Handle mode toggle (legacy radio buttons)
    if (weekRadio) {
      weekRadio.addEventListener('change', () => {
        if (weekRadio.checked) {
          populateRangeOptions('week');
        }
      });
    }

    if (monthRadio) {
      monthRadio.addEventListener('change', () => {
        if (monthRadio.checked) {
          populateRangeOptions('month');
        }
      });
    }

    // Handle apply button (legacy)
    if (applyBtn) {
      applyBtn.addEventListener('click', () => {
        timelineRangeState.startIdx = parseInt(startSelect.value) || 0;
        timelineRangeState.endIdx = parseInt(endSelect.value) || 0;
        loadTimelineDataWithRange();
      });
    }

    // NEW: Toolbar range type toggle
    toolbarRangeTypeButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const mode = btn.dataset.rangeType;
        toolbarRangeTypeButtons.forEach(b => b.classList.toggle('active', b === btn));
        populateRangeOptions(mode, true);
        // Auto-apply on mode change
        if (currentViewMode === 'timeline') {
          loadTimelineDataWithRange();
        }
      });
    });

    // NEW: Toolbar range selects - auto-apply on change
    if (toolbarStartSelect) {
      toolbarStartSelect.addEventListener('change', () => {
        timelineRangeState.startIdx = parseInt(toolbarStartSelect.value) || 0;
        // Sync legacy picker
        if (startSelect) startSelect.value = toolbarStartSelect.value;
        if (currentViewMode === 'timeline') {
          loadTimelineDataWithRange();
        }
      });
    }

    if (toolbarEndSelect) {
      toolbarEndSelect.addEventListener('change', () => {
        timelineRangeState.endIdx = parseInt(toolbarEndSelect.value) || 0;
        // Sync legacy picker
        if (endSelect) endSelect.value = toolbarEndSelect.value;
        if (currentViewMode === 'timeline') {
          loadTimelineDataWithRange();
        }
      });
    }

    console.log('📅 Timeline range picker initialized (toolbar + legacy)');
  };

  // Modified timeline loader with range filter - uses same aggregate mode
  const loadTimelineDataWithRange = async () => {
    // Simply call loadTimelineData - it already uses timelineRangeState
    await loadTimelineData();
  };


  const init = async () => {
    console.log('🚀 Initializing Rekap Kebutuhan...');

    parseInitialParams();
    await loadFilterOptions();
    await loadTahapan();
    updateFilterIndicator();
    updateScopeIndicator();
    attachEventListeners();
    initExportButtons();
    initTimelineRangePicker(); // Phase 3: Timeline range picker
    initializeUXEnhancements(); // UX Enhancement: Ripple effects & animations
    refreshActiveView();

    console.log('✅ Rekap Kebutuhan initialized');
    console.log('💡 Press Ctrl+Shift+D to open debug panel');
  };

  init();
})();

