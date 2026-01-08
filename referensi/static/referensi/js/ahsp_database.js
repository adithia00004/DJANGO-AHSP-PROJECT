/**
 * AHSP Database Management JavaScript
 * Handles: Bulk Delete, Table Sorting, Change Tracking, Save Confirmation
 */

(function () {
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

    // =====================================================
    // QUICK SEARCH FUNCTIONALITY
    // =====================================================

    const quickSearchModule = {
        init() {
            // Jobs table search
            const searchJobsInput = document.getElementById('quickSearchJobs');
            const clearJobsBtn = document.getElementById('btnClearSearchJobs');
            if (searchJobsInput) {
                searchJobsInput.addEventListener('input', (e) => {
                    this.filterTable('tableJobs', e.target.value);
                });
            }
            if (clearJobsBtn) {
                clearJobsBtn.addEventListener('click', () => {
                    searchJobsInput.value = '';
                    this.filterTable('tableJobs', '');
                });
            }

            // Items table search
            const searchItemsInput = document.getElementById('quickSearchItems');
            const clearItemsBtn = document.getElementById('btnClearSearchItems');
            if (searchItemsInput) {
                searchItemsInput.addEventListener('input', (e) => {
                    this.filterTable('tableItems', e.target.value);
                });
            }
            if (clearItemsBtn) {
                clearItemsBtn.addEventListener('click', () => {
                    searchItemsInput.value = '';
                    this.filterTable('tableItems', '');
                });
            }
        },

        filterTable(tableId, query) {
            const table = document.getElementById(tableId);
            if (!table) return;

            const tbody = table.querySelector('tbody');
            const rows = tbody.querySelectorAll('tr');
            const lowerQuery = query.toLowerCase();
            let visibleCount = 0;

            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(lowerQuery)) {
                    row.style.display = '';
                    visibleCount++;
                } else {
                    row.style.display = 'none';
                }
            });

            // Show count (optional)
            console.log(`Showing ${visibleCount} of ${rows.length} rows`);
        }
    };

    // =====================================================
    // 1. BULK DELETE FUNCTIONALITY
    // =====================================================

    const bulkDeleteModule = {
        modal: null,
        previewData: null,

        init() {
            this.modal = new bootstrap.Modal(document.getElementById('modalBulkDelete'));

            // Open modal button
            const btnBulkDelete = document.getElementById('btnBulkDelete');
            if (btnBulkDelete) {
                btnBulkDelete.addEventListener('click', () => this.openModal());
            }

            // Preview button
            const btnPreview = document.getElementById('btnPreviewDelete');
            if (btnPreview) {
                btnPreview.addEventListener('click', () => this.loadPreview());
            }

            // Confirm delete button
            const btnConfirm = document.getElementById('btnConfirmDelete');
            if (btnConfirm) {
                btnConfirm.addEventListener('click', () => this.executeDelete());
            }

            // Reset on modal close
            document.getElementById('modalBulkDelete').addEventListener('hidden.bs.modal', () => {
                this.reset();
            });
        },

        openModal() {
            this.reset();
            this.modal.show();
        },

        reset() {
            document.getElementById('formBulkDelete').reset();
            document.getElementById('deletePreview').classList.add('d-none');
            document.getElementById('btnConfirmDelete').classList.add('d-none');
            document.getElementById('btnPreviewDelete').classList.remove('d-none');
            this.previewData = null;
        },

        async loadPreview() {
            const sumber = document.getElementById('deleteSumber').value.trim();
            const sourceFile = document.getElementById('deleteSourceFile').value.trim();

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

            if (preview.affected_files.length > 0) {
                html += `
                    <li class="list-group-item">
                        <strong>File terdampak:</strong><br>
                        <small class="text-muted">${preview.affected_files.join(', ')}</small>
                    </li>
                `;
            }

            contentList.innerHTML = html;
            previewDiv.classList.remove('d-none');

            // Show confirm button
            document.getElementById('btnConfirmDelete').classList.remove('d-none');
            document.getElementById('btnPreviewDelete').classList.add('d-none');
        },

        async executeDelete() {
            if (!this.previewData) {
                showToast('Harap lakukan preview terlebih dahulu', 'warning');
                return;
            }

            if (!confirm(`Anda yakin ingin menghapus ${this.previewData.jobs_count} pekerjaan dan ${this.previewData.rincian_count} rincian?\n\nOperasi ini TIDAK DAPAT dibatalkan!`)) {
                return;
            }

            const sumber = document.getElementById('deleteSumber').value.trim();
            const sourceFile = document.getElementById('deleteSourceFile').value.trim();

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

                // Reload page after 1 second
                setTimeout(() => window.location.reload(), 1000);

            } catch (error) {
                showToast(error.message, 'danger');
                btnConfirm.disabled = false;
                btnConfirm.innerHTML = originalText;
            }
        }
    };

    // =====================================================
    // 2. TABLE SORTING FUNCTIONALITY
    // =====================================================

    const tableSortModule = {
        currentSort: {
            column: null,
            direction: 'asc'
        },

        init() {
            // Initialize sorting for both tables
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

            // Determine sort direction
            if (this.currentSort.column === sortKey) {
                this.currentSort.direction = this.currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                this.currentSort.column = sortKey;
                this.currentSort.direction = 'asc';
            }

            // Sort rows
            rows.sort((a, b) => {
                const aValue = this.getCellValue(a, sortKey);
                const bValue = this.getCellValue(b, sortKey);

                if (aValue === bValue) return 0;

                const result = aValue > bValue ? 1 : -1;
                return this.currentSort.direction === 'asc' ? result : -result;
            });

            // Re-append sorted rows
            rows.forEach(row => tbody.appendChild(row));

            // Update sort indicators
            this.updateSortIndicators(table, sortKey);
        },

        getCellValue(row, sortKey) {
            // Map sort keys to column indices
            const table = row.closest('table');
            const headers = table.querySelectorAll('th.sortable');
            let colIndex = -1;

            headers.forEach((header, index) => {
                if (header.dataset.sort === sortKey) {
                    colIndex = index;
                }
            });

            if (colIndex === -1) return '';

            const cell = row.cells[colIndex];
            if (!cell) return '';

            // Try to get value from input/select/textarea
            const input = cell.querySelector('input, select, textarea');
            if (input) {
                return (input.value || '').toLowerCase();
            }

            // Otherwise get text content
            return (cell.textContent || '').trim().toLowerCase();
        },

        updateSortIndicators(table, sortKey) {
            const headers = table.querySelectorAll('th.sortable');

            headers.forEach(header => {
                const icon = header.querySelector('i');
                if (!icon) return;

                if (header.dataset.sort === sortKey) {
                    // Active sort column
                    icon.className = this.currentSort.direction === 'asc'
                        ? 'bi bi-arrow-up text-primary'
                        : 'bi bi-arrow-down text-primary';
                } else {
                    // Inactive columns
                    icon.className = 'bi bi-arrow-down-up text-muted';
                }
            });
        }
    };

    // =====================================================
    // 3. CHANGE TRACKING & SAVE CONFIRMATION
    // =====================================================

    const changeTrackingModule = {
        originalValues: new Map(),
        changedFields: new Set(),

        init() {
            // Track initial values of all form inputs
            this.captureInitialState();

            // Listen for changes
            document.querySelectorAll('.ahsp-database-table input, .ahsp-database-table select, .ahsp-database-table textarea').forEach(input => {
                input.addEventListener('change', (e) => this.trackChange(e.target));
                input.addEventListener('input', (e) => this.trackChange(e.target));
            });

            // Intercept form submission
            const forms = document.querySelectorAll('form[method="post"]');
            forms.forEach(form => {
                // Skip bulk delete form
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

        trackChange(input) {
            const key = this.getFieldKey(input);
            const originalValue = this.originalValues.get(key);
            const currentValue = input.value;

            if (originalValue !== currentValue) {
                this.changedFields.add(key);
                input.classList.add('is-modified');
            } else {
                this.changedFields.delete(key);
                input.classList.remove('is-modified');
            }

            // Update save button state
            this.updateSaveButtonState();
        },

        updateSaveButtonState() {
            // Only target save buttons within card-footer (avoid logout button, etc.)
            const saveBtns = document.querySelectorAll('.card-footer button[type="submit"]');
            saveBtns.forEach(btn => {
                // Check if button contains save icon or text
                const btnText = btn.textContent.toLowerCase();
                if (!btnText.includes('simpan') && !btnText.includes('save')) {
                    return; // Skip buttons that are not save buttons
                }

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
            if (this.changedFields.size === 0) {
                e.preventDefault();
                showToast('Tidak ada perubahan untuk disimpan', 'info');
                return false;
            }

            // Show confirmation with change summary
            const changeCount = this.changedFields.size;
            const confirmed = confirm(
                `Anda akan menyimpan ${changeCount} perubahan.\n\n` +
                `Perubahan ini akan langsung tersimpan ke database.\n\n` +
                `Lanjutkan?`
            );

            if (!confirmed) {
                e.preventDefault();
                return false;
            }

            // Let form submit normally
            return true;
        },

        getChangeSummary() {
            const changes = [];
            this.changedFields.forEach(key => {
                const originalValue = this.originalValues.get(key);
                const input = document.querySelector(`[name="${key.split('_')[0]}"]`);
                if (input) {
                    changes.push({
                        field: key,
                        from: originalValue,
                        to: input.value
                    });
                }
            });
            return changes;
        }
    };

    // =====================================================
    // 4. INITIALIZATION
    // =====================================================

    document.addEventListener('DOMContentLoaded', function () {
        quickSearchModule.init();
        bulkDeleteModule.init();
        tableSortModule.init();
        changeTrackingModule.init();
    });

})();
