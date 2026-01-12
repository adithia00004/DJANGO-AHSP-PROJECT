/**
 * AHSP Database API-Based JavaScript
 * 
 * Performance-optimized implementation using:
 * - API-based data loading (no formsets)
 * - Client-side pagination
 * - Inline editing with PATCH requests
 * - Event delegation for minimal memory usage
 */

(function () {
    'use strict';

    // =====================================================
    // Configuration & State
    // =====================================================

    const config = window.AHSP_CONFIG || {};

    const state = {
        activeTab: 'jobs',
        currentPage: 1,
        pageSize: 20,
        sortField: 'kode_ahsp',
        sortOrder: 'asc',
        searchQuery: '',
        filterSumber: '',
        filterAnomalyOnly: false,
        data: [],
        totalCount: 0,
        totalPages: 0,
        isLoading: false,
    };

    // =====================================================
    // Utilities
    // =====================================================

    function debounce(func, wait) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    function showToast(message, type = 'success') {
        // Simple toast implementation
        const toast = document.createElement('div');
        toast.className = `alert alert-${type} position-fixed bottom-0 end-0 m-3 shadow-lg`;
        toast.style.zIndex = '9999';
        toast.innerHTML = `<i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i> ${message}`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    function formatNumber(num) {
        return new Intl.NumberFormat('id-ID').format(num);
    }

    // =====================================================
    // API Functions
    // =====================================================

    async function fetchData(endpoint, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': config.csrfToken,
            },
        };

        try {
            const response = await fetch(endpoint, { ...defaultOptions, ...options });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || 'Request failed');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    async function loadStats() {
        try {
            const result = await fetchData(config.apiUrls.stats);
            if (result.status === 'success') {
                document.getElementById('stat-jobs').textContent = formatNumber(result.data.jobs_count);
                document.getElementById('stat-items').textContent = formatNumber(result.data.items_count);
                document.getElementById('stat-anomalies').textContent = formatNumber(result.data.anomaly_count);
            }
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    async function loadData() {
        if (state.isLoading) return;

        state.isLoading = true;
        showLoading(true);

        try {
            const isJobs = state.activeTab === 'jobs';
            const baseUrl = isJobs ? config.apiUrls.listJobs : config.apiUrls.listItems;

            const params = new URLSearchParams({
                page: state.currentPage,
                page_size: state.pageSize,
                search: state.searchQuery,
                sort: state.sortField,
                order: state.sortOrder,
            });

            if (state.filterSumber) {
                params.append('sumber', state.filterSumber);
            }
            if (state.filterAnomalyOnly) {
                params.append('anomaly_only', '1');
            }

            const result = await fetchData(`${baseUrl}?${params.toString()}`);

            if (result.status === 'success') {
                state.data = result.data;
                state.totalCount = result.pagination.total_count;
                state.totalPages = result.pagination.total_pages;

                renderTable();
                renderPagination();
                updatePaginationInfo();
            }
        } catch (error) {
            showToast('Gagal memuat data: ' + error.message, 'danger');
        } finally {
            state.isLoading = false;
            showLoading(false);
        }
    }

    async function updateField(pk, field, value) {
        const isJobs = state.activeTab === 'jobs';
        const url = isJobs
            ? config.apiUrls.updateJob.replace('{pk}', pk)
            : config.apiUrls.updateItem.replace('{pk}', pk);

        try {
            const result = await fetchData(url, {
                method: 'PATCH',
                body: JSON.stringify({ field, value }),
            });

            if (result.status === 'success') {
                showToast('Berhasil disimpan');

                // Update local data
                const item = state.data.find(d => d.id === pk);
                if (item) {
                    item[field] = result.data.value;
                }

                // Re-render the affected row
                renderTable();

                return true;
            }
        } catch (error) {
            showToast('Gagal menyimpan: ' + error.message, 'danger');
        }

        return false;
    }

    // =====================================================
    // Rendering Functions
    // =====================================================

    function showLoading(show) {
        const loading = document.getElementById('loading-indicator');
        const tableJobs = document.getElementById('table-jobs');
        const tableItems = document.getElementById('table-items');
        const empty = document.getElementById('empty-state');

        if (show) {
            loading.classList.remove('d-none');
            tableJobs.classList.add('d-none');
            tableItems.classList.add('d-none');
            empty.classList.add('d-none');
        } else {
            loading.classList.add('d-none');
        }
    }

    function renderTable() {
        const isJobs = state.activeTab === 'jobs';
        const tableJobs = document.getElementById('table-jobs');
        const tableItems = document.getElementById('table-items');
        const empty = document.getElementById('empty-state');

        // Show correct table
        tableJobs.classList.toggle('d-none', !isJobs || state.data.length === 0);
        tableItems.classList.toggle('d-none', isJobs || state.data.length === 0);
        empty.classList.toggle('d-none', state.data.length > 0);

        if (state.data.length === 0) return;

        const tbody = document.getElementById(isJobs ? 'tbody-jobs' : 'tbody-items');
        tbody.innerHTML = state.data.map(item => isJobs ? renderJobRow(item) : renderItemRow(item)).join('');
    }

    function renderJobRow(job) {
        const anomalyBadge = job.has_anomaly
            ? `<span class="badge bg-warning-subtle text-warning-emphasis" title="${job.anomalies.join(', ')}"><i class="bi bi-exclamation-triangle"></i> ${job.anomalies.length}</span>`
            : `<span class="badge bg-success-subtle text-success-emphasis"><i class="bi bi-check-circle"></i> OK</span>`;

        return `
            <tr data-pk="${job.id}" class="${job.has_anomaly ? 'has-anomaly' : ''}">
                <td class="editable" data-field="kode_ahsp">${escapeHtml(job.kode_ahsp)}</td>
                <td class="editable" data-field="nama_ahsp">${escapeHtml(job.nama_ahsp)}</td>
                <td class="editable" data-field="klasifikasi">${escapeHtml(job.klasifikasi)}</td>
                <td class="editable" data-field="sub_klasifikasi">${escapeHtml(job.sub_klasifikasi)}</td>
                <td class="editable" data-field="satuan">${escapeHtml(job.satuan)}</td>
                <td class="editable" data-field="sumber">${escapeHtml(job.sumber)}</td>
                <td>
                    <div class="ahsp-rincian-badges">
                        <span class="badge bg-primary-subtle text-primary-emphasis" title="Tenaga Kerja">TK:${job.tk_count}</span>
                        <span class="badge bg-info-subtle text-info-emphasis" title="Bahan">BHN:${job.bhn_count}</span>
                        <span class="badge bg-secondary-subtle text-secondary-emphasis" title="Alat">ALT:${job.alt_count}</span>
                        ${job.lain_count > 0 ? `<span class="badge bg-dark-subtle text-dark-emphasis">+${job.lain_count}</span>` : ''}
                        <span class="badge bg-body-secondary text-body fw-semibold">Σ${job.rincian_count}</span>
                    </div>
                </td>
                <td>${anomalyBadge}</td>
            </tr>
        `;
    }

    function renderItemRow(item) {
        const anomalyBadge = item.has_anomaly
            ? `<span class="badge bg-warning-subtle text-warning-emphasis" title="${item.anomalies.join(', ')}"><i class="bi bi-exclamation-triangle"></i></span>`
            : `<span class="badge bg-success-subtle text-success-emphasis"><i class="bi bi-check-circle"></i></span>`;

        const kategoriBadgeClass = {
            'TK': 'bg-primary-subtle text-primary-emphasis',
            'BHN': 'bg-info-subtle text-info-emphasis',
            'ALT': 'bg-secondary-subtle text-secondary-emphasis',
            'LAIN': 'bg-dark-subtle text-dark-emphasis',
        }[item.kategori] || 'bg-secondary';

        return `
            <tr data-pk="${item.id}" class="${item.has_anomaly ? 'has-anomaly' : ''}">
                <td>
                    <div class="fw-semibold small">${escapeHtml(item.job_kode)}</div>
                    <div class="text-muted small text-truncate" style="max-width: 150px;" title="${escapeHtml(item.job_nama)}">${escapeHtml(item.job_nama)}</div>
                </td>
                <td class="editable" data-field="kategori" data-type="select">
                    <span class="badge ${kategoriBadgeClass}">${item.kategori}</span>
                </td>
                <td class="editable" data-field="kode_item">${escapeHtml(item.kode_item)}</td>
                <td class="editable" data-field="uraian_item">${escapeHtml(item.uraian_item)}</td>
                <td class="editable" data-field="satuan_item">${escapeHtml(item.satuan_item)}</td>
                <td class="editable text-end" data-field="koefisien" data-type="number">${item.koefisien}</td>
                <td>${anomalyBadge}</td>
            </tr>
        `;
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function renderPagination() {
        const container = document.getElementById('pagination-controls');

        if (state.totalPages <= 1) {
            container.innerHTML = '';
            return;
        }

        let html = '';

        // Previous button
        html += `<li class="page-item ${state.currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" data-page="${state.currentPage - 1}"><i class="bi bi-chevron-left"></i></a>
        </li>`;

        // Page numbers
        const maxVisible = 5;
        let startPage = Math.max(1, state.currentPage - Math.floor(maxVisible / 2));
        let endPage = Math.min(state.totalPages, startPage + maxVisible - 1);

        if (endPage - startPage < maxVisible - 1) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }

        if (startPage > 1) {
            html += `<li class="page-item"><a class="page-link" href="#" data-page="1">1</a></li>`;
            if (startPage > 2) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `<li class="page-item ${i === state.currentPage ? 'active' : ''}">
                <a class="page-link" href="#" data-page="${i}">${i}</a>
            </li>`;
        }

        if (endPage < state.totalPages) {
            if (endPage < state.totalPages - 1) {
                html += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
            }
            html += `<li class="page-item"><a class="page-link" href="#" data-page="${state.totalPages}">${state.totalPages}</a></li>`;
        }

        // Next button
        html += `<li class="page-item ${state.currentPage === state.totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" data-page="${state.currentPage + 1}"><i class="bi bi-chevron-right"></i></a>
        </li>`;

        container.innerHTML = html;
    }

    function updatePaginationInfo() {
        const info = document.getElementById('pagination-info');
        const start = (state.currentPage - 1) * state.pageSize + 1;
        const end = Math.min(state.currentPage * state.pageSize, state.totalCount);

        if (state.totalCount === 0) {
            info.textContent = 'Tidak ada data';
        } else {
            info.textContent = `${formatNumber(start)}-${formatNumber(end)} dari ${formatNumber(state.totalCount)}`;
        }
    }

    // =====================================================
    // Event Handlers
    // =====================================================

    function handleTabClick(e) {
        const tab = e.target.closest('[data-tab]');
        if (!tab) return;

        const newTab = tab.dataset.tab;
        if (newTab === state.activeTab) return;

        // Update UI
        document.querySelectorAll('[data-tab]').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        // Update state and reload
        state.activeTab = newTab;
        state.currentPage = 1;
        state.sortField = newTab === 'jobs' ? 'kode_ahsp' : 'ahsp__kode_ahsp';
        loadData();
    }

    function handleSearch() {
        state.searchQuery = document.getElementById('search-input').value.trim();
        state.currentPage = 1;
        loadData();
    }

    function handleSortClick(e) {
        const th = e.target.closest('th.sortable');
        if (!th) return;

        const field = th.dataset.sort;
        if (field === state.sortField) {
            state.sortOrder = state.sortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            state.sortField = field;
            state.sortOrder = 'asc';
        }

        // Update sort indicators
        document.querySelectorAll('th.sortable i').forEach(icon => {
            icon.className = 'bi bi-arrow-down-up text-muted';
        });
        const icon = th.querySelector('i');
        icon.className = state.sortOrder === 'asc' ? 'bi bi-arrow-up' : 'bi bi-arrow-down';

        loadData();
    }

    function handlePageClick(e) {
        e.preventDefault();
        const link = e.target.closest('[data-page]');
        if (!link || link.parentElement.classList.contains('disabled')) return;

        state.currentPage = parseInt(link.dataset.page, 10);
        loadData();
    }

    function handlePageSizeChange(e) {
        state.pageSize = parseInt(e.target.value, 10);
        state.currentPage = 1;
        loadData();
    }

    function handleFilterSumberChange(e) {
        state.filterSumber = e.target.value;
        state.currentPage = 1;
        loadData();
    }

    function handleFilterAnomalyToggle(e) {
        const btn = e.target.closest('.btn-filter');
        if (!btn) return;

        state.filterAnomalyOnly = !state.filterAnomalyOnly;
        btn.classList.toggle('active', state.filterAnomalyOnly);
        state.currentPage = 1;
        loadData();
    }

    function handleCellClick(e) {
        const cell = e.target.closest('td.editable');
        if (!cell) return;

        const row = cell.closest('tr');
        const pk = parseInt(row.dataset.pk, 10);
        const field = cell.dataset.field;
        const type = cell.dataset.type || 'text';
        const currentValue = state.data.find(d => d.id === pk)?.[field] || '';

        openEditModal(pk, field, type, currentValue);
    }

    function openEditModal(pk, field, type, value) {
        const modal = document.getElementById('edit-modal');
        const title = document.getElementById('edit-modal-title');
        const container = document.getElementById('edit-input-container');

        document.getElementById('edit-pk').value = pk;
        document.getElementById('edit-field').value = field;
        document.getElementById('edit-type').value = type;

        // Set title
        const fieldLabels = {
            'kode_ahsp': 'Kode AHSP',
            'nama_ahsp': 'Nama Pekerjaan',
            'klasifikasi': 'Klasifikasi',
            'sub_klasifikasi': 'Sub-klasifikasi',
            'satuan': 'Satuan',
            'sumber': 'Sumber',
            'source_file': 'File Sumber',
            'kategori': 'Kategori',
            'kode_item': 'Kode Item',
            'uraian_item': 'Uraian',
            'satuan_item': 'Satuan',
            'koefisien': 'Koefisien',
        };
        title.textContent = `Edit ${fieldLabels[field] || field}`;

        // Create appropriate input
        let html = '';
        if (type === 'select' && field === 'kategori') {
            html = `<select class="form-select" id="edit-value">
                <option value="TK" ${value === 'TK' ? 'selected' : ''}>TK - Tenaga Kerja</option>
                <option value="BHN" ${value === 'BHN' ? 'selected' : ''}>BHN - Bahan</option>
                <option value="ALT" ${value === 'ALT' ? 'selected' : ''}>ALT - Alat</option>
                <option value="LAIN" ${value === 'LAIN' ? 'selected' : ''}>LAIN - Lainnya</option>
            </select>`;
        } else if (type === 'number') {
            html = `<input type="text" class="form-control" id="edit-value" value="${escapeHtml(value)}" inputmode="decimal">`;
        } else if (field === 'nama_ahsp' || field === 'uraian_item') {
            html = `<textarea class="form-control" id="edit-value" rows="3">${escapeHtml(value)}</textarea>`;
        } else {
            html = `<input type="text" class="form-control" id="edit-value" value="${escapeHtml(value)}">`;
        }
        container.innerHTML = html;

        // Show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();

        // Focus input
        setTimeout(() => {
            const input = document.getElementById('edit-value');
            input.focus();
            if (input.select) input.select();
        }, 200);
    }

    async function handleSaveEdit() {
        const pk = parseInt(document.getElementById('edit-pk').value, 10);
        const field = document.getElementById('edit-field').value;
        const value = document.getElementById('edit-value').value;

        const success = await updateField(pk, field, value);

        if (success) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('edit-modal'));
            modal.hide();
        }
    }

    // =====================================================
    // Initialization
    // =====================================================

    function init() {
        // Load initial data
        loadStats();
        loadData();

        // Tab navigation
        document.getElementById('database-tabs').addEventListener('click', handleTabClick);

        // Search
        const searchInput = document.getElementById('search-input');
        searchInput.addEventListener('input', debounce(handleSearch, 300));
        searchInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') handleSearch();
        });
        document.getElementById('btn-search').addEventListener('click', handleSearch);

        // Sorting (event delegation on table)
        document.getElementById('table-jobs').addEventListener('click', handleSortClick);
        document.getElementById('table-items').addEventListener('click', handleSortClick);

        // Cell click for editing (event delegation)
        document.getElementById('tbody-jobs').addEventListener('click', handleCellClick);
        document.getElementById('tbody-items').addEventListener('click', handleCellClick);

        // Pagination
        document.getElementById('pagination-controls').addEventListener('click', handlePageClick);
        document.getElementById('page-size').addEventListener('change', handlePageSizeChange);

        // Filters
        document.getElementById('filter-sumber').addEventListener('change', handleFilterSumberChange);
        document.getElementById('filter-anomaly').addEventListener('click', handleFilterAnomalyToggle);

        // Edit modal save
        document.getElementById('btn-save-edit').addEventListener('click', handleSaveEdit);

        // Enter key in edit modal
        document.getElementById('edit-modal').addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSaveEdit();
            }
        });

        // Bulk delete
        document.getElementById('btn-bulk-delete')?.addEventListener('click', () => {
            const modal = new bootstrap.Modal(document.getElementById('modalBulkDelete'));
            modal.show();
        });
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
