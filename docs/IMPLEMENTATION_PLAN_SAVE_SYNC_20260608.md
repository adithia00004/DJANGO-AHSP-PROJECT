# Rencana Implementasi — Perbaikan Save/Sync & Kesiapan Produksi

Tanggal: 2026-06-08
Acuan temuan: `docs/AUDIT_SAVE_SYNC_PAGES_20260608.md` (S1–S7, P-1…P-5).
Status dokumen: **rencana + adendum pasca-implementasi parsial**. Sebagian fase teknis sudah dieksekusi di working tree; perubahan policy single-user/last-save-wins **belum dieksekusi** dan tetap menunggu konfirmasi eksplisit.
Revisi: v3 — amandemen A1–A5, temuan verifikasi implementasi, dan adendum single-user/single-role sudah dimasukkan; dokumen ini menjadi checklist final sebelum eksekusi lanjutan.

## Tujuan

Menutup akar masalah (divergensi "yang berjalan" vs "yang diedit") dan sisa lubang sistemik secara **seragam lintas-halaman**, dengan verifikasi pasti, agar aplikasi siap di-launch oleh user.

## Prinsip kerja

1. **Test-first & per-fase**: tiap fase punya kriteria verifikasi pasti; tidak lanjut ke fase berikut bila verifikasi gagal.
2. **Seragam, bukan tambal per-halaman**: solusi diterapkan di satu titik (decorator/util/context helper) agar halaman baru otomatis ikut aman.
3. **Reversible**: tiap fase punya rencana rollback.
4. **Verifikasi "yang berjalan"**: selain test otomatis, wajib cek runtime (browser/curl), bukan hanya `node --check`/baca source.
5. **Tidak menyentuh data**: tidak ada migrasi destruktif; perubahan bersifat penyajian, header, dan logika klien.

## Definisi istilah verifikasi

- **VT (Verifikasi Teknis)**: test otomatis / command yang harus lulus.
- **VR (Verifikasi Runtime)**: pengecekan manual di browser/staging.
- **DoD**: Definition of Done item.

---

## Progress Tracker

Update terakhir: 2026-06-08, berdasarkan pemeriksaan working tree lokal.

Legenda:
- **DONE**: sudah terimplementasi dan bukti source/test tersedia.
- **PARTIAL**: sebagian sudah selesai, masih ada sisa cleanup/verifikasi.
- **BLOCKED**: harus ditutup sebelum launch/deploy.
- **WAITING**: menunggu keputusan produk/konfirmasi sebelum eksekusi kode.
- **TODO**: belum dieksekusi atau belum diverifikasi.

### Ringkasan Status Eksekusi

| Kode | Item | Status | Bukti / catatan | Next action |
|---|---|---|---|---|
| 0 | Checkpoint working tree + baseline | PARTIAL | Baseline test pernah dicatat, tetapi repo masih sangat dirty dan dokumen plan/audit masih untracked | Buat checkpoint terkurasi sebelum lanjut perubahan besar |
| 1A | Middleware `no-store` halaman `detail_project` | DONE | `config.middleware.cache_control.DetailProjectNoStoreMiddleware` terdaftar di settings; test header ada | Tetap verifikasi runtime di staging |
| 1B | Bootstrap defensif | DONE (B1) | Strategy yang dipilih: andalkan `no-store`, tanpa fetch tambahan | Tidak perlu B2 kecuali ada bukti cache eksternal |
| 1C | Dockerfile collectstatic fail-fast | DONE | `collectstatic` build tidak lagi disembunyikan | Verifikasi saat clean build |
| 2A | Sync LED output + Jadwal | DONE source / TODO runtime | Include LED ada di Rekap RAB, Rincian RAB, Rekap Kebutuhan, Jadwal | Uji browser: ubah data hulu -> LED berubah -> refresh benar |
| 2B | Precision `watch` | DONE source / TODO runtime | Template `pekerjaan,harga`; Volume `pekerjaan` | Uji browser perubahan harga tidak memicu Volume, tapi memicu Template |
| 2C | Legacy sync indicator JS/partial | PARTIAL | `sync_indicator.js` dan partial legacy sudah dihapus; `sync_indicator.css` masih dipakai untuk `.dp-sync-led` | Split CSS LED ke `sync_led.css`/CSS utama, lalu hapus legacy CSS |
| 2D | Hygiene Jadwal (`le.log`, legacy `mode`) | DONE source / TODO runtime | Source guard sebelumnya bersih; legacy `mode` sudah disesuaikan | Uji Jadwal planned/actual save di browser |
| 3A | Policy single-user last-save-wins | WAITING | UI Template/Harga masih mengirim `client_updated_at` dan masih punya dialog konflik | Eksekusi hanya setelah konfirmasi produk |
| 3B | Util save read-after-write seragam | TODO / optional | Refactor lintas halaman berisiko regresi | Tunda sampai blocker launch bersih |
| 3C | Import Validate await save + `beforeunload` | DONE source / TODO runtime | Source sudah memakai `await persistCurrentEdits()` dan guard unload | Simulasi offline/500 dan reload dengan dirty edit |
| V1 | Cleanup build/manifest Jadwal | BLOCKED | Nested dist masih tracked di `detail_project/static/detail_project/detail_project/...`; hash manifest tidak tunggal | Hapus nested tracked dist, clean build, clean collectstatic, verifikasi satu hash |
| V2 | Migration drift `referensi/0024` | BLOCKED | `makemigrations referensi --check --dry-run` masih menghasilkan `0024_alter_ahspimportstaging_segment_type` | Generate migration, commit, apply, cek ulang |
| V3 | Split/hapus `sync_indicator.css` legacy | TODO | CSS terkonfirmasi masih memuat `.dp-sync-led` | Pindahkan style LED dulu, baru hapus legacy CSS |
| V4 | Triase 5 test merah baseline/domain | TODO | Masih perlu keputusan: update expectation atau `xfail` beralasan | Triage setelah V1/V2 bersih |
| D1 | Konfirmasi shared-login | WAITING | Menentukan apakah asumsi benar-benar 1 akun = 1 operator, bukan 1 akun dipakai 2 orang | Wajib dijawab sebelum 3A |
| D2 | Persetujuan 3A last-save-wins | WAITING | 3A menurunkan UI optimistic-lock Template/Harga yang sudah terbangun | Wajib disetujui sebelum mengubah UI save |
| 4 | Verifikasi staging/browser gate | TODO | Belum boleh dianggap selesai sebelum V1/V2 ditutup | Clean build -> collectstatic -> buka halaman target |

### Jalur Eksekusi Terdekat

1. **V1 - Build/manifest Jadwal**: tutup nested tracked dist dan buktikan satu hash end-to-end.
2. **V2 - Migration drift referensi**: generate `0024`, lalu pastikan `makemigrations --check --dry-run` bersih.
3. **V3 - CSS legacy**: pindahkan style LED aktif dari `sync_indicator.css`, lalu hapus legacy file/link.
4. **Fase 4 - Gate staging/browser**: jalankan setelah V1/V2/V3 minimal bersih.
5. **D1/D2 - Keputusan produk single-user**: jawab shared-login dan setujui 3A sebelum perubahan UI save.
6. **3A - Last-save-wins**: eksekusi setelah D1/D2 clear, bukan bagian blocker teknis awal.

### Jangan Dikerjakan Dulu Tanpa Konfirmasi

- Menghapus optimistic-lock backend. Backend token harus tetap dormant/reversible.
- Mengubah UI Template AHSP/Harga Items ke last-save-wins.
- Menghapus Sync LED dari halaman output. LED tetap dipakai sebagai indikator pasif.
- Menghapus `sync_indicator.css` sebelum style `.dp-sync-led` dipindahkan.

---

## Fase 0 — Pra-syarat (safety net) — wajib sebelum apa pun

Tujuan: pastikan ada baseline yang bisa di-rollback dan ukur kondisi awal.

Langkah:
1. **Checkpoint working tree terkurasi** (P-2) — **[A1]**. Seluruh perbaikan sejak 11 Feb masih uncommitted; tanpa ini tidak ada titik balik. **JANGAN `git add -A` tanpa review** — worktree sangat dirty & lintas-app.
   - Aksi: `git status` dulu → pisahkan perubahan tidak terkait bila perlu → commit checkpoint dengan scope jelas (mis. per-area: `detail_project`, `config/settings`, `docs`) → lalu `git tag pre-sync-hardening`.
   - Tujuan: titik balik penuh yang bersih, bukan satu commit raksasa campur aduk.
2. **Jalankan baseline test** dan simpan hasilnya:
   - `python manage.py check`
   - `python -m pytest detail_project/ -q`
   - `node --check` untuk semua JS detail_project yang akan disentuh.
3. Catat daftar test yang hijau sekarang (baseline) untuk pembanding pasca-perubahan.

DoD Fase 0: ada commit+tag; baseline test tercatat; `manage.py check` bersih.

Trade-off sisi-klien: tidak ada (proses repo saja).

---

## Fase 1 — Pengerasan aset & kesegaran tampilan (akar sisi-baca)

Menutup S2/S3 dan P-3. Risiko rendah, dampak besar, seragam semua halaman.

### 1A. `never_cache` seragam pada halaman detail_project (S2 / P-1)

Masalah: HTML dinamis tanpa `Cache-Control` → browser/bfcache bisa menyajikan halaman lama (bootstrap basi, atau referensi nama JS-hash lama 404 pasca-deploy).

Pendekatan (seragam, satu titik) — **[A2]**:
- **Direkomendasikan: middleware non-API.** Satu middleware ringan men-set `Cache-Control: no-store` untuk path `^/detail_project/` yang merender HTML (kecualikan `/api/`, export file, dan unduhan). Keunggulan: **halaman baru otomatis tertutup** (termasuk `export_test_view`) tanpa perlu mengingat menempel decorator.
- **Alternatif: decorator manual** `@never_cache` (`django.views.decorators.cache`) pada **semua** view halaman di `detail_project/views.py`: `list_pekerjaan_view`, `volume_pekerjaan_view`, `template_ahsp_view`, `harga_items_view`, `rincian_ahsp_view`, `rekap_rab_view`, `rincian_rab_view`, `rekap_kebutuhan_view`, `jadwal_pekerjaan_view`, **`export_test_view`**, `audit_trail_view`, `orphan_cleanup_view`. (Risiko: mudah terlewat untuk view baru.)

Acceptance **[A2]**: semua URL halaman `detail_project` yang merender HTML (bukan API/unduhan file) mengirim `Cache-Control` berisi `no-store`.

VT (pasti):
- Test baru `tests_page_cache_headers.py`: untuk **tiap** URL halaman (termasuk **`export_test_view`**), `client.get(url, HTTP_HOST='127.0.0.1')` → assert `response.headers['Cache-Control']` mengandung `no-store` (atau `no-cache, no-store, must-revalidate`). Jika pakai middleware: tambahkan asersi bahwa path API/unduhan **tidak** ikut diberi `no-store` (tidak ada efek samping).
- `python manage.py check` bersih.

VR (pasti):
- DevTools → Network → reload halaman: dokumen utama berstatus `200` (bukan `from disk cache`), header respons memuat `Cache-Control: no-store`.
- Uji back-button: tidak memulihkan tampilan lama dari bfcache.

DoD: semua halaman edit/output mengirim `no-store`; test header hijau.

Trade-off sisi-klien:
- **Menonaktifkan bfcache & cache HTML untuk halaman ini** → reload/back-button **selalu meminta ulang HTML ke server** (tidak ada restore instan dari memori). Konsekuensinya: navigasi back terasa sedikit lebih lambat (perlu satu round-trip), dan kehilangan efek "kembali instan". Untuk aplikasi data ber-login ini wajar dan justru diinginkan demi kebenaran data.

Rollback: hapus decorator/middleware (header kembali default).

### 1B. Bootstrap defensif / kepastian kesegaran (S3)

Catatan dependensi: bila 1A terpasang, HTML (berisi bootstrap) selalu segar → **S3 sebagian besar sudah teratasi**. 1B hanya pengaman tambahan untuk skenario cache di luar kendali (proxy korporat, ekstensi).

Pendekatan (pilih salah satu, default: B1):
- **B1 (default, murah):** andalkan 1A; tidak menambah request. Cukup beri komentar di kode bootstrap bahwa kesegaran dijamin oleh `no-store`.
- **B2 (paranoid):** setelah seed dari bootstrap, lakukan **validasi latar belakang** (1 fetch ringan) lalu rekonsiliasi bila berbeda.

VT: jika B2 — test source memastikan ada jalur revalidate; jika B1 — tidak ada perubahan kode (cukup catatan).

VR: muat halaman dengan koneksi normal → data sesuai DB.

Trade-off sisi-klien:
- **B1:** tidak ada tambahan beban; bergantung penuh pada 1A.
- **B2:** **menambah 1 request per buka halaman** dan berpotensi **kedip singkat** (nilai berubah dari bootstrap→hasil validasi) bila ternyata berbeda. Mengorbankan sebagian keunggulan kecepatan bootstrap.

Rekomendasi: **B1** (karena 1A sudah menutup lubang); naikkan ke B2 hanya bila lapangan menunjukkan cache di luar kendali.

### 1C. Dockerfile collectstatic fail-fast (P-3)

Pendekatan: hapus `2>/dev/null || true` pada baris `collectstatic` di `Dockerfile` agar build gagal bila aset rusak (entrypoint sudah fail-fast; ini pengaman ganda di build).

VT: build image lokal/staging → pastikan tahap collectstatic terlihat sukses (bukan tersembunyi).

VR: tidak ada (build-time).

Trade-off sisi-klien: tidak ada (proses build).

Rollback: kembalikan `|| true`.

---

## Fase 2 — Cakupan & ketepatan sinkronisasi antar-halaman

Menutup S4, S5, S6.

### 2A. Sync LED untuk halaman output (S4): Rekap RAB, Rincian RAB, **Rekap Kebutuhan**, Jadwal — **[A3]**

Pendekatan:
- Tambahkan `{% include "detail_project/_sync_led.html" with scope=... watch="all" change_status=change_status %}` pada template **keempat halaman**.
- Update view terkait di `detail_project/views.py` agar context memuat `change_status=_ensure_change_status(project)` + `**_get_sync_initial_timestamps(project)`.
- Untuk halaman read-only (Rekap RAB, Rincian RAB, **Rekap Kebutuhan**): handler refresh cukup `location.reload()` saat LED diklik (tidak perlu sinkron parsial).
- Untuk Jadwal: handler `dp:sync-refresh-request` yang **menolak refresh bila ada unsaved progress lokal** (guarded), konsisten dengan halaman lain. Ini bukan dialog konflik multi-tab; hanya pelindung agar input yang belum disimpan tidak hilang.

VT (pasti):
- Test: `client.get(url)` **keempat halaman** (Rekap RAB, Rincian RAB, Rekap Kebutuhan, Jadwal) → HTML memuat `class="dp-sync-led"` + atribut `data-initial-pekerjaan`, `data-initial-volume`, dan `data-initial-jadwal`. Nilai boleh kosong untuk project baru; untuk fixture yang punya data, assert nilainya sesuai timestamp DB.
- Test source: Jadwal app memiliki listener `dp:sync-refresh-request`.
- Test source: Jadwal app melakukan `dp:sync-led-ack` dengan `jadwal: true` setelah save sukses, agar LED tidak menandai save dari halaman sendiri sebagai stale.
- Catatan test timestamp: `data-initial-*` boleh kosong pada project baru. Test jangan memaksa nilai non-kosong kecuali fixture memang membuat data terkait; yang wajib adalah atribut hadir dan sesuai DB bila data ada.

VR (pasti):
- Buka Rekap, ubah volume di tab lain → dalam ≤30 dtk LED Rekap berubah "ada perubahan"; klik → halaman reload menampilkan angka baru.
- Jadwal: dengan progress lokal belum tersimpan, klik sinkron → muncul konfirmasi/guard, progress tidak hilang.

DoD: keempat halaman menampilkan LED akurat; Jadwal punya guarded refresh dan acknowledge LED setelah save sukses.

Trade-off sisi-klien:
- **Polling tambahan tiap 30 dtk** pada **4 halaman** (beban jaringan/CPU kecil; sama seperti halaman lain).
- Rekap RAB / Rincian RAB / Rekap Kebutuhan: aksi sinkron = **full reload** → **posisi scroll & state tampilan hilang** (wajar untuk halaman read-only).
- Jadwal: muncul **satu guard/konfirmasi lokal** saat sinkron bila ada perubahan belum tersimpan (mencegah kehilangan progress). Ini tetap relevan walau policy save memakai last-save-wins, karena guard ini bukan konflik antar-tab.

Rollback: hapus include + context tambahan.

### 2B. Ketepatan `watch` (S5)

Pendekatan:
- `template_ahsp.html`: ubah `watch="pekerjaan"` → `watch="pekerjaan,harga"` (Template menampilkan harga_satuan).
- `volume_pekerjaan.html`: ubah `watch="all"` → `watch="pekerjaan"` (Volume hanya bergantung list pekerjaan + parameter).

VT: test source/HTML memastikan atribut `data-watch` sesuai.

VR:
- Ubah harga → buka Template: LED menandai perubahan (sebelumnya diam).
- Ubah harga/ahsp → buka Volume: LED **tidak** lagi menyalakan alarm yang tak relevan.

Trade-off sisi-klien:
- Template: **lebih sering muncul indikator pasif "perlu sinkron"** ketika harga berubah (akurat, tapi tidak boleh memblok save atau berubah menjadi dialog konflik). Ini sadar-pilihan demi akurasi.
- Volume: **lebih sedikit alarm palsu** (perbaikan UX murni; tidak ada sisi negatif berarti). Risiko: bila ternyata Volume punya ketergantungan tak terduga pada harga/ahsp, perubahan itu tidak ter-flag — namun secara desain Volume tidak bergantung pada keduanya.

Rollback: kembalikan nilai `watch` semula.

### 2C. Hapus dead code indikator legacy (S6)

Pendekatan: hapus `<script ... sync_indicator.js>` dari `base_detail.html`, serta berkas `sync_indicator.js` dan partial `_sync_indicator.html` bila tidak dipakai di mana pun (verifikasi grep dulu). Untuk CSS, **jangan langsung hapus**: hasil verifikasi menunjukkan `sync_indicator.css` masih memuat style `.dp-sync-led`; pindahkan style LED aktif ke file bernama jelas (mis. `sync_led.css` atau CSS utama) lebih dulu, baru hapus sisa `sync_indicator.css`.

VT: grep memastikan tidak ada include `_sync_indicator.html` dan tidak ada referensi `sync_indicator.js` tersisa; grep memastikan `.dp-sync-led` tetap punya style aktif setelah migrasi CSS; `manage.py check` bersih; halaman tetap render.

VR: buka beberapa halaman detail → tidak ada error console; LED aktif tetap berfungsi.

Trade-off sisi-klien: **positif** — satu file JS lebih sedikit dimuat per halaman (sedikit lebih ringan). Risiko fungsional hanya muncul bila CSS LED ikut terhapus tanpa dipindahkan; karena itu CSS harus dipisah sebelum cleanup final.

Rollback: kembalikan script tag + berkas.

### 2D. Hygiene Jadwal production & legacy fallback — **[A4]** (audit 6.2 & 6.3)

Masalah:
- `kelola_tahapan_grid_modern.html` memuat `le.log(...)` (bukan `console.log`) → `ReferenceError: le is not defined` saat aset production dipakai.
- Legacy `save_handler_module.js` mengirim `mode: state.timeScale` (`weekly/daily/monthly`), sedangkan backend v2 menafsirkan `mode` sebagai progress mode (`planned/actual`). Jika rollback ke legacy, input *actual* berisiko tersimpan sebagai *planned*.

Pendekatan:
- Ganti `le.log(...)` → `console.log(...)` di `kelola_tahapan_grid_modern.html`.
- Update legacy `save_handler_module.js` agar mengirim progress mode eksplisit (`planned`/`actual`), ATAU hapus/tandai eksplisit jalur legacy bila sudah tidak dipakai (agar tidak ada rollback ke kontrak usang).

VT (pasti):
- Source guard: tidak ada lagi pola `le.log(` di template Jadwal.
- Source guard: legacy save handler tidak mengirim `mode: state.timeScale` ke endpoint v2; planned & actual mengirim `mode` yang benar.
- `node --check` pada berkas yang disentuh.

VR:
- Buka Jadwal → console bersih (tidak ada ReferenceError).
- Simpan progress *actual* → tersimpan sebagai *actual* (bukan *planned*).

Trade-off sisi-klien: **positif** — menghilangkan error console nyata; tidak ada sisi negatif. (Jika legacy dihapus: pastikan tidak ada tombol/flow yang masih memanggilnya.)

Rollback: kembalikan baris semula (tidak disarankan untuk `le.log`, itu memang bug).

---

## Adendum Arsitektur — Single-user SSOT Save Policy (menunggu konfirmasi)

Status: **proposal perubahan plan, belum otomatis dieksekusi ke kode**.

Keputusan produk yang sedang dipertimbangkan:
- Aplikasi diasumsikan **1 akun = 1 user/operator = 1 role aktif**.
- Multi-tab/multi-page edit bersamaan dianggap kasus kecil, bukan workflow utama.
- Database tetap menjadi **SSOT**.
- Browser/HTML tidak boleh menjadi sumber kebenaran stale.
- Redis/cache tetap boleh dipakai sebagai akselerator read model/perhitungan, tetapi harus bisa diinvalidate dan tidak menjadi sumber kebenaran edit.

Policy target bila disetujui:
- Load page/API selalu mengambil state terbaru dari DB/read model yang valid.
- Save dari UI memakai pola **last-save-wins**: payload terakhir yang berhasil diproses server menjadi state terbaru.
- UI normal **tidak mengirim optimistic-lock token** seperti `client_updated_at` untuk memblok save.
- UI normal **tidak menampilkan dialog konflik multi-tab**.
- Setelah save sukses, frontend wajib melakukan **read-after-write baseline update** dari response server atau fetch ulang terarah.
- Jika save gagal, input lokal tetap dirty dan tidak boleh ditandai sukses.
- Guard tetap dipakai untuk **unsaved local edits** saat user reload/close/pindah halaman, karena itu berbeda dari konflik multi-tab.

Fitur yang hilang bila policy ini diterapkan:
- Dialog "Konflik Data" / "Muat Ulang atau Timpa" pada save normal.
- Konfirmasi kedua "Ya, Timpa" untuk overwrite stale tab.
- Proteksi eksplisit terhadap skenario dua tab mengedit record yang sama lalu tab lama menyimpan terakhir.
- Test/source guard yang mengharuskan stale token menghasilkan `409` untuk workflow UI normal.

Trade-off:
- Positif: workflow lebih tegas, lebih sederhana, tidak cerewet, dan sesuai asumsi single-user.
- Positif: lebih sedikit cabang UI save dan lebih kecil risiko user bingung oleh konflik yang ia sebabkan sendiri di tab lain.
- Negatif: bila user benar-benar mengedit objek sama di dua tab, save terakhir akan menimpa save sebelumnya tanpa dialog.
- Mitigasi: `no-store`, refresh/fetch terbaru saat page dibuka, dirty-state jujur, dan read-after-write setelah save.

Konfirmasi yang dibutuhkan sebelum eksekusi kode:
- Apakah policy last-save-wins ini berlaku untuk **semua page input**, termasuk Harga Items dan Template AHSP?
- Apakah Sync LED tetap dipertahankan sebagai indikator pasif/sinkron manual, atau dikurangi agar tidak memberi warning lintas page?
- Apakah backend tetap boleh menyimpan dukungan `client_updated_at` untuk API/internal test, tetapi UI tidak mengirim token?
- **[BARU] Risiko shared-login**: apakah ada kemungkinan **satu akun dipakai 2 orang** (mis. satu firma satu login)? Bila ya, last-save-wins berarti dua orang bisa saling menimpa tanpa peringatan. Bila tidak (benar-benar 1 operator), policy ini aman.

### Pengaman rekayasa (keputusan engineering yang disarankan)

Tiga pengaman ini membuat penyederhanaan **aman dan reversible**:

1. **Backend token tetap DORMANT, jangan dicabut.** UI berhenti mengirim `client_updated_at` untuk save normal (last-save-wins). Endpoint tetap **mampu** memeriksa token bila dikirim, dan **mengabaikannya bila tidak ada** (perilaku default = terima save). Biaya nyaris nol; bila suatu hari multi-user diaktifkan, proteksi tinggal "dinyalakan" dari sisi UI tanpa menulis ulang backend. **Mencabut plumbing backend = mahal untuk dibalik → hindari.**
2. **"Single-user" ≠ "single-session".** Satu user tetap bisa membuka 2 tab / 2 perangkat / reload di tengah edit. Last-save-wins aman untuk semua kasus ini **kecuali** mengedit objek sama di 2 tab secara bergantian (trade-off yang diterima). Kasus reload-before-save bukan konflik dan tetap dijaga oleh `no-store` + dirty-state + `beforeunload`.
3. **Sync LED tetap ada tetapi pasif/non-blocking**, terutama untuk halaman **output** (Rekap/Rincian/Jadwal): nilainya "data hulu berubah, klik untuk segarkan" — **bukan** dialog konflik. Jangan dihapus untuk output pages; cukup pastikan tidak pernah memblok atau memunculkan dialog "Timpa".

Catatan penting: **dialog optimistic-lock untuk Template AHSP dan Harga Items SUDAH terbangun** di working tree saat ini. Eksekusi 3A berarti **menurunkan (downgrade) UI yang sudah ada** ke last-save-wins, bukan membangun dari nol — dan **memperbarui** (bukan menghapus) test yang saat ini mengunci perilaku `409`.

---

## Fase 3 — Keseragaman Read-After-Write (S7)

Menutup S7 dengan policy save yang konsisten. Setelah adendum single-user di atas, fokus utama Fase 3 bukan lagi memblok overwrite multi-tab, tetapi memastikan **save sukses benar-benar menjadi baseline UI terbaru** dan **save gagal tidak pernah tampak sukses**.

### 3A. Standardisasi UI save ke last-save-wins (downgrade dari optimistic-lock yang sudah terbangun)

Konteks: Template AHSP & Harga Items **sudah** memiliki UI dialog konflik + `client_updated_at`. 3A **menurunkannya**, bukan membangun baru.

Pendekatan:
- **UI**: hentikan pengiriman `client_updated_at` pada save normal; **hapus jalur dialog konflik** "Muat Ulang/Timpa" + konfirmasi kedua dari Template AHSP & Harga Items. Setelah response sukses, frontend memperbarui baseline dari response server (read-after-write) atau fetch ulang terarah.
- **Backend (DORMANT, jangan dicabut)**: endpoint tetap menerima `client_updated_at` **bila dikirim** dan **mengabaikannya bila tidak ada** (default = proses save). Cabang 409 tetap ada di kode tapi tidak terpicu oleh UI normal. Tujuan: reversibilitas bila multi-user diaktifkan.
- **Test**: **perbarui, jangan hapus** — test yang kini meng-assert `409` blocking untuk UI normal diubah menjadi: (a) UI normal tanpa token → `200`; (b) **bila** token usang dikirim eksplisit → backend masih mampu `409` (membuktikan plumbing dorman utuh).

VT (pasti):
- Source guard: save normal Template AHSP dan Harga Items **tidak** mengirim `client_updated_at` dan **tidak** punya dialog konflik "Muat Ulang/Timpa".
- Backend test: save normal (tanpa token) → `200`; save dengan `client_updated_at` usang (eksplisit) → tetap mampu `409` (dorman, untuk reversibilitas/API).
- Test save: response sukses memperbarui baseline; response gagal mempertahankan dirty state (honest failure).

VR: buka halaman → edit → save → reload; data yang tampil adalah data terakhir di DB. Jika dua tab menyimpan objek sama, tab yang save terakhir menjadi state DB **tanpa** dialog konflik.

Trade-off sisi-klien:
- Workflow lebih sederhana; **hilang false-positive konflik** akibat token project-wide saat membuka 2 halaman berbeda (mis. Volume + Harga) — ini perbaikan UX nyata.
- Risiko yang diterima: tab lama bisa menimpa tab baru bila user sengaja/tidak sengaja mengedit **objek yang sama** di dua tab.

### 3B. Standardisasi util save (read-after-write) — opsional, refactor

Pendekatan: ekstrak satu util klien "save → perbarui baseline dari respons server; jangan commit baris yang tak dikonfirmasi (gunakan kontrak `saved_job_ids`/HTTP 207)". Volume & Harga sudah pakai pola ini; jadikan satu fungsi bersama dan adopsi di Template/Rincian.

VT: test per-halaman bahwa baris gagal tetap dirty; baris sukses bersih dari respons server.

VR: matriks runtime (Fase 4).

Trade-off sisi-klien:
- Setelah save, **baseline diambil dari respons server** → bisa ada **render ulang/kedip kecil** bila server menormalkan nilai (mis. pembulatan) berbeda dari input. Ini justru benar (menampilkan yang tersimpan), tapi user melihat nilainya "dirapikan".
- Refactor menyentuh banyak halaman → **risiko regresi**; karenanya ditempatkan paling akhir dan dijaga test.

Catatan: 3B adalah peningkatan kualitas; bisa **ditunda pasca-launch** bila ingin meminimalkan risiko sebelum rilis (Volume/Harga sudah aman secara fungsional).

### 3C. Import Validate Report: save benar-benar menunggu server — **[A5]** (audit 7.1 & 7.2)

Scope: `referensi` (di luar `detail_project`). **Masuk jalur minimum launch BILA workflow Import Validate dipakai sebelum launch.**

Masalah:
- Tombol Simpan memanggil `persistCurrentEdits()` lalu **langsung** menandai UI "Perubahan tersimpan untuk export" tanpa menunggu respons server → **false success** bila fetch gagal/putus.
- Tidak ada `beforeunload` guard → edit bisa hilang saat reload/close tab sebelum tersimpan.

Pendekatan (`referensi/templates/referensi/import_validate_report.html`):
- Jadikan handler Simpan `await persistCurrentEdits()` **sebelum** menyatakan sukses.
- `persistCurrentEdits()` **melempar error** bila fetch gagal atau response bukan OK; saat gagal, tombol Simpan & counter dirty tetap aktif + tampil pesan error.
- Tambahkan `beforeunload` guard saat `changes.modified.length + changes.deleted.length > 0`.

VT (pasti):
- Source guard: handler Simpan memakai `await persistCurrentEdits()`.
- Source guard: ada `beforeunload` berbasis `changes.modified`/`changes.deleted`.

VR (pasti):
- Simulasi save gagal (offline/500) → UI **tidak** menampilkan "Perubahan tersimpan".
- Edit lalu reload/close tab → muncul guard unsaved changes.

Trade-off sisi-klien:
- Klik Simpan terasa **sedikit lebih lambat** (menunggu respons server) + butuh state loading/error.
- `beforeunload` memunculkan **prompt browser** saat keluar dengan edit belum tersimpan (bisa terasa mengganggu bagi yang sering navigasi) — pertukaran wajar demi mencegah edit hilang.

Rollback: kembalikan handler & hapus guard.

---

## Cleanup Pra-Launch — Temuan Verifikasi Implementasi (2026-06-08)

Ditemukan saat verifikasi hasil implementasi (`docs/evidence/SAVE_SYNC_IMPLEMENTATION_RESULT_20260608.md`). Ini **bukan** bagian save-policy, tetapi harus tuntas sebelum/saat gate Fase 4.

### V1. Build/manifest Jadwal — bersihkan artefak bersarang — **[LAUNCH BLOCKER]**
- Direktori build **bersarang ter-commit**: `detail_project/static/detail_project/detail_project/static/detail_project/dist/...` (7 file) — sisa bug outDir lama (yang outDir-nya sudah diperbaiki, tapi artefak lama belum dibersihkan).
- **3 hash berbeda**: source `C9Ct7gjz`, bersarang `DXFScqEi`, staticfiles `B5tOsYbZ`; **2 manifest Vite**.
- Risiko produksi: `{% vite_entry %}` menghasilkan path hashed seperti `detail_project/dist/assets/js/jadwal-kegiatan-<hash>.js`, lalu `{% static %}` akan divalidasi oleh `ManifestStaticFilesStorage`. Bila artefak final tidak ada di `staticfiles` setelah `collectstatic`, halaman Jadwal bisa 500 dengan **"Missing manifest entry"**.
- Aksi: hapus direktori bersarang ter-commit (`git rm -r`); pastikan **satu** Vite manifest yang aktif di `detail_project/static/detail_project/dist/.vite/manifest.json`; clean `npm run build` → clean `collectstatic` → verifikasi **satu hash end-to-end**. `staticfiles/` adalah artefak lokal/ignored dan harus diregenerasi, bukan dikomit.
- VT: `git ls-files` path bersarang = 0; hanya satu manifest Jadwal di source tree; `staticfiles` hasil clean collectstatic memuat hash yang sama dengan manifest aktif; staging buka Jadwal tanpa 500 (di Fase 4).

### V2. Migration drift `referensi/0024` — **[LAUNCH BLOCKER]**
- `python manage.py makemigrations referensi --check --dry-run` melaporkan `0024_alter_ahspimportstaging_segment_type` pending.
- Aksi: generate + commit + apply migration sebelum deploy.
- VT: `makemigrations --check --dry-run` bersih untuk **semua** app.

### V3. S6 belum tuntas (minor)
- `base_detail.html` masih memuat `sync_indicator.css` dan file CSS-nya masih ada (JS sudah dihapus).
- Catatan penting: file CSS ini terkonfirmasi masih memuat style LED aktif (`.dp-sync-led`). Jangan hapus link + file secara langsung. Aksi yang benar: pindahkan style LED ke `sync_led.css`/CSS utama, update link, lalu hapus legacy `sync_indicator.css`.

### V4. 5 test merah baseline — triase (dianjurkan)
- 3 param decimal/negative + 2 Template formula (akibat policy SSOT auto-code). **Perbarui** ekspektasi ke perilaku yang diinginkan, atau tandai `xfail` beralasan, agar "gate hijau" bermakna.

---

## Fase 4 — Verifikasi akhir di staging (gate launch)

1. Build image staging dengan aset produksi (manifest), jalankan clean `npm run build` dan `docker-entrypoint.sh`/`collectstatic --clear`.
2. Jalankan **Matriks Re-Verifikasi Runtime** (lihat audit, bagian "Matriks Re-Verifikasi Runtime") di staging untuk semua halaman.
3. Cek header `no-store` aktif di staging (curl/DevTools).
4. Cek aset tersaji adalah versi terbaru (nama hashed, memuat penanda perbaikan), dan khusus Jadwal pastikan hash manifest aktif = hash file di staticfiles = hash yang dimuat browser.

DoD launch: semua baris matriks runtime ✅, header benar, aset terbaru tersaji.

---

## Urutan, dependensi, dan estimasi risiko

| Fase | Item | Tergantung | Risiko klien | Blocker launch? |
|---|---|---|---|---|
| 0 | Commit/tag + baseline | — | nihil | ya (safety) |
| 1A | never_cache | 0 | rendah (back-button lebih lambat) | **ya (P-1)** |
| 1B | bootstrap defensif | 1A | nihil (B1) | tidak |
| 1C | Dockerfile fail-fast | 0 | nihil | dianjurkan |
| 2A | LED output + Jadwal | 0 | rendah (polling, reload) | tidak (UX) |
| 2B | watch precision | 0 | rendah (Template lebih cerewet) | tidak |
| 2C | hapus dead code | 0 | positif | tidak |
| 2D | hygiene Jadwal (`le.log`, legacy `mode`) **[A4]** | 0 | positif | dianjurkan (murah, bug nyata) |
| 3A | last-save-wins UI save policy | 0 | rendah-sedang (overwrite multi-tab diterima) | perlu konfirmasi produk |
| 3B | util save seragam | 3A | sedang (kedip; risiko regresi) | tidak (boleh pasca-launch) |
| 3C | Import Validate save UX **[A5]** | 0 | sedang (save lebih lambat; prompt unload) | **ya, BILA Import Validate dipakai sebelum launch** |
| V1 | cleanup build/manifest Jadwal | 0 | nihil | **ya (blocker)** |
| V2 | migration drift referensi/0024 | 0 | nihil | **ya (blocker)** |
| V3 | split/hapus legacy `sync_indicator.css` sisa | 0 | positif bila style LED dipindahkan dulu | tidak (minor) |
| V4 | triase 5 test merah baseline | 0 | nihil | tidak (kualitas gate) |
| 4 | verifikasi staging | semua | — | **ya (gate)** |

Jalur minimum siap-launch: **Fase 0 → 1A → 1C → V1 → V2 → 4** (+ P-2). **V1 (build/manifest Jadwal)** dan **V2 (migration drift)** adalah **launch blocker** dari hasil verifikasi. **[A5]** Bila workflow **Import Validate** dipakai sebelum launch, **3C masuk jalur minimum**. **2D** dianjurkan lebih awal karena murah & menutup bug nyata. **2A** (LED output) disesuaikan dengan adendum: indikator pasif/silent, **bukan** dialog konflik multi-tab. **3A** (last-save-wins) perlu konfirmasi produk sebelum eksekusi karena mengubah perilaku konflik save; bila disetujui, ia **menurunkan** UI optimistic-lock yang sudah terbangun (lihat Pengaman rekayasa di adendum).

---

## Strategi test menyeluruh (dijalankan tiap akhir fase)

1. `python manage.py check` → 0 issues.
2. `python -m pytest detail_project/ -q` → semua hijau (bandingkan dengan baseline Fase 0).
3. `node --check` untuk setiap JS yang disentuh.
4. **Verifikasi "yang berjalan"**: `curl` aset → cek penanda versi; DevTools Network untuk header & request save.
5. Matriks runtime (Fase 4) di staging.

### Guard test/otomatis wajib (per item) — **[A1–A5]**

1. `tests_page_cache_headers.py`: setiap halaman HTML `detail_project` (termasuk **`export_test_view`**) mengirim `Cache-Control: no-store`; bila middleware → buktikan path API/unduhan **tidak** terdampak. (Fase 1A)
2. Test template/source untuk **empat** Sync LED output: Rekap RAB, Rincian RAB, **Rekap Kebutuhan**, Jadwal (LED ada + `data-initial-*` hadir; nilai sesuai DB bila fixture punya data). (Fase 2A)
3. Source guard: **tidak ada** pola `le.log(` di template Jadwal. (Fase 2D)
4. Source guard: legacy jadwal **tidak** mengirim `mode: state.timeScale` ke backend v2; planned/actual mengirim `mode` benar. (Fase 2D)
5. Source guard Import Validate: handler Simpan memakai `await persistCurrentEdits()`. (Fase 3C)
6. Source guard Import Validate: ada `beforeunload` berdasarkan `changes.modified`/`changes.deleted`. (Fase 3C)
7. Source guard last-save-wins (Fase 3A, bila disetujui):
   - UI save normal **tidak** mengirim `client_updated_at` dan **tidak** punya dialog konflik multi-tab (Template AHSP & Harga Items).
   - Backend test dorman: save tanpa token → `200`; save dengan token usang eksplisit → masih `409` (plumbing reversibel utuh).
   - Test `409`-blocking lama **di-update** ke kontrak baru (bukan dihapus); tidak ada test merah baru pada gate Fase 0.

## Rollback umum
Setiap fase di-commit terpisah dengan pesan jelas; rollback = `git revert <commit fase>`. Tag `pre-sync-hardening` (Fase 0) adalah titik balik penuh.

## Ringkasan trade-off sisi-klien (yang diminta)

| Item | Dampak ke proses sisi-klien |
|---|---|
| never_cache (1A) | back-button/reload selalu round-trip (tak ada restore instan dari bfcache) |
| bootstrap B2 (jika dipilih) | +1 request per buka halaman; kemungkinan kedip stale→fresh |
| LED output (2A) | polling 30 dtk pada **4 halaman**; aksi sinkron Rekap RAB/Rincian RAB/Rekap Kebutuhan = full reload (scroll hilang); Jadwal hanya guard untuk unsaved local edit |
| watch Template (2B) | indikator pasif "perlu sinkron" lebih sering muncul saat harga berubah, tanpa memblok save |
| watch Volume (2B) | berkurangnya alarm palsu (positif) |
| hapus sync_indicator (2C) | satu file JS lebih sedikit; CSS legacy boleh dihapus hanya setelah style LED dipindahkan |
| hygiene Jadwal (2D) | **positif** — hilang error console; tidak ada sisi negatif |
| last-save-wins UI save (3A) | tidak ada dialog konflik; save terakhir menang bila objek sama diedit di dua tab |
| util save seragam (3B) | kemungkinan kedip kecil saat baseline diambil dari respons server |
| Import Validate save UX (3C) | klik Simpan menunggu server (sedikit lebih lambat) + prompt `beforeunload` saat keluar dengan edit belum disimpan |

Trade-off utama setelah adendum: sistem menjadi lebih tegas dan sederhana, tetapi sengaja melepas proteksi konflik multi-tab sebagai default. Kebenaran tampilan tetap dijaga lewat `no-store`, load/fetch terbaru, dirty-state jujur, dan read-after-write setelah save.
