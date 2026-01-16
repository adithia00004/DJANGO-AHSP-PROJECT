# Archived Templates - 2025-12-16

## Files Archived

### Templates
- `kelola_tahapan_grid_LEGACY.html` - Legacy Frappe Gantt version (pre-Vite migration)
- `kelola_tahapan_grid_vite.html.backup` - Vite migration backup template
- `rincian_ahsp.html.backup` - Unrelated backup file (AHSP details page)

### JavaScript Files
- `jadwal_kegiatan_app.js.backup` - Main app backup before refactoring
- `gantt-chart-redesign.js.backup` - Gantt module backup

## Rollback Procedure (Emergency Only)

### To rollback to LEGACY template (Frappe Gantt):

1. **Copy template back**:
   ```bash
   copy archive\templates\2025-12-16\kelola_tahapan_grid_LEGACY.html detail_project\templates\detail_project\
   ```

2. **Update view** (`detail_project/views.py` line 208):
   ```python
   # Change from:
   return render(request, "detail_project/kelola_tahapan_grid_modern.html", context)

   # To:
   return render(request, "detail_project/kelola_tahapan_grid_LEGACY.html", context)
   ```

3. **Restart Django server**:
   ```bash
   python manage.py runserver
   ```

4. **Disable Vite** (optional, if needed):
   ```python
   # In settings.py
   USE_VITE_DEV_SERVER = False
   ```

## Rollback to Pre-Refactor Main App

1. **Restore backup**:
   ```bash
   copy archive\static\js\2025-12-16\jadwal_kegiatan_app.js.backup detail_project\static\detail_project\js\src\jadwal_kegiatan_app.js
   ```

2. **Remove new modules** (if causing issues):
   ```bash
   # Temporarily rename modules folder
   move detail_project\static\detail_project\js\src\modules\app detail_project\static\detail_project\js\src\modules\app.disabled
   ```

3. **Rebuild Vite bundle**:
   ```bash
   npm run build
   ```

## Reason for Archival

- **Modern template** (`kelola_tahapan_grid_modern.html`) has been stable since 2025-11-19
- **Legacy files** not used in production for 4+ weeks
- **Sprint 1 cleanup** - Part of roadmap optimization (ROADMAP_IMPLEMENTASI_OPTIMISASI_JADWAL.md)
- **Kept for historical reference** and emergency rollback scenarios

## Modern Stack (Current Active)

- **Template**: `kelola_tahapan_grid_modern.html`
- **Entry Point**: `js/src/jadwal_kegiatan_app.js` (3,055 lines after refactor)
- **Architecture**: Vite + TanStack Table + StateManager + 5 App Modules
- **Modules**:
  - AppInitializer.js
  - EventBinder.js
  - DataOrchestrator.js
  - ChartCoordinator.js
  - UXManager.js

## Performance Comparison

| Metric | Legacy | Modern | Improvement |
|--------|--------|--------|-------------|
| Bundle Size | ~850 KB | ~612 KB | -28% |
| Initial Load | ~1.8s | ~1.2s | -33% |
| HMR Support | No | Yes | N/A |
| Tree Shaking | No | Yes | N/A |
| Test Coverage | 0% | 60%+ | +60% |

## Archive Retention Policy

- Keep for **6 months** (until June 2026)
- Review before deletion
- If no issues reported by March 2026, safe to delete

## Contact

For questions about this archive, contact the development team or refer to:
- LAPORAN_OPTIMISASI_JADWAL_PEKERJAAN.md
- ROADMAP_IMPLEMENTASI_OPTIMISASI_JADWAL.md

---

**Archived by**: Sprint 1 Cleanup Task
**Date**: 2025-12-16
**Status**: SAFE TO DELETE ORIGINALS (after verification)
