/**
 * UX Enhancements for Dashboard
 * Professional Corporate Design System
 *
 * Features:
 * - Floating Action Button (FAB)
 * - Quick Search with keyboard shortcuts
 * - Filter Pills interaction
 * - Active Filters display
 * - Toast notifications
 * - Smooth scrolling
 */

(function() {
  'use strict';

  // ============================================================================
  // 1. FLOATING ACTION BUTTON (FAB)
  // ============================================================================

  function initFAB() {
    const fabMainBtn = document.getElementById('fabMainBtn');
    const fabMenu = document.getElementById('fabMenu');
    const fabIcon = fabMainBtn?.querySelector('.fab-icon');
    let isOpen = false;

    if (!fabMainBtn || !fabMenu) return;

    // Toggle FAB menu
    fabMainBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      isOpen = !isOpen;

      if (isOpen) {
        fabMenu.classList.add('active');
        fabIcon.classList.replace('bi-plus-lg', 'bi-x-lg');
        fabMainBtn.classList.add('fab-open');
      } else {
        closeFABMenu();
      }
    });

    // Close FAB menu
    function closeFABMenu() {
      fabMenu.classList.remove('active');
      fabIcon.classList.replace('bi-x-lg', 'bi-plus-lg');
      fabMainBtn.classList.remove('fab-open');
      isOpen = false;
    }

    // Close on outside click
    document.addEventListener('click', function(e) {
      if (isOpen && !fabMainBtn.contains(e.target) && !fabMenu.contains(e.target)) {
        closeFABMenu();
      }
    });

    // Close on ESC key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && isOpen) {
        closeFABMenu();
      }
    });

    // FAB Actions
    const fabScrollToForm = document.getElementById('fabScrollToForm');
    const fabScrollToTop = document.getElementById('fabScrollToTop');
    const fabToggleAnalytics = document.getElementById('fabToggleAnalytics');

    // Scroll to form
    if (fabScrollToForm) {
      fabScrollToForm.addEventListener('click', function(e) {
        e.preventDefault();
        const formSection = document.querySelector('#project-formset-form');
        if (formSection) {
          formSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
          closeFABMenu();

          // Focus on first input
          setTimeout(() => {
            const firstInput = formSection.querySelector('input:not([type="hidden"]), select, textarea');
            if (firstInput) firstInput.focus();
          }, 500);
        }
      });
    }

    // Scroll to top
    if (fabScrollToTop) {
      fabScrollToTop.addEventListener('click', function(e) {
        e.preventDefault();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        closeFABMenu();
      });
    }

    // Toggle analytics
    if (fabToggleAnalytics) {
      fabToggleAnalytics.addEventListener('click', function() {
        const analyticsSection = document.getElementById('analyticsSection');
        if (analyticsSection) {
          const bsCollapse = new bootstrap.Collapse(analyticsSection, { toggle: true });
        }
        closeFABMenu();
      });
    }

    // Show/hide FAB on scroll
    let lastScrollTop = 0;
    const fabContainer = document.querySelector('.quick-actions-fab');

    window.addEventListener('scroll', function() {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

      // Show FAB after scrolling down 300px
      if (scrollTop > 300) {
        fabContainer.classList.add('fab-visible');
      } else {
        fabContainer.classList.remove('fab-visible');
      }

      // Hide FAB when scrolling down, show when scrolling up
      if (scrollTop > lastScrollTop && scrollTop > 500) {
        fabContainer.classList.add('fab-hidden');
      } else {
        fabContainer.classList.remove('fab-hidden');
      }

      lastScrollTop = scrollTop;
    }, { passive: true });
  }

  // ============================================================================
  // 2. QUICK SEARCH
  // ============================================================================

  function initQuickSearch() {
    const searchInput = document.getElementById('quickSearchInput');
    const clearBtn = document.getElementById('clearSearchBtn');
    const projectTable = document.querySelector('.dashboard-project-table');
    const projectCards = document.querySelectorAll('.project-mobile-card');

    if (!searchInput) return;

    // Debounce function
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

    // Search function
    function performSearch(query) {
      const searchTerm = query.toLowerCase().trim();

      if (!searchTerm) {
        showAllProjects();
        clearBtn.style.display = 'none';
        return;
      }

      clearBtn.style.display = 'block';
      let visibleCount = 0;

      // Search in table rows (desktop)
      if (projectTable) {
        const rows = projectTable.querySelectorAll('tbody tr');
        rows.forEach(row => {
          const text = row.textContent.toLowerCase();
          if (text.includes(searchTerm)) {
            row.style.display = '';
            visibleCount++;
          } else {
            row.style.display = 'none';
          }
        });
      }

      // Search in mobile cards
      projectCards.forEach(card => {
        const text = card.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
          card.style.display = '';
          visibleCount++;
        } else {
          card.style.display = 'none';
        }
      });

      // Show result count toast
      showToast(`Ditemukan ${visibleCount} project`, 'info');
    }

    // Show all projects
    function showAllProjects() {
      if (projectTable) {
        const rows = projectTable.querySelectorAll('tbody tr');
        rows.forEach(row => row.style.display = '');
      }
      projectCards.forEach(card => card.style.display = '');
    }

    // Search input event
    searchInput.addEventListener('input', debounce(function(e) {
      performSearch(e.target.value);
    }, 300));

    // Clear button
    if (clearBtn) {
      clearBtn.addEventListener('click', function() {
        searchInput.value = '';
        showAllProjects();
        clearBtn.style.display = 'none';
        searchInput.focus();
      });
    }

    // Keyboard shortcut: Ctrl + K
    document.addEventListener('keydown', function(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }
    });

    // ESC to clear and blur
    searchInput.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        this.value = '';
        showAllProjects();
        clearBtn.style.display = 'none';
        this.blur();
      }
    });
  }

  // ============================================================================
  // 3. FILTER PILLS
  // ============================================================================

  function initFilterPills() {
    const filterPills = document.querySelectorAll('.filter-pill');
    const projectTable = document.querySelector('.dashboard-project-table');
    const projectCards = document.querySelectorAll('.project-mobile-card');

    if (filterPills.length === 0) return;

    filterPills.forEach(pill => {
      pill.addEventListener('click', function() {
        const filterType = this.dataset.filter;

        // Update active state
        filterPills.forEach(p => {
          p.classList.remove('active');
          p.dataset.active = 'false';
        });
        this.classList.add('active');
        this.dataset.active = 'true';

        // Apply filter
        applyFilter(filterType);
      });
    });

    function applyFilter(filterType) {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const currentYear = today.getFullYear();
      let visibleCount = 0;

      // Filter table rows (desktop)
      if (projectTable) {
        const rows = projectTable.querySelectorAll('tbody tr');
        rows.forEach(row => {
          if (shouldShowRow(row, filterType, today, currentYear)) {
            row.style.display = '';
            visibleCount++;
          } else {
            row.style.display = 'none';
          }
        });
      }

      // Filter mobile cards
      projectCards.forEach(card => {
        if (shouldShowCard(card, filterType, today, currentYear)) {
          card.style.display = '';
          visibleCount++;
        } else {
          card.style.display = 'none';
        }
      });

      // Show toast
      const filterLabels = {
        'all': 'Semua Project',
        'active': 'Project Aktif',
        'overdue': 'Project Terlambat',
        'upcoming': 'Project Akan Datang',
        'thisyear': 'Project Tahun Ini'
      };
      showToast(`Filter: ${filterLabels[filterType]} (${visibleCount} project)`, 'info');
    }

    function shouldShowRow(row, filterType, today, currentYear) {
      if (filterType === 'all') return true;

      const statusBadge = row.querySelector('.badge');
      const yearCell = row.cells[3]?.textContent.trim();

      switch (filterType) {
        case 'active':
          return statusBadge && statusBadge.textContent.includes('Berjalan');
        case 'overdue':
          return statusBadge && statusBadge.textContent.includes('Terlambat');
        case 'upcoming':
          return statusBadge && statusBadge.textContent.includes('Belum Mulai');
        case 'thisyear':
          return yearCell && yearCell.includes(currentYear.toString());
        default:
          return true;
      }
    }

    function shouldShowCard(card, filterType, today, currentYear) {
      if (filterType === 'all') return true;

      const statusBadge = card.querySelector('.badge');
      const yearRow = Array.from(card.querySelectorAll('.info-row-mobile'))
        .find(row => row.querySelector('.label')?.textContent.includes('Tahun'));
      const yearValue = yearRow?.querySelector('.value')?.textContent.trim();

      switch (filterType) {
        case 'active':
          return statusBadge && statusBadge.textContent.includes('Berjalan');
        case 'overdue':
          return statusBadge && statusBadge.textContent.includes('Terlambat');
        case 'upcoming':
          return statusBadge && statusBadge.textContent.includes('Belum Mulai');
        case 'thisyear':
          return yearValue && yearValue.includes(currentYear.toString());
        default:
          return true;
      }
    }
  }

  // ============================================================================
  // 4. ACTIVE FILTERS DISPLAY
  // ============================================================================

  function initActiveFilters() {
    const filterForm = document.getElementById('filterForm');
    const activeFiltersContainer = document.getElementById('activeFiltersContainer');
    const activeFiltersList = document.getElementById('activeFiltersList');
    const clearAllFilters = document.getElementById('clearAllFilters');

    if (!filterForm || !activeFiltersContainer) return;

    // Check URL parameters on load
    const urlParams = new URLSearchParams(window.location.search);
    updateActiveFiltersDisplay();

    // Update on form change
    if (filterForm) {
      filterForm.addEventListener('change', function() {
        // Give a small delay to allow form to update
        setTimeout(updateActiveFiltersDisplay, 100);
      });
    }

    function updateActiveFiltersDisplay() {
      const urlParams = new URLSearchParams(window.location.search);
      const activeFilters = [];

      // Field labels
      const fieldLabels = {
        'search': 'Pencarian',
        'sort_by': 'Urutan',
        'is_active': 'Status Aktif',
        'tahun_project': 'Tahun',
        'sumber_dana': 'Sumber Dana',
        'status_timeline': 'Status Timeline',
        'anggaran_min': 'Anggaran Min',
        'anggaran_max': 'Anggaran Max',
        'tanggal_mulai_from': 'Tgl Mulai Dari',
        'tanggal_mulai_to': 'Tgl Mulai Sampai'
      };

      // Collect active filters
      urlParams.forEach((value, key) => {
        if (key !== 'page' && value && value.trim() !== '' && fieldLabels[key]) {
          activeFilters.push({ key, label: fieldLabels[key], value });
        }
      });

      // Show/hide container
      if (activeFilters.length > 0) {
        activeFiltersContainer.style.display = 'block';
        renderActiveFilters(activeFilters);
      } else {
        activeFiltersContainer.style.display = 'none';
      }
    }

    function renderActiveFilters(filters) {
      if (!activeFiltersList) return;

      activeFiltersList.innerHTML = '';

      filters.forEach(filter => {
        const tag = document.createElement('div');
        tag.className = 'active-filter-tag';
        tag.innerHTML = `
          <span class="filter-label">${filter.label}:</span>
          <span class="filter-value">${truncate(filter.value, 20)}</span>
          <button type="button" class="remove-filter" data-filter-key="${filter.key}" title="Hapus filter">
            <i class="bi bi-x"></i>
          </button>
        `;
        activeFiltersList.appendChild(tag);

        // Add remove handler
        const removeBtn = tag.querySelector('.remove-filter');
        removeBtn.addEventListener('click', function() {
          removeFilter(filter.key);
        });
      });
    }

    function removeFilter(key) {
      const url = new URL(window.location.href);
      url.searchParams.delete(key);
      window.location.href = url.toString();
    }

    // Clear all filters
    if (clearAllFilters) {
      clearAllFilters.addEventListener('click', function() {
        window.location.href = window.location.pathname;
      });
    }

    function truncate(str, maxLength) {
      if (str.length <= maxLength) return str;
      return str.substring(0, maxLength) + '...';
    }
  }

  // ============================================================================
  // 5. TOAST NOTIFICATIONS
  // ============================================================================

  let toastContainer = null;

  function initToasts() {
    // Create toast container if it doesn't exist
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.className = 'toast-container-modern';
      toastContainer.id = 'toastContainer';
      document.body.appendChild(toastContainer);
    }
  }

  function showToast(message, type = 'info', duration = 3000) {
    if (!toastContainer) initToasts();

    const toast = document.createElement('div');
    toast.className = `toast-modern toast-${type}`;

    const icons = {
      success: 'bi-check-circle-fill',
      error: 'bi-x-circle-fill',
      warning: 'bi-exclamation-triangle-fill',
      info: 'bi-info-circle-fill'
    };

    toast.innerHTML = `
      <div class="toast-icon">
        <i class="bi ${icons[type] || icons.info}"></i>
      </div>
      <div class="toast-content">
        <div class="toast-message">${message}</div>
      </div>
      <button type="button" class="toast-close" aria-label="Close">
        <i class="bi bi-x"></i>
      </button>
    `;

    toastContainer.appendChild(toast);

    // Animate in
    setTimeout(() => {
      toast.classList.add('toast-show');
    }, 10);

    // Close button
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => {
      removeToast(toast);
    });

    // Auto remove
    setTimeout(() => {
      removeToast(toast);
    }, duration);
  }

  function removeToast(toast) {
    toast.classList.remove('toast-show');
    toast.classList.add('toast-hide');

    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }

  // Make showToast globally available
  window.showToast = showToast;

  // ============================================================================
  // 6. ENHANCED TABLE INTERACTIONS
  // ============================================================================

  function initTableEnhancements() {
    const table = document.querySelector('.dashboard-project-table');
    if (!table) return;

    // Row hover highlight
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
      row.addEventListener('mouseenter', function() {
        this.classList.add('row-hover');
      });

      row.addEventListener('mouseleave', function() {
        this.classList.remove('row-hover');
      });

      // Row selection on checkbox change
      const checkbox = row.querySelector('.project-checkbox');
      if (checkbox) {
        checkbox.addEventListener('change', function() {
          if (this.checked) {
            row.classList.add('selected');
          } else {
            row.classList.remove('selected');
          }
        });

        // Initialize selection state
        if (checkbox.checked) {
          row.classList.add('selected');
        }
      }
    });
  }

  // ============================================================================
  // 7. SMOOTH SCROLLING
  // ============================================================================

  function initSmoothScrolling() {
    // Smooth scroll for all anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        const href = this.getAttribute('href');

        if (href === '#') return;

        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }

  // ============================================================================
  // 8. LOADING STATES
  // ============================================================================

  function showLoadingState(element) {
    if (!element) return;

    element.classList.add('loading');
    element.style.pointerEvents = 'none';
    element.style.opacity = '0.6';
  }

  function hideLoadingState(element) {
    if (!element) return;

    element.classList.remove('loading');
    element.style.pointerEvents = '';
    element.style.opacity = '';
  }

  // Make globally available
  window.showLoadingState = showLoadingState;
  window.hideLoadingState = hideLoadingState;

  // ============================================================================
  // 9. RESPONSIVE ENHANCEMENTS
  // ============================================================================

  function initResponsiveEnhancements() {
    // Detect mobile/tablet
    function isMobile() {
      return window.innerWidth < 992;
    }

    // Adjust quick filters on mobile
    function adjustQuickFilters() {
      const quickFiltersBar = document.querySelector('.quick-filters-bar');
      if (!quickFiltersBar) return;

      if (isMobile()) {
        quickFiltersBar.classList.add('mobile-layout');
      } else {
        quickFiltersBar.classList.remove('mobile-layout');
      }
    }

    // Run on load and resize
    adjustQuickFilters();
    window.addEventListener('resize', debounce(adjustQuickFilters, 250));

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
  }

  // ============================================================================
  // 10. ACCESSIBILITY ENHANCEMENTS
  // ============================================================================

  function initAccessibility() {
    // Focus visible on keyboard navigation
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Tab') {
        document.body.classList.add('keyboard-nav');
      }
    });

    document.addEventListener('mousedown', function() {
      document.body.classList.remove('keyboard-nav');
    });

    // Announce dynamic changes to screen readers
    const announcer = document.createElement('div');
    announcer.className = 'sr-only';
    announcer.setAttribute('role', 'status');
    announcer.setAttribute('aria-live', 'polite');
    announcer.setAttribute('aria-atomic', 'true');
    document.body.appendChild(announcer);

    window.announce = function(message) {
      announcer.textContent = message;
      setTimeout(() => {
        announcer.textContent = '';
      }, 1000);
    };
  }

  // ============================================================================
  // 11. MASS EDIT FUNCTIONALITY
  // ============================================================================

  function initMassEdit() {
    const massEditModal = document.getElementById('massEditModal');
    const massEditForm = document.getElementById('massEditForm');
    const massEditSubmitBtn = document.getElementById('massEditSubmitBtn');
    const fabMassEdit = document.getElementById('fabMassEdit');

    if (!massEditModal || !massEditForm) return;

    // Enable/disable inputs based on checkbox state
    const checkboxes = massEditForm.querySelectorAll('.form-check-input');
    checkboxes.forEach(checkbox => {
      checkbox.addEventListener('change', function() {
        const inputId = this.id.replace('update', 'massEdit');
        const input = document.getElementById(inputId) ||
                     document.querySelector(`[name="${this.id.replace('update', '').toLowerCase().replace(/([A-Z])/g, '_$1').slice(1)}"]`);

        if (input) {
          input.disabled = !this.checked;
          if (this.checked) {
            input.focus();
          }
        }
      });
    });

    // Populate selected project IDs when modal opens
    massEditModal.addEventListener('show.bs.modal', function() {
      const selectedCheckboxes = document.querySelectorAll('.project-checkbox:checked');
      const selectedIds = Array.from(selectedCheckboxes).map(cb => cb.value);
      const selectedCount = selectedIds.length;

      // Update selected count display
      const countDisplay = document.getElementById('massEditSelectedCount');
      const alertInfo = massEditModal.querySelector('.alert-info');
      const alertWarning = massEditModal.querySelector('.alert-warning');

      if (countDisplay) {
        countDisplay.textContent = selectedCount;
      }

      if (selectedCount > 0) {
        if (alertInfo) alertInfo.style.display = 'block';
        if (alertWarning) alertWarning.style.display = 'none';

        // Populate hidden input with project IDs
        let projectIdsInput = document.getElementById('massEditProjectIds');
        if (!projectIdsInput) {
          projectIdsInput = document.createElement('input');
          projectIdsInput.type = 'hidden';
          projectIdsInput.id = 'massEditProjectIds';
          projectIdsInput.name = 'project_ids';
          massEditForm.appendChild(projectIdsInput);
        }
        projectIdsInput.value = selectedIds.join(',');
      } else {
        if (alertInfo) alertInfo.style.display = 'none';
        if (alertWarning) alertWarning.style.display = 'block';
        massEditSubmitBtn.disabled = true;
      }
    });

    // Reset form when modal closes
    massEditModal.addEventListener('hidden.bs.modal', function() {
      massEditForm.reset();
      checkboxes.forEach(checkbox => {
        checkbox.checked = false;
        const inputId = checkbox.id.replace('update', 'massEdit');
        const input = document.getElementById(inputId) ||
                     document.querySelector(`[name="${checkbox.id.replace('update', '').toLowerCase().replace(/([A-Z])/g, '_$1').slice(1)}"]`);
        if (input) {
          input.disabled = true;
        }
      });
      massEditSubmitBtn.disabled = false;
    });

    // Handle form submission
    massEditSubmitBtn.addEventListener('click', function(e) {
      e.preventDefault();

      // Get selected project IDs
      const projectIdsInput = document.getElementById('massEditProjectIds');
      if (!projectIdsInput || !projectIdsInput.value) {
        showToast('Tidak ada project yang dipilih', 'warning');
        return;
      }

      // Collect enabled fields
      const formData = new FormData();
      formData.append('project_ids', projectIdsInput.value);

      // Get CSRF token
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
      formData.append('csrfmiddlewaretoken', csrfToken);

      // Add only checked fields
      let hasChanges = false;
      checkboxes.forEach(checkbox => {
        if (checkbox.checked) {
          const fieldName = checkbox.id.replace('update', '').toLowerCase().replace(/([A-Z])/g, '_$1').slice(1);
          const input = massEditForm.querySelector(`[name="${fieldName}"]`);

          if (input) {
            formData.append(fieldName, input.value);
            formData.append(`update_${fieldName}`, 'true');
            hasChanges = true;
          }
        }
      });

      if (!hasChanges) {
        showToast('Pilih minimal satu field untuk di-update', 'warning');
        return;
      }

      // Disable submit button
      massEditSubmitBtn.disabled = true;
      massEditSubmitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Menyimpan...';

      // Submit via AJAX
      fetch(massEditForm.dataset.url || '/dashboard/mass-edit/', {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          showToast(`${data.count} project berhasil diupdate`, 'success');

          // Close modal
          const modalInstance = bootstrap.Modal.getInstance(massEditModal);
          modalInstance.hide();

          // Reload page after short delay
          setTimeout(() => {
            window.location.reload();
          }, 1500);
        } else {
          showToast(data.message || 'Terjadi kesalahan', 'error');
          massEditSubmitBtn.disabled = false;
          massEditSubmitBtn.innerHTML = 'Simpan Perubahan';
        }
      })
      .catch(error => {
        console.error('Mass edit error:', error);
        showToast('Terjadi kesalahan saat menyimpan', 'error');
        massEditSubmitBtn.disabled = false;
        massEditSubmitBtn.innerHTML = 'Simpan Perubahan';
      });
    });

    // Update "Select All" checkbox functionality
    const selectAllCheckbox = document.getElementById('selectAllProjects');
    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener('change', function() {
        const projectCheckboxes = document.querySelectorAll('.project-checkbox');
        projectCheckboxes.forEach(cb => {
          cb.checked = this.checked;
          const row = cb.closest('tr');
          if (row) {
            if (this.checked) {
              row.classList.add('selected');
            } else {
              row.classList.remove('selected');
            }
          }
        });

        // Update count badge if exists
        updateSelectedCount();
      });
    }

    // Update selected count on individual checkbox change
    document.addEventListener('change', function(e) {
      if (e.target.classList.contains('project-checkbox')) {
        updateSelectedCount();
      }
    });

    function updateSelectedCount() {
      const selectedCheckboxes = document.querySelectorAll('.project-checkbox:checked');
      const count = selectedCheckboxes.length;

      // Update count badge in FAB button if exists
      const countBadge = document.getElementById('massEditCountBadge');
      if (countBadge) {
        if (count > 0) {
          countBadge.textContent = count;
          countBadge.style.display = 'inline-block';
        } else {
          countBadge.style.display = 'none';
        }
      }
    }
  }

  // ============================================================================
  // INITIALIZATION
  // ============================================================================

  document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing UX Enhancements...');

    initFAB();
    initQuickSearch();
    initFilterPills();
    initActiveFilters();
    initToasts();
    initTableEnhancements();
    initSmoothScrolling();
    initResponsiveEnhancements();
    initAccessibility();
    initMassEdit();

    console.log('✅ UX Enhancements initialized successfully');

    // Welcome toast (optional - comment out if not needed)
    // setTimeout(() => {
    //   showToast('Dashboard siap digunakan!', 'success', 2000);
    // }, 500);
  });

})();
