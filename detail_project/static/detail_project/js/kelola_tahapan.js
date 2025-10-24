// static/detail_project/js/kelola_tahapan.js
// Kelola Tahapan Pelaksanaan - New Simplified Workflow

(function() {
  'use strict';

  // =========================================================================
  // CONFIGURATION & STATE
  // =========================================================================

  const app = document.getElementById('tahapan-app');
  if (!app) return;

  const projectId = parseInt(app.dataset.projectId);
  const apiBase = app.dataset.apiBase;

  // State Management
  let tahapanList = [];        // List of all tahapan
  let allPekerjaan = [];       // List of all pekerjaan (flat)
  let pekerjaanMap = new Map(); // pekerjaan_id -> pekerjaan object with assignments
  let volumeMap = new Map();    // pekerjaan_id -> volume quantity
  let changes = new Map();      // pekerjaan_id -> {tahapan_ids: [...], proportions: {...}}

  // DOM Elements
  const $loading = document.getElementById('loading');
  const $emptyState = document.getElementById('empty-state');
  const $mainContainer = document.getElementById('main-table-container');
  const $tbody = document.getElementById('pekerjaan-tbody');
  const $loadingOverlay = document.getElementById('loading-overlay');
  const $statusInfo = document.getElementById('status-info');
  const $statusMessage = document.getElementById('status-message');

  // Sidebar Elements
  const sidebar = document.getElementById('kt-sidebar');
  const $formTahapan = document.getElementById('form-tahapan');
  const $tahapanListSidebar = document.getElementById('tahapan-list-sidebar');
  const $tahapanCount = document.getElementById('tahapan-count');

  // Filter Elements
  const $searchInput = document.getElementById('search-pekerjaan');
  const $filterKlasifikasi = document.getElementById('filter-klasifikasi');
  const $filterStatus = document.getElementById('filter-status');

  // =========================================================================
  // UTILITY FUNCTIONS
  // =========================================================================

  function showLoading(show = true) {
    if ($loading) $loading.classList.toggle('d-none', !show);
  }

  function showEmpty(show = true) {
    if ($emptyState) $emptyState.classList.toggle('d-none', !show);
    if ($mainContainer) $mainContainer.classList.toggle('d-none', show);
  }

  function showLoadingOverlay(show = true) {
    if ($loadingOverlay) $loadingOverlay.classList.toggle('d-none', !show);
  }

  function showStatus(message, type = 'info') {
    if (!$statusInfo || !$statusMessage) return;
    $statusMessage.textContent = message;
    $statusInfo.classList.remove('d-none', 'alert-info', 'alert-success', 'alert-warning', 'alert-danger');
    $statusInfo.classList.add('alert-' + type);
    setTimeout(() => $statusInfo.classList.add('d-none'), 5000);
  }

  function showToast(message, type = 'success') {
    const toastEl = document.getElementById('kt-toast');
    const toastBody = document.getElementById('kt-toast-body');
    if (!toastEl || !toastBody) return;

    // Set color based on type
    toastEl.classList.remove('text-bg-success', 'text-bg-danger', 'text-bg-warning', 'text-bg-info');
    if (type === 'error') toastEl.classList.add('text-bg-danger');
    else if (type === 'warning') toastEl.classList.add('text-bg-warning');
    else if (type === 'info') toastEl.classList.add('text-bg-info');
    else toastEl.classList.add('text-bg-success');

    toastBody.textContent = message;

    const toast = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 3000 });
    toast.show();
  }

  async function apiCall(url, options = {}) {
    const response = await fetch(url, {
      credentials: 'same-origin',
      ...options
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  // =========================================================================
  // DATA LOADING
  // =========================================================================

  async function loadAllData() {
    showLoading(true);
    try {
      await loadTahapan();

      if (tahapanList.length === 0) {
        await autoInitializeTahap1();
      }

      await loadPekerjaan();
      await loadVolumes();
      await loadAllAssignments();
      await autoAssignUnassignedToTahap1();

      renderTable();
      showEmpty(false);

    } catch (error) {
      console.error('Load data failed:', error);
      showToast('Gagal memuat data: ' + error.message, 'error');
    } finally {
      showLoading(false);
    }
  }

  async function loadTahapan() {
    try {
      const data = await apiCall(apiBase);
      tahapanList = (data.tahapan || []).sort((a, b) => a.urutan - b.urutan);

      // Update sidebar
      renderTahapanSidebar();

      return tahapanList;
    } catch (error) {
      console.error('Failed to load tahapan:', error);
      throw error;
    }
  }

  async function loadPekerjaan() {
    try {
      const response = await apiCall(`/detail_project/api/project/${projectId}/list-pekerjaan/tree/`);
      allPekerjaan = [];

      // Flatten tree structure - handle API response format
      function flattenNode(node, parentKlasifikasi = '', parentSubKlasifikasi = '') {
        if (!node) return;

        if (Array.isArray(node)) {
          node.forEach(n => flattenNode(n, parentKlasifikasi, parentSubKlasifikasi));
          return;
        }

        // Handle response format: {ok: true, klasifikasi: [...]}
        if (node.klasifikasi && Array.isArray(node.klasifikasi)) {
          node.klasifikasi.forEach(klas => flattenNode(klas, '', ''));
          return;
        }

        // Handle klasifikasi node: has "sub" array property
        if (node.sub && Array.isArray(node.sub)) {
          const klasNama = node.name || node.nama || '';
          node.sub.forEach(sub => flattenNode(sub, klasNama, ''));
          return;
        }

        // Handle sub-klasifikasi node: has "pekerjaan" array property
        if (node.pekerjaan && Array.isArray(node.pekerjaan)) {
          const subKlasNama = node.name || node.nama || '';

          node.pekerjaan.forEach(pkj => {
            const pekerjaanId = pkj.id || pkj.pekerjaan_id;
            if (pekerjaanId) {
              const pkjData = {
                id: pekerjaanId,
                kode: pkj.snapshot_kode || pkj.kode || '',
                uraian: pkj.snapshot_uraian || pkj.uraian || '',
                satuan: pkj.snapshot_satuan || pkj.satuan || '-',
                klasifikasi: pkj.klasifikasi_nama || parentKlasifikasi || '',
                sub_klasifikasi: pkj.sub_klasifikasi_nama || parentSubKlasifikasi || subKlasNama || '',
                ordering_index: pkj.ordering_index || 0
              };

              allPekerjaan.push(pkjData);

              // Initialize in pekerjaanMap
              pekerjaanMap.set(pekerjaanId, {
                ...pkjData,
                assignments: []
              });
            }
          });
          return;
        }

        // Fallback: check children array (tree format)
        if (node.children && Array.isArray(node.children)) {
          node.children.forEach(child => flattenNode(child, parentKlasifikasi, parentSubKlasifikasi));
        }
      }

      flattenNode(response);

      // Populate filter klasifikasi dropdown
      const klasifikasiSet = new Set(allPekerjaan.map(p => p.klasifikasi).filter(Boolean));
      if ($filterKlasifikasi) {
        $filterKlasifikasi.innerHTML = '<option value="">Semua Klasifikasi</option>' +
          Array.from(klasifikasiSet).map(k => `<option value="${escapeHtml(k)}">${escapeHtml(k)}</option>`).join('');
      }

      return allPekerjaan;
    } catch (error) {
      console.error('Failed to load pekerjaan:', error);
      throw error;
    }
  }

  async function loadVolumes() {
    try {
      const data = await apiCall(`/detail_project/api/project/${projectId}/volume-pekerjaan/list/`);
      volumeMap.clear();

      const volumes = data.items || data.volumes || data.data || [];

      if (Array.isArray(volumes)) {
        volumes.forEach(v => {
          const pkjId = v.pekerjaan_id || v.id;
          const qty = parseFloat(v.quantity || v.volume || v.qty) || 0;

          if (pkjId) {
            volumeMap.set(pkjId, qty);
          }
        });
      }

      return volumeMap;
    } catch (error) {
      console.error('Failed to load volumes:', error);
      return volumeMap;
    }
  }

  async function loadAllAssignments() {
    // Load assignments for all pekerjaan
    const promises = Array.from(pekerjaanMap.keys()).map(async (pkjId) => {
      try {
        const data = await apiCall(`/detail_project/api/project/${projectId}/pekerjaan/${pkjId}/assignments/`);
        const pkj = pekerjaanMap.get(pkjId);
        if (pkj) {
          pkj.assignments = data.assignments || [];
          pkj.total_assigned = parseFloat(data.total_assigned) || 0;
        }
      } catch (error) {
        // If endpoint doesn't exist or fails, continue
        console.warn(`Failed to load assignments for pekerjaan ${pkjId}:`, error);
      }
    });

    await Promise.all(promises);
  }

  // =========================================================================
  // AUTO-INITIALIZATION (DEFAULT TAHAP 1)
  // =========================================================================

  async function autoInitializeTahap1() {
    try {
      await apiCall(apiBase, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
          nama: 'Tahap 1',
          urutan: 1,
          deskripsi: 'Tahap pelaksanaan default',
          tanggal_mulai: null,
          tanggal_selesai: null
        })
      });

      // Reload tahapan list with retry
      let retries = 3;
      while (retries > 0) {
        await loadTahapan();
        if (tahapanList.length > 0) {
          showStatus('Tahap 1 telah dibuat secara otomatis', 'success');
          return;
        }
        retries--;
        if (retries > 0) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }
    } catch (error) {
      console.error('Failed to auto-initialize Tahap 1:', error);
    }
  }

  async function autoAssignUnassignedToTahap1() {
    // Find Tahap 1 (try multiple methods)
    let tahap1 = tahapanList.find(t => t.nama && t.nama.toLowerCase().includes('tahap 1'));

    if (!tahap1) {
      tahap1 = tahapanList.find(t => t.urutan === 1);
    }

    if (!tahap1) {
      tahap1 = tahapanList[0];
    }

    if (!tahap1) return;

    // Find all unassigned or partially assigned pekerjaan
    const unassignedPekerjaan = [];

    pekerjaanMap.forEach((pkjData, pkjId) => {
      const totalAssigned = pkjData.total_assigned || 0;

      if (totalAssigned < 99.99) {
        const remainingProportion = 100 - totalAssigned;
        const existingTahap1 = pkjData.assignments.find(a => a.tahapan_id === tahap1.tahapan_id);

        if (!existingTahap1 && remainingProportion > 0) {
          unassignedPekerjaan.push({
            pekerjaan_id: pkjId,
            proporsi: remainingProportion
          });

          pkjData.assignments.push({
            tahapan_id: tahap1.tahapan_id,
            proporsi: remainingProportion
          });
          pkjData.total_assigned = 100;
        }
      }
    });

    // If there are unassigned pekerjaan, assign them to Tahap 1
    if (unassignedPekerjaan.length > 0) {
      try {
        const chunkSize = 50;
        for (let i = 0; i < unassignedPekerjaan.length; i += chunkSize) {
          const chunk = unassignedPekerjaan.slice(i, i + chunkSize);

          await apiCall(`${apiBase}${tahap1.tahapan_id}/assign/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ assignments: chunk })
          });
        }

        showStatus(`${unassignedPekerjaan.length} pekerjaan telah di-assign ke Tahap 1 secara otomatis`, 'success');
      } catch (error) {
        console.error('Failed to auto-assign to Tahap 1:', error);
        showToast('Gagal auto-assign ke Tahap 1: ' + error.message, 'warning');
      }
    }
  }

  // =========================================================================
  // TABLE RENDERING (Hierarchical Structure)
  // =========================================================================

  // Group pekerjaan by klasifikasi and sub-klasifikasi
  function groupPekerjaanHierarchical() {
    const grouped = {};

    allPekerjaan.forEach(pkj => {
      const klasNama = pkj.klasifikasi || '(Tanpa Klasifikasi)';
      const subNama = pkj.sub_klasifikasi || '(Tanpa Sub-Klasifikasi)';

      if (!grouped[klasNama]) {
        grouped[klasNama] = {};
      }

      if (!grouped[klasNama][subNama]) {
        grouped[klasNama][subNama] = [];
      }

      grouped[klasNama][subNama].push(pkj);
    });

    return grouped;
  }

  function renderTable() {
    if (!$tbody) return;

    if (allPekerjaan.length === 0) {
      $tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted py-4">Tidak ada pekerjaan</td></tr>';
      return;
    }

    const grouped = groupPekerjaanHierarchical();

    const html = Object.entries(grouped).map(([klasNama, subGroups]) => {
      return createKlasifikasiCard(klasNama, subGroups);
    }).join('');

    $tbody.innerHTML = html;

    attachTableEventListeners();
    attachCollapseToggles();

    const showingCount = document.getElementById('showing-count');
    const totalCount = document.getElementById('total-count');
    if (showingCount) showingCount.textContent = allPekerjaan.length;
    if (totalCount) totalCount.textContent = allPekerjaan.length;
  }

  function createKlasifikasiCard(klasNama, subGroups) {
    const klasId = klasNama.replace(/[^a-zA-Z0-9]/g, '_');
    const subCardsHtml = Object.entries(subGroups).map(([subNama, pekerjaanList]) => {
      return createSubKlasifikasiCard(klasId, subNama, pekerjaanList);
    }).join('');

    return `
      <tr>
        <td colspan="10" class="p-0">
          <div class="card dp-card-primary kt-klas-card mb-3" data-klas-id="${klasId}">
            <div class="card-header d-flex align-items-center justify-content-between">
              <span class="dp-card-title-primary fw-bold">${escapeHtml(klasNama)}</span>
              <button type="button"
                      class="btn btn-sm btn-outline-secondary dp-btn-sm kt-card-toggle"
                      data-type="klas"
                      data-key="${klasId}"
                      aria-expanded="true"
                      title="Collapse/Expand">
                <i class="bi bi-caret-down-fill"></i>
              </button>
            </div>
            <div class="card-body kt-klas-body" data-klas-id="${klasId}">
              ${subCardsHtml}
            </div>
          </div>
        </td>
      </tr>
    `;
  }

  function createSubKlasifikasiCard(klasId, subNama, pekerjaanList) {
    const subId = `${klasId}_${subNama.replace(/[^a-zA-Z0-9]/g, '_')}`;
    const rowsHtml = pekerjaanList.map((pkj, idx) => {
      return createPekerjaanRow(pkj, idx + 1);
    }).join('');

    return `
      <div class="dp-card-secondary kt-sub-card mb-3" data-sub-id="${subId}" data-klas-id="${klasId}">
        <div class="d-flex align-items-center justify-content-between mb-2">
          <span class="dp-card-title-secondary fw-semibold">${escapeHtml(subNama)}</span>
          <button type="button"
                  class="btn btn-sm btn-outline-secondary dp-btn-sm kt-card-toggle"
                  data-type="sub"
                  data-key="${subId}"
                  aria-expanded="true"
                  title="Collapse/Expand">
            <i class="bi bi-caret-down-fill"></i>
          </button>
        </div>
        <div class="kt-sub-body" data-sub-id="${subId}">
          <table class="table dp-table kt-table table-sm">
            <thead class="table-light">
              <tr>
                <th class="text-center" style="width: 50px;">No</th>
                <th style="width: 100px;">Kode</th>
                <th style="min-width: 300px;">Uraian Pekerjaan</th>
                <th class="text-end" style="width: 100px;">Volume</th>
                <th style="width: 80px;">Satuan</th>
                <th style="width: 180px;">Tahapan</th>
                <th style="width: 320px;">Detail Proporsi</th>
                <th class="text-center" style="width: 100px;">Status</th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  function attachCollapseToggles() {
    document.querySelectorAll('.kt-card-toggle').forEach(btn => {
      btn.addEventListener('click', function() {
        const type = this.dataset.type;
        const key = this.dataset.key;
        const icon = this.querySelector('i');
        const isExpanded = this.getAttribute('aria-expanded') === 'true';

        if (type === 'klas') {
          const body = document.querySelector(`.kt-klas-body[data-klas-id="${key}"]`);
          if (body) {
            if (isExpanded) {
              body.style.display = 'none';
              icon.className = 'bi bi-caret-right-fill';
            } else {
              body.style.display = 'block';
              icon.className = 'bi bi-caret-down-fill';
            }
          }
        } else if (type === 'sub') {
          const body = document.querySelector(`.kt-sub-body[data-sub-id="${key}"]`);
          if (body) {
            if (isExpanded) {
              body.style.display = 'none';
              icon.className = 'bi bi-caret-right-fill';
            } else {
              body.style.display = 'block';
              icon.className = 'bi bi-caret-down-fill';
            }
          }
        }

        this.setAttribute('aria-expanded', !isExpanded);
      });
    });
  }

  function createPekerjaanRow(pkj, rowNum) {
    const volume = volumeMap.get(pkj.id) || 0;
    const pkjData = pekerjaanMap.get(pkj.id);
    const assignments = pkjData?.assignments || [];
    const totalAssigned = pkjData?.total_assigned || 0;

    // Determine status
    let status = 'unassigned';
    let statusBadge = '<span class="badge bg-secondary">Belum</span>';
    if (totalAssigned >= 99.99) {
      status = 'assigned';
      statusBadge = '<span class="badge bg-success">100%</span>';
    } else if (totalAssigned > 0) {
      status = 'partial';
      statusBadge = `<span class="badge bg-warning">${totalAssigned.toFixed(0)}%</span>`;
    }

    // Get currently assigned tahapan IDs
    const assignedTahapanIds = assignments.map(a => a.tahapan_id);

    return `
      <tr data-pekerjaan-id="${pkj.id}" data-status="${status}">
        <td class="text-center text-muted">${rowNum}</td>
        <td class="font-monospace">${escapeHtml(pkj.kode)}</td>
        <td>${escapeHtml(pkj.uraian)}</td>
        <td class="text-end font-monospace">${formatNumber(volume)}</td>
        <td>${escapeHtml(pkj.satuan)}</td>
        <td>
          ${createTahapanMultiSelect(pkj.id, assignedTahapanIds)}
        </td>
        <td>
          ${createProportionInputs(pkj.id, assignments, volume)}
        </td>
        <td class="text-center">
          ${statusBadge}
        </td>
      </tr>
    `;
  }

  function createTahapanMultiSelect(pekerjaanId, assignedIds = []) {
    // Create a simple multi-select with checkboxes in dropdown
    const options = tahapanList.map(t => {
      const checked = assignedIds.includes(t.tahapan_id) ? 'checked' : '';
      return `
        <div class="form-check form-check-sm">
          <input class="form-check-input tahapan-checkbox"
                 type="checkbox"
                 value="${t.tahapan_id}"
                 id="tahap-${pekerjaanId}-${t.tahapan_id}"
                 ${checked}
                 data-pekerjaan-id="${pekerjaanId}">
          <label class="form-check-label small" for="tahap-${pekerjaanId}-${t.tahapan_id}">
            ${escapeHtml(t.nama)}
          </label>
        </div>
      `;
    }).join('');

    return `
      <div class="dropdown">
        <button class="btn btn-sm btn-outline-primary dropdown-toggle w-100"
                type="button"
                data-bs-toggle="dropdown"
                aria-expanded="false"
                id="dropdown-btn-${pekerjaanId}">
          <span class="selected-count">${assignedIds.length}</span> Tahapan
        </button>
        <ul class="dropdown-menu dropdown-menu-checkbox p-2" style="max-height: 300px; overflow-y: auto;">
          ${options}
        </ul>
      </div>
    `;
  }

  function createProportionInputs(pekerjaanId, assignments = [], totalVolume = 0) {
    if (assignments.length === 0) {
      return '<span class="text-muted small">Pilih tahapan terlebih dahulu</span>';
    }

    // Get satuan from pekerjaan
    const pkj = allPekerjaan.find(p => p.id === pekerjaanId);
    const satuan = pkj?.satuan || '-';

    // Create dual input (percentage AND volume) for each assigned tahapan
    const inputs = assignments.map(a => {
      const tahap = tahapanList.find(t => t.tahapan_id === a.tahapan_id);
      if (!tahap) return '';

      const proportion = parseFloat(a.proporsi);
      const calculatedVolume = totalVolume > 0 ? (totalVolume * proportion / 100).toFixed(3) : '0.000';

      return `
        <div class="proportion-row mb-2" data-pekerjaan-id="${pekerjaanId}" data-tahapan-id="${a.tahapan_id}">
          <div class="d-flex align-items-center gap-2">
            <span class="text-muted small" style="min-width: 90px;">${escapeHtml(tahap.nama)}</span>

            <!-- Percentage Input -->
            <div class="input-group input-group-sm" style="width: 120px;">
              <input type="number"
                     class="form-control proportion-pct-input"
                     min="0.01"
                     max="100"
                     step="0.01"
                     value="${proportion.toFixed(2)}"
                     data-pekerjaan-id="${pekerjaanId}"
                     data-tahapan-id="${a.tahapan_id}"
                     data-original="${proportion.toFixed(2)}"
                     title="Input persentase">
              <span class="input-group-text">%</span>
            </div>

            <span class="text-muted">=</span>

            <!-- Volume Input (Calculated) -->
            <div class="input-group input-group-sm" style="width: 140px;">
              <input type="number"
                     class="form-control proportion-vol-input"
                     min="0"
                     step="0.001"
                     value="${calculatedVolume}"
                     data-pekerjaan-id="${pekerjaanId}"
                     data-tahapan-id="${a.tahapan_id}"
                     data-total-volume="${totalVolume}"
                     title="Input volume (akan auto-calculate persentase)"
                     ${totalVolume === 0 ? 'disabled' : ''}>
              <span class="input-group-text">${escapeHtml(satuan)}</span>
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Add total indicator
    const total = assignments.reduce((sum, a) => sum + parseFloat(a.proporsi || 0), 0);
    const totalClass = Math.abs(total - 100) < 0.01 ? 'text-success' : 'text-danger';
    const totalVolumeCalc = totalVolume > 0 ? (totalVolume * total / 100).toFixed(3) : '0.000';

    return `
      <div class="proportion-container" data-pekerjaan-id="${pekerjaanId}">
        ${inputs}
        <div class="d-flex justify-content-between align-items-center mt-2 pt-2 border-top">
          <span class="small ${totalClass} fw-bold">
            Total: <span class="total-proportion">${total.toFixed(2)}</span>%
          </span>
          <span class="small ${totalClass} fw-bold">
            = <span class="total-volume">${totalVolumeCalc}</span> ${escapeHtml(satuan)}
          </span>
        </div>
      </div>
    `;
  }

  function formatNumber(num) {
    if (!num && num !== 0) return '-';
    return parseFloat(num).toLocaleString('id-ID', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 3
    });
  }

  // =========================================================================
  // EVENT HANDLERS
  // =========================================================================

  function attachTableEventListeners() {
    // Tahapan checkbox change handler
    document.querySelectorAll('.tahapan-checkbox').forEach(checkbox => {
      checkbox.addEventListener('change', handleTahapanCheckboxChange);
    });

    // Proportion percentage input change handler
    document.querySelectorAll('.proportion-pct-input').forEach(input => {
      input.addEventListener('input', handleProportionPctInputChange);
      input.addEventListener('blur', validateProportionInput);
    });

    // Proportion volume input change handler
    document.querySelectorAll('.proportion-vol-input').forEach(input => {
      input.addEventListener('input', handleProportionVolInputChange);
    });

    // Prevent dropdown from closing when clicking checkboxes
    document.querySelectorAll('.dropdown-menu-checkbox').forEach(menu => {
      menu.addEventListener('click', (e) => {
        e.stopPropagation();
      });
    });
  }

  // Handler when user changes PERCENTAGE input
  function handleProportionPctInputChange(e) {
    const input = e.target;
    const pekerjaanId = parseInt(input.dataset.pekerjaanId);
    const tahapanId = parseInt(input.dataset.tahapanId);
    const newPct = parseFloat(input.value) || 0;

    // Update corresponding volume input
    const row = input.closest('.proportion-row');
    const volInput = row.querySelector('.proportion-vol-input');
    if (volInput) {
      const totalVolume = parseFloat(volInput.dataset.totalVolume) || 0;
      const calculatedVol = totalVolume > 0 ? (totalVolume * newPct / 100).toFixed(3) : '0.000';
      volInput.value = calculatedVol;
    }

    // Update local state and mark as dirty
    handleProportionInputChange(e);
  }

  // Handler when user changes VOLUME input
  function handleProportionVolInputChange(e) {
    const input = e.target;
    const pekerjaanId = parseInt(input.dataset.pekerjaanId);
    const tahapanId = parseInt(input.dataset.tahapanId);
    const newVol = parseFloat(input.value) || 0;
    const totalVolume = parseFloat(input.dataset.totalVolume) || 0;

    if (totalVolume > 0) {
      // Calculate percentage from volume
      const calculatedPct = ((newVol / totalVolume) * 100).toFixed(2);

      // Update corresponding percentage input
      const row = input.closest('.proportion-row');
      const pctInput = row.querySelector('.proportion-pct-input');
      if (pctInput) {
        pctInput.value = calculatedPct;

        // Trigger percentage input change to update local state
        pctInput.dispatchEvent(new Event('input', { bubbles: true }));
      }
    }
  }

  function handleTahapanCheckboxChange(e) {
    const checkbox = e.target;
    const pekerjaanId = parseInt(checkbox.dataset.pekerjaanId);
    const tahapanId = parseInt(checkbox.value);

    // Get all selected tahapan for this pekerjaan
    const row = checkbox.closest('tr');
    const selectedCheckboxes = row.querySelectorAll('.tahapan-checkbox:checked');
    const selectedTahapanIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));

    // Update dropdown button text
    const dropdownBtn = row.querySelector(`#dropdown-btn-${pekerjaanId} .selected-count`);
    if (dropdownBtn) {
      dropdownBtn.textContent = selectedTahapanIds.length;
    }

    // Auto-calculate proportions based on 3 conditions
    const pkjData = pekerjaanMap.get(pekerjaanId);
    const newAssignments = calculateProportions(selectedTahapanIds, pkjData);

    // Update pekerjaanMap
    if (pkjData) {
      pkjData.assignments = newAssignments;
      pkjData.total_assigned = newAssignments.reduce((sum, a) => sum + parseFloat(a.proporsi), 0);
    }

    // Re-render proportion inputs
    const proportionCell = row.querySelector(`td:nth-child(9)`);
    if (proportionCell) {
      proportionCell.innerHTML = createProportionInputs(pekerjaanId, newAssignments);

      // Reattach event listeners for new inputs
      proportionCell.querySelectorAll('.proportion-input').forEach(input => {
        input.addEventListener('input', handleProportionInputChange);
        input.addEventListener('blur', validateProportionInput);
      });
    }

    // Mark as changed
    markRowAsChanged(row);
  }

  function calculateProportions(tahapanIds, pkjData) {
    if (tahapanIds.length === 0) return [];

    const existingAssignments = pkjData?.assignments || [];
    const newAssignments = [];

    // Detect pattern: single, range, or combination
    const sortedIds = [...tahapanIds].sort((a, b) => {
      const aIdx = tahapanList.findIndex(t => t.tahapan_id === a);
      const bIdx = tahapanList.findIndex(t => t.tahapan_id === b);
      return aIdx - bIdx;
    });

    // Calculate equal distribution
    const equalProportion = parseFloat((100 / sortedIds.length).toFixed(2));
    let remainder = parseFloat((100 - equalProportion * sortedIds.length).toFixed(2));

    sortedIds.forEach((tahapanId, idx) => {
      // Check if this tahapan already has assignment
      const existing = existingAssignments.find(a => a.tahapan_id === tahapanId);
      let proporsi = existing ? parseFloat(existing.proporsi) : equalProportion;

      // Add remainder to first item to ensure total = 100%
      if (idx === 0 && remainder !== 0) {
        proporsi += remainder;
      }

      newAssignments.push({
        tahapan_id: tahapanId,
        proporsi: parseFloat(proporsi.toFixed(2))
      });
    });

    return newAssignments;
  }

  function handleProportionInputChange(e) {
    const input = e.target;
    const pekerjaanId = parseInt(input.dataset.pekerjaanId);
    const row = input.closest('tr');

    // Recalculate total
    updateTotalProportion(row);

    // Mark as changed
    markRowAsChanged(row);
  }

  function validateProportionInput(e) {
    const input = e.target;
    let value = parseFloat(input.value);

    if (isNaN(value) || value < 0.01) {
      value = 0.01;
    } else if (value > 100) {
      value = 100;
    }

    input.value = value.toFixed(2);

    // Update pekerjaanMap
    const pekerjaanId = parseInt(input.dataset.pekerjaanId);
    const tahapanId = parseInt(input.dataset.tahapanId);
    const pkjData = pekerjaanMap.get(pekerjaanId);

    if (pkjData) {
      const assignment = pkjData.assignments.find(a => a.tahapan_id === tahapanId);
      if (assignment) {
        assignment.proporsi = value;
      }

      // Recalculate total
      pkjData.total_assigned = pkjData.assignments.reduce((sum, a) => sum + parseFloat(a.proporsi), 0);
    }

    // Recalculate total display
    const row = input.closest('tr');
    updateTotalProportion(row);
  }

  function updateTotalProportion(row) {
    const proportionContainer = row.querySelector('.proportion-container');
    if (!proportionContainer) return;

    const inputs = proportionContainer.querySelectorAll('.proportion-pct-input');
    let totalPct = 0;

    inputs.forEach(input => {
      totalPct += parseFloat(input.value) || 0;
    });

    // Update total percentage
    const totalPctSpan = proportionContainer.querySelector('.total-proportion');
    if (totalPctSpan) {
      totalPctSpan.textContent = totalPct.toFixed(2);
    }

    // Update total volume
    const totalVolSpan = proportionContainer.querySelector('.total-volume');
    if (totalVolSpan) {
      const firstVolInput = proportionContainer.querySelector('.proportion-vol-input');
      if (firstVolInput) {
        const totalVolume = parseFloat(firstVolInput.dataset.totalVolume) || 0;
        const calculatedTotal = totalVolume > 0 ? (totalVolume * totalPct / 100).toFixed(3) : '0.000';
        totalVolSpan.textContent = calculatedTotal;
      }
    }

    // Update styling based on total
    const totalContainers = proportionContainer.querySelectorAll('.border-top span');
    totalContainers.forEach(container => {
      container.classList.remove('text-success', 'text-danger', 'text-warning');
      if (Math.abs(totalPct - 100) < 0.01) {
        container.classList.add('text-success');
      } else {
        container.classList.add('text-danger');
      }
    });
  }

  function markRowAsChanged(row) {
    if (!row.classList.contains('table-warning')) {
      row.classList.add('table-warning');
    }

    // Track in changes Map
    const pekerjaanId = parseInt(row.dataset.pekerjaanId);
    if (!changes.has(pekerjaanId)) {
      changes.set(pekerjaanId, true);
    }

    // Enable save button
    const saveBtn = document.getElementById('btn-save-all');
    if (saveBtn && changes.size > 0) {
      saveBtn.disabled = false;
      saveBtn.innerHTML = `
        <i class="bi bi-save"></i>
        <span class="d-none d-sm-inline">Simpan (${changes.size})</span>
      `;
    }
  }

  // =========================================================================
  // SAVE FUNCTIONALITY
  // =========================================================================

  async function saveAllChanges() {
    if (changes.size === 0) {
      showToast('Tidak ada perubahan untuk disimpan', 'info');
      return;
    }

    showLoadingOverlay(true);

    try {
      const changedPekerjaanIds = Array.from(changes.keys());
      let successCount = 0;
      let errorCount = 0;

      for (const pekerjaanId of changedPekerjaanIds) {
        try {
          await savePekerjaanAssignments(pekerjaanId);
          successCount++;
        } catch (error) {
          console.error(`Failed to save pekerjaan ${pekerjaanId}:`, error);
          errorCount++;
        }
      }

      // Clear changes
      changes.clear();

      // Reload data to get fresh state
      await loadAllData();

      // Show result
      if (errorCount === 0) {
        showToast(`Berhasil menyimpan ${successCount} pekerjaan`, 'success');
      } else {
        showToast(`Berhasil: ${successCount}, Gagal: ${errorCount}`, 'warning');
      }

      // Reset save button
      const saveBtn = document.getElementById('btn-save-all');
      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = `
          <i class="bi bi-save"></i>
          <span class="d-none d-sm-inline">Simpan Semua</span>
        `;
      }

    } catch (error) {
      showToast('Gagal menyimpan: ' + error.message, 'error');
    } finally {
      showLoadingOverlay(false);
    }
  }

  async function savePekerjaanAssignments(pekerjaanId) {
    const pkjData = pekerjaanMap.get(pekerjaanId);
    if (!pkjData) throw new Error('Pekerjaan not found');

    const assignments = pkjData.assignments || [];

    // Group assignments by tahapan
    const assignmentsByTahapan = new Map();
    assignments.forEach(a => {
      if (!assignmentsByTahapan.has(a.tahapan_id)) {
        assignmentsByTahapan.set(a.tahapan_id, []);
      }
      assignmentsByTahapan.get(a.tahapan_id).push({
        pekerjaan_id: pekerjaanId,
        proporsi: parseFloat(a.proporsi)
      });
    });

    // Save to each tahapan
    for (const [tahapanId, tahapAssignments] of assignmentsByTahapan.entries()) {
      await apiCall(`${apiBase}${tahapanId}/assign/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ assignments: tahapAssignments })
      });
    }

    // Remove from tahapan that are no longer selected
    const currentTahapanIds = new Set(assignments.map(a => a.tahapan_id));
    const allTahapanIds = new Set(tahapanList.map(t => t.tahapan_id));

    for (const tahapanId of allTahapanIds) {
      if (!currentTahapanIds.has(tahapanId)) {
        try {
          await apiCall(`${apiBase}${tahapanId}/unassign/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ pekerjaan_ids: [pekerjaanId] })
          });
        } catch (e) {
          // Ignore if assignment doesn't exist
          console.warn(`Failed to unassign pekerjaan ${pekerjaanId} from tahapan ${tahapanId}:`, e);
        }
      }
    }
  }

  // =========================================================================
  // SIDEBAR - TAHAPAN MANAGEMENT
  // =========================================================================

  function renderTahapanSidebar() {
    if (!$tahapanListSidebar || !$tahapanCount) return;

    $tahapanCount.textContent = tahapanList.length;

    if (tahapanList.length === 0) {
      $tahapanListSidebar.innerHTML = '<div class="text-muted small">Belum ada tahapan</div>';
      return;
    }

    const html = tahapanList.map(t => `
      <div class="card card-sm">
        <div class="card-body p-2">
          <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
              <div class="fw-bold small">${escapeHtml(t.nama)}</div>
              <div class="text-muted" style="font-size: 0.75rem;">
                Urutan: ${t.urutan} | Pekerjaan: ${t.jumlah_pekerjaan || 0}
              </div>
            </div>
            <div class="btn-group btn-group-sm">
              <button type="button" class="btn btn-outline-secondary btn-sm"
                      data-action="edit-tahapan"
                      data-tahapan-id="${t.tahapan_id}"
                      title="Edit">
                <i class="bi bi-pencil"></i>
              </button>
              <button type="button" class="btn btn-outline-danger btn-sm"
                      data-action="delete-tahapan"
                      data-tahapan-id="${t.tahapan_id}"
                      title="Hapus">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    `).join('');

    $tahapanListSidebar.innerHTML = html;

    // Attach event listeners
    $tahapanListSidebar.querySelectorAll('[data-action="edit-tahapan"]').forEach(btn => {
      btn.addEventListener('click', () => editTahapan(parseInt(btn.dataset.tahapanId)));
    });

    $tahapanListSidebar.querySelectorAll('[data-action="delete-tahapan"]').forEach(btn => {
      btn.addEventListener('click', () => deleteTahapan(parseInt(btn.dataset.tahapanId)));
    });
  }

  async function saveTahapan(e) {
    e.preventDefault();

    const tahapanId = document.getElementById('tahapan-id').value;
    const nama = document.getElementById('tahapan-nama').value.trim();
    const urutan = document.getElementById('tahapan-urutan').value;
    const deskripsi = document.getElementById('tahapan-deskripsi').value.trim();
    const tanggalMulai = document.getElementById('tahapan-tanggal-mulai').value;
    const tanggalSelesai = document.getElementById('tahapan-tanggal-selesai').value;

    if (!nama) {
      showToast('Nama tahapan harus diisi', 'error');
      return;
    }

    const payload = {
      nama,
      deskripsi,
      tanggal_mulai: tanggalMulai || null,
      tanggal_selesai: tanggalSelesai || null
    };

    if (urutan) {
      payload.urutan = parseInt(urutan);
    }

    showLoadingOverlay(true);

    try {
      let url, method;

      if (tahapanId) {
        // Update
        url = `${apiBase}${tahapanId}/`;
        method = 'PUT';
      } else {
        // Create
        url = apiBase;
        method = 'POST';
      }

      await apiCall(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(payload)
      });

      showToast(tahapanId ? 'Tahapan berhasil diupdate' : 'Tahapan berhasil ditambahkan', 'success');

      // Reset form
      $formTahapan.reset();
      document.getElementById('form-title').textContent = 'Tambah Tahapan Baru';

      // Reload data
      await loadAllData();

    } catch (error) {
      showToast('Gagal menyimpan tahapan: ' + error.message, 'error');
    } finally {
      showLoadingOverlay(false);
    }
  }

  async function editTahapan(tahapanId) {
    const tahap = tahapanList.find(t => t.tahapan_id === tahapanId);
    if (!tahap) return;

    // Populate form
    document.getElementById('tahapan-id').value = tahap.tahapan_id;
    document.getElementById('tahapan-nama').value = tahap.nama;
    document.getElementById('tahapan-urutan').value = tahap.urutan;
    document.getElementById('tahapan-deskripsi').value = tahap.deskripsi || '';
    document.getElementById('tahapan-tanggal-mulai').value = tahap.tanggal_mulai || '';
    document.getElementById('tahapan-tanggal-selesai').value = tahap.tanggal_selesai || '';

    document.getElementById('form-title').textContent = 'Edit Tahapan';

    // Scroll to form
    $formTahapan.scrollIntoView({ behavior: 'smooth' });
  }

  async function deleteTahapan(tahapanId) {
    const tahap = tahapanList.find(t => t.tahapan_id === tahapanId);
    if (!tahap) return;

    if (!confirm(`Hapus tahapan "${tahap.nama}"?\n\nSemua assignment pekerjaan ke tahapan ini akan dihapus.`)) {
      return;
    }

    showLoadingOverlay(true);

    try {
      await apiCall(`${apiBase}${tahapanId}/`, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': getCookie('csrftoken')
        }
      });

      showToast('Tahapan berhasil dihapus', 'success');

      // Reload data
      await loadAllData();

    } catch (error) {
      showToast('Gagal menghapus tahapan: ' + error.message, 'error');
    } finally {
      showLoadingOverlay(false);
    }
  }

  // =========================================================================
  // FILTERS & SEARCH
  // =========================================================================

  function applyFilters() {
    const searchQuery = $searchInput?.value.toLowerCase() || '';
    const filterKlas = $filterKlasifikasi?.value || '';
    const filterStat = $filterStatus?.value || '';

    let visibleCount = 0;

    document.querySelectorAll('#pekerjaan-tbody tr').forEach(row => {
      const pekerjaanId = row.dataset.pekerjaanId;
      if (!pekerjaanId) return;

      const pkj = pekerjaanMap.get(parseInt(pekerjaanId));
      if (!pkj) return;

      const text = (pkj.kode + ' ' + pkj.uraian + ' ' + pkj.klasifikasi + ' ' + pkj.sub_klasifikasi).toLowerCase();
      const matchesSearch = searchQuery === '' || text.includes(searchQuery);
      const matchesKlas = filterKlas === '' || pkj.klasifikasi === filterKlas;
      const matchesStatus = filterStat === '' || row.dataset.status === filterStat;

      if (matchesSearch && matchesKlas && matchesStatus) {
        row.style.display = '';
        visibleCount++;
      } else {
        row.style.display = 'none';
      }
    });

    document.getElementById('showing-count').textContent = visibleCount;
  }

  function resetFilters() {
    if ($searchInput) $searchInput.value = '';
    if ($filterKlasifikasi) $filterKlasifikasi.value = '';
    if ($filterStatus) $filterStatus.value = '';
    applyFilters();
  }

  // =========================================================================
  // SIDEBAR TOGGLE
  // =========================================================================

  try {
    const btnToggle = document.querySelector('.js-kt-sidebar-toggle');
    const btnClose = document.querySelector('.js-kt-sidebar-close');
    const hotspot = document.querySelector('.vp-overlay-hotspot');

    const openSidebar = () => {
      if (!sidebar) return;
      sidebar.classList.add('is-open');
      sidebar.setAttribute('aria-hidden', 'false');
      if (btnToggle) btnToggle.setAttribute('aria-expanded', 'true');
    };

    const closeSidebar = () => {
      if (!sidebar) return;
      sidebar.classList.remove('is-open');
      sidebar.setAttribute('aria-hidden', 'true');
      if (btnToggle) btnToggle.setAttribute('aria-expanded', 'false');
    };

    if (btnToggle) {
      btnToggle.addEventListener('click', () => {
        if (!sidebar) return;
        const isOpen = sidebar.classList.contains('is-open');
        isOpen ? closeSidebar() : openSidebar();
      });
    }

    if (btnClose) {
      btnClose.addEventListener('click', closeSidebar);
    }

    // Click outside closes
    if (sidebar) {
      sidebar.addEventListener('mousedown', (e) => {
        const inner = sidebar.querySelector('.dp-sidebar-inner');
        if (inner && !inner.contains(e.target)) closeSidebar();
      });
    }

    // ESC closes
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeSidebar();
    });

    // Hover edge opens
    if (hotspot) {
      let hoverTimer = null;
      hotspot.addEventListener('mouseenter', () => {
        hoverTimer = setTimeout(openSidebar, 200);
      });
      hotspot.addEventListener('mouseleave', () => {
        if (hoverTimer) clearTimeout(hoverTimer);
      });
    }

    // Resizer
    const handle = sidebar?.querySelector('.dp-resizer');
    const inner = sidebar?.querySelector('.dp-sidebar-inner');
    if (handle && inner) {
      let startX = 0;
      let startW = 0;
      let dragging = false;

      const onMove = (e) => {
        if (!dragging) return;
        const dx = startX - (e.clientX || 0);
        let w = Math.max(320, Math.min(760, startW + dx));
        inner.style.width = w + 'px';
      };

      const onUp = () => {
        dragging = false;
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
      };

      handle.addEventListener('mousedown', (e) => {
        dragging = true;
        startX = e.clientX;
        startW = inner.getBoundingClientRect().width;
        document.addEventListener('mousemove', onMove);
        document.addEventListener('mouseup', onUp);
        e.preventDefault();
      });
    }
  } catch (e) {
    console.error('Sidebar setup error:', e);
  }

  // =========================================================================
  // EVENT BINDINGS
  // =========================================================================

  // Save all button
  document.getElementById('btn-save-all')?.addEventListener('click', saveAllChanges);

  // Tahapan form submit
  if ($formTahapan) {
    $formTahapan.addEventListener('submit', saveTahapan);
  }

  // Reset form button
  document.getElementById('btn-reset-form')?.addEventListener('click', () => {
    $formTahapan.reset();
    document.getElementById('form-title').textContent = 'Tambah Tahapan Baru';
  });

  // Filters
  if ($searchInput) {
    $searchInput.addEventListener('input', applyFilters);
  }
  if ($filterKlasifikasi) {
    $filterKlasifikasi.addEventListener('change', applyFilters);
  }
  if ($filterStatus) {
    $filterStatus.addEventListener('change', applyFilters);
  }
  document.getElementById('btn-reset-filters')?.addEventListener('click', resetFilters);

  // =========================================================================
  // INITIALIZATION
  // =========================================================================

  loadAllData();

})();
