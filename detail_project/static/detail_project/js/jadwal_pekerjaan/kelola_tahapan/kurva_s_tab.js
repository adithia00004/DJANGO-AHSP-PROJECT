(function() {
  'use strict';

  const bootstrap = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp;
  const manifest = window.KelolaTahapanModuleManifest;
  if (!bootstrap || !manifest || !manifest.modules || !manifest.modules.kurvaSTab) {
    return;
  }

  const meta = manifest.modules.kurvaSTab;
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

  function getKurvaFacade() {
    const facade = getFacade();
    return facade && facade.kurvaS ? facade.kurvaS : null;
  }

  function bindTabActivation(kurva) {
    const tab = document.getElementById('scurve-tab');
    if (!tab) {
      return;
    }

    tab.addEventListener('shown.bs.tab', () => {
      const result = kurva.refreshView
        ? kurva.refreshView({ reason: 'tab-shown', rebuild: false })
        : null;
      if (result === 'legacy' || result === null) {
        if (!kurva.getChart || !kurva.getChart()) {
          kurva.init && kurva.init({ reason: 'tab-shown' });
        } else if (kurva.resize) {
          kurva.resize();
        }
      }
    });

    moduleStore.bound = true;
  }

  bootstrap.registerModule(meta.id, {
    namespace: meta.namespace,
    pageId: manifest.pageId,
    description: meta.description,
    onRegister() {
      bootstrap.log.info('Kelola Tahapan Kurva S tab module registered.');
    },
    init() {
      const kurva = getKurvaFacade();
      if (!kurva) {
        bootstrap.log.warn('Kelola Tahapan Kurva S tab: facade unavailable on init.');
        return moduleStore;
      }
      if (!moduleStore.bound) {
        bindTabActivation(kurva);
      }
      return moduleStore;
    },
    refresh() {
      return this.init();
    },
  });
})();
