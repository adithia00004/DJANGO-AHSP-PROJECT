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
  let draftValues = new Map(); // Keeps edits when optional columns are hidden
  let editedCells = new Set(); // Tracks which cells have been edited
  let errorCells = new Set(); // Tracks cells with validation errors

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  function toast(message, type = 'info', duration) {
    if (window.DP?.toast?.show) {
      window.DP.toast.show({ message, type, duration });
      return;
    }
    if (window.showToast) {
      window.showToast(message, type, duration || 3000);
    }
  }

  function confirmAction(options) {
    if (window.DPConfirm) {
      return window.DPConfirm(options);
    }
    return Promise.resolve(false);
  }

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

  // All editable fields. Keep the default grid focused; users can opt into
  // additional columns from the action bar.
  const ALL_FIELDS = [
    // 6 Required
    { name: 'nama', label: 'Nama Project', type: 'text', required: true },
    { name: 'sumber_dana', label: 'Sumber Dana', type: 'text', required: true },
    { name: 'lokasi_project', label: 'Lokasi Project', type: 'text', required: true },
    { name: 'nama_client', label: 'Nama Client', type: 'text', required: true },
    { name: 'anggaran_owner', label: 'Anggaran Owner', type: 'text', required: true, isNumeric: true, allowDecimal: true },
    { name: 'tanggal_mulai', label: 'Tanggal Mulai', type: 'date', required: true },

    // 14 Optional
    { name: 'tanggal_selesai', label: 'Tanggal Selesai', type: 'date', required: false },
    { name: 'durasi_hari', label: 'Durasi (hari)', type: 'text', required: false, isNumeric: true, allowDecimal: false },
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
  const DEFAULT_FIELD_NAMES = [
    'nama',
    'sumber_dana',
    'lokasi_project',
    'nama_client',
    'anggaran_owner',
    'tanggal_mulai',
    'tanggal_selesai'
  ];
  let visibleFieldNames = new Set(DEFAULT_FIELD_NAMES);
  let selectedProjectIds = new Set();
  const MULTILINE_FIELD_NAMES = new Set([
    'nama',
    'sumber_dana',
    'lokasi_project',
    'nama_client',
    'ket_project1',
    'ket_project2',
    'jabatan_client',
    'instansi_client',
    'nama_kontraktor',
    'instansi_kontraktor',
    'nama_konsultan_perencana',
    'instansi_konsultan_perencana',
    'nama_konsultan_pengawas',
    'instansi_konsultan_pengawas',
    'deskripsi',
    'kategori'
  ]);

  // ============================================================================
  // INITIALIZATION
  // ============================================================================

  document.addEventListener('DOMContentLoaded', function() {

    const toggleBtn = document.getElementById('massEditToggleBtn');
    const saveBtn = document.getElementById('massEditSaveAllBtn');
    const cancelBtn = document.getElementById('massEditCancelBtn');
    const bulkModeToggleBtn = document.getElementById('bulkModeToggleBtn');

    if (!toggleBtn) {
      console.warn('Mass Edit Toggle button not found');
      return;
    }

    function updateMobileAvailability() {
      const unavailable = window.innerWidth <= 992;
      if (!bulkModeToggleBtn || isEditMode) return;
      bulkModeToggleBtn.disabled = unavailable;
      bulkModeToggleBtn.title = unavailable
        ? 'Edit massal tersedia pada layar desktop (lebih dari 992px)'
        : 'Pilih project untuk diedit atau dihapus';
    }
    updateMobileAvailability();
    window.addEventListener('resize', updateMobileAvailability);

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
      cancelBtn.addEventListener('click', async function() {
        const confirmed = await confirmAction({
          title: 'Batalkan Perubahan',
          message: 'Yakin ingin membatalkan semua perubahan?',
          confirmText: 'Batalkan',
          confirmClass: 'btn-danger'
        });
        if (confirmed) {
          exitEditMode(false);
        }
      });
    }

    // Auto-cancel when clicking any link that navigates away
    document.addEventListener('click', async function(e) {
      if (isEditMode) {
        const target = e.target.closest('a');
        if (target && target.href && !target.href.includes('#')) {
          // Check if it's not a same-page link
          const currentUrl = window.location.href.split('#')[0];
          const targetUrl = target.href.split('#')[0];

          if (targetUrl !== currentUrl) {
            if (editedCells.size > 0) {
              e.preventDefault();
              const confirmed = await confirmAction({
                title: 'Perubahan Belum Disimpan',
                message: 'Ada perubahan yang belum disimpan. Yakin ingin meninggalkan halaman?',
                confirmText: 'Tinggalkan',
                confirmClass: 'btn-warning'
              });
              if (!confirmed) {
                return;
              }
            }
            // Auto-cancel mass edit mode before navigation
            isEditMode = false;
            enableUIInteractions();
            window.location.href = target.href;
          }
        }
      }
    });

  });

  // ============================================================================
  // ENTER EDIT MODE
  // ============================================================================

  function enterEditMode() {

    const table = document.querySelector('.dashboard-project-table');
    const bulkActionsBar = document.getElementById('bulkActionsBar');
    const editActionBar = document.getElementById('massEditActionBar');

    if (!table) {
      console.error('Project table not found');
      return;
    }

    if (window.innerWidth <= 992) {
      toast('Edit massal tersedia pada layar desktop.', 'warning', 4000);
      return;
    }

    selectedProjectIds = new Set(
      Array.from(table.querySelectorAll('tbody .project-checkbox:checked'))
        .map(checkbox => checkbox.value)
    );
    if (selectedProjectIds.size === 0) {
      toast('Pilih minimal satu project untuk diedit.', 'warning', 4000);
      return;
    }

    // Clear previous state
    originalData.clear();
    draftValues.clear();
    editedCells.clear();
    errorCells.clear();
    visibleFieldNames = new Set(DEFAULT_FIELD_NAMES);

    // Show edit action bar, hide bulk actions
    if (editActionBar) editActionBar.style.display = 'block';
    if (bulkActionsBar) bulkActionsBar.style.display = 'none';

    // Add edit mode class to table
    table.classList.add('mass-edit-mode');

    // Disable all other UI interactions
    disableUIInteractions();

    buildColumnOptions();
    updateEditSummary();

    // Rebuild table with selected projects and focused fields.
    rebuildTableForEdit(table);

    // Mark as edit mode
    isEditMode = true;

    // Show success message
    toast(`${selectedProjectIds.size} project siap diedit.`, 'info', 4000);
  }

  function getVisibleFields() {
    return ALL_FIELDS.filter(field => visibleFieldNames.has(field.name));
  }

  function buildColumnOptions() {
    const container = document.getElementById('massEditColumnOptions');
    if (!container) return;

    container.innerHTML = ALL_FIELDS
      .filter(field => !DEFAULT_FIELD_NAMES.includes(field.name))
      .map(field => `
        <label class="form-check mb-2">
          <input class="form-check-input mass-edit-column-option" type="checkbox"
            value="${field.name}" ${visibleFieldNames.has(field.name) ? 'checked' : ''}>
          <span class="form-check-label">${field.label}</span>
        </label>
      `).join('');

    container.querySelectorAll('.mass-edit-column-option').forEach(checkbox => {
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) {
          visibleFieldNames.add(checkbox.value);
        } else {
          visibleFieldNames.delete(checkbox.value);
        }
        rebuildTableForEdit(document.querySelector('.dashboard-project-table'), true);
      });
    });
  }

  function updateEditSummary() {
    const projectCount = document.getElementById('massEditProjectCount');
    const changeCount = document.getElementById('massEditChangeCount');
    if (projectCount) projectCount.textContent = `${selectedProjectIds.size} project`;
    if (changeCount) changeCount.textContent = `${editedCells.size} perubahan`;
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

  function rebuildTableForEdit(table, preserveCurrentValues = false) {
    const tbody = table.querySelector('tbody');
    const thead = table.querySelector('thead');

    if (!tbody || !thead) return;

    const rows = Array.from(tbody.querySelectorAll('tr'));
    const currentValues = new Map();

    if (preserveCurrentValues) {
      table.querySelectorAll('input[data-project-id][data-field], textarea[data-project-id][data-field]')
        .forEach(input => {
          const key = `${input.dataset.projectId}-${input.dataset.field}`;
          currentValues.set(key, input.value);
          draftValues.set(key, input.value);
        });
    }

    rows.forEach(row => {
      const projectId = row.dataset.projectId || row.querySelector('.project-checkbox')?.value;
      row.hidden = !selectedProjectIds.has(String(projectId));
    });

    // Rebuild header with ALL fields
    const headerRow = thead.querySelector('tr');
    headerRow.innerHTML = '';

    const projectTh = document.createElement('th');
    projectTh.className = 'mass-edit-project-name';
    projectTh.textContent = 'Project';
    headerRow.appendChild(projectTh);

    getVisibleFields().forEach(field => {
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
      const projectId = String(row.dataset.projectId || row.querySelector('.project-checkbox')?.value || '');
      if (!projectId || !selectedProjectIds.has(projectId)) return;

      // Store original data from data attributes
      const originalRowData = {};
      ALL_FIELDS.forEach(field => {
        // Convert field name to camelCase for dataset access
        const camelCaseName = snakeToCamel(field.name);
        // Use !== undefined to preserve '0' values
        const value = row.dataset[camelCaseName] !== undefined ? row.dataset[camelCaseName] : '';
        originalRowData[field.name] = value;
      });
      if (!originalData.has(projectId)) originalData.set(projectId, originalRowData);

      row.innerHTML = '';
      const projectCell = document.createElement('td');
      projectCell.className = 'mass-edit-project-name fw-semibold';
      projectCell.textContent = originalData.get(projectId).nama || `Project ${projectId}`;
      row.appendChild(projectCell);

      getVisibleFields().forEach(field => {
        const td = document.createElement('td');
        td.setAttribute('data-field', field.name);
        td.setAttribute('data-project-id', projectId);

        const key = `${projectId}-${field.name}`;
        const value = draftValues.has(key)
          ? draftValues.get(key)
          : currentValues.has(key)
            ? currentValues.get(key)
          : originalData.get(projectId)[field.name];
        const input = createEditableInput(
          field,
          value,
          projectId,
          originalData.get(projectId)[field.name]
        );
        td.appendChild(input);

        row.appendChild(td);
      });

      // Add action column (keep it simple in edit mode)
      const actionTd = document.createElement('td');
      actionTd.className = 'text-center';
      actionTd.innerHTML = '<small class="text-muted">Edit mode</small>';
      row.appendChild(actionTd);
    });

  }

  // ============================================================================
  // CREATE EDITABLE INPUT
  // ============================================================================

  function createEditableInput(field, value, projectId, originalValue = value) {
    let input;

    if (field.type === 'textarea' || MULTILINE_FIELD_NAMES.has(field.name)) {
      input = document.createElement('textarea');
      input.className = 'form-control form-control-sm mass-edit-multiline';
      input.rows = field.type === 'textarea' ? 3 : 1;
    } else {
      input = document.createElement('input');
      input.type = field.type;
      input.className = 'form-control form-control-sm';

      // Special handling for numeric fields (using type="text" for better control)
      if (field.isNumeric) {
        // Use appropriate inputmode for mobile keyboards
        input.inputMode = field.allowDecimal ? 'decimal' : 'numeric';

        // Add pattern for validation
        if (field.allowDecimal) {
          input.pattern = '^[0-9]+(\\.[0-9]{1,2})?$'; // Allow up to 2 decimal places
          input.placeholder = 'Contoh: 1000000.50';
        } else {
          input.pattern = '^[0-9]+$'; // Only integers
          input.placeholder = 'Contoh: 365';
        }

        // Prevent non-numeric input on keypress
        input.addEventListener('keypress', function(e) {
          const char = e.key;
          const currentValue = this.value;

          // Allow: backspace, delete, tab, escape, enter
          if ([8, 9, 27, 13].includes(e.keyCode)) {
            return;
          }

          // Allow decimal point only for decimal fields and only once
          if (field.allowDecimal && char === '.') {
            if (currentValue.includes('.')) {
              e.preventDefault();
              return;
            }
            return;
          }

          // Only allow digits
          if (!/^\d$/.test(char)) {
            e.preventDefault();
          }
        });

        // Format on blur for better display
        input.addEventListener('blur', function() {
          let val = this.value.trim();
          if (val && field.allowDecimal) {
            // Try to parse as float and format
            const num = parseFloat(val);
            if (!isNaN(num)) {
              this.value = num.toString();
            }
          }
        });
      }
    }

    input.value = value || '';
    input.title = value || '';
    input.setAttribute('data-field', field.name);
    input.setAttribute('data-project-id', projectId);
    input.setAttribute('data-original-value', originalValue || '');

    if (field.required) {
      input.required = true;
      input.classList.add('required-field');
    }

    // Track changes
    input.addEventListener('input', function() {
      handleFieldChange(this, field);
      this.title = this.value;
      if (this.classList.contains('mass-edit-multiline')) {
        autoSizeMultiline(this);
      }
    });

    // Validate on blur (after numeric blur handler)
    input.addEventListener('blur', function() {
      validateField(this, field);
    });

    if (input.classList.contains('mass-edit-multiline')) {
      input.addEventListener('focus', function() {
        this.classList.add('is-expanded');
        autoSizeMultiline(this);
      });
      input.addEventListener('blur', function() {
        this.classList.remove('is-expanded');
        this.style.height = '';
      });
    }

    return input;
  }

  function autoSizeMultiline(input) {
    const maxHeight = Math.min(window.innerHeight * 0.35, 180);
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, maxHeight)}px`;
    input.style.overflowY = input.scrollHeight > maxHeight ? 'auto' : 'hidden';
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
    draftValues.set(cellKey, currentValue);

    // Track if changed
    if (currentValue !== originalValue) {
      editedCells.add(cellKey);
      input.parentElement.classList.add('cell-edited');
    } else {
      editedCells.delete(cellKey);
      input.parentElement.classList.remove('cell-edited');
    }
    updateEditSummary();

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
      // Numeric field validation (using type="text" but isNumeric flag)
      if (field.isNumeric) {
        const num = parseFloat(value);
        if (isNaN(num) || num < 0) {
          hasError = true;
        }

        // Check decimal places for decimal fields
        if (!hasError && field.allowDecimal) {
          const parts = value.split('.');
          if (parts.length > 1 && parts[1].length > 2) {
            hasError = true; // Max 2 decimal places
          }
        }

        // Check pattern for integer fields
        if (!hasError && !field.allowDecimal) {
          if (!/^[0-9]+$/.test(value)) {
            hasError = true;
          }
        }
      }

      // Date validation
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

  async function saveAllChanges() {

    // Validate visible fields first. Hidden fields retain their original values.
    const table = document.querySelector('.dashboard-project-table');
    const allInputs = table.querySelectorAll('input, textarea, select');
    let hasErrors = false;

    allInputs.forEach(input => {
      const fieldName = input.getAttribute('data-field');
      const field = ALL_FIELDS.find(f => f.name === fieldName);
      if (field && !validateField(input, field)) {
        hasErrors = true;
      }
    });

    if (hasErrors) {
      toast('Ada field wajib yang kosong atau tidak valid (ditandai merah).', 'warning', 4000);
      return;
    }

    if (editedCells.size === 0) {
      toast('Tidak ada perubahan yang perlu disimpan.', 'info', 3000);
      return;
    }

    // Confirm save
    const editedCount = new Set(Array.from(editedCells).map(key => key.split('-')[0])).size;
    const confirmed = await confirmAction({
      title: 'Simpan Perubahan',
      message: `Simpan perubahan pada ${editedCount} project?`,
      confirmText: 'Simpan',
      confirmClass: 'btn-success'
    });
    if (!confirmed) {
      return;
    }

    // Collect all changes
    const changes = [];
    const projectIds = new Set();

    // First, identify which projects have changes
    allInputs.forEach(input => {
      const projectId = input.getAttribute('data-project-id');
      const fieldName = input.getAttribute('data-field');
      const cellKey = `${projectId}-${fieldName}`;

      if (editedCells.has(cellKey)) {
        projectIds.add(projectId);
      }
    });


    // For each modified project, send every editable field. Empty optional
    // values are intentional and must reach the backend to clear stored data.
    projectIds.forEach(projectId => {
      const projectData = { id: projectId };

      ALL_FIELDS.forEach(field => {
        // Find INPUT or TEXTAREA element specifically (not TD which also has data attributes)
        const input = table.querySelector(`input[data-project-id="${projectId}"][data-field="${field.name}"], textarea[data-project-id="${projectId}"][data-field="${field.name}"]`);

        const key = `${projectId}-${field.name}`;
        projectData[field.name] = draftValues.has(key)
          ? draftValues.get(key)
          : input
            ? input.value
            : (originalData.get(projectId)?.[field.name] || '');
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


    const requestBody = { changes: changes };

    fetch('/dashboard/mass-edit-bulk/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify(requestBody)
    })
    .then(async response => {
      const data = await response.json().catch(() => null);
      if (!response.ok && !data) {
        throw new Error(`HTTP ${response.status}`);
      }
      return data || {
        success: false,
        message: `Permintaan gagal dengan status HTTP ${response.status}.`
      };
    })
    .then(data => {

      if (data.success) {

        if (window.showToast) {
          window.showToast(`${data.updated_count} project berhasil diupdate`, 'success');
        }

        // Clear editedCells to prevent beforeunload alert
        editedCells.clear();
        isEditMode = false;


        // Reload page after short delay
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        console.error('❌ Failed:', data.message);
        toast(data.message || 'Terjadi kesalahan saat menyimpan.', 'error', 5000);
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.innerHTML = '<i class="fas fa-save"></i> Simpan';
        }
        applyServerErrors(data.errors || {});
      }
    })
    .catch(error => {
      console.error('❌ Error saving changes:', error);
      console.error('Error stack:', error.stack);
      toast(`Terjadi kesalahan saat menyimpan perubahan: ${error.message}`, 'error', 5000);
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fas fa-save"></i> Simpan';
      }
    });
  }

  function applyServerErrors(errors) {
    const table = document.querySelector('.dashboard-project-table');
    const hiddenErrorFields = new Set();
    Object.values(errors).forEach(fields => {
      Object.keys(fields || {}).forEach(fieldName => {
        if (
          ALL_FIELDS.some(field => field.name === fieldName) &&
          !visibleFieldNames.has(fieldName)
        ) {
          hiddenErrorFields.add(fieldName);
        }
      });
    });
    if (hiddenErrorFields.size > 0) {
      hiddenErrorFields.forEach(fieldName => visibleFieldNames.add(fieldName));
      buildColumnOptions();
      rebuildTableForEdit(table, true);
    }

    Object.entries(errors).forEach(([projectId, fields]) => {
      const row = table?.querySelector(`tr[data-project-id="${projectId}"]`);
      row?.classList.add('mass-edit-row-error');

      Object.entries(fields || {}).forEach(([fieldName, messages]) => {
        const input = table?.querySelector(
          `input[data-project-id="${projectId}"][data-field="${fieldName}"], ` +
          `textarea[data-project-id="${projectId}"][data-field="${fieldName}"]`
        );
        if (!input) return;
        input.classList.add('is-invalid');
        input.title = Array.isArray(messages) ? messages.join(' ') : String(messages);
        input.parentElement?.classList.add('cell-error');
      });
    });
    toast('Sebagian data tidak valid. Periksa field yang ditandai merah.', 'warning', 5000);
  }

  window.addEventListener('beforeunload', function(event) {
    if (!isEditMode || editedCells.size === 0) return;
    event.preventDefault();
    event.returnValue = '';
  });

  // ============================================================================
  // EXIT EDIT MODE
  // ============================================================================

  async function exitEditMode(save = false) {
    if (!save && editedCells.size > 0) {
      const confirmed = await confirmAction({
        title: 'Keluar Mode Edit',
        message: 'Ada perubahan yang belum disimpan. Yakin ingin keluar dari mode edit?',
        confirmText: 'Keluar',
        confirmClass: 'btn-warning'
      });
      if (!confirmed) {
        return;
      }
    }


    isEditMode = false;

    // Reload page to restore original view
    window.location.reload();
  }

})();
