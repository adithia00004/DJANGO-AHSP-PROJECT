# Panduan Validasi Data AHSP Hasil Impor

Panduan ini membantu administrator memastikan bahwa berkas Excel yang diimpor
melalui halaman preview (`/referensi/import/preview/`) cocok dengan skema model
`AHSPReferensi` dan `RincianReferensi` yang digunakan aplikasi.

## 1. Persiapan dan Upload
1. **Gunakan akun staff/superuser.** Hanya akun dengan hak istimewa yang dapat
   mengakses preview dan melakukan impor.
2. **Siapkan berkas Excel.** Pastikan kolom-kolom minimal berisi kode AHSP,
   nama pekerjaan, kategori item, uraian, satuan, dan koefisien. Parser akan
   menormalkan variasi penamaan kolom umum (mis. `kode`, `uraian`, `qty`).
3. **Buka halaman preview impor** dan unggah berkas. Sistem hanya membaca data
   dan belum menulis ke basis data.

## 2. Standar Tabel Excel yang Diterima

Pastikan lembar kerja Anda memiliki satu tabel dengan kolom-kolom berikut. Nama
kolom dapat memakai salah satu alias pada tabel di bawah ini. Nilai pada kolom
"wajib" harus tersedia agar parser bisa menyalin data ke model `AHSPReferensi`
dan `RincianReferensi`.

### Pekerjaan AHSP (ditulis ke `referensi_ahspreferensi`)

| Kolom (wajib?) | Alias header yang diterima | Tipe data | Keterangan |
| --- | --- | --- | --- |
| `sumber_ahsp` ✅ | `sumber_ahsp` | Teks ≤ 100 karakter | Nama sumber referensi, mis. `AHSP SNI 2025`. |
| `kode_ahsp` ✅ | `kode_ahsp`, `kode` | Teks ≤ 50 karakter | Kode pekerjaan unik dalam satu sumber. |
| `nama_ahsp` ✅ | `nama_ahsp`, `nama` | Teks bebas | Nama/uraian pekerjaan. |
| `klasifikasi` | `klasifikasi` | Teks ≤ 100 karakter | Klasifikasi pekerjaan (opsional). |
| `sub_klasifikasi` | `sub_klasifikasi`, `sub klasifikasi`, `subklasifikasi` | Teks ≤ 100 karakter | Sub-klasifikasi (opsional). |
| `satuan_pekerjaan` | `satuan_pekerjaan`, `satuan_ahsp`, `satuan_pekerjaan_ahsp` | Teks ≤ 50 karakter | Satuan pekerjaan (opsional). |

### Rincian Item (ditulis ke `referensi_rincianreferensi`)

| Kolom (wajib?) | Alias header yang diterima | Tipe data | Keterangan |
| --- | --- | --- | --- |
| `kategori` ✅ | `kategori`, `kelompok` | Teks (`TK`, `BHN`, `ALT`, `LAIN` atau sinonim) | Kategori item; variasi teks akan dipetakan otomatis. |
| `kode_item` ✅ | `kode_item`, `kode_item_lookup` | Teks ≤ 50 karakter | Kode item terkait pekerjaan. |
| `uraian_item` ✅ | `uraian_item`, `item` | Teks bebas | Deskripsi item/material. |
| `satuan_item` ✅ | `satuan_item`, `satuan` | Teks ≤ 20 karakter | Satuan item. |
| `koefisien` ✅ | `koefisien`, `koef`, `qty` | Angka desimal ≥ 0 | Koefisien pemakaian item. |

Apabila salah satu kolom wajib hilang atau nama kolom tidak sesuai daftar di
atas, halaman preview akan menampilkan pesan error dan tidak menyediakan tombol
"Impor ke Database" hingga kolom diperbaiki.

## 3. Memeriksa Tab "AHSP Referensi"
Tab ini mewakili isi yang akan ditulis ke tabel `referensi_ahspreferensi`.
Verifikasi hal berikut:

- **Kolom wajib terisi.**
  - `Sumber` diisi sesuai nama sumber pada berkas (default `AHSP SNI 2025`).
  - `Kode` tidak boleh kosong atau duplikat dalam kombinasi `sumber + kode`.
  - `Nama Pekerjaan` memuat deskripsi jelas. Gunakan preview untuk menemukan
    baris yang dipotong atau tidak sesuai.
- **Klasifikasi dan sub-klasifikasi**: bila berkas tidak menyediakan nilai,
  kolom akan menunjukkan `-`. Anda dapat melengkapinya kemudian dari halaman
  manajemen database.
- **Satuan**: pastikan satuan per pekerjaan terisi bila dibutuhkan.
- **Jumlah Rincian**: angka di kolom ini memudahkan mengecek apakah setiap
  pekerjaan memiliki rincian yang terbaca.

Jika ada inkonsistensi, perbaiki di sumber Excel terlebih dahulu dan ulangi
proses preview.

## 4. Memeriksa Tab "Rincian Item"
Tab kedua menggambarkan data yang akan disimpan ke `referensi_rincianreferensi`.
Periksa dengan teliti karena setiap baris menjadi item terkait pekerjaan.

- **Kategori (DB)** menampilkan hasil pemetaan ke enum `TK/BHN/ALT/LAIN`.
  Kolom "Kategori Sumber" membantu melihat teks asli dari berkas. Jika parser
  tidak dapat mengenali kategori, badge peringatan akan muncul dan baris
  diberi label `(otomatis)`.
- **Kode Item, Uraian, dan Satuan** harus terisi. Nilai kosong akan diimpor
  sebagai string kosong dan memicu anomali di dashboard database.
- **Koefisien** tampil dalam format desimal standar. Pastikan angka yang
  menggunakan pemisah ribuan/koma lokal sudah tersaji benar (mis. `1.234,56`
  menjadi `1234.56`).
- **Jumlah baris**: cocokkan dengan total rincian pada tab pertama untuk
  mendeteksi item yang hilang.

Jika menemukan data salah, klik "Kembali" di browser atau muat ulang halaman,
perbaiki berkas Excel, lalu unggah ulang.

## 5. Menyimpan Hasil ke Basis Data
1. Setelah dua tab di atas terlihat benar dan tidak ada pesan error merah,
   tekan tombol **"Impor ke Database"**. Sistem akan:
   - Menghapus rincian lama untuk kombinasi `sumber + kode` yang sama.
   - Menulis ulang metadata pekerjaan ke `AHSPReferensi`.
   - Mengisi semua rincian ke `RincianReferensi` dalam satu transaksi sehingga
     kedua tabel selalu sinkron.
2. Tunggulah pesan sukses hijau sebagai konfirmasi.

## 6. Validasi Pascaimpor
1. **Dashboard Database Referensi**: buka `/referensi/admin/database/` untuk
   melihat tab AHSP dan Rincian secara langsung. Fitur filter dan indikator
   anomali memudahkan mendeteksi data kosong atau tidak wajar.
2. **Cek via Django shell** (opsional):
   ```python
   from referensi.models import AHSPReferensi, RincianReferensi
   AHSPReferensi.objects.count()
   RincianReferensi.objects.count()
   ```
   Cocokkan jumlah baris dengan ringkasan preview atau sumber Excel.
3. **Audit relasi**: di halaman detail pekerjaan (tab "Rincian"), pastikan
   item yang tampil sesuai dengan preview.

## 7. Langkah Pemulihan Jika Terjadi Kesalahan
1. Jalankan `python manage.py dumpdata referensi.AHSPReferensi referensi.RincianReferensi --indent 2 > backup_ahsp.json`
   sebelum mengimpor untuk berjaga-jaga.
2. Jika perlu mengulang dari awal, gunakan perintah `python manage.py purge_ahsp_referensi`
   yang akan melepaskan relasi ke proyek dan membersihkan kedua tabel secara
   aman.
3. Setelah databasenya bersih, ulangi proses preview dan impor hingga data
   sesuai.

Dengan mengikuti langkah-langkah di atas, Anda dapat memastikan berkas Excel
menyesuaikan skema model dan kedua tabel target menerima data yang konsisten.
