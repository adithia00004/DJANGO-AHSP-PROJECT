# R4.8 - Review Dashboard Export Formats

**Status:** `[x]` PASS
**Terakhir diperbarui:** 2026-02-17

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| Excel URL | `/dashboard/export/excel/` |
| CSV URL | `/dashboard/export/csv/` |
| PDF URL | `/dashboard/project/<pk>/export/pdf/` |
| Views | `dashboard.views_export.*` |
| Auth Required | Ya + subscription policy |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-1 | Export Excel (owner PRO) | File `.xlsx` terunduh | `[x]` | PASS - `Content-Type` excel valid |
| TC-2 | Export CSV (owner PRO) | File `.csv` terunduh | `[x]` | PASS - `Content-Type=text/csv; charset=utf-8` + attachment filename `.csv` |
| TC-3 | Export PDF project (owner PRO) | File `.pdf` terunduh | `[x]` | PASS - `Content-Type=application/pdf` + signature `%PDF` |
| TC-4 | Trial user -> Export Excel | Diblok (PRO-only) | `[x]` | PASS - 403 JSON |
| TC-5 | Watermark policy pada dashboard PDF (expired user) | Diizinkan sesuai `api_pdf_export_allowed` context | `[x]` | PASS - view memakai `request.pdf_export_context` untuk watermark |

Evidence runtime 2026-02-17:
- `pro_export_excel_status=200`, `Content-Type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- `pro_export_csv_status=200`, `Content-Type=text/csv; charset=utf-8`
- `pro_export_pdf_status=200`, `Content-Type=application/pdf`
- `trial_export_excel_status=403`

Evidence test suite:
- `dashboard.tests_prelaunch_smoke.PrelaunchFunctionalSmokeTests.test_dashboard_export_gating_and_real_file_behavior`
- `detail_project.tests_export_access.ExportAccessControlTests` (gating CSV/PDF dashboard)

---

## Temuan (Findings)

Tidak ada temuan terbuka untuk R4.8.

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Pertahankan regression test untuk Content-Type + signature `%PDF` agar endpoint tidak kembali jadi placeholder | P1 | Low | Prevent regresi |
| REC-2 | Jika butuh hardening tambahan, tambah test khusus watermark text pada expired-user PDF export dashboard | P2 | Low | Opsional |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-17 | Audit runtime export dashboard (Excel/CSV/PDF) + entitlement gating | - | DONE |
| 2 | 2026-02-17 | Tambah regression test behavior export saat ini (excel real + csv/pdf stub + trial block) | - | DONE |
| 3 | 2026-02-17 | Implementasi CSV export riil + PDF export riil (owner-scope, watermark-aware) di `dashboard/views_export.py` | - | DONE |
| 4 | 2026-02-17 | Update smoke test: validasi CSV/PDF real file behavior | - | DONE |

---

## Checklist Sign-off

- [x] All formats generate correctly (F-1, F-2 closed)
- [x] Entitlement gating works
- [x] Watermark/export policy untuk dashboard PDF final
- [x] Error handling baseline OK
- [ ] Reviewer sign-off
