// /static/detail_project/js/list_pekerjaan.js
/* =====================================================================
   List Pekerjaan — JS
   - Kompatibel: jQuery 3.7, Select2 4.1, Bootstrap 5
   - Fitur: TOC Sidebar, Drag & Drop, Template Library, Filter
   ===================================================================== */

(function () {
  // ========= [UTILITIES] Logging & Guards ====================================
  const __DEBUG__ = false; // set true untuk log/diagnostic

  const log = (...a) => __DEBUG__ && console.debug('[LP]', ...a);
  const warn = (...a) => __DEBUG__ && console.warn('[LP]', ...a);
  const err = (...a) => console.error('[LP]', ...a); // error tetap tampil

  // jQuery alias (boleh null jika belum ter-load saat eval; cek dilakukan runtime)
  const $ = window.jQuery || window.$;
  const HAS_JQ = !!$;
  const HAS_S2 = !!($ && $.fn && $.fn.select2);

  // Global error diagnostics (tidak mengubah flow normal)
  window.addEventListener('error', (e) => {
    err('GlobalError:', e.message, 'at', e.filename + ':' + e.lineno + ':' + e.colno, e.error);
  });
  window.addEventListener('unhandledrejection', (e) => {
    err('UnhandledPromise:', e.reason);
  });

  // ========= [CORE SHORTCUTS] jfetch & toast =================================
  const jfetch = (window.DP && DP.core && DP.core.http && DP.core.http.jfetch)
    ? DP.core.http.jfetch
    : async function (url, opts = {}) {
      const res = await fetch(url, { credentials: 'same-origin', ...opts });
      const ok = res.ok;
      const ctyp = res.headers.get('content-type') || '';
      const body = ctyp.includes('application/json') ? await res.json() : await res.text();
      if (!ok) {
        const e = new Error('HTTP ' + res.status);
        e.status = res.status; e.body = body;
        throw e;
      }
      return body;
    };

  const tShow = (function () {
    if (window.DP && DP.toast && DP.toast.show) return DP.toast.show;
    if (window.DP && DP.core && DP.core.toast && DP.core.toast.show) return DP.core.toast.show;
    if (typeof window.showToast === 'function') return window.showToast;
    return (msg) => console.warn('[LP] Toast:', msg);
  })();

  // ========= [DOM REFS] ========================================================
  const mainArea = document.querySelector('.lp-main');
  const root = document.getElementById('lp-app');

  // Pastikan #klas-list adalah DIV container
  function ensureKlasList() {
    const tableWrap = document.querySelector('.lp-table-wrap');
    let klasList = document.getElementById('klas-list');

    if (klasList && klasList.tagName !== 'TBODY') return klasList;

    const newDiv = document.createElement('div');
    newDiv.id = 'klas-list';
    newDiv.className = 'vstack gap-3';

    if (tableWrap) {
      tableWrap.insertAdjacentElement('afterend', newDiv);
      tableWrap.style.display = 'none';
    } else if (klasList?.tagName === 'TBODY') {
      klasList.replaceWith(newDiv);
    } else {
      (mainArea || document.body).appendChild(newDiv);
    }

    return newDiv;
  }

  let klasWrap = ensureKlasList();

  // Tombol (kanonik + alias class)
  const btnAddKlasAll = Array.from(document.querySelectorAll('#btn-add-klas, .js-add-klas'));
  const btnSaveAll = Array.from(document.querySelectorAll('#btn-save, .js-save'));
  const btnCompactAll = Array.from(document.querySelectorAll('#btn-compact, .js-compact'));

  // Mini TOC DOM anchors
  const tocTree = document.getElementById('lp-toc-tree');
  const tocStats = document.getElementById('lp-toc-stats');
  const tocSearch = document.getElementById('lp-toc-search');
  const tocExpandAll = document.getElementById('lp-toc-expand-all');
  const tocCollapseAll = document.getElementById('lp-toc-collapse-all');
  const navSearchToolbar = document.getElementById('lp-nav-search');
  const tbAnnounce = document.getElementById('lp-toolbar-announce');

  // ========= [A11Y] Live region ==============================================
  let live = document.getElementById('lp-live');
  if (!live) {
    live = document.createElement('div');
    live.id = 'lp-live';
    live.setAttribute('aria-live', 'polite');
    live.setAttribute('aria-atomic', 'true');
    live.className = 'visually-hidden';
    document.body.appendChild(live);
  }
  const say = (t) => { live.textContent = t; };

  // ========= [DIRTY TRACKING] Prevent Data Loss ==============================
  let isDirty = false;
  let allowUnload = false;
  let dirtySuppressCount = 0;
  let hardReloadBypassUntil = 0;
  const HARD_RELOAD_BYPASS_MS = 1500;

  function setDirty(dirty) {
    if (dirty && dirtySuppressCount > 0) {
      return;
    }
    isDirty = !!dirty;
    log('[DIRTY]', isDirty ? 'Set to dirty' : 'Cleared');

    // Update save button state
    btnSaveAll.forEach(btn => {
      if (isDirty) {
        btn.classList.add('btn-neon'); // Add pulsing effect
        btn.removeAttribute('disabled');
      } else {
        btn.classList.remove('btn-neon');
      }
    });

    // Update FAB save button
    const fabBtn = document.getElementById('btn-save-fab');
    if (fabBtn) {
      fabBtn.classList.toggle('d-none', !isDirty);
    }
  }

  function withDirtySuppressed(fn) {
    dirtySuppressCount += 1;
    try {
      return fn();
    } finally {
      dirtySuppressCount -= 1;
    }
  }

  function getModalApi() {
    return (window.DP && DP.core && DP.core.modal) ? DP.core.modal : null;
  }

  async function confirmReload(reason) {
    const modalApi = getModalApi();
    if (!modalApi || !modalApi.confirm) return false;
    if (!isDirty) {
      allowUnload = true;
      window.location.reload();
      return true;
    }
    const message = reason
      ? `${reason}\n\nPerubahan belum disimpan akan hilang jika Anda melanjutkan.`
      : 'Perubahan belum disimpan akan hilang jika Anda melanjutkan reload halaman.';
    const ok = await modalApi.confirm(message, {
      title: 'Konfirmasi Reload',
      confirmText: 'Reload',
      cancelText: 'Batal',
      confirmClass: 'btn btn-danger',
    });
    if (ok) {
      allowUnload = true;
      window.location.reload();
    }
    return ok;
  }

  function isEditableTarget(target) {
    if (!target || !(target instanceof Element)) return false;
    if (target.closest('input, textarea, select, [contenteditable="true"]')) return true;
    return false;
  }

  // Prevent accidental data loss on page close/refresh
  window.addEventListener('beforeunload', (e) => {
    if (Date.now() < hardReloadBypassUntil) return;
    if (isDirty && !allowUnload) {
      const msg = 'Anda memiliki perubahan yang belum disimpan. Yakin ingin keluar?';
      e.preventDefault();
      e.returnValue = msg; // Chrome requires returnValue
      return msg;
    }
  });

  window.addEventListener('keydown', (e) => {
    if (!isDirty) return;
    if (e.defaultPrevented) return;
    if (e.repeat) return;
    if (isEditableTarget(e.target)) return;

    const key = String(e.key || '').toLowerCase();
    const isF5 = e.key === 'F5';
    const isHardReload =
      ((e.ctrlKey || e.metaKey) && e.shiftKey && key === 'r')
      || (isF5 && (e.ctrlKey || e.metaKey || e.shiftKey));
    if (isHardReload) {
      // Let hard reload pass without the custom/native unsaved-change blocker.
      hardReloadBypassUntil = Date.now() + HARD_RELOAD_BYPASS_MS;
      return;
    }

    const isSoftReload = isF5 || ((e.ctrlKey || e.metaKey) && key === 'r');
    if (!isSoftReload) return;

    const modalApi = getModalApi();
    if (!modalApi || !modalApi.confirm) return;
    e.preventDefault();
    confirmReload('Anda akan memuat ulang halaman.');
  });

  // ========= [CROSS-TAB SYNC] BroadcastChannel API ===========================
  let bc = null;

  // Initialize BroadcastChannel if supported
  if (typeof BroadcastChannel !== 'undefined') {
    try {
      bc = new BroadcastChannel('list_pekerjaan_sync');

      // Listen for changes from other tabs
      bc.onmessage = (event) => {
        if (!event.data || !event.data.type) return;

        if (event.data.type === 'ordering_changed') {
          const { projectId: changedProjectId } = event.data;

          // Only show notification if same project
          if (changedProjectId && String(changedProjectId) === String(projectId)) {
            log('[BROADCAST] Received ordering_changed from other tab');

            // Show warning toast
            tShow('⚠️ Urutan pekerjaan diubah di tab lain. Refresh halaman untuk melihat perubahan terbaru.', 'warning', 8000);

            // Optionally: Add refresh button to banner
            const banner = document.createElement('div');
            banner.className = 'alert alert-warning alert-dismissible fade show position-fixed';
            banner.style.cssText = 'top: 80px; right: 20px; z-index: 9999; max-width: 400px;';
            banner.innerHTML = `
              <strong>Perubahan dari tab lain</strong><br>
              <small>Urutan pekerjaan telah diubah di tab lain.</small>
              <div class="mt-2">
                <button class="btn btn-sm btn-warning" data-action="lp-reload">
                  <i class="bi bi-arrow-clockwise"></i> Refresh Sekarang
                </button>
              </div>
              <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.body.appendChild(banner);

            const reloadBtn = banner.querySelector('[data-action="lp-reload"]');
            if (reloadBtn) {
              reloadBtn.addEventListener('click', () => {
                confirmReload('Perubahan dari tab lain tidak akan terlihat sebelum reload.');
              });
            }

            // Auto-remove after 30 seconds
            setTimeout(() => banner.remove(), 30000);
          }
        }
      };

      log('[BROADCAST] BroadcastChannel initialized');
    } catch (err) {
      warn('[BROADCAST] Failed to initialize BroadcastChannel:', err);
      bc = null;
    }
  } else {
    warn('[BROADCAST] BroadcastChannel not supported in this browser');
  }

  // Broadcast ordering change to other tabs
  function broadcastOrderingChange() {
    if (bc) {
      try {
        bc.postMessage({
          type: 'ordering_changed',
          projectId,
          timestamp: Date.now()
        });
        log('[BROADCAST] Sent ordering_changed notification');
      } catch (err) {
        warn('[BROADCAST] Failed to send message:', err);
      }
    }
  }

  // ========= [DRAG & DROP] Infrastructure ====================================
  let dragState = {
    draggingRow: null,      // TR element being dragged
    sourceKlasId: null,     // Klas ID where drag started
    sourceSubId: null,      // Sub ID where drag started
    pekerjaanId: null,      // Pekerjaan ID (from dataset.id or row.id)
    sourceTbody: null,      // Original tbody
    dragOverTarget: null    // Current drop target (tbody or row)
  };

  // Auto-scroll while dragging near viewport/container edges.
  const DRAG_SCROLL_EDGE_PX = 72;
  const DRAG_SCROLL_MAX_STEP = 22;
  let dragScrollRaf = 0;
  let dragScrollActive = false;
  let dragScrollPointerX = 0;
  let dragScrollPointerY = 0;
  let dragScrollContainer = null;

  function dragScrollSpeed(distance, edge = DRAG_SCROLL_EDGE_PX, max = DRAG_SCROLL_MAX_STEP) {
    if (distance >= edge) return 0;
    const ratio = (edge - distance) / edge;
    return Math.max(1, Math.round(ratio * max));
  }

  function findScrollableAncestor(el) {
    let node = el instanceof Element ? el : null;
    while (node && node !== document.body) {
      const style = window.getComputedStyle(node);
      const overflowY = style.overflowY || style.overflow;
      const canScrollY = /(auto|scroll|overlay)/.test(overflowY || '');
      if (canScrollY && node.scrollHeight > node.clientHeight + 1) return node;
      node = node.parentElement;
    }
    return document.scrollingElement || document.documentElement;
  }

  function resolveDragScrollContainer(hintEl) {
    return findScrollableAncestor(hintEl || klasWrap || document.body);
  }

  function tickDragAutoScroll() {
    if (!dragScrollActive) return;

    const viewportH = window.innerHeight || document.documentElement.clientHeight;
    const topDistance = dragScrollPointerY;
    const bottomDistance = Math.max(0, viewportH - dragScrollPointerY);

    let windowDelta = 0;
    if (topDistance < DRAG_SCROLL_EDGE_PX) {
      windowDelta = -dragScrollSpeed(topDistance);
    } else if (bottomDistance < DRAG_SCROLL_EDGE_PX) {
      windowDelta = dragScrollSpeed(bottomDistance);
    }

    if (windowDelta !== 0) {
      window.scrollBy(0, windowDelta);
    }

    const c = dragScrollContainer;
    if (c && c !== document.body && c !== document.documentElement && c !== document.scrollingElement) {
      const rect = c.getBoundingClientRect();
      const inVerticalRange = dragScrollPointerY >= rect.top && dragScrollPointerY <= rect.bottom;
      if (inVerticalRange) {
        const cTopDistance = dragScrollPointerY - rect.top;
        const cBottomDistance = rect.bottom - dragScrollPointerY;
        let cDelta = 0;
        if (cTopDistance < DRAG_SCROLL_EDGE_PX) {
          cDelta = -dragScrollSpeed(cTopDistance);
        } else if (cBottomDistance < DRAG_SCROLL_EDGE_PX) {
          cDelta = dragScrollSpeed(cBottomDistance);
        }
        if (cDelta !== 0) {
          c.scrollTop += cDelta;
        }
      }
    }

    dragScrollRaf = window.requestAnimationFrame(tickDragAutoScroll);
  }

  function startDragAutoScroll(containerHint, e = null) {
    dragScrollContainer = resolveDragScrollContainer(containerHint);
    if (e) {
      dragScrollPointerX = e.clientX;
      dragScrollPointerY = e.clientY;
    }
    if (dragScrollActive) return;
    dragScrollActive = true;
    dragScrollRaf = window.requestAnimationFrame(tickDragAutoScroll);
  }

  function updateDragAutoScroll(e, containerHint = null) {
    if (!e) return;
    dragScrollPointerX = e.clientX;
    dragScrollPointerY = e.clientY;
    if (containerHint) {
      dragScrollContainer = resolveDragScrollContainer(containerHint);
    } else if (!dragScrollContainer) {
      dragScrollContainer = resolveDragScrollContainer(e.target);
    }
  }

  function stopDragAutoScroll() {
    dragScrollActive = false;
    dragScrollContainer = null;
    if (dragScrollRaf) {
      window.cancelAnimationFrame(dragScrollRaf);
      dragScrollRaf = 0;
    }
  }

  function resetDragState() {
    stopDragAutoScroll();
    // Remove visual feedback
    document.querySelectorAll('.lp-row-dragging').forEach(el => el.classList.remove('lp-row-dragging'));
    document.querySelectorAll('.lp-drop-target').forEach(el => el.classList.remove('lp-drop-target'));
    document.querySelectorAll('.lp-drag-over').forEach(el => el.classList.remove('lp-drag-over'));

    dragState = {
      draggingRow: null,
      sourceKlasId: null,
      sourceSubId: null,
      pekerjaanId: null,
      sourceTbody: null,
      dragOverTarget: null
    };
  }

  function resolveDropTbody(target) {
    if (!target || !(target instanceof Element)) return null;
    if (target.tagName === 'TBODY') return target;
    if (target.tagName === 'TABLE') return target.querySelector('tbody');
    if (target.closest) {
      const tbody = target.closest('tbody');
      if (tbody) return tbody;
      const subCard = target.closest('.lp-sub-card');
      if (subCard) return subCard.querySelector('tbody');
    }
    return null;
  }

  function getDropAreaRect(target, fallbackTbody) {
    if (target instanceof Element) {
      if (target.tagName === 'TABLE' || target.classList.contains('lp-sub-card')) {
        return target.getBoundingClientRect();
      }
    }
    return fallbackTbody?.getBoundingClientRect?.() || null;
  }

  function handleDragStart(e) {
    const row = e.currentTarget;
    if (!row || row.tagName !== 'TR') return;

    // Find parent tbody and its klas/sub
    const tbody = row.closest('tbody');
    if (!tbody) return;

    const subCard = tbody.closest('.lp-sub-card');
    const klasCard = tbody.closest('.lp-klas-card');

    dragState.draggingRow = row;
    dragState.sourceTbody = tbody;
    dragState.sourceSubId = subCard?.dataset.subId || null;
    dragState.sourceKlasId = klasCard?.dataset.klasId || null;
    dragState.pekerjaanId = row.dataset.id || row.id;

    row.classList.add('lp-row-dragging');
    startDragAutoScroll(row, e);

    // Set drag data
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', dragState.pekerjaanId);

    // Set drag image (optional - browser default is fine)
    if (e.dataTransfer.setDragImage) {
      e.dataTransfer.setDragImage(row, 10, 10);
    }

    log('[DRAG] Start:', {
      pekerjaanId: dragState.pekerjaanId,
      klasId: dragState.sourceKlasId,
      subId: dragState.sourceSubId
    });
  }

  function handleDragEnd() {
    log('[DRAG] End');
    resetDragState();
  }

  function handleDragOver(e) {
    if (!dragState.draggingRow) return;
    e.preventDefault(); // Required to allow drop
    e.dataTransfer.dropEffect = 'move';
    updateDragAutoScroll(e, e.currentTarget);

    const tbody = resolveDropTbody(e.currentTarget);
    if (!tbody) return;

    // Highlight valid drop zone
    if (dragState.dragOverTarget !== tbody) {
      // Remove previous highlight
      document.querySelectorAll('.lp-drag-over').forEach(el => el.classList.remove('lp-drag-over'));

      // Add current highlight
      tbody.classList.add('lp-drag-over');
      dragState.dragOverTarget = tbody;
    }
  }

  function handleDragLeave(e) {
    if (!dragState.draggingRow) return;
    const tbody = resolveDropTbody(e.currentTarget);
    if (!tbody) return;

    // Only remove highlight if actually leaving (not just moving to child)
    const rect = getDropAreaRect(e.currentTarget, tbody);
    if (!rect) return;
    const x = e.clientX;
    const y = e.clientY;

    if (x < rect.left || x >= rect.right || y < rect.top || y >= rect.bottom) {
      tbody.classList.remove('lp-drag-over');
      if (dragState.dragOverTarget === tbody) {
        dragState.dragOverTarget = null;
      }
    }
  }

  function handleDrop(e) {
    if (!dragState.draggingRow) return;
    e.preventDefault();
    e.stopPropagation();

    const targetTbody = resolveDropTbody(e.currentTarget);
    if (!targetTbody) {
      resetDragState();
      return;
    }

    const { draggingRow, sourceTbody } = dragState;
    if (!draggingRow) {
      resetDragState();
      return;
    }

    // Find target klas/sub
    const targetSubCard = targetTbody.closest('.lp-sub-card');
    const targetKlasCard = targetTbody.closest('.lp-klas-card');
    const targetSubId = targetSubCard?.dataset.subId || null;
    const targetKlasId = targetKlasCard?.dataset.klasId || null;

    log('[DROP] Target:', {
      targetKlasId,
      targetSubId,
      sourceKlasId: dragState.sourceKlasId,
      sourceSubId: dragState.sourceSubId
    });

    // Determine insert position
    let insertBeforeRow = null;
    const dropY = e.clientY;
    const rows = Array.from(targetTbody.querySelectorAll('tr'));

    for (const row of rows) {
      if (row === draggingRow) continue; // Skip the dragging row itself
      const rect = row.getBoundingClientRect();
      const rowMiddle = rect.top + rect.height / 2;

      if (dropY < rowMiddle) {
        insertBeforeRow = row;
        break;
      }
    }

    // Perform the move
    if (insertBeforeRow) {
      targetTbody.insertBefore(draggingRow, insertBeforeRow);
    } else {
      targetTbody.appendChild(draggingRow);
    }

    // Renumber both source and target tbody
    renum(sourceTbody);
    if (targetTbody !== sourceTbody) {
      renum(targetTbody);
    }

    // Update ordering indices
    updateOrderingIndices(targetTbody);
    if (targetTbody !== sourceTbody) {
      updateOrderingIndices(sourceTbody);
    }

    // Mark as dirty (assuming setDirty exists)
    if (typeof setDirty === 'function') {
      setDirty(true);
    }

    // Rebuild sidebar to reflect changes
    scheduleSidebarRebuild();

    // Show feedback
    const movedWithinSameSub = (targetSubId === dragState.sourceSubId);
    const msg = movedWithinSameSub
      ? 'Urutan pekerjaan diubah'
      : 'Pekerjaan dipindahkan ke sub/klasifikasi lain';

    tShow(msg, 'success');
    say(msg);

    log('[DROP] Complete - moved pekerjaan');
    resetDragState();
  }

  function updateOrderingIndices(tbody) {
    if (!tbody) return;

    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.forEach((row, index) => {
      row.dataset.orderingIndex = String(index + 1);
    });
  }

  function attachDragHandlers(row) {
    if (!row || row.tagName !== 'TR') return;

    row.setAttribute('draggable', 'true');
    row.addEventListener('dragstart', handleDragStart);
    row.addEventListener('dragend', handleDragEnd);
  }

  function attachDropZone(tbody) {
    if (!tbody || tbody.tagName !== 'TBODY') return;
    const table = tbody.closest('table.list-pekerjaan') || tbody.closest('table');

    if (tbody.dataset.dndBound !== '1') {
      tbody.addEventListener('dragover', handleDragOver);
      tbody.addEventListener('dragleave', handleDragLeave);
      tbody.addEventListener('drop', handleDrop);
      tbody.dataset.dndBound = '1';
    }

    // Important: empty tbody often has near-zero height.
    // Bind on table as well so new/unsaved empty sub-kategori tetap bisa jadi target drop.
    if (table && table.dataset.dndBound !== '1') {
      table.addEventListener('dragover', handleDragOver);
      table.addEventListener('dragleave', handleDragLeave);
      table.addEventListener('drop', handleDrop);
      table.dataset.dndBound = '1';
    }
  }

  // ========= [DRAG & DROP] Hierarchy (Klasifikasi/Sub-Klasifikasi) ===========
  let hierarchyDragState = {
    type: null,               // 'klas' | 'sub'
    draggingEl: null,         // HTMLElement being dragged
    overContainer: null,      // Current container under drag
    insertBeforeEl: null,     // Target sibling to insert before
  };

  function resetHierarchyDragState() {
    stopDragAutoScroll();
    document.querySelectorAll('.lp-klas-dragging').forEach(el => el.classList.remove('lp-klas-dragging'));
    document.querySelectorAll('.lp-sub-dragging').forEach(el => el.classList.remove('lp-sub-dragging'));
    document.querySelectorAll('.lp-hierarchy-drag-over').forEach(el => el.classList.remove('lp-hierarchy-drag-over'));
    hierarchyDragState = { type: null, draggingEl: null, overContainer: null, insertBeforeEl: null };
  }

  function getHierarchyContainerFromEvent(e) {
    if (hierarchyDragState.type === 'klas') {
      if (klasWrap && klasWrap.contains(e.target)) return klasWrap;
      return null;
    }
    // sub: allow dropping inside any sub-wrap, or over a klas card (append to its sub-wrap)
    const directSubWrap = e.target.closest('.sub-wrap');
    if (directSubWrap) return directSubWrap;
    const klasCard = e.target.closest('.lp-klas-card');
    return klasCard?.querySelector('.sub-wrap') || null;
  }

  function getInsertBeforeByY(container, draggingEl, y, itemClass) {
    const items = Array.from(container.children)
      .filter(el => el !== draggingEl && el.classList.contains(itemClass));
    for (const item of items) {
      const rect = item.getBoundingClientRect();
      const middle = rect.top + rect.height / 2;
      if (y < middle) return item;
    }
    return null;
  }

  function initHierarchyDragAndDrop() {
    if (!klasWrap) return;

    klasWrap.addEventListener('dragstart', (e) => {
      const klasHandle = e.target.closest('.lp-drag-handle-klas');
      const subHandle = e.target.closest('.lp-drag-handle-sub');
      if (!klasHandle && !subHandle) return;

      const isKlas = !!klasHandle;
      const item = isKlas
        ? klasHandle.closest('.lp-klas-card')
        : subHandle.closest('.lp-sub-card');
      if (!item) return;

      hierarchyDragState.type = isKlas ? 'klas' : 'sub';
      hierarchyDragState.draggingEl = item;
      item.classList.add(isKlas ? 'lp-klas-dragging' : 'lp-sub-dragging');
      startDragAutoScroll(item, e);

      if (e.dataTransfer) {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', item.id || '');
      }
    });

    klasWrap.addEventListener('dragover', (e) => {
      if (!hierarchyDragState.draggingEl) return;
      const container = getHierarchyContainerFromEvent(e);
      if (!container) return;

      e.preventDefault();
      if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
      updateDragAutoScroll(e, container);

      if (hierarchyDragState.overContainer !== container) {
        document.querySelectorAll('.lp-hierarchy-drag-over').forEach(el => el.classList.remove('lp-hierarchy-drag-over'));
        container.classList.add('lp-hierarchy-drag-over');
        hierarchyDragState.overContainer = container;
      }

      hierarchyDragState.insertBeforeEl = getInsertBeforeByY(
        container,
        hierarchyDragState.draggingEl,
        e.clientY,
        hierarchyDragState.type === 'klas' ? 'lp-klas-card' : 'lp-sub-card'
      );
    });

    klasWrap.addEventListener('drop', (e) => {
      if (!hierarchyDragState.draggingEl) return;
      const container = getHierarchyContainerFromEvent(e);
      if (!container) {
        resetHierarchyDragState();
        return;
      }

      e.preventDefault();
      e.stopPropagation();

      const { type, draggingEl, insertBeforeEl } = hierarchyDragState;
      const sourceContainer = draggingEl.parentElement;

      if (insertBeforeEl && insertBeforeEl.parentElement === container) {
        container.insertBefore(draggingEl, insertBeforeEl);
      } else {
        container.appendChild(draggingEl);
      }

      setDirty(true);
      scheduleSidebarRebuild();
      broadcastOrderingChange();

      if (type === 'klas') {
        const moved = sourceContainer !== container ? 'Klasifikasi dipindahkan' : 'Urutan klasifikasi diubah';
        tShow(moved, 'success');
        say(moved);
      } else {
        const moved = sourceContainer !== container ? 'Sub-Klasifikasi dipindahkan' : 'Urutan sub-klasifikasi diubah';
        tShow(moved, 'success');
        say(moved);
      }

      resetHierarchyDragState();
    });

    klasWrap.addEventListener('dragend', () => {
      if (hierarchyDragState.draggingEl) resetHierarchyDragState();
    });
  }

  // ========= [DIAGNOSTICS] Cek Anchor Wajib ==================================
  const REQUIRED = [
    ['#lp-app', !!root],
    ['#klas-list (DIV legacy)', !!klasWrap && klasWrap.tagName !== 'TBODY'],
    ['#btn-add-klas', btnAddKlasAll.length > 0],
    ['#btn-save', btnSaveAll.length > 0],
    ['#btn-compact', btnCompactAll.length > 0],
  ];
  function injectDiagBanner(missingKeys) {
    if (!root) return;
    const id = 'lp-diag-banner';
    if (document.getElementById(id)) return;
    const box = document.createElement('div');
    box.id = id;
    box.style.cssText = 'position:sticky;top:64px;z-index:2000;margin:12px;padding:10px 12px;border-radius:8px;background:#fff3cd;border:1px solid #ffec99;color:#664d03;font:14px/1.4 system-ui;';
    box.innerHTML = `<b>LP Diagnostic:</b> Anchor wajib belum lengkap: <code>${missingKeys.join(', ')}</code>. Fitur terkait dinonaktifkan supaya tidak crash.`;
    root.prepend(box);
  }
  const missing = REQUIRED.filter(([, ok]) => !ok).map(([key]) => key);
  if (missing.length) {
    warn('Missing required anchors:', missing);
    injectDiagBanner(missing);
  } else {
    log('All required anchors OK');
  }

  initHierarchyDragAndDrop();

  // ========= [SIDEBAR] ========================================================
  // Sederhana: buka / tutup. Tidak ada "locked mode" yang kompleks.
  //
  // | Aksi              | Hasil                    |
  // |-------------------|--------------------------|
  // | Klik Navigasi     | Toggle (buka/tutup)      |
  // | Klik X / ESC      | Tutup                    |
  // | Hover masuk       | Buka                     |
  // | Hover keluar      | Tutup (delay 150ms)      |
  //
  const Sidebar = {
    _open: false,
    _timer: null,

    get el() { return document.getElementById('lp-sidebar'); },

    isOpen() { return this._open; },

    open() {
      this._clearTimer();
      if (this._open) return;
      this._open = true;
      this._render();
    },

    close() {
      this._clearTimer();
      if (!this._open) return;
      this._open = false;
      this._render();
    },

    toggle() {
      this._open ? this.close() : this.open();
    },

    // Untuk hover: tutup dengan delay agar tidak flickering
    closeDelayed(ms = 150) {
      this._clearTimer();
      this._timer = setTimeout(() => this.close(), ms);
    },

    _clearTimer() {
      if (this._timer) { clearTimeout(this._timer); this._timer = null; }
    },

    _render() {
      const sb = this.el;
      if (!sb) return;

      sb.classList.toggle('show', this._open);
      sb.classList.toggle('is-open', this._open);
      sb.setAttribute('aria-hidden', String(!this._open));

      // Update tombol
      document.querySelectorAll('.lp-sidebar-toggle, .btn-sidebar-toggle').forEach(btn => {
        btn.setAttribute('aria-expanded', String(this._open));
      });
    }
  };

  // Alias untuk kompatibilitas dengan kode lain
  const SidebarManager = {
    isOpen: () => Sidebar.isOpen(),
    open: () => Sidebar.open(),
    close: () => Sidebar.close(),
    toggle: () => Sidebar.toggle(),
    locked: false // selalu false, tidak ada locked mode
  };

  if (__DEBUG__) window.Sidebar = Sidebar;

  // === EVENT HANDLERS ===

  // Hover (desktop only)
  (function () {
    const isDesktop = () => window.matchMedia('(min-width: 992px)').matches;
    const hotspot = document.querySelector('.lp-overlay-hotspot');
    const sidebar = document.getElementById('lp-sidebar');

    hotspot?.addEventListener('mouseenter', () => { if (isDesktop()) Sidebar.open(); });
    hotspot?.addEventListener('mouseleave', () => { if (isDesktop()) Sidebar.closeDelayed(); });
    sidebar?.addEventListener('mouseenter', () => Sidebar._clearTimer());
    sidebar?.addEventListener('mouseleave', () => { if (isDesktop()) Sidebar.closeDelayed(); });
  })();

  // Klik tombol Navigasi → toggle
  document.addEventListener('click', (e) => {
    if (e.target.closest('.lp-sidebar-toggle, .btn-sidebar-toggle, [data-open="lp-sidebar"]')) {
      e.preventDefault();
      Sidebar.toggle();
    }
  });

  // Klik tombol X → simulasi tekan ESC
  document.addEventListener('click', (e) => {
    if (e.target.closest('[data-action="close-sidebar"]')) {
      e.preventDefault();
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    }
  });

  // ESC → tutup sidebar
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && Sidebar.isOpen()) {
      if (window.jQuery && jQuery(e.target).closest('.select2-container').length) return;
      Sidebar.close();
    }
  });

  // ========= [APP GUARDS] Root & Project Id ==================================
  if (!root || !klasWrap) {
    err('Abort: #lp-app atau #klas-list tidak ditemukan.');
    return;
  }
  const projectId = root.dataset.projectId;
  const REF_YEAR = root.dataset.refYear || null;

  // ========= [HELPERS] Umum ===================================================
  const uid = () => Math.random().toString(36).slice(2, 9);
  function renum(tbody) {
    if (!tbody) return;
    Array.from(tbody.children).forEach((tr, i) => {
      const first = tr.firstElementChild;
      if (first) first.textContent = i + 1;
    });
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }
  function truncateText(str, n = 100) {
    const arr = Array.from(String(str || ""));
    return arr.length > n ? arr.slice(0, n).join('') + '…' : String(str || "");
  }
  function buildSourceLabel(src) {
    if (src === 'ref') return REF_YEAR ? `Ref AHSP ${REF_YEAR}` : 'Ref';
    if (src === 'ref_modified') return REF_YEAR ? `AHSP ${REF_YEAR} (modified)` : 'Ref (modified)';
    return 'Kustom';
  }

  // ========= [AHSP SOURCE SELECTION] ==========================================
  // Global state for available AHSP sources
  let availableAhspSources = [];
  let defaultAhspSource = null;
  let ahspSourcesLoaded = false;

  /**
   * Fetch available AHSP sources from backend.
   * Called once on page init, results cached in module scope.
   */
  async function fetchAhspSources() {
    if (ahspSourcesLoaded) return;
    try {
      const sourcesUrl = document.querySelector('[data-sources-url]')?.dataset.sourcesUrl
        || '/referensi/api/sources';
      const data = await jfetch(sourcesUrl);
      availableAhspSources = data.sources || [];
      defaultAhspSource = data.default || (availableAhspSources[0] || null);
      ahspSourcesLoaded = true;
      log('[AHSP-SRC] Loaded sources:', availableAhspSources, 'default:', defaultAhspSource);
    } catch (e) {
      warn('[AHSP-SRC] Failed to load sources:', e);
      availableAhspSources = [];
      defaultAhspSource = null;
    }
  }

  /**
   * Populate the AHSP source dropdown for a given row.
   * @param {HTMLElement} row - The pekerjaan row element
   * @param {string} [preselect] - Value to preselect (if any)
   */
  function populateAhspSourceDropdown(row, preselect = null) {
    const dropdown = row.querySelector('.ahsp-source-select');
    if (!dropdown) return;

    const selectedValue = preselect || defaultAhspSource || '';
    dropdown.innerHTML = availableAhspSources
      .map(s => {
        const selected = (s === selectedValue) ? ' selected' : '';
        return `<option value="${escapeHtml(s)}"${selected}>${escapeHtml(s)}</option>`;
      })
      .join('');

    // Store in dataset for later reference
    if (selectedValue) {
      row.dataset.ahspSumber = selectedValue;
    }
  }

  /**
   * Update AHSP source dropdown visibility based on mode.
   * - ref / ref_modified: show dropdown
   * - custom: hide dropdown
   */
  function updateAhspSourceVisibility(row) {
    const mode = row.querySelector('.src')?.value || row.dataset.sourceType;
    const dropdown = row.querySelector('.ahsp-source-select');
    if (!dropdown) return;

    const isRefLike = (mode === 'ref' || mode === 'ref_modified');
    dropdown.style.display = isRefLike ? '' : 'none';
    dropdown.disabled = !isRefLike;
  }

  /**
   * Get current AHSP source for a row (from dropdown or dataset).
   */
  function getRowAhspSource(row) {
    const dropdown = row.querySelector('.ahsp-source-select');
    return dropdown?.value || row.dataset.ahspSumber || defaultAhspSource || '';
  }

  // Mapper aman untuk berbagai format respons API → {id, text}
  function mapToSelect2Results(input) {
    try {
      if (!input) return [];
      if (Array.isArray(input)) {
        return input.map(it => ({
          id: String(it.id ?? it.value ?? it.kode_ahsp ?? it.kode ?? it.uid ?? ''),
          text: String(it.text ?? it.label ?? it.nama_ahsp ?? it.nama ?? it.name ?? it.uraian ?? '')
        })).filter(x => x.id && x.text);
      }
      if (Array.isArray(input.results)) return input.results;
      if (Array.isArray(input.items)) {
        return input.items.map(it => ({
          id: String(it.id ?? it.value ?? it.kode_ahsp ?? it.kode ?? it.uid ?? ''),
          text: String(it.text ?? it.label ?? it.nama_ahsp ?? it.nama ?? it.name ?? it.uraian ?? '')
        })).filter(x => x.id && x.text);
      }
      const src = Array.isArray(input.data) ? input.data : Object.values(input);
      if (Array.isArray(src) && src.length && typeof src[0] === 'object') {
        return src.map(it => ({
          id: String(it.id ?? it.pk ?? it.value ?? it.kode_ahsp ?? it.kode ?? it.uid ?? ''),
          text: String(it.text ?? it.label
            ?? (it.kode_ahsp && it.nama_ahsp
              ? `${it.kode_ahsp} — ${it.nama_ahsp}`
              : (it.nama_ahsp ?? it.nama ?? it.name ?? it.uraian ?? '')))
        })).filter(x => x.id && x.text);
      }
      return [];
    } catch (_) { return []; }
  }

  // ========= [URAIAN] Preview 2-baris & Edit =================================
  function autoResize(ta) { if (!ta) return; ta.style.height = 'auto'; ta.style.height = Math.max(ta.scrollHeight, ta.offsetHeight) + 'px'; }
  function syncPreview(td) {
    const ta = td?.querySelector('.uraian');
    const pv = td?.querySelector('.lp-urai-preview');
    if (!ta || !pv) return;
    pv.textContent = (ta.value || '').replace(/\s+$/g, '');
  }
  function enterEdit(td) {
    if (!td) return;
    td.classList.add('is-editing');
    const ta = td.querySelector('.uraian');
    if (!ta) return;
    requestAnimationFrame(() => {
      ta.focus();
      try { const n = ta.value?.length || 0; ta.setSelectionRange(n, n); } catch { }
      autoResize(ta);
    });
  }
  function applyUraianGate(td) {
    const tr = td.closest('tr'); if (!tr) return;
    const src = tr.dataset.sourceType || '';
    const ta = td.querySelector('.uraian');
    const pv = td.querySelector('.lp-urai-preview');
    if (!ta || !pv) return;

    const editable = (src === 'custom' || src === 'ref_modified');
    ta.readOnly = !editable;
    ta.tabIndex = editable ? 0 : -1;
    pv.style.cursor = editable ? 'text' : 'default';
  }
  function setupUraianInteractivity(scope = document) {
    // dukung selector lama (td.col-urai) dan baru
    scope.querySelectorAll('td.col-urai, #lp-table tbody td:nth-child(4)').forEach((td) => {
      const ta = td.querySelector('.uraian');
      let pv = td.querySelector('.lp-urai-preview');
      if (!ta) return;
      if (!pv) { pv = document.createElement('div'); pv.className = 'lp-urai-preview'; td.prepend(pv); }
      syncPreview(td); autoResize(ta); applyUraianGate(td);
      pv.onclick = () => enterEdit(td);
      ta.addEventListener('input', () => { autoResize(ta); syncPreview(td); setDirty(true); });
      ta.addEventListener('focus', () => td.classList.add('is-editing'));
      ta.addEventListener('blur', () => { td.classList.remove('is-editing'); syncPreview(td); });
    });
  }
  document.addEventListener('DOMContentLoaded', () => {
    setupUraianInteractivity(document);
    try { setupRightHoverEdge(); } catch (_) { }
    // Fetch available AHSP sources for dropdown population
    fetchAhspSources().catch(e => warn('[AHSP-SRC] Init fetch failed:', e));
  });

  // ========= [BUILDERS] Klas / Sub / Row =====================================
  let kCounter = 0;

  function newKlas(prefillName = null) {
    kCounter++;
    const id = `k_${Date.now()}_${uid()}`;
    const div = document.createElement('div');
    div.className = 'card shadow-sm lp-klas-card';
    div.id = id;
    div.dataset.anchorId = id;
    div.dataset.klasId = id;

    div.innerHTML = `
      <div class="card-header d-flex gap-2 align-items-center">
        <button class="btn btn-sm btn-outline-secondary lp-collapse-toggle" type="button"
          data-target="sub-wrap" aria-expanded="true" title="Collapse/Expand">
          <i class="bi bi-caret-down-fill"></i>
        </button>
        <button class="btn btn-sm btn-outline-secondary lp-drag-handle lp-drag-handle-klas" type="button" title="Drag Klasifikasi" draggable="true">
          <i class="bi bi-grip-vertical"></i>
        </button>
        <input class="form-control klas-name" placeholder="Nama Klasifikasi (auto: Klasifikasi ${kCounter})" value="${prefillName ? escapeHtml(prefillName) : ''}">
        <button class="btn btn-primary btn-add-sub lp-btn lp-btn-wide" type="button">
          <i class="bi bi-plus-circle"></i> Sub-Klasifikasi
        </button>
        <button class="btn btn-outline-danger btn-del lp-btn" type="button">Hapus</button>
      </div>
      <div class="card-body vstack gap-2 sub-wrap"></div>`;

    div.dataset.tempId = `k${kCounter}_${Date.now()}`;
    const subWrap = div.querySelector('.sub-wrap');
    div.querySelector('.btn-add-sub').onclick = () => { addSub(subWrap); scheduleSidebarRebuild(); };
    div.querySelector('.btn-del').onclick = () => { div.remove(); scheduleSidebarRebuild(); setDirty(true); };
    div.querySelector('.klas-name').addEventListener('input', () => { scheduleSidebarRebuild(); setDirty(true); });

    // Collapse toggle for Klasifikasi
    const toggleBtn = div.querySelector('.lp-collapse-toggle');
    toggleBtn?.addEventListener('click', () => {
      const isExpanded = toggleBtn.getAttribute('aria-expanded') === 'true';
      toggleBtn.setAttribute('aria-expanded', !isExpanded);
      toggleBtn.querySelector('i').className = isExpanded ? 'bi bi-caret-right-fill' : 'bi bi-caret-down-fill';
      subWrap.style.display = isExpanded ? 'none' : '';
    });

    klasWrap.appendChild(div);
    requestAnimationFrame(() => {
      div.scrollIntoView({ behavior: 'smooth', block: 'start' });
      div.classList.add('lp-flash');
      const inp = div.querySelector('.klas-name'); inp?.focus();
      say('Klasifikasi ditambahkan'); tbAnnounce && (tbAnnounce.textContent = 'Klasifikasi ditambahkan');
    });
    lastKlasTarget = div;
    scheduleSidebarRebuild();
    return div;
  }

  function addSub(container, options = {}) {
    const { name = null } = options;
    const id = `s_${Date.now()}_${uid()}`;
    const block = document.createElement('div');
    block.className = 'border rounded p-2 lp-sub-card';
    block.id = id;
    block.dataset.anchorId = id;
    block.dataset.subId = id;

    block.innerHTML = `
    <div class="d-flex gap-2 align-items-center mb-2 lp-sub-header">
      <button class="btn btn-sm btn-outline-secondary lp-collapse-toggle" type="button"
        data-target="lp-sub-body" aria-expanded="true" title="Collapse/Expand">
        <i class="bi bi-caret-down-fill"></i>
      </button>
      <button class="btn btn-sm btn-outline-secondary lp-drag-handle lp-drag-handle-sub" type="button" title="Drag Sub-Klasifikasi" draggable="true">
        <i class="bi bi-grip-vertical"></i>
      </button>
      <input class="form-control sub-name" placeholder="Nama Sub-Klasifikasi (mis. 1.1)" value="${name ? escapeHtml(name) : ''}">
      <button class="btn btn-primary btn-add-pekerjaan lp-btn lp-btn-wide" type="button">
        <i class="bi bi-plus-circle"></i> Pekerjaan
      </button>
      <button class="btn btn-outline-danger btn-del" type="button">Hapus</button>
    </div>
    <table class="table mb-0 list-pekerjaan lp-table">
      <!-- SSOT: kolom & rasio pakai colgroup; CSS memberi width via var -->
      <colgroup>
        <col class="col-num">
        <col class="col-mode">
        <col class="col-ref">
        <col class="col-urai">
        <col class="col-sat">
        <col class="col-act">
      </colgroup>
      <thead>
        <tr>
          <th class="col-num">No</th>
          <th class="col-mode">Sumber</th>
          <th class="col-ref">Referensi AHSP</th>
          <th class="col-urai">Uraian Pekerjaan</th>
          <th class="col-sat">Satuan</th>
          <th class="col-act"></th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>`;

    block.dataset.tempId = `s${Date.now()}_${Math.random().toString(16).slice(2)}`;
    const tbody = block.querySelector('tbody');

    // Attach drop zone handlers to tbody for drag-and-drop
    attachDropZone(tbody);

    block.querySelector('.btn-add-pekerjaan').onclick = () => { addPekerjaan(tbody); scheduleSidebarRebuild(); };
    block.querySelector('.btn-del').onclick = () => { block.remove(); scheduleSidebarRebuild(); setDirty(true); };
    block.querySelector('.sub-name').addEventListener('input', () => { scheduleSidebarRebuild(); setDirty(true); });

    // Collapse toggle for Sub-klasifikasi
    const subToggleBtn = block.querySelector('.lp-collapse-toggle');
    const tableWrap = block.querySelector('table');
    subToggleBtn?.addEventListener('click', () => {
      const isExpanded = subToggleBtn.getAttribute('aria-expanded') === 'true';
      subToggleBtn.setAttribute('aria-expanded', !isExpanded);
      subToggleBtn.querySelector('i').className = isExpanded ? 'bi bi-caret-right-fill' : 'bi bi-caret-down-fill';
      tableWrap.style.display = isExpanded ? 'none' : '';
    });

    container.appendChild(block);
    requestAnimationFrame(() => {
      block.scrollIntoView({ behavior: 'smooth', block: 'start' });
      block.classList.add('lp-flash');
      const inp = block.querySelector('.sub-name'); inp?.focus();
      say('Sub-Klasifikasi ditambahkan'); tbAnnounce && (tbAnnounce.textContent = 'Sub-Klasifikasi ditambahkan');
    });
    scheduleSidebarRebuild();
    return block;
  }

  function preselectSelect2($sel, id, labelText) {
    if (!id) return;
    const text = labelText || String(id);
    withDirtySuppressed(() => {
      const opt = new Option(text, String(id), true, true);
      $sel.empty().append(opt).trigger('change');
    });
  }

  function addPekerjaan(tbody, preset = {}, opts = {}) {
    const { autofocus = true } = opts;
    const {
      mode = 'ref',
      ref_id = null,
      ref_label = null,
      uraian = '',
      satuan = '',
      snapshot_kode = null,
      snapshot_uraian = null
    } = preset;

    const S2_TRUNC = 150;
    const pid = `p_${Date.now()}_${uid()}`;
    let row;

    const tpl = document.getElementById('tpl-pekerjaan-row-table');
    if (tpl && tpl.content) {
      row = tpl.content.firstElementChild.cloneNode(true);
      row.id = pid;
      row.dataset.anchorId = pid;
      row.querySelector('.current-ref')?.remove();
    } else {
      row = document.createElement('tr');
      row.id = pid;
      row.dataset.anchorId = pid;
      row.innerHTML = `
        <td class="col-num"></td>
        <td class="col-mode">
          <div class="vstack gap-1">
            <select class="form-select src" aria-label="Pilih sumber pekerjaan">
              <option value="ref">Referensi</option>
              <option value="ref_modified">Referensi (Dimodifikasi)</option>
              <option value="custom">Kustom</option>
            </select>
            <span class="source-badge badge rounded-pill text-bg-secondary source-hint"></span>
          </div>
        </td>
        <td class="col-ref">
          <div class="vstack gap-1">
            <div class="select2-host">
              <select class="form-select ref-select native-select" style="width:100%" aria-label="Cari referensi AHSP"></select>
            </div>
          </div>
        </td>
        <td class="col-urai">
          <div class="lp-urai-preview"></div>
          <textarea class="form-control uraian" rows="2" placeholder="Uraian pekerjaan"></textarea>
        </td>
        <td class="col-sat">
          <input class="form-control satuan" placeholder="cth: m, m2, m3, unit">
        </td>
        <td class="col-act">
          <button class="btn btn-outline-danger btn-del" title="Hapus baris">
            <i class="bi bi-x-lg" aria-hidden="true"></i>
            <span class="visually-hidden">Hapus</span>
          </button>
        </td>`;
    }

    // gate editing via dataset
    row.dataset.sourceType = mode || 'ref';
    if (ref_id) row.dataset.refId = String(ref_id);

    // BUGFIX: Store original values for comparison during save
    // This prevents false-negative change detection when dataset.refId
    // is updated immediately on select2:select event
    row.dataset.originalSourceType = mode || 'ref';
    if (ref_id) row.dataset.originalRefId = String(ref_id);

    if (tbody) tbody.appendChild(row);
    renum(tbody);

    row.querySelector('.btn-del')?.addEventListener('click', () => {
      row.remove(); renum(tbody); scheduleSidebarRebuild(); setDirty(true);
    });

    const srcSel = row.querySelector('.src');
    if (srcSel) srcSel.value = mode;

    // ----- AHSP Source dropdown init -----
    const ahspSrcSel = row.querySelector('.ahsp-source-select');
    if (ahspSrcSel && ahspSourcesLoaded) {
      // Populate dropdown with available sources
      populateAhspSourceDropdown(row, preset.ahsp_sumber || null);
      // Set initial visibility based on mode
      updateAhspSourceVisibility(row);

      // Event: when source changes, clear current reference and notify user
      ahspSrcSel.addEventListener('change', () => {
        row.dataset.ahspSumber = ahspSrcSel.value;
        // Clear current reference selection since source changed
        if (HAS_S2 && $sel && $sel.length && $sel.val()) {
          $sel.val(null).trigger('change');
          delete row.dataset.refId;
          tShow('Referensi di-reset karena sumber AHSP berubah', 'info');
        } else if (selEl && selEl.value) {
          selEl.value = '';
          delete row.dataset.refId;
          tShow('Referensi di-reset karena sumber AHSP berubah', 'info');
        }
        setDirty(true);
      });
    }

    // ----- Select2 init (dengan guard jQuery/Select2) -----
    let host, $sel;
    const selEl = row.querySelector('.ref-select');
    const ajaxUrl = selEl?.dataset.ajaxUrl || '/referensi/api/search';
    const minLen = Number(selEl?.dataset.minlength || 2);
    const placeholder = selEl?.dataset.placeholder || 'Cari referensi kode/nama…';

    if (HAS_JQ) {
      host = $(row).find('.select2-host');
      $sel = $(row).find('.ref-select');
    }

    if (HAS_S2 && $sel && $sel.length) {
      $sel.select2({
        width: '100%',
        placeholder,
        allowClear: false,
        minimumInputLength: minLen,
        dropdownAutoWidth: true,
        dropdownParent: host,
        ajax: {
          delay: 140,
          transport: function (params, success, failure) {
            const q = params.data && params.data.q ? params.data.q : '';
            // Include AHSP sumber filter from row dropdown
            const sumber = getRowAhspSource(row);
            const urlParams = new URLSearchParams({ q });
            if (sumber) urlParams.set('sumber', sumber);
            fetch(`${ajaxUrl}?${urlParams.toString()}`, { credentials: 'same-origin' })
              .then(r => r.json())
              .then(json => success({ results: mapToSelect2Results(json) }))
              .catch(failure);
          },
          processResults: function (data) { return data; }
        },
        closeOnSelect: true,
        templateResult: function (item) {
          if (item.loading) return item.text;
          return $(
            `<div class="s2-option">
              <div class="s2-title">${escapeHtml(item.text || '')}</div>
            </div>`
          );
        },
        templateSelection: function (item) {
          const full = item.text || '';
          const short = truncateText(full, S2_TRUNC);
          return $(`<div class="s2-selection-wrap" title="${escapeHtml(full)}">${escapeHtml(short)}</div>`);
        },
        dropdownCssClass: 's2-dropdown-wrap',
        selectionCssClass: 's2-selection-compact'
      });

      $sel.on('select2:open', function () {
        $('.select2-host.s2-open').removeClass('s2-open');
        host.addClass('s2-open');
        setTimeout(() => { try { $('.select2-container--open .select2-search__field').trigger('focus'); } catch { } }, 0);

        // blokir Enter agar tidak bentrok dengan shortcut global
        const $input = $('.select2-container--open .select2-search__field');
        $input.on('keydown.lpEnter', (ev) => {
          if (ev.key === 'Enter') { ev.stopImmediatePropagation(); }
        });
        $sel.one('select2:close', () => $input.off('keydown.lpEnter'));
      });

      $sel.on('select2:close', function () { host.removeClass('s2-open'); });

      row.querySelector('.ref-select')?.classList.add('is-enhanced');

      // Clear via Delete/Backspace pada selection
      const $selection = host.find('.select2-selection');
      $selection.on('keydown', function (e) {
        if ((e.key === 'Delete' || e.key === 'Backspace') && $sel.val()) {
          $sel.val(null).trigger('change'); e.preventDefault(); e.stopPropagation();
        }
      });

      $sel.on('select2:open', function () {
        const $input = $('.select2-container--open .select2-search__field');
        const onKey = (e) => {
          if ((e.key === 'Delete' || e.key === 'Backspace') && !$input.val() && $sel.val()) {
            $sel.val(null).trigger('change'); $sel.select2('close'); e.preventDefault(); e.stopPropagation();
          }
        };
        $input.on('keydown.lpClear', onKey);
        $sel.one('select2:close', () => $input.off('keydown.lpClear', onKey));
      });

      // set dataset.refId & seed uraian saat ref_modified
      $sel.on('select2:select', function () {
        const v = $sel.val();
        if (v) row.dataset.refId = String(v);
        const srcNow = srcSel?.value;
        const ta = row.querySelector('.uraian');
        if (srcNow === 'ref_modified' && ta && !ta.value) {
          const item = $sel.select2('data')[0];
          const full = item?.text ? String(item.text) : '';
          const parts = full.split('—');
          const ura = parts.length > 1 ? parts.slice(1).join('—').trim() : '';
          if (ura) { ta.value = ura; }
          const td = row.querySelector('td.col-urai, #lp-table tbody td:nth-child(4)');
          syncPreview(td || row);
          autoResize(ta);
        }
      });
      // kosongkan dataset.refId saat clear
      $sel.on('change', function () {
        if (!$sel.val()) { delete row.dataset.refId; }
        setDirty(true);
      });

    } else {
      // Tanpa jQuery/Select2: biarkan native select terlihat & aktif
      if (selEl) {
        selEl.classList.remove('is-enhanced');
        selEl.removeAttribute('style');
        selEl.disabled = false;
      }
      warn('Select2 belum tersedia saat init baris; lanjut tanpa enhance');
    }

    // Preselect jika ada ref_id
    if (ref_id) {
      const lbl = ref_label
        || (snapshot_kode && snapshot_uraian
          ? `${snapshot_kode || ''}${snapshot_kode && snapshot_uraian ? ' — ' : ''}${snapshot_uraian || ''}`
          : null);
      if (HAS_S2 && $sel && $sel.length) {
        preselectSelect2($sel, ref_id, lbl);
      } else if (selEl) {
        const opt = document.createElement('option');
        opt.value = String(ref_id); opt.textContent = lbl || String(ref_id);
        opt.selected = true;
        selEl.innerHTML = ''; selEl.appendChild(opt);
      }
    }

    const uraianInput = row.querySelector('.uraian');
    const satuanInput = row.querySelector('.satuan');
    const sourceHint = row.querySelector('.source-hint');

    if (uraian && uraianInput) uraianInput.value = uraian;
    if (satuan && satuanInput) satuanInput.value = satuan;

    function syncFields() {
      const v = srcSel?.value;
      const oldSourceType = row.dataset.sourceType;  // Save old value before update
      row.dataset.sourceType = v || '';
      const isCustom = (v === 'custom');
      const isRefLike = (v === 'ref' || v === 'ref_modified');

      // AUTO-RESET: Reset uraian/satuan when changing FROM custom TO ref/ref_modified
      // User expects fields to clear when switching from CUSTOM to REF
      if (oldSourceType === 'custom' && isRefLike) {
        if (uraianInput) {
          uraianInput.value = '';
          autoResize(uraianInput);  // Resize textarea after clear
        }
        if (satuanInput) satuanInput.value = '';
        // Trigger preview update
        const td = row.querySelector('td.col-urai, #lp-table tbody td:nth-child(4)');
        if (td) syncPreview(td);
      }

      if (uraianInput) uraianInput.readOnly = !(isCustom || v === 'ref_modified');
      if (satuanInput) satuanInput.readOnly = !isCustom;

      if (HAS_S2 && $sel && $sel.length) {
        $sel.prop('disabled', !isRefLike).trigger('change.select2');
        if (!isRefLike && $sel.val()) {
          $sel.val(null).trigger('change');
          delete row.dataset.refId;
        }
      } else if (selEl) {
        selEl.disabled = !isRefLike;
        if (!isRefLike && selEl.value) {
          selEl.value = '';
          delete row.dataset.refId;
        }
      }

      if (sourceHint) sourceHint.textContent = buildSourceLabel(v);
      // Update AHSP source dropdown visibility based on mode
      updateAhspSourceVisibility(row);
      row.querySelector('.current-ref')?.remove();

      const td = row.querySelector('td.col-urai, #lp-table tbody td:nth-child(4)');
      if (td) { applyUraianGate(td); syncPreview(td); }
    }

    // Interaksi kolom uraian
    setupUraianInteractivity(row);

    // Autofocus UX saat tambah baru (bukan saat loadTree)
    if (autofocus) {
      requestAnimationFrame(() => {
        row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        const srcNow = srcSel?.value;
        if (srcNow === 'ref' || srcNow === 'ref_modified') {
          if (HAS_JQ) {
            const $selEl = $(row).find('.ref-select');
            $selEl.select2 ? $selEl.select2('open') : row.querySelector('.ref-select')?.focus();
          } else {
            row.querySelector('.ref-select')?.focus();
          }
        } else {
          row.querySelector('.uraian')?.focus();
        }
        row.classList.add('lp-flash');
        say('Pekerjaan ditambahkan');
        tbAnnounce && (tbAnnounce.textContent = 'Pekerjaan ditambahkan');
      });
    }

    if (HAS_S2 && $sel && $sel.length) {
      $sel.on('select2:select', function () {
        setDirty(true);
        if (srcSel?.value === 'ref_modified' && uraianInput && !uraianInput.value) {
          const item = $sel.select2('data')[0];
          const text = item?.text ? String(item.text) : '';
          const parts = text.split('—');
          const ura = parts.length > 1 ? parts.slice(1).join('—').trim() : '';
          if (ura) uraianInput.value = ura;
          const td = row.querySelector('td.col-urai, #lp-table tbody td:nth-child(4)');
          if (td) { syncPreview(td); autoResize(uraianInput); }
        }
      });
    }

    srcSel?.addEventListener('change', () => { syncFields(); setDirty(true); });
    syncFields();

    uraianInput?.addEventListener('input', () => { scheduleSidebarRebuild(); setDirty(true); });
    satuanInput?.addEventListener('input', () => { scheduleSidebarRebuild(); setDirty(true); });

    scheduleSidebarRebuild();

    // Attach drag-and-drop handlers to make row draggable
    attachDragHandlers(row);

    return row;
  }

  function collectTree() {
    const data = [];
    if (!klasWrap) return data;
    const kCards = Array.from(klasWrap.children).filter(el => el?.querySelector && el.querySelector('.sub-wrap'));
    kCards.forEach((kc, ki) => {
      const kName = kc.querySelector('.klas-name')?.value?.trim()
        || kc.dataset.title || kc.getAttribute?.('data-title') || `Klasifikasi ${ki + 1}`;
      const kAnchor = kc.dataset.anchorId || kc.id || `k_auto_${ki + 1}`;
      const nodeK = { id: kAnchor, name: kName, sub: [] };

      const subWrap = kc.querySelector('.sub-wrap');
      Array.from(subWrap?.children || []).forEach((sb, si) => {
        const sName = sb.querySelector('.sub-name')?.value?.trim() || `Sub ${ki + 1}.${si + 1}`;
        const sAnchor = sb.dataset.anchorId || sb.id || `s_auto_${ki + 1}_${si + 1}`;
        const nodeS = { id: sAnchor, name: sName, pekerjaan: [] };

        const rows = sb.querySelectorAll('tbody tr');
        Array.from(rows || []).forEach((tr, pi) => {
          const uraian = tr.querySelector('.uraian')?.value?.trim()
            || tr.querySelector('.current-ref .ref-uraian')?.textContent?.trim()
            || `Pekerjaan ${pi + 1}`;
          const pAnchor = tr.dataset.anchorId || tr.id || `p_auto_${ki + 1}_${si + 1}_${pi + 1}`;
          nodeS.pekerjaan.push({ id: pAnchor, name: uraian });
        });

        nodeK.sub.push(nodeS);
      });

      data.push(nodeK);
    });
    return data;
  }

  function scheduleSidebarRebuild() {
    clearTimeout(scheduleSidebarRebuild._tid);
    scheduleSidebarRebuild._tid = setTimeout(buildMiniToc, 120);
  }

  // ====== MINI TOC: Build compact navigation tree =====================
  function buildMiniToc() {
    if (!tocTree) return;
    try {
      const data = collectTree();
      const filterText = (tocSearch?.value || '').toLowerCase().trim();

      // Calculate stats
      let totalKlas = 0, totalSub = 0, totalPkj = 0;
      data.forEach(K => {
        totalKlas++;
        (K.sub || []).forEach(S => {
          totalSub++;
          totalPkj += (S.pekerjaan || []).length;
        });
      });

      // Update stats display
      if (tocStats) {
        tocStats.innerHTML = `<i class="bi bi-diagram-3 me-1"></i>${totalKlas} Klas · ${totalSub} Sub · ${totalPkj} Pkj`;
      }

      // Build tree HTML - compact 3-level tree
      if (!Array.isArray(data) || data.length === 0) {
        tocTree.innerHTML = '<div class="text-muted small px-2 py-3 text-center">Belum ada klasifikasi</div>';
        return;
      }

      // Filter matching function
      const matchFilter = (text) => !filterText || text.toLowerCase().includes(filterText);

      // Generate tree with all 3 levels
      const html = data.map(K => {
        const subMatches = (K.sub || []).some(S =>
          matchFilter(S.name) || (S.pekerjaan || []).some(P => matchFilter(P.name))
        );
        const klasMatch = matchFilter(K.name) || subMatches;
        if (!klasMatch && filterText) return '';

        const subHtml = (K.sub || []).map(S => {
          const pkjMatches = (S.pekerjaan || []).filter(P => matchFilter(P.name));
          const subMatch = matchFilter(S.name) || pkjMatches.length > 0;
          if (!subMatch && filterText) return '';

          // Render pekerjaan (3rd level) - compact single line items
          const pkjHtml = (S.pekerjaan || []).map(P => {
            if (filterText && !matchFilter(P.name)) return '';
            const truncName = truncateText(P.name, 45);
            return `
              <div class="lp-toc-item" data-anchor="${escapeHtml(P.id)}" title="${escapeHtml(P.name)}">
                <span class="lp-toc-bullet">·</span>
                <span class="lp-toc-text">${escapeHtml(truncName)}</span>
              </div>`;
          }).filter(Boolean).join('');

          return `
            <div class="lp-toc-node lp-toc-sub" data-sub-id="${escapeHtml(S.id)}">
              <div class="lp-toc-header" data-anchor="${escapeHtml(S.id)}">
                <span class="lp-toc-toggle">▸</span>
                <span class="lp-toc-label" title="${escapeHtml(S.name)}">${escapeHtml(truncateText(S.name, 35))}</span>
                <span class="lp-toc-badge">${(S.pekerjaan || []).length}</span>
              </div>
              <div class="lp-toc-children" style="display:none;">
                ${pkjHtml}
              </div>
            </div>`;
        }).filter(Boolean).join('');

        return `
          <div class="lp-toc-node lp-toc-klas" data-klas-id="${escapeHtml(K.id)}">
            <div class="lp-toc-header" data-anchor="${escapeHtml(K.id)}">
              <span class="lp-toc-toggle">▸</span>
              <span class="lp-toc-label" title="${escapeHtml(K.name)}">${escapeHtml(truncateText(K.name, 30))}</span>
              <span class="lp-toc-badge">${(K.sub || []).length}</span>
            </div>
            <div class="lp-toc-children" style="display:none;">
              ${subHtml}
            </div>
          </div>`;
      }).filter(Boolean).join('');

      tocTree.innerHTML = html || '<div class="text-muted small px-2 py-3 text-center">Tidak ada hasil</div>';

      // Bind click events
      tocTree.querySelectorAll('.lp-toc-header, .lp-toc-item').forEach(el => {
        el.addEventListener('click', (e) => {
          const anchor = el.dataset.anchor;

          // If clicking on toggle area of header, toggle children
          if (el.classList.contains('lp-toc-header')) {
            const node = el.closest('.lp-toc-node');
            const children = node?.querySelector('.lp-toc-children');
            const toggle = el.querySelector('.lp-toc-toggle');

            if (e.target === toggle || e.target.closest('.lp-toc-toggle')) {
              // Toggle only
              if (children) {
                const isOpen = children.style.display !== 'none';
                children.style.display = isOpen ? 'none' : '';
                if (toggle) toggle.textContent = isOpen ? '▸' : '▾';
              }
              return;
            }
          }

          // Navigate to anchor
          if (anchor) {
            scrollToAnchor(anchor);
          }
        });
      });

      // Auto-expand if search is active
      if (filterText) {
        tocTree.querySelectorAll('.lp-toc-children').forEach(c => c.style.display = '');
        tocTree.querySelectorAll('.lp-toc-toggle').forEach(t => t.textContent = '▾');
      }

    } catch (e) {
      err('buildMiniToc failed:', e);
    }
  }

  // TOC search filter
  let tocSearchTimer = null;
  tocSearch?.addEventListener('input', () => {
    clearTimeout(tocSearchTimer);
    tocSearchTimer = setTimeout(buildMiniToc, 150);
  });

  // Expand/Collapse All buttons
  tocExpandAll?.addEventListener('click', () => {
    tocTree?.querySelectorAll('.lp-toc-children').forEach(c => c.style.display = '');
    tocTree?.querySelectorAll('.lp-toc-toggle').forEach(t => t.textContent = '▾');
    say('Semua bagian terbuka');
  });
  tocCollapseAll?.addEventListener('click', () => {
    tocTree?.querySelectorAll('.lp-toc-children').forEach(c => c.style.display = 'none');
    tocTree?.querySelectorAll('.lp-toc-toggle').forEach(t => t.textContent = '▸');
    say('Semua bagian tertutup');
  });

  // Toolbar search handling (kept for backwards compat)
  function handleToolbarSearch() {
    const q = (navSearchToolbar?.value || '').toLowerCase().trim();
    if (!q) return;
    const tree = collectTree();
    // Find first match and scroll
    for (const K of tree) {
      if (K.name.toLowerCase().includes(q)) {
        scrollToAnchor(K.id);
        return;
      }
      for (const S of (K.sub || [])) {
        if (S.name.toLowerCase().includes(q)) {
          scrollToAnchor(S.id);
          return;
        }
        for (const P of (S.pekerjaan || [])) {
          if (P.name.toLowerCase().includes(q)) {
            scrollToAnchor(P.id);
            return;
          }
        }
      }
    }
    tShow('Tidak ditemukan: ' + q, 'warning');
  }

  navSearchToolbar?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); handleToolbarSearch(); }
  });
  document.getElementById('lp-toolbar-find')
    ?.addEventListener('click', handleToolbarSearch);

  // (Old suggest initialization removed - Mini TOC doesn't use suggest boxes)

  function scrollToAnchor(anchorId) {
    const target = document.getElementById(anchorId);
    if (!target) return;
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    target.classList.remove('lp-flash'); void target.offsetWidth; target.classList.add('lp-flash');
    // Tutup sidebar setelah navigasi
    Sidebar.close();
  }

  // ========= [LOAD & SAVE] ====================================================
  async function loadTree() {
    try {
      if (!projectId) {
        if (!klasWrap.querySelector('.sub-wrap')) newKlas();
        scheduleSidebarRebuild();
        return;
      }

      const url = `/detail_project/api/project/${projectId}/list-pekerjaan/tree/`;
      const data = await jfetch(url, { method: 'GET' });
      const list = data?.klasifikasi;

      if (!list || !Array.isArray(list) || list.length === 0) {
        if (!klasWrap.querySelector('.sub-wrap')) newKlas();
        scheduleSidebarRebuild();
        return;
      }

      list.forEach(k => {
        const kCard = newKlas(k.name || null);
        if (k.id) {
          kCard.dataset.id = k.id;
          kCard.dataset.klasId = String(k.id);
        }
        const subWrap = kCard.querySelector('.sub-wrap');
        (k.sub || []).forEach(s => {
          const subBlock = addSub(subWrap, { name: s.name || null });
          if (s.id) {
            subBlock.dataset.id = s.id;
            subBlock.dataset.subId = String(s.id);
          }
          const tbody = subBlock.querySelector('tbody');
          (s.pekerjaan || []).forEach(p => {
            const row = addPekerjaan(tbody, {
              mode: p.source_type || 'ref',
              ref_id: p.ref_id || null,
              ref_label: (p.snapshot_kode || p.snapshot_uraian)
                ? `${p.snapshot_kode || ''}${p.snapshot_kode && p.snapshot_uraian ? ' — ' : ''}${p.snapshot_uraian || ''}`
                : null,
              uraian: p.snapshot_uraian || '',
              satuan: p.snapshot_satuan || '',
              snapshot_kode: p.snapshot_kode || null,
              snapshot_uraian: p.snapshot_uraian || null
            },
              { autofocus: false });
            if (p.id) row.dataset.id = p.id;
          });
        });
      });

      if (!klasWrap.querySelector('.sub-wrap')) newKlas();
      scheduleSidebarRebuild();

      setupScrollSpy();
    } catch (e) {
      err(e);
      tShow('Gagal memuat data.', 'danger');
      if (!klasWrap.querySelector('.sub-wrap')) newKlas();
      scheduleSidebarRebuild();
    }
  }

  async function handleSave() {
    if (!projectId) {
      tShow('Project ID tidak ditemukan.', 'error');
      return;
    }

    const btn = document.querySelector('#btn-save');
    const orig = btn?.textContent;
    btn?.setAttribute('disabled', 'true');
    if (btn) btn.textContent = 'Menyimpan…';

    const payload = { klasifikasi: [] };
    let hasError = false;
    let globalOrder = 0; // ordering_index global per project (server mengharapkan ini)

    const kCards = Array.from(klasWrap.children).filter(el => el?.querySelector && el.querySelector('.sub-wrap'));

    kCards.forEach((kc, ki) => {
      const subWrap = kc.querySelector('.sub-wrap');
      const kNameRaw = (kc.querySelector('.klas-name')?.value || '').trim();
      const hasAnySub = subWrap && subWrap.children.length > 0;
      if (!hasAnySub && !kNameRaw) return;

      const kCode = `K${ki + 1}`;
      const kName = kNameRaw || kCode;

      const k = {
        id: kc.dataset.id ? parseInt(kc.dataset.id, 10) : undefined,
        temp_id: kc.dataset.tempId,
        name: kName,
        ordering_index: ki + 1,
        sub: []
      };

      Array.from(subWrap?.children || []).forEach((sb, si) => {
        const rows = sb.querySelectorAll('tbody tr');
        const sNameRaw = (sb.querySelector('.sub-name')?.value || '').trim();
        if (!rows.length && !sNameRaw) return;

        const sName = sNameRaw || `${kCode}.${si + 1}`;

        const s = {
          id: sb.dataset.id ? parseInt(sb.dataset.id, 10) : undefined,
          temp_id: sb.dataset.tempId,
          name: sName,
          ordering_index: si + 1,
          pekerjaan: []
        };

        rows.forEach(tr => {
          const src = tr.querySelector('.src')?.value;

          // Baca nilai select2/native tanpa bergantung pada jQuery
          let refRaw;
          if (HAS_JQ) {
            refRaw = $(tr).find('.ref-select').val();
          } else {
            refRaw = tr.querySelector('.ref-select')?.value ?? '';
          }

          const uraian = (tr.querySelector('.uraian')?.value || '').trim();
          const satuan = (tr.querySelector('.satuan')?.value || '').trim();

          let invalid = false;
          let refIdNum = null;

          if (src === 'custom') {
            if (!uraian) invalid = true;
          } else {
            if (refRaw == null || refRaw === '') invalid = true;
            else {
              refIdNum = Number.parseInt(String(refRaw), 10);
              if (Number.isNaN(refIdNum)) invalid = true;
            }
          }

          if (invalid) {
            hasError = true;
            tr.classList.add('table-danger');
            return;
          } else {
            tr.classList.remove('table-danger');
          }

          globalOrder += 1;

          const existingId = tr.dataset.id ? parseInt(tr.dataset.id, 10) : undefined;
          // BUGFIX: Use originalRefId (set at load) instead of refId (updated on select)
          const originalRefId = (tr.dataset.originalRefId ?? null);
          const originalSourceType = (tr.dataset.originalSourceType ?? 'custom');
          const isRefChanged = (refIdNum != null) && (String(refIdNum) !== String(originalRefId ?? ''));

          const p = {
            id: existingId,
            temp_id: `p_${ki}_${si}_${globalOrder}`,
            source_type: src,
            ordering_index: globalOrder
          };

          if (src === 'custom') {
            p.snapshot_uraian = uraian;
            if (satuan) p.snapshot_satuan = satuan;
          } else if (src === 'ref_modified') {
            // BUGFIX: Always send ref_id if:
            // 1. New pekerjaan (!existingId)
            // 2. ref_id changed (isRefChanged)
            // 3. Source type changed (originalSourceType !== src)
            if (!existingId || isRefChanged || originalSourceType !== src) {
              p.ref_id = refIdNum;
            }
            if (uraian) p.snapshot_uraian = uraian;
            if (satuan) p.snapshot_satuan = satuan;
          } else { // 'ref'
            // BUGFIX: Same logic - send ref_id on source type change
            if (!existingId || isRefChanged || originalSourceType !== src) {
              p.ref_id = refIdNum;
            }
          }

          s.pekerjaan.push(p);
        });

        if (s.pekerjaan.length) k.sub.push(s);
      });

      if (k.sub.length) payload.klasifikasi.push(k);
    });

    if (!payload.klasifikasi.length) {
      tShow('Tidak ada data yang layak disimpan.', 'warning');
      if (btn) { btn.disabled = false; btn.textContent = orig; }
      return;
    }
    if (hasError) {
      tShow('Periksa baris merah. Pastikan ref_id numerik & nama K/Sub tidak kosong (fallback Kx/Kx.y aktif).', 'warning');
      if (btn) { btn.disabled = false; btn.textContent = orig; }
      return;
    }

    try {
      const response = await jfetch(`/detail_project/api/project/${projectId}/list-pekerjaan/upsert/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response?.change_flags && window.DP?.sourceChange) {
        try {
          window.DP.sourceChange.pushFlags(projectId, response.change_flags);
        } catch (err) {
          console.warn('[LP] Failed to push source change flags', err);
        }
      }

      // BUGFIX: Check for validation errors in response
      // Backend returns status 207 with errors array when validation fails
      if (response && response.errors && response.errors.length > 0) {
        console.error('[LP] Save validation errors:', response.errors);

        // Build user-friendly error messages
        let errorMessages = [];
        response.errors.forEach(e => {
          let userMsg = e.message;

          // Make common errors more understandable
          if (e.message && e.message.includes('ordering_index')) {
            userMsg = 'Terjadi konflik urutan pekerjaan. Coba simpan sekali lagi.';
          } else if (e.message && e.message.includes('ref_id')) {
            userMsg = `${e.field}: Referensi AHSP tidak valid atau tidak ditemukan`;
          } else if (e.message && e.message.includes('cascade reset')) {
            userMsg = `${e.field}: Data terkait telah dihapus karena perubahan sumber`;
          }

          errorMessages.push(`• ${userMsg}`);
        });

        const errorMsg = errorMessages.join('\n');
        tShow(`Sebagian perubahan tidak tersimpan:\n\n${errorMsg}\n\nSilakan periksa dan coba lagi.`, 'warning');

        // Reload to show actual database state (changes were rejected)
        await reloadAfterSave();
        return;
      }

      tShow('Perubahan tersimpan.', 'success');
      tbAnnounce && (tbAnnounce.textContent = 'Perubahan tersimpan');

      // Clear dirty state after successful save
      setDirty(false);

      // Broadcast to other tabs
      broadcastOrderingChange();

      // Keep current editing context (no hard re-render) and only sync IDs.
      try {
        await syncTreeIdsFromServer();
      } catch (syncErr) {
        console.warn('[LP] Save succeeded but ID sync failed:', syncErr);
      }
      scheduleSidebarRebuild();
    } catch (e) {
      const raw = (e && e.body && typeof e.body === 'string') ? e.body : (e?.message || '');
      const clean = String(raw).replace(/<[^>]+>/g, '').slice(0, 800);

      // Make error message more user-friendly
      let errorMsg = 'Gagal menyimpan perubahan.';
      if (e?.status === 500) {
        errorMsg = 'Terjadi kesalahan server. Silakan coba lagi atau hubungi administrator.';
      } else if (e?.status === 403) {
        errorMsg = 'Anda tidak memiliki izin untuk menyimpan perubahan ini.';
      } else if (e?.status === 404) {
        errorMsg = 'Data tidak ditemukan. Halaman mungkin sudah tidak valid.';
      } else if (clean) {
        errorMsg = `Gagal menyimpan: ${clean}`;
      }

      tShow(errorMsg, 'error');
      console.error('[LP] Save failed:', e, '\nStatus:', e?.status, '\nBody:', clean);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = orig; }
    }
  }

  async function reloadAfterSave() { klasWrap.innerHTML = ''; await loadTree(); }

  async function syncTreeIdsFromServer() {
    if (!projectId) return;
    const data = await jfetch(`/detail_project/api/project/${projectId}/list-pekerjaan/tree/`, { method: 'GET' });
    const serverKlas = Array.isArray(data?.klasifikasi) ? data.klasifikasi : [];

    const kCards = Array.from(klasWrap.children).filter(el => el?.querySelector && el.querySelector('.sub-wrap'));
    kCards.forEach((kc, ki) => {
      const kSrv = serverKlas[ki];
      if (kSrv?.id) {
        kc.dataset.id = String(kSrv.id);
        kc.dataset.klasId = String(kSrv.id);
      }

      const subBlocks = Array.from(kc.querySelector('.sub-wrap')?.children || []);
      subBlocks.forEach((sb, si) => {
        const sSrv = kSrv?.sub?.[si];
        if (sSrv?.id) {
          sb.dataset.id = String(sSrv.id);
          sb.dataset.subId = String(sSrv.id);
        }

        const rows = Array.from(sb.querySelectorAll('tbody tr'));
        rows.forEach((tr, pi) => {
          const pSrv = sSrv?.pekerjaan?.[pi];
          if (pSrv?.id) tr.dataset.id = String(pSrv.id);

          const srcSel = tr.querySelector('.src');
          const srcNow = srcSel?.value || tr.dataset.sourceType || 'custom';
          tr.dataset.sourceType = srcNow;
          tr.dataset.originalSourceType = srcNow;

          let refRaw;
          if (HAS_JQ) {
            refRaw = $(tr).find('.ref-select').val();
          } else {
            refRaw = tr.querySelector('.ref-select')?.value ?? '';
          }

          const refVal = (refRaw == null || refRaw === '') ? null : String(refRaw);
          if (refVal) {
            tr.dataset.refId = refVal;
            tr.dataset.originalRefId = refVal;
          } else {
            delete tr.dataset.refId;
            delete tr.dataset.originalRefId;
          }
        });
      });
    });
  }

  // ========= [BINDING] Toolbar & Sidebar Buttons =============================
  btnAddKlasAll.forEach(b => b.addEventListener('click', () => newKlas()));
  btnSaveAll.forEach(b => b.addEventListener('click', () => handleSave()));

  // Track "klas terakhir yang disentuh" di views utama
  let lastKlasTarget = null;
  klasWrap.addEventListener('click', (e) => {
    const header = e.target.closest('.card-header');
    if (header?.parentElement?.classList.contains('card')) {
      lastKlasTarget = header.parentElement;
    }
  });

  // Sidebar buttons (+Klas / +Sub)
  const btnAddKlasSide = document.getElementById('btn-add-klas--sidebar');
  const btnAddSubSide = document.getElementById('btn-add-sub--sidebar');

  btnAddKlasSide?.addEventListener('click', () => {
    const card = newKlas();
    lastKlasTarget = card;
  });

  btnAddSubSide?.addEventListener('click', () => {
    let container = null;

    if (lastKlasTarget?.isConnected) {
      container = lastKlasTarget.querySelector('.sub-wrap');
    }

    if (!container) {
      // Try to find active item from Mini TOC
      const activeItem = tocTree?.querySelector('.lp-toc-active');
      const anchorId = activeItem?.dataset?.anchor;
      if (anchorId) {
        const el = document.getElementById(anchorId);
        const klasCard = el?.closest('.card.shadow-sm');
        if (klasCard) container = klasCard.querySelector('.sub-wrap');
      }
    }

    if (!container) {
      let lastKlas = klasWrap?.querySelector('.card.shadow-sm:last-of-type');
      if (!lastKlas) lastKlas = newKlas();
      container = lastKlas.querySelector('.sub-wrap');
    }

    addSub(container);
    scheduleSidebarRebuild();
  });

  // ========= [UI PREFERENCES] Compact Toggle =================================
  (function setupCompactToggle() {
    const KEY = 'lp_compact_v2';
    const app = root;
    const saved = localStorage.getItem(KEY);
    const defOn = (app.dataset.compactDefault === '1');
    const initialOn = saved === '1' ? true : saved === '0' ? false : defOn;

    applyCompact(initialOn);
    btnCompactAll.forEach(btn => {
      btn.setAttribute('aria-pressed', String(initialOn));
      btn.addEventListener('click', (e) => { e.preventDefault(); applyCompact(!app.classList.contains('compact')); });
    });

    function applyCompact(on) {
      app.classList.toggle('compact', on);
      try { localStorage.setItem(KEY, on ? '1' : '0'); } catch { }
      btnCompactAll.forEach(b => b.setAttribute('aria-pressed', String(on)));
    }
  })();

  // FAB klik = klik save utama
  document.getElementById('btn-save-fab')?.addEventListener('click', () => {
    document.querySelector('#btn-save')?.click();
  });

  // ========= [SCROLL SPY] Sinkron active node di Mini TOC ========================
  function setupScrollSpy() {
    if (setupScrollSpy._done || !tocTree) return;
    const io = new IntersectionObserver(entries => {
      const vis = entries.filter(e => e.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
      if (!vis) return;
      const id = vis.target.id || vis.target.dataset.anchorId;
      if (!id) return;
      // Highlight active item in Mini TOC
      tocTree.querySelectorAll('.lp-toc-active').forEach(n => n.classList.remove('lp-toc-active'));
      const item = tocTree.querySelector(`[data-anchor="${CSS.escape(id)}"]`);
      item?.classList.add('lp-toc-active');
    }, { rootMargin: '-45% 0px -50% 0px', threshold: 0.01 });
    document.querySelectorAll('[data-anchor-id], .card, .sub-wrap > div').forEach(el => {
      if (el.id || el.dataset.anchorId) io.observe(el);
    });
    setupScrollSpy._done = true;
  }

  // ========= [SIDEBAR RESIZE] Persist width ==================================
  (function enableSidebarResize() {
    const sidebar = document.getElementById('lp-sidebar');
    const panel = sidebar?.querySelector('.lp-sidebar-inner');
    if (!sidebar || !panel) return;

    let resizer = panel.querySelector('.lp-resizer');
    if (!resizer) {
      resizer = document.createElement('div');
      resizer.className = 'lp-resizer';
      panel.appendChild(resizer);
    }

    const RESIZE_SENSE = (sidebar.dataset.resizeSense || 'west').toLowerCase();

    // Restore saved width
    try {
      const saved = localStorage.getItem('lp_sidebar_w');
      document.documentElement.style.setProperty('--lp-sidebar-w', saved ? `${parseInt(saved, 10)}px` : '380px');
    } catch { }

    let drag = false, startX = 0, startW = 0;

    resizer.addEventListener('mousedown', (e) => {
      drag = true;
      startX = e.clientX;
      startW = panel.getBoundingClientRect().width;
      e.preventDefault();
      document.body.style.userSelect = 'none';
    });

    window.addEventListener('mousemove', (e) => {
      if (!drag) return;
      const MIN_W = 280, MAX_W = 500;
      const dx = e.clientX - startX;
      const wRaw = (RESIZE_SENSE === 'east') ? (startW - dx) : (startW + dx);
      const w = Math.min(Math.max(wRaw, MIN_W), MAX_W);
      document.documentElement.style.setProperty('--lp-sidebar-w', `${w}px`);
    });

    window.addEventListener('mouseup', () => {
      if (!drag) return;
      drag = false;
      document.body.style.userSelect = '';
      const v = getComputedStyle(document.documentElement).getPropertyValue('--lp-sidebar-w');
      const w = parseInt(v, 10);
      if (Number.isFinite(w)) {
        try { localStorage.setItem('lp_sidebar_w', String(w)); } catch { }
      }
    });
  })();

  // ========= [TOPBAR OFFSET] Sinkron CSS var =================================
  (function syncTopbarOffset() {
    function recalc() {
      const tb = document.getElementById('dp-topbar') || document.querySelector('#dp-topbar');
      if (!tb) return;
      const rect = tb.getBoundingClientRect();
      const h = Math.ceil(rect.height) + 1;
      document.documentElement.style.setProperty('--lp-topbar-h', `${h}px`);
      document.documentElement.style.setProperty('--dp-topbar-h', `${h}px`); // bridge ke core
    }
    recalc();
    window.addEventListener('resize', recalc);
    window.addEventListener('load', recalc);
  })();

  // ========= [START] Bootstrap module ========================================
  (async function start() {
    if (!projectId) warn('data-project-id pada #lp-app kosong; sebagian fitur (load/save) non-aktif.');
    if (typeof $ === 'undefined') warn('jQuery belum tersedia saat init awal (defer race?), lanjut saja.');
    if (typeof $?.fn?.select2 !== 'function') warn('Select2 belum terpasang; dropdown ref tetap jalan tanpa enhance.');

    // Keyboard shortcuts (scoped ke #lp-app)
    try {
      const { bindMap } = window.DP.core.keys;
      bindMap(document, {
        'Ctrl+S': () => handleSave(),
        'Cmd+S': () => handleSave(),
        'Esc': () => { if (SidebarManager.isOpen()) SidebarManager.close(); },
        '/': () => { if (SidebarManager.isOpen()) tocSearch?.focus(); else navSearchToolbar?.focus(); }
      }, { scopeSelector: '#lp-app' });
    } catch (_) { /* no-op jika core belum siap */ }

    await loadTree();
    setupScrollSpy();
  })();

  // ========= [P2] Bootstrap Tooltips Initialization =========================
  (function initTooltips() {
    // Initialize Bootstrap 5 tooltips
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
      document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        try {
          new bootstrap.Tooltip(el);
        } catch (err) {
          warn('[TOOLTIP] Failed to initialize:', err);
        }
      });
      log('[TOOLTIP] Bootstrap tooltips initialized');
    } else {
      warn('[TOOLTIP] Bootstrap not available - tooltips disabled');
    }
  })();

  // ========= [DEBUG] (hanya aktif jika __DEBUG__ = true) ======================
  if (__DEBUG__) {
    window.LP_DEBUG = {
      newKlas, addSub, addPekerjaan, handleSave, scheduleSidebarRebuild, buildMiniToc,
      report() {
        console.table({
          '#lp-app': !!root,
          '#klas-list': !!klasWrap,
          '#btn-add-klas': btnAddKlasAll.length,
          '#btn-save': btnSaveAll.length,
          '#lp-toc-tree': !!tocTree,
        });
      }
    };
  }

  // ========= [TEMPLATE LIBRARY] ===============================================
  (async function initTemplateLibrary() {
    const templateList = document.getElementById('template-list');
    const templateSearch = document.getElementById('template-search');
    const templateCategory = document.getElementById('template-category');
    const btnSaveAsTemplate = document.getElementById('btn-save-as-template');
    const btnConfirmImport = document.getElementById('btn-confirm-import');
    const btnConfirmSaveTemplate = document.getElementById('btn-confirm-save-template');

    let currentTemplates = [];
    let selectedTemplateId = null;

    // Load templates on sidebar open
    async function loadTemplates() {
      if (!templateList) return;
      templateList.innerHTML = '<div class=\"text-center text-muted py-3\"><i class=\"bi bi-arrow-clockwise spin\"></i> Memuat template...</div>';

      try {
        const q = (templateSearch?.value || '').trim();
        const cat = templateCategory?.value || '';
        const params = new URLSearchParams();
        if (q) params.set('q', q);
        if (cat) params.set('category', cat);

        const data = await jfetch(`/detail_project/api/templates/?${params}`);
        currentTemplates = data.templates || [];
        renderTemplateList();
      } catch (err) {
        templateList.innerHTML = '<div class=\"template-list-empty\"><i class=\"bi bi-exclamation-circle\"></i> Gagal memuat template</div>';
        err('[TEMPLATE]', err);
      }
    }

    function renderTemplateList() {
      if (!templateList) return;
      if (!currentTemplates.length) {
        templateList.innerHTML = '<div class=\"template-list-empty\"><i class=\"bi bi-inbox\"></i> Belum ada template</div>';
        return;
      }

      templateList.innerHTML = currentTemplates.map(t => `
        <div class=\"template-item\" data-template-id=\"${t.id}\">
          <div class=\"template-item-content\">
            <div class=\"template-item-name\">${t.name}</div>
            <div class=\"template-item-meta\">
              ${t.total_klasifikasi} klas, ${t.total_sub} sub, ${t.total_pekerjaan} pkj
            </div>
          </div>
          <i class=\"bi bi-chevron-right template-item-arrow\"></i>
        </div>
      `).join('');

      // Bind click
      templateList.querySelectorAll('.template-item').forEach(el => {
        el.onclick = () => openTemplatePreview(parseInt(el.dataset.templateId));
      });
    }

    async function openTemplatePreview(templateId) {
      selectedTemplateId = templateId;

      const previewName = document.getElementById('template-preview-name');
      const previewDesc = document.getElementById('template-preview-desc');
      const previewStats = document.getElementById('template-preview-stats');
      const previewTree = document.getElementById('template-preview-tree');

      if (!previewTree) return;

      // Show modal with loading
      previewTree.innerHTML = '<div class=\"text-center py-3\"><i class=\"bi bi-arrow-clockwise spin\"></i></div>';
      if (previewName) previewName.textContent = 'Memuat...';
      if (previewDesc) previewDesc.textContent = '';
      if (previewStats) previewStats.textContent = '';

      const modal = new bootstrap.Modal(document.getElementById('templatePreviewModal'));
      modal.show();

      try {
        const data = await jfetch(`/detail_project/api/templates/${templateId}/`);
        const t = data.template;

        if (previewName) previewName.textContent = t.name;
        if (previewDesc) previewDesc.textContent = t.description || '';
        if (previewStats) {
          previewStats.innerHTML = `<i class=\"bi bi-info-circle\"></i> <strong>${t.total_klasifikasi}</strong> Klasifikasi, <strong>${t.total_sub}</strong> Sub, <strong>${t.total_pekerjaan}</strong> Pekerjaan`;
        }

        // Render tree
        const content = t.content || {};
        const klasList = content.klasifikasi || [];

        previewTree.innerHTML = klasList.map(k => {
          const subHtml = (k.sub || []).map(s => {
            const pkjCount = (s.pekerjaan || []).length;
            return `<div class=\"template-sub-item\"><i class=\"bi bi-folder2\"></i> ${s.name} <span class=\"text-muted\">(${pkjCount} pkj)</span></div>`;
          }).join('');
          return `<div class=\"template-klas-item\"><div class=\"template-klas-name\"><i class=\"bi bi-folder-fill text-primary\"></i> ${k.name}</div>${subHtml}</div>`;
        }).join('') || '<div class=\"text-muted\">Template kosong</div>';

      } catch (err) {
        previewTree.innerHTML = '<div class=\"text-danger\">Gagal memuat detail template</div>';
        console.error('[TEMPLATE]', err);
      }
    }

    // Import template
    btnConfirmImport?.addEventListener('click', async () => {
      if (!selectedTemplateId || !projectId) return;

      btnConfirmImport.disabled = true;
      btnConfirmImport.innerHTML = '<i class=\"bi bi-arrow-clockwise spin\"></i> Importing...';

      try {
        const data = await jfetch(`/detail_project/api/project/${projectId}/templates/${selectedTemplateId}/import/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: '{}'
        });

        bootstrap.Modal.getInstance(document.getElementById('templatePreviewModal'))?.hide();
        tShow(data.message || 'Template berhasil diimport!', 'success');
        await loadTree();  // Refresh data
        setDirty(true);

      } catch (err) {
        tShow('Gagal import template: ' + (err.body?.message || err.message), 'danger');
      } finally {
        btnConfirmImport.disabled = false;
        btnConfirmImport.innerHTML = '<i class=\"bi bi-check-circle\"></i> Import Template';
      }
    });

    // Save as template
    btnSaveAsTemplate?.addEventListener('click', () => {
      const modal = new bootstrap.Modal(document.getElementById('saveTemplateModal'));
      modal.show();
    });

    btnConfirmSaveTemplate?.addEventListener('click', async () => {
      const nameInput = document.getElementById('new-template-name');
      const descInput = document.getElementById('new-template-desc');
      const catInput = document.getElementById('new-template-category');

      const name = (nameInput?.value || '').trim();
      if (!name) {
        tShow('Nama template wajib diisi', 'warning');
        nameInput?.focus();
        return;
      }

      btnConfirmSaveTemplate.disabled = true;
      btnConfirmSaveTemplate.innerHTML = '<i class=\"bi bi-arrow-clockwise spin\"></i> Menyimpan...';

      try {
        const data = await jfetch(`/detail_project/api/project/${projectId}/templates/create/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify({
            name: name,
            description: descInput?.value || '',
            category: catInput?.value || 'lainnya'
          })
        });

        bootstrap.Modal.getInstance(document.getElementById('saveTemplateModal'))?.hide();
        tShow(data.message || 'Template berhasil disimpan!', 'success');

        // Clear form
        if (nameInput) nameInput.value = '';
        if (descInput) descInput.value = '';

        // Reload templates
        loadTemplates();

      } catch (err) {
        tShow('Gagal menyimpan template: ' + (err.body?.message || err.message), 'danger');
      } finally {
        btnConfirmSaveTemplate.disabled = false;
        btnConfirmSaveTemplate.innerHTML = '<i class=\"bi bi-save\"></i> Simpan Template';
      }
    });

    // ========== Import from File ==========
    const btnImportFromFile = document.getElementById('btn-import-from-file');
    const importFileInput = document.getElementById('import-template-file');

    // Helper to get CSRF token
    const getCsrfToken = () => {
      // Try from cookie first
      const cookies = document.cookie.split(';');
      for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') return value;
      }
      // Fallback to meta tag or hidden input
      return document.querySelector('meta[name="csrf-token"]')?.content
        || document.querySelector('input[name="csrfmiddlewaretoken"]')?.value
        || '';
    };

    btnImportFromFile?.addEventListener('click', () => {
      importFileInput?.click();
    });

    importFileInput?.addEventListener('change', async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;

      // Reset for next selection
      e.target.value = '';

      try {
        const text = await file.text();
        const data = JSON.parse(text);

        // Validate template format
        if (!data.export_type || !['project_template', 'list_pekerjaan'].includes(data.export_type)) {
          tShow('Format file tidak valid. Gunakan file template JSON.', 'warning');
          return;
        }

        // Show confirmation
        const stats = data.stats || {};
        const msg = `Import template dari file:\n\n` +
          `• Klasifikasi: ${stats.total_klasifikasi || '?'}\n` +
          `• Sub-Klasifikasi: ${stats.total_sub || '?'}\n` +
          `• Pekerjaan: ${stats.total_pekerjaan || '?'}\n\n` +
          `Lanjutkan import?`;

        if (!confirm(msg)) return;

        btnImportFromFile.disabled = true;
        btnImportFromFile.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Importing...';

        // Get CSRF token
        const csrfToken = getCsrfToken();
        console.log('[IMPORT] Using CSRF token:', csrfToken ? csrfToken.substring(0, 10) + '...' : 'EMPTY');

        // Use api_import_template endpoint by creating temporary template first
        // Or directly use import helper via POST
        const response = await jfetch(`/detail_project/api/project/${projectId}/templates/import-file/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
          body: JSON.stringify({ content: data })
        });

        tShow(response.message || 'Import berhasil!', 'success');
        setDirty(false);

        // Refresh data in-place to avoid blocking reload confirmation popup.
        await reloadAfterSave();

      } catch (err) {
        if (err instanceof SyntaxError) {
          tShow('File JSON tidak valid', 'danger');
        } else {
          tShow('Gagal import: ' + (err.body?.message || err.message), 'danger');
        }
      } finally {
        btnImportFromFile.disabled = false;
        btnImportFromFile.innerHTML = '<i class="bi bi-upload"></i> Import dari File';
      }
    });

    // Search & filter
    let searchTimeout;
    templateSearch?.addEventListener('input', () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(loadTemplates, 300);
    });

    templateCategory?.addEventListener('change', loadTemplates);

    // Load templates when Modal opens
    const templateModal = document.getElementById('templateLibraryModal');
    if (templateModal) {
      // Fix Z-Index/Stacking Context issues by moving modal to body
      if (templateModal.parentElement !== document.body) {
        document.body.appendChild(templateModal);
      }
      templateModal.addEventListener('shown.bs.modal', loadTemplates);
    }

    // ========== Toolbar Template Dropdown Handlers ==========
    const btnToolbarSave = document.getElementById('btn-toolbar-save-template');
    const btnToolbarImport = document.getElementById('btn-toolbar-import-file');

    // Toolbar: Save as Template -> Open modal
    btnToolbarSave?.addEventListener('click', () => {
      const modal = new bootstrap.Modal(document.getElementById('saveTemplateModal'));
      modal.show();
    });

    // Toolbar: Import from File -> Trigger file input
    btnToolbarImport?.addEventListener('click', () => {
      importFileInput?.click();
    });

    // Sidebar sudah dikelola oleh Sidebar object di atas
    // Tidak perlu duplikasi event handlers

    log('[TEMPLATE] Template Library initialized');
  })();

  // ========= [FILTER DROPDOWNS] Klasifikasi & Sub-klasifikasi ================
  (function initFilterDropdowns() {
    const filterToggleBtn = document.getElementById('btn-filter-toggle');
    const filterDropdownsWrap = document.getElementById('lp-filter-dropdowns');
    const filterKlas = document.getElementById('lp-filter-klas');
    const filterSub = document.getElementById('lp-filter-sub');

    if (!filterKlas || !filterSub) {
      log('[FILTER] Filter dropdowns not found, skipping init');
      return;
    }

    // Toggle filter dropdowns visibility
    function toggleFilterDropdowns() {
      const isVisible = !filterDropdownsWrap.classList.contains('d-none');

      if (isVisible) {
        // Hide dropdowns
        filterDropdownsWrap.classList.add('d-none');
        filterDropdownsWrap.classList.remove('d-flex');
        filterToggleBtn.classList.remove('active', 'btn-primary');
        filterToggleBtn.classList.add('btn-outline-secondary');
        filterToggleBtn.setAttribute('aria-expanded', 'false');
      } else {
        // Show dropdowns
        filterDropdownsWrap.classList.remove('d-none');
        filterDropdownsWrap.classList.add('d-flex');
        filterToggleBtn.classList.add('active', 'btn-primary');
        filterToggleBtn.classList.remove('btn-outline-secondary');
        filterToggleBtn.setAttribute('aria-expanded', 'true');
      }

      log('[FILTER] Toggle visibility:', !isVisible);
    }

    // Attach toggle event
    if (filterToggleBtn && filterDropdownsWrap) {
      filterToggleBtn.addEventListener('click', toggleFilterDropdowns);
      log('[FILTER] Toggle button initialized');
    }

    // Populate dropdowns from existing cards
    function populateFilterDropdowns() {
      // Clear existing options (keep first "All" option)
      filterKlas.innerHTML = '<option value="">Semua Klasifikasi</option>';
      filterSub.innerHTML = '<option value="">Semua Sub</option>';

      const klasCards = klasWrap.querySelectorAll('.card');
      klasCards.forEach((card, idx) => {
        const nameInput = card.querySelector('.klas-name');
        const name = nameInput?.value || `Klasifikasi ${idx + 1}`;
        const id = card.id || card.dataset.klasId || `klas_${idx}`;

        const opt = document.createElement('option');
        opt.value = id;
        opt.textContent = name;
        filterKlas.appendChild(opt);
      });

      log('[FILTER] Dropdowns populated with', klasCards.length, 'klasifikasi');
    }

    // Populate sub-klasifikasi based on selected klasifikasi
    function populateSubDropdown(klasId) {
      filterSub.innerHTML = '<option value="">Semua Sub</option>';

      if (!klasId) {
        // Show all subs from all klas
        const allSubs = klasWrap.querySelectorAll('.card .sub-wrap > div');
        allSubs.forEach((sub, idx) => {
          const nameInput = sub.querySelector('.sub-name');
          const name = nameInput?.value || `Sub ${idx + 1}`;
          const id = sub.id || sub.dataset.subId || `sub_${idx}`;

          const opt = document.createElement('option');
          opt.value = id;
          opt.textContent = name;
          filterSub.appendChild(opt);
        });
      } else {
        // Show only subs from selected klas
        const klasCard = klasWrap.querySelector(`#${CSS.escape(klasId)}`);
        if (klasCard) {
          const subs = klasCard.querySelectorAll('.sub-wrap > div');
          subs.forEach((sub, idx) => {
            const nameInput = sub.querySelector('.sub-name');
            const name = nameInput?.value || `Sub ${idx + 1}`;
            const id = sub.id || sub.dataset.subId || `sub_${idx}`;

            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = name;
            filterSub.appendChild(opt);
          });
        }
      }
    }

    // Apply filter to show/hide cards
    function applyFilter() {
      const klasId = filterKlas.value;
      const subId = filterSub.value;

      const klasCards = klasWrap.querySelectorAll('.card');

      klasCards.forEach(card => {
        const cardId = card.id || card.dataset.klasId;

        if (klasId && cardId !== klasId) {
          card.classList.add('lp-filtered-out');
        } else {
          card.classList.remove('lp-filtered-out');

          // Filter subs within this klas
          const subs = card.querySelectorAll('.sub-wrap > div');
          subs.forEach(sub => {
            const sId = sub.id || sub.dataset.subId;

            if (subId && sId !== subId) {
              sub.classList.add('lp-filtered-out');
            } else {
              sub.classList.remove('lp-filtered-out');
            }
          });
        }
      });

      // Announce filter change
      const msg = klasId
        ? (subId ? 'Filter diterapkan' : `Filter: ${filterKlas.options[filterKlas.selectedIndex]?.text}`)
        : 'Filter dihapus - Semua item ditampilkan';
      say(msg);
      log('[FILTER] Applied:', { klasId, subId });
    }

    // Event listeners
    filterKlas.addEventListener('change', () => {
      populateSubDropdown(filterKlas.value);
      filterSub.value = ''; // Reset sub filter
      applyFilter();
    });

    filterSub.addEventListener('change', applyFilter);

    // Initial population
    populateFilterDropdowns();
    populateSubDropdown('');

    // Re-populate when cards change (debounced via MutationObserver)
    let repopulateTimer = null;
    const observer = new MutationObserver(() => {
      if (repopulateTimer) clearTimeout(repopulateTimer);
      repopulateTimer = setTimeout(() => {
        const currentKlas = filterKlas.value;
        populateFilterDropdowns();
        if (currentKlas && filterKlas.querySelector(`option[value="${CSS.escape(currentKlas)}"]`)) {
          filterKlas.value = currentKlas;
        }
        populateSubDropdown(filterKlas.value);
      }, 300);
    });

    observer.observe(klasWrap, { childList: true, subtree: true });

    log('[FILTER] Filter dropdowns initialized');
  })();

  // ========= [DROP INDICATOR] Enhanced Drag-Drop Position Feedback ===========
  (function initDropIndicator() {
    // Create singleton drop indicator element
    let dropIndicator = document.getElementById('lp-drop-indicator');
    if (!dropIndicator) {
      dropIndicator = document.createElement('div');
      dropIndicator.id = 'lp-drop-indicator';
      dropIndicator.className = 'lp-drop-indicator';
      document.body.appendChild(dropIndicator);
      log('[DND-INDICATOR] Created drop indicator element');
    }

    let currentInsertBefore = null;

    // Position the drop indicator based on cursor position
    function positionDropIndicator(tbody, clientY) {
      if (!tbody || !dragState.draggingRow) {
        hideDropIndicator();
        return null;
      }

      const rows = Array.from(tbody.querySelectorAll('tr:not(.lp-row-dragging)'));
      let insertBeforeRow = null;

      for (const row of rows) {
        const rect = row.getBoundingClientRect();
        const rowMiddle = rect.top + rect.height / 2;

        if (clientY < rowMiddle) {
          insertBeforeRow = row;
          break;
        }
      }

      // Position indicator
      const tbodyRect = tbody.getBoundingClientRect();

      if (!insertBeforeRow) {
        // Insert at end - position below last row
        const lastRow = rows[rows.length - 1];
        if (lastRow) {
          const rect = lastRow.getBoundingClientRect();
          dropIndicator.style.top = `${rect.bottom + window.scrollY}px`;
          dropIndicator.style.left = `${tbodyRect.left + 10}px`;
          dropIndicator.style.width = `${tbodyRect.width - 20}px`;
        } else {
          // Empty tbody
          dropIndicator.style.top = `${tbodyRect.top + window.scrollY + 5}px`;
          dropIndicator.style.left = `${tbodyRect.left + 10}px`;
          dropIndicator.style.width = `${tbodyRect.width - 20}px`;
        }
      } else {
        const rect = insertBeforeRow.getBoundingClientRect();
        dropIndicator.style.top = `${rect.top + window.scrollY - 2}px`;
        dropIndicator.style.left = `${tbodyRect.left + 10}px`;
        dropIndicator.style.width = `${tbodyRect.width - 20}px`;
      }

      dropIndicator.classList.add('is-visible');
      currentInsertBefore = insertBeforeRow;

      return insertBeforeRow;
    }

    function hideDropIndicator() {
      dropIndicator.classList.remove('is-visible');
      currentInsertBefore = null;
    }

    // Override handlers to add indicator positioning
    handleDragOver = function (e) {
      if (!dragState.draggingRow) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      updateDragAutoScroll(e, e.currentTarget);

      const tbody = resolveDropTbody(e.currentTarget);
      if (!tbody) return;

      if (dragState.dragOverTarget !== tbody) {
        document.querySelectorAll('.lp-drag-over').forEach(el => el.classList.remove('lp-drag-over'));
        tbody.classList.add('lp-drag-over');
        dragState.dragOverTarget = tbody;
      }

      positionDropIndicator(tbody, e.clientY);
    };

    handleDragLeave = function (e) {
      if (!dragState.draggingRow) return;
      const tbody = resolveDropTbody(e.currentTarget);
      if (!tbody) return;

      const rect = getDropAreaRect(e.currentTarget, tbody);
      if (!rect) return;
      if (e.clientX < rect.left || e.clientX >= rect.right || e.clientY < rect.top || e.clientY >= rect.bottom) {
        tbody.classList.remove('lp-drag-over');
        if (dragState.dragOverTarget === tbody) dragState.dragOverTarget = null;
        hideDropIndicator();
      }
    };

    handleDrop = function (e) {
      if (!dragState.draggingRow) return;
      e.preventDefault();
      e.stopPropagation();

      const targetTbody = resolveDropTbody(e.currentTarget);
      if (!targetTbody) {
        resetDragState();
        hideDropIndicator();
        return;
      }

      const { draggingRow, sourceTbody } = dragState;
      if (!draggingRow) {
        resetDragState();
        hideDropIndicator();
        return;
      }

      const targetSubCard = targetTbody.closest('.lp-sub-card, .sub-wrap > div, .border.rounded');
      const targetSubId = targetSubCard?.dataset.subId || targetSubCard?.id || null;

      const insertBeforeRow = currentInsertBefore;
      if (insertBeforeRow) {
        targetTbody.insertBefore(draggingRow, insertBeforeRow);
      } else {
        targetTbody.appendChild(draggingRow);
      }

      renum(sourceTbody);
      if (targetTbody !== sourceTbody) renum(targetTbody);

      updateOrderingIndices(targetTbody);
      if (targetTbody !== sourceTbody) updateOrderingIndices(sourceTbody);

      setDirty(true);
      scheduleSidebarRebuild();
      broadcastOrderingChange();

      const msg = (targetSubId === dragState.sourceSubId)
        ? 'Urutan pekerjaan diubah'
        : 'Pekerjaan dipindahkan ke sub/klasifikasi lain';
      tShow(msg, 'success');
      say(msg);

      resetDragState();
      hideDropIndicator();
    };

    handleDragEnd = function () {
      resetDragState();
      hideDropIndicator();
    };

    log('[DND-INDICATOR] Drop indicator initialized');
  })();

})();
