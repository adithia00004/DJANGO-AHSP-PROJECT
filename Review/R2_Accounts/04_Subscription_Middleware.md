# R2.4 - Review Subscription Middleware & Access Control

**Status:** `[x]` SELESAI DIREVIEW - PASS
**Terakhir diperbarui:** 2026-02-17

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| File | `accounts/middleware.py` |
| Class | `SubscriptionMiddleware` |
| Decorator/Mixin | `accounts/mixins.py` |
| Policy Engine | `subscriptions/entitlements.py` |

---

## Audit Fungsional

### Middleware Test Cases

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-1 | Expired user -> GET | Allowed (read-only) | `[x]` | PASS |
| TC-2 | Expired user -> POST web | Redirect ke pricing | `[x]` | PASS |
| TC-3 | Expired user -> POST API (Accept JSON) | JSON 403 | `[x]` | PASS |
| TC-4 | Path excluded (`/accounts/*`, `/admin/*`, `/pricing/`) | Bypass check | `[x]` | PASS |
| TC-5 | Anonymous request | Lewat ke auth/view layer | `[x]` | PASS |
| TC-6 | TRIAL tanpa `trial_end_date` -> POST | Semestinya dibatasi sampai trial valid | `[x]` | PASS - kini diblok (403 JSON / redirect pricing) karena status entitlement dinormalisasi ke `EXPIRED` |

### Decorator/Mixin Test Cases

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-7 | `@api_subscription_required` untuk expired | 403 JSON | `[x]` | PASS |
| TC-8 | `@api_export_excel_word_required` untuk trial | 403 JSON | `[x]` | PASS (berdasarkan matrix) |
| TC-9 | `@api_pdf_export_allowed` untuk expired | Allowed + watermark context | `[x]` | PASS (berdasarkan matrix) |

---

## Temuan (Findings)

| # | Severity | Deskripsi | Lokasi | Evidence |
|---|----------|-----------|--------|----------|
| F-1 | **RESOLVED (was HIGH)** | Gap policy write-access telah ditutup: status `TRIAL`/`PRO` non-aktif kini dinormalisasi ke `EXPIRED` sebelum entitlement dievaluasi. | `subscriptions/entitlements.py:141`, `subscriptions/entitlements.py:178` | Runtime + test 2026-02-17: user `TRIAL` + `trial_end_date=None` -> `SUBSCRIPTION_EXPIRED`, POST API diblok `403`. |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Ubah rule `FEATURE_WRITE_ACCESS` untuk `TRIAL` agar mensyaratkan trial aktif (`trial_end_date` ada dan belum lewat), bukan status string saja | P0 | Medium | F-1 (`[DONE]` via normalisasi status efektif) |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-17 | Revalidasi middleware + decorator via `accounts.tests` dan runtime request simulation | - | DONE |
| 2 | 2026-02-17 | Implement normalisasi status efektif di entitlement policy (`TRIAL/PRO` non-aktif -> `EXPIRED`) + tambah regression tests | - | DONE |

---

## Checklist Sign-off

- [x] Middleware mechanics (redirect/JSON/path exclude) OK
- [x] Decorator/mixin behavior matrix OK
- [x] Policy consistency terhadap trial lifecycle OK
- [ ] Reviewer sign-off
