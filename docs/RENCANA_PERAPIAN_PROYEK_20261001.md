# Rencana Perapian Proyek (Owner + Codex + Claude) — v2

| | |
|---|---|
| Tanggal | 2026-10-01 (v1 pagi; **v2** sore, setelah verifikasi Codex) |
| Pembaca | Owner, Codex, Claude |
| Tujuan | Merapikan kondisi repo, dokumen, cara kerja, dan notifikasi (toast) **sebelum** memulai pekerjaan baru |
| Status | **Rencana implementasi** — menunggu keputusan owner di §7 (K-1..K-5, K-8, K-9). K-6/K-7 sudah disetujui |
| Dasar v2 | `docs/VERIFIKASI_RENCANA_PERAPIAN_PROYEK_20261001.md` (Codex, V-01..V-09). Seluruh temuan V-01..V-09 **dicek ulang Claude dan terbukti**. Ada dua tambahan dari Claude: daftar migrasi berisiko ternyata 11 berkas (§1), dan container hanya membaca folder proyek utama (R2) |

Cara membaca:
- §1 kondisi saat ini (fakta).
- §2 peta fase & ketergantungan.
- §3–§6 langkah per fase, lengkap dengan perintah dan kriteria selesai.
- §7 keputusan owner.
- §8 aturan kerja wajib.
- §9 tracker.
- §10 format bukti.
- §11 indeks dokumen.

Perubahan dari v1:
- **V-01:** tanggal `main` dikoreksi; 4 branch lama belum tergabung.
- **V-02:** inventaris migrasi dilengkapi.
- **V-03:** gerbang tes diperluas; tes PostgreSQL tidak menjalankan migrasi.
- **V-04..V-07:** spesifikasi toast dipertegas, dan bug batas jumlah toast ditambahkan.
- **V-08:** inventaris toast diklasifikasi, bukan dihitung kasar.
- **V-09:** toast menunggu merge; nama database tes unik per sesi; worktree tidak terbaca container.

---

## 1. Kondisi saat ini (snapshot HEAD `6c87a6e6`, 2026-10-01)

| Area | Kondisi | Bukti |
|---|---|---|
| `main` | `69059282`, tanggal commit **2026-02-11** (v1 salah menulis 06-08) | `git show -s --format=fuller main` |
| Garis kerja | 14 branch lama bertumpuk. Ditambah `fix/rekap-pdf-layout` (commit `230f975b`), yang sudah di-fast-forward ke `feat/tambahan-waktu-kerja`; ujung kini `6c87a6e6`, `main` ancestor → **fast-forward mungkin** (324 commit). Worktree kedua untuk branch fix PDF masih ada; A-6 perlu menutupnya sebelum menghapus ref | `git worktree list`, `git rev-list`, verifikasi Codex |
| Branch lama belum tergabung | 4 branch, **bukan** bagian garis kerja: `claude/fix-transaction-management-error-011CUox8f9ABCiXmbvqMPmtS` (1 commit, 2025-11-05), `codex/review-workflow_3_pages-and-create-agenda` (1, 2025-11-13), `fix/kurva-s-phase1-critical-fixes` (48, 2026-01-13), `refactor/bundle-quantity-semantic` (16, 2025-12-26). `git cherry` belum menemukan padanan patch, **tetapi isinya bisa saja sudah diintegrasikan ulang dengan cara lain** → perlu review (A-8) | `git branch --no-merged`, `git cherry` |
| WIP owner | W-1..W-4 sudah dipisah menjadi 3 commit (`bf92d0c7`, `de212bd8`, `6c87a6e6`); kode WIP tidak lagi tersisa di working tree | `git log -3`, bukti A-3 |
| Migrasi | 27 berkas migrasi di antara `main` dan ujung. **11 menyentuh data atau menambah constraint** (tabel di bawah). Jumlah yang *benar-benar pending* di DB produksi **belum diketahui** | `git diff --name-only main..HEAD -- '*/migrations/*.py'` |
| Tes | Setelah commit pada HEAD `6c87a6e6`: backend 5 app **1.041 tes, 0 gagal, 40 skipped**; Vitest **39 file, 432 lulus, 25 skipped**; `makemigrations --check` tanpa perubahan; `npm run build` lulus, `dist/` tidak berubah. Build memberi peringatan chunk Jadwal >500 kB yang sudah ada sebelumnya | bukti A-3/A-4 di §9 |
| Tes vs migrasi | `config/settings/test_pg.py` mewarisi `test.py` yang memasang `MIGRATION_MODULES = DisableMigrations()` → **tes lulus ≠ migrasi aman** | `config/settings/test.py:31-38` |
| Container | `ahsp_web` me-mount **hanya** `D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT` → `/app`. Worktree lain tidak terbaca `docker exec`. Image tidak memasang Git; cocokkan SHA sumber pada host dengan `sha256sum /app/<berkas>` untuk bukti kode yang dites | `docker inspect ahsp_web`; probe SHA 2026-10-01 |
| Fitur Tambahan Waktu Kerja + export | Selesai; UAT otomatis lulus (doc 41: 16/16, doc 43: 9/9). Sisa: cek visual owner | doc 41 §6, doc 43 §5 |
| Launch | Checklist terakhir `452401ae` (2026-06-10), masih **NO-GO**; commit ops sesudahnya belum tercermin | `docs/CHECKLIST_PROGRESS_KESIAPAN_LAUNCH_20260609.md` |
| Toast | 10 temuan (T-F1..T-F10), §5 | §5 |

### Migrasi berisiko (wajib diuji di salinan DB, A-7)

| Migrasi | Jenis | Risiko |
|---|---|---|
| `accounts/0003_customuser_trial_used_once` | RunPython | Backfill flag trial; salah hitung → user bisa trial ulang / terkunci |
| `dashboard/0017_project_additional_work_end` | CheckConstraint | Gagal bila data melanggar aturan tanggal tambahan |
| `detail_project/0042_templateahspkoefformulastate` | UniqueConstraint | Tabel baru; risiko rendah |
| `detail_project/0047_backfill_expanded_source_signature` | RunPython | Backfill signature seluruh data |
| `detail_project/0048_repair_expanded_source_signature` | RunPython | Mengubah signature data existing |
| `detail_project/0050_backfill_ref_snapshot_signature` | RunPython | Backfill signature |
| `detail_project/0051_detailahsp_koef_nonneg_constraint` | CheckConstraint | **Gagal bila ada koefisien negatif** → audit dulu |
| `referensi/0023_unique_registry_code_per_category` | UniqueConstraint | **Gagal bila ada kode duplikat per kategori** → audit dulu |
| `subscriptions/0003_paymenttransaction_base_amount_snapshot_and_more` | CheckConstraint | Gagal bila data transaksi melanggar |
| `subscriptions/0004_alter_subscriptionplan_options_and_more` | RunPython + UniqueConstraint | Backfill + unik |
| `subscriptions/0006_remove_planfeatureentitlement_…` | RunPython + UniqueConstraint | **Menghapus entitlement duplikat; reverse tidak memulihkan baris** → backup wajib |

---

## 2. Peta fase & ketergantungan

```
Fase A  Bersihkan meja kerja & merge  ──►  Fase C  Toast (branch dari main baru)
   │                                            │
   └──►  Fase B  Satu sumber kebenaran (dok)    └──►  Fase D  Arah berikutnya (launch/backlog)
```

- **C bergantung pada A** (V-09): branch toast dibuat dari `main` **setelah** merge A-5. Bila owner ingin toast lebih dulu, pilih K-9 = "pengecualian transisi" dan catat di tracker. Dalam hal itu branch toast dibuat dari `feat/tambahan-waktu-kerja` setelah WIP di-commit, **bukan** dari `main` lama.
- **B** bisa berjalan paralel dengan C setelah A selesai (hanya dokumen).
- **Pelaksana:** satu agen per fase aktif (K-5); agen lain mereview.

---

## 3. Fase A — Bersihkan meja kerja & merge

| # | Tugas | Perintah / cara | Selesai bila | Butuh |
|---|---|---|---|---|
| A-1 | **Cek visual owner.** Halaman Jadwal: tombol Perpanjang hanya di mode Realisasi, pesan sel terkunci, Kurva S melewati garis batas. Export: 12 sampel; pengesahan harian muat 1 halaman. Keputusan owner: XLSX bukan siap-cetak, jadi abaikan uji cetak seluruh workbook. PDF Rekap sudah diperbaiki di `230f975b`; sampel lama belum diekspor ulang | — | Owner memeriksa Word dan Jadwal live; OK / temuan dicatat di doc 41 §6, doc 43 §5, dan laporan cek visual | K-1 |
| A-2 | **Commit WIP owner** per topik, hanya hunk topiknya (R5): W-1 (List Pekerjaan + tes grow_tree), W-2 (Mass Edit), W-3+W-4 (timeline repair + template) | `git diff <f> > full.patch` → pilih hunk → `git apply --cached` | 3 commit; `git status` bersih kecuali berkas lokal | K-2 |
| A-3 | **Gerbang tes pada snapshot baru** (R4). Catat SHA, status WIP, perintah, settings, DB, pass/skip/fail (§10) | Suite **semua app terdampak**: `detail_project dashboard accounts subscriptions referensi` dengan `config.settings.test_pg` + DB unik (R3); `npm run test:frontend`; `npm run build` (dist tak berubah atau ikut di-commit) | Semua hijau; bukti di §9 | A-2 |
| A-4 | **Cek drift migrasi dengan migrasi aktif** (bukan settings tes) | `docker exec ahsp_web python manage.py makemigrations --check --dry-run` (settings dev) | "No changes detected" | A-2 |
| A-5 | **Merge ke `main`** | `git tag pre-merge-main-20261001 main` → `git switch main && git merge --ff-only feat/tambahan-waktu-kerja`. Tanpa push | `main` = ujung garis; tag ada | A-1, A-3, A-4, **K-2** |
| A-6 | **Hapus branch garis kerja yang sudah tergabung** | `git branch --merged main` → `git branch -d <b>` (**bukan** `-D`); hapus worktree kedua hanya setelah dipastikan bersih | 15 ref garis kerja (termasuk `fix/rekap-pdf-layout`) hilang; **4 branch lama tetap ada** sampai A-8 | A-5 |
| A-7 | **Uji migrasi di salinan DB produksi** (settings dengan migrasi aktif, bukan `test_pg`) | 1) `showmigrations` → daftar pending nyata. 2) Audit pra-migrasi: koef negatif (0051), duplikat kode registry per kategori (referensi 0023), duplikat entitlement (subs 0006), data pelanggar constraint dashboard 0017 / subs 0003. 3) Backup salinan. 4) `migrate`, catat durasi per migrasi. 5) Catat jumlah baris sebelum/sesudah tabel terdampak. 6) Uji restore dari backup | Laporan: daftar pending, hasil audit, durasi, selisih baris, restore OK | K-2 (akses salinan) |
| A-8 | **Review 4 branch lama** (§1): bandingkan patch terhadap `main`, putuskan per branch: sudah terintegrasi → hapus `-d`/arsip tag; masih relevan → backlog; usang → arsip tag lalu hapus | `git log -p main..<b>`, `git range-diff` bila perlu | Keputusan per branch tercatat; hanya dihapus setelah K-8 | K-8 |

| A-9 | **Bersihkan kode mati sesudah merge** (branch `chore/hapus-kode-mati` dari `main` baru, satu commit per kelompok): (a) Jadwal v1 `detail_project/static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/`: `module_manifest.js` + 7 modul yang hanya dirujuk manifest itu (`data_loader_module.js`, `grid_module.js`, `grid_tab.js`, `save_handler_module.js`, `shared_module.js`, `time_column_generator_module.js`, `validation_module.js`). **Pertahankan** `kelola_tahapan_page_bootstrap.js` (masih dimuat `kelola_tahapan_grid_modern.html`). Rujukan di `src/modules/core/*.js` hanya komentar "Migrated from"; (b) Referensi `referensi/static/referensi/js/ahsp_database.js` (digantikan `ahsp_database_v2.js`) dan `admin_portal.js` (tidak dimuat template mana pun); (c) opsional: `dist/stats.html` (artefak analisis build) → gitignore | Sebelum hapus: `git grep` nama berkas = 0 rujukan non-komentar; suite + Vitest + build hijau; cek halaman Jadwal & Referensi terbuka normal | A-5 |

**Hasil pemeriksaan isi merge (2026-10-01):** 14 branch lama bertumpuk lurus. Perbaikan PDF Rekap dibuat pada `fix/rekap-pdf-layout` (`230f975b`) lalu di-fast-forward ke `feat/tambahan-waktu-kerja`; tiga commit WIP menyusul. Jadi `main..HEAD` kini 324 commit dan fast-forward tetap mungkin. Ref/worktree `fix/rekap-pdf-layout` masih tersisa; A-6 harus melepas worktree bersih sebelum menghapus ref tersebut. `checkpoint/*` dan `implementation/*` hanya label titik tengah tanpa isi unik; ikut terhapus di A-6. Merge juga **berhenti melacak** 17.199 berkas `node_modules/` dan 2.690 berkas `cleanup_archive/`. Ini disengaja (`fb2d60a4`, `8483685e`, 2026-06-09): berkas tetap di disk dan sudah di-`.gitignore`. Sesudah merge, **jangan** `git clean -fdX` tanpa sadar, karena itu menghapus `node_modules` lokal dan arsip. Ikut dibuang pula ±45 berkas mati/cadangan lama (`*.bak`, `*_old`, dist bersarang salah tempat, template/JS halaman yang sudah pensiun); rute `orphan_cleanup`/`audit_trail` tetap dijaga tes admin-only. Sisa usang yang **masih ikut masuk** = A-9 dan dokumen perencanaan lama di root (B-3).

**Catatan:** tag Git hanya mengamankan kode, **tidak** membalikkan perubahan database. Rollback DB = restore backup A-7.

---

## 4. Fase B — Satu sumber kebenaran (dokumen)

| # | Tugas | Selesai bila |
|---|---|---|
| B-1 | Buat `docs/STATUS_PROYEK.md`: satu baris per area (Jadwal, Export, Dashboard, Referensi, Subscriptions/Accounts, Launch & Ops, Toast, Backlog audit). Kolom: status, dokumen detail, langkah berikutnya, bukti terakhir (SHA + tanggal) | Semua area punya baris & tautan |
| B-2 | Perbarui checklist launch sesuai commit Juni–Oktober (Sentry/STORAGES `b2ebb7fc`, `dfa388fa`, dll.) atau pindahkan ke B-1 | Status launch mencerminkan kode saat ini |
| B-3 | Label **"ARSIP — lihat docs/STATUS_PROYEK.md"** di baris pertama dokumen status usang (tidak dihapus). Termasuk 9 dokumen perencanaan di root repo yang ikut masuk merge (`AUDIT_VOLUME_PEKERJAAN.md`, `FORMULA_EDITOR_AUDIT.md`, `FORMULA_EDITOR_REMEDIATION.md`, `IMPLEMENTATION_PLAN_OPAQUE_ID.md`, `IMPLEMENTATION_PLAN_PROJECT_TIMELINE_WEEKLY_PROGRESS.md`, `IMPLEMENTATION_PLAN_TEMPLATE_AHSP_FORMULA.md`, `IMPLEMENTATION_PLAN_TEMPLATE_OPTIONS.md`, `OPAQUE_ID_CHECKLIST.md`, `REVIEW_PARAMETER_FORMULA.md`); opsional pindah ke `docs/arsip/` dengan `git mv` | Tiap dokumen jelas aktif/arsip |
| B-4 | Selaraskan dokumen detail yang tertinggal: mis. `Review/R5_Detail_Project/12_Export_System.md`; doc 44 §1 (tanggal `main` 2026-02-11, migrasi berisiko 11 berkas, 4 branch lama) | Tidak ada status bertentangan |
| B-5 | Verifikasi ulang backlog (tabel di bawah) dan masukkan ke B-1 | Tiap butir punya status terkini |

| Butir backlog | Catatan terakhir | Dokumen |
|---|---|---|
| SYN-01..07 Template AHSP terlalu sering minta muat ulang | Fase 1 + 4b dikerjakan (Agustus); 2/3/4a/4c belum; commit berlabel SYN tidak ditemukan | `Review/R5_Detail_Project/36_Cross_Page_Sync_Over_Notification_Audit_Plan_20260824.md` |
| N-6 kepercayaan IP klien | Harus repo-wide (helper tunggal) | `Review/R6_Referensi/00_Audit_Summary_20260624.md` |
| N-2 Referensi | Belum | idem |
| Kontrol Kalkulasi Excel | Ada di Rincian AHSP; Rekap RAB & Jadwal belum | doc 30 §7 |
| Aksesibilitas RA-13, HI-13..15 | Ditunda | doc 20 §13, doc 19 §13 |
| Opaque ID uji manual C2/C3, migrasi staging/prod | Belum | `OPAQUE_ID_CHECKLIST.md` |
| Laten export X-6 | Dicatat, tidak dicetak | doc 42 §5 |

---

## 5. Fase C — Notifikasi (toast)

Keluhan owner (2026-10-01): toast kembar, ada yang tidak hilang, sebagian sulit dipahami. Keputusan: **K-6** (sukses/info → toast; error/peringatan → tetap modal) dan **K-7** (T-2 + T-3 dulu) **disetujui**.

### 5.1 Temuan (dicek Claude, diverifikasi Codex dengan probe Node + happy-dom)

| # | Temuan | Dampak | Bukti |
|---|---|---|---|
| T-F1 | Durasi dikirim sebagai objek `{duration, position}`; inti mengharapkan angka → **tidak ada timer tutup** | Toast tidak pernah hilang (export, PNG, gagal export) | 7 pemanggilan `js/src/jadwal_kegiatan_app.js` ±1662, 1712, 1725, 3954, 3961, 3993, 4001; probe: nol timer |
| T-F2 | Pesan Django tampil sebagai modal harus-klik | Terasa permanen | `js/messages_modal.js`; `templates/base.html:352` |
| T-F3 | Toast hasil simpan dari dua lapisan | Kembar | `js/src/modules/core/save-handler.js:388/433` + `jadwal_kegiatan_app.js:3587/3595` |
| T-F4 | Toast proses validasi bundle tidak ditutup sebelum toast hasil (pada jalur `DP.toast`, `info(…,0)` menjadi 3000 ms, bukan permanen) | Tumpuk | `js/template_ahsp.js` |
| T-F5 | Jenis `danger` tak dikenal: kelas `dp-toast-danger` **tanpa gaya error**, **ikon info**; `DP.toast.danger` tidak ada → wrapper dinamis `DP.toast[type]` jatuh ke `info` | Pesan gagal tampak netral | probe Codex; `referensi/.../ahsp_database_api.js:51`, `dashboard/.../ux-enhancements.js:585` |
| T-F6 | Tidak ada deduplikasi di inti | Kembar | `js/core/toast.js` `show` |
| T-F7 | Banyak jalur toast: renderer aktif, fallback darurat, wrapper delegasi (Dashboard, 4 berkas Referensi sudah delegasi ke `DP.toast`), kemungkinan kode mati. **Jumlah pasti belum diklasifikasi** (lihat T-4) | Tampilan tidak seragam | V-08 |
| T-F8 | Bahasa teknis/campuran ("Rendering chart image…", "offscreen rendering (300 DPI)", "(1234ms)", `error.message` mentah, emoji + ikon ganda) | Sulit dipahami | `jadwal_kegiatan_app.js`, preset `core/toast.js` |
| T-F9 | `_showLoading` mengabaikan handle toast; `_hideLoading` hanya memulihkan tombol | Toast loading menempel | `js/src/export/ui-integration.js` (cakupan pemakaian dicek di T-4). Catatan: `js/export/ExportManager.js` **dimuat di semua halaman detail** lewat `templates/detail_project/base_detail.html:78`, jadi bila punya renderer toast sendiri, prioritasnya tinggi di T-4 |
| T-F10 | **Batas jumlah bocor:** `clampToasts()` dipanggil **sebelum** toast baru ditambahkan → maxVisible 3 menampilkan 4 | Tumpukan toast | `js/core/toast.js:177`; probe: 4 toast aktif |
| T-F11 | `duration: 0` dan durasi tidak valid diperlakukan `|| default`; wrapper `Toast` memaksa default 1600/2000/3000 ms | Durasi tak seragam walau inti diubah | `js/src/modules/shared/ux-enhancements.js:268-303` |

### 5.2 Spesifikasi kontrak `DP.toast` (T-1, ditulis sebagai komentar kepala `core/toast.js`)

**Bentuk pemanggilan yang WAJIB tetap didukung:**
1. `DP.toast.show({message, type, duration, title, closable, icon})`, dipakai antara lain oleh `referensi/static/referensi/js/import_progress.js:369`.
2. `DP.toast.show(message, type, durationOrOptions)`.
3. `DP.toast.success|error|info|warning(message, durationOrOptions)`.
4. **Baru:** `DP.toast.danger` (= `error`) dan `DP.toast.warn` (= `warning`) sebagai metode publik, agar wrapper dinamis `DP.toast[type]` bekerja.
5. `DP.core.toast.*` dan `window.showToast(...)` selama masa migrasi.

**Jenis:** `success`, `info`, `warning`, `error`, `loading`. Alias: `danger→error`, `warn→warning`. Jenis tak dikenal → `info`, dengan peringatan di console.

**Durasi** (argumen angka atau `{duration}`):

| Nilai | Makna |
|---|---|
| tidak diberikan / `undefined` / `null` | default jenis: sukses/info **3000**, peringatan **5000**, error **6000** ms (error selalu punya tombol tutup) |
| `0` | **menetap sampai ditutup** (hanya dihormati bila `closable` tidak `false`, atau untuk jenis `loading`) |
| angka > 0 | dipakai apa adanya, dibatasi maks 60000 ms |
| negatif / `NaN` / non-angka / objek tanpa `duration` | default jenis |
| `loading` | menetap sampai `dismiss(handle)`; **batas aman 60 dtk** lalu tutup otomatis |

Wrapper `Toast` (`ux-enhancements.js`) **tidak lagi** memaksa default sendiri; bila durasi tidak diberikan, teruskan `undefined` ke inti.

**Deduplikasi:**
- Kunci = `jenis + teks pesan` pada toast yang **sedang tampil**; jendela ±2 dtk sejak kemunculan terakhir.
- Duplikat → **batalkan timer lama**, jadwalkan ulang, perbarui penanda `×N` melalui `textContent` (**tidak** lewat HTML dari pesan).
- Peta kunci dibersihkan saat dismiss / clear / eviction oleh batas jumlah.
- **`loading` tidak dideduplikasi**: dua operasi berbeda dengan pesan sama tetap punya handle sendiri, supaya menutup satu tidak menghilangkan indikator operasi lain.

**Batas jumlah:** maks 3 toast tampil **termasuk yang baru**; kapasitas dihitung setelah dedupe; yang tertua (non-`loading` lebih dulu) digusur.

**Pengembalian:** setiap pemanggilan mengembalikan handle yang bisa diberikan ke `DP.toast.dismiss(handle)`.

### 5.3 Tugas

| # | Tugas | Isi | Tes wajib | Selesai bila |
|---|---|---|---|---|
| T-1 | Kontrak | Tulis §5.2 sebagai komentar kepala `core/toast.js` | — | Komentar ada; dirujuk di B-1 |
| T-2 | Perkuat inti `core/toast.js` + wrapper `ux-enhancements.js` | Normalisasi argumen & durasi (§5.2), alias jenis + metode `danger`/`warn`, dedupe, batas jumlah dibetulkan (T-F10), batas aman loading, handle + `dismiss`, CSS `.dp-toast-error` untuk alias | Vitest (happy-dom, timer palsu): tiap baris tabel durasi; `show('x','danger')` **dan** `DP.toast['danger']('x')` → gaya/ikon error; dedupe (timer lama dibatalkan, `×N` via textContent, peta dibersihkan); 4 toast berurutan → 3 tampil; dedupe × batas; dua `loading` pesan sama → tutup satu, satu tetap; loading tutup di 60 dtk; bentuk objek `show({...})` tetap jalan | Semua tes hijau |
| T-3a | T-F1 | Seragamkan 7 pemanggilan menjadi `Toast.x('…', <angka>)` | Tes sumber: tidak ada `Toast.*(…, {duration` di `jadwal_kegiatan_app.js` | Hijau + cek visual |
| T-3b | T-F3 | Satu sumber toast simpan, yaitu `SaveHandler`; toast di app dihapus, atau `SaveHandler` diberi opsi `silent` bila app perlu teks khusus | Vitest: satu simpan sukses = 1 toast; gagal = 1 toast | Hijau + cek visual |
| T-3c | T-F4 | Toast proses validasi bundle memakai `loading` + `dismiss(handle)` sebelum toast hasil | Tes sumber/perilaku | Hijau + cek visual |
| T-3d | T-F9 | `_showLoading` menyimpan handle; `_hideLoading` memanggil `dismiss` | Vitest | Hijau |
| T-6 | Pesan server (K-6) | `messages_modal.js`: cari **token level yang dikenal** di `tags` (bukan `split(' ')[0]`; ada `extra_tags='import-error'` di `referensi/views/preview.py:481,498`), atau kirim level sebagai atribut data terpisah dari template. success/info → `DP.toast`; error/warning → modal. **Tukar urutan** `core/toast.js` sebelum `messages_modal.js` di `templates/base.html:352-354`. Fallback modal bila `DP.toast` tak tersedia. Pertahankan detail/tautan pesan import | Django render: urutan skrip. Vitest perilaku: success/info → toast; error/warning → modal; tag gabungan dikenali; pesan campuran → masing-masing tampil **tepat sekali**; fallback modal | Hijau + cek visual (simpan project Dashboard, import Referensi gagal) |
| T-4 | Satukan implementasi | **Inventaris dulu** (tabel: lokasi, kelas = renderer aktif / fallback / wrapper delegasi / tak terpakai, dimuat di halaman mana). Migrasi satu halaman per commit: Harga Items → Rincian AHSP → Rekap Kebutuhan → Template AHSP → Dashboard → Referensi → `src/utils/error-handler.js` → `export/ExportManager.js` → `src/export/ui-integration.js`. Renderer aktif diganti panggilan `DP.toast`; fallback darurat boleh tetap bila `core/toast.js` bisa gagal dimuat; kode tak terpakai dihapus | **Tes penjaga** (Python, gaya `tests_export_json_separation.py`) pada sumber produksi saja (kecualikan `dist/`, arsip, `node_modules`, fixture/tes) yang melarang **renderer/penjadwal toast independen** di luar `core/toast.js` (membuat kontainer toast + `setTimeout` penutup), **bukan** sekadar nama `showToast`; adapter delegasi diizinkan | Inventaris di §9; penjaga hijau |
| T-5 | Bahasa pesan | Kumpulkan semua teks toast ke tabel "sebelum → sesudah" (bahasa Indonesia sederhana, tanpa ms/DPI/istilah teknis; error server → kalimat yang bisa ditindaklanjuti, detail teknis ke console) → **owner meninjau dulu** → baru ubah kode | Tes sumber untuk frasa terlarang yang disepakati | Owner menyetujui tabel; kode diubah |

**Urutan & commit:** T-1+T-2 (1 commit) → T-3a..d (1 commit per butir) → T-6 → T-4 (1 commit per halaman) → T-5. Setiap commit JS: `npm run test:frontend` + `npm run build` (bundle `dist/` ikut di-commit) + restart `ahsp_web` terkoordinasi (R8).

---

## 6. Fase D — Aturan kerja, lalu arah berikutnya

- **D-1:** owner menyetujui aturan §8 (K-3).
- **D-2:** owner memilih arah (K-4):
  - **A. Menuju launch (rekomendasi):** server nyata (domain, TLS, secret produksi, port DB/Flower ditutup); backup terjadwal + uji restore; CI remote; UAT browser proyek nyata termasuk Midtrans sandbox; keputusan GO/NO-GO. Sumber: checklist launch + `docs/RUNBOOK_DEPLOY_TLS_L5_L6.md`.
  - **B. Melunasi backlog dulu:** tabel §4.

---

## 7. Keputusan owner

| # | Keputusan | Status / rekomendasi |
|---|---|---|
| K-1 | Jadwal cek visual A-1 | ✅ **Selesai 2026-10-01**: owner menyetujui sampel v6 (PDF/Word/Excel; XLSX tidak perlu siap-cetak) dan perilaku toast |
| K-2 | Izin commit WIP (A-2), merge ke `main` (A-5), akses salinan DB produksi (A-7) | Commit WIP: dilakukan atas instruksi owner. ✅ **Merge ke `main` diizinkan owner 2026-10-01** (tanpa push). Akses salinan DB produksi (A-7) masih menunggu |
| K-3 | Setuju aturan kerja R1–R10 | Menunggu |
| K-4 | Arah berikutnya | Rekomendasi **A. Launch** |
| K-5 | Pelaksana | Rekomendasi: satu agen per fase, agen lain mereview |
| K-6 | Pesan server → toast/modal | ✅ Disetujui 2026-10-01: sukses/info → toast; error/peringatan → modal |
| K-7 | Urutan agenda toast | ✅ Disetujui 2026-10-01: T-2 + T-3 dulu, lalu T-6, kemudian T-4/T-5 |
| K-8 | Nasib 4 branch lama (A-8) | Rekomendasi: review patch dulu; yang usang → tag arsip `archive/<nama>` lalu `git branch -d`/`-D` **hanya** setelah owner setuju per branch |
| K-9 | Toast sebelum atau sesudah merge | ✅ **Diputuskan owner 2026-10-01: sekarang** (pengecualian transisi). Toast T-1/T-2/T-3/T-6 dikerjakan di `feat/tambahan-waktu-kerja` setelah A-2, ikut merge A-5. **Penyimpangan dari §5.2:** `duration: 0` pada toast biasa TIDAK menetap (kembali ke default jenisnya); hanya `loading` yang menetap (batas aman 60 dtk), sesuai keluhan owner soal toast permanen |

---

## 8. Aturan kerja (wajib untuk Codex dan Claude)

| # | Aturan | Cara menjalankan |
|---|---|---|
| R1 | **Satu fitur = satu branch dari `main` terbaru.** Tidak membangun di atas branch belum-merge, kecuali pengecualian transisi yang dicatat (K-9) | `git switch main && git switch -c <tipe>/<nama>`; tipe `feat`/`fix`/`docs`/`chore` |
| R2 | **Satu agen per branch.** Container `ahsp_web` hanya membaca folder proyek utama, jadi **tes Docker hanya menguji kode yang ter-mount dari folder utama**. Agen di worktree lain hanya boleh membaca/mereview, atau menjalankan tes di container/volume sendiri yang di-mount ke worktree-nya | Catat `git rev-parse HEAD` pada host; image saat ini tidak punya Git. Untuk membuktikan sumber yang diuji, cocokkan `Get-FileHash` host dengan `docker exec ahsp_web sha256sum /app/<berkas>` untuk berkas yang berubah |
| R3 | **DB tes unik per sesi/task** (bukan per hari) | `POSTGRES_TEST_DB=test_<agen>_<yyyymmdd>_<task>_<4 hex acak>` |
| R4 | **Definisi selesai:** (a) suite **semua app terdampak** 0 gagal (minimal `detail_project dashboard`; tambah `accounts subscriptions referensi` bila tersentuh / untuk gerbang merge); (b) Vitest + `npm run build` bila JS berubah, `dist/` ikut di-commit; (c) perubahan export mengikuti & memperbarui `docs/DESIGN_REGISTRY_EXPORT.md`; (d) cek visual owner untuk perubahan tampilan; (e) status dicatat; (f) merge ke `main` | Bukti format §10. **Tes `test_pg` tidak membuktikan migrasi** (migrasi dinonaktifkan); migrasi dibuktikan terpisah (A-4/A-7) |
| R5 | **Jangan menyentuh pekerjaan pihak lain;** stage hanya hunk sendiri | `git diff <f> > full.patch` → pilih hunk → `git apply --cached`. Jangan `git add <f>` utuh / `git commit -- <path>` |
| R6 | **Satu langkah = satu commit**, pesan bahasa Indonesia (apa & mengapa) | `tipe(area): ringkasan` |
| R7 | **Tanpa push, deploy, hapus data, atau hapus branch belum-tergabung** tanpa persetujuan owner. Probe/UAT data nyata hanya pada salinan dalam `transaction.atomic()` yang di-rollback | Hapus branch: hanya `git branch -d` |
| R8 | **Restart server** sesudah perubahan backend/bundle, **terkoordinasi**: pastikan tidak ada tes agen lain sedang berjalan di container | `docker restart ahsp_web`, tunggu `healthy` |
| R9 | **Bahasa export:** tanpa "terlambat/keterlambatan"; gunakan "Penambahan Waktu Kerja" | — |
| R10 | **Hasil historis bukan jaminan.** Setiap klaim status menyebut SHA & tanggal bukti; klaim tanpa bukti snapshot sekarang ditulis "tercatat historis" | §10 |

---

## 9. Tracker

Status: `TODO` / `WIP` / `REVIEW` / `DONE` / `BLOCKED` (alasan wajib) / `SKIP` (alasan wajib).

| ID | Tugas | Bergantung | Status | Pelaksana | Bukti (SHA / perintah / hasil) | Tanggal |
|---|---|---|---|---|---|---|
| A-1 | Cek visual owner | K-1 | DONE | Owner | Cetak XLSX dikecualikan sesuai arahan owner. PDF Rekap diperbaiki `230f975b`; 50 tes ekspor lulus. Belum cek visual DOCX atau Jadwal live. Detail: `docs/CEK_VISUAL_SAMPEL_EXPORT_20261001.md`. **Verifikasi Claude atas `230f975b`** (Rekap PDF proyek 217 di-render dari HEAD `6c87a6e6`): daftar isi ✅ benar (Rencana 3, Realisasi 5, Kurva S 7). **Judul Kurva S ❌ masih sendirian di hal. 7**, grafik di hal. 8. Akar: grafik halaman pertama setinggi `rows + 24 + 70` dengan `max_table_height = doc.height − 124`, jadi sisa ±30 pt, sedangkan judul (16 pt + `spaceAfter` 5 mm + `Spacer` 5 mm ≈ 47 pt) tidak muat dan `KeepTogether` terpaksa memisah. Tes `test_kurva_s_title_stays_with_first_chart_page` lulus hanya karena fixture-nya sedikit baris. Perlu: kurangi tinggi chunk pertama sebesar tinggi judul (ukur via `wrap`) + tes regresi dengan baris cukup banyak hingga grafik penuh. Registri `docs/DESIGN_REGISTRY_EXPORT.md` belum mencatat perubahan tampilan daftar isi (ikon & latar selang-seling dihapus, R4c). **Diselesaikan Claude `14ceacba`**: judul Kurva S kini sehalaman dengan grafik pada data 217 (potongan pertama dikurangi tinggi judul) + tes regresi 60 baris (gagal tanpa perbaikan) + registri R-46/R-47. **Sampel baru: `D:\PORTOFOLIO ADIT\sample_export_217_v4\`** (12 berkas, dari `14ceacba`); `09_Rekap.pdf` 8 hal.: daftar isi 3/5/7, judul+grafik hal. 7, sisa kurva + ringkasan hal. 8. Sisa untuk owner: cek visual DOCX (4), PDF v4, halaman Jadwal live. **Masukan owner (Word mingguan/bulanan beda gaya dari PDF) diselesaikan `ca881692`**: Word mengikuti PDF (R-48, uraian tetap utuh), persen PDF memakai koma (R-49); 1.045 tes / 0 gagal. **Sampel terbaru: `D:\PORTOFOLIO ADIT\sample_export_217_v5\`**. Temuan sampingan (belum dikerjakan): persen Word **harian** masih bertitik ("100.00%"); cover periode ke-2 dst. di PDF mingguan/bulanan masih menampilkan header/footer (cover pertama tidak) **Owner 2026-10-01: sampel `sample_export_217_v6` DISETUJUI (visual)** | 2026-10-01 |
| A-2 | Commit WIP W-1, W-2, W-3+W-4 | K-2 | DONE | Codex | W-1 `bf92d0c7`; W-2 `de212bd8`; W-3+W-4 `6c87a6e6` | 2026-10-01 |
| A-2v | Retest terarah WIP pra-commit (4 modul) | WIP tersedia | DONE | Codex | SHA host `5767608d`; PG `test_codex_20261001_wipverify_5043`; 58 tes, 0 gagal; empat berkas sumber hash cocok host/container; DB tes dihapus. `test_pg` memakai skema model, migrasi dinonaktifkan | 2026-10-01 |
| A-3 | Gerbang tes 5 app + Vitest + build | A-2 | DONE | Codex | HEAD `6c87a6e6`; backend 1.041 tes, 0 gagal, 40 skipped (PG `test_codex_20261001_postcommit_66c5`); Vitest 39 file, 432 lulus, 25 skipped; `npm run build` lulus, `dist/` tidak berubah. Peringatan chunk Jadwal >500 kB sudah ada sebelum perubahan ini. **Diverifikasi ulang Claude** pada HEAD `6c87a6e6` (DB `test_claude_20261001_head6c87_*`): backend 1.041 / 0 gagal / 40 skipped ✅. **Sesudah `14ceacba`** (Claude, DB `test_claude_20261001_kurvafix_*`): backend **1.043 / 0 gagal / 40 skipped** ✅; tidak ada perubahan JS (Vitest/build tidak perlu diulang). **Gerbang final Claude 2026-10-01 pada HEAD `2f64f956`** (WIP bersih kecuali 3 dok rencana): backend 5 app **1.047 / 0 gagal / 40 skipped** (`test_claude_20261001_gate_*`); Vitest **40 berkas, 458 lulus / 25 skipped**; `npm run build` lulus, `dist/` tidak berubah | 2026-10-01 |
| A-4 | `makemigrations --check` (migrasi aktif) | A-2 | DONE | Codex | `docker exec ahsp_web python manage.py makemigrations --check --dry-run` → No changes detected; settings `config.settings`, PostgreSQL, `MIGRATION_MODULES={}`. Diulang Claude pada `2f64f956`: No changes detected | 2026-10-01 |
| A-5 | Tag + merge `--ff-only` ke `main` | A-1, A-3, A-4, K-2 | REVIEW | Codex | Preflight ulang Claude pada HEAD `14ceacba`: `main` ancestor, `merge-tree` bersih, 325 commit di depan. Preflight pada HEAD `6c87a6e6`: `main` ancestor; `git merge-tree --write-tree main HEAD` bersih; 324 commit di depan. Belum merge; A-1 visual Word/Jadwal dan persetujuan K-2 untuk merge menunggu owner. **Preflight ulang pada `2f64f956`**: `main` ancestor, `merge-tree` bersih, 328 commit di depan. A-1/A-3/A-4 selesai; **tinggal izin owner K-2** | 2026-10-01 |
| A-6 | Hapus branch garis kerja tergabung (`-d`) | A-5 | TODO | | | |
| A-7 | Uji migrasi di salinan DB produksi (11 berisiko) | K-2 | TODO | Owner + pelaksana | | |
| A-8 | Review 4 branch lama | K-8 | TODO | | | |
| A-9 | Hapus kode mati (Jadwal v1, 2 JS Referensi, stats.html) | A-5 | TODO | | | |
| B-1 | `docs/STATUS_PROYEK.md` | A-5 | TODO | | | |
| B-2 | Perbarui checklist launch | B-1 | TODO | | | |
| B-3 | Label arsip dokumen usang | B-1 | TODO | | | |
| B-4 | Selaraskan dokumen detail | B-1 | TODO | | | |
| B-5 | Verifikasi ulang backlog | B-1 | TODO | | | |
| T-1 | Kontrak `DP.toast` di kepala `core/toast.js` | A-5 / K-9 | DONE | Claude | `2f64f956`; Vitest `toast_core.test.js` 26 lulus (15 gagal di kode lama); frontend 40 berkas/458 lulus; backend 5 app 1.047/0 gagal; build ulang dist | 2026-10-01 |
| T-2 | Inti toast: argumen, durasi, alias+metode, dedupe, batas jumlah, loading, handle | T-1 | DONE | Claude | `2f64f956`; Vitest `toast_core.test.js` 26 lulus (15 gagal di kode lama); frontend 40 berkas/458 lulus; backend 5 app 1.047/0 gagal; build ulang dist | 2026-10-01 |
| T-3a | 7 pemanggilan durasi objek (Jadwal) + teks error ekspor tanpa JSON mentah | T-2 | DONE | Claude | `2f64f956`; Vitest `toast_core.test.js` 26 lulus (15 gagal di kode lama); frontend 40 berkas/458 lulus; backend 5 app 1.047/0 gagal; build ulang dist | 2026-10-01 |
| T-3b | Satu sumber toast simpan | T-2 | DONE | Claude | `2f64f956`; Vitest `toast_core.test.js` 26 lulus (15 gagal di kode lama); frontend 40 berkas/458 lulus; backend 5 app 1.047/0 gagal; build ulang dist | 2026-10-01 |
| T-3c | Toast proses validasi bundle ditutup (+ unduh gambar Jadwal) | T-2 | DONE | Claude | `2f64f956`; Vitest `toast_core.test.js` 26 lulus (15 gagal di kode lama); frontend 40 berkas/458 lulus; backend 5 app 1.047/0 gagal; build ulang dist | 2026-10-01 |
| T-3d | `_hideLoading` menutup toast | T-2 | DONE | Claude | `2f64f956`; Vitest `toast_core.test.js` 26 lulus (15 gagal di kode lama); frontend 40 berkas/458 lulus; backend 5 app 1.047/0 gagal; build ulang dist | 2026-10-01 |
| T-3v | Cek visual owner T-3 (Jadwal: simpan/export/PNG; Template AHSP: validasi) | T-3a..d | DONE | Owner | Owner 2026-10-01: toast hilang sendiri, tidak ada toast menumpuk | 2026-10-01 |
| T-6 | Pesan server: level tag, urutan skrip, toast/modal, fallback (+ dekode escapejs) | T-3 | DONE | Claude | `2f64f956`; Vitest `toast_core.test.js` 26 lulus (15 gagal di kode lama); frontend 40 berkas/458 lulus; backend 5 app 1.047/0 gagal; build ulang dist | 2026-10-01 |
| T-6x | Temuan: HTML error import Referensi (`format_error_as_html`) menyisipkan data tanpa escape dan kini tampil sebagai teks escape mentah di modal; perbaikan aman perlu escape di server dulu | — | TODO | | | |
| T-6v | Cek visual owner T-6 | T-6 | DONE | Owner | Owner 2026-10-01: disetujui bersama T-3v | 2026-10-01 |
| T-4.0 | Inventaris jalur toast (klasifikasi) | T-2 | TODO | | | |
| T-4.x | Migrasi per halaman (9 lokasi, satu baris per commit saat dikerjakan) | T-4.0 | TODO | | | |
| T-4.g | Tes penjaga renderer independen | T-4.x | TODO | | | |
| T-5.0 | Tabel teks "sebelum → sesudah" | T-4.0 | TODO | | | |
| T-5.1 | Owner meninjau tabel | T-5.0 | TODO | Owner | | |
| T-5.2 | Terapkan teks + tes frasa terlarang | T-5.1 | TODO | | | |
| D-1 | Aturan R1–R10 disetujui | K-3 | TODO | Owner | | |
| D-2 | Arah berikutnya dipilih | K-4 | TODO | Owner | | |

---

## 10. Format bukti (wajib di kolom Bukti / laporan)

```
SHA: <git rev-parse HEAD di host>   (container tak punya git: cocokkan hash berkas berubah, host vs `docker exec ahsp_web sha256sum /app/<berkas>`, lihat R2)
WIP: bersih | <daftar berkas>
Perintah: <perintah lengkap>
Settings: config.settings.test_pg | <settings lain>   Migrasi aktif: ya/tidak
DB: <nama DB tes / salinan>
Hasil: <N> tes, <pass>/<skip>/<fail>   (Vitest: <N> file)
Tanggal: yyyy-mm-dd
```

---

## 11. Indeks dokumen terkait

| Dokumen | Isi |
|---|---|
| `docs/VERIFIKASI_RENCANA_PERAPIAN_PROYEK_20261001.md` | Verifikasi Codex atas v1 (V-01..V-09) |
| `docs/CEK_VISUAL_SAMPEL_EXPORT_20261001.md` | Pratinjau Codex A-1 atas PDF, hasil cetak workbook, dan batas render DOCX/Jadwal |
| `Review/R5_Detail_Project/44_Rencana_Merge_dan_Review_WIP_20260930.md` | Detail branch, migrasi, review WIP |
| `Review/R5_Detail_Project/41_Tambahan_Waktu_Kerja_Implementation_Tracker_20260929.md` | Fitur Tambahan Waktu Kerja + UAT |
| `Review/R5_Detail_Project/42_Export_Jadwal_Kondisi_Saat_Ini_20260930.md` | Peta export Jadwal + keputusan K-1..K-16 |
| `Review/R5_Detail_Project/43_Export_Penambahan_Waktu_Kerja_Plan_Tracker_20260930.md` | Tracker fase export + UAT |
| `docs/DESIGN_REGISTRY_EXPORT.md` | Keputusan tampilan export (R-1..R-45, A-1..A-8) |
| `docs/CHECKLIST_PROGRESS_KESIAPAN_LAUNCH_20260609.md` | Status launch (diperbarui di B-2) |
| `docs/RUNBOOK_DEPLOY_TLS_L5_L6.md` | Runbook deploy/TLS |
