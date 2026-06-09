# Laporan Bug: Dampak Import AHSP (sumber & suffix) terhadap detail_project

**Tanggal:** 2026-06-02
**Konteks:** Pengujian import AHSP 2026 (kode bersuffix `X.X.X.X.X.a/b/c`) dan penambahan sumber AHSP baru.
**Catatan:** ASCII-only (hindari mojibake). Dua bug independen di bawah, plus satu akar penyebab arsitektural yang sama untuk Bug B.

---

## Bug A -- Nama AHSP bersuffix tersimpan = kodenya sendiri

### Gejala
AHSP dengan kode `X.X.X.X.X.a/b/c/d` (mis. `2.2.1.1.5.a`) tersimpan dengan `nama_ahsp` = kode itu sendiri (`"2.2.1.1.5.a"`), bukan uraian pekerjaan. Kode 4-segmen (`X.X.X.X`) normal.

### Akar penyebab (TERKONFIRMASI)
Pemisah kode/nama di JS export WYSIWYG, `referensi/templates/referensi/import_validate_report.html:797`:
```js
const codeMatch = rawText.match(/^([\d\.]+)/);   // character class hanya digit & titik
```
`[\d\.]+` tidak menerima huruf. Untuk `2.2.1.1.5.a Pasangan Batu Kali`, regex berhenti sebelum huruf `a` tetapi menelan titik sebelumnya:
- `code = "2.2.1.1.5."` (titik gantung di akhir)
- `title = "a Pasangan Batu Kali"`

Untuk kode 4-segmen, regex berhenti di spasi -> kode bersih -> normal. Inilah diferensialnya.

### Rantai dampak
1. JS menulis `hierarchy` dengan kode rusak `2.2.1.1.5.` ke sheet "Daftar Isi" saat "Download Data Valid".
2. Saat clean-import, `_stage_rincian_from_export` menormalkan: `normalize_ahsp_code("2.2.1.1.5.")` -> `""` (ditolak) -> **HEADING (judul) dibuang**.
3. Baris data tetap punya parent benar `2.2.1.1.5.a`.
4. `staging_commit`: HEADING untuk `2.2.1.1.5.a` tidak ketemu -> fallback `nama_ahsp = parent_code` -> nama = kode.

### Bukti empiris
Reproduksi regex+normalisasi: `1.1.1.1 ...` -> code `1.1.1.1` (HEADING ok); `2.2.1.1.5.a ...` -> code `2.2.1.1.5.` -> `normalize` mengembalikan `""` -> HEADING DROPPED.

### Severity
Sedang-tinggi: data referensi suffix masuk DB tanpa nama yang benar (perlu koreksi/re-import setelah fix). Hanya jalur WYSIWYG round-trip; jalur clean-import flat menangani suffix dengan benar (`split(' ')[0]`).

### Rekomendasi fix
- **Cepat:** ganti `rawText.match(/^([\d\.]+)/)` -> ambil token pertama `rawText.split(/\s+/)[0]` (sudah menangani suffix), atau regex sadar-suffix `^(\d+(?:\.\d+)+(?:\.[A-Za-z])?)`.
- **Prinsipil (sejalan roadmap R1/R8):** server mengekspos atribut terstruktur (`data-code`, `data-title`) pada elemen hierarchy_parent; JS berhenti mem-parse string tampilan.
- Backfill: AHSP suffix yang sudah terlanjur tersimpan dengan nama = kode perlu di-perbaiki (re-import setelah fix, atau update nama).

---

## Bug B -- Menambah sumber baru membuat pekerjaan REF lama "berubah versi" dan gagal disimpan (500)

### Gejala
Setelah menambah sumber AHSP baru (mis. AHSP 2026), pekerjaan di proyek lama yang memakai versi lama:
1. **Otomatis "ter-update" ke versi terbaru** (tampilan/rincian berubah), dan
2. **Gagal disimpan** -- `POST /detail_project/api/project/<id>/list-pekerjaan/upsert/` -> **500 Internal Server Error**.

### Akar penyebab (TERKONFIRMASI secara arsitektur)
`detail_project` me-resolve sebagian referensi **berdasarkan `kode_ahsp` SAJA**, tanpa `sumber`. Selama hanya ada satu sumber, `kode_ahsp` efektif unik dan ini laten. Setelah ada >1 sumber dengan kode sama (justru didorong oleh model uniqueness per `(sumber, kode_ahsp)`), resolusi jadi ambigu:

- **`AHSPReferensi.objects.filter(kode_ahsp=kode).first()`** -- `detail_project/services.py:1925` (`clone_ref_pekerjaan`, resolusi item LAIN/bundle) dan `services.py:2012` (clone rincian). `.first()` **tidak crash** tetapi **memilih sumber sembarang** (urutan model `["kode_ahsp"]` tidak menentukan sumber) -> menjelaskan **"otomatis ter-update ke versi terbaru"** (sumber baru bisa terpilih).
- **`AHSPReferensi.objects.get(kode_ahsp=comp.kode_item)`** -- `detail_project/services.py:1433` (`expand_ahsp_bundle_to_components`, juga dipanggil di `views_api.py:2473`, `services.py:1436/1542`). `.get()` pada field non-unik dengan >1 baris -> **`MultipleObjectsReturned` -> 500**.

Jalur seleksi utama (pilih AHSP by `ref_id`/id) tetap aman; **hanya titik resolusi by-`kode_ahsp` ini** yang rusak.

### Hipotesis rantai 500 (perlu konfirmasi traceback)
1. Sumber baru -> `kode_ahsp` duplikat.
2. Saat load/refresh, resolusi by-`kode_ahsp` (`.first()`) menampilkan/mengirim ref versi baru -> pekerjaan "ter-update".
3. Saat save, ref efektif berubah -> jalur **replace** memanggil `clone_ref_pekerjaan`; selama clone, salah satu terjadi:
   - `expand`/lookup `.get(kode_ahsp=...)` -> `MultipleObjectsReturned` -> 500; **atau**
   - `_upsert_harga_item` (`services.py:998`) menolak karena kategori `kode_item` berubah antar-sumber (ValidationError kategori immutability) -> jika tak tertangani -> 500.

> **Yang belum pasti:** baris persis pelempar 500. Browser hanya menampilkan "Internal Server Error" generik. **Dibutuhkan traceback dari console server Django** (terminal `runserver`) saat upsert gagal untuk memilih antara MultipleObjectsReturned vs ValidationError vs lainnya.

### Severity
**Tinggi.** Memblokir penyimpanan pekerjaan di proyek existing begitu ada >1 sumber; berpotensi mengganti versi AHSP pekerjaan tanpa kehendak user (integritas data proyek).

### Rekomendasi fix
1. **Resolusi referensi harus sadar-`sumber`.** Ganti lookup by-`kode_ahsp` menjadi by-`(kode_ahsp, sumber)` -- resolve nested/bundle dalam **sumber yang sama** dengan AHSP induk (objek induk sudah punya `.sumber`):
   ```python
   AHSPReferensi.objects.filter(kode_ahsp=comp.kode_item, sumber=ahsp.sumber).first()
   ```
2. **Hapus `.get(kode_ahsp=...)`** -> pakai `filter(...).first()` + tangani not-found, sehingga tidak pernah `MultipleObjectsReturned`.
3. **Ideal jangka panjang:** simpan referensi nested sebagai **FK by id** (`ref_ahsp_id`), bukan pencocokan string `kode_ahsp`, agar tahan terhadap multi-sumber & re-import.
4. **Jangan auto-ganti versi.** Pekerjaan REF existing harus tetap terikat ke `ref_id` yang tersimpan; penggantian versi harus aksi eksplisit user, bukan efek samping resolusi by-kode.

---

## Akar penyebab lintas-bug & kaitan roadmap

Kedua bug berakar pada **kode AHSP dipakai sebagai kunci string yang diparse/diresolusi ulang**, bukan sebagai data terstruktur dengan identitas stabil:
- Bug A: kode di-parse dari string tampilan di klien (regex tak sadar-suffix).
- Bug B: referensi diresolusi ulang dari `kode_ahsp` tanpa `sumber` (ambigu saat multi-sumber).

Ini menguatkan arah `docs/REVIEW_ALUR_IMPORT_AHSP.md`:
- **R1 (kontrak terstruktur)** + tidak mem-parse kode di klien -> mencegah Bug A.
- **Resolusi by id / by `(sumber, kode_ahsp)`** -> mencegah Bug B. Tambahkan ini sebagai temuan implikasi di bagian detail_project.

---

## Status & langkah berikut
- **Bug A:** akar penyebab pasti; fix siap diterapkan (1 baris JS + test regression end-to-end suffix membawa nama).
- **Bug B:** akar penyebab arsitektur pasti; perbaikan resolusi sadar-sumber siap dirancang. **Butuh traceback server** untuk memilih perbaikan paling tepat di titik crash (MultipleObjectsReturned vs ValidationError) dan menambah guard yang sesuai.
- Belum ada kode produksi diubah oleh laporan ini (analisis + dokumentasi).
