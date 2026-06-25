# Cross-Cutting: Security Audit

**Status:** `[~]` REVALIDASI STATIK SELESAI (2026-06-25) — 0 CRITICAL/HIGH; residual = INFO/eksternal
**Terakhir diperbarui:** 2026-06-25

> **Metode:** konsolidasi verdict dari audit per-app sesi ini (R1 Pages, R2 Accounts, R3 Subscriptions, R4 Dashboard, R5 Detail Project, R6 Referensi) + sweep repo-wide khusus item lintas-app (raw SQL, CORS, SSRF, admin path, error pages). Telaah kode statis; item bertanda ⏳ butuh runtime/eksternal (mis. `pip-audit`).

---

## Scope

Audit keamanan lintas seluruh apps berdasarkan OWASP Top 10 2021.

---

## A01:2021 - Broken Access Control

| # | Check Item | Status | Temuan/Bukti |
|---|-----------|--------|--------|
| S-1 | IDOR project endpoints | ✅ | R5/R4: `get_object_or_404(... owner=request.user)`; queryset owner-scoped |
| S-2 | IDOR dashboard endpoints | ✅ | R4: semua CRUD `owner=request.user, is_active=True` (audit 09 SSOT owner=Tinggi) |
| S-3 | IDOR template/detail endpoints | ✅ | R5: owner-scoped + async guard token |
| S-4 | Owner check konsisten | ✅ | R4/R5/R6 verified; pola seragam |
| S-5 | Admin-only routes protected | ✅ | R6: access control referensi menyeluruh (`has_referensi_*`/`@permission_required`); admin via is_staff |
| S-6 | Subscription middleware coverage | ✅ | R2/R3: `SubscriptionMiddleware` write-gate + excluded paths (F9 payment) |
| S-7 | CORS configuration | ✅ | Sweep: tak ada `corsheaders`/`CORS_*` → same-origin default (benar utk app server-rendered) |
| S-8 | Directory traversal upload | ✅ | Upload diproses in-memory (openpyxl pada UploadedFile), tak menulis path user; `safe_filename` (R6) |

## A02:2021 - Cryptographic Failures

| # | Check Item | Status | Temuan/Bukti |
|---|-----------|--------|--------|
| S-9 | SECRET_KEY tidak hardcoded | ✅ | R2: `production.py` guard (non-placeholder, ≥32 char, env-only) |
| S-10 | Password hashing | ✅ | R2: PBKDF2 + 4 validators |
| S-11 | HTTPS enforcement | ✅ | R2: SSL redirect + HSTS preload + cookie-secure (prod) |
| S-12 | Sensitive data di logs | ✅ (1 INFO) | str(e)-leak ditutup (WP Export, R6 N-5); **N-6 INFO**: XFF client-IP di log (lihat residual) |
| S-13 | Midtrans keys secure | ✅ | R3: keys via env, server-side only |
| S-14 | Database credentials secure | ✅ | env/.env (tak di-commit) |

## A03:2021 - Injection

| # | Check Item | Status | Temuan/Bukti |
|---|-----------|--------|--------|
| S-15 | SQL injection - ORM | ✅ | ORM di seluruh app |
| S-16 | SQL injection - raw queries | ✅ | Sweep: `cursor.execute` statis; `RawSQL(f"{table}…")` pakai `Model._meta.db_table` (konstan), search `SearchQuery` parameterized |
| S-17 | XSS - autoescaping | ✅ | R1/R4/R6: auto-escape default; audit template aman |
| S-18 | XSS - `\|safe` usage | ✅ | R4: chart XSS (F-01) ditutup `_safe_inline_json`; R1: tak ada `\|safe` di pages |
| S-19 | XSS - JS DOM | ✅ | R6 `safe_display`; tak ada `innerHTML`/`document.write` pada data user (R1) |
| S-20 | Command injection | ✅ | Tak ada `os.system`/`subprocess` dengan input user |
| S-21 | Formula injection (JS eval) | ✅ | R5: vol formula engine tokenizer, bukan `eval` |
| S-22 | Excel formula injection | ✅ | R6: `AHSPFileValidator` blokir WEBSERVICE/IMPORT*/HYPERLINK/EXEC/SYSTEM/CALL |

## A04:2021 - Insecure Design

| # | Check Item | Status | Temuan/Bukti |
|---|-----------|--------|--------|
| S-23 | Rate limiting login | ✅ | R2: allauth default rate-limit (prod) |
| S-24 | Rate limiting API write | ✅ | HI-10: `rate_limit`+`body_limit` repo-wide pada write endpoints (`9f8a5673`) |
| S-25 | Rate limiting import | ✅ | R6 **N-7 FIXED**: middleware cakup `/referensi/import/` (write-only) |
| S-26 | File upload size limits | ✅ | R6 50MB/50k baris; R4 10MB/2k baris |
| S-27 | Request timeout | ✅ | `config.middleware.timeout.TimeoutMiddleware` |

## A05:2021 - Security Misconfiguration

| # | Check Item | Status | Temuan/Bukti |
|---|-----------|--------|--------|
| S-28 | DEBUG=False prod | ✅ | R2: `production.py` DEBUG=False + DJANGO_ENV guard |
| S-29 | ALLOWED_HOSTS | ✅ | R2: wajib + tolak placeholder |
| S-30 | Security middleware | ✅ | SecurityMiddleware + CSP + Subscription + RateLimit |
| S-31 | SECURE_SSL_REDIRECT | ✅ | R2 prod |
| S-32 | SECURE_HSTS | ✅ | R2: 1th + subdomains + preload |
| S-33 | X-Frame-Options | ✅ | Django default DENY + CSP `frame-ancestors 'self'` |
| S-34 | Content-Security-Policy | ✅ report-only | WP-A2: CSP report-only matang (`script-src` tanpa `unsafe-inline`); **enforcement = milestone (F-12)**: migrasi inline script lalu flip `CSP_REPORT_ONLY=False` |
| S-35 | Admin path customized | ⚠️ INFO | `/admin/` default (terlindung is_staff + allauth login rate-limited); kustomisasi = obscurity opsional |
| S-36 | Error pages no leak | ✅ | `templates/404.html`/`500.html` kustom; DEBUG=False prod |

## A06:2021 - Vulnerable Components

| # | Check Item | Status | Temuan/Bukti |
|---|-----------|--------|--------|
| S-37 | Python deps up-to-date | ⏳ | Perlu `pip-audit` (eksternal) |
| S-38 | JS deps up-to-date | ✅ | xlsx/SheetJS di-patch 0.20.3 (`4d1f4353`, Prototype Pollution+ReDoS) |
| S-39 | Known CVE (pip-audit) | ⏳ | Jalankan `pip-audit` di CI |
| S-40 | Django version current | ✅ | Django 5.2.x (current) |

## A07:2021 - Authentication Failures

| # | Check Item | Status | Temuan/Bukti |
|---|-----------|--------|--------|
| S-41 | Password complexity | ✅ | R2: 4 validators (min-length/common/numeric/similarity) |
| S-42 | Session security | ✅ | R2: httponly/samesite/secure(prod), cached_db |
| S-43 | Session timeout | ✅ | `SESSION_COOKIE_AGE` 2 minggu (kebijakan) |
| S-44 | CSRF semua form | ✅ | R1/R2: `{% csrf_token %}` semua form; logout POST |
| S-45 | Webhook CSRF exemption justified | ✅ | R3: webhook `@csrf_exempt` + signature constant-time (A6/A8) |

## A08:2021 - Data Integrity Failures

| # | Check Item | Status | Temuan/Bukti |
|---|-----------|--------|--------|
| S-46 | JSON import validation | ✅ | R5/R6: schema validation import |
| S-47 | Excel import validation | ✅ | R6: `AHSPFileValidator` (zip-bomb/formula/row/col/mime) |
| S-48 | Webhook signature | ✅ | R3: SHA512 signature + status/amount cross-check (A4/A5) |

## A09:2021 - Logging & Monitoring

| # | Check Item | Status | Temuan/Bukti |
|---|-----------|--------|--------|
| S-49 | Auth events logged | ⏳ | allauth + Sentry; kelengkapan event login perlu verifikasi runtime |
| S-50 | Failed login logged | ⏳ | allauth rate-limit + `SecurityAuditLog`; verifikasi runtime |
| S-51 | API errors logged | ✅ | R4 **F-07 FIXED** (logger.exception); `export_error_response` |
| S-52 | Audit trail | ✅ | R6: `simple_history` + `SecurityAuditLog`; R3 subscription log |
| S-53 | Health check endpoints | ✅ | `views_health.py` (health/ready/live) |

## A10:2021 - SSRF

| # | Check Item | Status | Temuan/Bukti |
|---|-----------|--------|--------|
| S-54 | No user-supplied URLs fetched | ✅ | Sweep: satu-satunya fetch = Midtrans API (endpoint tetap dari settings) |
| S-55 | Midtrans callback URL validation | ✅ | R3: base URL ikut `MIDTRANS_IS_PRODUCTION` (bukan input user) |

---

## Ringkasan Temuan

| Severity | Jumlah | Items |
|----------|--------|-------|
| CRITICAL | 0 | - |
| HIGH | 0 | - |
| MEDIUM | 0 | - |
| INFO/residual | 3 | N-6 (XFF client-IP, S-12) · S-35 (admin path obscurity) · F-12 (CSP enforcement milestone, S-34) |
| Eksternal (⏳) | 3 | S-37/S-39 (`pip-audit`) · S-49/S-50 (auth-event logging runtime) |

**Verdict:** postur keamanan lintas-app **KUAT**. Seluruh kelas OWASP Top 10 yang dapat diverifikasi statik = PASS. Tidak ada celah CRITICAL/HIGH/MEDIUM cross-cutting yang terbuka.

---

## Rekomendasi Prioritas

| # | Rekomendasi | Severity | Effort | Status |
|---|-------------|----------|--------|--------|
| N-6 | Helper `get_trusted_client_ip` repo-wide (proxy-count/`django-ipware`) untuk 4 titik (`auth_debug`, `referensi/rate_limit`, `views_monitoring`, `audit_logger`) — jangan tambal satu titik (pelajaran UF-013/AT-01). Tak ter-eksploitasi (import auth-gated). | INFO | Sedang | OPEN (backlog) |
| F-12 | CSP enforcement: migrasi inline script ke `json_script`/nonce, lalu `DJANGO_CSP_REPORT_ONLY=False`. | LOW (defense-in-depth) | Besar | OPEN (milestone; report-only sudah aktif) |
| S-37/S-39 | Tambah `pip-audit` ke CI (gate dependency CVE). | LOW | Kecil | OPEN |
| S-35 | (Opsional) kustomisasi path admin untuk obscurity. | INFO | Kecil | OPEN |

---

## Aktivitas Perbaikan (lintas-sesi, ringkas)

| Tanggal | Deskripsi | Commit/Ref |
|---------|-----------|-----------|
| 2026-06 | R6 N-7 import rate-limit; N-5 validator leak; N-1 debug route | `83f45f64`/`b23c518b`/`49abecde` |
| 2026-06 | R4 F-01 chart XSS, F-02 mass-edit, F-07 progress logging | dashboard fix-phase |
| 2026-06 | R3 webhook signature/idempotency (A1/A3/A4/A5/A6/A8) | subscriptions SUB-* |
| 2026-06 | R2 admin subscription fields | `cbcd4383` |
| 2026-02 | WP-A2 CSP report-only; monitoring harden; csrf_exempt removal | baseline |

---

## Checklist Sign-off

- [x] OWASP A01-A10 ditinjau (statik, konsolidasi R1-R6 + sweep)
- [x] 0 CRITICAL/HIGH terbuka
- [ ] `pip-audit` di CI (S-37/S-39)
- [ ] N-6 client-IP helper (jika diputuskan dikerjakan)
- [ ] CSP enforcement (F-12 milestone)
- [ ] Reviewer sign-off
