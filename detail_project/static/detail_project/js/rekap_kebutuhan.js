
// static/detail_project/js/rekap_kebutuhan.js
// Fully rebuilt client for Rekap Kebutuhan page with advanced filtering & insights

(function () {
  'use strict';

  const app = document.getElementById('rk-app');
  if (!app) {
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
  const currencyFormatter = new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 2,
  });

  const formatQtyValue = (value) => {
    const num = Number(value);
    if (!Number.isFinite(num)) return '-';
    return qtyFormatter.format(num);
  };

  const formatCurrencyValue = (value) => {
    const num = Number(value);
    if (!Number.isFinite(num)) return 'Rp 0';
    return currencyFormatter.format(num);
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
    generatedAt: $('#rk-generated'),
    chartMix: $('#rk-chart-mix'),
    chartMixSummary: $('#rk-chart-mix-summary'),
    chartCost: $('#rk-chart-cost'),
    chartCostSummary: $('#rk-chart-cost-summary'),
    analyticsPeriod: $('#rk-analytics-period'),
    viewToggleButtons: $$('#rk-view-toggle [data-view]'),
    costModeToggle: $('#rk-cost-mode-toggle'),
  };

  const showToast = (message, type = 'info') => {
    if (window.DP && window.DP.core && window.DP.core.toast) {
      window.DP.core.toast.show(message, type);
      return;
    }
    console.log(`[${type}] ${message}`);
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
    const html = rows.map((row) => {
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
    }).join('');
    refs.tbody.innerHTML = html;
  };

  const updateStats = (meta = {}) => {
    const counts = meta.counts_per_kategori || {};
    const qtyTotals = meta.quantity_totals || {};
    if (refs.countTK) refs.countTK.textContent = counts.TK || 0;
    if (refs.countBHN) refs.countBHN.textContent = counts.BHN || 0;
    if (refs.countALT) refs.countALT.textContent = counts.ALT || 0;
    if (refs.countLAIN) refs.countLAIN.textContent = counts.LAIN || 0;
    if (refs.qtyTK) refs.qtyTK.textContent = qtyTotals.TK || '0';
    if (refs.qtyBHN) refs.qtyBHN.textContent = qtyTotals.BHN || '0';
    if (refs.qtyALT) refs.qtyALT.textContent = qtyTotals.ALT || '0';
    if (refs.qtyLAIN) refs.qtyLAIN.textContent = qtyTotals.LAIN || '0';
    if (refs.nrows) refs.nrows.textContent = meta.n_rows || 0;
    if (refs.totalCost) refs.totalCost.textContent = meta.grand_total_cost || 'Rp 0';
    if (refs.generatedAt) refs.generatedAt.textContent = meta.generated_at || '';
  };

  const updateScopeIndicator = (meta = {}) => {
    if (!refs.scopeIndicator) return;
    const chips = [];
    if (currentFilter.mode === 'tahapan' && meta.tahapan) {
      chips.push(`<span class="badge bg-primary-subtle text-primary">Tahapan: ${esc(meta.tahapan.nama || '#')}</span>`);
    } else {
      chips.push('<span class="badge bg-secondary-subtle text-secondary">Mode: Keseluruhan</span>');
    }
    const periodLabel = describePeriodChip();
    if (periodLabel) {
      chips.push(`<span class="badge bg-info-subtle text-info">Waktu: ${esc(periodLabel)}</span>`);
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
    chartMixInstance.setOption({
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
        data,
        label: { formatter: '{b}\n{d}%' },
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
    chartCostInstance.setOption({
      grid: { left: '3%', right: '6%', bottom: '5%', containLabel: true },
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
        axisLabel: { formatter: (val) => formatCurrencyValue(val) },
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
      const qtyText = item.qty ? `<small>${formatQtyValue(item.qty)}</small>` : '';
      return `<li><span class="rk-chart-label">${esc(item.name)}</span><span class="rk-chart-value">${formatCurrencyValue(item.cost)}${qtyText ? `<span>${qtyText}</span>` : ''}</span></li>`;
    });

    renderSummaryList(refs.chartCostSummary, costSeries, (item) => (
      `<li><span class="rk-chart-label">${esc(item.label)}</span><span class="rk-chart-value">${formatCurrencyValue(item.value)}</span></li>`
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
    const limit = costChartMode === 'compact' ? 5 : null;
    const html = periods.map((period) => {
      const source = period.items || [];
      const items = limit ? source.slice(0, limit) : source;
      const itemList = items.map((item) => (
        `<li><span class="rk-chart-label">${esc(item.kode || '-')} - ${esc(item.uraian || '-')}</span>` +
        `<span class="rk-chart-value">${formatCurrencyValue(item.harga_total_decimal || item.harga_total)}</span></li>`
      )).join('');
      return `
        <div class="rk-timeline-period">
          <div class="rk-timeline-period__header">
            <div>
              <div class="rk-timeline-period__title">${esc(period.label || period.value || '-')}</div>
              <div class="rk-timeline-period__dates text-muted">${esc(period.start_date || '')} - ${esc(period.end_date || '')}</div>
            </div>
            <div class="rk-timeline-period__total">${formatCurrencyValue(period.total_cost_decimal || period.total_cost)}</div>
          </div>
          <ul class="rk-chart-summary">
            ${itemList || '<li class="text-muted">Tidak ada item</li>'}
          </ul>
        </div>`;
    }).join('');
    refs.timelineContent.innerHTML = html;
  };

  const refreshAnalyticsCostMode = () => {
    const costSeries = costChartMode === 'compact'
      ? analyticsState.costSeriesFull.slice(0, 5)
      : analyticsState.costSeriesFull;
    renderCostChart(costSeries);
    renderSummaryList(refs.chartCostSummary, costSeries, (item) => (
      `<li><span class="rk-chart-label">${esc(item.label)}</span><span class="rk-chart-value">${formatCurrencyValue(item.value)}</span></li>`
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
    if (!refs.klasifikasiMenu) return;
    if (!filterMeta.klasifikasi.length) {
      refs.klasifikasiMenu.innerHTML = '<div class="text-muted small px-2 py-1">Belum ada klasifikasi</div>';
      return;
    }
    const html = filterMeta.klasifikasi.map((row) => {
      const checked = currentFilter.klasifikasi_ids.includes(row.id);
      return `<label class="rk-dropdown-item">
        <input type="checkbox" class="form-check-input klasifikasi-check" value="${row.id}" ${checked ? 'checked' : ''}>
        <span>${esc(row.name)} <small class="text-muted">(${row.pekerjaan_count || 0})</small></span>
      </label>`;
    }).join('');
    refs.klasifikasiMenu.innerHTML = html;
  };

  const getSubOptions = () => {
    const subs = [];
    filterMeta.klasifikasi.forEach((row) => {
      (row.sub || []).forEach((sub) => subs.push({ ...sub, klasifikasi_id: row.id }));
    });
    return subs;
  };

  const renderSubOptions = () => {
    if (!refs.subMenu) return;
    const subs = getSubOptions();
    if (!subs.length) {
      refs.subMenu.innerHTML = '<div class="text-muted small px-2 py-1">Belum ada sub-klasifikasi</div>';
      return;
    }
    const html = subs.map((sub) => {
      const checked = currentFilter.sub_klasifikasi_ids.includes(sub.id);
      return `<label class="rk-dropdown-item">
        <input type="checkbox" class="form-check-input sub-check" value="${sub.id}" ${checked ? 'checked' : ''}>
        <span>${esc(sub.name)} <small class="text-muted">(${sub.pekerjaan_count || 0})</small></span>
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
    const options = getPeriodOptionsForMode(mode);
    const disableStart = mode === 'all';
    refs.periodStart.disabled = disableStart;
    refs.periodEnd.disabled = disableStart || !mode.endsWith('range');
    if (disableStart) {
      refs.periodStart.innerHTML = '<option value="">Pilih mode terlebih dahulu</option>';
      refs.periodEnd.innerHTML = '<option value="">Pilih mode terlebih dahulu</option>';
      return;
    }
    const optionHtml = options.map((item) => `<option value="${item.value}">${esc(item.label)}</option>`).join('');
    refs.periodStart.innerHTML = `<option value="">Pilih salah satu</option>${optionHtml}`;
    refs.periodStart.value = currentFilter.period_start || '';
    refs.periodEnd.innerHTML = `<option value="">Sama seperti mulai</option>${optionHtml}`;
    refs.periodEnd.value = currentFilter.period_end || '';
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
    refreshActiveView();
  };

  const resetFilter = () => {
    currentFilter = defaultFilter();
    if (refs.searchInput) refs.searchInput.value = '';
    if (refs.pekerjaanSearch) refs.pekerjaanSearch.value = '';
    syncFilterControls();
    updateFilterIndicator();
    updateScopeIndicator();
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
      const data = await apiCall(`${endpoint}${query}`);
      const rows = data.rows || [];
      renderRows(rows);
      updateStats(data.meta || {});
      updateScopeIndicator(data.meta || {});
      updateFilterIndicator();
      updateAnalyticsFromRows(rows);
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
      const query = buildQueryString();
      const data = await apiCall(`${timelineEndpoint}${query}`);
      const periods = data.periods || [];
      renderTimeline(periods);
      updateAnalyticsFromTimeline(periods);
    } catch (error) {
      console.error('[rk] gagal memuat timeline', error);
      showToast('Gagal memuat timeline: ' + error.message, 'danger');
      renderTimeline([]);
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
    refreshActiveView();
  };

  const initExportButtons = () => {
    const exporter = window.ExportManager ? new window.ExportManager(projectId, 'rekap-kebutuhan') : null;
    const triggerExport = async (format) => {
      const query = buildQueryParams();
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
    if (btnCsv) btnCsv.addEventListener('click', () => triggerExport('csv'));
    if (btnPdf) btnPdf.addEventListener('click', () => triggerExport('pdf'));
    if (btnWord) btnWord.addEventListener('click', () => triggerExport('word'));
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
  const attachEventListeners = () => {
    if (refs.applyBtn) {
      refs.applyBtn.addEventListener('click', applyFilter);
    }
    if (refs.resetBtn) {
      refs.resetBtn.addEventListener('click', resetFilter);
    }
    if (refs.searchInput) {
      refs.searchInput.addEventListener('input', debounce((event) => {
        currentFilter.search = (event.target.value || '').trim();
        refreshActiveView();
      }, 400));
    }
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

  const init = async () => {
    parseInitialParams();
    await loadFilterOptions();
    await loadTahapan();
    updateFilterIndicator();
    updateScopeIndicator();
    attachEventListeners();
    initExportButtons();
    refreshActiveView();
  };

  init();
})();

