/**
 * Preview Import Enhancement JavaScript V2
 * Features: Import Notifications, Validation Indicators, Autocomplete Search, Row Limit, Column Toggle, Resizable Columns
 * Adapted from ahsp_database_v2.js
 */

(function () {
    'use strict';

    // =====================================================
    // Configuration & Utilities
    // =====================================================

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function showToast(message, type = 'success') {
        // Use global DP.toast if available
        if (window.DP && window.DP.toast && window.DP.toast[type]) {
            window.DP.toast[type](message);
            return;
        }

        // Fallback to inline toast
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
        toast.style.zIndex = '99999';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    function highlightText(text, query) {
        if (!query) return text;
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    // =====================================================
    // IMPORT RESULT NOTIFICATION MODULE
    // =====================================================

    const importNotificationModule = {
        modal: null,

        init() {
            // Get or create modal
            this.modal = this.getOrCreateModal();
        },

        getOrCreateModal() {
            let modal = document.getElementById('modalImportResult');
            if (modal) {
                return new bootstrap.Modal(modal);
            }

            // Create modal if doesn't exist
            const modalHTML = `
                <div class="modal fade" id="modalImportResult" tabindex="-1" aria-labelledby="modalImportResultLabel" aria-hidden="true">
                    <div class="modal-dialog modal-lg modal-dialog-scrollable">
                        <div class="modal-content">
                            <div class="modal-header" id="importResultHeader">
                                <h5 class="modal-title" id="modalImportResultLabel">
                                    <i class="bi bi-clipboard-check"></i> Hasil Import
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <div id="importResultSummary"></div>
                                <div id="importErrorsList"></div>
                                <div id="importWarningsList"></div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Tutup</button>
                                <button type="button" class="btn btn-primary" id="btnFixErrors" style="display: none;">
                                    <i class="bi bi-pencil-square"></i> Perbaiki Kesalahan
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHTML);
            return new bootstrap.Modal(document.getElementById('modalImportResult'));
        },

        /**
         * Show import result notification
         * @param {Object} result - Import result object
         * @param {string} result.status - 'success', 'error', or 'warning'
         * @param {number} result.totalJobs - Total jobs imported/processed
         * @param {number} result.totalRincian - Total rincian imported/processed
         * @param {Array} result.errors - Array of error objects {row, column, message, value}
         * @param {Array} result.warnings - Array of warning objects {row, column, message, value}
         */
        show(result) {
            const header = document.getElementById('importResultHeader');
            const summary = document.getElementById('importResultSummary');
            const errorsList = document.getElementById('importErrorsList');
            const warningsList = document.getElementById('importWarningsList');
            const btnFix = document.getElementById('btnFixErrors');

            // Clear previous content
            errorsList.innerHTML = '';
            warningsList.innerHTML = '';

            // Set header style based on status
            if (result.status === 'success') {
                header.className = 'modal-header bg-success-subtle';
                header.querySelector('.modal-title').innerHTML = `
                    <i class="bi bi-check-circle-fill text-success"></i> Import Berhasil
                `;
            } else if (result.status === 'error') {
                header.className = 'modal-header bg-danger-subtle';
                header.querySelector('.modal-title').innerHTML = `
                    <i class="bi bi-x-circle-fill text-danger"></i> Import Gagal
                `;
            } else if (result.status === 'warning') {
                header.className = 'modal-header bg-warning-subtle';
                header.querySelector('.modal-title').innerHTML = `
                    <i class="bi bi-exclamation-triangle-fill text-warning"></i> Import dengan Peringatan
                `;
            }

            // Build summary
            let summaryHTML = '<div class="row g-3 mb-4">';

            // Success stats
            summaryHTML += `
                <div class="col-6">
                    <div class="card border-0 bg-primary-subtle">
                        <div class="card-body text-center p-3">
                            <div class="display-6 fw-bold text-primary">${result.totalJobs || 0}</div>
                            <div class="small text-muted">Pekerjaan AHSP</div>
                        </div>
                    </div>
                </div>
                <div class="col-6">
                    <div class="card border-0 bg-info-subtle">
                        <div class="card-body text-center p-3">
                            <div class="display-6 fw-bold text-info">${result.totalRincian || 0}</div>
                            <div class="small text-muted">Rincian Item</div>
                        </div>
                    </div>
                </div>
            `;

            summaryHTML += '</div>';
            summary.innerHTML = summaryHTML;

            // Show errors if any
            if (result.errors && result.errors.length > 0) {
                btnFix.style.display = 'inline-block';
                errorsList.innerHTML = this.buildIssueList(result.errors, 'Kesalahan', 'danger');
            } else {
                btnFix.style.display = 'none';
            }

            // Show warnings if any
            if (result.warnings && result.warnings.length > 0) {
                warningsList.innerHTML = this.buildIssueList(result.warnings, 'Peringatan', 'warning');
            }

            // Show modal
            this.modal.show();

            // Setup fix button
            if (result.errors && result.errors.length > 0) {
                btnFix.onclick = () => {
                    this.modal.hide();
                    this.highlightErrorsInTable(result.errors);
                };
            }
        },

        buildIssueList(issues, title, type) {
            let html = `
                <div class="alert alert-${type} mb-3">
                    <h6 class="alert-heading">
                        <i class="bi bi-${type === 'danger' ? 'x-circle' : 'exclamation-triangle'}"></i>
                        ${title} (${issues.length})
                    </h6>
                    <div class="small">
            `;

            // Group issues by row for better readability
            const groupedIssues = this.groupIssuesByRow(issues);
            const maxDisplay = 10;
            let count = 0;

            for (const [row, rowIssues] of Object.entries(groupedIssues)) {
                if (count >= maxDisplay) {
                    const remaining = Object.keys(groupedIssues).length - maxDisplay;
                    html += `<div class="text-muted mt-2"><i class="bi bi-three-dots"></i> Dan ${remaining} baris lainnya...</div>`;
                    break;
                }

                html += `<div class="mb-3 pb-2 border-bottom">`;
                html += `<strong class="d-block mb-1">Baris ${row}:</strong>`;
                html += `<ul class="mb-0 ps-3">`;

                for (const issue of rowIssues) {
                    html += `
                        <li class="mb-1">
                            <span class="badge bg-secondary">${issue.column}</span>
                            ${issue.message}
                            ${issue.value ? `<br><span class="text-muted small">Nilai: "${issue.value}"</span>` : ''}
                        </li>
                    `;
                }

                html += `</ul></div>`;
                count++;
            }

            html += `</div></div>`;
            return html;
        },

        groupIssuesByRow(issues) {
            const grouped = {};
            for (const issue of issues) {
                if (!grouped[issue.row]) {
                    grouped[issue.row] = [];
                }
                grouped[issue.row].push(issue);
            }
            return grouped;
        },

        highlightErrorsInTable(errors) {
            // This will be called by validationIndicatorModule
            if (window.previewValidation) {
                window.previewValidation.highlightErrors(errors);
            }
        }
    };

    // =====================================================
    // VALIDATION INDICATOR MODULE
    // =====================================================

    const validationIndicatorModule = {
        errorCells: new Map(), // row-column -> error object
        warningCells: new Map(), // row-column -> warning object

        init() {
            // Expose to window for access from notification module
            window.previewValidation = this;
        },

        /**
         * Add validation indicator to a cell
         * @param {string} tableId - 'tablePreviewJobs' or 'tablePreviewDetails'
         * @param {number} row - Row number (Excel row)
         * @param {string} column - Column name
         * @param {string} type - 'error' or 'warning'
         * @param {string} message - Error/warning message
         * @param {string} value - Current value
         */
        addIndicator(tableId, row, column, type, message, value = null) {
            const table = document.querySelector(`#${tableId} tbody`);
            if (!table) return;

            // Find the cell
            const cell = this.findCell(table, row, column);
            if (!cell) return;

            // Store the issue
            const key = `${row}-${column}`;
            if (type === 'error') {
                this.errorCells.set(key, { row, column, message, value });
                cell.classList.add('cell-invalid');
                cell.classList.remove('cell-warning');
            } else if (type === 'warning') {
                this.warningCells.set(key, { row, column, message, value });
                cell.classList.add('cell-warning');
                cell.classList.remove('cell-invalid');
            }

            // Add tooltip data
            cell.setAttribute('data-validation-message', message);
            cell.setAttribute('data-validation-type', type);
            cell.setAttribute('title', message);

            // Add click handler for editing
            if (!cell.hasAttribute('data-validation-handler')) {
                cell.setAttribute('data-validation-handler', 'true');
                cell.addEventListener('click', (e) => {
                    this.handleCellClick(e.currentTarget, type);
                });
            }
        },

        findCell(tbody, row, column) {
            // Find row by row number
            const rows = tbody.querySelectorAll('tr');
            for (const tr of rows) {
                const rowNumCell = tr.querySelector('td:first-child');
                if (rowNumCell && rowNumCell.textContent.trim() == row) {
                    // Find column by header name
                    const table = tbody.closest('table');
                    const headers = Array.from(table.querySelectorAll('thead th'));
                    const colIndex = headers.findIndex(th =>
                        th.textContent.trim().toLowerCase().includes(column.toLowerCase())
                    );

                    if (colIndex !== -1) {
                        return tr.querySelectorAll('td')[colIndex];
                    }
                }
            }
            return null;
        },

        handleCellClick(cell, type) {
            const message = cell.getAttribute('data-validation-message');

            // Show options: Edit or Ignore
            const optionsHTML = `
                <div class="validation-options position-absolute bg-white border rounded shadow p-2" style="z-index: 9999;">
                    <div class="small mb-2">
                        <i class="bi bi-${type === 'error' ? 'x-circle' : 'exclamation-triangle'} text-${type === 'error' ? 'danger' : 'warning'}"></i>
                        ${message}
                    </div>
                    <div class="d-flex gap-2">
                        <button class="btn btn-sm btn-primary btn-edit-cell">
                            <i class="bi bi-pencil"></i> Edit
                        </button>
                        ${type === 'warning' ? `
                            <button class="btn btn-sm btn-secondary btn-ignore-cell">
                                <i class="bi bi-eye-slash"></i> Abaikan
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;

            // Remove existing options
            document.querySelectorAll('.validation-options').forEach(el => el.remove());

            // Add options
            cell.style.position = 'relative';
            cell.insertAdjacentHTML('beforeend', optionsHTML);

            const options = cell.querySelector('.validation-options');

            // Edit button
            options.querySelector('.btn-edit-cell').addEventListener('click', (e) => {
                e.stopPropagation();
                this.enableEdit(cell);
                options.remove();
            });

            // Ignore button (for warnings only)
            const ignoreBtn = options.querySelector('.btn-ignore-cell');
            if (ignoreBtn) {
                ignoreBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.ignoreWarning(cell);
                    options.remove();
                });
            }

            // Close on outside click
            setTimeout(() => {
                document.addEventListener('click', function closeOptions(e) {
                    if (!options.contains(e.target)) {
                        options.remove();
                        document.removeEventListener('click', closeOptions);
                    }
                }, { once: true });
            }, 100);
        },

        enableEdit(cell) {
            // Find the input field in the cell
            const input = cell.querySelector('input, select, textarea');
            if (input) {
                input.focus();
                input.select();
            }
        },

        ignoreWarning(cell) {
            cell.classList.remove('cell-warning');
            cell.removeAttribute('data-validation-message');
            cell.removeAttribute('data-validation-type');
            cell.removeAttribute('title');
        },

        highlightErrors(errors) {
            // Scroll to first error and highlight all errors
            for (const error of errors) {
                const tableId = this.determineTableId(error);
                this.addIndicator(tableId, error.row, error.column, 'error', error.message, error.value);
            }

            // Scroll to first error
            const firstError = document.querySelector('.cell-invalid');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        },

        determineTableId(issue) {
            // Determine which table based on column names
            const jobColumns = ['sumber', 'kode', 'nama pekerjaan', 'klasifikasi', 'satuan'];
            const detailColumns = ['kategori', 'kode item', 'uraian', 'koefisien'];

            const columnLower = issue.column.toLowerCase();
            if (jobColumns.some(col => columnLower.includes(col))) {
                return 'tablePreviewJobs';
            } else if (detailColumns.some(col => columnLower.includes(col))) {
                return 'tablePreviewDetails';
            }

            return 'tablePreviewJobs'; // Default
        },

        clearAll() {
            this.errorCells.clear();
            this.warningCells.clear();
            document.querySelectorAll('.cell-invalid, .cell-warning').forEach(cell => {
                cell.classList.remove('cell-invalid', 'cell-warning');
                cell.removeAttribute('data-validation-message');
                cell.removeAttribute('data-validation-type');
                cell.removeAttribute('title');
            });
        }
    };

    // =====================================================
    // AUTOCOMPLETE SEARCH MODULE
    // =====================================================

    const autocompleteModule = {
        // State
        currentTable: null,
        currentInput: null,
        currentDropdown: null,
        suggestions: [],
        selectedIndex: -1,
        tableData: new Map(),
        initializedInputs: new Set(), // Track which inputs have been initialized

        init() {
            // Initialize after AJAX reloads
            this.initializeTables();

            // Re-initialize on tab change
            const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
            tabButtons.forEach(btn => {
                btn.addEventListener('shown.bs.tab', () => {
                    this.initializeTables();
                });
            });

            // Reposition dropdown on scroll/resize
            window.addEventListener('scroll', () => {
                if (this.currentDropdown && this.currentDropdown.style.display === 'block') {
                    this.positionDropdown(this.currentDropdown);
                }
            }, true);

            window.addEventListener('resize', () => {
                if (this.currentDropdown && this.currentDropdown.style.display === 'block') {
                    this.positionDropdown(this.currentDropdown);
                }
            });
        },

        initializeTables() {
            this.initTable('tablePreviewJobs', 'quickSearchJobs', 'autocompleteJobsDropdown');
            this.initTable('tablePreviewDetails', 'quickSearchDetails', 'autocompleteDetailsDropdown');
        },

        initTable(tableId, inputId, dropdownId) {
            const table = document.getElementById(tableId);
            const input = document.getElementById(inputId);
            const dropdown = document.getElementById(dropdownId);

            if (!table || !input || !dropdown) return;

            // Extract table data (always update this)
            this.extractTableData(tableId, table);

            // Skip event listener setup if already initialized
            if (this.initializedInputs.has(inputId)) {
                return;
            }

            // Mark as initialized
            this.initializedInputs.add(inputId);

            // Input events - faster response with 150ms debounce
            input.addEventListener('input', debounce((e) => {
                this.handleInput(e.target, dropdown, tableId);
            }, 150));

            input.addEventListener('focus', (e) => {
                if (e.target.value) {
                    this.handleInput(e.target, dropdown, tableId);
                }
            });

            input.addEventListener('keydown', (e) => {
                this.handleKeydown(e, dropdown, tableId, input);
            });

            // Search button handler
            const searchBtn = input.closest('.input-group')?.querySelector('.btn-search');
            if (searchBtn) {
                searchBtn.addEventListener('click', () => {
                    this.performSearch(input.value, tableId);
                    dropdown.style.display = 'none';
                });
            }

            // Close dropdown when clicking outside
            document.addEventListener('click', (e) => {
                if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                    dropdown.style.display = 'none';
                }
            });
        },

        extractTableData(tableId, table) {
            const data = [];
            const tbody = table.querySelector('tbody');
            const rows = tbody.querySelectorAll('tr');

            rows.forEach((row, index) => {
                const cells = row.querySelectorAll('td');
                if (cells.length === 0) return;

                const rowData = {
                    index: index,
                    rowElement: row,
                    searchText: '',
                    cells: []
                };

                cells.forEach(cell => {
                    const text = cell.textContent.trim();
                    rowData.cells.push(text);
                    rowData.searchText += text + ' ';
                });

                data.push(rowData);
            });

            this.tableData.set(tableId, data);
        },

        handleInput(input, dropdown, tableId) {
            const query = input.value.trim();

            if (!query) {
                dropdown.style.display = 'none';
                this.clearSearch(tableId);
                return;
            }

            // Search and get suggestions
            this.suggestions = this.search(tableId, query);
            this.selectedIndex = -1;

            if (this.suggestions.length > 0) {
                this.showDropdown(dropdown, this.suggestions, query, tableId);
            } else {
                dropdown.style.display = 'none';
            }

            this.currentInput = input;
            this.currentDropdown = dropdown;
            this.currentTable = tableId;
        },

        search(tableId, query) {
            const data = this.tableData.get(tableId);
            if (!data) return [];

            const queryLower = query.toLowerCase();
            const results = [];

            data.forEach(row => {
                if (row.searchText.toLowerCase().includes(queryLower)) {
                    results.push({
                        rowIndex: row.index,
                        rowElement: row.rowElement,
                        text: row.cells.slice(0, 4).join(' | '), // First 4 columns
                        matchScore: this.calculateMatchScore(row.searchText, queryLower)
                    });
                }
            });

            // Sort by match score
            results.sort((a, b) => b.matchScore - a.matchScore);

            return results.slice(0, 10); // Max 10 suggestions
        },

        calculateMatchScore(text, query) {
            const textLower = text.toLowerCase();
            let score = 0;

            // Exact match
            if (textLower === query) score += 100;

            // Starts with query
            if (textLower.startsWith(query)) score += 50;

            // Contains query
            if (textLower.includes(query)) score += 10;

            return score;
        },

        showDropdown(dropdown, suggestions, query, tableId) {
            let html = '';

            suggestions.forEach((suggestion, index) => {
                const highlighted = highlightText(suggestion.text, query);
                html += `
                    <div class="autocomplete-item ${index === 0 ? 'active' : ''}"
                         data-index="${index}"
                         data-row-index="${suggestion.rowIndex}">
                        ${highlighted}
                    </div>
                `;
            });

            dropdown.innerHTML = html;

            // Position dropdown
            this.positionDropdown(dropdown);

            dropdown.style.display = 'block';

            // Add click handlers
            dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    const rowIndex = parseInt(e.currentTarget.getAttribute('data-row-index'));
                    this.jumpToRow(tableId, rowIndex);
                    dropdown.style.display = 'none';
                });
            });
        },

        positionDropdown(dropdown) {
            if (!this.currentInput) return;

            const rect = this.currentInput.getBoundingClientRect();

            dropdown.style.position = 'fixed';
            dropdown.style.top = (rect.bottom) + 'px';
            dropdown.style.left = rect.left + 'px';
            dropdown.style.width = rect.width + 'px';
        },

        handleKeydown(e, dropdown, tableId, input) {
            const items = dropdown.querySelectorAll('.autocomplete-item');

            if (e.key === 'ArrowDown' && dropdown.style.display === 'block') {
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, items.length - 1);
                this.updateSelection(items);
            } else if (e.key === 'ArrowUp' && dropdown.style.display === 'block') {
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
                this.updateSelection(items);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (dropdown.style.display === 'block' && this.selectedIndex >= 0 && this.selectedIndex < items.length) {
                    // Select item from dropdown
                    items[this.selectedIndex].click();
                } else {
                    // Perform search
                    this.performSearch(input.value, tableId);
                    dropdown.style.display = 'none';
                }
            } else if (e.key === 'Escape') {
                dropdown.style.display = 'none';
            }
        },

        updateSelection(items) {
            items.forEach((item, index) => {
                if (index === this.selectedIndex) {
                    item.classList.add('active');
                    item.scrollIntoView({ block: 'nearest' });
                } else {
                    item.classList.remove('active');
                }
            });
        },

        jumpToRow(tableId, rowIndex) {
            const data = this.tableData.get(tableId);
            if (!data || !data[rowIndex]) return;

            const row = data[rowIndex].rowElement;

            // Scroll to row
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Highlight row temporarily
            row.classList.add('table-active');
            setTimeout(() => {
                row.classList.remove('table-active');
            }, 2000);
        },

        clearSearch(tableId) {
            // Clear any search highlighting
            const table = document.getElementById(tableId);
            if (!table) return;

            table.querySelectorAll('mark').forEach(mark => {
                mark.replaceWith(mark.textContent);
            });
        },

        performSearch(query, tableId) {
            // Backend search - reload page with search parameter
            const trimmedQuery = query?.trim() || '';

            if (!trimmedQuery) {
                // Clear search - redirect to page without search param
                const url = new URL(window.location.href);
                url.searchParams.delete('search_jobs');
                url.searchParams.delete('search_details');
                url.searchParams.delete('jobs_page'); // Reset to page 1
                url.searchParams.delete('details_page');

                // Show loading
                showToast('Membersihkan pencarian...', 'info');

                // Redirect
                window.location.href = url.toString();
                return;
            }

            // Build URL with search parameter
            const url = new URL(window.location.href);

            if (tableId === 'tablePreviewJobs') {
                url.searchParams.set('search_jobs', trimmedQuery);
                url.searchParams.set('jobs_page', '1'); // Reset to page 1
                url.hash = '#pane-ahsp';
            } else if (tableId === 'tablePreviewDetails') {
                url.searchParams.set('search_details', trimmedQuery);
                url.searchParams.set('details_page', '1'); // Reset to page 1
                url.hash = '#pane-rincian';
            }

            // Show loading feedback
            showToast(`Mencari "${trimmedQuery}"...`, 'info');

            // Redirect to search results
            window.location.href = url.toString();
        }
    };

    // =====================================================
    // ROW LIMIT MODULE
    // =====================================================

    const rowLimitModule = {
        init() {
            // DISABLED - Fixed to 50 rows per page
            // Row limit dropdown hidden via CSS
            console.log('[Preview Import V2] Row limit fixed to 50 rows per page');
        }
    };

    // =====================================================
    // COLUMN TOGGLE MODULE
    // =====================================================

    const columnToggleModule = {
        activeMenu: null,
        activeButton: null,

        init() {
            this.initTable('tablePreviewJobs', 'btnColumnToggleJobs', 'columnToggleJobsMenu');
            this.initTable('tablePreviewDetails', 'btnColumnToggleDetails', 'columnToggleDetailsMenu');

            // Re-initialize on tab change
            const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
            tabButtons.forEach(btn => {
                btn.addEventListener('shown.bs.tab', () => {
                    this.initTable('tablePreviewJobs', 'btnColumnToggleJobs', 'columnToggleJobsMenu');
                    this.initTable('tablePreviewDetails', 'btnColumnToggleDetails', 'columnToggleDetailsMenu');
                });
            });

            // Reposition menu on scroll
            window.addEventListener('scroll', () => {
                if (this.activeMenu && this.activeButton && this.activeMenu.style.display === 'block') {
                    this.positionMenu(this.activeButton, this.activeMenu);
                }
            }, true); // Use capture to catch all scroll events

            // Reposition on window resize
            window.addEventListener('resize', () => {
                if (this.activeMenu && this.activeButton && this.activeMenu.style.display === 'block') {
                    this.positionMenu(this.activeButton, this.activeMenu);
                }
            });
        },

        initTable(tableId, btnId, menuId) {
            const table = document.getElementById(tableId);
            const btn = document.getElementById(btnId);
            const menu = document.getElementById(menuId);

            if (!table || !btn) return;

            // Create or get menu
            let menuElement = menu;
            if (!menuElement) {
                menuElement = this.createMenu(tableId, btnId);
            }

            // Load saved column visibility first
            this.loadColumnVisibility(table, tableId);

            // Build column list
            this.buildColumnList(table, menuElement, tableId);

            // Toggle menu on button click
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isVisible = menuElement.style.display === 'block';

                // Close all other menus
                document.querySelectorAll('.column-toggle-menu').forEach(m => {
                    m.style.display = 'none';
                });

                if (isVisible) {
                    menuElement.style.display = 'none';
                    this.activeMenu = null;
                    this.activeButton = null;
                } else {
                    menuElement.style.display = 'block';
                    this.activeMenu = menuElement;
                    this.activeButton = btn;
                    this.positionMenu(btn, menuElement);
                }
            });

            // Close menu on outside click
            document.addEventListener('click', (e) => {
                if (!btn.contains(e.target) && !menuElement.contains(e.target)) {
                    menuElement.style.display = 'none';
                    if (this.activeMenu === menuElement) {
                        this.activeMenu = null;
                        this.activeButton = null;
                    }
                }
            });
        },

        createMenu(tableId, btnId) {
            const menu = document.createElement('div');
            menu.id = `${btnId.replace('btn', '')}Menu`;
            menu.className = 'column-toggle-menu';
            document.body.appendChild(menu);
            return menu;
        },

        buildColumnList(table, menu, tableId) {
            const headers = table.querySelectorAll('thead th');
            const savedState = JSON.parse(localStorage.getItem(`${tableId}_columnVisibility`) || '{}');

            let html = '<div class="column-toggle-header">Tampilkan Kolom:</div>';

            headers.forEach((th, index) => {
                const columnName = th.textContent.trim();
                const isVisible = savedState[index] !== false;

                html += `
                    <label class="column-toggle-item">
                        <input type="checkbox"
                               data-column-index="${index}"
                               ${isVisible ? 'checked' : ''}>
                        <span>${columnName}</span>
                    </label>
                `;
            });

            menu.innerHTML = html;

            // Add change handlers
            menu.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
                checkbox.addEventListener('change', (e) => {
                    const columnIndex = parseInt(e.target.getAttribute('data-column-index'));
                    this.toggleColumn(table, columnIndex, e.target.checked, tableId);
                });
            });
        },

        toggleColumn(table, columnIndex, show, tableId) {
            // Toggle header
            const headers = table.querySelectorAll('thead th');
            if (headers[columnIndex]) {
                headers[columnIndex].style.display = show ? '' : 'none';
            }

            // Toggle all cells in column
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells[columnIndex]) {
                    cells[columnIndex].style.display = show ? '' : 'none';
                }
            });

            // Save state
            const savedState = JSON.parse(localStorage.getItem(`${tableId}_columnVisibility`) || '{}');
            savedState[columnIndex] = show;
            localStorage.setItem(`${tableId}_columnVisibility`, JSON.stringify(savedState));
        },

        loadColumnVisibility(table, tableId) {
            const savedState = JSON.parse(localStorage.getItem(`${tableId}_columnVisibility`) || '{}');

            // Apply saved visibility state to columns
            Object.keys(savedState).forEach(columnIndex => {
                const show = savedState[columnIndex];
                const index = parseInt(columnIndex);

                // Toggle header
                const headers = table.querySelectorAll('thead th');
                if (headers[index]) {
                    headers[index].style.display = show ? '' : 'none';
                }

                // Toggle all cells in column
                const rows = table.querySelectorAll('tbody tr');
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells[index]) {
                        cells[index].style.display = show ? '' : 'none';
                    }
                });
            });
        },

        positionMenu(btn, menu) {
            const rect = btn.getBoundingClientRect();
            menu.style.position = 'fixed';
            menu.style.top = (rect.bottom + 5) + 'px';
            menu.style.left = rect.left + 'px';
            menu.style.minWidth = '200px';
        }
    };

    // =====================================================
    // RESIZABLE COLUMNS MODULE
    // =====================================================

    const resizableColumnsModule = {
        isResizing: false,
        currentResizer: null,
        currentColumn: null,
        startX: 0,
        startWidth: 0,

        init() {
            this.initTable('tablePreviewJobs');
            this.initTable('tablePreviewDetails');

            // Re-initialize on tab change
            const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
            tabButtons.forEach(btn => {
                btn.addEventListener('shown.bs.tab', () => {
                    this.initTable('tablePreviewJobs');
                    this.initTable('tablePreviewDetails');
                });
            });
        },

        initTable(tableId) {
            const table = document.getElementById(tableId);
            if (!table) return;

            const headers = table.querySelectorAll('thead th');

            // Clear existing resizers
            headers.forEach(header => {
                const existingResizer = header.querySelector('.column-resizer');
                if (existingResizer) {
                    existingResizer.remove();
                }
            });

            headers.forEach((header, index) => {
                // Skip last column
                if (index === headers.length - 1) return;

                // Create resizer element
                const resizer = document.createElement('div');
                resizer.className = 'column-resizer';
                header.style.position = 'relative';
                header.appendChild(resizer);

                // Add mouse events
                resizer.addEventListener('mousedown', (e) => {
                    this.startResize(e, header, resizer, table);
                });
            });

            // Load saved widths
            this.loadColumnWidths(table);
        },

        startResize(e, header, resizer, table) {
            e.preventDefault();
            e.stopPropagation();

            this.isResizing = true;
            this.currentResizer = resizer;
            this.currentColumn = header;
            this.currentTable = table;
            this.startX = e.pageX;
            this.startWidth = header.offsetWidth;

            // Visual feedback
            document.body.classList.add('column-resizing');
            resizer.classList.add('resizing');

            // Add global mouse events
            const mouseMoveHandler = (e) => this.doResize(e);
            const mouseUpHandler = () => {
                this.stopResize();
                document.removeEventListener('mousemove', mouseMoveHandler);
                document.removeEventListener('mouseup', mouseUpHandler);
            };

            document.addEventListener('mousemove', mouseMoveHandler);
            document.addEventListener('mouseup', mouseUpHandler);
        },

        doResize(e) {
            if (!this.isResizing) return;

            const diff = e.pageX - this.startX;
            const newWidth = this.startWidth + diff;

            // Minimum width: 60px
            if (newWidth >= 60) {
                this.currentColumn.style.width = newWidth + 'px';
                this.currentColumn.style.minWidth = newWidth + 'px';
            }
        },

        stopResize() {
            if (!this.isResizing) return;

            this.isResizing = false;
            document.body.classList.remove('column-resizing');
            this.currentResizer.classList.remove('resizing');

            // Save width
            if (this.currentTable) {
                this.saveColumnWidths(this.currentTable);
            }

            this.currentResizer = null;
            this.currentColumn = null;
            this.currentTable = null;
        },

        saveColumnWidths(table) {
            const tableId = table.id;
            const headers = table.querySelectorAll('thead th');
            const widths = [];

            headers.forEach(header => {
                widths.push(header.style.width || '');
            });

            localStorage.setItem(`${tableId}_columnWidths`, JSON.stringify(widths));
        },

        loadColumnWidths(table) {
            const tableId = table.id;
            const saved = localStorage.getItem(`${tableId}_columnWidths`);

            if (!saved) return;

            try {
                const widths = JSON.parse(saved);
                const headers = table.querySelectorAll('thead th');

                headers.forEach((header, index) => {
                    if (widths[index]) {
                        header.style.width = widths[index];
                        header.style.minWidth = widths[index];
                    }
                });
            } catch (e) {
                console.error('Error loading column widths:', e);
            }
        }
    };

    // =====================================================
    // CHANGE TRACKING & SAVE MODULE
    // =====================================================

    const changeTrackingModule = {
        originalValues: new Map(),
        changedFields: new Map(),
        saveModal: null,
        currentForm: null,

        init() {
            this.captureInitialState();
            this.createSaveModal();

            // Track changes on all form inputs
            document.querySelectorAll('.preview-table input, .preview-table select, .preview-table textarea').forEach(input => {
                input.addEventListener('change', (e) => this.trackChange(e.target));
                input.addEventListener('input', (e) => this.trackChange(e.target));
            });

            // Handle form submissions
            const forms = document.querySelectorAll('form.js-preview-form');
            forms.forEach(form => {
                form.addEventListener('submit', (e) => this.handleSubmit(e, form));
            });
        },

        captureInitialState() {
            document.querySelectorAll('.preview-table input, .preview-table select, .preview-table textarea').forEach(input => {
                const key = this.getFieldKey(input);
                this.originalValues.set(key, input.value);
            });
        },

        getFieldKey(input) {
            return `${input.name || input.id}_${input.closest('tr')?.rowIndex || 0}`;
        },

        getFieldLabel(input) {
            const cell = input.closest('td');
            if (!cell) return 'Field';

            const cellIndex = Array.from(cell.parentElement.children).indexOf(cell);
            const table = cell.closest('table');
            const headers = table.querySelectorAll('thead th');

            if (headers[cellIndex]) {
                return headers[cellIndex].textContent.trim().replace(/\s+/g, ' ');
            }

            return 'Field';
        },

        trackChange(input) {
            const key = this.getFieldKey(input);
            const originalValue = this.originalValues.get(key);
            const currentValue = input.value;

            if (originalValue !== currentValue) {
                this.changedFields.set(key, {
                    input: input,
                    label: this.getFieldLabel(input),
                    oldValue: originalValue,
                    newValue: currentValue
                });
                input.classList.add('is-modified');
            } else {
                this.changedFields.delete(key);
                input.classList.remove('is-modified');
            }

            this.updateSaveButtonState();
        },

        updateSaveButtonState() {
            const saveBtns = document.querySelectorAll('button[type="submit"]:has(.bi-save)');
            saveBtns.forEach(btn => {
                if (this.changedFields.size > 0) {
                    btn.classList.add('btn-warning');
                    btn.classList.remove('btn-primary');
                    const icon = btn.querySelector('i');
                    if (icon && icon.className.includes('save')) {
                        icon.className = 'bi bi-exclamation-circle';
                    }
                } else {
                    btn.classList.add('btn-primary');
                    btn.classList.remove('btn-warning');
                    const icon = btn.querySelector('i');
                    if (icon && icon.className.includes('exclamation')) {
                        icon.className = 'bi bi-save';
                    }
                }
            });
        },

        handleSubmit(e, form) {
            e.preventDefault();

            if (this.changedFields.size === 0) {
                showToast('Tidak ada perubahan untuk disimpan', 'info');
                return false;
            }

            this.currentForm = form;
            this.showSaveModal();
            return false;
        },

        createSaveModal() {
            if (document.getElementById('modalSaveConfirmation')) {
                this.saveModal = new bootstrap.Modal(document.getElementById('modalSaveConfirmation'));
                const btnConfirm = document.getElementById('btnConfirmSave');
                if (btnConfirm) {
                    btnConfirm.addEventListener('click', () => this.confirmSave());
                }
                return;
            }

            const modalHTML = `
                <div class="modal fade" id="modalSaveConfirmation" tabindex="-1" aria-hidden="true">
                    <div class="modal-dialog modal-dialog-scrollable">
                        <div class="modal-content">
                            <div class="modal-header bg-warning-subtle">
                                <h5 class="modal-title">
                                    <i class="bi bi-exclamation-triangle-fill text-warning"></i> Konfirmasi Simpan
                                </h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <p class="mb-3">Anda akan menyimpan <strong id="saveChangeCount">0</strong> perubahan:</p>
                                <div id="saveChangesList" class="small"></div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Batal</button>
                                <button type="button" class="btn btn-primary" id="btnConfirmSave">
                                    <i class="bi bi-save"></i> Simpan
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHTML);
            this.saveModal = new bootstrap.Modal(document.getElementById('modalSaveConfirmation'));
            document.getElementById('btnConfirmSave').addEventListener('click', () => this.confirmSave());
        },

        showSaveModal() {
            const changeCount = this.changedFields.size;
            document.getElementById('saveChangeCount').textContent = changeCount;

            const changesList = document.getElementById('saveChangesList');
            let html = '<ul class="list-unstyled mb-0">';

            let count = 0;
            for (const [key, change] of this.changedFields) {
                if (count >= 10) {
                    const remaining = changeCount - 10;
                    html += `<li class="text-muted"><i class="bi bi-three-dots"></i> Dan ${remaining} perubahan lainnya...</li>`;
                    break;
                }

                const oldVal = (change.oldValue || '(kosong)').substring(0, 40);
                const newVal = (change.newValue || '(kosong)').substring(0, 40);

                html += `
                    <li class="mb-2 pb-2 border-bottom">
                        <strong>${change.label}</strong>
                        <div class="mt-1">
                            <span class="badge bg-danger-subtle text-danger text-decoration-line-through">${oldVal}</span>
                            <i class="bi bi-arrow-right mx-1"></i>
                            <span class="badge bg-success-subtle text-success">${newVal}</span>
                        </div>
                    </li>
                `;
                count++;
            }

            html += '</ul>';
            changesList.innerHTML = html;

            if (this.saveModal) {
                this.saveModal.show();
            }
        },

        confirmSave() {
            if (!this.currentForm) return;

            const btnSave = document.getElementById('btnConfirmSave');
            const originalHTML = btnSave.innerHTML;
            btnSave.disabled = true;
            btnSave.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Menyimpan...';

            const formData = new FormData(this.currentForm);
            const csrfToken = getCookie('csrftoken');

            fetch(this.currentForm.action || window.location.href, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(response => response.json())
                .then(data => {
                    this.saveModal.hide();

                    if (data.success) {
                        this.showSuccessNotification(data);
                        this.changedFields.clear();
                        this.captureInitialState();
                        this.updateSaveButtonState();
                        document.querySelectorAll('.is-modified').forEach(el => el.classList.remove('is-modified'));
                    } else {
                        showToast(data.message || 'Gagal menyimpan perubahan', 'danger');
                    }
                })
                .catch(error => {
                    console.error('Save error:', error);
                    showToast('Terjadi kesalahan saat menyimpan', 'danger');
                    this.saveModal.hide();
                })
                .finally(() => {
                    btnSave.disabled = false;
                    btnSave.innerHTML = originalHTML;
                });
        },

        showSuccessNotification(data) {
            let successModal = document.getElementById('modalSaveSuccess');

            if (!successModal) {
                const modalHTML = `
                    <div class="modal fade" id="modalSaveSuccess" tabindex="-1" aria-hidden="true">
                        <div class="modal-dialog modal-dialog-centered">
                            <div class="modal-content">
                                <div class="modal-header bg-success-subtle border-0">
                                    <h5 class="modal-title">
                                        <i class="bi bi-check-circle-fill text-success"></i> Berhasil
                                    </h5>
                                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                </div>
                                <div class="modal-body text-center py-4">
                                    <i class="bi bi-check-circle text-success" style="font-size: 3rem;"></i>
                                    <h4 class="mt-3">Perubahan Tersimpan!</h4>
                                    <p class="text-muted mb-0" id="successMessage">Data berhasil diperbarui</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                document.body.insertAdjacentHTML('beforeend', modalHTML);
                successModal = document.getElementById('modalSaveSuccess');
            }

            const messageEl = document.getElementById('successMessage');
            if (messageEl && data.message) {
                messageEl.textContent = data.message;
            }

            const modal = new bootstrap.Modal(successModal);
            modal.show();

            setTimeout(() => modal.hide(), 2000);
        }
    };

    // =====================================================
    // JUMP TO PAGE MODULE
    // =====================================================

    const jumpToPageModule = {
        init() {
            const inputs = document.querySelectorAll('.inline-page-input');
            inputs.forEach(input => {
                // Handle Enter key
                input.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        input.blur(); // Trigger blur to execute jump
                    }
                });

                // Handle blur (when user clicks outside or presses Enter)
                input.addEventListener('blur', () => {
                    this.jumpToPage(input);
                });

                // Prevent form submission on Enter
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                    }
                });
            });
        },

        jumpToPage(input) {
            const targetPage = parseInt(input.value);
            const currentPage = parseInt(input.dataset.currentPage);
            const totalPages = parseInt(input.dataset.totalPages);
            const section = input.dataset.section;

            // Validate
            if (isNaN(targetPage) || targetPage < 1 || targetPage > totalPages) {
                // Reset to current page
                input.value = currentPage;
                showToast(`Halaman harus antara 1 dan ${totalPages}`, 'warning');
                return;
            }

            // Skip if same page
            if (targetPage === currentPage) {
                return;
            }

            // Build URL
            const url = new URL(window.location.href);

            if (section === 'jobs') {
                url.searchParams.set('jobs_page', targetPage);
                const detailsPage = input.dataset.detailsPage;
                if (detailsPage) {
                    url.searchParams.set('details_page', detailsPage);
                }
                url.hash = '#pane-ahsp';
            } else if (section === 'details') {
                url.searchParams.set('details_page', targetPage);
                const jobsPage = input.dataset.jobsPage;
                if (jobsPage) {
                    url.searchParams.set('jobs_page', jobsPage);
                }
                url.hash = '#pane-rincian';
            }

            // Navigate
            window.location.href = url.toString();
        }
    };

    // =====================================================
    // INITIALIZATION
    // =====================================================

    document.addEventListener('DOMContentLoaded', function () {
        // Initialize modules
        importNotificationModule.init();
        validationIndicatorModule.init();
        autocompleteModule.init();
        rowLimitModule.init();
        columnToggleModule.init();
        resizableColumnsModule.init();
        changeTrackingModule.init();
        jumpToPageModule.init();

        // Expose to window for external calls
        window.showImportResult = (result) => {
            importNotificationModule.show(result);
        };

        // Debounced re-initialization to prevent freeze on tab switch
        let reinitTimeout = null;
        let isReinitializing = false;
        let mutationObserver = null;

        const debouncedReinit = () => {
            if (reinitTimeout) {
                clearTimeout(reinitTimeout);
            }

            reinitTimeout = setTimeout(() => {
                // Prevent re-entry while already reinitializing
                if (isReinitializing) {
                    console.log('[Preview Import V2] Skipping reinit - already in progress');
                    return;
                }

                // Only reinit if table is visible
                const visibleJobsTable = document.querySelector('#tablePreviewJobs:not([style*="display: none"])');
                const visibleDetailsTable = document.querySelector('#tablePreviewDetails:not([style*="display: none"])');

                if (visibleJobsTable || visibleDetailsTable) {
                    isReinitializing = true;

                    // Temporarily disconnect observer to prevent loop
                    if (mutationObserver) {
                        mutationObserver.disconnect();
                    }

                    console.log('[Preview Import V2] Reinitializing visible tables...');

                    // Reinit in chunks to prevent freeze
                    requestAnimationFrame(() => {
                        autocompleteModule.initializeTables();

                        requestAnimationFrame(() => {
                            rowLimitModule.init();

                            requestAnimationFrame(() => {
                                columnToggleModule.init();

                                requestAnimationFrame(() => {
                                    resizableColumnsModule.init();

                                    // Reconnect observer after reinit complete
                                    setTimeout(() => {
                                        if (mutationObserver && previewRoot) {
                                            mutationObserver.observe(previewRoot, {
                                                childList: true,
                                                subtree: true
                                            });
                                        }
                                        isReinitializing = false;
                                        console.log('[Preview Import V2] Reinit complete, observer reconnected');
                                    }, 100);
                                });
                            });
                        });
                    });
                }
            }, 500); // Increased to 500ms for better debouncing
        };

        // Re-initialize modules after AJAX reloads (debounced)
        const previewRoot = document.getElementById('preview-root');
        if (previewRoot) {
            mutationObserver = new MutationObserver((mutations) => {
                // Only trigger if actual content changed
                const hasSignificantChange = mutations.some(mutation => {
                    // Ignore style-only changes
                    if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                        return false;
                    }
                    // Check if nodes were added/removed
                    return mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0;
                });

                if (hasSignificantChange) {
                    debouncedReinit();
                }
            });

            mutationObserver.observe(previewRoot, {
                childList: true,
                subtree: true,
                attributes: false // Don't watch attribute changes to reduce triggers
            });
        }

        // Smart tab switching without freeze
        const tabButtons = document.querySelectorAll('[data-bs-toggle="tab"]');
        tabButtons.forEach(btn => {
            btn.addEventListener('shown.bs.tab', (e) => {
                console.log('[Preview Import V2] Tab switched, lazy initializing...');

                // Show loading briefly
                const targetPane = document.querySelector(btn.getAttribute('data-bs-target'));
                if (targetPane) {
                    targetPane.style.opacity = '0.5';

                    // Lazy init after a brief delay
                    setTimeout(() => {
                        debouncedReinit();
                        targetPane.style.opacity = '1';
                    }, 50);
                }
            });
        });

        console.log('[Preview Import V2] All modules initialized');
    });

})();
