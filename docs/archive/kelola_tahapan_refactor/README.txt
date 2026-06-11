Kelola Tahapan modular structure (bridge stage)
==============================================

This directory holds the new modular surface for the Jadwal Pekerjaan
Kelola Tahapan page. It currently operates in *bridge mode*: the existing
`kelola_tahapan_grid.js` bundle continues to own the business logic, while
each module wrapper delegates calls back into that file until the logic is
fully migrated.

Files
-----
- `module_manifest.js`  
  Declares canonical identifiers, namespaces, and script locations for
  the grid / gantt / kurva-s / shared modules. The manifest is injected
  into both the page bootstrap (`KelolaTahapanPageApp.state.shared`) and
  the public facade (`window.KelolaTahapanPage.manifest`).

- `shared_module.js`  
  Registers the shared module with the page bootstrap and exposes helper
  accessors (`getFacade`, `getManifest`, `getState`). Use this to store
  cross-view utilities once the migration starts.

- `grid_module.js`, `gantt_module.js`, `kurva_s_module.js`  
  Bridge implementations that register dedicated modules with the
  bootstrap. Each wrapper defers to `window.KelolaTahapanPage.*` methods,
  so the existing implementation keeps working. When moving functionality
  out of `kelola_tahapan_grid.js`, redirect the methods here step by step.

Migration workflow
------------------
1. Move a cohesive set of functions from `kelola_tahapan_grid.js` into the
   respective module file.
2. Update the module wrapper to reference the new functions locally
   instead of delegating through the facade.
3. Trim the exported methods in `window.KelolaTahapanPage` once the bridge
   is no longer required for that view.

Current progress
----------------
- `grid_module.js` now owns the layout helpers responsible for header/row
  height synchronisation and scroll syncing. The legacy bundle delegates
  to these helpers (with a fallback for safety), so future refactors can
  continue migrating grid rendering logic piece by piece.
- Tree toggle and cell-editing event wiring (including edit workflow)
  are handled through the grid module. The legacy handlers remain as a
  safety fallback, but new code should rely on the module API.
- Gantt tasks, progress calculations, sidebar rendering, and chart
  refresh logic are now served through `gantt_module.js`. The main bundle
  defers to these helpers while keeping the legacy implementations as a
  fallback.
- `kurva_s_module.js` owns chart initialization/resizing (ECharts), with
  the legacy chart configuration retained as a fallback for parity.

During the transition, the module wrappers guard against duplicate
registration by checking the bootstrap's module registry. This allows us
to roll out dedicated modules incrementally without breaking the legacy
entry script.
