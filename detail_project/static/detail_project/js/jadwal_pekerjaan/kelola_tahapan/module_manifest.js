(function() {
  'use strict';

  const manifest = {
    pageId: 'kelola_tahapan',
    pageName: 'Kelola Tahapan',
    globals: {
      app: 'KelolaTahapanPageApp',
      legacyApp: 'JadwalPekerjaanApp',
      state: 'kelolaTahapanPageState',
      facade: 'KelolaTahapanPage',
    },
    modules: {
      grid: {
        id: 'kelolaTahapanGridView',
        namespace: 'kelola_tahapan.grid',
        label: 'Kelola Tahapan - Grid View',
        description: 'Excel-like grid interactions for jadwal pekerjaan.',
        scriptPath: 'detail_project/js/jadwal_pekerjaan/kelola_tahapan/grid_module.js',
      },
      gantt: {
        id: 'kelolaTahapanGanttView',
        namespace: 'kelola_tahapan.gantt',
        label: 'Kelola Tahapan - Gantt Chart',
        description: 'ECharts-based Gantt visualisation with sidebar rendering.',
        scriptPath: 'detail_project/js/jadwal_pekerjaan/kelola_tahapan/gantt_module.js',
      },
      kurvaS: {
        id: 'kelolaTahapanKurvaSView',
        namespace: 'kelola_tahapan.kurva_s',
        label: 'Kelola Tahapan - Kurva S',
        description: 'ECharts S-curve visualisation utilities.',
        scriptPath: 'detail_project/js/jadwal_pekerjaan/kelola_tahapan/kurva_s_module.js',
      },
      shared: {
        id: 'kelolaTahapanShared',
        namespace: 'kelola_tahapan.shared',
        label: 'Kelola Tahapan - Shared Utilities',
        description: 'Cross-view helpers, adapters, and state bridges.',
        scriptPath: 'detail_project/js/jadwal_pekerjaan/kelola_tahapan/shared_module.js',
      },
    },
  };

  Object.freeze(manifest.modules);
  Object.freeze(manifest);

  window.KelolaTahapanModuleManifest = manifest;

  const bootstrap = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp;
  if (bootstrap) {
    bootstrap.state = bootstrap.state || {};
    bootstrap.state.shared = bootstrap.state.shared || {};
    bootstrap.state.shared.moduleManifest = manifest;
  }
})();
