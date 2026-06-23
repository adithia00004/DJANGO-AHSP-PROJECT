# R3.9 - Implementation Execution Tracker (Subscriptions)

**Mulai:** 2026-06-23
**Plan otoritatif:** [08_Implementation_Plan_20260623.md](08_Implementation_Plan_20260623.md)
**Registry temuan:** [00_Audit_Summary_20260623.md](00_Audit_Summary_20260623.md) (A1–A17)
**Status keseluruhan:** **IN PROGRESS** — eksekusi M1 dimulai dari SUB-1.
**Baseline test (2026-06-23):** `test subscriptions` = **23/23 PASS**; `check` PASS; `makemigrations --check` PASS. Semua perubahan diukur terhadap baseline ini.

---

## 1. Aturan Tracking (kapan dokumen ini WAJIB diperbarui)

Perbarui dokumen ini setiap kali:
- sebuah item (SUB-*/ACC-*) **dimulai, selesai, diblokir, atau berubah scope**;
- ada **perubahan kode** (file dimodifikasi/ditambah/dihapus) → catat di §3 + §4;
- **keputusan** baru diambil atau keputusan lama berubah → catat di §5;
- **artefak ditambah atau dihapus** (command, migrasi, template, test, endpoint) → catat di §4;
- **baseline/test** menghasilkan kegagalan baru atau gate hijau → catat di §6;
- ditemukan kondisi yang **belum dibahas** dalam audit/plan → catat di §7 dan rujuk balik ke doc 00/08.

Aturan emas: **tidak ada perubahan kode tanpa baris di §3.** Tidak ada file baru/terhapus tanpa baris di §4.

### Status legend

| Status | Arti |
|---|---|
| `PENDING` | belum dimulai |
| `IN PROGRESS` | sedang dikerjakan |
| `BLOCKED` | tertahan keputusan/dependency |
| `DONE` | Definition of Done (doc 08) terpenuhi + test hijau |
| `DEFERRED` | ditunda dengan alasan + gate eksplisit |
| `REMOVED` | diselesaikan via cleanup/penghapusan |

---

## 2. Progress Work Item

> Paket SUB = `subscriptions/`; Paket ACC = `accounts/`. ⇄ = lintas-area.

| Item | Paket | Temuan | Prio | Status | Mulai | Selesai | Gate/Dependency | Branch/Commit |
|------|-------|--------|------|--------|-------|---------|-----------------|---------------|
| SUB-1 | SUB | A11+A5 | P0 | DONE | 2026-06-23 | 2026-06-23 | PASS: targeted 6/6; full 52/52; check PASS; makemigrations PASS | `e9475bed` (branch `fix/subscriptions-sub1-idempotent-activation`) |
| SUB-2 | SUB | A3 | P0 | PENDING | - | - | Baseline | - |
| SUB-3 | SUB | A1 | P0 | PENDING | - | - | Baseline | - |
| SUB-4 ⇄ | SUB | A2 | P0 | PENDING | - | - | **SUB-1** | - |
| ACC-1 ⇄ | ACC | A12 | P1 | PENDING | - | - | **SUB-1** | - |
| SUB-5 | SUB | A4 | P1 | PENDING | - | - | SUB-4 (reuse helper) | - |
| SUB-6 | SUB | A6/A7/A8 | P1 | PENDING | - | - | Baseline | - |
| SUB-7 | SUB | A13 | P2 | PENDING | - | - | data dedupe | - |
| ACC-2 | ACC | A15 | P2 | PENDING | - | - | D-3 (✅) | - |
| SUB-8 | SUB | A9 | P3 | PENDING | - | - | - | - |
| SUB-9 | SUB | A10a/A10b | P3 | PENDING | - | - | - | - |
| SUB-10 ⇄ | SUB | A14 (helper) | P3 | PENDING | - | - | - | - |
| ACC-4 ⇄ | ACC | A14 (sites) | P3 | PENDING | - | - | **SUB-10** | - |
| ACC-3 | ACC | A16 | P3 | PENDING | - | - | - | - |

**Milestone:** M1 (go-live) = SUB-1, SUB-2, SUB-3, SUB-4, ACC-1 · M2 = SUB-5, SUB-6 · M3 = SUB-7, ACC-2 · M4 = SUB-8, SUB-9, SUB-10, ACC-4, ACC-3.

---

## 3. Change Log (Perubahan kode)

> Satu baris per perubahan bermakna. M=modified, A=added, D=deleted.

| # | Tanggal | Item | File(s) | Aksi | Ringkasan perubahan | Test | Commit |
|---|---------|------|---------|------|---------------------|------|--------|
| 1 | 2026-06-23 | SUB-1 | `subscriptions/views.py`, `accounts/models.py` | M | Webhook aktivasi kini idempotent berbasis `paid_at`; late `cancel/deny/expire` setelah aktivasi diabaikan; handler `refund` mengubah transaksi ke REFUND dan revoke subscription user tanpa menghapus marker aktivasi. | PASS | `e9475bed` |
| 2 | 2026-06-23 | SUB-1 | `subscriptions/tests.py` | M | Tambah regression test untuk refund revoke, preservasi `paid_at`, replay settlement pasca-refund, dan late deny setelah success. | PASS | `e9475bed` |
| 3 | 2026-06-23 | SUB-1 | `Review/R3_Subscriptions/00_Audit_Summary_20260623.md`, `02_Payment_Flow.md`, `05_Webhook_Security.md`, `09_Implementation_Execution_Tracker_20260623.md` | M | Update status dokumentasi: A5/A11 tertutup oleh SUB-1; A12 tetap pending. | PASS | `b165e752` |

---

## 4. Ledger Penambahan & Penghapusan Artefak

> Lacak artefak BARU yang kita buat dan artefak LAMA yang kita hapus/deprecate, beserta alasan & guard.

### 4.1 Penambahan (Additions)

| # | Tanggal | Item | Artefak baru | Jenis | Alasan |
|---|---------|------|--------------|-------|--------|
| 1 | 2026-06-23 | SUB-1 | `test_refund_after_success_revokes_access`; `test_refund_preserves_activation_marker`; `test_replay_settlement_after_refund_does_not_reactivate`; `test_late_deny_after_success_does_not_overwrite_success` | Regression tests | Guard A11/A5 agar refund mencabut akses, replay sukses tidak mengaktifkan ulang, dan terminal webhook terlambat tidak menimpa success. |
| 2 | 2026-06-23 | SUB-1 | `CustomUser.revoke_subscription(revoked_at=None)` | Method (API baru `accounts`) | Mencabut akses PRO segera (set EXPIRED + `subscription_end_date=now`) untuk D-1; dipakai handler refund webhook. Lihat catatan EC-1 §7. |

### 4.2 Penghapusan / Deprecation (Deletions)

| # | Tanggal | Item | Artefak dihapus/deprecated | Pengganti / Guard | Alasan |
|---|---------|------|----------------------------|-------------------|--------|
| - | - | - | _(belum ada)_ | - | - |

---

## 5. Decisions Ledger

> Keputusan owner & kontrak teknis. Keputusan runtime baru diberi nomor lanjut (D-4, D-5, …).

| # | Tanggal | Keputusan | Konteks/Alasan | Dampak implementasi |
|---|---------|-----------|----------------|---------------------|
| D-1 | 2026-06-23 | **Refund → CABUT akses PRO segera** | Integritas: refund/chargeback tak boleh tetap dapat akses | SUB-1 + ACC-1: handler `refund` set status REFUND **dan** turunkan user ke EXPIRED |
| D-2 | 2026-06-23 | **Rate-limit webhook di EDGE/WAF** (di luar kode) | Limit app-level berisiko men-drop burst notifikasi Midtrans yang sah | A6 webhook → runbook ops; di kode hanya `create_payment` (SUB-6) |
| D-3 | 2026-06-23 | **Implement email reminder sekarang** | Tutup celah silent-churn (task saat ini stub) | ACC-2 = tulis pengiriman email reminder |

---

## 6. Test & Gate Log

| # | Tanggal | Item | Perintah | Hasil | Catatan |
|---|---------|------|----------|-------|---------|
| 0 | 2026-06-23 | baseline | `test subscriptions --settings=config.settings.test` | **23/23 PASS** | titik nol sebelum perubahan |
| 1 | 2026-06-23 | SUB-1 | `python manage.py test subscriptions.tests.PaymentWebhookIdempotencyTests --settings=config.settings.test --noinput --verbosity 1` | **6/6 PASS** | refund revoke, marker `paid_at`, replay settlement pasca-refund, late deny |
| 2 | 2026-06-23 | SUB-1 | `python manage.py test subscriptions --settings=config.settings.test --noinput --verbosity 1` | **27/27 PASS** | subscriptions gate setelah 4 regression test baru |
| 3 | 2026-06-23 | SUB-1 | `python manage.py test subscriptions accounts --settings=config.settings.test --noinput --verbosity 1` | **52/52 PASS** | full subscriptions+accounts gate |
| 4 | 2026-06-23 | SUB-1 | `python manage.py check --settings=config.settings.test` | **PASS** | warning Allauth deprecation existing |
| 5 | 2026-06-23 | SUB-1 | `python manage.py makemigrations --check --dry-run --settings=config.settings.test` | **PASS** | no changes detected |

**Gate per-item (Definition of Done, doc 08):** kode + regression test baru hijau di `config.settings.test`; tidak menurunkan baseline (subscriptions 23/23 + accounts existing); doc review terkait diupdate; migrasi → `makemigrations --check` bersih.

---

## 7. Catatan / Temuan Baru Selama Implementasi (Deviasi dari Plan)

> Bila saat coding ditemukan hal di luar audit/plan, catat di sini dan rujuk balik ke doc 00/08 (jangan diam-diam ubah scope).

| # | Tanggal | Item | Temuan/Deviasi | Tindakan |
|---|---------|------|----------------|----------|
| EC-1 | 2026-06-23 | SUB-1 | **Revoke bersifat account-wide.** `revoke_subscription()` set `subscription_end_date=now` + EXPIRED untuk SELURUH akun. Bila user punya >1 transaksi sukses dengan masa berlaku tumpang-tindih (mis. renewal mendekati expiry), refund pada SATU order ikut mencabut sisa masa berlaku order lain. **Eksposur rendah**: `CheckoutView` memblok checkout saat `is_subscription_active`, jadi overlap umumnya hanya via renewal-near-expiry atau direct `create_payment`. **Bukan regresi SUB-1** (D-1 diimplementasikan sesuai spec) dan **bukan blocker**. | Track sebagai **refinement D-1** (kaitkan ke A12/ACC-1): saat revoke, pertimbangkan recompute `subscription_end_date` dari transaksi sukses non-refund tersisa, bukan blanket EXPIRED. Verifikasi auditor: kode + 6/6 test PASS independen. |

---

## 8. Konvensi Commit & Branch

- Branch per paket/item (mis. `fix/subscriptions-sub1-idempotent-activation`) agar PR/review terisolasi (sesuai keputusan struktur per-area).
- Pesan commit merujuk ID item + temuan (mis. `SUB-1 (A11/A5): idempotent activation by paid_at + refund revoke`).
- Setiap commit yang menyentuh kode HARUS punya baris di §3; setiap file baru/hapus di §4.
- Update kolom Status §2 + Branch/Commit saat item DONE.
