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
      // Core Data & Logic Modules
      dataLoader: {
        id: 'kelolaTahapanDataLoader',
        namespace: 'kelola_tahapan.data_loader',
        label: 'Kelola Tahapan - Data Loader',
        description: 'Handles all data loading operations: tahapan, pekerjaan, volumes, assignments.',
        scriptPath: 'detail_project/js/jadwal_pekerjaan/kelola_tahapan/data_loader_module.js',
      },
      timeColumnGenerator: {
        id: 'kelolaTahapanTimeColumnGenerator',
        namespace: 'kelola_tahapan.time_column_generator',
        label: 'Kelola Tahapan - Time Column Generator',
        description: 'Generates time columns for different modes: daily, weekly, monthly, custom.',
        scriptPath: 'detail_project/js/jadwal_pekerjaan/kelola_tahapan/time_column_generator_module.js',
      },
      validation: {
        id: 'kelolaTahapanValidation',
        namespace: 'kelola_tahapan.validation',
        label: 'Kelola Tahapan - Validation',
        description: 'Validates progress totals, cell values, and provides visual feedback.',
        scriptPath: 'detail_project/js/jadwal_pekerjaan/kelola_tahapan/validation_module.js',
      },
      saveHandler: {
        id: 'kelolaTahapanSaveHandler',
        namespace: 'kelola_tahapan.save_handler',
        label: 'Kelola Tahapan - Save Handler',
        description: 'Handles save operations with canonical storage conversion.',
        scriptPath: 'detail_project/js/jadwal_pekerjaan/kelola_tahapan/save_handler_module.js',
      },

      // View Modules
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

      // Tab Entry Modules
      gridTab: {
        id: 'kelolaTahapanGridTab',
        namespace: 'kelola_tahapan.tab.grid',
        label: 'Kelola Tahapan - Grid Tab Controller',
        description: 'Manages UI bindings and interactions specific to the grid tab.',
        scriptPath: 'detail_project/js/jadwal_pekerjaan/kelola_tahapan/grid_tab.js',
      },
      ganttTab: {
        id: 'kelolaTahapanGanttTab',
        namespace: 'kelola_tahapan.tab.gantt',
        label: 'Kelola Tahapan - Gantt Tab Controller',
        description: 'Handles Gantt tab toolbar actions and tab lifecycle events.',
        scriptPath: 'detail_project/js/jadwal_pekerjaan/kelola_tahapan/gantt_tab.js',
      },
      kurvaSTab: {
        id: 'kelolaTahapanKurvaSTab',
        namespace: 'kelola_tahapan.tab.kurva_s',
        label: 'Kelola Tahapan - Kurva S Tab Controller',
        description: 'Controls Kurva S tab activation behaviour and resize handling.',
        scriptPath: 'detail_project/js/jadwal_pekerjaan/kelola_tahapan/kurva_s_tab.js',
      },

      // Shared Utilities
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
