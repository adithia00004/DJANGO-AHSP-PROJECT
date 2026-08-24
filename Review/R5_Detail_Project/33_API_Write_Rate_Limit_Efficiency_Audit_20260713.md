# 33 — Audit Efisiensi & Kalibrasi Rate Limit Endpoint Tulis

**Tanggal:** 2026-07-13
**Status:** LAPORAN TEMUAN — murni investigasi, TANPA perubahan kode. Menunggu keputusan
owner untuk scope implementasi (lihat §8).
**Pemicu:** Owner melaporkan warning "coba lagi dalam 60 detik" berulang saat menginput
data, pada proyek yang tergolong kecil.
**Prinsip evaluasi (arahan owner):** aplikasi ini **1 akun = 1 project = 1 user** —
tidak ada kontensi multi-tenant pada resource yang sama. Semua analisis di bawah
mengabaikan skenario "banyak user berebut 1 endpoint" dan fokus ke: apakah pola
pemakaian **solo yang wajar** bisa menabrak limit, dan apakah jumlah request yang
dikirim untuk pekerjaan yang sama sudah seefisien mungkin.

---

## 1. Ringkasan Eksekutif

Rate limiter (`detail_project/api_helpers.py:84-206`) memakai cache key
**`rate_limit:{user_id}:{endpoint}`** — artinya limiter ini murni membatasi **1 user
terhadap dirinya sendiri per endpoint**, bukan alat keadilan antar-user. Fungsinya
adalah pengaman terhadap bug klien/script/klik-panik yang membanjiri database dengan
write — **bukan** throttle yang perlu ketat karena "banyak orang akan memakainya
bersamaan" (itu tidak pernah jadi skenario di app dengan model 1-akun-1-project ini).

**Temuan utama:**

1. **Inkonsistensi kalibrasi, bukan kebijakan yang disengaja.** 8 endpoint (family
   Volume Pekerjaan + assign-weekly Jadwal) sudah dinaikkan ke **240 req/60s** oleh
   perbaikan sebelumnya (tag "WP-P3b"). 20 endpoint lain — termasuk **Template AHSP
   save**, yang pola pemakaiannya identik — masih di **20 req/60s**. Investigasi ke
   riwayat (doc 18/19) mengonfirmasi: angka 20/60s bukan hasil hitungan pola pakai,
   melainkan efek blanket-fix "endpoint ini sebelumnya TANPA proteksi sama sekali,
   pasang kategori generik yang sudah ada" (commit `9f8a5673` HI-10, `f4bf7960` TA-07).
   Artinya keluhan owner bukan karena keamanan sengaja diperketat, tapi karena
   kalibrasi belum pernah benar-benar dilakukan.
2. **Root cause keluhan awal, terverifikasi presisi:** Template AHSP (`selectJob()`,
   `template_ahsp.js:1086-1130`) memicu 1 POST otomatis setiap pindah pekerjaan saat
   ada perubahan belum tersimpan. Endpoint `api_save_detail_ahsp_for_pekerjaan`
   berada di kategori 20/60s. Mengisi data untuk 25-30 pekerjaan secara berpindah
   cepat = 15-25 POST/menit — persis di ambang limit.
3. **Pemborosan request nyata yang berdiri sendiri (di luar soal angka limit):**
   List Pekerjaan mengirim **2 POST per klik Simpan** (bukan 1); Rekap RAB memakai
   debounce 250ms per-keystroke yang tidak konsisten dengan filosofi cadence di
   halaman lain.
4. **Yang sudah benar dan jadi acuan:** Harga Items, Volume Pekerjaan, dan modul
   Jadwal Pekerjaan yang aktif (bukan legacy) sudah membatch semua perubahan jadi
   1 request — bukti bahwa arsitektur "1 aksi user = 1 request" itu achievable dan
   sudah diterapkan konsisten di beberapa halaman.

---

## 2. Metodologi

- Inventaris menyeluruh semua `@rate_limit(...)` di `detail_project/views_api.py` dan
  `detail_project/views_api_tahapan_v2.py` (30 endpoint), disilangkan dengan
  `detail_project/urls.py` untuk pemetaan URL.
- Pembacaan menyeluruh setiap `fetch()` yang mengirim POST/PUT/PATCH/DELETE di
  seluruh JS halaman `detail_project` (`volume_pekerjaan.js`, `list_pekerjaan.js`,
  `harga_items.js`, `template_ahsp.js`, `rincian_ahsp.js`, `rekap_rab.js`,
  `rekap_kebutuhan.js`, serta seluruh `src/modules/**` termasuk Jadwal/Gantt/Kurva-S),
  untuk menentukan trigger (klik eksplisit vs auto vs per-baris vs debounce) dan
  status batching-nya.
- Verifikasi mekanisme limiter (`api_helpers.py:141-206`) baris-per-baris.
- Ditelusuri balik ke riwayat audit (doc 18 Template AHSP, doc 19 Harga Items) untuk
  memastikan angka 20/60s memang belum pernah dikalibrasi ke pola pakai nyata —
  bukan keputusan produk yang disengaja yang sekarang mau dibatalkan begitu saja.
- **Di luar scope:** rate limiting di app `referensi` (import) memakai mekanisme
  terpisah (`IMPORT_RATE_LIMIT`/middleware) — sudah diaudit tuntas di R6 (2026-06-24),
  tidak disentuh di sini.

---

## 3. Mekanisme Limiter (agar kalibrasi berikutnya presisi)

```python
# detail_project/api_helpers.py:141-198 (ringkas)
current_count = cache.get(cache_key, 0)
if current_count >= max_requests:
    return 429  # TIDAK menyentuh cache — TTL lama terus berjalan
new_count = current_count + 1
cache.set(cache_key, new_count, window)  # TTL direset ke `window` PENUH tiap hit sukses
```

Implikasi yang perlu dipahami sebelum mengubah angka:

- Ini **bukan** fixed calendar window (mis. "per menit jam wall-clock") — TTL selalu
  di-refresh penuh (`window` detik) pada setiap request yang **berhasil**. Begitu
  limit tercapai, request berikutnya diblokir 429 **tanpa** menyentuh cache, sehingga
  counter meluruh alami tepat `window` detik sejak request sukses terakhir.
- Praktis: begitu Anda berhenti mengirim request ke endpoint itu selama `window`
  detik, limit otomatis pulih ke 0 — bukan macet permanen, tapi tetap terasa
  mengganggu di tengah sesi kerja aktif.
- Cache backend: **Redis** (baik di Docker lokal maupun `docker-compose.prod.yml`,
  keduanya `CACHE_BACKEND=redis` — sudah diverifikasi sebelum laporan ini ditulis).
  Counter konsisten lintas proses/worker; bukan artefak lokal.

---

## 4. Peta Lengkap Endpoint Tulis Ber-Rate-Limit (30 endpoint)

### 4.1 Kategori `bulk` — 5 req / 300 detik (2 endpoint)

| Endpoint | Baris | Halaman | Alasan kategori ini masuk akal |
|---|---|---|---|
| `api_deep_copy_project` | views_api.py:6568 | Dashboard | Operasi berat (copy seluruh project) — 5/5menit sudah sesuai kelangkaannya |
| `api_batch_copy_project` | views_api.py:6847 | Dashboard | Sama |

### 4.2 Kategori `write` — 20 req / 60 detik (20 endpoint)

**Aksi LANGKA (jarang diklik dalam 1 sesi) — limit 20/60s sudah lebih dari cukup, TIDAK direkomendasikan berubah:**

| Endpoint | Baris | Halaman |
|---|---|---|
| `api_list_pekerjaan_destructive_impact` | views_api.py:1724 | List Pekerjaan (preview) |
| `api_create_template` / `api_delete_template` / `api_import_template` / `api_import_template_from_file` | views_api.py:9709/9796/10255/10326 | List Pekerjaan (template library) |
| `api_reset_detail_ahsp_to_ref` | views_api.py:3044 | Template AHSP |
| `api_sync_reference` | views_api.py:3165 | Template AHSP |
| `api_rebuild_missing_expansion` | views_api.py:3276 | Template AHSP |
| `api_save_detail_ahsp_gabungan` | views_api.py:4706 | Rincian AHSP (legacy combined-save) |
| `api_cleanup_orphaned_harga_items` | views_api.py:5074 | Harga Items |
| `api_ack_source_change_flags` | views_api.py:5266 | Harga Items ↔ Rincian AHSP |
| `api_reset_all_overrides` | views_api.py:5705 | Rekap RAB pricing |
| `api_update_week_boundaries` | views_api_tahapan_v2.py:445 | Jadwal (setting) |
| `api_regenerate_tahapan_v2` | views_api_tahapan_v2.py:842 | Jadwal (ganti time-scale) |
| `api_reset_progress` | views_api_tahapan_v2.py:1011 | Jadwal |

**Aksi BERULANG dalam 1 sesi data-entry — kandidat kuat untuk dikalibrasi ulang (§6):**

| Endpoint | Baris | Halaman | Kenapa berulang |
|---|---|---|---|
| **`api_save_detail_ahsp_for_pekerjaan`** | views_api.py:2320 | **Template AHSP** | 1 POST per pekerjaan, auto-trigger tiap pindah job dengan perubahan (§5.1) — **root cause keluhan** |
| `api_upsert_list_pekerjaan` | views_api.py:809 | List Pekerjaan | 1 klik = 2 POST (§5.2) — masalah efisiensi, bukan hanya limit |
| `api_save_harga_items` | views_api.py:3382 | Harga Items | Sudah batched baik (1 klik = 1 POST semua baris) — limit 20/60s praktis tak pernah tersentuh, tapi tetap tercatat sebagai family yang sama |
| `api_save_conversion_profile` | views_api.py:3649 | Harga Items | Legacy/deprecated, jarang dipakai |
| `api_pekerjaan_pricing` | views_api.py:5570 | Rekap RAB / Rincian AHSP | Modal override BUK per-pekerjaan, 1 POST per pekerjaan (§5.4) |

### 4.3 Kategori custom `240 req / 60 detik` — 8 endpoint (preseden yang sudah tervalidasi)

| Endpoint | Baris | Halaman |
|---|---|---|
| `api_save_volume_pekerjaan` | views_api.py:1893 | Volume Pekerjaan |
| `api_project_parameters` / `_sync` | views_api.py:3950/4284 | Volume Pekerjaan |
| `api_project_computed_parameters` / `_sync` | views_api.py:4461/4553 | Volume Pekerjaan |
| `api_volume_formula_state` (+alias) | views_api.py:5861 | Volume Pekerjaan |
| `api_project_pricing` | views_api.py:3800 | Rekap RAB (panel setting, sering dipoll UI) |
| `api_assign_pekerjaan_weekly` | views_api_tahapan_v2.py:49 | Jadwal Pekerjaan |

### 4.4 Kategori `read` (100/60s) dan `export` (10/60s) — **0 endpoint terpakai**

Kategori ini didefinisikan di `RATE_LIMIT_CATEGORIES` tapi **tidak pernah dipasang**
di satu pun view. Semua endpoint baca (list/search/get) dan seluruh endpoint
`export_*` (PDF/Word/XLSX/CSV — termasuk yang baru dikerjakan di doc 32) berjalan
**tanpa rate limit sama sekali**, hanya `@login_required`. Ini di luar topik keluhan
owner (bukan penyebab warning 429), tapi dicatat sebagai observasi housekeeping —
lihat §7.

---

## 5. Analisis Akar Masalah per Halaman (bukti file:baris)

### 5.1 Template AHSP — ROOT CAUSE keluhan owner

`selectJob()` (`template_ahsp.js:1086-1130`): setiap pindah pekerjaan sambil ada
`dirty=true` → `confirm()` → `doSave(activeJobId)` (`:1893-2092`) → 1 POST ke
`api_save_detail_ahsp_for_pekerjaan`. Payload **sudah** membawa semua baris 1
pekerjaan sekaligus (bukan per-baris) — masalahnya murni **1 request per pekerjaan
yang dikunjungi**, dan endpoint ini masih di kategori 20/60s yang sama dengan aksi
langka seperti "hapus template".

Estimasi realistis: mengisi 25-30 pekerjaan berpindah cepat = **15-25 POST/menit** —
tepat di ambang batas. Ini menjelaskan kenapa proyek "kecil" pun bisa kena, karena
pemicunya adalah **jumlah pekerjaan yang dikunjungi**, bukan ukuran project.

Sudah diverifikasi bukan masalah: cek "freshness" via GET sebelum save (pola boros
klasik) **sudah dinonaktifkan** di kode (`if (false && ...)`, `template_ahsp.js:1949`,
dengan komentar eksplisit "Server already sends fresh data in save response").

### 5.2 List Pekerjaan — pemborosan 2× request per Save

Setiap klik Simpan memicu **dua** POST berurutan:
1. `api_list_pekerjaan_destructive_impact` (`list_pekerjaan.js:2168`) — preview
   read-only dampak destruktif.
2. `api_upsert_list_pekerjaan` (`list_pekerjaan.js:2175`) — commit sesungguhnya.

10 kali klik Simpan = 20 request, bukan 10. Ini murni **inefisiensi struktural**,
berlaku independen dari angka limit berapa pun dipasang.

### 5.3 Rekap RAB — debounce keystroke-level tidak konsisten

Input PPN/rounding-base memakai debounce **250ms** (`rekap_rab.js:841-844`) yang
memicu POST ke `api_project_pricing` tiap kali user berhenti mengetik sejenak.
Bandingkan dengan filosofi "commit on blur" yang sudah ada di baris 855-857 (tidak
dipakai untuk field ini) dan cadence 5-menit yang konsisten dipakai Volume
Pekerjaan/Jadwal modern. Field ini kebetulan berada di tier 240/60s (custom), jadi
TIDAK memicu 429 — tapi tetap tercatat karena polanya secara desain tidak konsisten
dan berpotensi menghasilkan request beruntun tanpa perlu.

### 5.4 Rincian AHSP — override BUK per-pekerjaan via modal

`saveOverride` (`rincian_ahsp.js:617`) mengirim 1 POST per pekerjaan ke
`api_pekerjaan_pricing` setiap kali modal Apply/Clear diklik. Belum ada mekanisme
"set override untuk banyak pekerjaan sekaligus". Kategori 20/60s — berpotensi jadi
hot path kalau alur kerja "atur BUK untuk banyak pekerjaan satu-satu" memang umum
dipakai, meski frekuensi switch di sini biasanya lebih lambat daripada Template AHSP
(harus buka modal per pekerjaan, bukan sekadar klik item di list).

### 5.5 Yang SUDAH BENAR (acuan pola ideal, jangan diubah)

| Halaman | Pola | Bukti |
|---|---|---|
| Harga Items | 1 klik Simpan = 1 POST, semua baris dirty + semua conversion profile dalam 1 payload | `harga_items.js:729` |
| Volume Pekerjaan | Autosave 5 menit (`AUTOSAVE_MS`) + semua item dirty dalam 1 `{items:[...]}`; formula-state & parameter sync memakai cadence sama | `volume_pekerjaan.js:54-55, 6500-6517, 122, 6907` |
| Jadwal Pekerjaan (modul modern `jadwal_kegiatan_app.js`, **aktif di produksi**) | 1 klik Save = 1 POST membawa SEMUA sel yang diubah lintas SEMUA pekerjaan (`_buildPayload()` di `save-handler.js`) | Dikonfirmasi via komentar migrasi eksplisit di template — modul legacy dengan loop per-baris **tidak dimuat** |

### 5.6 Temuan sampingan (bukan penyebab, tapi dicatat untuk kebersihan)

- `detail_project/static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/save_handler_module.js`:
  loop `for...of` mengirim 1 POST per pekerjaan ke endpoint yang **sama**
  (`assign-weekly`) yang sudah dibatch dengan benar di modul modern. **Dead code** —
  dikonfirmasi tidak dimuat (`kelola_tahapan_grid_modern.html` eksplisit menyebut
  "This template ONLY loads modern Vite-based modules"). Tidak berdampak ke user
  sekarang, tapi berisiko kalau suatu saat ter-rollback tanpa fix batching-nya ikut.
- `shared/performance-monitor.js:432`: fungsi report metric via `keepalive` fetch,
  tidak pernah benar-benar dipanggil (`initPerformanceMonitor()` tak pernah
  diaktifkan) — dead code, nol dampak.

---

## 6. Mengapa Angka 20/60s Bukan Keputusan yang Disengaja (verifikasi ke riwayat)

Ditelusuri ke asal-usulnya di doc 18 dan 19:

> **HI-10** (doc 19, baris 301-305): *"Setiap save mengirim semua item dan
> melakukan loop query/update. **Tidak terlihat payload count limit atau rate limit
> pada endpoint ini.**"* → ditutup commit `9f8a5673`, "HI-10 governance ditutup
> REPO-WIDE (~11 endpoint write)".
>
> **TA-07** (doc 18, baris 413-423): *"Endpoint write Template AHSP **tidak
> memakai** `@rate_limit(category='write')`."* → ditutup commit `f4bf7960`,
> menambahkan `@rate_limit(category='write')` ke 4 endpoint sekaligus.

Kedua audit sebelumnya benar mengidentifikasi masalah **"endpoint ini benar-benar
TANPA proteksi apa pun"** — itu perbaikan yang tepat dan penting (celah sungguhan).
Tapi solusinya adalah memasang **kategori generik yang sudah ada**, bukan menghitung
ulang angka berdasarkan pola pemakaian tiap endpoint. Wajar — saat itu prioritasnya
menutup celah "0 proteksi", bukan mengkalibrasi angka. **Laporan ini melanjutkan
pekerjaan yang belum sempat dilakukan: kalibrasi**, bukan membatalkan keputusan
keamanan sebelumnya.

Bukti konsistensi niat: Volume Pekerjaan (tag "WP-P3b") justru **sudah** menjalani
kalibrasi eksplisit — dinaikkan ke 240/60s karena disadari polanya "banyak item
disimpan berulang dalam 1 sesi". Template AHSP punya pola identik tapi belum
kebagian kalibrasi yang sama — inkonsistensi antar-commit, bukan risk-based decision.

---

## 7. Observasi Housekeeping (di luar akar masalah, opsional)

- Kategori `read` (100/60s) dan `export` (10/60s) tidak pernah dipakai — semua
  endpoint baca & seluruh export PDF/Word/XLSX/CSV berjalan tanpa rate limit sama
  sekali. Ini bukan penyebab keluhan (GET tidak memicu warning yang dilaporkan), tapi
  merupakan celah yang simetris dengan yang ditutup HI-10/TA-07 dulu (endpoint tanpa
  proteksi). Di luar scope laporan ini (fokus: efisiensi & kalibrasi endpoint tulis
  yang SUDAH match dengan keluhan), dicatat sebagai kandidat audit terpisah bila
  diperlukan.
- Modul Jadwal legacy (`kelola_tahapan/save_handler_module.js`) dan
  `performance-monitor.js` adalah dead code — kandidat pembersihan berisiko-rendah.

---

## 8. Ringkasan Opsi untuk Implementation Plan (BELUM dieksekusi)

Tabel ini murni ringkasan pilihan yang tersedia berdasarkan temuan di atas — bukan
keputusan final. Owner memutuskan scope & urutan sebelum implementation plan disusun.

| # | Area | Sifat perubahan | Efek | Risiko |
|---|---|---|---|---|
| A | List Pekerjaan: satukan destructive-check ke dalam alur upsert (return "perlu konfirmasi" di percobaan pertama) | Efisiensi murni, tanpa ubah kebijakan keamanan | Separuh jumlah request per Save | Rendah — perlu ubah kontrak response endpoint upsert (2 percobaan: dry-run → confirmed) |
| B | Rekap RAB: hapus debounce 250ms, pakai commit-on-blur (infrastruktur sudah ada) | Efisiensi murni | Hilangkan request beruntun saat mengetik | Sangat rendah |
| C | Template AHSP: naikkan `api_save_detail_ahsp_for_pekerjaan` ke tier yang sama dengan Volume Pekerjaan (240/60s) | Konsistensi klasifikasi (bukan pelemahan keamanan baru — menyamakan dengan preseden yang sudah divalidasi) | Selesaikan keluhan awal langsung | Rendah — endpoint ini tetap `@transaction.atomic` + `@limit_request_body()`; DoS-guard lapis payload-size tidak berubah |
| D | Template AHSP: ubah `selectJob()` agar tidak auto-POST synchronous tiap pindah (tunda/gabung simpan) | Efisiensi arsitektural — mengurangi KEBUTUHAN request, bukan hanya menaikkan pagu | Mengatasi akar masalah dari sisi frontend, berlaku jangka panjang | Sedang — kemungkinan perlu endpoint baru (multi-job) atau logic penundaan yang hati-hati agar tidak kehilangan data saat pindah cepat |
| E | Rincian AHSP: pertimbangkan bulk-override BUK jika alur "atur banyak pekerjaan sekaligus" umum dipakai | Efisiensi | Mengurangi request jika dipakai | Rendah, tapi perlu konfirmasi apakah use-case ini nyata dipakai |
| F | Bersihkan modul Jadwal legacy + performance-monitor dead code | Housekeeping | Cegah regresi laten | Sangat rendah |
| G | (Opsional, terpisah) Isi kategori `read`/`export` yang selama ini kosong | Housekeeping keamanan simetris | Menutup celah "tanpa proteksi" yang sama seperti HI-10/TA-07 dulu, kali ini di sisi baca/export | Perlu audit terpisah agar tidak salah kalibrasi lagi |

**Tidak direkomendasikan diubah:** seluruh endpoint "aksi langka" di §4.2 (hapus
template, reset-to-ref, sync-reference, reset-all-overrides, dll.) — 20/60s sudah
lebih dari cukup untuk frekuensi pemakaiannya, menaikkannya hanya memperbesar
permukaan risiko tanpa manfaat nyata.

---

## 8.1 Klarifikasi Owner (2026-07-13): Granularitas Request & Skalabilitas

Tiga pertanyaan owner yang mempertajam analisis §5-6:

**Apakah request berlaku per baris?** Tidak seragam — inilah akar kebingungan.
Harga Items/Volume Pekerjaan/Jadwal-assign-weekly/List-Pekerjaan-upsert membatch
**semua baris** jadi 1 request, tidak peduli jumlahnya. Template AHSP save dan
Rincian AHSP override BUK granularitasnya **per PEKERJAAN** (baris di List
Pekerjaan) — baris detail AHSP *di dalam* satu pekerjaan sudah batched, tapi
lintas-pekerjaan tidak.

**Apakah jumlah List Pekerjaan besar membuat user kerap kena limit?** Hanya untuk
2 endpoint yang granularitasnya per-pekerjaan (Template AHSP, Rincian AHSP
override) — di situ jumlah request **berbanding lurus** dengan jumlah pekerjaan
yang dikunjungi, karena itulah use-case paling umum saat mengisi RAB baru
(membuka-edit-tinggal setiap item satu-per-satu). Untuk 4 endpoint lain (batched)
— TIDAK; jumlah baris hanya memengaruhi *ukuran payload* satu request, dibatasi
mekanisme terpisah (`limit_request_body`, 413), bukan rate limit (429).

**Apakah aturan saat ini sudah tepat untuk kebutuhan ke depan?** Belum. Selama
granularitas Template AHSP tetap "1 request per pekerjaan dikunjungi", masalah
akan memburuk seiring project tumbuh (lebih banyak baris pekerjaan = wajar untuk
bisnis berkembang) — angka fixed berapa pun (20, 240, atau lainnya) hanya
menggeser titik jenuh, tidak menghilangkannya. **Opsi C (naikkan ke 240/60s)
direkomendasikan sebagai penambal aman jangka pendek; opsi D (hilangkan
auto-POST-per-pindah, batch lintas-pekerjaan) adalah satu-satunya perbaikan yang
membuat jumlah request tidak lagi bergantung pada ukuran project — future-proof
sesungguhnya, sejalan dengan pola yang sudah terbukti di Volume Pekerjaan/Jadwal.**

## 8.2 Temuan Tambahan: GET Ikut Terhitung di `api_pekerjaan_pricing`

Verifikasi ulang (2026-07-13) menemukan `api_pekerjaan_pricing`
(`views_api.py:5568-5573`) melayani **GET dan POST di view yang sama**, dan
`@rate_limit` tidak membedakan method — GET (sekadar membuka modal override BUK
untuk melihat nilai, tanpa menyimpan) ikut memakan jatah 20/60s yang sama dengan
POST (simpan). Ini lebih parah daripada dugaan awal §5.4: browsing pricing 15
pekerjaan tanpa menyimpan apa pun bisa menghabiskan 75% jatah.

Sebagai pembanding, `api_get_detail_ahsp` (Template AHSP, GET load-job-saat-pindah)
**tidak** memakai `@rate_limit` sama sekali — sudah bersih; yang kena limit murni
POST save saat job yang ditinggalkan memang dirty.

## 8.3 Rekomendasi Final (2026-07-13)

**Keputusan:** naikkan HANYA 2 endpoint (`api_save_detail_ahsp_for_pekerjaan` dan
`api_pekerjaan_pricing`) ke tier yang sama dengan Volume Pekerjaan (**240 req/60s**),
dan batasi `@rate_limit` di `api_pekerjaan_pricing` agar **hanya berlaku untuk POST**
(GET dibebaskan, konsisten dengan pola Template AHSP). Disarankan dirapikan sebagai
kategori resmi baru `RATE_LIMIT_CATEGORIES['write_frequent'] = {240, 60}` (bukan
angka ad-hoc yang ditempel manual seperti 8 endpoint Volume Pekerjaan saat ini) agar
inkonsistensi seperti yang memicu audit ini tidak terulang.

**Justifikasi angka:** 240/60s = 4 req/detik *sustained* selama 60 detik penuh —
melampaui kecepatan interaksi manusia mana pun (klik pilih → edit → pindah) untuk
pengisian data manual, berapa pun besar project di masa depan. Ambang ini dibatasi
oleh KECEPATAN TANGAN, bukan UKURAN PROJECT — sehingga tidak akan pernah kedaluwarsa
seiring pertumbuhan data, dan skenario yang masih tertangkap limitnya (>240/60s)
hanya mungkin berasal dari script/bot, bukan pemakaian wajar.

**Konsekuensi:** NOL perubahan fitur/UX — dialog konfirmasi & simpan-otomatis-saat-
pindah tetap identik persis. Satu-satunya trade-off: permukaan DoS teoretis melebar
20→240, dinilai dapat diterima karena payload tetap dibatasi 2 MB, tiap save tetap
`@transaction.atomic`, dan model 1-akun-1-project menghilangkan skenario abuse
lintas-user yang jadi alasan awal angka 20 dipasang generik.

**Opsi D (rombak arsitektur save-per-switch) DITARIK dari rekomendasi** — trade-off
nyata (jeda editan hanya di memori browser = risiko hilang data saat crash/tutup
tab) dan kompleksitas (perlu endpoint batch baru yang berisiko menabrak konvensi
atomic "1 simpan = all-or-nothing" yang berlaku konsisten di aplikasi ini) tidak
sepadan, mengingat 240/60s sudah menutup kasus untuk kecepatan manusia mana pun.

## 8.4 Klarifikasi: Tampilan (Display) vs Persistensi (Save Trigger)

Owner sempat mengusulkan arah lain: apakah model tampilan satu-pekerjaan-sekaligus
(master-detail) di Template/Rincian AHSP sendiri yang perlu dirombak? Jawaban:
**tidak** — dua hal ini independen:

- **View/GET** (berpindah melihat pekerjaan lain, tanpa edit): sudah di-cache
  client-side (`rowsByJob[id]`, TTL — `template_ahsp.js:1151-1168`) DAN endpoint
  GET-nya (`api_get_detail_ahsp`) tidak berlimit sama sekali. Berpindah-pindah
  melihat data **bukan** sumber masalah di Template AHSP.
- **Edit+Save/POST**: inilah yang 1:1 dengan jumlah pekerjaan yang disentuh — tapi
  ini soal **kapan sistem memutuskan mengirim ke server** (persistensi), bukan soal
  **bagaimana data ditata di layar** (tampilan). Mengubah tampilan (mis. tampilkan
  semua pekerjaan sekaligus) tanpa mengubah trigger simpan tidak mengurangi jumlah
  request sama sekali; sebaliknya, trigger simpan bisa diubah (ditunda/digabung)
  tanpa mengubah tampilan — itu persis Opsi D yang sudah DITARIK di §8.3 karena
  risiko kehilangan data > manfaatnya.
- Alasan tambahan menolak rombak tampilan: data AHSP per pekerjaan bertingkat
  (banyak kelompok × banyak baris), tidak datar seperti Harga Items/Volume
  Pekerjaan — memaksa semua pekerjaan tampil sekaligus berisiko memperburuk UX
  kerja fokus per-item, bukan memperbaikinya.

**Kesimpulan tetap konsisten dengan §8.3**: cukup naikkan ceiling + lepaskan GET
dari limit di Rincian AHSP. Tampilan tidak perlu diubah.

## 8.5 Klarifikasi: AHSP Custom dengan Referensi Bundle (Pekerjaan Gabungan)

Owner bertanya apakah temuan mempertimbangkan AHSP custom yang mereferensikan AHSP
lain (bundle, via `ref_ahsp_id`/`ref_kind='ahsp'|'job'`). Diverifikasi langsung ke
kode (bukan asumsi):

**Tidak mengubah kesimpulan rate-limit — terkonfirmasi, bukan diasumsikan:**

- Ekspansi bundle (ke Master AHSP maupun ke pekerjaan lain dalam project), termasuk
  bersarang sampai `MAX_DEPTH=10` (`services.py:2392-2398`, dengan deteksi circular
  dependency), berjalan sepenuhnya di server dalam 1 transaksi —
  `expand_bundle_to_components()`/`expand_ahsp_bundle_to_components()`
  (`views_api.py:2749, 2815`) adalah pemanggilan fungsi Python terhadap data yang
  sudah di-fetch, BUKAN API call terpisah.
- **Cascade re-ekspansi**: bila pekerjaan yang disimpan direferensikan pekerjaan
  lain sebagai bundle, `cascade_bundle_re_expansion(project, pkj.id)`
  (`views_api.py:2972-2988`) otomatis re-ekspansi SEMUA pekerjaan dependent — **di
  dalam request POST yang sama**. Gagal → seluruh transaksi rollback (WP-P2b/TA-20,
  konsisten no-silent-partial-success).
- Picker pencarian bundle (`api_search_ahsp`, `views_api.py:603-605`) juga tidak
  berlimit; memilih target "pekerjaan lain" tidak perlu API call terpisah (dari
  list yang sudah termuat).

**Kesimpulan: sesederhana atau serumit apa pun rantai bundle-nya, tetap 1 request
per pekerjaan yang disimpan.** Rekomendasi §8.3 tidak perlu direvisi untuk kasus ini.

**Batas eksplisit ruang lingkup (belum diaudit, dimensi berbeda):** cascade
re-ekspansi di atas berarti 1 request simpan BISA memicu kerja server yang lebih
berat (re-ekspansi banyak pekerjaan dependent sekaligus) bila pekerjaan yang
disimpan adalah komponen dasar yang direferensikan banyak pekerjaan lain. Ini soal
**seberapa berat 1 request diproses (latensi)**, bukan **berapa banyak request**
(topik doc 33). Efisiensi query di dalam `cascade_bundle_re_expansion` (mis. pola
N+1) belum diaudit — di luar scope laporan ini, dicatat sebagai kandidat audit
performa terpisah bila diperlukan.

## 14. KOREKSI (2026-08-01): Kesalahan Analitis pada Mekanisme Limiter

Verifikasi independen (owner + repo re-check) menemukan §3 dan §8.3 laporan ini
salah simpul, meski mekanisme TTL sudah dideskripsikan dengan benar. Dicatat di
sini agar jejak audit tetap jujur, bukan diam-diam diedit seolah tidak pernah salah.

**Kesalahan:** §3 menyatakan counter "meluruh alami `window` detik setelah request
sukses terakhir", lalu §8.3 menyimpulkan 240/60s = "4 req/detik sustained" yang
"future-proof". **Simpulan ini salah.** Karena `cache.set()` me-reset TTL ke
`window` PENUH di **setiap** hit sukses (bukan hanya menjaga TTL asli), maka
selama jeda antar-request < `window` detik, TTL tidak pernah sempat meluruh —
counter terus berakumulasi **tanpa batas waktu nyata**, bukan hanya dalam jendela
60 detik. Simulasi pembuktian: request tiap 50 detik selama 1.000 detik (16m40s)
tetap memblokir request ke-21 — kontradiksi langsung dengan klaim "240/60s tidak
akan pernah kedaluwarsa".

**Implikasi:** menaikkan angka (20→240) menunda masalah, tidak menghilangkannya —
user yang bekerja terus-menerus dengan jeda <60 detik akan tetap kena limit
setelah N operasi berapa pun N-nya, karena akar masalahnya di **algoritma**
(fixed-TTL-refresh, bukan fixed/sliding window yang valid), bukan di angka.

**Temuan lain yang perlu nuansa (bukan salah, tapi kurang presisi):**
- §5.2 (List Pekerjaan 2× POST): benar terjadi, tapi cache key berbasis nama
  fungsi view — dua endpoint beda `key_prefix` **tidak berbagi bucket rate-limit
  yang sama**. Ini tetap pemborosan (2× round-trip/beban server), tapi bukan
  "menghabiskan separuh kuota rate-limit yang sama" seperti tersirat di §5.2.
- §8.2 (GET+POST berbagi kuota): pola ini ditemukan di `api_pekerjaan_pricing`,
  tapi POLA YANG SAMA juga ada di 4 endpoint lain yang sudah tercatat di §4.3
  (`api_project_pricing`, `api_project_parameters`,
  `api_project_computed_parameters`, `api_volume_formula_state`) — perbaikannya
  perlu generik (parameter `methods=` di decorator), bukan patch khusus 1 endpoint.
- §1/§5.1 ("root cause terverifikasi presisi"): akurat secara pembacaan kode dan
  kecocokan pola dengan keluhan, tapi **belum dikonfirmasi dari log 429 server
  sungguhan** — klaimnya seharusnya "sangat masuk akal berdasarkan kode", bukan
  "terverifikasi presisi".
- §8.3 tidak mengaitkan temuan §8.5 (cascade bundle re-expansion bisa membuat 1
  request Template AHSP lebih berat secara komputasi) ke angka ceiling yang
  direkomendasikan — 240/60s dipilih murni dari argumen "kecepatan tangan
  manusia", tanpa bukti kapasitas server menangani volume itu.
- `Project.owner` adalah `ForeignKey` (`dashboard/models.py:12`, `related_name=
  "projects"`, jamak) — 1 user BISA memiliki banyak project. Arahan owner
  "abaikan skenario multi-user" tetap valid (limiter memang per-user, bukan
  per-project — lihat D-06 doc 34), tapi premis "1 akun = 1 project" yang
  dipakai sebagai penyederhana di seluruh laporan ini tidak ditegakkan oleh
  data model, murni cara pakai personal owner saat ini.

**Rujukan perbaikan:** seluruh rekomendasi numerik & algoritmik di laporan ini
digantikan oleh `34_API_Rate_Limiter_Remediation_Implementation_Plan_20260801.md`
(atomic fixed-window v2, pemisahan kuota GET/POST generik, kategori
`write_interactive`=60/60 awal — bukan 240 — dikalibrasi dari telemetry).
Peta endpoint & analisis pola trigger per halaman (§4-§6, §8.4-§8.5) tetap
berlaku dan menjadi input bagi doc 34.

## 9. Definisi Selesai Laporan Ini

- [x] Peta lengkap 30 endpoint tulis + kategorinya
- [x] Pola trigger & status batching tiap halaman ber-bukti file:baris
- [x] Root cause keluhan owner terverifikasi presisi (Template AHSP)
- [x] Pemborosan independen ditemukan & didokumentasikan (List Pekerjaan, Rekap RAB)
- [x] Verifikasi bahwa 20/60s bukan keputusan risk-based yang disengaja (riwayat doc 18/19)
- [x] Opsi implementasi disusun dengan trade-off eksplisit, TANPA eksekusi
- [ ] Menunggu owner memilih scope → lanjut ke implementation plan (dokumen terpisah)
