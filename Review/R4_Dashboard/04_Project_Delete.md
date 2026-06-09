# R4.4 - Review Project Delete

**Status:** `[x]` PASS
**Terakhir diperbarui:** 2026-02-17

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/dashboard/project/<pk>/delete/` |
| View | `dashboard.views.project_delete` |
| Template | `dashboard/templates/dashboard/project_confirm_delete.html` |
| Auth Required | Ya + owner check |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Konfirmasi delete -> project terhapus | Soft delete (`is_active=False`), redirect | `[x]` |
| TC-2 | Cancel delete | Kembali ke halaman asal (`next`) | `[x]` |
| TC-3 | Non-owner delete | 403/404 | `[x]` |
| TC-4 | Cascade delete semua child data | N/A (project delete saat ini soft-delete; child data tidak dihapus) | `[x]` |
| TC-5 | CSRF protection | Token present di form | `[x]` |
| TC-6 | DELETE via URL manipulation (GET) | Hanya POST yang proses; GET hanya tampilkan konfirmasi | `[x]` |
| TC-7 | Konfirmasi message jelas | Nama project ditampilkan + pesan soft-delete jelas | `[x]` |

Evidence test:
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_owner_edit_delete_project`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_project_delete_confirmation_preserves_next_and_soft_delete`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_expired_owner_blocked_on_project_delete_post`
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_non_owner_blocked_from_project_pages`

---

## Temuan (Findings)

| # | Severity | Deskripsi | Langkah Reproduksi | Evidence |
|---|----------|-----------|---------------------|----------|
| - | - | Tidak ada temuan terbuka | - | - |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort |
|---|-------------|-----------|--------|
| REC-1 | Jika dibutuhkan hard-delete cascade di masa depan, pisahkan endpoint/admin action khusus dan lindungi dengan guard ekstra + backup | P2 | Medium |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-17 | Selaraskan UX delete page dengan perilaku aktual soft-delete (arsip) | - | DONE |
| 2 | 2026-02-17 | Preserve `next` di halaman konfirmasi delete (hidden input + tombol Batal) | - | DONE |
| 3 | 2026-02-17 | Tambah regression test untuk GET confirm, POST soft-delete, redirect `next`, dan block expired-user POST | - | DONE |

---

## Checklist Sign-off

- [x] Cascade delete correct
- [x] Authorization OK
- [x] CSRF OK
- [x] Confirmation UX OK
- [ ] Reviewer sign-off
