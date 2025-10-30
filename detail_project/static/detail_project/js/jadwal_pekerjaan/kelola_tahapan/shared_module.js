(function() {
  'use strict';

  const bootstrap = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp;
  const manifest = window.KelolaTahapanModuleManifest;
  if (!bootstrap || !manifest || !manifest.modules || !manifest.modules.shared) {
    return;
  }

  const meta = manifest.modules.shared;
  const hasModule = typeof bootstrap.hasModule === 'function'
    ? (id) => bootstrap.hasModule(id)
    : (id) => bootstrap.modules && bootstrap.modules.has
      ? bootstrap.modules.has(id)
      : false;

  if (hasModule(meta.id)) {
    return;
  }

  const getFacade = () => window[manifest.globals.facade];

  bootstrap.registerModule(meta.id, {
    namespace: meta.namespace,
    pageId: manifest.pageId,
    description: meta.description,
    onRegister(context) {
      bootstrap.log.info('Kelola Tahapan shared module (bridge) registered.');
      if (context && context.state) {
        context.state.shared = context.state.shared || {};
        context.state.shared.moduleManifest = manifest;
      }
      if (context && context.emit) {
        context.emit('kelola_tahapan.shared:registered', { manifest, meta });
      }
    },
    getFacade,
    getManifest: () => manifest,
    getState: () => window[manifest.globals.state] || null,
  });
})();

