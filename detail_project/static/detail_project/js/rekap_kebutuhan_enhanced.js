// static/detail_project/js/rekap_kebutuhan_enhanced.js
// Enhanced Rekap Kebutuhan dengan support filter tahapan

(function() {
  'use strict';

  // =========================================================================
  // CONFIGURATION & STATE
  // =========================================================================
  
  const app = document.getElementById('rk-app');
  if (!app) return;

  const projectId = parseInt(app.dataset.projectId);
  const endpoint = app.dataset.endpoint;
  const endpointExport = app.dataset.endpointExport;

  // State
  let tahapanList = [];
  let currentFilter = {
    mode: 'all',
    tahapan_id: null,
    kategori: ['TK', 'BHN', 'ALT', 'LAIN']
  };
  let currentData = {
    rows: [],
    meta: {}
  };

  // DOM Elements
  const $loading = document.getElementById('rk-loading');
  const $empty = document.getElementById('rk-empty');
  const $tbody = document.getElementById('rk-tbody');
  const $tahapanButtons = document.getElementById('tahapan-buttons');
  const $scopeIndicator = document.getElementById('rk-scope-indicator');
  const $filterIndicator = document.getElementById('rk-filter-indicator');

  // Summary counters
  const $countTK = document.getElementById('rk-count-TK');
  const $countBHN = document.getElementById('rk-count-BHN');
  const $countALT = document.getElementById('rk-count-ALT');
  const $countLAIN = document.getElementById('rk-count-LAIN');
  const $nrows = document.getElementById('rk-nrows');
  const $generated = document.getElementById('rk-generated');

  // Export buttons
  const $btnCsv = document.getElementById('btn-export-csv');
  const $btnPdf = document.getElementById('btn-export-pdf');
  const $btnWord = document.getElementById('btn-export-word');

  // =========================================================================
  // UTILITY FUNCTIONS
  // =========================================================================

  function showLoading(show = true) {
    $loading?.classList.toggle('d-none', !show);
    $empty?.classList.toggle('d-none', true);
  }

  function showEmpty(show = true) {
    $empty?.classList.toggle('d-none', !show);
    $loading?.classList.toggle('d-none', true);
  }

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

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // =========================================================================
  // DATA LOADING
  // =========================================================================

  async function loadTahapan() {
    try {
      const data = await apiCall(`/detail_project/api/project/${projectId}/tahapan/`);
      tahapanList = data.tahapan || [];
      renderTahapanButtons();
    } catch (error) {
      console.error('Failed to load tahapan:', error);
    }
  }

  async function loadRekapKebutuhan() {
    showLoading(true);
    
    try {
      // Build query params
      const params = new URLSearchParams();
      params.append('mode', currentFilter.mode);
      
      if (currentFilter.mode === 'tahapan' && currentFilter.tahapan_id) {
        params.append('tahapan_id', currentFilter.tahapan_id);
      }
      
      if (currentFilter.kategori.length < 4) {
        params.append('kategori', currentFilter.kategori.join(','));
      }

      const url = `${endpoint}?${params.toString()}`;
      const data = await apiCall(url);
      
      currentData = data;
      
      if (!data.rows || data.rows.length === 0) {
        showEmpty(true);
        $tbody.innerHTML = '';
      } else {
        showEmpty(false);
        renderTable(data.rows);
      }
      
      renderMeta(data.meta, data.rows);
      updateScopeIndicator();
      updateFilterIndicator();
      
    } catch (error) {
      console.error('Failed to load rekap kebutuhan:', error);
      showToast('Gagal memuat data: ' + error.message, 'error');
      $tbody.innerHTML = `
        <tr>
          <td colspan="5" class="text-center text-danger">
            Gagal memuat data. Silakan refresh halaman.
          </td>
        </tr>
      `;
    } finally {
      showLoading(false);
    }
  }

  // =========================================================================
  // RENDER FUNCTIONS
  // =========================================================================

  function renderTahapanButtons() {
    if (tahapanList.length === 0) {
      $tahapanButtons.innerHTML = `
        <span class="text-muted small">
          <i class="bi bi-info-circle"></i>
          Belum ada tahapan. <a href="/detail_project/${projectId}/kelola-tahapan/">Buat tahapan</a>
        </span>
      `;
      return;
    }

    const html = tahapanList.map(tahap => `
      <button type="button" 
              class="tahapan-btn" 
              data-scope="tahapan" 
              data-tahapan-id="${tahap.tahapan_id}">
        <i class="bi bi-bookmark"></i>
        ${escapeHtml(tahap.nama)}
        <small class="text-muted">(${tahap.jumlah_pekerjaan})</small>
      </button>
    `).join('');

    $tahapanButtons.innerHTML = html;
    attachTahapanButtonListeners();
  }

  function attachTahapanButtonListeners() {
    document.querySelectorAll('.tahapan-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        // Remove active from all
        document.querySelectorAll('.tahapan-btn').forEach(b => {
          b.classList.remove('active');
        });

        // Add active to clicked
        e.currentTarget.classList.add('active');

        // Update filter
        const scope = e.currentTarget.dataset.scope;
        const tahapanId = e.currentTarget.dataset.tahapanId;

        if (scope === 'all') {
          currentFilter.mode = 'all';
          currentFilter.tahapan_id = null;
        } else {
          currentFilter.mode = 'tahapan';
          currentFilter.tahapan_id = parseInt(tahapanId);
        }
      });
    });
  }

  function renderTable(rows) {
    if (!$tbody) return;

    // Sort rows (already sorted from backend, but ensure consistency)
    const sorted = [...rows].sort((a, b) => {
      const katOrder = { 'TK': 1, 'BHN': 2, 'ALT': 3, 'LAIN': 4 };
      const katCompare = (katOrder[a.kategori] || 99) - (katOrder[b.kategori] || 99);
      if (katCompare !== 0) return katCompare;
      return (a.kode || '').localeCompare(b.kode || '');
    });

    const fragment = document.createDocumentFragment();
    
    sorted.forEach(row => {
      const tr = document.createElement('tr');
      
      // Kategori badge
      let katClass = 'bg-secondary';
      if (row.kategori === 'TK') katClass = 'bg-primary';
      else if (row.kategori === 'BHN') katClass = 'bg-success';
      else if (row.kategori === 'ALT') katClass = 'bg-warning';
      else if (row.kategori === 'LAIN') katClass = 'bg-info';

      tr.innerHTML = `
        <td>
          <span class="badge ${katClass}">${escapeHtml(row.kategori)}</span>
        </td>
        <td class="mono">${escapeHtml(row.kode)}</td>
        <td>${escapeHtml(row.uraian)}</td>
        <td>${escapeHtml(row.satuan)}</td>
        <td class="text-end mono">${escapeHtml(row.quantity || '0')}</td>
      `;
      
      fragment.appendChild(tr);
    });

    $tbody.innerHTML = '';
    $tbody.appendChild(fragment);
  }

  function renderMeta(meta, rows) {
    // Count per kategori
    const counts = { TK: 0, BHN: 0, ALT: 0, LAIN: 0 };
    
    if (meta && meta.counts_per_kategori) {
      Object.assign(counts, meta.counts_per_kategori);
    } else if (rows) {
      rows.forEach(r => {
        if (r.kategori && counts.hasOwnProperty(r.kategori)) {
          counts[r.kategori]++;
        }
      });
    }

    // Update counters
    if ($countTK) $countTK.textContent = counts.TK;
    if ($countBHN) $countBHN.textContent = counts.BHN;
    if ($countALT) $countALT.textContent = counts.ALT;
    if ($countLAIN) $countLAIN.textContent = counts.LAIN;
    
    if ($nrows) $nrows.textContent = rows ? rows.length : 0;
    
    if ($generated && meta && meta.generated_at) {
      $generated.textContent = `· ${meta.generated_at}`;
    }
  }

  function updateScopeIndicator() {
    if (!$scopeIndicator) return;

    if (currentFilter.mode === 'all') {
      $scopeIndicator.innerHTML = `
        <span class="badge bg-primary">
          <i class="bi bi-globe"></i> Keseluruhan Project
        </span>
      `;
    } else if (currentFilter.mode === 'tahapan' && currentFilter.tahapan_id) {
      const tahap = tahapanList.find(t => t.tahapan_id === currentFilter.tahapan_id);
      if (tahap) {
        $scopeIndicator.innerHTML = `
          <span class="badge bg-info">
            <i class="bi bi-bookmark-fill"></i> ${escapeHtml(tahap.nama)}
          </span>
        `;
      }
    }
  }

  function updateFilterIndicator() {
    if (!$filterIndicator) return;

    const filters = [];
    
    // Check kategori filter
    if (currentFilter.kategori.length < 4) {
      filters.push(`Kategori: ${currentFilter.kategori.join(', ')}`);
    }

    if (filters.length > 0) {
      $filterIndicator.innerHTML = `
        <span class="filter-active-indicator">
          <i class="bi bi-funnel-fill"></i>
          Filter aktif: ${filters.join(' · ')}
        </span>
      `;
    } else {
      $filterIndicator.innerHTML = '';
    }
  }

  // =========================================================================
  // FILTER OPERATIONS
  // =========================================================================

  function applyFilter() {
    // Get selected kategori
    const selectedKategori = [];
    document.querySelectorAll('.kategori-check:checked').forEach(cb => {
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

    // Reset UI
    document.querySelectorAll('.tahapan-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.scope === 'all');
    });

    document.querySelectorAll('.kategori-check').forEach(cb => {
      cb.checked = true;
    });

    // Reload
    loadRekapKebutuhan();
  }

  // =========================================================================
  // EXPORT FUNCTIONS
  // =========================================================================

  function setupExport() {
    if (!window.ExportManager || !projectId) return;

    const exportManager = new window.ExportManager(projectId, 'rekap-kebutuhan');

    // Build query params for export
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

    // Override export methods to include current filter
    if ($btnCsv) {
      $btnCsv.addEventListener('click', () => {
        const params = getExportParams();
        const url = params 
          ? `/detail_project/api/project/${projectId}/export/rekap-kebutuhan/csv/?${params}`
          : `/detail_project/api/project/${projectId}/export/rekap-kebutuhan/csv/`;
        window.open(url, '_blank');
      });
    }

    if ($btnPdf) {
      $btnPdf.addEventListener('click', () => {
        const params = getExportParams();
        const url = params 
          ? `/detail_project/api/project/${projectId}/export/rekap-kebutuhan/pdf/?${params}`
          : `/detail_project/api/project/${projectId}/export/rekap-kebutuhan/pdf/`;
        window.open(url, '_blank');
      });
    }

    if ($btnWord) {
      $btnWord.addEventListener('click', () => {
        const params = getExportParams();
        const url = params 
          ? `/detail_project/api/project/${projectId}/export/rekap-kebutuhan/word/?${params}`
          : `/detail_project/api/project/${projectId}/export/rekap-kebutuhan/word/`;
        window.open(url, '_blank');
      });
    }
  }

  // =========================================================================
  // EVENT LISTENERS
  // =========================================================================

  document.getElementById('btn-apply-filter')?.addEventListener('click', applyFilter);
  document.getElementById('btn-reset-filter')?.addEventListener('click', resetFilter);

  // Kategori checkboxes - auto apply on change (optional, bisa diubah jadi manual)
  document.querySelectorAll('.kategori-check').forEach(cb => {
    cb.addEventListener('change', () => {
      // Optional: auto-apply filter
      // applyFilter();
    });
  });

  // =========================================================================
  // URL PARAMS HANDLING (untuk deep linking)
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
        const btn = document.querySelector(`.tahapan-btn[data-tahapan-id="${tahapanParam}"]`);
        if (btn) {
          document.querySelectorAll('.tahapan-btn').forEach(b => b.classList.remove('active'));
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
      document.querySelectorAll('.kategori-check').forEach(cb => {
        cb.checked = selected.includes(cb.value);
      });
    }
  }

  // =========================================================================
  // INITIALIZATION
  // =========================================================================

  async function init() {
    parseUrlParams();
    await loadTahapan();
    await loadRekapKebutuhan();
    setupExport();
  }

  init();

})();
