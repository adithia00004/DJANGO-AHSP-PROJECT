# Rencana Assisted Repair Import AHSP

## Tujuan

Mencegah data AHSP masuk database secara parsial atau salah kolom ketika hasil convert PDF ke Excel memiliki warning seperti `WARNING: Uraian Kosong (Wrapped Data)`.

Prinsip utama: jika satu tabel AHSP belum bersih, tabel tersebut tidak boleh masuk `Data Valid` untuk import database.

## Masalah Saat Ini

Alur saat ini:

1. User convert PDF ke Excel validasi.
2. Sistem menandai wrapped/geser kolom sebagai warning.
3. Warning tetap dapat ikut `Download Data Valid` jika struktur tabel dianggap lengkap.
4. Import berikutnya membaca data berdasarkan posisi kolom.

Risiko:

- `uraian_item` bisa kosong atau `-`.
- Nilai yang seharusnya `Uraian` bisa tersimpan sebagai `Kode Referensi`.
- `Satuan` dan `Koefisien` bisa bergeser.
- Import terlihat berhasil tetapi database berisi data AHSP yang salah.

## Kebijakan Validasi Baru

Status tabel dibagi menjadi:

- `valid`: struktur lengkap dan tidak ada blocker.
- `repairable_warning`: ada warning yang mungkin bisa diperbaiki otomatis.
- `blocked_warning`: masih ada warning setelah repair atau confidence rendah.
- `anomaly`: struktur tidak lengkap, segmen tidak dikenal, atau data tidak bisa dipetakan.

Aturan download:

- `Download Data Valid` hanya berisi tabel `valid`.
- Tabel `repairable_warning`, `blocked_warning`, dan `anomaly` dilewati.
- Sistem wajib memberi ringkasan tabel yang dilewati sebelum download.

## Assisted Repair

Fitur assisted repair berjalan sebelum user download `Data Valid`.

Target awal repair:

- `WARNING: Uraian Kosong (Wrapped Data)`.
- Baris dengan kolom bergeser akibat wrapped text.
- Segment title yang ikut terbaca sebagai data.

Repair harus berbasis preview dan approval user, bukan silent mutation.

### Kandidat Repair

Sistem membuat saran per baris, misalnya:

- Geser nilai dari `Kode Referensi` ke `Uraian`.
- Geser nilai dari `Satuan` ke `Kode Referensi`.
- Geser nilai dari `Koefisien` ke `Satuan`.
- Gabungkan teks continuation ke baris sebelumnya jika confidence tinggi.
- Tandai `Tidak bisa diperbaiki otomatis` jika pola tidak jelas.

### Confidence

Gunakan confidence sederhana:

- `high`: pola jelas, misalnya `Uraian` kosong tetapi kolom sebelah berisi teks panjang dan kolom koefisien tetap numerik.
- `medium`: pola mungkin benar, tetapi ada lebih dari satu kemungkinan.
- `low`: sistem tidak boleh auto-apply, hanya tampilkan untuk edit manual.

Default:

- `high` boleh dipilih otomatis tetapi tetap ditampilkan untuk review.
- `medium` dan `low` butuh keputusan user.

## UX Flow

1. User membuka halaman validation report.
2. Sistem menampilkan summary:
   - tabel valid
   - tabel perlu repair
   - tabel blocked/anomali
3. Jika ada warning repairable, tampilkan tombol `Review Assisted Repair`.
4. User membuka panel repair:
   - daftar tabel bermasalah
   - daftar baris bermasalah
   - before/after kolom
   - aksi `Apply`, `Edit Manual`, `Skip Tabel`
5. Setelah repair, sistem validasi ulang status tabel.
6. Sebelum download, tampilkan konfirmasi:
   - jumlah tabel yang akan masuk Data Valid
   - jumlah tabel yang dilewati
   - daftar kode AHSP yang dilewati
7. User download:
   - `Data Valid`
   - opsional `Data Dilewati / Perlu Review`

## Aturan Penting

Jika satu tabel AHSP masih memiliki warning blocker, seluruh tabel dilewati dari `Data Valid`.

Contoh:

- `4.1.1.1` memiliki 20 baris.
- 18 baris valid.
- 2 baris masih `WARNING: Uraian Kosong`.
- Maka seluruh `4.1.1.1` tidak masuk `Data Valid`.

Alasan: input sebagian dapat merusak integritas referensi AHSP.

## Perubahan Teknis

### 1. Status Model di Validation Result

Tambahkan properti pada `table_container`:

- `repair_status`
- `repair_reasons`
- `repair_candidates`
- `is_blocked`
- `blocked_reasons`

Lokasi awal:

- `referensi/views/import_views.py`
- helper `_get_validation_results`

### 2. Deteksi Wrapped Row

Buat helper terpisah:

- `detect_wrapped_row(clean_row)`
- `build_repair_candidate(clean_row)`
- `apply_repair_candidate(row, candidate)`

Pertimbangkan memindahkan logic ke service agar testable:

- `referensi/services/import_repair.py`

### 3. API Repair Preview

Endpoint kandidat:

- `POST /referensi/import/validate/repair/preview/`
- `POST /referensi/import/validate/repair/apply/`

Alternatif fase awal:

- lakukan repair state di frontend WYSIWYG, lalu export dari DOM.
- kelemahan: tidak persist dan lebih sulit dites.

Rekomendasi: backend service + session/temp file agar hasil repair bisa divalidasi ulang.

### 4. Download Data Valid

Saat export:

- filter hanya `table_container` dengan `is_blocked == False` dan `is_anomaly == False`.
- dedupe `Daftar Isi` berdasarkan parent code yang benar-benar memiliki data.
- jangan masukkan kode hierarki seperti `1.2.1` jika tidak punya data rincian.

### 5. Download Data Dilewati

File ini berisi:

- `Kode AHSP`
- `Judul`
- `Alasan dilewati`
- `Jumlah baris bermasalah`
- data baris raw/normalized

Tujuan: memudahkan user memperbaiki Excel sumber.

## Acceptance Criteria

- Tabel dengan wrapped warning tidak masuk `Data Valid` sebelum diperbaiki.
- User melihat daftar kode AHSP yang dilewati sebelum download.
- Setelah assisted repair berhasil, tabel dapat berubah menjadi valid.
- Jika repair gagal atau warning tersisa, seluruh tabel tetap dilewati.
- `Data Valid` hanya berisi parent AHSP yang punya data rincian valid.
- `Daftar Isi` tidak dobel antara level struktur `1.2.1` dan parent data `1.2.1.1`.
- Import database tidak menerima tabel setengah lengkap dari alur validasi.

## Test Plan

Unit tests:

- wrapped row terdeteksi.
- repair candidate dibuat dengan confidence benar.
- low confidence tidak auto-apply.
- tabel dengan warning blocker ditandai blocked.
- tabel valid tetap masuk export.

Integration tests:

- file dengan `4.1.1.1` berisi 2 wrapped rows tidak masuk `Data Valid`.
- setelah repair, `4.1.1.1` masuk `Data Valid`.
- `Data Dilewati` memuat kode dan alasan yang benar.
- `Daftar Isi` hanya berisi parent yang memiliki data valid.

Manual QA:

- validasi file PDF convert yang sudah ada.
- klik Review Assisted Repair.
- apply repair pada beberapa baris.
- download Data Valid.
- import ke database.
- cek database tidak memiliki `uraian_item` kosong akibat wrapped row.

## Risiko

- Auto repair salah dapat lebih berbahaya daripada skip.
- Pola wrapped text bisa berbeda antar PDF.
- Edit frontend tanpa persist bisa membingungkan user.
- Session/temp file perlu cleanup agar tidak menumpuk.

Mitigasi:

- jangan silent auto-fix.
- gunakan confidence dan user approval.
- simpan hasil repair sebagai file/session revisi.
- sediakan export `Data Dilewati`.

## Fase Implementasi

### Fase 1: Blocker Policy

- Warning wrapped menjadi blocker tabel.
- Download Data Valid melewati tabel blocked.
- Tambah konfirmasi daftar tabel dilewati.

### Fase 2: Repair Preview

- Tambah deteksi kandidat repair.
- Tampilkan before/after.
- User bisa apply atau skip.

### Fase 3: Persisted Repair

- Simpan hasil repair ke temp file/session.
- Validasi ulang setelah repair.
- Export memakai hasil repair terbaru.

### Fase 4: Hardening

- Tambah test coverage.
- Tambah telemetry/log import repair.
- Tambah cleanup temp files.

