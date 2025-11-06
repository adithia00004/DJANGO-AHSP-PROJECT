/**
 * Resizable Columns with LocalStorage Persistence
 * Allows users to resize table columns by dragging and saves preferences
 */

(function() {
  'use strict';

  // Storage key for column widths
  const STORAGE_KEY = 'formset-column-widths';
  const TEXT_WRAP_KEY = 'formset-text-wrap';

  // Configuration
  const MIN_COLUMN_WIDTH = 120; // Minimum width in pixels
  const RESIZER_WIDTH = 5; // Width of the resize handle

  class ResizableColumns {
    constructor(tableId) {
      this.table = document.getElementById(tableId);
      if (!this.table) {
        console.warn(`Table with id "${tableId}" not found`);
        return;
      }

      this.thead = this.table.querySelector('thead');
      this.headers = Array.from(this.thead.querySelectorAll('th'));
      this.isResizing = false;
      this.currentResizer = null;
      this.startX = 0;
      this.startWidth = 0;
      this.currentColumn = null;

      this.init();
    }

    init() {
      // Load saved column widths
      this.loadColumnWidths();

      // Add resize handles to each column header
      this.headers.forEach((th, index) => {
        this.makeResizable(th, index);
      });

      // Load text wrap preference
      this.loadTextWrapPreference();

      console.log('✅ Resizable columns initialized');
    }

    makeResizable(th, index) {
      // Create resize handle
      const resizer = document.createElement('div');
      resizer.className = 'column-resizer';
      resizer.dataset.columnIndex = index;

      // Position the resizer
      th.style.position = 'relative';
      th.appendChild(resizer);

      // Mouse events
      resizer.addEventListener('mousedown', (e) => this.onMouseDown(e, th, index));
    }

    onMouseDown(e, th, index) {
      e.preventDefault();
      e.stopPropagation();

      this.isResizing = true;
      this.currentColumn = th;
      this.startX = e.pageX;
      this.startWidth = th.offsetWidth;

      // Add resizing class to table
      this.table.classList.add('is-resizing');

      // Bind mouse events
      document.addEventListener('mousemove', this.onMouseMoveHandler = (e) => this.onMouseMove(e));
      document.addEventListener('mouseup', this.onMouseUpHandler = (e) => this.onMouseUp(e));

      // Prevent text selection while resizing
      document.body.style.userSelect = 'none';
    }

    onMouseMove(e) {
      if (!this.isResizing) return;

      const deltaX = e.pageX - this.startX;
      const newWidth = Math.max(MIN_COLUMN_WIDTH, this.startWidth + deltaX);

      // Apply new width
      this.currentColumn.style.width = newWidth + 'px';
      this.currentColumn.style.minWidth = newWidth + 'px';
      this.currentColumn.style.maxWidth = newWidth + 'px';

      // Also apply to corresponding cells in tbody
      const columnIndex = Array.from(this.headers).indexOf(this.currentColumn);
      this.applyColumnWidth(columnIndex, newWidth);
    }

    onMouseUp(e) {
      if (!this.isResizing) return;

      this.isResizing = false;
      this.table.classList.remove('is-resizing');

      // Remove event listeners
      document.removeEventListener('mousemove', this.onMouseMoveHandler);
      document.removeEventListener('mouseup', this.onMouseUpHandler);

      // Restore text selection
      document.body.style.userSelect = '';

      // Save column widths to localStorage
      this.saveColumnWidths();
    }

    applyColumnWidth(columnIndex, width) {
      // Apply to tbody cells
      const rows = this.table.querySelectorAll('tbody tr');
      rows.forEach(row => {
        const cell = row.cells[columnIndex];
        if (cell) {
          cell.style.width = width + 'px';
          cell.style.minWidth = width + 'px';
          cell.style.maxWidth = width + 'px';
        }
      });
    }

    saveColumnWidths() {
      const widths = {};

      this.headers.forEach((th, index) => {
        const width = th.offsetWidth;
        // Use column text as key (more reliable than index)
        const columnKey = this.getColumnKey(th, index);
        widths[columnKey] = width;
      });

      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(widths));
        console.log('💾 Column widths saved', widths);
      } catch (e) {
        console.warn('Failed to save column widths to localStorage', e);
      }
    }

    loadColumnWidths() {
      try {
        const savedWidths = localStorage.getItem(STORAGE_KEY);
        if (!savedWidths) return;

        const widths = JSON.parse(savedWidths);
        console.log('📂 Loading saved column widths', widths);

        this.headers.forEach((th, index) => {
          const columnKey = this.getColumnKey(th, index);
          const width = widths[columnKey];

          if (width) {
            th.style.width = width + 'px';
            th.style.minWidth = width + 'px';
            th.style.maxWidth = width + 'px';

            // Apply to tbody cells
            this.applyColumnWidth(index, width);
          }
        });
      } catch (e) {
        console.warn('Failed to load column widths from localStorage', e);
      }
    }

    getColumnKey(th, index) {
      // Use column text content as key, fallback to index
      const text = th.textContent.trim().replace(/\s+/g, '_').toLowerCase();
      return text || `col_${index}`;
    }

    resetColumnWidths() {
      try {
        localStorage.removeItem(STORAGE_KEY);

        // Remove inline styles
        this.headers.forEach((th, index) => {
          th.style.width = '';
          th.style.minWidth = '';
          th.style.maxWidth = '';

          // Remove from tbody cells
          const rows = this.table.querySelectorAll('tbody tr');
          rows.forEach(row => {
            const cell = row.cells[index];
            if (cell) {
              cell.style.width = '';
              cell.style.minWidth = '';
              cell.style.maxWidth = '';
            }
          });
        });

        console.log('🔄 Column widths reset');
        alert('Ukuran kolom telah direset ke default');
      } catch (e) {
        console.warn('Failed to reset column widths', e);
      }
    }

    // Text wrap functionality
    loadTextWrapPreference() {
      try {
        const textWrap = localStorage.getItem(TEXT_WRAP_KEY);
        if (textWrap === 'enabled') {
          this.enableTextWrap();
        }
      } catch (e) {
        console.warn('Failed to load text wrap preference', e);
      }
    }

    enableTextWrap() {
      this.table.classList.add('text-wrap-enabled');
      try {
        localStorage.setItem(TEXT_WRAP_KEY, 'enabled');
      } catch (e) {
        console.warn('Failed to save text wrap preference', e);
      }
    }

    disableTextWrap() {
      this.table.classList.remove('text-wrap-enabled');
      try {
        localStorage.setItem(TEXT_WRAP_KEY, 'disabled');
      } catch (e) {
        console.warn('Failed to save text wrap preference', e);
      }
    }

    toggleTextWrap() {
      if (this.table.classList.contains('text-wrap-enabled')) {
        this.disableTextWrap();
        return false;
      } else {
        this.enableTextWrap();
        return true;
      }
    }
  }

  // Initialize when DOM is ready
  document.addEventListener('DOMContentLoaded', function() {
    // Initialize resizable columns for formset table
    const resizableTable = new ResizableColumns('formset-table');

    // Make globally accessible for reset functionality
    window.formsetResizableTable = resizableTable;

    // Add control buttons
    addControlButtons();
  });

  function addControlButtons() {
    const formsetTable = document.getElementById('formset-table');
    if (!formsetTable) return;

    // Find the button container (before the table wrapper)
    const tableWrapper = formsetTable.closest('.dashboard-form-table-wrapper');
    if (!tableWrapper) return;

    // Create control bar
    const controlBar = document.createElement('div');
    controlBar.className = 'formset-table-controls mb-2';
    controlBar.innerHTML = `
      <div class="d-flex gap-2 align-items-center">
        <small class="text-muted me-2">
          <i class="fas fa-info-circle"></i> Drag kolom untuk resize
        </small>
        <button type="button" class="btn btn-sm btn-outline-secondary" id="toggleTextWrapBtn">
          <i class="fas fa-align-left"></i> Text Wrap
        </button>
        <button type="button" class="btn btn-sm btn-outline-secondary" id="resetColumnWidthsBtn">
          <i class="fas fa-undo"></i> Reset Ukuran
        </button>
      </div>
    `;

    // Insert before table wrapper
    tableWrapper.parentNode.insertBefore(controlBar, tableWrapper);

    // Attach event listeners
    document.getElementById('toggleTextWrapBtn').addEventListener('click', function() {
      const isEnabled = window.formsetResizableTable.toggleTextWrap();
      this.classList.toggle('active', isEnabled);

      if (isEnabled) {
        this.innerHTML = '<i class="fas fa-align-justify"></i> Text Wrap ON';
      } else {
        this.innerHTML = '<i class="fas fa-align-left"></i> Text Wrap OFF';
      }
    });

    document.getElementById('resetColumnWidthsBtn').addEventListener('click', function() {
      if (confirm('Reset semua ukuran kolom ke default?')) {
        window.formsetResizableTable.resetColumnWidths();
      }
    });

    // Set initial text wrap button state
    const textWrapBtn = document.getElementById('toggleTextWrapBtn');
    try {
      const textWrap = localStorage.getItem(TEXT_WRAP_KEY);
      if (textWrap === 'enabled') {
        textWrapBtn.classList.add('active');
        textWrapBtn.innerHTML = '<i class="fas fa-align-justify"></i> Text Wrap ON';
      }
    } catch (e) {}
  }

})();
