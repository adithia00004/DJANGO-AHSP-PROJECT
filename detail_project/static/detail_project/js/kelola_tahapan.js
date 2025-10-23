// static/detail_project/js/kelola_tahapan.js
// Kelola Tahapan Pelaksanaan Manager

(function() {
  'use strict';

  // =========================================================================
  // CONFIGURATION & STATE
  // =========================================================================
  
  const app = document.getElementById('tahapan-app');
  if (!app) return;

  const projectId = parseInt(app.dataset.projectId);
  const apiBase = app.dataset.apiBase;

  // State
  let tahapanList = [];
  let currentTahapan = null;
  let allPekerjaan = [];
  // Client-side caches & state for smarter interactions
  let globalAssignCache = new Map(); // pekerjaan_id -> detail assignments (includes total_assigned)
  let unassignedCache = null; // { set: Set(ids), map: { id -> assigned_proportion } }
  let currentAssignedMap = {}; // pekerjaan_id -> proporsi (di tahapan aktif)

  // DOM Elements
  const $loading = document.getElementById('loading');
  const $emptyState = document.getElementById('empty-state');
  const $tahapanList = document.getElementById('tahapan-list');
  const $warningIncomplete = document.getElementById('warning-incomplete');
  const $incompleteCount = document.getElementById('incomplete-count');
  const $loadingOverlay = document.getElementById('loading-overlay');
  // Matrix mode elements
  const $matrixWrap = document.getElementById('matrix-mode');
  const $matrixThead = document.getElementById('matrix-thead');
  const $matrixTbody = document.getElementById('matrix-tbody');
  const $matrixSaveBtn = document.getElementById('btn-matrix-save');
  const $matrixChangeCount = document.getElementById('matrix-change-count');
  const $toggleMatrix = document.getElementById('toggle-matrix-mode');

  // Modals
  const modalTahapan = new bootstrap.Modal(document.getElementById('modal-tahapan'));
  const modalAssign = new bootstrap.Modal(document.getElementById('modal-assign'));
  const modalUnassigned = new bootstrap.Modal(document.getElementById('modal-unassigned'));
  const modalTahapanDetail = new bootstrap.Modal(document.getElementById('modal-tahapan-detail'));

  // Hover edge → open right offcanvas (to match Volume behavior)
  try {
    if (document.body && document.body.dataset && document.body.dataset.page === 'kelola_tahapan') {
      const hoverEdge = document.querySelector('.dp-hover-edge');
      const offcanvasEl = document.getElementById('vpVarOffcanvas');
      if (hoverEdge && offcanvasEl && window.bootstrap && window.bootstrap.Offcanvas) {
        const oc = window.bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
        let timer = null;
        hoverEdge.addEventListener('mouseenter', () => {
          timer = setTimeout(() => { try { oc.show(); } catch {} }, 180);
        });
        hoverEdge.addEventListener('mouseleave', () => {
          if (timer) { clearTimeout(timer); timer = null; }
        });
      }
    }
  } catch {}

  // Sidebar Overlay (dp-sidebar-overlay) toggling + hover edge open + resizer
  try {
    const sidebar = document.getElementById('kt-sidebar');
    const btnToggle = document.querySelector('.js-kt-sidebar-toggle');
    const btnClose = document.querySelector('.js-kt-sidebar-close');
    const hotspot = document.querySelector('.vp-overlay-hotspot');
    const hoverEdge = document.querySelector('.dp-hover-edge');

    const openSidebar = () => { if (!sidebar) return; sidebar.classList.add('is-open'); sidebar.setAttribute('aria-hidden','false'); btnToggle && btnToggle.setAttribute('aria-expanded','true'); };
    const closeSidebar = () => { if (!sidebar) return; sidebar.classList.remove('is-open'); sidebar.setAttribute('aria-hidden','true'); btnToggle && btnToggle.setAttribute('aria-expanded','false'); };

    btnToggle && btnToggle.addEventListener('click', () => {
      if (!sidebar) return;
      const isOpen = sidebar.classList.contains('is-open');
      isOpen ? closeSidebar() : openSidebar();
    });

    btnClose && btnClose.addEventListener('click', closeSidebar);

    // Click outside (overlay area) closes, but ignore clicks inside panel
    sidebar && sidebar.addEventListener('mousedown', (e) => {
      if (!sidebar) return;
      const inner = sidebar.querySelector('.dp-sidebar-inner');
      if (inner && !inner.contains(e.target)) closeSidebar();
    });

    // ESC to close
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSidebar(); });

    // Hover triggers open (both hotspot and right-edge)
    let hoverTimer = null;
    const scheduleOpen = () => { hoverTimer = setTimeout(openSidebar, 180); };
    const cancelOpen = () => { if (hoverTimer) { clearTimeout(hoverTimer); hoverTimer = null; } };
    hotspot && hotspot.addEventListener('mouseenter', scheduleOpen);
    hotspot && hotspot.addEventListener('mouseleave', cancelOpen);
    hoverEdge && hoverEdge.addEventListener('mouseenter', scheduleOpen);
    hoverEdge && hoverEdge.addEventListener('mouseleave', cancelOpen);

    // Resizer (simple east resize)
    if (sidebar) {
      const inner = sidebar.querySelector('.dp-sidebar-inner');
      const handle = sidebar.querySelector('.dp-resizer');
      if (inner && handle) {
        let startX = 0; let startW = 0; let dragging = false;
        const onMove = (e) => {
          if (!dragging) return;
          const dx = startX - (e.clientX || (e.touches && e.touches[0].clientX) || 0);
          let w = Math.max(320, Math.min(760, startW + dx));
          inner.style.width = w + 'px';
        };
        const onUp = () => { dragging = false; document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp); };
        handle.addEventListener('mousedown', (e) => { dragging = true; startX = e.clientX; startW = inner.getBoundingClientRect().width; document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp); e.preventDefault(); });
      }
    }
  } catch {}

  // =========================================================================
  // UTILITY FUNCTIONS
  // =========================================================================

  function showLoading(show = true) {
    $loading.classList.toggle('d-none', !show);
  }

  function showEmpty(show = true) {
    $emptyState.classList.toggle('d-none', !show);
  }

  function showLoadingOverlay(show = true) {
    $loadingOverlay.classList.toggle('d-none', !show);
  }

  function showToast(message, type = 'success') {
    if (window.DP && window.DP.core && window.DP.core.toast) {
      window.DP.core.toast.show(message, type);
      return;
    }
    try {
      const toastEl = document.getElementById('kt-toast');
      const toastBody = document.getElementById('kt-toast-body');
      if (toastEl && window.bootstrap) {
        toastEl.classList.remove('text-bg-success','text-bg-danger','text-bg-warning');
        toastEl.classList.add(type === 'error' ? 'text-bg-danger' : (type === 'warning' ? 'text-bg-warning' : 'text-bg-success'));
        if (toastBody) toastBody.textContent = message || 'OK';
        const t = window.bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 1600 });
        t.show();
        return;
      }
    } catch {}
    alert(message);
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

  function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('id-ID', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  }

  // =========================================================================
  // DATA LOADING
  // =========================================================================

  async function loadTahapan() {
    showLoading(true);
    try {
      const data = await apiCall(apiBase);
      tahapanList = data.tahapan || [];
      
      if (tahapanList.length === 0) {
        showEmpty(true);
        $tahapanList.innerHTML = '';
        // Offer default initialization of Tahap 1
        try { await ensureDefaultTahap(); } catch(e) { /* ignore */ }
      } else {
        showEmpty(false);
        renderTahapanList();
      }
      
      // Load validation status
      await loadValidationStatus();
      
    } catch (error) {
      console.error('Failed to load tahapan:', error);
      showToast('Gagal memuat tahapan: ' + error.message, 'error');
    } finally {
      showLoading(false);
    }
  }

  async function loadValidationStatus() {
    try {
      const data = await apiCall(`${apiBase}validate/`);
      
      if (data.incomplete > 0) {
        $incompleteCount.textContent = `${data.incomplete} dari ${data.total_pekerjaan}`;
        $warningIncomplete.classList.remove('d-none');
      } else {
        $warningIncomplete.classList.add('d-none');
      }
    } catch (error) {
      console.error('Failed to load validation:', error);
    }
  }

  async function loadAllPekerjaan() {
    try {
      // Use existing API to get pekerjaan tree
      const response = await apiCall(`/detail_project/api/project/${projectId}/list-pekerjaan/tree/`);
      allPekerjaan = [];
      
      // Flatten tree structure (supports array or single root)
      function flattenNode(node) {
        if (!node) return;
        if (Array.isArray(node)) { node.forEach(n => flattenNode(n)); return; }
        if (node.type === 'pekerjaan') {
          allPekerjaan.push({
            id: node.pekerjaan_id,
            kode: node.kode || node.snapshot_kode,
            uraian: node.uraian || node.snapshot_uraian,
            klasifikasi: node.klasifikasi_nama || '',
            sub_klasifikasi: node.sub_klasifikasi_nama || ''
          });
        }
        if (node.children) {
          node.children.forEach(child => flattenNode(child));
        }
      }
      
      flattenNode(response);
      
    } catch (error) {
      console.error('Failed to load pekerjaan:', error);
    }
  }

  // =========================================================================
  // RENDER FUNCTIONS
  // =========================================================================

  function renderTahapanList() {
    const html = tahapanList.map(tahap => createTahapanCard(tahap)).join('');
    $tahapanList.innerHTML = html;
    
    // Attach event listeners
    attachTahapanCardListeners();
  }

  function createTahapanCard(tahap) {
    const periode = tahap.tanggal_mulai || tahap.tanggal_selesai
      ? `${formatDate(tahap.tanggal_mulai)} - ${formatDate(tahap.tanggal_selesai)}`
      : 'Tanggal belum ditentukan';

    return `
      <div class="card dp-card-primary tahap-card" data-tahapan-id="${tahap.tahapan_id}">
        <div class="card-header tahap-header d-flex justify-content-between align-items-center">
          <div class="flex-grow-1">
            <h5 class="mb-0">
              <i class="bi bi-folder2"></i>
              ${escapeHtml(tahap.nama)}
            </h5>
            <small class="text-muted">
              <i class="bi bi-calendar3"></i> ${periode}
            </small>
          </div>
          <div class="btn-group btn-group-sm">
            <button class="btn btn-outline-primary dp-btn dp-btn-sm" data-action="assign" aria-label="Assign Pekerjaan" 
                    data-tahapan-id="${tahap.tahapan_id}"
                    title="Assign Pekerjaan">
              <i class="bi bi-plus-circle"></i>
            </button>
            <button class="btn btn-outline-secondary dp-btn dp-btn-sm" data-action="edit" aria-label="Edit Tahapan" 
                    data-tahapan-id="${tahap.tahapan_id}"
                    title="Edit Tahapan">
              <i class="bi bi-pencil"></i>
            </button>
            <button class="btn btn-outline-danger dp-btn dp-btn-sm" data-action="delete" aria-label="Hapus Tahapan" 
                    data-tahapan-id="${tahap.tahapan_id}"
                    title="Hapus Tahapan">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </div>
        <div class="card-body">
          ${tahap.deskripsi ? `<p class="text-muted small mb-2">${escapeHtml(tahap.deskripsi)}</p>` : ''}
          
          <div class="d-flex gap-3 mb-3">
            <span class="badge bg-primary">${tahap.jumlah_pekerjaan} Pekerjaan</span>
            <span class="badge bg-info">${tahap.total_assigned_proportion.toFixed(0)}% Total Proporsi</span>
          </div>

          <div class="d-flex justify-content-between align-items-center">
            <button class="btn btn-sm btn-outline-primary" 
                    data-action="view-detail" 
                    data-tahapan-id="${tahap.tahapan_id}">
              <i class="bi bi-eye"></i> Lihat Detail
            </button>
            <button class="btn btn-sm btn-outline-secondary" 
                    data-action="view-kebutuhan" 
                    data-tahapan-id="${tahap.tahapan_id}">
              <i class="bi bi-list-check"></i> Lihat Rekap Kebutuhan
            </button>
          </div>
        </div>
      </div>
    `;
  }

  function attachTahapanCardListeners() {
    // Assign buttons
    document.querySelectorAll('[data-action="assign"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tahapanId = parseInt(e.currentTarget.dataset.tahapanId);
        openAssignModal(tahapanId);
      });
    });

    // Edit buttons
    document.querySelectorAll('[data-action="edit"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tahapanId = parseInt(e.currentTarget.dataset.tahapanId);
        editTahapan(tahapanId);
      });
    });

    // Delete buttons
    document.querySelectorAll('[data-action="delete"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tahapanId = parseInt(e.currentTarget.dataset.tahapanId);
        deleteTahapan(tahapanId);
      });
    });

    // View detail buttons
    document.querySelectorAll('[data-action="view-detail"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tahapanId = parseInt(e.currentTarget.dataset.tahapanId);
        openTahapanDetailModal(tahapanId);
      });
    });

    // View kebutuhan buttons
    document.querySelectorAll('[data-action="view-kebutuhan"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tahapanId = parseInt(e.currentTarget.dataset.tahapanId);
        // Redirect to rekap kebutuhan dengan filter tahapan
        window.location.href = `/detail_project/${projectId}/rekap-kebutuhan/?tahapan=${tahapanId}`;
      });
    });
  }

  // =========================================================================
  // TAHAPAN CRUD OPERATIONS
  // =========================================================================

  function openTahapanModal(tahapan = null) {
    const $form = document.getElementById('form-tahapan');
    const $title = document.getElementById('modal-tahapan-title');
    
    $form.reset();
    
    if (tahapan) {
      $title.textContent = 'Edit Tahapan';
      document.getElementById('tahapan-id').value = tahapan.tahapan_id;
      document.getElementById('tahapan-nama').value = tahapan.nama;
      document.getElementById('tahapan-deskripsi').value = tahapan.deskripsi || '';
      document.getElementById('tahapan-tanggal-mulai').value = tahapan.tanggal_mulai || '';
      document.getElementById('tahapan-tanggal-selesai').value = tahapan.tanggal_selesai || '';
    } else {
      $title.textContent = 'Tambah Tahapan';
      document.getElementById('tahapan-id').value = '';
    }
    
    modalTahapan.show();
  }

  async function saveTahapan() {
    const tahapanId = document.getElementById('tahapan-id').value;
    const nama = document.getElementById('tahapan-nama').value.trim();
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

      modalTahapan.hide();
      showToast(tahapanId ? 'Tahapan berhasil diupdate' : 'Tahapan berhasil ditambahkan', 'success');
      await loadTahapan();
      
    } catch (error) {
      showToast('Gagal menyimpan tahapan: ' + error.message, 'error');
    } finally {
      showLoadingOverlay(false);
    }
  }

  async function editTahapan(tahapanId) {
    try {
      const data = await apiCall(`${apiBase}${tahapanId}/`);
      openTahapanModal(data.tahapan);
    } catch (error) {
      showToast('Gagal memuat data tahapan: ' + error.message, 'error');
    }
  }

  async function deleteTahapan(tahapanId) {
    const tahap = tahapanList.find(t => t.tahapan_id === tahapanId);
    if (!tahap) return;

    if (!confirm(`Hapus tahapan "${tahap.nama}"?\n\nPeringatan: Semua assignment pekerjaan ke tahapan ini akan dihapus.`)) {
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
      await loadTahapan();
      
    } catch (error) {
      showToast('Gagal menghapus tahapan: ' + error.message, 'error');
    } finally {
      showLoadingOverlay(false);
    }
  }

  async function viewTahapanDetail(tahapanId) {
    try {
      const data = await apiCall(`${apiBase}${tahapanId}/`);
      const tahap = data.tahapan;
      
      // Simple alert with detail (bisa di-enhance jadi modal yang lebih bagus)
      let message = `Tahapan: ${tahap.nama}\n\n`;
      message += `Pekerjaan (${tahap.jumlah_pekerjaan}):\n`;
      
      if (tahap.pekerjaan.length === 0) {
        message += '  (belum ada pekerjaan)\n';
      } else {
        tahap.pekerjaan.forEach(p => {
          message += `  • ${p.kode} - ${p.uraian} (${p.proporsi}%)\n`;
        });
      }
      
      try { message = message.replace(/�+/g, '-'); } catch {}
      alert(message);
      
    } catch (error) {
      showToast('Gagal memuat detail: ' + error.message, 'error');
    }
  }

  // =========================================================================
  // ASSIGNMENT OPERATIONS
  // =========================================================================

  async function openAssignModal(tahapanId) {
    const tahap = tahapanList.find(t => t.tahapan_id === tahapanId);
    if (!tahap) return;

    currentTahapan = tahap;
    
    document.getElementById('assign-tahapan-nama').textContent = tahap.nama;
    
    // Load pekerjaan if not loaded
    if (allPekerjaan.length === 0) {
      await loadAllPekerjaan();
    }

    // Load current assignments for this tahapan
    showLoadingOverlay(true);
    try {
      const data = await apiCall(`${apiBase}${tahapanId}/`);
      const assignedIds = new Set(data.tahapan.pekerjaan.map(p => p.pekerjaan_id));
      const assignedMap = {};
      data.tahapan.pekerjaan.forEach(p => {
        assignedMap[p.pekerjaan_id] = p.proporsi;
      });
      currentAssignedMap = assignedMap;

      renderPekerjaanList(assignedIds, assignedMap);
      modalAssign.show();
      setupAssignQuickTools();
      
    } catch (error) {
      showToast('Gagal memuat data: ' + error.message, 'error');
    } finally {
      showLoadingOverlay(false);
    }
  }

  function renderPekerjaanList(assignedIds, assignedMap) {
    const $list = document.getElementById('pekerjaan-list');
    
    let html = allPekerjaan.map(pkj => {
      const isAssigned = assignedIds.has(pkj.id);
      const proporsi = assignedMap[pkj.id] || 100;
      
      return `
        <div class="card mb-2">
          <div class="card-body py-2">
            <div class="form-check">
              <input class="form-check-input pekerjaan-checkbox" 
                     type="checkbox" 
                     value="${pkj.id}"
                     id="pkj-${pkj.id}"
                     ${isAssigned ? 'checked' : ''}>
              <label class="form-check-label flex-grow-1" for="pkj-${pkj.id}">
                <strong>${escapeHtml(pkj.kode)}</strong> - ${escapeHtml(pkj.uraian)}
                <br>
                <small class="text-muted">${escapeHtml(pkj.klasifikasi)} › ${escapeHtml(pkj.sub_klasifikasi)}</small>
              </label>
            </div>
            <div class="mt-2 ms-4">
              <label class="form-label small mb-1">Proporsi Volume (%)</label>
              <input type="number" 
                     class="form-control form-control-sm proporsi-input" 
                     data-pekerjaan-id="${pkj.id}"
                     value="${proporsi}"
                     min="0.01" 
                     max="100" 
                     step="0.01"
                     ${isAssigned ? '' : 'disabled'}>
            </div>
          </div>
        </div>
      `;
    }).join('');

    // Sanitize stray encoding artifacts (fallback fix)
    try { html = html.replace(/�+/g, '—'); } catch {}
    $list.innerHTML = html;
    
    // Enhance with smarter interactions (autofill/validation/filter)
    try { enhancePekerjaanListInteractions(assignedMap); } catch (e) { /* noop */ }
    
    // Enable/disable proporsi input based on checkbox
    document.querySelectorAll('.pekerjaan-checkbox').forEach(cb => {
      cb.addEventListener('change', (e) => {
        const pkjId = e.target.value;
        const proporsiInput = document.querySelector(`.proporsi-input[data-pekerjaan-id="${pkjId}"]`);
        proporsiInput.disabled = !e.target.checked;
      });
    });
  }

  async function saveAssignments() {
    if (!currentTahapan) return;

    const assignments = [];
    
    document.querySelectorAll('.pekerjaan-checkbox:checked').forEach(cb => {
      const pkjId = parseInt(cb.value);
      const proporsiInput = document.querySelector(`.proporsi-input[data-pekerjaan-id="${pkjId}"]`);
      const proporsi = parseFloat(proporsiInput.value);
      
      if (proporsi > 0) {
        assignments.push({
          pekerjaan_id: pkjId,
          proporsi: proporsi
        });
      }
    });

    if (assignments.length === 0) {
      showToast('Pilih minimal satu pekerjaan', 'warning');
      return;
    }

    // Guard: prevent exceeding 100% globally when cached
    const invalid = [];
    for (const a of assignments) {
      const cache = globalAssignCache.get(a.pekerjaan_id);
      const existing = currentAssignedMap[a.pekerjaan_id] || 0;
      if (cache && typeof cache.total_assigned === 'number') {
        const newTotal = (cache.total_assigned - existing) + a.proporsi;
        if (newTotal > 100.0001) {
          invalid.push({ id: a.pekerjaan_id, newTotal });
        }
      }
    }
    if (invalid.length > 0) {
      invalid.forEach(item => {
        const input = document.querySelector(`.proporsi-input[data-pekerjaan-id="${item.id}"]`);
        input && input.classList.add('is-invalid');
        const statusEl = document.getElementById(`status-${item.id}`);
        statusEl && (statusEl.textContent = `Melebihi 100% (akan ${item.newTotal.toFixed(2)}%)`);
      });
      showToast('Ada proporsi melebihi 100% secara global. Perbaiki input yang ditandai.', 'error');
      return;
    }

    if (assignments.length === 0) {
      showToast('Pilih minimal satu pekerjaan', 'warning');
      return;
    }

    showLoadingOverlay(true);
    
    try {
      const data = await apiCall(`${apiBase}${currentTahapan.tahapan_id}/assign/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ assignments })
      });

      modalAssign.hide();
      showToast(data.message || 'Assignments berhasil disimpan', 'success');
      await loadTahapan();
      
    } catch (error) {
      showToast('Gagal menyimpan assignments: ' + error.message, 'error');
    } finally {
      showLoadingOverlay(false);
    }
  }

  // =========================================================================
  // UNASSIGNED PEKERJAAN
  // =========================================================================

  async function showUnassignedPekerjaan() {
    showLoadingOverlay(true);
    
    try {
      const data = await apiCall(`${apiBase}unassigned/`);
      
      const $list = document.getElementById('unassigned-list');
      
      if (data.count === 0) {
        $list.innerHTML = `
          <div class="alert alert-success">
            <i class="bi bi-check-circle"></i>
            Semua pekerjaan sudah fully assigned ke tahapan!
          </div>
        `;
      } else {
        const html = `
          <p class="text-muted">Ditemukan ${data.count} pekerjaan yang belum/partial assigned:</p>
          <div class="list-group">
            ${data.pekerjaan.map(p => `
              <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-center">
                  <div>
                    <strong>${escapeHtml(p.kode)}</strong> - ${escapeHtml(p.uraian)}
                    <br>
                    <small class="text-muted">${escapeHtml(p.klasifikasi)} › ${escapeHtml(p.sub_klasifikasi)}</small>
                  </div>
                  <div>
                    <span class="badge ${p.status === 'unassigned' ? 'bg-danger' : 'bg-warning'}">
                      ${p.assigned_proportion.toFixed(0)}% / 100%
                    </span>
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
        `;
        $list.innerHTML = html;
      }
      
      modalUnassigned.show();
      
    } catch (error) {
      showToast('Gagal memuat data: ' + error.message, 'error');
    } finally {
      showLoadingOverlay(false);
    }
  }

  // =========================================================================
  // EVENT LISTENERS
  // =========================================================================

  document.getElementById('btn-add-tahapan')?.addEventListener('click', () => {
    openTahapanModal();
  });

  document.querySelectorAll('[data-trigger="add-tahapan"]').forEach(btn => {
    btn.addEventListener('click', () => openTahapanModal());
  });

  document.getElementById('btn-save-tahapan')?.addEventListener('click', saveTahapan);

  document.getElementById('btn-save-assignments')?.addEventListener('click', saveAssignments);

  document.getElementById('btn-validate')?.addEventListener('click', async () => {
    await loadValidationStatus();
    showToast('Validasi selesai', 'info');
  });

  document.getElementById('btn-show-incomplete')?.addEventListener('click', showUnassignedPekerjaan);

  // Search pekerjaan
  document.getElementById('search-pekerjaan')?.addEventListener('input', (e) => {
    const query = (e.target.value || '').toLowerCase();
    const onlyUnassigned = !!document.getElementById('filter-unassigned-toggle')?.checked;
    document.querySelectorAll('#pekerjaan-list .card').forEach(card => {
      const text = card.textContent.toLowerCase();
      const matchesSearch = text.includes(query);
      let matchesUnassigned = true;
      if (onlyUnassigned && unassignedCache && unassignedCache.set) {
        const cb = card.querySelector('.pekerjaan-checkbox');
        const id = cb ? parseInt(cb.value) : null;
        matchesUnassigned = id ? unassignedCache.set.has(id) : true;
      }
      card.style.display = (matchesSearch && matchesUnassigned) ? '' : 'none';
    });
  });

  // Matrix mode toggle
  $toggleMatrix?.addEventListener('change', async (e) => {
    const on = !!e.target.checked;
    await enableMatrixMode(on);
  });

  async function enableMatrixMode(on) {
    if (!$matrixWrap) return;
    if (on) {
      // Hide card list and empty state; show matrix
      $tahapanList?.classList.add('d-none');
      document.getElementById('empty-state')?.classList.add('d-none');
      $matrixWrap.classList.remove('d-none');
      showLoadingOverlay(true);
      try {
        await loadMatrixData();
        renderMatrix();
      } catch (e) {
        showToast('Gagal memuat matrix: ' + e.message, 'error');
      } finally {
        showLoadingOverlay(false);
      }
    } else {
      $matrixWrap.classList.add('d-none');
      $tahapanList?.classList.remove('d-none');
    }
  }

  $matrixSaveBtn?.addEventListener('click', saveMatrixChanges);

  // =========================================================================
  // HELPERS
  // =========================================================================

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ========================= Matrix Mode (Pivot) =========================
  let matrixOriginal = null; // { tahapan: [...], rows: [{id,kode,uraian,map:{tahapId:prop}}] }
  let matrixChanges = new Map(); // key `${pkjId}:${tahapId}` -> number

  function setMatrixChanged(key, value) {
    const orig = matrixGetOriginalValue(key);
    if (orig === value || (isNaN(value) && (orig === null || orig === undefined))) {
      matrixChanges.delete(key);
    } else {
      matrixChanges.set(key, value);
    }
    if ($matrixChangeCount) $matrixChangeCount.textContent = String(matrixChanges.size);
    if ($matrixSaveBtn) $matrixSaveBtn.disabled = matrixChanges.size === 0;
  }

  function matrixGetOriginalValue(key) {
    if (!matrixOriginal) return undefined;
    const [pkjIdStr, tahapIdStr] = key.split(':');
    const pkjId = parseInt(pkjIdStr), tahapId = parseInt(tahapIdStr);
    const row = matrixOriginal.rowsById[pkjId];
    if (!row) return undefined;
    return row.map[tahapId] || 0;
  }

  async function loadMatrixData() {
    // Ensure base data
    if (allPekerjaan.length === 0) await loadAllPekerjaan();
    // Reload tahapan summary
    const data = await apiCall(apiBase);
    const tahapan = (data.tahapan || []).map(t => ({ id: t.tahapan_id, nama: t.nama }));
    // Build per pekerjaan mapping
    const rows = allPekerjaan.map(p => ({ id: p.id, kode: p.kode || p.snapshot_kode, uraian: p.uraian || p.snapshot_uraian, map: {} }));
    const rowsById = Object.fromEntries(rows.map(r => [r.id, r]));
    // Fetch detail for each tahapan to populate proporsi map
    for (const t of tahapan) {
      try {
        const det = await apiCall(`${apiBase}${t.id}/`);
        (det.tahapan.pekerjaan || []).forEach(p => {
          const row = rowsById[p.pekerjaan_id];
          if (row) row.map[t.id] = p.proporsi || 0;
        });
      } catch (e) { /* skip single failure */ }
    }
    matrixOriginal = { tahapan, rows, rowsById };
    matrixChanges = new Map();
  }

  function renderMatrix() {
    if (!$matrixWrap) return;
    // Header
    const cols = matrixOriginal.tahapan.map(t => `<th class="text-end text-nowrap">${escapeHtml(t.nama)}</th>`).join('');
    $matrixThead.innerHTML = `
      <tr>
        <th style="width:160px" class="text-nowrap">Kode</th>
        <th>Uraian</th>
        ${cols}
        <th style="width:90px" class="text-end">Σ (%)</th>
      </tr>
    `;
    // Body
    const frag = document.createDocumentFragment();
    matrixOriginal.rows.forEach(row => {
      let sum = 0;
      const tr = document.createElement('tr');
      const codeTd = document.createElement('td'); codeTd.className = 'text-nowrap mono'; codeTd.textContent = row.kode || '-';
      const uraTd = document.createElement('td'); uraTd.textContent = row.uraian || '-';
      tr.appendChild(codeTd); tr.appendChild(uraTd);
      matrixOriginal.tahapan.forEach(t => {
        const val = row.map[t.id] || 0; sum += +val;
        const td = document.createElement('td'); td.className = 'text-end';
        td.innerHTML = `<input type="number" class="form-control form-control-sm text-end matrix-input" data-pkj-id="${row.id}" data-tahap-id="${t.id}" min="0" max="100" step="0.01" value="${(+val).toFixed(2)}">`;
        tr.appendChild(td);
      });
      const sumTd = document.createElement('td'); sumTd.className = 'text-end mono fw-semibold';
      sumTd.textContent = sum.toFixed(2);
      sumTd.dataset.sumFor = row.id;
      colorizeSum(sumTd, sum);
      tr.appendChild(sumTd);
      frag.appendChild(tr);
    });
    $matrixTbody.innerHTML = '';
    $matrixTbody.appendChild(frag);
    // Bind inputs
    $matrixTbody.querySelectorAll('.matrix-input').forEach(inp => {
      inp.addEventListener('input', onMatrixInputChange);
    });
    // Reset change state
    if ($matrixChangeCount) $matrixChangeCount.textContent = '0';
    if ($matrixSaveBtn) $matrixSaveBtn.disabled = true;
  }

  function colorizeSum(cell, sum) {
    cell.classList.remove('text-danger', 'text-warning', 'text-success');
    if (sum > 100.0001) cell.classList.add('text-danger');
    else if (sum < 99.999) cell.classList.add('text-warning');
    else cell.classList.add('text-success');
  }

  function onMatrixInputChange(e) {
    const inp = e.target;
    const pkjId = parseInt(inp.dataset.pkjId);
    const tahapId = parseInt(inp.dataset.tahapId);
    const key = `${pkjId}:${tahapId}`;
    const raw = parseFloat(inp.value);
    const v = isNaN(raw) ? 0 : Math.max(0, Math.min(100, raw));
    if (v !== raw) inp.value = v.toFixed(2);
    setMatrixChanged(key, v);
    // Update sum
    const row = matrixOriginal.rowsById[pkjId];
    let sum = 0;
    matrixOriginal.tahapan.forEach(t => {
      const k = `${pkjId}:${t.id}`;
      if (matrixChanges.has(k)) sum += +matrixChanges.get(k);
      else sum += +(row.map[t.id] || 0);
    });
    const sumCell = $matrixTbody.querySelector(`td[data-sum-for="${pkjId}"]`) || Array.from($matrixTbody.querySelectorAll('td')).find(td => td.dataset && td.dataset.sumFor == pkjId);
    if (sumCell) { sumCell.textContent = sum.toFixed(2); colorizeSum(sumCell, sum); }
  }

  async function saveMatrixChanges() {
    if (matrixChanges.size === 0) return;
    showLoadingOverlay(true);
    try {
      // Build assignments and unassign per tahapan
      const byTahap = new Map();
      const toUnassign = new Map();
      matrixChanges.forEach((val, key) => {
        const [pkjIdStr, tahapIdStr] = key.split(':');
        const pkjId = parseInt(pkjIdStr), tahapId = parseInt(tahapIdStr);
        const orig = matrixGetOriginalValue(key) || 0;
        if (val > 0) {
          if (!byTahap.has(tahapId)) byTahap.set(tahapId, []);
          byTahap.get(tahapId).push({ pekerjaan_id: pkjId, proporsi: +val });
        } else if (orig > 0) {
          if (!toUnassign.has(tahapId)) toUnassign.set(tahapId, []);
          toUnassign.get(tahapId).push(pkjId);
        }
      });
      // Execute calls tahap by tahap
      for (const [tahapId, assignments] of byTahap.entries()) {
        await apiCall(`${apiBase}${tahapId}/assign/`, {
          method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify({ assignments })
        });
      }
      for (const [tahapId, ids] of toUnassign.entries()) {
        await apiCall(`${apiBase}${tahapId}/unassign/`, {
          method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify({ pekerjaan_ids: ids })
        });
      }
      showToast('Perubahan matrix disimpan', 'success');
      await loadTahapan();
      await loadMatrixData();
      renderMatrix();
    } catch (e) {
      showToast('Gagal menyimpan matrix: ' + e.message, 'error');
    } finally {
      showLoadingOverlay(false);
    }
  }

  // Ensure default Tahap 1 and optionally assign all pekerjaan
  async function ensureDefaultTahap() {
    // Avoid infinite loop if user cancels
    if (!confirm('Belum ada tahapan. Buat "Tahap 1" sekarang?')) return;
    showLoadingOverlay(true);
    try {
      // Create Tahap 1
      await apiCall(apiBase, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({ nama: 'Tahap 1', deskripsi: '', tanggal_mulai: null, tanggal_selesai: null })
      });
      await loadTahapan();
      if (!confirm('Assign semua pekerjaan 100% ke Tahap 1?')) return;
      // Load pekerjaan
      if (allPekerjaan.length === 0) { await loadAllPekerjaan(); }
      const tahap1 = tahapanList.find(t => /tahap\s*1/i.test(t.nama)) || tahapanList[0];
      if (!tahap1) return;
      // Chunk assignments to avoid oversized payloads
      const chunkSize = 150;
      for (let i = 0; i < allPekerjaan.length; i += chunkSize) {
        const slice = allPekerjaan.slice(i, i + chunkSize).map(p => ({ pekerjaan_id: p.id, proporsi: 100.0 }));
        await apiCall(`${apiBase}${tahap1.tahapan_id}/assign/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify({ assignments: slice })
        });
      }
      showToast('Tahap 1 dibuat dan semua pekerjaan di-assign 100%', 'success');
      await loadTahapan();
    } catch (e) {
      showToast('Gagal inisialisasi Tahap 1: ' + e.message, 'error');
    } finally {
      showLoadingOverlay(false);
    }
  }

  // Add smarter behavior to pekerjaan list in assign modal
  function enhancePekerjaanListInteractions(assignedMap) {
    // Tag cards with pekerjaan id and ensure status container exists
    document.querySelectorAll('#pekerjaan-list .card').forEach(card => {
      const cb = card.querySelector('.pekerjaan-checkbox');
      const input = card.querySelector('.proporsi-input');
      if (!cb || !input) return;
      const id = parseInt(cb.value);
      card.setAttribute('data-card-pekerjaan-id', String(id));

      let statusEl = card.querySelector(`#status-${id}`);
      if (!statusEl) {
        statusEl = document.createElement('div');
        statusEl.id = `status-${id}`;
        statusEl.className = 'mt-1 small text-muted';
        input.parentElement.appendChild(statusEl);
      }
    });

    // Advanced change handler: autofill remaining and validate
    document.querySelectorAll('.pekerjaan-checkbox').forEach(cb => {
      cb.addEventListener('change', async (e) => {
        const pkjId = parseInt(e.target.value);
        const input = document.querySelector(`.proporsi-input[data-pekerjaan-id="${pkjId}"]`);
        if (!input) return;
        const statusEl = document.getElementById(`status-${pkjId}`);
        if (!e.target.checked) {
          input.classList.remove('is-invalid');
          statusEl && (statusEl.textContent = '');
          return;
        }
        try {
          const cache = globalAssignCache.get(pkjId) || await apiCall(`/detail_project/api/project/${projectId}/pekerjaan/${pkjId}/assignments/`);
          globalAssignCache.set(pkjId, cache);
          const existing = (assignedMap && assignedMap[pkjId]) || 0;
          let allowed = 100 - (cache.total_assigned - existing);
          if (allowed < 0) allowed = 0; if (allowed > 100) allowed = 100;
          const cur = parseFloat(input.value);
          if (!cur || isNaN(cur) || cur > allowed) {
            input.value = allowed.toFixed(2);
          }
          statusEl && (statusEl.textContent = `Total terpakai: ${cache.total_assigned.toFixed(2)}% • Sisa boleh: ${allowed.toFixed(2)}%`);
          const newTotal = (cache.total_assigned - existing) + parseFloat(input.value || '0');
          if (newTotal > 100.0001) {
            input.classList.add('is-invalid');
            statusEl && (statusEl.textContent = `Melebihi 100% (akan ${newTotal.toFixed(2)}%)`);
          } else {
            input.classList.remove('is-invalid');
          }
        } catch (err) {
          statusEl && (statusEl.textContent = 'Gagal ambil status global');
        }
      });
    });

    // Validate on manual input
    document.querySelectorAll('.proporsi-input').forEach(inp => {
      inp.addEventListener('input', (e) => {
        const pkjId = parseInt(e.target.dataset.pekerjaanId);
        const cache = globalAssignCache.get(pkjId);
        const statusEl = document.getElementById(`status-${pkjId}`);
        if (!cache) return;
        const existing = (assignedMap && assignedMap[pkjId]) || 0;
        const val = parseFloat(e.target.value || '0');
        const newTotal = (cache.total_assigned - existing) + val;
        if (newTotal > 100.0001) {
          e.target.classList.add('is-invalid');
          statusEl && (statusEl.textContent = `Melebihi 100% (akan ${newTotal.toFixed(2)}%)`);
        } else {
          e.target.classList.remove('is-invalid');
          statusEl && (statusEl.textContent = `Total sesudah simpan: ${newTotal.toFixed(2)}%`);
        }
      });
    });
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

  // Setup quick tools in assign modal: filter unassigned and bulk fill remaining
  function setupAssignQuickTools() {
    const toggle = document.getElementById('filter-unassigned-toggle');
    const fillBtn = document.getElementById('btn-fill-remaining');

    if (toggle && !toggle.dataset.bound) {
      toggle.dataset.bound = '1';
      toggle.addEventListener('change', async (e) => {
        if (e.target.checked) {
          // Load unassigned cache
          if (!unassignedCache) {
            try {
              const data = await apiCall(`${apiBase}unassigned/`);
              const set = new Set(data.pekerjaan.map(p => p.pekerjaan_id));
              const map = {};
              data.pekerjaan.forEach(p => { map[p.pekerjaan_id] = p.assigned_proportion; });
              unassignedCache = { set, map };
            } catch (err) {
              showToast('Gagal memuat daftar unassigned', 'error');
              e.target.checked = false;
              return;
            }
          }
          // Apply filter
          document.querySelectorAll('#pekerjaan-list .card').forEach(card => {
            const cb = card.querySelector('.pekerjaan-checkbox');
            if (!cb) return;
            const id = parseInt(cb.value);
            if (!unassignedCache.set.has(id)) {
              card.style.display = 'none';
            }
          });
        } else {
          // Show all; search filter will re-apply below
          document.querySelectorAll('#pekerjaan-list .card').forEach(card => {
            card.style.display = '';
          });
          // Re-apply current search if any
          const search = document.getElementById('search-pekerjaan');
          if (search && search.value) {
            const event = new Event('input');
            search.dispatchEvent(event);
          }
        }
      });
    }

    if (fillBtn && !fillBtn.dataset.bound) {
      fillBtn.dataset.bound = '1';
      fillBtn.addEventListener('click', async () => {
        if (!unassignedCache) {
          try {
            const data = await apiCall(`${apiBase}unassigned/`);
            const set = new Set(data.pekerjaan.map(p => p.pekerjaan_id));
            const map = {};
            data.pekerjaan.forEach(p => { map[p.pekerjaan_id] = p.assigned_proportion; });
            unassignedCache = { set, map };
          } catch (err) {
            unassignedCache = { set: new Set(), map: {} };
          }
        }

        const cards = Array.from(document.querySelectorAll('#pekerjaan-list .card'));
        for (const card of cards) {
          if (card.style.display === 'none') continue; // filtered
          const cb = card.querySelector('.pekerjaan-checkbox');
          const input = card.querySelector('.proporsi-input');
          const id = parseInt(cb.value);
          const statusEl = document.getElementById(`status-${id}`) || (function(){ const el = document.createElement('div'); el.id = `status-${id}`; el.className = 'mt-1 small text-muted'; input.parentElement.appendChild(el); return el; })();

          cb.checked = true;
          input.disabled = false;

          let totalAssigned = unassignedCache.map[id];
          if (typeof totalAssigned !== 'number') {
            try {
              const detail = await apiCall(`/detail_project/api/project/${projectId}/pekerjaan/${id}/assignments/`);
              globalAssignCache.set(id, detail);
              totalAssigned = detail.total_assigned;
            } catch (err) { continue; }
          }
          const existing = currentAssignedMap[id] || 0;
          let allowed = 100 - (totalAssigned - existing);
          if (allowed < 0) allowed = 0; if (allowed > 100) allowed = 100;
          input.value = allowed.toFixed(2);
          statusEl.textContent = `Total terpakai: ${(totalAssigned || 0).toFixed(2)}% • Sisa boleh: ${allowed.toFixed(2)}%`;
        }
        showToast('Nilai diisi otomatis dengan sisa yang tersedia', 'info');
      });
    }
  }

  // ---------------- Offcanvas Panel Tahapan ----------------
  function renderOffcanvasTahapan() {
    const wrap = document.getElementById('offcanvas-tahapan-list');
    if (!wrap) return;
    const html = (tahapanList || []).map(t => `
      <div class="d-flex align-items-center justify-content-between border rounded px-2 py-1">
        <div class="me-2">
          <div class="fw-semibold">${escapeHtml(t.nama)}</div>
          <div class="text-muted small">Pekerjaan: ${t.jumlah_pekerjaan} • Σ: ${t.total_assigned_proportion.toFixed(0)}%</div>
        </div>
        <div class="btn-group btn-group-sm">
          <button type="button" class="btn btn-outline-secondary" data-oc-edit="${t.tahapan_id}"><i class="bi bi-pencil"></i></button>
          <button type="button" class="btn btn-outline-danger" data-oc-delete="${t.tahapan_id}"><i class="bi bi-trash"></i></button>
        </div>
      </div>
    `).join('');
    wrap.innerHTML = html || '<div class="text-muted">Belum ada tahapan</div>';
    // Bind edit/delete
    wrap.querySelectorAll('[data-oc-edit]')?.forEach(btn => btn.addEventListener('click', () => fillOffcanvasForm(parseInt(btn.dataset.ocEdit))));
    wrap.querySelectorAll('[data-oc-delete]')?.forEach(btn => btn.addEventListener('click', async () => {
      await deleteTahapan(parseInt(btn.dataset.ocDelete));
      renderOffcanvasTahapan();
    }));
  }

  function fillOffcanvasForm(tahapanId) {
    const t = tahapanList.find(x => x.tahapan_id === tahapanId);
    if (!t) return;
    document.getElementById('oc-tahapan-id').value = t.tahapan_id;
    document.getElementById('oc-tahapan-nama').value = t.nama || '';
    document.getElementById('oc-tahapan-deskripsi').value = t.deskripsi || '';
    document.getElementById('oc-tahapan-mulai').value = t.tanggal_mulai || '';
    document.getElementById('oc-tahapan-selesai').value = t.tanggal_selesai || '';
  }

  document.getElementById('vpVarOffcanvas')?.addEventListener('shown.bs.offcanvas', () => {
    renderOffcanvasTahapan();
  });

  document.getElementById('oc-btn-reset')?.addEventListener('click', () => {
    document.getElementById('offcanvas-form-tahapan').reset();
    document.getElementById('oc-tahapan-id').value = '';
  });

  document.getElementById('offcanvas-form-tahapan')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('oc-tahapan-id').value;
    const nama = document.getElementById('oc-tahapan-nama').value.trim();
    const deskripsi = document.getElementById('oc-tahapan-deskripsi').value.trim();
    const mulai = document.getElementById('oc-tahapan-mulai').value || null;
    const selesai = document.getElementById('oc-tahapan-selesai').value || null;
    if (!nama) { showToast('Nama tahapan harus diisi', 'error'); return; }
    showLoadingOverlay(true);
    try {
      if (id) {
        await apiCall(`${apiBase}${id}/`, { method: 'PUT', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') }, body: JSON.stringify({ nama, deskripsi, tanggal_mulai: mulai, tanggal_selesai: selesai }) });
        showToast('Tahapan diupdate', 'success');
      } else {
        await apiCall(apiBase, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') }, body: JSON.stringify({ nama, deskripsi, tanggal_mulai: mulai, tanggal_selesai: selesai }) });
        showToast('Tahapan ditambahkan', 'success');
      }
      await loadTahapan();
      renderOffcanvasTahapan();
    } catch (err) {
      showToast('Gagal menyimpan tahapan: ' + err.message, 'error');
    } finally {
      showLoadingOverlay(false);
    }
  });


  // Show tahapan detail in a proper modal (replaces alert UX)
  async function openTahapanDetailModal(tahapanId) {
    try {
      const data = await apiCall(`${apiBase}${tahapanId}/`);
      const tahap = data.tahapan;
      const $body = document.getElementById('tahapan-detail-body');

      const rows = (tahap.pekerjaan || []).map(p => `
        <tr>
          <td class="text-nowrap mono">${escapeHtml(p.kode || '')}</td>
          <td>${escapeHtml(p.uraian || '')}</td>
          <td class="text-end">${(p.proporsi ?? 0).toFixed(2)}%</td>
        </tr>
      `).join('');

      $body.innerHTML = `
        <div class="mb-2">
          <strong>${escapeHtml(tahap.nama)}</strong>
          <div class="small text-muted">Pekerjaan: ${tahap.jumlah_pekerjaan}</div>
        </div>
        <div class="table-responsive">
          <table class="table table-sm align-middle">
            <thead class="table-light">
              <tr>
                <th style=\"width: 160px;\" class=\"text-nowrap\">Kode</th>
                <th>Uraian</th>
                <th style=\"width: 120px;\" class=\"text-end\">Proporsi</th>
              </tr>
            </thead>
            <tbody>
              ${rows || '<tr><td colspan="3" class="text-muted">Belum ada pekerjaan</td></tr>'}
            </tbody>
          </table>
        </div>
      `;

      modalTahapanDetail.show();
    } catch (error) {
      showToast('Gagal memuat detail: ' + error.message, 'error');
    }
  }

  // =========================================================================
  // INITIALIZATION
  // =========================================================================

  loadTahapan();
  // Keep Matrix Mode OFF by default to avoid load errors if API not ready

})();

