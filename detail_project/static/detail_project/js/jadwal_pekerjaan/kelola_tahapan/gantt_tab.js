(function() {
  'use strict';

  const bootstrap = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp;
  const manifest = window.KelolaTahapanModuleManifest;
  if (!bootstrap || !manifest || !manifest.modules || !manifest.modules.ganttTab) {
    return;
  }

  const meta = manifest.modules.ganttTab;
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
  };

  function getFacade() {
    return window[manifest.globals.facade] || null;
  }

  function getGanttFacade() {
    const facade = getFacade();
    return facade && facade.gantt ? facade.gantt : null;
  }

  function syncButtons(buttons, activeMode) {
    const mode = (activeMode || '').toLowerCase();
    buttons.forEach((btn) => {
      const value = (btn.getAttribute('data-gantt-view') || '').toLowerCase();
      if (value === mode) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  function bindToolbar(gantt) {
    const toolbar = document.querySelector('.gantt-toolbar');
    if (!toolbar) {
      return;
    }

    const buttons = Array.from(toolbar.querySelectorAll('[data-gantt-view]'));
    if (!buttons.length) {
      return;
    }

    buttons.forEach((button) => {
      button.addEventListener('click', (event) => {
        event.preventDefault();
        const mode = button.getAttribute('data-gantt-view') || 'Week';
        const normalized = gantt.setViewMode(mode, { refresh: true, rebuildTasks: false });
        syncButtons(buttons, normalized);
      });
    });

    const currentMode = gantt.getViewMode ? gantt.getViewMode() : 'Week';
    syncButtons(buttons, currentMode);
    moduleStore.bound = true;
  }

  function bindTabActivation(gantt) {
    const ganttTab = document.getElementById('gantt-tab');
    if (!ganttTab) {
      return;
    }

    ganttTab.addEventListener('shown.bs.tab', () => {
      const result = gantt.refreshView
        ? gantt.refreshView({ reason: 'tab-shown', rebuildTasks: false })
        : null;
      if (result === 'legacy' || result === null) {
        gantt.init && gantt.init();
      }
    });
  }

  bootstrap.registerModule(meta.id, {
    namespace: meta.namespace,
    pageId: manifest.pageId,
    description: meta.description,
    onRegister() {
      bootstrap.log.info('Kelola Tahapan Gantt tab module registered.');
    },
    init() {
      const gantt = getGanttFacade();
      if (!gantt) {
        bootstrap.log.warn('Kelola Tahapan Gantt tab: facade unavailable on init.');
        return moduleStore;
      }
      if (!moduleStore.bound) {
        bindToolbar(gantt);
        bindTabActivation(gantt);
      } else if (typeof gantt.getViewMode === 'function') {
        const toolbar = document.querySelector('.gantt-toolbar');
        if (toolbar) {
          const buttons = Array.from(toolbar.querySelectorAll('[data-gantt-view]'));
          syncButtons(buttons, gantt.getViewMode());
        }
      }
      return moduleStore;
    },
    refresh() {
      return this.init();
    },
  });
})();
