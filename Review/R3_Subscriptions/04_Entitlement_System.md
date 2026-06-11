# R3.4 - Review Entitlement System

**Status:** `[x]` SELESAI DIREVIEW - PASS
**Terakhir diperbarui:** 2026-02-17

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| File | `subscriptions/entitlements.py` |
| Models | `SubscriptionPlan`, `SubscriptionFeature`, `PlanFeatureEntitlement` |
| Function | `get_feature_access(user, feature_code)` |
| Integrasi | `accounts/middleware.py`, `accounts/mixins.py`, `accounts/models.py` |

---

## Feature Matrix (Efektif)

| Feature Code | Trial Aktif | Trial Belum Aktif | PRO Aktif | Expired |
|-------------|-------------|-------------------|-----------|---------|
| `FEATURE_WRITE_ACCESS` | Allow | Deny | Allow | Deny |
| `FEATURE_EXPORT_CLEAN` | Deny | Deny | Allow | Deny |
| `FEATURE_EXPORT_EXCEL_WORD` | Deny | Deny | Allow | Deny |
| `FEATURE_EXPORT_PDF` | Deny | Deny | Allow | Allow + Watermark |
| `FEATURE_PRO_ONLY` | Deny | Deny | Allow | Deny |

Catatan:
- `TRIAL` tanpa window aktif (`trial_end_date` null/expired) dinormalisasi ke status internal `TRIAL_PENDING` agar tidak mewarisi hak `EXPIRED` untuk PDF watermark.
- `PRO` non-aktif tetap dinormalisasi ke `EXPIRED`.

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-1 | Trial aktif -> `WRITE_ACCESS` | allowed=True | `[x]` | PASS |
| TC-2 | Trial aktif -> `EXPORT_PDF` | allowed=False (`TRIAL_NO_EXPORT`) | `[x]` | PASS |
| TC-3 | Trial belum aktif -> `EXPORT_PDF` | allowed=False (`TRIAL_NO_EXPORT`) | `[x]` | PASS |
| TC-4 | PRO aktif -> `EXPORT_EXCEL_WORD` | allowed=True | `[x]` | PASS |
| TC-5 | Expired -> `WRITE_ACCESS` | allowed=False | `[x]` | PASS |
| TC-6 | Expired -> `EXPORT_PDF` | allowed=True + `add_watermark=True` | `[x]` | PASS |
| TC-7 | Staff/admin bypass | allowed=True (`ALLOWED_ADMIN`) | `[x]` | PASS |
| TC-8 | Plan-level override deny | `source='plan'`, access denied | `[x]` | PASS |
| TC-9 | Unknown feature code | Graceful deny | `[x]` | PASS |

Evidence test suite:
- `subscriptions.tests.EntitlementPolicyEngineTests`
- `subscriptions.tests.EntitlementFeatureGatingDecoratorTests`

---

## Temuan (Findings)

| # | Severity | Deskripsi | Lokasi | Evidence |
|---|----------|-----------|--------|----------|
| F-1 | **RESOLVED (was HIGH)** | Trial belum aktif sempat diperlakukan sebagai `EXPIRED`, sehingga bisa lolos export PDF watermark. Kini dipetakan ke status internal `TRIAL_PENDING` (deny semua export). | `subscriptions/entitlements.py:23`, `subscriptions/entitlements.py:57`, `subscriptions/entitlements.py:157` | Regression test PASS 2026-02-17: `test_pdf_export_blocks_trial_pending_user` |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Pertahankan normalisasi status efektif (`TRIAL_PENDING`) agar trial belum aktif tidak mendapatkan hak export | P0 | Low | F-1 (`[DONE]`) |
| REC-2 | Pertahankan regression tests entitlement + decorator gating dalam pipeline CI | P1 | Low | F-1 (`[DONE]`) |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-17 | Audit entitlement engine + verifikasi matrix aktual terhadap kode | - | DONE |
| 2 | 2026-02-17 | Perbaikan status normalisasi trial belum aktif (`TRIAL_PENDING`) untuk menutup celah export PDF | - | DONE |
| 3 | 2026-02-17 | Tambah regression tests decorator gating (PDF/Excel/Word) | - | DONE |

---

## Checklist Sign-off

- [x] Matrix sesuai business rules
- [x] `get_feature_access()` returns correct decisions
- [x] Staff/admin bypass works
- [x] Edge cases handled
- [ ] Reviewer sign-off
