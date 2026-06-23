# R3.4 - Review Entitlement System

**Status:** `[x]` SELESAI DIREVIEW - PASS (logika resolusi) + follow-up A9 (LOW) & A13 (MED, constraint) dari audit 2026-06-23
**Terakhir diperbarui:** 2026-06-23 (addendum audit + verifikasi independen; hasil PASS logika dipertahankan)

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
| A9 | 🟢 FIXED (SUB-8) | `except Exception: pass` dipersempit ke `except DatabaseError` + `logger.warning(exc_info=True)` sebelum fallback. Mock tanpa pk sudah ditangani early-return, jadi narrowing aman (terverifikasi 12/12 regresi entitlement/middleware). | `subscriptions/entitlements.py:get_feature_access` | Regression: `EntitlementDbErrorFallbackTests` (1/1) |
| A13 | 🟠 MED (audit 2026-06-23, verifikasi independen) | `UniqueConstraint(feature, plan, subscription_status)` **tidak** mencegah beberapa baris default status-level (`plan=NULL`) untuk feature+status yang sama. Terkonfirmasi **PostgreSQL 15** (default `NULLS DISTINCT` → `NULL ≠ NULL` pada unique index). Mitigasi app-level via `get_or_create` ada, tetapi safety-net DB tak efektif → risiko duplikat default dengan `access_level` bertentangan; `base_qs.filter(plan__isnull=True).first()` lalu non-deterministik. | `subscriptions/models.py:212-219`, migrasi `0002` | Telaah kode + `docker-compose.yml` (postgres:15-alpine) + Django 5.2 |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Pertahankan normalisasi status efektif (`TRIAL_PENDING`) agar trial belum aktif tidak mendapatkan hak export | P0 | Low | F-1 (`[DONE]`) |
| REC-2 | Pertahankan regression tests entitlement + decorator gating dalam pipeline CI | P1 | Low | F-1 (`[DONE]`) |
| REC-3 | Persempit `except Exception` menjadi error DB spesifik (mis. `DatabaseError`/`OperationalError`) dan tambahkan `logger.warning` sebelum fallback, agar kegagalan terlihat. | P3 | Low | A9 (`[DONE]` SUB-8) |
| REC-4 | Set `nulls_distinct=False` pada `UniqueConstraint` (didukung Django 5.2 + PG15 → `NULLS NOT DISTINCT`) agar default status-level `plan=NULL` benar-benar unik per feature+status. Bersihkan duplikat eksisting lebih dulu bila ada. | P2 | Low | A13 (`[TODO]`) |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-17 | Audit entitlement engine + verifikasi matrix aktual terhadap kode | - | DONE |
| 2 | 2026-02-17 | Perbaikan status normalisasi trial belum aktif (`TRIAL_PENDING`) untuk menutup celah export PDF | - | DONE |
| 3 | 2026-02-17 | Tambah regression tests decorator gating (PDF/Excel/Word) | - | DONE |
| 4 | 2026-06-23 | Audit + verifikasi independen: tambah A9 (except-pass) & A13 (UniqueConstraint NULL plan di PG15) | - | DONE (audit) |
| 5 | 2026-06-23 | SUB-8: `except DatabaseError` + `logger.warning` (A9) | branch `fix/subscriptions-sub8-entitlement-except` | DONE |

---

## Checklist Sign-off

- [x] Matrix sesuai business rules
- [x] `get_feature_access()` returns correct decisions
- [x] Staff/admin bypass works
- [x] Edge cases handled
- [ ] Reviewer sign-off
