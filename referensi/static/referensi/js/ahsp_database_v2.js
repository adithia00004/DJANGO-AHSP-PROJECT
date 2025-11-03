/**
 * AHSP Database Management JavaScript V2
 * Features: Autocomplete Search, Jump to Row, Table Sorting, Change Tracking, Bulk Delete
 */

(function() {
    'use strict';

    // =====================================================
    // Configuration & Utilities
    // =====================================================

    const config = window.AHSP_DB_CONFIG || {};

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function showToast(message, type = 'success') {
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

        init() {
            // Initialize Jobs table autocomplete
            this.initTable('tableJobs', 'quickSearchJobs', 'autocompleteJobsDropdown', 'btnSearchJobs');

            // Initialize Items table autocomplete
            this.initTable('tableItems', 'quickSearchItems', 'autocompleteItemsDropdown', 'btnSearchItems');

            // Reposition dropdown on scroll/resize (for fixed positioning)
            window.addEventListener('scroll', () => {
                if (this.currentDropdown && this.currentDropdown.style.display === 'block') {
                    this.positionDropdown(this.currentDropdown);
                }
            }, true); // Use capture phase to catch all scroll events

            window.addEventListener('resize', () => {
                if (this.currentDropdown && this.currentDropdown.style.display === 'block') {
                    this.positionDropdown(this.currentDropdown);
                }
            });
        },

        initTable(tableId, inputId, dropdownId, btnId) {
            const table = document.getElementById(tableId);
            const input = document.getElementById(inputId);
            const dropdown = document.getElementById(dropdownId);
            const searchBtn = document.getElementById(btnId);

            if (!table || !input || !dropdown) return;

            // Extract table data
            this.extractTableData(tableId, table);

            // Input events
            input.addEventListener('input', debounce((e) => {
                this.handleInput(e.target, dropdown, tableId);
            }, 300));

            input.addEventListener('keydown', (e) => {
                this.handleKeydown(e, dropdown, tableId);
            });

            input.addEventListener('focus', (e) => {
                if (e.target.value.length >= 2) {
                    this.handleInput(e.target, dropdown, tableId);
                }
            });

            // Search button click
            if (searchBtn) {
                searchBtn.addEventListener('click', () => {
                    this.performSearch(input.value, tableId);
                });
            }

            // Close dropdown when clicking outside
            document.addEventListener('click', (e) => {
                if (!input.contains(e.target) && !dropdown.contains(e.target)) {
                    this.hideDropdown(dropdown);
                }
            });
        },

        extractTableData(tableId, table) {
            const rows = table.querySelectorAll('tbody tr');
            const data = [];

            rows.forEach((row, rowIndex) => {
                const cells = row.querySelectorAll('td');
                const rowData = {
                    rowIndex: rowIndex,
                    rowElement: row,
                    cells: []
                };

                cells.forEach((cell, cellIndex) => {
                    // Get text from cell, excluding hidden inputs and buttons
                    let text = '';

                    // Try to get value from input/select/textarea
                    const input = cell.querySelector('input:not([type="hidden"]), select, textarea');
                    if (input) {
                        text = input.value || input.textContent || '';
                    } else {
                        // Get visible text only
                        text = cell.textContent.trim();
                    }

                    if (text) {
                        rowData.cells.push({
                            cellIndex: cellIndex,
                            text: text,
                            element: cell
                        });
                    }
                });

                data.push(rowData);
            });

            this.tableData.set(tableId, data);
        },

        handleInput(input, dropdown, tableId) {
            const query = input.value.trim();

            if (query.length < 2) {
                this.hideDropdown(dropdown);
                return;
            }

            this.currentInput = input;
            this.currentDropdown = dropdown;
            this.currentTable = tableId;

            // Build suggestions
            this.suggestions = this.buildSuggestions(query, tableId);

            if (this.suggestions.length > 0) {
                this.showDropdown(dropdown, this.suggestions, query);
            } else {
                this.hideDropdown(dropdown);
            }
        },

        buildSuggestions(query, tableId) {
            const data = this.tableData.get(tableId);
            if (!data) return [];

            const lowerQuery = query.toLowerCase();
            const suggestions = [];
            const seenTexts = new Set();

            data.forEach(row => {
                row.cells.forEach(cell => {
                    const lowerText = cell.text.toLowerCase();

                    if (lowerText.includes(lowerQuery) && !seenTexts.has(lowerText)) {
                        suggestions.push({
                            text: cell.text,
                            rowIndex: row.rowIndex,
                            rowElement: row.rowElement,
                            cellIndex: cell.cellIndex,
                            cellElement: cell.element
                        });
                        seenTexts.add(lowerText);
                    }
                });
            });

            // Limit to 10 suggestions
            return suggestions.slice(0, 10);
        },

        showDropdown(dropdown, suggestions, query) {
            const html = suggestions.map((suggestion, index) => `
                <div class="autocomplete-item ${index === this.selectedIndex ? 'active' : ''}"
                     data-index="${index}">
                    ${highlightText(suggestion.text, query)}
                </div>
            `).join('');

            dropdown.innerHTML = html;

            // Position dropdown using fixed positioning to escape overflow clipping
            this.positionDropdown(dropdown);

            dropdown.style.display = 'block';

            // Add click handlers
            dropdown.querySelectorAll('.autocomplete-item').forEach((item, index) => {
                item.addEventListener('click', () => {
                    this.selectSuggestion(index);
                });
            });
        },

        positionDropdown(dropdown) {
            // Get input element that triggered this dropdown
            const input = this.currentInput;
            if (!input) return;

            // Get input's position relative to viewport
            const rect = input.getBoundingClientRect();

            // Position dropdown below input
            dropdown.style.top = (rect.bottom) + 'px';
            dropdown.style.left = rect.left + 'px';
            dropdown.style.width = rect.width + 'px';
        },

        hideDropdown(dropdown) {
            dropdown.style.display = 'none';
            dropdown.innerHTML = '';
            this.selectedIndex = -1;
        },

        handleKeydown(e, dropdown, tableId) {
            const items = dropdown.querySelectorAll('.autocomplete-item');

            switch(e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    this.selectedIndex = Math.min(this.selectedIndex + 1, items.length - 1);
                    this.updateSelection(items);
                    break;

                case 'ArrowUp':
                    e.preventDefault();
                    this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                    this.updateSelection(items);
                    break;

                case 'Enter':
                    e.preventDefault();
                    if (this.selectedIndex >= 0 && this.suggestions[this.selectedIndex]) {
                        this.selectSuggestion(this.selectedIndex);
                    } else {
                        // Perform search
                        this.performSearch(e.target.value, tableId);
                    }
                    break;

                case 'Escape':
                    this.hideDropdown(dropdown);
                    break;
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

        selectSuggestion(index) {
            const suggestion = this.suggestions[index];
            if (!suggestion) return;

            // Update input
            if (this.currentInput) {
                this.currentInput.value = suggestion.text;
            }

            // Hide dropdown
            if (this.currentDropdown) {
                this.hideDropdown(this.currentDropdown);
            }

            // Jump to row
            this.jumpToRow(suggestion.rowElement);
        },

        jumpToRow(rowElement) {
            if (!rowElement) return;

            // Remove previous highlights
            document.querySelectorAll('.row-highlighted').forEach(el => {
                el.classList.remove('row-highlighted');
            });

            // Add highlight
            rowElement.classList.add('row-highlighted');

            // Scroll into view
            rowElement.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });

            // Remove highlight after 3 seconds
            setTimeout(() => {
                rowElement.classList.remove('row-highlighted');
            }, 3000);

            showToast('Baris ditemukan dan di-highlight', 'info');
        },

        performSearch(query, tableId) {
            const table = document.getElementById(tableId);
            if (!table) return;

            const tbody = table.querySelector('tbody');
            const rows = tbody.querySelectorAll('tr');

            if (!query || query.length < 1) {
                // Clear search filter, then re-apply row limit
                rows.forEach(row => {
                    row.removeAttribute('data-search-hidden');
                });
                this.showAllRows(tableId);
                return;
            }

            const lowerQuery = query.toLowerCase();
            let matchCount = 0;

            // Mark rows as search-hidden or search-visible
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(lowerQuery)) {
                    row.removeAttribute('data-search-hidden');
                    matchCount++;
                } else {
                    row.setAttribute('data-search-hidden', 'true');
                    row.style.display = 'none';
                }
            });

            // Re-apply row limit on search results
            if (window.rowLimitModule) {
                rowLimitModule.applyRowLimit(table, rowLimitModule.getCurrentLimit(tableId));
            }

            showToast(`Ditemukan ${matchCount} baris yang cocok`, 'success');

            // Hide dropdown
            if (this.currentDropdown) {
                this.hideDropdown(this.currentDropdown);
            }
        },

        showAllRows(tableId) {
            const table = document.getElementById(tableId);
            if (!table) return;

            const tbody = table.querySelector('tbody');
            const rows = tbody.querySelectorAll('tr');

            // Clear search hidden attributes
            rows.forEach(row => {
                row.removeAttribute('data-search-hidden');
            });

            // Re-apply row limit
            if (window.rowLimitModule) {
                rowLimitModule.applyRowLimit(table, rowLimitModule.getCurrentLimit(tableId));
            }
        }
    };

    // =====================================================
    // BULK DELETE MODULE
    // =====================================================

    const bulkDeleteModule = {
        modal: null,
        previewData: null,

        init() {
            const modalElement = document.getElementById('modalBulkDelete');
            if (!modalElement) return;

            this.modal = new bootstrap.Modal(modalElement);

            const btnBulkDelete = document.getElementById('btnBulkDelete');
            if (btnBulkDelete) {
                btnBulkDelete.addEventListener('click', () => this.openModal());
            }

            const btnPreview = document.getElementById('btnPreviewDelete');
            if (btnPreview) {
                btnPreview.addEventListener('click', () => this.loadPreview());
            }

            const btnConfirm = document.getElementById('btnConfirmDelete');
            if (btnConfirm) {
                btnConfirm.addEventListener('click', () => this.executeDelete());
            }

            modalElement.addEventListener('hidden.bs.modal', () => {
                this.reset();
            });
        },

        openModal() {
            this.reset();
            this.modal.show();
        },

        reset() {
            const form = document.getElementById('formBulkDelete');
            if (form) form.reset();

            const preview = document.getElementById('deletePreview');
            if (preview) preview.classList.add('d-none');

            const btnConfirm = document.getElementById('btnConfirmDelete');
            if (btnConfirm) btnConfirm.classList.add('d-none');

            const btnPreview = document.getElementById('btnPreviewDelete');
            if (btnPreview) btnPreview.classList.remove('d-none');

            this.previewData = null;
        },

        async loadPreview() {
            const sumber = document.getElementById('deleteSumber')?.value.trim() || '';
            const sourceFile = document.getElementById('deleteSourceFile')?.value.trim() || '';

            if (!sumber && !sourceFile) {
                showToast('Pilih minimal satu filter (Sumber atau File Sumber)', 'warning');
                return;
            }

            const btnPreview = document.getElementById('btnPreviewDelete');
            const originalText = btnPreview.innerHTML;
            btnPreview.disabled = true;
            btnPreview.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Loading...';

            try {
                const params = new URLSearchParams();
                if (sumber) params.append('sumber', sumber);
                if (sourceFile) params.append('source_file', sourceFile);

                const response = await fetch(`${config.deletePreviewUrl}?${params.toString()}`, {
                    credentials: 'same-origin'
                });

                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.error || 'Gagal memuat preview');
                }

                const data = await response.json();
                this.previewData = data.preview;
                this.renderPreview(data.preview);

            } catch (error) {
                showToast(error.message, 'danger');
            } finally {
                btnPreview.disabled = false;
                btnPreview.innerHTML = originalText;
            }
        },

        renderPreview(preview) {
            const previewDiv = document.getElementById('deletePreview');
            const contentList = document.getElementById('deletePreviewContent');

            if (preview.jobs_count === 0) {
                contentList.innerHTML = `
                    <li class="list-group-item">
                        <i class="bi bi-info-circle text-info"></i>
                        Tidak ada data yang cocok dengan filter ini.
                    </li>
                `;
                previewDiv.classList.remove('d-none');
                return;
            }

            let html = `
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-briefcase text-primary"></i> Pekerjaan AHSP</span>
                    <span class="badge bg-danger">${preview.jobs_count.toLocaleString()}</span>
                </li>
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    <span><i class="bi bi-list-ul text-info"></i> Rincian Item</span>
                    <span class="badge bg-danger">${preview.rincian_count.toLocaleString()}</span>
                </li>
            `;

            if (preview.affected_sources.length > 0) {
                html += `
                    <li class="list-group-item">
                        <strong>Sumber terdampak:</strong><br>
                        <small class="text-muted">${preview.affected_sources.join(', ')}</small>
                    </li>
                `;
            }

            contentList.innerHTML = html;
            previewDiv.classList.remove('d-none');

            document.getElementById('btnConfirmDelete')?.classList.remove('d-none');
            document.getElementById('btnPreviewDelete')?.classList.add('d-none');
        },

        async executeDelete() {
            if (!this.previewData) {
                showToast('Harap lakukan preview terlebih dahulu', 'warning');
                return;
            }

            if (!confirm(`Anda yakin ingin menghapus ${this.previewData.jobs_count} pekerjaan dan ${this.previewData.rincian_count} rincian?\n\nOperasi ini TIDAK DAPAT dibatalkan!`)) {
                return;
            }

            const sumber = document.getElementById('deleteSumber')?.value.trim() || '';
            const sourceFile = document.getElementById('deleteSourceFile')?.value.trim() || '';

            const btnConfirm = document.getElementById('btnConfirmDelete');
            const originalText = btnConfirm.innerHTML;
            btnConfirm.disabled = true;
            btnConfirm.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Menghapus...';

            try {
                const response = await fetch(config.deleteExecuteUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        sumber: sumber,
                        source_file: sourceFile,
                        confirm: true
                    })
                });

                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.error || 'Gagal menghapus data');
                }

                const data = await response.json();
                showToast(
                    `✅ Berhasil menghapus ${data.result.jobs_deleted} pekerjaan dan ${data.result.rincian_deleted} rincian`,
                    'success'
                );

                this.modal.hide();
                setTimeout(() => window.location.reload(), 1000);

            } catch (error) {
                showToast(error.message, 'danger');
                btnConfirm.disabled = false;
                btnConfirm.innerHTML = originalText;
            }
        }
    };

    // =====================================================
    // TABLE SORTING MODULE
    // =====================================================

    const tableSortModule = {
        currentSort: { column: null, direction: 'asc' },

        init() {
            this.initTableSort('tableJobs');
            this.initTableSort('tableItems');
        },

        initTableSort(tableId) {
            const table = document.getElementById(tableId);
            if (!table) return;

            const headers = table.querySelectorAll('th.sortable');
            headers.forEach(header => {
                header.style.cursor = 'pointer';
                header.addEventListener('click', () => {
                    const sortKey = header.dataset.sort;
                    this.sortTable(table, sortKey);
                });
            });
        },

        sortTable(table, sortKey) {
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));

            if (this.currentSort.column === sortKey) {
                this.currentSort.direction = this.currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                this.currentSort.column = sortKey;
                this.currentSort.direction = 'asc';
            }

            rows.sort((a, b) => {
                const aValue = this.getCellValue(a, sortKey);
                const bValue = this.getCellValue(b, sortKey);

                if (aValue === bValue) return 0;
                const result = aValue > bValue ? 1 : -1;
                return this.currentSort.direction === 'asc' ? result : -result;
            });

            rows.forEach(row => tbody.appendChild(row));
            this.updateSortIndicators(table, sortKey);
        },

        getCellValue(row, sortKey) {
            const table = row.closest('table');
            const headers = table.querySelectorAll('th.sortable');
            let colIndex = -1;

            headers.forEach((header, index) => {
                if (header.dataset.sort === sortKey) colIndex = index;
            });

            if (colIndex === -1) return '';

            const cell = row.cells[colIndex];
            if (!cell) return '';

            const input = cell.querySelector('input, select, textarea');
            if (input) return (input.value || '').toLowerCase();

            return (cell.textContent || '').trim().toLowerCase();
        },

        updateSortIndicators(table, sortKey) {
            const headers = table.querySelectorAll('th.sortable');
            headers.forEach(header => {
                const icon = header.querySelector('i');
                if (!icon) return;

                if (header.dataset.sort === sortKey) {
                    icon.className = this.currentSort.direction === 'asc'
                        ? 'bi bi-arrow-up text-primary'
                        : 'bi bi-arrow-down text-primary';
                } else {
                    icon.className = 'bi bi-arrow-down-up text-muted';
                }
            });
        }
    };

    // =====================================================
    // CHANGE TRACKING MODULE
    // =====================================================

    const changeTrackingModule = {
        originalValues: new Map(),
        changedFields: new Map(),
        saveModal: null,
        currentForm: null,

        init() {
            this.captureInitialState();

            // Initialize save confirmation modal
            const modalElement = document.getElementById('modalSaveConfirmation');
            if (modalElement) {
                this.saveModal = new bootstrap.Modal(modalElement);

                const btnConfirm = document.getElementById('btnConfirmSave');
                if (btnConfirm) {
                    btnConfirm.addEventListener('click', () => this.confirmSave());
                }
            }

            document.querySelectorAll('.ahsp-database-table input, .ahsp-database-table select, .ahsp-database-table textarea').forEach(input => {
                input.addEventListener('change', (e) => this.trackChange(e.target));
                input.addEventListener('input', (e) => this.trackChange(e.target));
            });

            const forms = document.querySelectorAll('form[method="post"]');
            forms.forEach(form => {
                if (form.id === 'formBulkDelete') return;
                form.addEventListener('submit', (e) => this.handleSubmit(e, form));
            });
        },

        captureInitialState() {
            document.querySelectorAll('.ahsp-database-table input, .ahsp-database-table select, .ahsp-database-table textarea').forEach(input => {
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
            const saveBtns = document.querySelectorAll('.card-header button[type="submit"]');
            saveBtns.forEach(btn => {
                const btnText = btn.textContent.toLowerCase();
                if (!btnText.includes('simpan') && !btnText.includes('save')) return;

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

        showSaveModal() {
            const changeCount = this.changedFields.size;

            // Update count
            document.getElementById('saveChangeCount').textContent = changeCount;

            // Build changes list (show first 10)
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
                        <i class="bi bi-pencil-square text-primary"></i>
                        <strong>${change.label}</strong>
                        <div class="ms-4 mt-1 small">
                            <span class="badge bg-danger-subtle text-danger text-decoration-line-through">${oldVal}</span>
                            <i class="bi bi-arrow-right mx-2"></i>
                            <span class="badge bg-success-subtle text-success">${newVal}</span>
                        </div>
                    </li>
                `;
                count++;
            }

            html += '</ul>';
            changesList.innerHTML = html;

            // Show modal
            if (this.saveModal) {
                this.saveModal.show();
            }
        },

        confirmSave() {
            if (this.saveModal) {
                this.saveModal.hide();
            }

            // Submit the form
            if (this.currentForm) {
                // Remove event listener temporarily to allow actual submit
                const clonedForm = this.currentForm.cloneNode(true);
                this.currentForm.parentNode.replaceChild(clonedForm, this.currentForm);
                clonedForm.submit();
            }
        }
    };

    // =====================================================
    // ROW LIMIT CONTROLLER MODULE
    // =====================================================

    const rowLimitModule = {
        limits: new Map(), // Store current limits per table

        init() {
            this.initRowLimit('rowLimitJobs', 'tableJobs');
            this.initRowLimit('rowLimitItems', 'tableItems');
        },

        initRowLimit(selectId, tableId) {
            const select = document.getElementById(selectId);
            const table = document.getElementById(tableId);

            if (!select || !table) return;

            // Load saved preference from localStorage
            const savedLimit = localStorage.getItem(`${tableId}_rowLimit`);
            if (savedLimit) {
                select.value = savedLimit;
            }

            // Store initial limit
            this.limits.set(tableId, parseInt(select.value));

            // Apply initial limit
            this.applyRowLimit(table, parseInt(select.value));

            // Listen for changes
            select.addEventListener('change', (e) => {
                const limit = parseInt(e.target.value);
                this.limits.set(tableId, limit);
                this.applyRowLimit(table, limit);
                localStorage.setItem(`${tableId}_rowLimit`, limit);
                showToast(`Tampilan diubah ke ${limit} baris`, 'success');
            });
        },

        applyRowLimit(table, limit) {
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));

            // First pass: Clear row-limit attributes and restore rows
            rows.forEach(row => {
                row.classList.remove('row-limit-hidden');
                row.removeAttribute('data-row-limit-hidden');

                // Only restore if not hidden by search
                if (!row.hasAttribute('data-search-hidden')) {
                    row.style.display = '';
                }
            });

            // Second pass: Apply new limit, only count non-search-hidden rows
            let visibleCount = 0;
            rows.forEach((row) => {
                // Check if row is hidden by search
                const isSearchHidden = row.hasAttribute('data-search-hidden');

                if (!isSearchHidden) {
                    // This row is visible from search perspective
                    if (visibleCount < limit) {
                        // Show this row
                        row.style.display = '';
                        row.removeAttribute('data-row-limit-hidden');
                    } else {
                        // Hide this row due to limit
                        row.style.display = 'none';
                        row.setAttribute('data-row-limit-hidden', 'true');
                    }
                    visibleCount++;
                }
            });
        },

        getCurrentLimit(tableId) {
            return this.limits.get(tableId) || 50;
        }
    };

    // =====================================================
    // COLUMN VISIBILITY TOGGLE MODULE
    // =====================================================

    const columnVisibilityModule = {
        modal: null,

        init() {
            const modalElement = document.getElementById('modalColumnToggle');
            if (!modalElement) return;

            this.modal = new bootstrap.Modal(modalElement);

            // Initialize for both tables
            this.initTable('tableJobs', 'btnColumnToggleJobs');
            this.initTable('tableItems', 'btnColumnToggleItems');

            // Reset button
            const btnReset = document.getElementById('btnResetColumns');
            if (btnReset) {
                btnReset.addEventListener('click', () => this.resetColumns());
            }
        },

        initTable(tableId, btnId) {
            const table = document.getElementById(tableId);
            const btn = document.getElementById(btnId);

            if (!table || !btn) return;

            btn.addEventListener('click', () => {
                this.currentTableId = tableId;
                this.openModal(table);
            });

            // Load saved column visibility
            this.loadColumnVisibility(table);
        },

        openModal(table) {
            const headers = table.querySelectorAll('thead th');
            const list = document.getElementById('columnToggleList');

            let html = '';
            headers.forEach((header, index) => {
                const columnName = header.textContent.trim() || `Kolom ${index + 1}`;
                const isVisible = !header.classList.contains('column-hidden');
                const isCheckbox = header.querySelector('input[type="checkbox"]');

                // Skip checkbox column
                if (isCheckbox) return;

                html += `
                    <div class="list-group-item">
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox"
                                   id="col_${index}"
                                   data-col-index="${index}"
                                   ${isVisible ? 'checked' : ''}>
                            <label class="form-check-label" for="col_${index}">
                                ${columnName}
                            </label>
                        </div>
                    </div>
                `;
            });

            list.innerHTML = html;

            // Add change listeners
            list.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
                checkbox.addEventListener('change', (e) => {
                    const colIndex = parseInt(e.target.dataset.colIndex);
                    this.toggleColumn(table, colIndex, e.target.checked);
                });
            });

            this.modal.show();
        },

        toggleColumn(table, colIndex, show) {
            const headers = table.querySelectorAll('thead th');
            const rows = table.querySelectorAll('tbody tr');

            // Toggle header
            if (headers[colIndex]) {
                if (show) {
                    headers[colIndex].classList.remove('column-hidden');
                } else {
                    headers[colIndex].classList.add('column-hidden');
                }
            }

            // Toggle cells
            rows.forEach(row => {
                const cell = row.cells[colIndex];
                if (cell) {
                    if (show) {
                        cell.classList.remove('column-hidden');
                    } else {
                        cell.classList.add('column-hidden');
                    }
                }
            });

            // Save to localStorage
            this.saveColumnVisibility(table);
        },

        saveColumnVisibility(table) {
            const tableId = table.id;
            const headers = table.querySelectorAll('thead th');
            const hiddenColumns = [];

            headers.forEach((header, index) => {
                if (header.classList.contains('column-hidden')) {
                    hiddenColumns.push(index);
                }
            });

            localStorage.setItem(`${tableId}_hiddenColumns`, JSON.stringify(hiddenColumns));
        },

        loadColumnVisibility(table) {
            const tableId = table.id;
            const saved = localStorage.getItem(`${tableId}_hiddenColumns`);

            if (!saved) return;

            try {
                const hiddenColumns = JSON.parse(saved);
                hiddenColumns.forEach(colIndex => {
                    this.toggleColumn(table, colIndex, false);
                });
            } catch (e) {
                console.error('Error loading column visibility:', e);
            }
        },

        resetColumns() {
            if (!this.currentTableId) return;

            const table = document.getElementById(this.currentTableId);
            if (!table) return;

            const headers = table.querySelectorAll('thead th');
            const rows = table.querySelectorAll('tbody tr');

            // Show all columns
            headers.forEach((header, index) => {
                header.classList.remove('column-hidden');
                rows.forEach(row => {
                    const cell = row.cells[index];
                    if (cell) cell.classList.remove('column-hidden');
                });
            });

            // Update checkboxes in modal
            const checkboxes = document.querySelectorAll('#columnToggleList input[type="checkbox"]');
            checkboxes.forEach(checkbox => {
                checkbox.checked = true;
            });

            // Clear localStorage
            localStorage.removeItem(`${this.currentTableId}_hiddenColumns`);

            showToast('Semua kolom ditampilkan', 'success');
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
            this.initTable('tableJobs');
            this.initTable('tableItems');
        },

        initTable(tableId) {
            const table = document.getElementById(tableId);
            if (!table) return;

            const headers = table.querySelectorAll('thead th');

            headers.forEach((header, index) => {
                // Skip last column (actions)
                if (index === headers.length - 1) return;

                // Create resizer element
                const resizer = document.createElement('div');
                resizer.className = 'column-resizer';
                header.appendChild(resizer);

                // Add mouse events
                resizer.addEventListener('mousedown', (e) => {
                    this.startResize(e, header, resizer);
                });
            });

            // Global mouse events
            document.addEventListener('mousemove', (e) => {
                if (this.isResizing) {
                    this.doResize(e);
                }
            });

            document.addEventListener('mouseup', () => {
                if (this.isResizing) {
                    this.stopResize();
                }
            });

            // Load saved widths
            this.loadColumnWidths(table);
        },

        startResize(e, header, resizer) {
            e.preventDefault();
            e.stopPropagation();

            this.isResizing = true;
            this.currentResizer = resizer;
            this.currentColumn = header;
            this.startX = e.pageX;
            this.startWidth = header.offsetWidth;

            // Visual feedback
            document.body.classList.add('column-resizing');
            resizer.classList.add('resizing');
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
            const table = this.currentColumn.closest('table');
            this.saveColumnWidths(table);

            this.currentResizer = null;
            this.currentColumn = null;
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
    // INITIALIZATION
    // =====================================================

    document.addEventListener('DOMContentLoaded', function() {
        autocompleteModule.init();
        bulkDeleteModule.init();
        tableSortModule.init();
        changeTrackingModule.init();
        rowLimitModule.init();
        columnVisibilityModule.init();
        resizableColumnsModule.init();
    });

})();
