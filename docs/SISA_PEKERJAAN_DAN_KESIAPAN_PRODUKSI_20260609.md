# Sisa Pekerjaan & Tingkat Kesiapan Produksi

**Tanggal:** 2026-06-09
**Branch:** `checkpoint/save-sync-plan-20260608` (HEAD `75dff35b`, sinkron dengan origin)
**Konteks:** disusun setelah konsolidasi seluruh WIP (C0–C7), migrasi data ke Docker SSOT, dan penyelesaian plan Save/Sync (3C). Dokumen ini melengkapi `IMPLEMENTATION_PLAN_SAVE_SYNC_20260608.md` dan `OPAQUE_ID_CHECKLIST.md`.

---

## 1. Ringkasan Eksekutif

- **Fitur inti SUDAH JALAN** di environment Docker (SSOT): Save/Sync, AHSP/Volume, Opaque ID parameter, import AHSP 2026, pricing/subscription. Web + 6 container Docker **healthy**.
- **BELUM siap launch publik.** Penahan utama **bukan** bug fitur, melainkan: **(a) hardening keamanan**, **(b) backup SSOT belum terjadwal**, **(c) gate kualitas (1 test merah + CI merah) & revalidasi karena cakupan branch membesar**, **(d) UAT manual belum**.
- Save/Sync sendiri: fondasi & kode selesai, namun **status plan ≠ 100%** karena gate harus diulang setelah commit C0–C7 menumpang masuk.

---

## 2. Yang SUDAH Selesai (ringkas)

| Area | Status |
|---|---|
| Save/Sync Fase 1–3 (no-store, bootstrap, LED, last-save-wins, 3C Import Validate) | ✅ Kode + test |
| V1–V4 (build/manifest, migration drift, css legacy, triase test) | ✅ |
| Migrasi data → Docker SSOT (159 proyek, AHSP 2026, pricing) | ✅ + backup satu-kali |
| Konsolidasi WIP berbulan-bulan jadi commit scoped (C0–C7) | ✅ dipush |
| Healthcheck worker (celery/flower) | ✅ semua healthy |
| Deskripsi PR #5 | ✅ diperbarui |

---

## 3. Sisa Pekerjaan — Prioritas & Dampak

Skala prioritas:
- **P0 = Blocker/Urgent** (keamanan/keselamatan data; harus sebelum dipakai serius/launch).
- **P1 = Sebelum launch** (kualitas/verifikasi; tak boleh launch tanpa ini).
- **P2 = Pasca-launch / opsional** (peningkatan; tak memblokir).

### P0 — Blocker (keamanan & data)

| # | Item | Status | Dampak bila diabaikan | Aksi |
|---|---|---|---|---|
| P0-1 | **Hardening keamanan SSOT** | ❌ | Superuser `admin/admin` di DB data nyata + port `:8000` & `:5432` bind `0.0.0.0` + mode `development` + (kemungkinan) `SECRET_KEY`/`POSTGRES_PASSWORD` default. **Jika mesin terjangkau jaringan → data klien bisa diakses/diubah pihak luar.** | Ganti/nonaktifkan dev-admin + password kuat; ikat port ke `127.0.0.1` (jika lokal) atau pasang firewall; `DJANGO_ENV` non-development; `SECRET_KEY` & DB password kuat |
| P0-2 | **Backup terjadwal SSOT** | ❌ | Data Juni kini "live" di volume Docker; hanya ada **dump satu-kali**. Volume rusak/terhapus → kehilangan seluruh kerja sejak migrasi. | Jadwalkan backup berkala (`scripts/safe_backup_db.sh`) + uji restore |
| P0-3 | **Cegah divergensi dua-DB** | ❌ | PG16 native masih jalan & menjawab `localhost:5432`. `runserver` host tak sengaja menulis ke **DB lama** → dua salinan menyimpang, sulit direkonsiliasi. | Pakai **hanya** Docker; setelah yakin, hentikan service `postgresql-x64-16` native |
| P0-4 | **1 test merah + CI merah** | ❌ | Gate kualitas gagal → tak boleh merge/deploy; regresi bisa lolos. (Suite terbaru: 403 passed, **1 failed**, 40 skipped.) | Identifikasi & perbaiki test gagal; selidiki & hijaukan CI |

### P1 — Sebelum launch (kualitas & verifikasi)

| # | Item | Status | Dampak | Aksi |
|---|---|---|---|---|
| P1-1 | **Revalidasi gate staging/browser** | 🟡 PARTIAL | Gate lama lulus, tapi C0–C7 masuk setelahnya → tak valid. Tanpa ini, perilaku runtime fitur terbaru belum terbukti. | Rebuild/restart → ulang runtime/browser gate |
| P1-2 | **UAT manual proyek nyata** | ❌ | Approval gate sebelum PR ready/merge. Tanpa UAT, bug alur nyata bisa lolos ke user. | Uji end-to-end di proyek nyata (input volume, formula, export, jadwal, import) |
| P1-3 | **QA sign-off Opaque ID (Gate D/Phase 2) + monitoring** | 🟡 | Migration opaque sudah dijalankan di target; tanpa sign-off + window monitoring, regresi parameter/formula bisa tak terdeteksi. | Jalankan AC Gate D; pantau error 1 minggu (`opaque_daily_monitor.sh`) |
| P1-4 | **Review & rapikan PR #5** | 🟡 | PR membesar (~295 file). Tanpa review, risiko merge kode tak ter-review ke main. | Review per area; pisah bila perlu sebelum merge |
| P1-5 | **Update dokumen tracker** | 🟡 | Item 4 mencatat celery/flower unhealthy yang **sudah diperbaiki** sesi ini; dokumen perlu sinkron. | Update tracker: healthcheck DONE |

### P2 — Pasca-launch / opsional

| # | Item | Status | Dampak | Aksi |
|---|---|---|---|---|
| P2-1 | **3B util save read-after-write seragam** | ⏸️ DEFERRED | Kualitas (kurangi kedip/duplikasi). Ditunda sengaja; Volume/Harga sudah aman fungsional. | Evaluasi pasca-launch berbasis bukti |
| P2-2 | **Test Opaque M5/R1/C2-C3** | ⏸️ | Cakupan test (perf 100+ param, feature-flag off, E2E concurrent). | Lengkapi pasca-stabil |
| P2-3 | **Cleanup guard `ProgrammingError` opaque** | ⏸️ | Kode kompatibilitas sementara untuk env belum-migrasi. | Hapus setelah semua env confirmed migrated |
| P2-4 | **CI frontend (vitest)** | ⏸️ | Test JS belum jalan di CI. | Tambah job Node yang benar (terverifikasi hijau) |
| P2-5 | **Dev superuser `admin/admin` di entrypoint** | 🟡 | Lihat P0-1; idealnya entrypoint tak membuat kredensial lemah di mode non-dev. | Kondisikan pembuatan admin hanya untuk dev lokal |

---

## 4. Tingkat Kesiapan Produksi (Production Readiness)

Penilaian per-area (0–100%), berdasarkan kondisi 2026-06-09:

| Area | Kesiapan | Catatan |
|---|---|---|
| **Fungsionalitas inti** (save/sync, AHSP, opaque, pricing, import) | **~90%** | Fitur lengkap & berjalan; UAT nyata belum menutup |
| **Keamanan / hardening** | **~40%** 🔴 | admin/admin, port `0.0.0.0`, mode dev, kemungkinan secret/DB password default — **BLOCKER** |
| **Keandalan data & backup** | **~55%** 🟠 | SSOT live + dump satu-kali; backup terjadwal & uji-restore belum |
| **Gate kualitas (test/CI)** | **~70%** 🟠 | Mayoritas hijau; **1 test merah + CI merah** harus ditutup |
| **Operasional / deploy** | **~50%** 🟠 | Docker SSOT lokal jalan; belum ada deploy produksi nyata; monitoring opaque belum berjalan |
| **Verifikasi / UAT** | **~30%** 🔴 | UAT proyek nyata & browser gate ulang belum |

### Skor keseluruhan: **~60% — "Siap FITUR, belum siap LAUNCH publik"**

**Verdict:**
- ✅ **Layak untuk pemakaian internal terkontrol** (mesin terisolasi, hanya operator tepercaya) **setelah P0-1 s/d P0-3** ditutup.
- ❌ **Belum layak launch publik** sampai **P0 (semua)** + **P1-1, P1-2** selesai.
- 🎯 **Jalur tercepat ke "siap launch terbatas":** tutup **P0** (keamanan + backup + matikan DB lama + test/CI hijau) → revalidasi gate → UAT proyek nyata.

---

## 5. Rekomendasi Urutan Eksekusi

1. **P0-1 Hardening** (admin, port, mode, secret/password) — lindungi data klien lebih dulu.
2. **P0-2 Backup terjadwal** + uji restore — amankan SSOT.
3. **P0-3 Matikan jalur PG16 native** — hentikan risiko divergensi.
4. **P0-4 Perbaiki 1 test merah + CI** — buka jalan merge.
5. **P1-1/P1-5 Revalidasi gate + update dokumen.**
6. **P1-2 UAT proyek nyata** → set PR ready → merge.
7. **P1-3 Sign-off & monitoring Opaque ID.**
8. P2 menyusul pasca-launch.

> Catatan: P0-1 menyentuh keamanan/akses dan P0-3 menyentuh infrastruktur DB — setiap langkah yang berdampak ke akses/produksi akan dikonfirmasi lebih dulu sebelum dieksekusi.
