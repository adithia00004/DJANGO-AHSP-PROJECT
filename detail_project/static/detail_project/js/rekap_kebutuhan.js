// static/detail_project/js/rekap_kebutuhan.js
// Enhanced Rekap Kebutuhan dengan support Tahapan Filter

(function () {
  'use strict';

  // =========================================================================
  // DOM UTILITIES
  // =========================================================================
  
  const $ = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
  
  const app = $('#rk-app');
  if (!app) return;

  // =========================================================================
  // CONFIGURATION & STATE
  // =========================================================================
  
  const projectId = app.getAttribute('data-project-id');
  const endpoint = app.dataset.endpoint;
  const endpointExport = app.dataset.endpointExport;
  
  if (!endpoint) {
    console.error('[rk] data-endpoint kosong pada #rk-app');
    return;
  }

  // State management
  let tahapanList = [];
  let currentFilter = {
    mode: 'all',
    tahapan_id: null,
    kategori: ['TK', 'BHN', 'ALT', 'LAIN']
  };

  // =========================================================================
  // DOM ELEMENTS
  // =========================================================================
  
  const tbody = $('#rk-tbody') || $('#rk-table tbody');
  const emptyEl = $('#rk-empty');
  const loadingEl = $('#rk-loading');
  
  const countTK = $('#rk-count-TK');
  const countBHN = $('#rk-count-BHN');
  const countALT = $('#rk-count-ALT');
  const countLAIN = $('#rk-count-LAIN');
  const nrowsEl = $('#rk-nrows');
  const genEl = $('#rk-generated');
  
  const btnCsv = $('#btn-export-csv');
  const btnPdf = $('#btn-export-pdf');
  const btnWord = $('#btn-export-word');
  
  const scopeIndicator = $('#rk-scope-indicator');
  const filterIndicator = $('#rk-filter-indicator');
  const tahapanButtonsContainer = $('#rk-tahapan-buttons');

  // =========================================================================
  // UTILITY FUNCTIONS
  // =========================================================================
  
  function setLoading(v) {
    if (loadingEl) loadingEl.classList.toggle('d-none', !v);
  }

  function setEmpty(v) {
    if (emptyEl) emptyEl.classList.toggle('d-none', !v);
  }

  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));

  function showToast(message, type = 'info') {
    if (window.DP && window.DP.core && window.DP.core.toast) {
      window.DP.core.toast.show(message, type);
    } else {
      console.log(`[${type}] ${message}`);
    }
  }

  async function apiCall(url, options = {}) {
    const response = await fetch(url, {
      credentials: 'same-origin',
      ...options
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
  }

  // =========================================================================
  // TAHAPAN LOADING
  // =========================================================================
  
  async function loadTahapan() {
    try {
      const data = await apiCall(`/detail_project/api/project/${projectId}/tahapan/`);
      tahapanList = data.tahapan || [];
      renderTahapanButtons();
    } catch (error) {
      console.error('[rk] Failed to load tahapan:', error);
      // Silently fail - filter will still work without tahapan
    }
  }

  function renderTahapanButtons() {
    if (!tahapanButtonsContainer) return;
    
    if (tahapanList.length === 0) {
      tahapanButtonsContainer.innerHTML = `
        <span class="text-muted small">
          <i class="bi bi-info-circle"></i>
          Belum ada tahapan.
          <a href="/detail_project/${projectId}/jadwal-pekerjaan/">Buat tahapan</a>
        </span>
      `;
      return;
    }

    const html = tahapanList.map(tahap => `
      <button type="button" 
              class="rk-tahapan-btn" 
              data-scope="tahapan" 
              data-tahapan-id="${tahap.tahapan_id}">
        <i class="bi bi-bookmark"></i>
        ${esc(tahap.nama)}
        <small class="opacity-75">(${tahap.jumlah_pekerjaan})</small>
      </button>
    `).join('');

    tahapanButtonsContainer.innerHTML = html;
    attachTahapanButtonListeners();
  }

  function attachTahapanButtonListeners() {
    $$('.rk-tahapan-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        // Remove active from all
        $$('.rk-tahapan-btn').forEach(b => b.classList.remove('active'));
        
        // Add active to clicked
        e.currentTarget.classList.add('active');
        
        // Update filter state
        const scope = e.currentTarget.dataset.scope;
        const tahapanId = e.currentTarget.dataset.tahapanId;

        if (scope === 'all') {
          currentFilter.mode = 'all';
          currentFilter.tahapan_id = null;
        } else {
          currentFilter.mode = 'tahapan';
          currentFilter.tahapan_id = parseInt(tahapanId);
        }
        
        // Don't auto-apply, let user click "Terapkan Filter"
        // But you can uncomment below for auto-apply:
        // loadRekapKebutuhan();
      });
    });
  }

  // =========================================================================
  // DATA LOADING
  // =========================================================================
  
  async function loadRekapKebutuhan() {
    setLoading(true);
    
    try {
      // Build query params
      const params = new URLSearchParams();
      params.append('mode', currentFilter.mode);
      
      if (currentFilter.mode === 'tahapan' && currentFilter.tahapan_id) {
        params.append('tahapan_id', currentFilter.tahapan_id);
      }
      
      // Only add kategori if not all selected
      if (currentFilter.kategori.length < 4) {
        params.append('kategori', currentFilter.kategori.join(','));
      }

      const url = `${endpoint}?${params.toString()}`;
      const data = await apiCall(url);
      
      const rows = data.rows || [];
      
      if (rows.length === 0) {
        tbody.innerHTML = '';
        setEmpty(true);
      } else {
        setEmpty(false);
        renderRows(rows);
      }
      
      renderMeta(data.meta, rows);
      updateScopeIndicator();
      updateFilterIndicator();
      
    } catch (error) {
      console.error('[rk] gagal ambil data:', error);
      showToast('Gagal memuat data: ' + error.message, 'error');
      if (tbody) {
        tbody.innerHTML = `
          <tr>
            <td colspan="5" class="text-danger text-center">
              Gagal memuat data. Silakan refresh halaman.
            </td>
          </tr>
        `;
      }
      setEmpty(false);
    } finally {
      setLoading(false);
    }
  }

  // =========================================================================
  // RENDERING FUNCTIONS
  // =========================================================================
  
  function renderRows(rows) {
    if (!tbody) return;
    
    // Sort by kategori, then kode
    rows.sort((a, b) =>
      (a.kategori || '').localeCompare(b.kategori || '') ||
      (a.kode || '').localeCompare(b.kode || '')
    );

    const frag = document.createDocumentFragment();
    
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="text-nowrap">${esc(r.kategori)}</td>
        <td class="text-nowrap mono">${esc(r.kode)}</td>
        <td>${esc((r.uraian || '').replace(/\r?\n/g, ' '))}</td>
        <td class="text-nowrap">${esc(r.satuan)}</td>
        <td class="text-end mono">${esc(r.quantity ?? '')}</td>
      `;
      frag.appendChild(tr);
    });
    
    tbody.innerHTML = '';
    tbody.appendChild(frag);
  }

  function renderMeta(meta, rows) {
    const counts = { TK: 0, BHN: 0, ALT: 0, LAIN: 0 };
    let nrows = 0;
    let generated = '';

    if (meta && meta.counts_per_kategori) {
      const m = meta.counts_per_kategori;
      counts.TK = m.TK || 0;
      counts.BHN = m.BHN || 0;
      counts.ALT = m.ALT || 0;
      counts.LAIN = m.LAIN || 0;
      nrows = meta.n_rows ?? (rows ? rows.length : 0);
      generated = meta.generated_at || '';
    } else if (Array.isArray(rows)) {
      rows.forEach(r => {
        if (r.kategori && counts.hasOwnProperty(r.kategori)) {
          counts[r.kategori]++;
        }
      });
      nrows = rows.length;
    }

    if (countTK) countTK.textContent = counts.TK;
    if (countBHN) countBHN.textContent = counts.BHN;
    if (countALT) countALT.textContent = counts.ALT;
    if (countLAIN) countLAIN.textContent = counts.LAIN;
    if (nrowsEl) nrowsEl.textContent = nrows;
    if (genEl) genEl.textContent = generated ? `· ${generated}` : '';
  }

  function updateScopeIndicator() {
    if (!scopeIndicator) return;

    if (currentFilter.mode === 'all') {
      scopeIndicator.innerHTML = `
        <span class="badge bg-primary">
          <i class="bi bi-globe"></i> Keseluruhan Project
        </span>
      `;
    } else if (currentFilter.mode === 'tahapan' && currentFilter.tahapan_id) {
      const tahap = tahapanList.find(t => t.tahapan_id === currentFilter.tahapan_id);
      if (tahap) {
        scopeIndicator.innerHTML = `
          <span class="badge bg-info">
            <i class="bi bi-bookmark-fill"></i> ${esc(tahap.nama)}
          </span>
        `;
      }
    }
  }

  function updateFilterIndicator() {
    if (!filterIndicator) return;

    const filters = [];
    
    // Check kategori filter
    if (currentFilter.kategori.length < 4) {
      filters.push(`Kategori: ${currentFilter.kategori.join(', ')}`);
    }

    if (filters.length > 0) {
      filterIndicator.innerHTML = `
        <span class="rk-filter-active-indicator">
          <i class="bi bi-funnel-fill"></i>
          ${filters.join(' · ')}
        </span>
      `;
    } else {
      filterIndicator.innerHTML = '';
    }
  }

  // =========================================================================
  // FILTER OPERATIONS
  // =========================================================================
  
  function applyFilter() {
    // Get selected kategori
    const selectedKategori = [];
    $$('.kategori-check:checked').forEach(cb => {
      selectedKategori.push(cb.value);
    });

    currentFilter.kategori = selectedKategori;

    // Reload data
    loadRekapKebutuhan();
  }

  function resetFilter() {
    // Reset to all
    currentFilter = {
      mode: 'all',
      tahapan_id: null,
      kategori: ['TK', 'BHN', 'ALT', 'LAIN']
    };

    // Reset UI - tahapan buttons
    $$('.rk-tahapan-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.scope === 'all');
    });

    // Reset UI - kategori checkboxes
    $$('.kategori-check').forEach(cb => {
      cb.checked = true;
    });

    // Reload
    loadRekapKebutuhan();
  }

  // =========================================================================
  // EXPORT FUNCTIONS
  // =========================================================================
  
  function setupExport() {
    // Build query params for export URL
    function getExportParams() {
      const params = new URLSearchParams();
      
      if (currentFilter.mode === 'tahapan' && currentFilter.tahapan_id) {
        params.append('tahapan_id', currentFilter.tahapan_id);
      }
      
      if (currentFilter.kategori.length < 4) {
        params.append('kategori', currentFilter.kategori.join(','));
      }
      
      return params.toString();
    }

    // CSV Export
    if (btnCsv) {
      btnCsv.addEventListener('click', () => {
        const params = getExportParams();
        const url = params 
          ? `/detail_project/api/project/${projectId}/export/rekap-kebutuhan/csv/?${params}`
          : `/detail_project/api/project/${projectId}/export/rekap-kebutuhan/csv/`;
        window.open(url, '_blank');
      });
    }

    // PDF Export
    if (btnPdf) {
      btnPdf.addEventListener('click', () => {
        const params = getExportParams();
        const url = params 
          ? `/detail_project/api/project/${projectId}/export/rekap-kebutuhan/pdf/?${params}`
          : `/detail_project/api/project/${projectId}/export/rekap-kebutuhan/pdf/`;
        window.open(url, '_blank');
      });
    }

    // Word Export
    if (btnWord) {
      btnWord.addEventListener('click', () => {
        const params = getExportParams();
        const url = params 
          ? `/detail_project/api/project/${projectId}/export/rekap-kebutuhan/word/?${params}`
          : `/detail_project/api/project/${projectId}/export/rekap-kebutuhan/word/`;
        window.open(url, '_blank');
      });
    }

    // ExportManager integration (if available)
    try {
      if (window.ExportManager && projectId) {
        const exp = new window.ExportManager(projectId, 'rekap-kebutuhan');
        // ExportManager will handle export with current params if implemented
      }
    } catch (e) {
      console.debug('[rk] ExportManager not available or not needed');
    }
  }

  // =========================================================================
  // URL PARAMS HANDLING (for deep linking)
  // =========================================================================
  
  function parseUrlParams() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // Check for tahapan param
    const tahapanParam = urlParams.get('tahapan');
    if (tahapanParam) {
      currentFilter.mode = 'tahapan';
      currentFilter.tahapan_id = parseInt(tahapanParam);
      
      // Activate button after tahapan loaded
      setTimeout(() => {
        const btn = $(`.rk-tahapan-btn[data-tahapan-id="${tahapanParam}"]`);
        if (btn) {
          $$('.rk-tahapan-btn').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
        }
      }, 500);
    }

    // Check for kategori param
    const kategoriParam = urlParams.get('kategori');
    if (kategoriParam) {
      const selected = kategoriParam.split(',').map(k => k.trim().toUpperCase());
      currentFilter.kategori = selected;
      
      // Update checkboxes
      $$('.kategori-check').forEach(cb => {
        cb.checked = selected.includes(cb.value);
      });
    }
  }

  // =========================================================================
  // EVENT LISTENERS
  // =========================================================================
  
  const btnApplyFilter = $('#rk-btn-apply-filter');
  const btnResetFilter = $('#rk-btn-reset-filter');

  if (btnApplyFilter) {
    btnApplyFilter.addEventListener('click', applyFilter);
  }

  if (btnResetFilter) {
    btnResetFilter.addEventListener('click', resetFilter);
  }

  // Optional: Auto-apply on kategori checkbox change
  // Uncomment if you want instant filtering:
  /*
  $$('.kategori-check').forEach(cb => {
    cb.addEventListener('change', applyFilter);
  });
  */

  // =========================================================================
  // INITIALIZATION
  // =========================================================================
  
  async function init() {
    parseUrlParams();
    await loadTahapan();
    await loadRekapKebutuhan();
    setupExport();
  }

  // Start the app
  init();

})();
