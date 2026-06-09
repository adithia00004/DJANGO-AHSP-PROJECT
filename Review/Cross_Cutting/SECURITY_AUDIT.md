# Cross-Cutting: Security Audit

**Status:** `[~]` BASELINE TERIMPORT, REVALIDASI SSOT BERJALAN
**Terakhir diperbarui:** 2026-02-16

---

## Scope

Audit keamanan lintas seluruh apps berdasarkan OWASP Top 10 2021.

---

## Baseline Terimport (Referensi 2026-02-08)

Baseline berikut diambil dari audit sebelumnya dan akan divalidasi ulang di SSOT ini:

- IDOR endpoint API v2 chart/kurva/rekap sudah ditutup.
- `@csrf_exempt` pada endpoint export POST sudah dihapus.
- Monitoring endpoint sudah harden (API key wajib + rate limit).
- Sanitasi metadata audit log (`json_script`) sudah diterapkan.

Sumber referensi:
- `AUDIT_PRE_LAUNCH.md`
- `PRE_PRODUCTION_LAUNCH_CHECKLIST.md`

---

## A01:2021 - Broken Access Control

| # | Check Item | Lokasi | Status | Temuan |
|---|-----------|--------|--------|--------|
| S-1 | IDOR pada semua project endpoints | `detail_project/views_api.py` | `[ ]` | - |
| S-2 | IDOR pada dashboard endpoints | `dashboard/views.py` | `[ ]` | - |
| S-3 | IDOR pada template endpoints | `detail_project/views_api.py` | `[ ]` | - |
| S-4 | Owner check konsisten di semua views | All apps | `[ ]` | - |
| S-5 | Admin-only routes protected | `referensi/`, `admin/` | `[ ]` | - |
| S-6 | Subscription middleware coverage | `accounts/middleware.py` | `[ ]` | - |
| S-7 | CORS configuration | `config/settings/` | `[ ]` | - |
| S-8 | Directory traversal pada file upload | All upload views | `[ ]` | - |

## A02:2021 - Cryptographic Failures

| # | Check Item | Lokasi | Status | Temuan |
|---|-----------|--------|--------|--------|
| S-9 | SECRET_KEY tidak hardcoded | `config/settings/` | `[ ]` | - |
| S-10 | Password hashing (default Django) | `accounts/` | `[ ]` | - |
| S-11 | HTTPS enforcement | `config/settings/production.py` | `[ ]` | - |
| S-12 | Sensitive data di logs | All apps | `[ ]` | - |
| S-13 | Midtrans keys secure | `subscriptions/midtrans.py` | `[ ]` | - |
| S-14 | Database credentials secure | `.env` files | `[ ]` | - |

## A03:2021 - Injection

| # | Check Item | Lokasi | Status | Temuan |
|---|-----------|--------|--------|--------|
| S-15 | SQL injection - ORM usage | All models/views | `[ ]` | - |
| S-16 | SQL injection - raw queries | Search for `.raw()`, `.extra()` | `[ ]` | - |
| S-17 | XSS - template autoescaping | All templates | `[ ]` | - |
| S-18 | XSS - `|safe` filter usage | All templates | `[ ]` | - |
| S-19 | XSS - JavaScript DOM manipulation | All JS files | `[ ]` | - |
| S-20 | Command injection | Management commands | `[ ]` | - |
| S-21 | Formula injection (eval) | `vol_formula_engine.js` | `[ ]` | - |
| S-22 | Excel formula injection | Import/export views | `[ ]` | - |

## A04:2021 - Insecure Design

| # | Check Item | Lokasi | Status | Temuan |
|---|-----------|--------|--------|--------|
| S-23 | Rate limiting pada login | `accounts/` (allauth) | `[ ]` | - |
| S-24 | Rate limiting pada API | All API endpoints | `[ ]` | - |
| S-25 | Rate limiting pada import | `referensi/middleware.py` | `[ ]` | - |
| S-26 | File upload size limits | All upload views | `[ ]` | - |
| S-27 | Request timeout | `config/middleware/` | `[ ]` | - |

## A05:2021 - Security Misconfiguration

| # | Check Item | Lokasi | Status | Temuan |
|---|-----------|--------|--------|--------|
| S-28 | DEBUG = False in production | `config/settings/production.py` | `[ ]` | - |
| S-29 | ALLOWED_HOSTS configured | `config/settings/production.py` | `[ ]` | - |
| S-30 | Security middleware enabled | `config/settings/base.py` | `[ ]` | - |
| S-31 | SECURE_SSL_REDIRECT | Production settings | `[ ]` | - |
| S-32 | SECURE_HSTS settings | Production settings | `[ ]` | - |
| S-33 | X-Frame-Options | Settings | `[ ]` | - |
| S-34 | Content-Security-Policy | Headers | `[ ]` | - |
| S-35 | Django admin path customized | `config/urls.py` | `[ ]` | - |
| S-36 | Error pages (404, 500) no info leak | `templates/404.html`, `500.html` | `[ ]` | - |

## A06:2021 - Vulnerable Components

| # | Check Item | Lokasi | Status | Temuan |
|---|-----------|--------|--------|--------|
| S-37 | Python dependencies up-to-date | `requirements.txt` | `[ ]` | - |
| S-38 | JS dependencies up-to-date | `package.json` | `[ ]` | - |
| S-39 | Known CVE check (pip-audit) | All packages | `[ ]` | - |
| S-40 | Django version current | `requirements.txt` | `[ ]` | - |

## A07:2021 - Authentication Failures

| # | Check Item | Lokasi | Status | Temuan |
|---|-----------|--------|--------|--------|
| S-41 | Password complexity requirements | allauth config | `[ ]` | - |
| S-42 | Session security settings | Settings | `[ ]` | - |
| S-43 | Session timeout | Settings | `[ ]` | - |
| S-44 | CSRF protection on all forms | All templates/views | `[ ]` | - |
| S-45 | Webhook CSRF exemption justified | `subscriptions/views.py` | `[ ]` | - |

## A08:2021 - Data Integrity Failures

| # | Check Item | Lokasi | Status | Temuan |
|---|-----------|--------|--------|--------|
| S-46 | JSON import validation | Import endpoints | `[ ]` | - |
| S-47 | Excel import validation | Import views | `[ ]` | - |
| S-48 | Webhook signature verification | `subscriptions/` | `[ ]` | - |

## A09:2021 - Logging & Monitoring

| # | Check Item | Lokasi | Status | Temuan |
|---|-----------|--------|--------|--------|
| S-49 | Authentication events logged | Allauth signals | `[ ]` | - |
| S-50 | Failed login attempts logged | Allauth | `[ ]` | - |
| S-51 | API errors logged | Exception middleware | `[ ]` | - |
| S-52 | Audit trail for data changes | `simple_history`, `DetailAHSPAudit` | `[ ]` | - |
| S-53 | Health check endpoints | `views_health.py` | `[ ]` | - |

## A10:2021 - Server-Side Request Forgery (SSRF)

| # | Check Item | Lokasi | Status | Temuan |
|---|-----------|--------|--------|--------|
| S-54 | No user-supplied URLs fetched server-side | All views | `[ ]` | - |
| S-55 | Midtrans callback URL validation | `subscriptions/` | `[ ]` | - |

---

## Ringkasan Temuan

| Severity | Jumlah | Items |
|----------|--------|-------|
| CRITICAL | 0 | - |
| HIGH | 0 | - |
| MEDIUM | 0 | - |
| LOW | 0 | - |

---

## Rekomendasi Prioritas

| # | Rekomendasi | Severity | Effort | Status |
|---|-------------|----------|--------|--------|
| - | Belum ada | - | - | - |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi | Commit/PR | Status |
|---|---------|-----------|-----------|--------|
| - | - | - | - | - |

---

## Checklist Sign-off

- [ ] OWASP A01-A10 reviewed
- [ ] All CRITICAL/HIGH fixed
- [ ] Reviewer sign-off
