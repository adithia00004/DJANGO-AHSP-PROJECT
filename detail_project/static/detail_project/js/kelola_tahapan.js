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
    console.log('=== LOAD ALL DATA START ===');
    showLoading(true);
    try {
      // Load tahapan list
      console.log('Step 1: Loading tahapan...');
      await loadTahapan();
      console.log('Step 1 DONE: tahapanList.length =', tahapanList.length);

      // Check if we have tahapan, if not auto-create Tahap 1
      if (tahapanList.length === 0) {
        console.log('Step 2: No tahapan found, auto-initializing...');
        await autoInitializeTahap1();
        console.log('Step 2 DONE: tahapanList.length =', tahapanList.length);
      }

      // Load pekerjaan tree
      console.log('Step 3: Loading pekerjaan...');
      await loadPekerjaan();
      console.log('Step 3 DONE: allPekerjaan.length =', allPekerjaan.length);
      console.log('Step 3 DONE: pekerjaanMap.size =', pekerjaanMap.size);

      // Load volumes
      console.log('Step 4: Loading volumes...');
      await loadVolumes();
      console.log('Step 4 DONE: volumeMap.size =', volumeMap.size);

      // Load all assignments
      console.log('Step 5: Loading assignments...');
      await loadAllAssignments();
      console.log('Step 5 DONE');

      // Auto-assign unassigned pekerjaan to Tahap 1
      console.log('Step 6: Auto-assigning unassigned...');
      await autoAssignUnassignedToTahap1();
      console.log('Step 6 DONE');

      // Render table
      console.log('Step 7: Rendering table...');
      renderTable();
      console.log('Step 7 DONE');

      // Show main container
      console.log('Step 8: Showing main container...');
      showEmpty(false);
      console.log('Step 8 DONE');

      console.log('=== LOAD ALL DATA COMPLETE ===');

    } catch (error) {
      console.error('!!! LOAD ALL DATA FAILED !!!');
      console.error('Error:', error);
      console.error('Stack:', error.stack);
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
      console.log('DEBUG loadPekerjaan: Fetching from API...');
      const response = await apiCall(`/detail_project/api/project/${projectId}/list-pekerjaan/tree/`);
      console.log('DEBUG loadPekerjaan: API response =', response);

      allPekerjaan = [];

      // Flatten tree structure
      function flattenNode(node) {
        if (!node) return;
        if (Array.isArray(node)) {
          node.forEach(n => flattenNode(n));
          return;
        }

        if (node.type === 'pekerjaan') {
          const pkjData = {
            id: node.pekerjaan_id,
            kode: node.snapshot_kode || node.kode,
            uraian: node.snapshot_uraian || node.uraian,
            satuan: node.snapshot_satuan || node.satuan || '-',
            klasifikasi: node.klasifikasi_nama || '',
            sub_klasifikasi: node.sub_klasifikasi_nama || '',
            ordering_index: node.ordering_index || 0
          };

          allPekerjaan.push(pkjData);

          // Initialize in pekerjaanMap
          pekerjaanMap.set(node.pekerjaan_id, {
            ...pkjData,
            assignments: [] // Will be populated later
          });
        }

        if (node.children) {
          node.children.forEach(child => flattenNode(child));
        }
      }

      flattenNode(response);

      console.log('DEBUG loadPekerjaan: Flattened allPekerjaan.length =', allPekerjaan.length);
      if (allPekerjaan.length > 0) {
        console.log('DEBUG loadPekerjaan: First pekerjaan =', allPekerjaan[0]);
      }

      // Populate filter klasifikasi dropdown
      const klasifikasiSet = new Set(allPekerjaan.map(p => p.klasifikasi).filter(Boolean));
      if ($filterKlasifikasi) {
        $filterKlasifikasi.innerHTML = '<option value="">Semua Klasifikasi</option>' +
          Array.from(klasifikasiSet).map(k => `<option value="${escapeHtml(k)}">${escapeHtml(k)}</option>`).join('');
      }

      return allPekerjaan;
    } catch (error) {
      console.error('Failed to load pekerjaan:', error);
      console.error('Error details:', error.message, error.stack);
      throw error;
    }
  }

  async function loadVolumes() {
    try {
      const data = await apiCall(`/detail_project/api/project/${projectId}/volume-pekerjaan/list/`);
      volumeMap.clear();

      (data.volumes || []).forEach(v => {
        volumeMap.set(v.pekerjaan_id, parseFloat(v.quantity) || 0);
      });

      return volumeMap;
    } catch (error) {
      console.error('Failed to load volumes:', error);
      // Non-critical, continue without volumes
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
    console.log('Auto-initializing Tahap 1...');
    try {
      // Create Tahap 1 automatically
      const response = await apiCall(apiBase, {
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

      console.log('DEBUG: Create Tahap 1 response =', response);

      // Reload tahapan list with retry
      let retries = 3;
      while (retries > 0) {
        await loadTahapan();
        if (tahapanList.length > 0) {
          console.log('Tahap 1 created and loaded successfully');
          showStatus('Tahap 1 telah dibuat secara otomatis', 'success');
          return;
        }
        retries--;
        if (retries > 0) {
          console.log(`Tahapan list still empty, retrying... (${retries} retries left)`);
          await new Promise(resolve => setTimeout(resolve, 500)); // Wait 500ms before retry
        }
      }

      console.warn('Tahap 1 created but not found in tahapanList after retries');
    } catch (error) {
      console.error('Failed to auto-initialize Tahap 1:', error);
      // Non-critical, continue
    }
  }

  async function autoAssignUnassignedToTahap1() {
    // Debug: Log tahapanList
    console.log('DEBUG: tahapanList =', tahapanList);
    console.log('DEBUG: tahapanList length =', tahapanList.length);
    if (tahapanList.length > 0) {
      console.log('DEBUG: First tahapan =', tahapanList[0]);
    }

    // Find Tahap 1 (try multiple methods)
    let tahap1 = tahapanList.find(t => t.nama && t.nama.toLowerCase().includes('tahap 1'));

    if (!tahap1) {
      // Try by urutan
      tahap1 = tahapanList.find(t => t.urutan === 1);
    }

    if (!tahap1) {
      // Try first tahapan as fallback
      tahap1 = tahapanList[0];
    }

    if (!tahap1) {
      console.warn('Tahap 1 not found, skipping auto-assignment');
      console.warn('DEBUG: Available tahapan:', tahapanList);
      return;
    }

    console.log('DEBUG: Using tahap1 =', tahap1);

    // Find all unassigned or partially assigned pekerjaan
    const unassignedPekerjaan = [];

    pekerjaanMap.forEach((pkjData, pkjId) => {
      const totalAssigned = pkjData.total_assigned || 0;

      // If completely unassigned or partially assigned
      if (totalAssigned < 99.99) {
        const remainingProportion = 100 - totalAssigned;

        // Check if already has Tahap 1 assignment
        const existingTahap1 = pkjData.assignments.find(a => a.tahapan_id === tahap1.tahapan_id);

        if (!existingTahap1 && remainingProportion > 0) {
          // Add to unassigned list
          unassignedPekerjaan.push({
            pekerjaan_id: pkjId,
            proporsi: remainingProportion
          });

          // Update local state
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
      console.log(`Auto-assigning ${unassignedPekerjaan.length} pekerjaan to Tahap 1...`);

      try {
        // Batch assign in chunks to avoid oversized payloads
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

        console.log('Auto-assignment completed successfully');
        showStatus(`${unassignedPekerjaan.length} pekerjaan telah di-assign ke Tahap 1 secara otomatis`, 'success');
      } catch (error) {
        console.error('Failed to auto-assign to Tahap 1:', error);
        showToast('Gagal auto-assign ke Tahap 1: ' + error.message, 'warning');
      }
    }
  }

  // =========================================================================
  // TABLE RENDERING
  // =========================================================================

  function renderTable() {
    console.log('DEBUG renderTable: Starting...');
    console.log('DEBUG renderTable: $tbody =', $tbody);
    console.log('DEBUG renderTable: allPekerjaan.length =', allPekerjaan.length);

    if (!$tbody) {
      console.error('DEBUG renderTable: $tbody is null!');
      return;
    }

    if (allPekerjaan.length === 0) {
      console.warn('DEBUG renderTable: No pekerjaan to render');
      $tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted py-4">Tidak ada pekerjaan</td></tr>';
      return;
    }

    console.log('DEBUG renderTable: Creating rows...');
    const html = allPekerjaan.map((pkj, idx) => {
      try {
        return createTableRow(pkj, idx + 1);
      } catch (error) {
        console.error('Error creating row for pekerjaan:', pkj, error);
        return '';
      }
    }).join('');

    console.log('DEBUG renderTable: HTML length =', html.length);
    console.log('DEBUG renderTable: First 500 chars =', html.substring(0, 500));

    $tbody.innerHTML = html;

    // Attach event listeners
    console.log('DEBUG renderTable: Attaching event listeners...');
    attachTableEventListeners();

    // Update count
    const showingCount = document.getElementById('showing-count');
    const totalCount = document.getElementById('total-count');
    if (showingCount) showingCount.textContent = allPekerjaan.length;
    if (totalCount) totalCount.textContent = allPekerjaan.length;

    console.log('DEBUG renderTable: Complete!');
  }

  function createTableRow(pkj, rowNum) {
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
        <td>${escapeHtml(pkj.klasifikasi)}</td>
        <td>${escapeHtml(pkj.sub_klasifikasi)}</td>
        <td class="font-monospace">${escapeHtml(pkj.kode)}</td>
        <td>${escapeHtml(pkj.uraian)}</td>
        <td class="text-end font-monospace">${formatNumber(volume)}</td>
        <td>${escapeHtml(pkj.satuan)}</td>
        <td>
          ${createTahapanMultiSelect(pkj.id, assignedTahapanIds)}
        </td>
        <td>
          ${createProportionInputs(pkj.id, assignments)}
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

  function createProportionInputs(pekerjaanId, assignments = []) {
    if (assignments.length === 0) {
      return '<span class="text-muted small">Pilih tahapan terlebih dahulu</span>';
    }

    // Create proportion inputs for each assigned tahapan
    const inputs = assignments.map(a => {
      const tahap = tahapanList.find(t => t.tahapan_id === a.tahapan_id);
      if (!tahap) return '';

      return `
        <div class="input-group input-group-sm mb-2">
          <span class="input-group-text" style="min-width: 120px;">${escapeHtml(tahap.nama)}</span>
          <input type="number"
                 class="form-control proportion-input"
                 min="0.01"
                 max="100"
                 step="0.01"
                 value="${parseFloat(a.proporsi).toFixed(2)}"
                 data-pekerjaan-id="${pekerjaanId}"
                 data-tahapan-id="${a.tahapan_id}"
                 data-original="${parseFloat(a.proporsi).toFixed(2)}">
          <span class="input-group-text">%</span>
        </div>
      `;
    }).join('');

    // Add total indicator
    const total = assignments.reduce((sum, a) => sum + parseFloat(a.proporsi || 0), 0);
    const totalClass = Math.abs(total - 100) < 0.01 ? 'text-success' : 'text-danger';

    return `
      <div class="proportion-container" data-pekerjaan-id="${pekerjaanId}">
        ${inputs}
        <div class="text-end small ${totalClass} fw-bold">
          Total: <span class="total-proportion">${total.toFixed(2)}</span>%
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

    // Proportion input change handler
    document.querySelectorAll('.proportion-input').forEach(input => {
      input.addEventListener('input', handleProportionInputChange);
      input.addEventListener('blur', validateProportionInput);
    });

    // Prevent dropdown from closing when clicking checkboxes
    document.querySelectorAll('.dropdown-menu-checkbox').forEach(menu => {
      menu.addEventListener('click', (e) => {
        e.stopPropagation();
      });
    });
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
    const inputs = row.querySelectorAll('.proportion-input');
    let total = 0;

    inputs.forEach(input => {
      total += parseFloat(input.value) || 0;
    });

    const totalSpan = row.querySelector('.total-proportion');
    const totalContainer = totalSpan?.parentElement;

    if (totalSpan) {
      totalSpan.textContent = total.toFixed(2);
    }

    if (totalContainer) {
      totalContainer.classList.remove('text-success', 'text-danger', 'text-warning');
      if (Math.abs(total - 100) < 0.01) {
        totalContainer.classList.add('text-success');
      } else {
        totalContainer.classList.add('text-danger');
      }
    }
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
