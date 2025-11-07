/**
 * Mass Edit Toggle for Project Table
 * Allows inline editing of all project fields directly in the table
 *
 * Features:
 * - Toggle edit mode for entire table
 * - Show ALL 20 editable project fields
 * - Yellow highlighting for edited fields
 * - Red highlighting for required field errors
 * - Confirmation dialog before saving
 * - Integrates with existing text wrap and column resize features
 */

(function() {
  'use strict';

  // ============================================================================
  // STATE MANAGEMENT
  // ============================================================================

  let isEditMode = false;
  let originalData = new Map(); // Stores original values for rollback
  let editedCells = new Set(); // Tracks which cells have been edited
  let errorCells = new Set(); // Tracks cells with validation errors

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  /**
   * Convert snake_case to camelCase for dataset access
   * Example: sumber_dana -> sumberDana
   */
  function snakeToCamel(str) {
    return str.replace(/_([a-z])/g, (g) => g[1].toUpperCase());
  }

  // Required fields (from Project model)
  const REQUIRED_FIELDS = [
    'nama',
    'sumber_dana',
    'lokasi_project',
    'nama_client',
    'anggaran_owner',
    'tanggal_mulai'
  ];

  // All 20 editable fields
  const ALL_FIELDS = [
    // 6 Required
    { name: 'nama', label: 'Nama Project', type: 'text', required: true },
    { name: 'sumber_dana', label: 'Sumber Dana', type: 'text', required: true },
    { name: 'lokasi_project', label: 'Lokasi Project', type: 'text', required: true },
    { name: 'nama_client', label: 'Nama Client', type: 'text', required: true },
    { name: 'anggaran_owner', label: 'Anggaran Owner', type: 'number', required: true },
    { name: 'tanggal_mulai', label: 'Tanggal Mulai', type: 'date', required: true },

    // 14 Optional
    { name: 'tanggal_selesai', label: 'Tanggal Selesai', type: 'date', required: false },
    { name: 'durasi_hari', label: 'Durasi (hari)', type: 'number', required: false },
    { name: 'ket_project1', label: 'Ket Project 1', type: 'text', required: false },
    { name: 'ket_project2', label: 'Ket Project 2', type: 'text', required: false },
    { name: 'jabatan_client', label: 'Jabatan Client', type: 'text', required: false },
    { name: 'instansi_client', label: 'Instansi Client', type: 'text', required: false },
    { name: 'nama_kontraktor', label: 'Nama Kontraktor', type: 'text', required: false },
    { name: 'instansi_kontraktor', label: 'Instansi Kontraktor', type: 'text', required: false },
    { name: 'nama_konsultan_perencana', label: 'Nama Konsultan Perencana', type: 'text', required: false },
    { name: 'instansi_konsultan_perencana', label: 'Instansi Konsultan Perencana', type: 'text', required: false },
    { name: 'nama_konsultan_pengawas', label: 'Nama Konsultan Pengawas', type: 'text', required: false },
    { name: 'instansi_konsultan_pengawas', label: 'Instansi Konsultan Pengawas', type: 'text', required: false },
    { name: 'deskripsi', label: 'Deskripsi', type: 'textarea', required: false },
    { name: 'kategori', label: 'Kategori', type: 'text', required: false }
  ];

  // ============================================================================
  // INITIALIZATION
  // ============================================================================

  document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 Initializing Mass Edit Toggle...');

    const toggleBtn = document.getElementById('massEditToggleBtn');
    const saveBtn = document.getElementById('massEditSaveAllBtn');
    const cancelBtn = document.getElementById('massEditCancelBtn');

    if (!toggleBtn) {
      console.warn('Mass Edit Toggle button not found');
      return;
    }

    // Toggle Edit Mode
    toggleBtn.addEventListener('click', function() {
      if (!isEditMode) {
        enterEditMode();
      } else {
        exitEditMode(false); // false = don't save changes
      }
    });

    // Save All Changes
    if (saveBtn) {
      saveBtn.addEventListener('click', function() {
        saveAllChanges();
      });
    }

    // Cancel Edit Mode
    if (cancelBtn) {
      cancelBtn.addEventListener('click', function() {
        if (confirm('Yakin ingin membatalkan semua perubahan?')) {
          exitEditMode(false);
        }
      });
    }

    console.log('✅ Mass Edit Toggle initialized');
  });

  // ============================================================================
  // ENTER EDIT MODE
  // ============================================================================

  function enterEditMode() {
    console.log('📝 Entering edit mode...');

    const table = document.querySelector('.dashboard-project-table');
    const bulkActionsBar = document.getElementById('bulkActionsBar');
    const editActionBar = document.getElementById('massEditActionBar');

    if (!table) {
      console.error('Project table not found');
      return;
    }

    // Clear previous state
    originalData.clear();
    editedCells.clear();
    errorCells.clear();

    // Show edit action bar, hide bulk actions
    if (editActionBar) editActionBar.style.display = 'block';
    if (bulkActionsBar) bulkActionsBar.style.display = 'none';

    // Add edit mode class to table
    table.classList.add('mass-edit-mode');

    // Disable all other UI interactions
    disableUIInteractions();

    // Rebuild table with ALL fields
    rebuildTableForEdit(table);

    // Mark as edit mode
    isEditMode = true;

    // Show success message
    if (window.showToast) {
      window.showToast('Mode edit aktif. Edit langsung di tabel, lalu klik Simpan Semua.', 'info', 4000);
    }
  }

  // ============================================================================
  // DISABLE/ENABLE UI INTERACTIONS
  // ============================================================================

  function disableUIInteractions() {
    // Disable FAB menu
    const fabMainBtn = document.getElementById('fabMainBtn');
    const fabMenu = document.getElementById('fabMenu');
    if (fabMainBtn) {
      fabMainBtn.disabled = true;
      fabMainBtn.style.pointerEvents = 'none';
      fabMainBtn.style.opacity = '0.5';
    }
    if (fabMenu) {
      fabMenu.style.display = 'none';
    }

    // Disable filter panel
    const filterPanel = document.getElementById('filterPanel');
    if (filterPanel) {
      const filterInputs = filterPanel.querySelectorAll('input, select, button');
      filterInputs.forEach(input => {
        input.disabled = true;
        input.style.opacity = '0.5';
      });
    }

    // Disable pagination
    const pagination = document.querySelector('.pagination');
    if (pagination) {
      const paginationLinks = pagination.querySelectorAll('a, button');
      paginationLinks.forEach(link => {
        link.style.pointerEvents = 'none';
        link.style.opacity = '0.5';
      });
    }

    // Disable all action buttons in table
    const actionButtons = document.querySelectorAll('.dashboard-project-table .btn');
    actionButtons.forEach(btn => {
      btn.disabled = true;
      btn.style.pointerEvents = 'none';
      btn.style.opacity = '0.5';
    });

    // Add overlay to body to prevent clicks
    const overlay = document.createElement('div');
    overlay.id = 'massEditOverlay';
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.05);
      z-index: var(--z-sticky, 1010);
      pointer-events: none;
    `;
    document.body.appendChild(overlay);
  }

  function enableUIInteractions() {
    // Enable FAB menu
    const fabMainBtn = document.getElementById('fabMainBtn');
    if (fabMainBtn) {
      fabMainBtn.disabled = false;
      fabMainBtn.style.pointerEvents = '';
      fabMainBtn.style.opacity = '';
    }

    // Enable filter panel
    const filterPanel = document.getElementById('filterPanel');
    if (filterPanel) {
      const filterInputs = filterPanel.querySelectorAll('input, select, button');
      filterInputs.forEach(input => {
        input.disabled = false;
        input.style.opacity = '';
      });
    }

    // Enable pagination
    const pagination = document.querySelector('.pagination');
    if (pagination) {
      const paginationLinks = pagination.querySelectorAll('a, button');
      paginationLinks.forEach(link => {
        link.style.pointerEvents = '';
        link.style.opacity = '';
      });
    }

    // Enable all action buttons in table
    const actionButtons = document.querySelectorAll('.dashboard-project-table .btn');
    actionButtons.forEach(btn => {
      btn.disabled = false;
      btn.style.pointerEvents = '';
      btn.style.opacity = '';
    });

    // Remove overlay
    const overlay = document.getElementById('massEditOverlay');
    if (overlay) {
      overlay.remove();
    }
  }

  // ============================================================================
  // REBUILD TABLE FOR EDIT
  // ============================================================================

  function rebuildTableForEdit(table) {
    const tbody = table.querySelector('tbody');
    const thead = table.querySelector('thead');

    if (!tbody || !thead) return;

    const rows = Array.from(tbody.querySelectorAll('tr'));

    // Rebuild header with ALL fields
    const headerRow = thead.querySelector('tr');
    headerRow.innerHTML = '';

    // Checkbox column
    const checkboxTh = document.createElement('th');
    checkboxTh.className = 'text-center';
    checkboxTh.style.width = '40px';
    checkboxTh.innerHTML = '<input type="checkbox" id="selectAll" class="form-check-input" title="Pilih semua">';
    headerRow.appendChild(checkboxTh);

    // Add all field headers
    ALL_FIELDS.forEach(field => {
      const th = document.createElement('th');
      th.textContent = field.label;
      th.setAttribute('data-field', field.name);

      if (field.required) {
        th.classList.add('field-required');
        th.innerHTML += ' <span class="text-danger">*</span>';
      }

      headerRow.appendChild(th);
    });

    // Action column
    const actionTh = document.createElement('th');
    actionTh.className = 'text-center';
    actionTh.textContent = 'Aksi';
    headerRow.appendChild(actionTh);

    // Rebuild each row
    rows.forEach((row, rowIndex) => {
      const projectId = row.querySelector('.project-checkbox')?.value;
      if (!projectId) return;

      // Store original data from data attributes
      const originalRowData = {};
      ALL_FIELDS.forEach(field => {
        // Convert field name to camelCase for dataset access
        const camelCaseName = snakeToCamel(field.name);
        // Use !== undefined to preserve '0' values
        const value = row.dataset[camelCaseName] !== undefined ? row.dataset[camelCaseName] : '';
        originalRowData[field.name] = value;
      });
      originalData.set(projectId, originalRowData);

      // Rebuild row with editable inputs
      const checkboxCell = row.cells[0]; // Keep checkbox

      row.innerHTML = '';
      row.appendChild(checkboxCell);

      // Add editable cells for each field
      ALL_FIELDS.forEach(field => {
        const td = document.createElement('td');
        td.setAttribute('data-field', field.name);
        td.setAttribute('data-project-id', projectId);

        const input = createEditableInput(field, originalRowData[field.name], projectId);
        td.appendChild(input);

        row.appendChild(td);
      });

      // Add action column (keep it simple in edit mode)
      const actionTd = document.createElement('td');
      actionTd.className = 'text-center';
      actionTd.innerHTML = '<small class="text-muted">Edit mode</small>';
      row.appendChild(actionTd);
    });

    // Re-attach select all checkbox listener
    const selectAllCheckbox = document.getElementById('selectAll');
    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener('change', function() {
        const checkboxes = tbody.querySelectorAll('.project-checkbox');
        checkboxes.forEach(cb => cb.checked = this.checked);
      });
    }
  }

  // ============================================================================
  // CREATE EDITABLE INPUT
  // ============================================================================

  function createEditableInput(field, value, projectId) {
    let input;

    if (field.type === 'textarea') {
      input = document.createElement('textarea');
      input.className = 'form-control form-control-sm';
      input.rows = 2;
    } else {
      input = document.createElement('input');
      input.type = field.type;
      input.className = 'form-control form-control-sm';

      if (field.type === 'number') {
        input.step = field.name === 'anggaran_owner' ? '0.01' : '1';
      }
    }

    input.value = value || '';
    input.setAttribute('data-field', field.name);
    input.setAttribute('data-project-id', projectId);
    input.setAttribute('data-original-value', value || '');

    if (field.required) {
      input.required = true;
      input.classList.add('required-field');
    }

    // Track changes
    input.addEventListener('input', function() {
      handleFieldChange(this, field);
    });

    // Validate on blur
    input.addEventListener('blur', function() {
      validateField(this, field);
    });

    return input;
  }

  // ============================================================================
  // HANDLE FIELD CHANGE
  // ============================================================================

  function handleFieldChange(input, field) {
    const projectId = input.getAttribute('data-project-id');
    const fieldName = field.name;
    const originalValue = input.getAttribute('data-original-value');
    const currentValue = input.value;
    const cellKey = `${projectId}-${fieldName}`;

    // Track if changed
    if (currentValue !== originalValue) {
      editedCells.add(cellKey);
      input.parentElement.classList.add('cell-edited');
    } else {
      editedCells.delete(cellKey);
      input.parentElement.classList.remove('cell-edited');
    }

    // Validate required fields
    if (field.required) {
      validateField(input, field);
    }
  }

  // ============================================================================
  // VALIDATE FIELD
  // ============================================================================

  function validateField(input, field) {
    const projectId = input.getAttribute('data-project-id');
    const fieldName = field.name;
    const cellKey = `${projectId}-${fieldName}`;
    const value = input.value.trim();

    let hasError = false;

    // Check required fields
    if (field.required && !value) {
      hasError = true;
    }

    // Type-specific validation
    if (value) {
      if (field.type === 'number') {
        const num = parseFloat(value);
        if (isNaN(num) || num < 0) {
          hasError = true;
        }
      }

      if (field.type === 'date') {
        const date = new Date(value);
        if (isNaN(date.getTime())) {
          hasError = true;
        }
      }
    }

    // Update error state
    if (hasError) {
      errorCells.add(cellKey);
      input.parentElement.classList.add('cell-error');
      input.classList.add('is-invalid');
    } else {
      errorCells.delete(cellKey);
      input.parentElement.classList.remove('cell-error');
      input.classList.remove('is-invalid');
    }

    return !hasError;
  }

  // ============================================================================
  // SAVE ALL CHANGES
  // ============================================================================

  function saveAllChanges() {
    console.log('💾 Saving all changes...');

    // Validate all fields first
    const table = document.querySelector('.dashboard-project-table');
    const allInputs = table.querySelectorAll('input, textarea');
    let hasErrors = false;

    allInputs.forEach(input => {
      const fieldName = input.getAttribute('data-field');
      const field = ALL_FIELDS.find(f => f.name === fieldName);
      if (field && !validateField(input, field)) {
        hasErrors = true;
      }
    });

    if (hasErrors) {
      alert('Ada field wajib yang kosong atau tidak valid (ditandai merah). Mohon perbaiki terlebih dahulu.');
      return;
    }

    if (editedCells.size === 0) {
      alert('Tidak ada perubahan yang perlu disimpan.');
      return;
    }

    // Confirm save
    const editedCount = new Set(Array.from(editedCells).map(key => key.split('-')[0])).size;
    if (!confirm(`Simpan perubahan pada ${editedCount} project?`)) {
      return;
    }

    // Collect all changes
    const changes = [];
    const projectIds = new Set();

    allInputs.forEach(input => {
      const projectId = input.getAttribute('data-project-id');
      const fieldName = input.getAttribute('data-field');
      const cellKey = `${projectId}-${fieldName}`;

      if (editedCells.has(cellKey)) {
        projectIds.add(projectId);
      }
    });

    // For each modified project, collect all its field values
    projectIds.forEach(projectId => {
      const projectData = { id: projectId };

      ALL_FIELDS.forEach(field => {
        const input = table.querySelector(`[data-project-id="${projectId}"][data-field="${field.name}"]`);
        if (input) {
          projectData[field.name] = input.value;
        }
      });

      changes.push(projectData);
    });

    // Send to server
    sendBulkUpdate(changes);
  }

  // ============================================================================
  // SEND BULK UPDATE TO SERVER
  // ============================================================================

  function sendBulkUpdate(changes) {
    const saveBtn = document.getElementById('massEditSaveAllBtn');
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Menyimpan...';
    }

    // Get CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                     document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    fetch('/dashboard/mass-edit-bulk/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify({ changes: changes })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        if (window.showToast) {
          window.showToast(`${data.updated_count} project berhasil diupdate`, 'success');
        }

        // Reload page after short delay
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        alert('Error: ' + (data.message || 'Terjadi kesalahan saat menyimpan'));
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = '<i class="fas fa-save"></i> Simpan Semua';
        }
      }
    })
    .catch(error => {
      console.error('Error saving changes:', error);
      alert('Terjadi kesalahan saat menyimpan perubahan.');
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fas fa-save"></i> Simpan Semua';
      }
    });
  }

  // ============================================================================
  // EXIT EDIT MODE
  // ============================================================================

  function exitEditMode(save = false) {
    if (!save && editedCells.size > 0) {
      if (!confirm('Ada perubahan yang belum disimpan. Yakin ingin keluar dari mode edit?')) {
        return;
      }
    }

    console.log('🚪 Exiting edit mode...');

    isEditMode = false;

    // Reload page to restore original view
    window.location.reload();
  }

})();