# R6.0 - Ringkasan Audit App `referensi`

**Status:** `[~]` AUDIT SELESAI; **N-7/N-5/N-4 FIXED & terverifikasi**; sisa N-1/N-2 (LOW) + N-6 (INFO) pending
**Tanggal:** 2026-06-24
**Metode:** Telaah kode statis read-only atas entry points, access control, model data, pipeline import (upload/validate/staging/commit), validators, rate-limit middleware, XSS toolkit, audit dashboard, dan konsumsi lintas-app. **Bukan** UAT runtime.
**Auditor:** Claude Code

---

## 1. Penilaian Umum

App `referensi` **berkualitas tinggi dan sadar-keamanan** di atas rata-rata. Tulang punggung (access control, validasi file, commit transaksional, XSS) solid. Hanya **1 temuan MEDIUM** (rate-limit import salah-konfigurasi path) + beberapa catatan LOW/INFO. Tidak ditemukan: endpoint privileged tanpa otorisasi, SQL injection, mass-assignment, str(e)-leak masif, atau XSS tersimpan.

---

## 2. Kontrak/Permukaan — TERVERIFIKASI BAIK ✅

| # | Area | Bukti |
|---|------|-------|
| C-1 | **Access control menyeluruh & benar** | Admin portal/pricing/database → `@login_required` + `has_referensi_portal_access`. Delete/CRUD → `@permission_required(delete/view/change_*)`. Import/staging/commit → `@user_passes_test(is_admin=has_referensi_import_access)` + `@require_POST`. Audit → `view_ahsp_stats`. |
| C-2 | **Validasi upload file EXCELLENT** | `AHSPFileValidator`: size 50MB, ext whitelist, MIME, **zip-bomb** (rasio + uncompressed 500MB), **formula-injection** (WEBSERVICE/IMPORTXML/HYPERLINK/EXEC/SYSTEM/CALL…), row 50k / col 100. |
| C-3 | **Commit staging atomic & aman** | `staging_commit`: user-scoped, sumber wajib, commit_mode divalidasi, preflight duplicate, `transaction.atomic` + `select_for_update`, suppress-signal cache via **try/finally** (reconnect terjamin), bulk create/update/delete, REPLACE hapus stale, batch difinalisasi dalam tx yang sama. |
| C-4 | **XSS aman** | Audit template pakai auto-escape Django default + `json_script` utk metadata. Toolkit `safe_display` (bleach strip, `safe_url` blokir `javascript:`/`data:`/`vbscript:`, `safe_filename` strip path). |
| C-5 | **Model data ber-constraint** | `AHSPReferensi` unik `(sumber, kode_ahsp)`; `RincianReferensi` koef≥0 + dedup 5-tuple; `KodeItemReferensi` 2 unique; permission kustom (import/export/view_stats); `AHSPStats` materialized view read-only. |
| C-6 | **Audit log komprehensif** | `SecurityAuditLog` (severity/category/user/IP/UA/metadata/path, classmethod logging file-validation/malicious/rate-limit/XSS/import, cleanup 90hr) + `AuditLogSummary` agregasi. |
| C-7 | **Pemisahan lintas-app benar** | Tulis referensi = admin (import perm); baca = semua pembuat proyek (`api_search_ahsp`/`api_list_sources` login-only). Konsumsi `detail_project` (19 file, sisi-baca) sudah diaudit di R5. |

---

## 3. Temuan (Findings)

| ID | Sev | Deskripsi | Lokasi | Rekomendasi |
|----|-----|-----------|--------|-------------|
| **N-7** | 🟢 FIXED | **Rate-limit import tidak aktif** — `IMPORT_RATE_LIMIT_PATHS` berisi path legacy yang tak cocok endpoint 3-tier nyata → import upload/convert/commit tak ter-rate-limit. **Fix:** (1) `base.py` → `IMPORT_RATE_LIMIT_PATHS = ["/referensi/import/"]`; (2) middleware hanya rate-limit metode **write** (GET navigasi/report/download tak memakan budget); (3) test settings `IMPORT_RATE_LIMIT_PATHS=[]` (hindari polusi cache lintas-test). | `config/settings/base.py`, `referensi/middleware/rate_limit.py`, `config/settings/test.py` | Regression: `ImportRateLimitMiddlewareTests` (3/3) |
| **N-1** | 🟡 LOW | Route `referensi/debug/clear-data/` masih terdaftar, namun view sudah `DEBUG`-only + superuser-only dan produksi normal mengembalikan 404. Ini bukan endpoint produksi reachable, tetapi tetap code smell karena route debug hidup di URL utama. | `referensi/views/preview.py:570`, `urls.py:63` | Pertimbangkan keluarkan dari URL produksi / registrasi hanya saat `DEBUG`. |
| **N-5** | 🟢 FIXED | `validate_content_security` menyertakan `str(e)` di pesan `ValidationError` ke user saat gagal baca file. **Fix:** detail teknis di-`logger.warning` server-side; pesan user generik (tanpa `str(e)`). | `referensi/validators.py` | Regression: `ContentSecurityErrorLeakTests` |
| **N-2** | 🟡 LOW | `bulk_create` → `rebuild_search_cache()` tiap panggilan (per-chunk import bisa rebuild berulang); `simple_history` kemungkinan tak melacak bulk-import → gap kelengkapan history utk baris ter-import. | `referensi/models.py:16-20` | Rebuild cache sekali di akhir import (commit sudah suppress signal — pola serupa); pertimbangkan `bulk_create` history bila audit-trail import diperlukan. |
| **N-6** | 🟡 INFO | `_get_client_ip` percaya IP pertama `X-Forwarded-For` tanpa daftar proxy tepercaya → key rate-limit anon bisa di-spoof. Dampak rendah (import auth-gated; user terotentikasi pakai `user.id`). | `referensi/middleware/rate_limit.py:240-247` | Bila perlu, pakai `django-ipware` / proxy-count tepercaya. |
| **N-4** | 🟢 FIXED | `staging_commit` saat exception → 500 tanpa set batch `FAILED`/pesan ramah. **Fix:** `except` membungkus atomic → `logger.exception`, set batch `FAILED`, `messages.error`, redirect ke staging (rollback terjaga; signal tetap reconnect via `finally`). | `referensi/views/import_views.py` | Regression: `test_commit_failure_marks_batch_failed_and_rolls_back` |
| **N-3** | ✅ BUKAN TEMUAN | XSS orde-kedua (audit log simpan payload) — **dimitigasi** oleh auto-escape Django + `json_script`. | `templates/referensi/audit/*.html` | — (diuji `test_audit_template_security.py`) |

---

## 4. Pemetaan ke 5 Area Review R6

| Doc | Area | Verdict |
|-----|------|---------|
| 01 Admin Portal | admin_portal/pricing/database | ✅ PASS (access control + pricing ModelForm-validated; database CRUD `@permission_required`) |
| 02 AHSP Database | models + constraints + stats | ✅ PASS (C-5; N-2 perf/history minor) |
| 03 Import System | upload/validate/parse | ✅ PASS (N-7 + N-5 **FIXED**; N-1 LOW pending) |
| 04 Staging Workflow | staging→commit | ✅ PASS (C-3; N-4 **FIXED**) |
| 05 Audit Dashboard | audit views/log | ✅ PASS (access gated; XSS-safe; C-6) |

---

## 5. Area Belum Didalami (opsional, risiko rendah)
- **Parser internal** (`ahsp_parser.py`, `import_writer.py`, `import_schema.py`, `import_repair.py`) — robustness parsing. Input sudah di-gate `AHSPFileValidator` (C-2), jadi risiko file-jahat sudah ditutup; sisa = korektnes parsing (bukan keamanan).
- **Audit tasks** (`cleanup_audit_logs`/`generate_audit_summary`/`send_audit_alerts`) + Celery beat — operasional.
- **Export services** (excel/pdf) — `export_*` gated; sejajar dengan WP Export.

---

## 6. Prioritas Tindakan
| Prioritas | Temuan | Alasan |
|-----------|--------|--------|
| ~~P1~~ | ~~N-7~~ | ✅ **FIXED** — rate-limit import kini aktif (write-only) + diuji |
| ~~P3~~ | ~~N-5, N-4~~ | ✅ **FIXED** — leak validator ditutup + commit error-handling (batch FAILED + rollback) |
| **P2** | N-1 | Route debug clear-data masih terdaftar di URL utama meski sudah 404 di produksi normal |
| **P3** | N-2 | Perf/audit-history (`bulk_create` cache/history) — butuh desain lebih hati-hati |
| **INFO** | N-6 | XFF (dampak rendah krn import auth-gated) |

Catatan: 5 doc area R6 (01–05) masih berstatus `BELUM DIREVIEW` (template); ringkasan ini menjadi record audit. Bisa diisi penuh per-area bila diperlukan.
