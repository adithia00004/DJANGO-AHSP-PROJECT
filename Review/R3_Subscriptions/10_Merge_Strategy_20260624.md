# R3.10 - Strategi Merge (Subscriptions Audit Implementation)

**Tanggal:** 2026-06-24
**Tujuan:** Rencana merge/cleanup untuk 28 commit subscription (SUB-1..10 + ACC-1..4 + SUB-7), **tanpa eksekusi** — sesuai keputusan owner "siapkan strategi dulu, jangan bulk-merge".

---

## 1. Topologi Aktual (hasil pemetaan git)

| Ref | Commit | Catatan |
|-----|--------|---------|
| `main` | `69059282` | **170 commit di belakang** base subscription |
| `implementation/r5-master-plan-20260614` | `49d19840` | **= base subscription** (parent dari commit SUB-1) |
| `fix/sub7-a13-pg-gate` (tip saat ini) | `9a980e7c` | 28 commit subscription di atas `49d19840` |

- Subscription = **28 commit linear** (`49d19840..tip`), **tanpa merge commit**.
- **12 label branch** (`fix/subscriptions-sub1..9` kecuali sub7, `fix/accounts-acc1..3`, `fix/a14-entitlement-memoization`) + tip `fix/sub7-a13-pg-gate` — **semua `--merged` ke tip** (terverifikasi `git branch --merged` + `merge-base --is-ancestor`).
- File kode tersentuh (18): `accounts/{context_processors,middleware,models,tasks,tests}.py`, `config/{celery.py,settings/test_pg.py}`, `subscriptions/{entitlements,midtrans,models,reconciliation,tasks,tests,tests_pg,views}.py` + `management/commands/reconcile_pending_payments.py` + `migrations/0006_*.py` + `templates/.../checkout.html` + dok `Review/R3_Subscriptions/*`.

---

## 2. Tiga Fakta Kunci (menghindari kesalahpahaman)

1. **"Stack branch panjang" = sekadar label pada SATU garis linear.** Branch-branch itu sudah saling terintegrasi di `fix/sub7-a13-pg-gate`. **Tidak ada konflik antar-branch untuk diselesaikan** dan tak perlu "menggabungkan" mereka — cukup hapus labelnya.
2. **Subscription TIDAK bisa di-merge ke `main` sendirian.** `main` tertinggal 170 commit dari base subscription (`49d19840`); di antaranya seluruh lineage R5 / WP-Export / save-sync / launch-prep. Rebase 28 commit langsung ke `main` → konflik masif. Mencapai `main` adalah **keputusan project-wide tentang seluruh garis R5**, di luar scope subscription.
3. **File R5 lokal** (`Review/R5_Detail_Project/31_…`) **tidak pernah di-commit** di stack ini → tak akan ikut merge apa pun. Tetap jaga keluar: **jangan `git add -A` / `git commit -a`**, selalu pathspec eksplisit (seperti sepanjang implementasi).

---

## 3. Rekomendasi (scope subscription)

### Langkah 1 — Konsolidasi subscription ke branch integrasi R5 (fast-forward, linear)
Karena `fix/sub7-a13-pg-gate` adalah descendant linear dari `implementation/r5-master-plan-20260614`:
```bash
git checkout implementation/r5-master-plan-20260614
git merge --ff-only fix/sub7-a13-pg-gate   # FF → tanpa merge commit, history tetap linear
```
Hasil: branch integrasi R5 kini memuat 28 commit subscription.

### Langkah 2 — Hapus label branch yang redundan (aman: hanya yang sudah merged)
```bash
git branch -d \
  fix/subscriptions-sub1-idempotent-activation fix/subscriptions-sub2-order-id \
  fix/subscriptions-sub3-snap-toggle fix/subscriptions-sub4-reconcile \
  fix/subscriptions-sub5-webhook-verify fix/subscriptions-sub6-webhook-hardening \
  fix/subscriptions-sub8-entitlement-except fix/subscriptions-sub9-pending-dedup \
  fix/accounts-acc1-atomic-activation fix/accounts-acc2-expiry-reminder \
  fix/accounts-acc3-effective-status-badge fix/a14-entitlement-memoization \
  fix/sub7-a13-pg-gate
```
`-d` (bukan `-D`) hanya menghapus bila sudah ter-merge → tak mungkin kehilangan commit. (Pertahankan beberapa label sebagai paper-trail bila diinginkan.)

### Langkah 3 — Mencapai `main` = KEPUTUSAN TERPISAH (project-wide)
Setelah Langkah 1, garis R5 = **198 commit** ahead of main (170 R5/export/save-sync + 28 subscription). Opsi (untuk diputuskan owner, **bukan** bagian audit ini):
- **R5 sebagai trunk de-facto:** kelak FF/merge `implementation/r5-master-plan-20260614` → `main` saat SELURUH garis siap (review besar, satu kali).
- **Review terfokus subscription dulu:** buka PR dengan **base = `49d19840`** (branch R5), **compare = tip subscription** → menampilkan persis 28 commit / 18 file + dok. PR ini reviewable tapi base-nya bukan `main` (tak langsung mergeable ke main).

---

## 4. Opsi PR / Squash (bila ingin history lebih ringkas)

- History 28 commit **sudah rapi**: pasangan `code` + `docs(tracker)` per item, pesan merujuk ID temuan, memetakan 1:1 ke tracker doc 09. Auditable apa adanya.
- Bila ingin lebih padat: squash **per-milestone** (M1/M2/M4) atau **per-paket** (SUB / ACC). Tidak wajib.
- Jangan squash lintas-item bila ingin mempertahankan ketertelusuran ke temuan A1–A16.

---

## 5. Catatan Deploy
- Stack subscription menambah **satu migrasi**: `subscriptions/migrations/0006_*` (A13: `NULLS NOT DISTINCT` + dedupe). PG-safe (aktif di PG15; di-skip diam-diam di SQLite — warning `models.W047` expected). Tak ada migrasi lain di stack.
- Saat garis R5 mencapai env/main + deploy: jalankan `migrate`. Beat baru `reconcile-pending-payments` (tiap 15 menit) perlu Celery beat aktif.

---

## 6. Yang JANGAN dilakukan
- ❌ Bulk-merge ke `main` yang stale tanpa rencana garis R5.
- ❌ `git add -A` / `git commit -a` (file R5 lokal ikut ter-stage).
- ❌ Rebase 28 commit langsung ke `main` (konflik masif krn 170 commit lineage hilang).
- ❌ `git branch -D` (force) untuk cleanup — pakai `-d` agar terlindung.

---

## 7. Status
Strategi ini **read-only** (tak ada merge/hapus dieksekusi). Eksekusi Langkah 1–2 aman & low-risk kapan pun; Langkah 3 menunggu keputusan project-wide tentang garis R5 → main.
