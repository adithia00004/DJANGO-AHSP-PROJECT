# L4 — Dead Code Review (reference-scan)

**Tanggal:** 2026-06-10
**Metode:** untuk tiap kandidat, scan referensi (import/call/route/template/static) di
seluruh file tracked (kecuali `dist/` build-output dan definisi diri sendiri).
**Prinsip (sesuai plan L4/D5):** jangan mass-delete berdasarkan penanda; legacy code
yang masih diroute/dipanggil/diuji = sengaja. Penghapusan butuh konfirmasi + smoke test.

---

## A. KEEP — legacy/compat yang masih hidup (jangan hapus)

| Simbol/Modul | Bukti masih dipakai |
|---|---|
| `referensi/repositories/ahsp_repository.py` | di-import 5 file (cache_admin, admin_service, tasks, export_views, __init__) |
| `referensi/services/import_error_analyzer.py` | di-import `views/preview.py` |
| `detail_project/views_api_tahapan.py` (API tahapan **v1**) | dirujuk `urls.py`, `views_api_tahapan_v2.py`, test — diroute + deprecation header (sengaja selama window deprecation) |
| `detail_project/exports/jadwal_pekerjaan_adapter.py` | di-import `export_manager.py`, `views_api.py` |
| `_stage_rincian_legacy_flat` (import_views) | dipanggil l.2604 (parser flat-Excel legacy) |
| `detail_project/decorators/api_deprecation.py` | framework deprecation, diexport `__init__`, dipakai endpoint v1 |
| `LEGACY_PARAM_NAME_RE` + kwargs `nama` (models) | kompat selama migrasi Opaque ID |
| export "backward compatibility" (word_exporter, base.py, import_utils) | jalur export lama masih dipakai/diuji |
| JS `chart-utils`, `ChartCoordinator`, `kelola_tahapan_page_bootstrap` | dirujuk modul vite `src/` + template modern |

**Kesimpulan A:** tidak ada **modul Python mati** di antara kandidat bertanda legacy.

---

## B. DEAD candidates — JS monolith pra-vite (0 referensi)

Top-level `detail_project/static/detail_project/js/*.js` yang **tidak dirujuk** template/JS
mana pun (digantikan oleh bundle vite `src/` → `dist/`). Diverifikasi 0-ref termasuk
pencarian tanpa ekstensi (anti false-negative loading dinamis):

| File | Status |
|---|---|
| `_common.js` | 0 ref |
| `detail_ahsp_gabungan.js` | 0 ref (UI gabungan; ada test `tests_detail_ahsp_gabungan_ui.py` — verifikasi test tak meng-assert file ini sebelum hapus) |
| `harga_numeric_patch.js` | 0 ref |
| `item_table.js` | 0 ref |
| `kelola_tahapan_grid.js` | 0 ref (versi pra-refactor; hanya disebut di dok refactoring) |
| `list_pekerjaan_test_helpers.js` | 0 ref |
| `performance_profiler.js` | 0 ref (dev tool) |
| `referensi_modal.js` | 0 ref |
| `rekap_kebutuhan_enhanced.js` | 0 ref |
| `test_toolbar_buttons.js` | 0 ref (dev/test) |
| `toggle_costum.js` | 0 ref (typo "costum") |

**Rekomendasi B:** hapus per-batch **setelah konfirmasi + smoke test browser** halaman
terkait (Volume, Template AHSP, Harga, Jadwal, List Pekerjaan). Sejarah tetap di Git.

## C. DEAD (lain-lain)

- Dok refactoring **di dalam folder static**: `js/jadwal_pekerjaan/kelola_tahapan/`
  (`MIGRATION_PROGRESS.md`, `PHASE_3_REFACTORING_PLAN.md`, `README.txt`, `REFACTORING.md`).
  Bukan aset web; pindahkan ke `docs/` atau hapus.
- Guard `ProgrammingError/OperationalError` kompat Opaque (D4) — hapus **setelah** semua
  env confirmed migrated.

---

## Catatan eksekusi
- Penghapusan B/C = perubahan yang **kuajukan dulu** (tidak dihapus tanpa konfirmasi).
- Setelah hapus: jalankan suite + clean build (`npm run build`) + smoke browser halaman target.
