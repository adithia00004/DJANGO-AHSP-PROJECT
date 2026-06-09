# R4.1 - Review Dashboard List Page

**Status:** `[x]` SELESAI DIREVIEW - PASS (non-responsive)
**Terakhir diperbarui:** 2026-02-17

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/dashboard/` |
| View | `dashboard.views.dashboard_view` |
| Template | `dashboard/templates/dashboard/dashboard.html`, `dashboard/templates/dashboard/_project_stats_and_table.html` |
| CSS | `dashboard.css`, `ux-enhancements.css` |
| JS | `dashboard.js`, `mass-edit-toggle.js`, `resizable-columns.js`, `ux-enhancements.js` |
| Auth Required | Ya (`login_required`) |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-1 | User melihat project miliknya | List project tampil | `[x]` | PASS |
| TC-2 | User tidak melihat project user lain | Data isolated per user | `[x]` | PASS (owner scoping pada queryset + smoke test) |
| TC-3 | Filter/search project | Hasil filter akurat | `[x]` | PASS |
| TC-4 | Sorting project | Urutan sesuai pilihan | `[x]` | PASS |
| TC-5 | Pagination | Navigasi halaman benar | `[x]` | PASS (20 item/page) |
| TC-6 | Empty state | Pesan empty state tampil | `[x]` | PASS |
| TC-7 | Filter status aktif/arsip tersedia di UI | User bisa pilih aktif/arsip | `[x]` | PASS (field `is_active` dirender) |
| TC-8 | Bulk action controls di list | Tombol bulk tersedia | `[x]` | PASS (`archive/unarchive/delete`) |
| TC-9 | Responsive mobile | Layout tetap usable | `[~]` | Perlu validasi visual manual |

Evidence test suite:
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests`
- Runtime render check dashboard 2026-02-17 (`name="is_active"`, `bulkArchiveBtn`, `bulkUnarchiveBtn`)

---

## Temuan (Findings)

| # | Severity | Deskripsi | Lokasi | Evidence |
|---|----------|-----------|--------|----------|
| F-1 | **RESOLVED (was MEDIUM)** | Filter `is_active` sebelumnya tidak tampil di UI meskipun backend mendukung. Kini field dirender di panel filter. | `dashboard/templates/dashboard/_project_stats_and_table.html:58` | Runtime check 2026-02-17: `has_filter_is_active_field=True` |
| F-2 | **RESOLVED (was MEDIUM)** | Tombol bulk archive/unarchive sebelumnya tidak dirender (JS handler ada tapi element kosong). Kini toolbar menampilkan keduanya. | `dashboard/templates/dashboard/_project_stats_and_table.html:174` | Runtime check 2026-02-17: `has_bulk_archive_button=True`, `has_bulk_unarchive_button=True` |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Pertahankan filter `is_active` di UI untuk akses data archived/unarchive workflow | P1 | Low | F-1 (`[DONE]`) |
| REC-2 | Pastikan elemen toolbar bulk selaras dengan JS handler + endpoint backend | P1 | Low | F-2 (`[DONE]`) |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-17 | Audit dashboard list view, filter pipeline, pagination, dan render toolbar | - | DONE |
| 2 | 2026-02-17 | Tambah render field `is_active` pada filter panel dashboard | - | DONE |
| 3 | 2026-02-17 | Tambah tombol bulk `archive/unarchive` pada action bar + selaraskan selection scope desktop table | - | DONE |
| 4 | 2026-02-17 | Tambah regression tests dashboard controls (`is_active`, `bulkArchiveBtn`, `bulkUnarchiveBtn`) | - | DONE |

---

## Checklist Sign-off

- [x] Fungsional OK
- [x] Data isolation (multi-tenant) OK
- [x] Keamanan dasar OK
- [x] Performa dasar OK (pagination aktif)
- [ ] UX/UI responsive manual
- [ ] Reviewer sign-off
