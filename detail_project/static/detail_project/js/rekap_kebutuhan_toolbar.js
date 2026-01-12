// static/detail_project/js/rekap_kebutuhan_toolbar.js
// Toolbar V2 enhancements for Phase 4 redesign
// Handles: refresh button, search clear, keyboard shortcuts, stat animations

(function () {
  'use strict';

  // Wait for main app to be ready
  if (!document.getElementById('rk-app')) {
    console.warn('[rk-toolbar] App not found, skipping toolbar enhancements');
    return;
  }

  // =========================================================================
  // CONFIGURATION
  // =========================================================================

  const DEBOUNCE_DELAY = 300;
  const ANIMATION_DURATION = 600;

  // =========================================================================
  // DOM ELEMENTS
  // =========================================================================

  const $refreshBtn = document.getElementById('rk-btn-refresh');
  const $searchInput = document.getElementById('rk-search');
  const $searchClearBtn = document.getElementById('rk-search-clear');
  const $statsToggle = document.querySelector('.rk-stats-toggle');
  const $statsSummaryBadge = document.getElementById('rk-stats-summary');
  const $statsCards = document.querySelectorAll('.rk-stat-card');
  const $viewToggleBtns = document.querySelectorAll('#rk-view-toggle button');

  // =========================================================================
  // UTILITY FUNCTIONS
  // =========================================================================

  /**
   * Debounce function
   */
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

  /**
   * Add pulse animation to stat card
   */
  function pulseStatCard(kategori) {
    const $card = document.querySelector(`.rk-stat-card[data-kategori="${kategori}"]`);
    if (!$card) return;

    $card.classList.add('rk-stat-card--pulse');
    setTimeout(() => {
      $card.classList.remove('rk-stat-card--pulse');
    }, ANIMATION_DURATION);
  }

  /**
   * Update stats summary badge (total items count)
   */
  function updateStatsSummary() {
    if (!$statsSummaryBadge) return;

    const counts = ['TK', 'BHN', 'ALT', 'LAIN'].map(kat => {
      const $count = document.getElementById(`rk-count-${kat}`);
      return $count ? parseInt($count.textContent) || 0 : 0;
    });

    const total = counts.reduce((sum, val) => sum + val, 0);
    $statsSummaryBadge.textContent = total;
  }

  /**
   * Show toast notification (delegate to global DP.toast)
   */
  function showToast(message, type = 'info') {
    // Use new global toast API
    if (window.DP && window.DP.toast && window.DP.toast[type]) {
      return window.DP.toast[type](message);
    }
    // Fallback to legacy API
    if (window.DP && window.DP.core && window.DP.core.toast) {
      window.DP.core.toast.show(message, type);
      return;
    }
    // Console fallback
    console.log(`[${type}] ${message}`);
  }

  // =========================================================================
  // REFRESH BUTTON
  // =========================================================================

  function handleRefresh() {
    if (!$refreshBtn) return;

    // Add spinning animation
    $refreshBtn.classList.add('spinning');
    $refreshBtn.disabled = true;

    // Trigger reload event (main app should listen to this)
    const event = new CustomEvent('rk:refresh', {
      detail: { timestamp: Date.now() }
    });
    document.dispatchEvent(event);

    // Show toast
    showToast('Memuat ulang data...', 'info');

    // Remove spinning after 2 seconds (fallback)
    setTimeout(() => {
      $refreshBtn.classList.remove('spinning');
      $refreshBtn.disabled = false;
    }, 2000);
  }

  if ($refreshBtn) {
    $refreshBtn.addEventListener('click', handleRefresh);
  }

  // Listen for data loaded event to stop spinner
  document.addEventListener('rk:dataLoaded', () => {
    if ($refreshBtn) {
      $refreshBtn.classList.remove('spinning');
      $refreshBtn.disabled = false;
    }
  });

  // =========================================================================
  // SEARCH CLEAR BUTTON
  // =========================================================================

  function updateSearchClearButton() {
    if (!$searchInput || !$searchClearBtn) return;

    if ($searchInput.value.trim().length > 0) {
      $searchClearBtn.classList.remove('d-none');
    } else {
      $searchClearBtn.classList.add('d-none');
    }
  }

  function handleSearchClear() {
    if (!$searchInput) return;

    $searchInput.value = '';
    $searchInput.focus();
    updateSearchClearButton();

    // Trigger search event
    const event = new Event('input', { bubbles: true });
    $searchInput.dispatchEvent(event);
  }

  if ($searchInput) {
    // Update clear button visibility on input
    $searchInput.addEventListener('input', debounce(updateSearchClearButton, 100));

    // Initial state
    updateSearchClearButton();
  }

  if ($searchClearBtn) {
    $searchClearBtn.addEventListener('click', handleSearchClear);
  }

  // =========================================================================
  // KEYBOARD SHORTCUTS
  // =========================================================================

  function handleKeyboardShortcuts(e) {
    // Ctrl+R / Cmd+R - Refresh
    if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
      e.preventDefault();
      handleRefresh();
      return;
    }

    // Ctrl+F / Cmd+F - Focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
      e.preventDefault();
      if ($searchInput) {
        $searchInput.focus();
        $searchInput.select();
      }
      return;
    }

    // Escape - Clear search if focused
    if (e.key === 'Escape') {
      if (document.activeElement === $searchInput && $searchInput.value) {
        handleSearchClear();
        e.preventDefault();
      }
    }
  }

  document.addEventListener('keydown', handleKeyboardShortcuts);

  // =========================================================================
  // STAT CARDS ANIMATION
  // =========================================================================

  // Create MutationObserver to watch for stat updates
  const observeStatUpdates = () => {
    const statCountElements = document.querySelectorAll('[id^="rk-count-"], [id^="rk-qty-"], #rk-total-cost');

    statCountElements.forEach($el => {
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.type === 'childList' || mutation.type === 'characterData') {
            // Get kategori from parent card
            const $card = $el.closest('.rk-stat-card');
            if ($card) {
              const kategori = $card.dataset.kategori;
              if (kategori) {
                pulseStatCard(kategori);
              } else {
                // Total card
                $card.classList.add('rk-stat-card--pulse');
                setTimeout(() => {
                  $card.classList.remove('rk-stat-card--pulse');
                }, ANIMATION_DURATION);
              }
            }

            // Update summary badge
            updateStatsSummary();
          }
        });
      });

      observer.observe($el, {
        childList: true,
        characterData: true,
        subtree: true
      });
    });
  };

  // Initialize observer after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', observeStatUpdates);
  } else {
    observeStatUpdates();
  }

  // =========================================================================
  // VIEW TOGGLE ENHANCEMENT
  // =========================================================================

  if ($viewToggleBtns.length > 0) {
    $viewToggleBtns.forEach($btn => {
      $btn.addEventListener('click', () => {
        // Update aria-pressed
        $viewToggleBtns.forEach($b => {
          $b.setAttribute('aria-pressed', 'false');
        });
        $btn.setAttribute('aria-pressed', 'true');

        // Announce to screen readers
        const view = $btn.dataset.view;
        const announcement = `Switched to ${view} view`;
        announceToScreenReader(announcement);
      });
    });
  }

  /**
   * Announce message to screen readers
   */
  function announceToScreenReader(message) {
    const $announcement = document.getElementById('rk-sr-announcement') ||
      (() => {
        const $el = document.createElement('div');
        $el.id = 'rk-sr-announcement';
        $el.className = 'visually-hidden';
        $el.setAttribute('role', 'status');
        $el.setAttribute('aria-live', 'polite');
        document.body.appendChild($el);
        return $el;
      })();

    $announcement.textContent = message;

    // Clear after announcement
    setTimeout(() => {
      $announcement.textContent = '';
    }, 1000);
  }

  // =========================================================================
  // STATS COLLAPSE STATE PERSISTENCE
  // =========================================================================

  const STORAGE_KEY = 'rk-stats-collapsed';

  // Restore collapse state from sessionStorage
  function restoreStatsCollapseState() {
    if (!$statsToggle) return;

    try {
      const isCollapsed = sessionStorage.getItem(STORAGE_KEY) === 'true';
      if (isCollapsed) {
        const $collapse = document.getElementById('rk-stats-collapse');
        if ($collapse) {
          // Use Bootstrap's Collapse API
          const bsCollapse = bootstrap.Collapse.getOrCreateInstance($collapse);
          bsCollapse.hide();
        }
      }
    } catch (e) {
      console.warn('[rk-toolbar] Could not restore stats collapse state:', e);
    }
  }

  // Save collapse state to sessionStorage
  function saveStatsCollapseState(isCollapsed) {
    try {
      sessionStorage.setItem(STORAGE_KEY, isCollapsed ? 'true' : 'false');
    } catch (e) {
      console.warn('[rk-toolbar] Could not save stats collapse state:', e);
    }
  }

  // Listen for collapse events
  const $statsCollapse = document.getElementById('rk-stats-collapse');
  if ($statsCollapse) {
    $statsCollapse.addEventListener('hidden.bs.collapse', () => {
      saveStatsCollapseState(true);
      announceToScreenReader('Statistics collapsed');
    });

    $statsCollapse.addEventListener('shown.bs.collapse', () => {
      saveStatsCollapseState(false);
      announceToScreenReader('Statistics expanded');
    });

    // Restore state on load
    restoreStatsCollapseState();
  }

  // =========================================================================
  // FOCUS MANAGEMENT
  // =========================================================================

  // Add visible focus indicators
  document.addEventListener('focusin', (e) => {
    if (e.target.matches('.rk-toolbar-v2 button, .rk-toolbar-v2 input')) {
      e.target.style.outline = '2px solid var(--dp-c-primary, #0d6efd)';
      e.target.style.outlineOffset = '2px';
    }
  });

  document.addEventListener('focusout', (e) => {
    if (e.target.matches('.rk-toolbar-v2 button, .rk-toolbar-v2 input')) {
      e.target.style.outline = '';
      e.target.style.outlineOffset = '';
    }
  });

  // =========================================================================
  // INITIALIZATION COMPLETE
  // =========================================================================

  console.log('[rk-toolbar] Toolbar V2 enhancements loaded');

  // Initial stats summary update
  updateStatsSummary();

  // Dispatch ready event
  document.dispatchEvent(new CustomEvent('rk:toolbarReady', {
    detail: { version: '2.0' }
  }));

})();
