# Format File XLSX untuk Import AHSP

Dokumentasi lengkap format file Excel (.xlsx/.xls) yang diterima oleh sistem import AHSP.

## 📊 Overview

**1 File XLSX → 2 Tabel Database**

Satu file Excel akan mengisi **dua tabel database** secara otomatis:
- ✅ `AHSPReferensi` - Tabel Pekerjaan AHSP
- ✅ `RincianReferensi` - Tabel Rincian Item

## 📋 Format Kolom yang Diterima

### **Kolom Wajib:**

| Nama Kolom | Alias yang Diterima | Tipe Data | Deskripsi | Tabel Target |
|------------|---------------------|-----------|-----------|--------------|
| `sumber_ahsp` | - | Teks (max 100 char) | Sumber AHSP, mis. "AHSP SNI 2025" | AHSPReferensi |
| `kode_ahsp` | `kode` | Teks (max 50 char) | Kode pekerjaan unik | AHSPReferensi |
| `nama_ahsp` | `nama` | Teks | Nama/uraian pekerjaan | AHSPReferensi |
| `kategori` | `kelompok` | Teks (TK/BHN/ALT/LAIN) | Kategori item | RincianReferensi |
| `uraian_item` | `item` | Teks | Uraian item/material | RincianReferensi |
| `satuan_item` | `satuan` | Teks (max 20 char) | Satuan item | RincianReferensi |
| `koefisien` | `koef`, `qty` | Angka desimal ≥ 0 | Koefisien pemakaian | RincianReferensi |

### **Kolom Opsional:**

| Nama Kolom | Alias yang Diterima | Tipe Data | Deskripsi | Tabel Target |
|------------|---------------------|-----------|-----------|--------------|
| `kode_item` | `kode_item_lookup` | Teks (max 50 char) | Kode item (auto-generate jika kosong) | RincianReferensi |
| `klasifikasi` | - | Teks (max 100 char) | Klasifikasi pekerjaan | AHSPReferensi |
| `sub_klasifikasi` | `sub klasifikasi`, `subklasifikasi` | Teks (max 100 char) | Sub-klasifikasi | AHSPReferensi |
| `satuan_pekerjaan` | `satuan_ahsp`, `satuan` | Teks (max 50 char) | Satuan kerja pekerjaan | AHSPReferensi |

## 📝 Contoh Format File

### **Struktur File Excel:**

```
sumber_ahsp | kode_ahsp | nama_ahsp | kategori | uraian_item | kode_item | satuan_item | koefisien
------------|-----------|-----------|----------|-------------|-----------|-------------|----------
SNI 2025    | 1.1.1     | Pek Tanah | TK       | Pekerja     | TK-001    | OH          | 0.5
            |           |           | BHN      | Semen       | BHN-001   | kg          | 10.5
            |           |           | ALT      | Molen       | ALT-001   | jam         | 0.000008
SNI 2025    | 1.1.2     | Pek Beton | TK       | Tukang      | TK-002    | OH          | 0.8
            |           |           | BHN      | Besi        | BHN-002   | kg          | 1.05
```

### **Cara Kerja Parser:**

1. **Baris dengan `kode_ahsp` + `nama_ahsp`** → Buat pekerjaan baru di `AHSPReferensi`
2. **Baris dengan data rincian** → Tambahkan ke `RincianReferensi` untuk pekerjaan aktif terakhir
3. **Kolom kosong** → Gunakan nilai dari baris sebelumnya (untuk `sumber_ahsp`)

## 🔢 Format Angka Koefisien

### **Format yang Diterima:**

| Format Input | Hasil Parsing | Keterangan |
|--------------|---------------|------------|
| `0.5` | 0.5 | Standard decimal |
| `0,5` | 0.5 | Comma sebagai decimal separator |
| `0.000008` | 0.000008 | Angka sangat kecil |
| `0,000008` | 0.000008 | Comma separator |
| `8e-05` | 0.00008 | **Scientific notation (Excel export)** ✅ |
| `1.23E-10` | 0.000000000123 | Scientific notation (uppercase) ✅ |
| `5E3` | 5000 | Scientific notation (besar) ✅ |
| `1.234,56` | 1234.56 | European format (thousand separator) |
| `1,234.56` | 1234.56 | US format (thousand separator) |

### **⚠️ Penting: Scientific Notation**

**Masalah yang Sering Terjadi:**

Ketika Anda mengetik `0,000008` di Excel:
1. ✏️ User mengetik: `0,000008`
2. 💾 Excel menyimpan: `8E-05` (scientific notation)
3. 📖 Parser membaca: `"8e-05"`
4. ✅ **Sistem sekarang menerima scientific notation!**

**Sebelum Fix:**
```
❌ Error: Baris 460: nilai koefisien '8e-05' tidak valid
```

**Setelah Fix:**
```
✅ Success: Nilai 8e-05 diterima sebagai 0.00008
```

## 🎯 Kategori Item

### **Kode Kategori yang Valid:**

| Kode | Label | Variasi yang Diterima |
|------|-------|-----------------------|
| `TK` | Tenaga Kerja | `tenaga kerja`, `tk`, `upah`, `labour` |
| `BHN` | Bahan | `bahan`, `bhn`, `material`, `materials` |
| `ALT` | Peralatan | `alat`, `alt`, `peralatan`, `equipment` |
| `LAIN` | Lainnya | `lain`, `lainnya`, `other`, `others` |

**Normalisasi Otomatis:**
- Input: `tenaga kerja` → Output: `TK`
- Input: `material` → Output: `BHN`
- Input: `equipment` → Output: `ALT`

## 📦 Contoh File Lengkap

### **Contoh 1: Format Sederhana**

```excel
sumber_ahsp | kode_ahsp | nama_ahsp        | kategori | uraian_item | satuan_item | koefisien
AHSP SNI    | A.1.1     | Pekerjaan Tanah  | TK       | Pekerja     | OH          | 0.5
            |           |                  | BHN      | Semen       | kg          | 10
            |           |                  | ALT      | Molen       | jam         | 0.25
```

### **Contoh 2: Dengan Kode Item & Klasifikasi**

```excel
sumber_ahsp | kode_ahsp | nama_ahsp | klasifikasi | sub_klasifikasi | satuan_pekerjaan | kategori | kode_item | uraian_item | satuan_item | koefisien
SNI 2025    | 1.1.1     | Pek Beton | Konstruksi  | Beton           | m3               | TK       | TK-001    | Pekerja     | OH          | 0.5
            |           |           |             |                 |                  | BHN      | BHN-001   | Semen       | kg          | 10.5
            |           |           |             |                 |                  | ALT      | ALT-001   | Molen       | jam         | 0.000008
```

### **Contoh 3: Scientific Notation (Excel Export)**

```excel
sumber_ahsp | kode_ahsp | nama_ahsp | kategori | uraian_item | satuan_item | koefisien
SNI 2025    | 2.1.1     | Cat Dinding | TK     | Tukang Cat  | OH          | 0.4
            |           |             | BHN    | Cat         | liter       | 8e-05
            |           |             | BHN    | Thinner     | liter       | 1.23E-10
```

## ✅ Validasi yang Dilakukan

### **Validasi Pekerjaan AHSP:**
- ✅ `sumber_ahsp` tidak boleh kosong
- ✅ `kode_ahsp` tidak boleh kosong (max 50 char)
- ✅ `nama_ahsp` tidak boleh kosong
- ✅ Kombinasi `sumber` + `kode_ahsp` harus unik

### **Validasi Rincian Item:**
- ✅ `kategori` harus salah satu: TK/BHN/ALT/LAIN
- ✅ `uraian_item` tidak boleh kosong
- ✅ `satuan_item` tidak boleh kosong (max 20 char)
- ✅ `koefisien` harus angka ≥ 0
- ✅ `koefisien` mendukung scientific notation ✨

### **Auto-generation:**
- 🤖 `kode_item` kosong → sistem generate otomatis (TK-0001, BHN-0002, dll)

## 🔍 Troubleshooting

### **Error: "Kolom tidak ditemukan"**

```
❌ Kolom 'kode_ahsp' tidak ditemukan. Gunakan salah satu header: kode_ahsp, kode.
```

**Solusi:**
- Pastikan header Excel menggunakan nama yang valid
- Gunakan alias yang diterima (lihat tabel di atas)
- Header tidak case-sensitive: `KODE_AHSP` = `kode_ahsp`

### **Error: "nilai koefisien tidak valid" (FIXED ✅)**

```
❌ Baris 460: nilai koefisien '8e-05' tidak valid.
```

**Penyebab:** Excel export angka sangat kecil sebagai scientific notation

**Solusi:** ✅ **Sudah diperbaiki!** Sistem sekarang menerima scientific notation.

### **Error: "sumber_ahsp kosong"**

```
❌ Baris 15: 'sumber_ahsp' kosong untuk pekerjaan 1.1.1 - Pekerjaan Tanah
```

**Solusi:**
- Isi kolom `sumber_ahsp` di baris pertama setiap pekerjaan
- Atau isi di baris pertama file, sistem akan reuse untuk baris berikutnya

## 📊 Hasil Import

Setelah import berhasil, Anda akan melihat:

```
✅ Import selesai.
   Pekerjaan baru: 15
   Pekerjaan diperbarui: 3
   Total rincian ditulis: 127
```

Data akan tersimpan di:
- **Tabel `referensi_ahspreferensi`** - 15 pekerjaan baru
- **Tabel `referensi_rincianreferensi`** - 127 rincian item (dengan foreign key ke AHSP)

## 🚀 Workflow Import

1. **Persiapan File Excel:**
   - Format kolom sesuai spesifikasi
   - Pastikan koefisien dalam format yang valid (desimal atau scientific)

2. **Upload & Preview:**
   - Upload file di halaman `/referensi/import/preview/`
   - Sistem akan parse dan tampilkan preview

3. **Review & Edit:**
   - Review data pekerjaan dan rincian
   - Edit jika ada kesalahan
   - Sistem akan re-validate perubahan

4. **Commit:**
   - Klik "Impor ke Database"
   - Data akan disimpan ke 2 tabel secara atomic (all or nothing)

## 🔧 Technical Details

**File Parser:** `referensi/services/ahsp_parser.py`

**Number Parser:** `referensi/services/import_utils.py::normalize_num()`

**Scientific Notation Support:** ✅ Added (supports `8e-05`, `1.23E-10`, etc.)

**Database Models:**
- `referensi.models.AHSPReferensi`
- `referensi.models.RincianReferensi`

**Import Writer:** `referensi/services/import_writer.py::write_parse_result_to_db()`

## 📚 Referensi

- **Column Schema:** `referensi/services/schema.py`
- **Form Validation:** `referensi/forms/preview.py`
- **View Handler:** `referensi/views/preview.py`
- **Service Layer:** `referensi/services/preview_service.py`
