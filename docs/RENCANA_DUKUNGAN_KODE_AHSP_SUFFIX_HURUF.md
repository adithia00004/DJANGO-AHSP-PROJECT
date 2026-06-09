# Rencana Dukungan Kode AHSP Suffix Huruf

> **Status: TERIMPLEMENTASI (2026-06-02).** Helper `referensi/services/ahsp_code.py`
> dibuat sebagai single source of truth; `_get_validation_results` dan
> `excel_clean_upload` di-refactor memakainya; bug laten `regex_kode_ahsp`
> (NameError) ikut diperbaiki. Aturan terkunci: suffix satu huruf valid pada
> **3+ segmen angka** (ikut regex PDF), huruf tidak dihitung sebagai segmen,
> klasifikasi berdasarkan jumlah segmen angka. PDF conversion sudah mendukung
> suffix sejak awal (regex `^(\d+(?:\.\d+){2,}(?:\.[a-zA-Z])?)`) sehingga tidak
> diubah. Tes: `referensi/tests/test_ahsp_code.py`, `test_suffix_import.py`.

## Tujuan

Mendukung format kode AHSP baru yang memiliki suffix huruf di akhir, misalnya:

```text
2.2.1.1.5.a
2.2.1.1.5.b
2.2.1.1.5.c
```

Kode tersebut harus diperlakukan sebagai parent AHSP yang berbeda, bukan digabung ke parent dasar `2.2.1.1.5`.

## Masalah Saat Ini

Beberapa bagian parser masih menganggap kode AHSP hanya berupa angka bertitik seperti:

```text
1.1.1.1
1.1.1.1.5
```

Akibatnya, kode seperti:

```text
2.2.1.1.5.a
2.2.1.1.5.b
2.2.1.1.5.c
```

berisiko terbaca sebagai satu parent:

```text
2.2.1.1.5
```

Dampak:

- rincian `a`, `b`, dan `c` tercampur dalam satu tabel.
- segment TK/BHN/PR dari beberapa parent menjadi duplikat.
- validation report menampilkan warning/anomali palsu.
- Data Valid bisa melewati tabel yang sebenarnya salah grouping.

## Definisi Kode AHSP

Kode AHSP valid:

```text
1.1
1.1.1
1.1.1.1
1.1.1.1.5
1.1.1.1.5.a
```

Aturan:

- Segmen angka dipisahkan titik.
- Jumlah segmen angka minimal 2.
- Parent AHSP untuk import rincian adalah 4 atau 5 segmen angka, atau 5 segmen angka dengan suffix huruf.
- Suffix huruf hanya boleh satu karakter alfabet di segmen terakhir.
- Suffix huruf tidak boleh muncul di tengah kode.
- Kode berhenti di spasi pertama atau akhir string.

Contoh parsing judul:

```text
1.1.1.1 Nama Judul
```

hasil:

```text
kode_ahsp = 1.1.1.1
nama_ahsp = Nama Judul
```

```text
2.2.1.1.5.a Nama Judul
```

hasil:

```text
kode_ahsp = 2.2.1.1.5.a
nama_ahsp = Nama Judul
```

## Format Invalid

Format berikut harus tetap ditolak:

```text
2.2.a.1
2.2.1.a.5
2.2.1.1.5.aa
2.2.1.1.5.a.1
2.2.1.1.5.a.b
```

## Rencana Teknis

### 1. Single Source of Truth

Buat helper/service baru:

```text
referensi/services/ahsp_code.py
```

Fungsi yang disarankan:

```python
extract_ahsp_code(text: str) -> str | None
split_ahsp_title(text: str) -> tuple[str | None, str]
is_ahsp_code(code: str) -> bool
classify_ahsp_code(code: str) -> str
normalize_ahsp_code(code: str) -> str
```

Klasifikasi:

```text
classification      -> 1.1
subclassification   -> 1.1.1
parent              -> 1.1.1.1, 1.1.1.1.5, 1.1.1.1.5.a
invalid             -> format tidak valid
```

### 2. Update PDF Conversion

Terapkan helper baru pada proses convert PDF ke Excel.

Target:

- `2.2.1.1.5.a` tetap disimpan penuh sebagai parent code.
- Header continuation tetap digabung sebagai judul.
- Tidak ada truncation ke `2.2.1.1.5`.

### 3. Update Validation Report

Terapkan helper baru di `_get_validation_results`.

Target:

- `2.2.1.1.5.a` dikenali sebagai `hierarchy_parent`.
- `2.2.1.1.5.b` dikenali sebagai parent berbeda.
- `2.2.1.1.5.c` dikenali sebagai parent berbeda.
- Table container memakai full parent code.
- Data Valid dan Anomali tidak menggabungkan parent yang berbeda.

### 4. Update Clean Excel Import

Terapkan helper baru di `excel_clean_upload`.

Target:

- file hasil `Download Data Valid` dengan parent suffix huruf bisa masuk staging.
- `staging_commit` membuat AHSP terpisah berdasarkan full code.
- `2.2.1.1.5.a` tidak digabung dengan `2.2.1.1.5`.

### 5. Export dan Daftar Isi

Pastikan export memakai full parent code.

Aturan:

- `Daftar Isi` dedupe berdasarkan kode penuh.
- `2.2.1.1.5`, `2.2.1.1.5.a`, `2.2.1.1.5.b` adalah entri berbeda.
- Tidak boleh dedupe berdasarkan prefix.

## Acceptance Criteria

- Sistem membaca `2.2.1.1.5.a`, `.b`, `.c` sebagai tiga parent AHSP berbeda.
- TK/BHN/PR dari `.a`, `.b`, `.c` tidak tercampur.
- Validation report tidak memberi anomali palsu akibat grouping ke parent dasar.
- `Download Data Valid` menghasilkan `Kode Induk` lengkap dengan suffix huruf.
- `Daftar Isi` berisi kode penuh dan tidak menghilangkan suffix huruf.
- `excel_clean_upload` menerima kode suffix huruf.
- `staging_commit` menyimpan AHSP suffix huruf sebagai record terpisah.
- Kode numerik lama tetap bekerja.
- Format invalid tetap ditolak.

## Test Plan

Unit tests untuk `ahsp_code.py`:

- valid numeric code.
- valid suffix-letter code.
- extract code from `2.2.1.1.5.a Nama Judul`.
- split title dari kode numeric dan suffix huruf.
- reject suffix huruf di tengah.
- reject suffix lebih dari satu huruf.

Integration tests:

- validation report dengan parent `2.2.1.1.5.a`, `.b`, `.c`.
- export WYSIWYG Data Valid tidak menggabungkan `.a`, `.b`, `.c`.
- clean import dapat memasukkan `.a`, `.b`, `.c` ke staging.
- staging commit membuat tiga `AHSPReferensi` berbeda.

Regression tests:

- parent numeric lama `1.1.1.1 Nama Judul` tetap terbaca sebagai `1.1.1.1`.
- `1.1.1` tetap sub-klasifikasi, bukan parent data.
- Data Valid lama tanpa suffix huruf tetap bisa diimport.

## Risiko dan Mitigasi

Risiko:

- Regex terlalu longgar menerima kode invalid.
- Kode suffix huruf terpotong saat split judul.
- Sorting string membuat urutan terlihat berbeda.
- Beberapa jalur import masih memakai regex lama.

Mitigasi:

- Semua parser wajib memakai helper `ahsp_code.py`.
- Tambahkan test untuk semua format invalid.
- Audit semua penggunaan regex kode AHSP setelah implementasi.
- Jangan mengubah model database karena field saat ini sudah cukup.

## Urutan Implementasi Disarankan

1. Buat `referensi/services/ahsp_code.py`.
2. Tambah unit test helper kode AHSP.
3. Refactor `_get_validation_results`.
4. Refactor PDF conversion.
5. Refactor `excel_clean_upload`.
6. Tambah integration test export dan staging commit.
7. Jalankan validasi ulang pada file AHSP yang memuat `.a/.b/.c`.

