(function() {
  'use strict';

  const bootstrap = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp;
  const manifest = window.KelolaTahapanModuleManifest;
  if (!bootstrap || !manifest || !manifest.modules || !manifest.modules.gridTab) {
    return;
  }

  const meta = manifest.modules.gridTab;
  const hasModule = typeof bootstrap.hasModule === 'function'
    ? (id) => bootstrap.hasModule(id)
    : (id) => bootstrap.modules && bootstrap.modules.has
      ? bootstrap.modules.has(id)
      : false;

  if (hasModule(meta.id)) {
    return;
  }

  const moduleStore = {
    bound: false,
    shadowBound: false,
  };

  function getFacade() {
    return window[manifest.globals.facade] || null;
  }

  function getGridFacade() {
    const facade = getFacade();
    return facade && facade.grid ? facade.grid : null;
  }

  function getState() {
    const grid = getGridFacade();
    if (grid && typeof grid.getState === 'function') {
      return grid.getState();
    }
    return bootstrap.state || null;
  }

  function bindTimeScale(radios, grid, state) {
    if (!Array.isArray(radios) || !grid || !state) {
      return;
    }

    radios.forEach((radio) => {
      radio.addEventListener('change', (event) => {
        const newMode = event.target.value;
        const unsavedCount = state.modifiedCells instanceof Map ? state.modifiedCells.size : 0;

        let message;
        if (unsavedCount > 0) {
          message = [
            `WARNING: You have ${unsavedCount} unsaved change(s).`,
            `Switching to ${newMode} mode will regenerate tahapan, convert assignments, and discard unsaved edits.`,
            'Continue? (Tip: choose "Cancel" and click "Save All Changes" first if needed.)',
          ].join('\n\n');
        } else {
          message = [
            `Switch to ${newMode} mode?`,
            'This will regenerate tahapan and convert assignments to the selected time scale.',
          ].join('\n\n');
        }

        if (window.confirm(message)) {
          grid.switchTimeScaleMode(newMode);
        } else {
          grid.updateTimeScaleControls(state.timeScale);
        }
      });
    });
  }

  function bindDisplayMode(radios, grid, state) {
    if (!Array.isArray(radios) || !grid || !state) {
      return;
    }

    radios.forEach((radio) => {
      radio.addEventListener('change', (event) => {
        state.displayMode = event.target.value;
        grid.renderGrid();
      });
    });
  }

  function bindActionButtons(grid, state) {
    const collapseBtn = document.getElementById('btn-collapse-all');
    if (collapseBtn) {
      collapseBtn.addEventListener('click', () => {
        if (state.expandedNodes instanceof Set) {
          state.expandedNodes.clear();
        }
        grid.renderGrid();
      });
    }

    const expandBtn = document.getElementById('btn-expand-all');
    if (expandBtn) {
      expandBtn.addEventListener('click', () => {
        if (Array.isArray(state.flatPekerjaan)) {
          state.flatPekerjaan.forEach((node) => {
            if (node && node.id && Array.isArray(node.children) && node.children.length > 0) {
              state.expandedNodes.add(node.id);
            }
          });
        }
        grid.renderGrid();
      });
    }

    const saveBtn = document.getElementById('btn-save-all');
    if (saveBtn) {
      saveBtn.addEventListener('click', () => {
        grid.saveAllChanges();
      });
    }

    const resetBtn = document.getElementById('btn-reset-progress');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        grid.resetAllProgress();
      });
    }
  }

  function bindPanelShadows(state) {
    if (moduleStore.shadowBound || !state || !state.domRefs) {
      return;
    }

    const domRefs = state.domRefs;
    const leftPanel = domRefs.leftPanelScroll || document.querySelector('.left-panel-scroll');
    const rightPanel = domRefs.rightPanelScroll || document.querySelector('.right-panel-scroll');
    const leftHead = domRefs.leftThead || document.getElementById('left-thead');
    const rightHead = domRefs.rightThead || document.getElementById('right-thead');

    if (!leftPanel && !rightPanel) {
      return;
    }

    const handler = () => {
      if (leftPanel && leftHead) {
        leftHead.classList.toggle('scrolled', leftPanel.scrollTop > 0);
      }
      if (rightPanel && rightHead) {
        rightHead.classList.toggle('scrolled', rightPanel.scrollTop > 0);
      }
    };

    if (leftPanel) {
      leftPanel.addEventListener('scroll', handler, { passive: true });
    }
    if (rightPanel) {
      rightPanel.addEventListener('scroll', handler, { passive: true });
    }

    handler();
    moduleStore.shadowBound = true;
    moduleStore.shadowHandler = handler;
  }

  function syncRadios(grid, state) {
    if (!grid || !state) {
      return;
    }
    grid.updateTimeScaleControls(state.timeScale);
    document.querySelectorAll('input[name="displayMode"]').forEach((radio) => {
      radio.checked = radio.value === state.displayMode;
    });
  }

  function bindControls() {
    const grid = getGridFacade();
    const state = getState();
    if (!grid || !state || moduleStore.bound) {
      if (grid && state) {
        syncRadios(grid, state);
      }
      return;
    }

    const timeScaleRadios = Array.from(document.querySelectorAll('input[name="timeScale"]'));
    const displayModeRadios = Array.from(document.querySelectorAll('input[name="displayMode"]'));

    bindTimeScale(timeScaleRadios, grid, state);
    bindDisplayMode(displayModeRadios, grid, state);
    bindActionButtons(grid, state);
    bindPanelShadows(state);
    syncRadios(grid, state);

    moduleStore.bound = true;
  }

  bootstrap.registerModule(meta.id, {
    namespace: meta.namespace,
    pageId: manifest.pageId,
    description: meta.description,
    onRegister() {
      bootstrap.log.info('Kelola Tahapan grid tab module registered.');
    },
    init() {
      bindControls();
      return moduleStore;
    },
    refresh() {
      bindControls();
      return moduleStore;
    },
    getState,
  });
})();
