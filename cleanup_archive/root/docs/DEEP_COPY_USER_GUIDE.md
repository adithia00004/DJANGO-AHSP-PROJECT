# Deep Copy Project - User Guide

## Overview

Fitur **Deep Copy Project** memungkinkan Anda untuk menduplikasi project yang sudah ada beserta seluruh data dan konfigurasi. Fitur ini sangat berguna untuk:

- Membuat project baru berdasarkan template project yang sudah ada
- Membuat variasi project dengan parameter berbeda
- Backup project dengan copy lengkap
- Menggunakan kembali struktur pekerjaan untuk project serupa

## Apa yang Dicopy?

### ✅ Data yang Dicopy (Deep Copy)

Deep copy akan menyalin **SEMUA** data berikut:

#### 1. **Project Information**
- Nama project (bisa diubah)
- Lokasi project
- Tanggal mulai (bisa diubah)
- Durasi
- Status

#### 2. **List Pekerjaan**
- Klasifikasi Pekerjaan
- Sub Klasifikasi Pekerjaan
- Pekerjaan dengan semua atribut:
  - Kode RAB
  - Uraian
  - Satuan
  - Source type (custom/ref/ref_modified)
  - Ordering index

#### 3. **Volume Pekerjaan**
- Formula perhitungan volume
- Volume calculated
- Volume manual
- Flag use_manual

#### 4. **Parameter Project** ⭐ NEW (FASE 3)
- Semua parameter untuk formula (panjang, lebar, dll)
- Nilai parameter
- Label dan unit
- Deskripsi parameter

#### 5. **Harga Items**
- Master harga items per kategori:
  - Tenaga Kerja (TK)
  - Bahan (BHN)
  - Peralatan (ALT)
  - Lain-lain (LAIN)
- Kode item
- Uraian
- Satuan
- Harga satuan

#### 6. **Template AHSP**
- Detail AHSP untuk setiap pekerjaan
- Koefisien
- Referensi ke harga item
- Bundle items (kategori LAIN dengan ref_ahsp)

#### 7. **Rincian AHSP**
- Override koefisien per pekerjaan
- Override harga per pekerjaan
- Override keuntungan per pekerjaan

#### 8. **Project Pricing**
- PPN
- Overhead
- Keuntungan
- Markup percent

#### 9. **Jadwal Pelaksanaan** (Opsional)
- Tahapan pelaksanaan
- Assignment pekerjaan ke tahapan
- Proporsi volume per tahapan
- Tanggal mulai & selesai tahapan

### ❌ Data yang TIDAK Dicopy

- Owner project (copy akan menjadi milik user yang melakukan copy)
- Timestamps (created_at, updated_at) - akan dibuat baru
- Project ID (akan di-generate otomatis)

## Cara Menggunakan

### Step 1: Buka Project Detail

1. Login ke aplikasi
2. Pilih project yang ingin dicopy dari dashboard
3. Masuk ke halaman detail project

### Step 2: Klik Tombol "Copy Project"

Di halaman detail project, Anda akan melihat tombol **"Copy Project"** dengan icon copy:

```
[Export PDF] [Copy Project] [Edit] [Hapus]
```

Klik tombol tersebut untuk membuka modal dialog.

### Step 3: Isi Form Copy Project

Modal akan menampilkan form dengan 3 field:

#### 1. **Nama Project Baru** (Required) ⚠️
- Field ini **wajib** diisi
- Default: `[Nama Project Asli] (Copy)`
- Contoh: `Pembangunan Gedung A (Copy)`

**Tips:** Berikan nama yang jelas dan deskriptif untuk membedakan dari project asli.

#### 2. **Tanggal Mulai Baru** (Optional)
- Field ini **opsional**
- Format: YYYY-MM-DD (date picker)
- Jika dikosongkan: akan menggunakan tanggal mulai dari project asli

**Use Case:**
- Kosongkan jika ingin menggunakan timeline yang sama
- Isi jika project copy akan dimulai di tanggal berbeda

#### 3. **Copy Jadwal Pelaksanaan** (Optional)
- Checkbox, default: **✓ Checked**
- Jika dicentang: Tahapan dan jadwal pekerjaan akan dicopy
- Jika tidak dicentang: Jadwal tidak dicopy, hanya data project dan pekerjaan

**Use Case:**
- ✓ Centang jika ingin copy lengkap termasuk jadwal
- ☐ Tidak centang jika ingin membuat jadwal baru dari awal

### Step 4: Klik "Copy Project"

1. Review semua data yang diisi
2. Klik tombol **"Copy Project"** (biru dengan icon copy)
3. Progress indicator akan muncul: "Sedang melakukan copy project..."

### Step 5: Redirect Otomatis

Setelah copy berhasil:
- Muncul pesan sukses: "✓ Berhasil! Project berhasil dicopy"
- Otomatis redirect ke halaman detail project **baru** (dalam 1 detik)
- Anda bisa langsung mulai bekerja dengan project copy

## Copy Statistics

Setelah copy berhasil, API akan mengembalikan statistics berisi jumlah data yang dicopy:

```json
{
  "parameter_copied": 5,
  "klasifikasi_copied": 3,
  "subklasifikasi_copied": 8,
  "pekerjaan_copied": 25,
  "volume_copied": 25,
  "harga_item_copied": 50,
  "ahsp_template_copied": 120,
  "tahapan_copied": 4,
  "jadwal_copied": 25
}
```

## Error Handling

### Possible Errors:

#### 1. **"Nama project tidak boleh kosong"**
- **Penyebab:** Field "Nama Project Baru" tidak diisi
- **Solusi:** Isi nama project baru

#### 2. **"Field 'new_tanggal_mulai' must be in YYYY-MM-DD format"**
- **Penyebab:** Format tanggal salah
- **Solusi:** Gunakan date picker atau format YYYY-MM-DD (contoh: 2025-06-15)

#### 3. **"Deep copy failed: ..."**
- **Penyebab:** Error di server saat copy (database error, permission, dll)
- **Solusi:**
  - Refresh halaman dan coba lagi
  - Jika masih gagal, hubungi admin
  - Check browser console untuk detail error

#### 4. **"Invalid JSON payload"**
- **Penyebab:** Request format tidak valid (jarang terjadi)
- **Solusi:** Refresh halaman dan coba lagi

## Advanced Use Cases

### Use Case 1: Template Project untuk Project Serupa

**Scenario:** Anda sering membuat project pembangunan gedung dengan struktur pekerjaan yang sama.

**Steps:**
1. Buat 1 project "template" dengan:
   - Seluruh list pekerjaan standar
   - Harga items standar
   - Template AHSP lengkap
   - Parameter default
2. Setiap kali ada project baru:
   - Copy project template
   - Ubah nama sesuai project baru
   - Ubah tanggal mulai
   - Adjust parameter sesuai kebutuhan (panjang, lebar, dll)
   - Update volume dan harga jika perlu

**Benefit:** Hemat waktu setup project baru dari 2-3 hari menjadi 30 menit.

### Use Case 2: Membuat Variasi Project dengan Parameter Berbeda

**Scenario:** Anda ingin membandingkan 3 skenario pembangunan dengan parameter berbeda.

**Steps:**
1. Buat project baseline
2. Copy 3 kali dengan nama:
   - "Project A - Skenario Minimal"
   - "Project A - Skenario Standar"
   - "Project A - Skenario Premium"
3. Untuk setiap copy, adjust:
   - Parameter volume (panjang, lebar, tinggi)
   - Harga items (material grade berbeda)
   - Keuntungan/margin
4. Bandingkan Rekap RAB dari 3 skenario

**Benefit:** Analisis multi-skenario tanpa mengubah project asli.

### Use Case 3: Backup Project Sebelum Perubahan Besar

**Scenario:** Anda akan melakukan perubahan besar pada project (ubah struktur pekerjaan, harga, dll).

**Steps:**
1. Copy project dengan nama: "[Nama Project] (Backup YYYY-MM-DD)"
2. Lakukan perubahan pada project asli
3. Jika perubahan tidak sesuai, Anda masih punya backup

**Benefit:** Safety net untuk eksperimen tanpa resiko kehilangan data.

## Performance Notes

### Copy Speed

Waktu copy tergantung ukuran project:

| Ukuran Project | Estimated Time |
|---------------|----------------|
| Small (< 20 pekerjaan) | < 2 detik |
| Medium (20-100 pekerjaan) | 2-5 detik |
| Large (100-500 pekerjaan) | 5-15 detik |
| Very Large (> 500 pekerjaan) | 15-30 detik |

**Note:** Copy menggunakan database transaction, jadi jika gagal di tengah jalan, semua perubahan akan di-rollback (tidak ada data corrupt).

### Database Load

Deep copy melakukan multiple insert operations:
- 1 project
- 1 pricing (optional)
- N parameters
- N klasifikasi
- N subklasifikasi
- N pekerjaan
- N volume
- N harga_item
- N detail_ahsp
- N tahapan (optional)
- N jadwal (optional)

Untuk project dengan 100 pekerjaan dan 300 detail AHSP, total ~600 insert operations.

**Recommendation:** Jangan spam copy button. Tunggu hingga proses selesai.

## Troubleshooting

### Problem: Modal tidak muncul saat klik button

**Possible Causes:**
- JavaScript error
- Bootstrap modal tidak loaded

**Solutions:**
1. Refresh halaman (Ctrl+F5)
2. Check browser console untuk error
3. Clear browser cache
4. Pastikan JavaScript tidak di-block

### Problem: Copy berhasil tapi tidak redirect

**Possible Causes:**
- JavaScript error saat redirect
- URL project baru tidak valid

**Solutions:**
1. Cek browser console untuk error
2. Manual refresh ke dashboard
3. Check project baru sudah muncul di list

### Problem: Copy sangat lambat (> 1 menit)

**Possible Causes:**
- Project sangat besar (> 1000 pekerjaan)
- Database slow
- Server overload

**Solutions:**
1. Tunggu hingga selesai (jangan close modal)
2. Jika timeout, coba lagi saat server tidak sibuk
3. Hubungi admin jika konsisten lambat

## API Documentation (for Developers)

### Endpoint

```
POST /detail-project/api/project/<project_id>/deep-copy/
```

### Request Headers

```
Content-Type: application/json
X-CSRFToken: <csrf_token>
```

### Request Body

```json
{
  "new_name": "Project Copy Name",
  "new_tanggal_mulai": "2025-06-01",
  "copy_jadwal": true
}
```

### Response Success (201)

```json
{
  "ok": true,
  "new_project": {
    "id": 123,
    "nama_project": "Project Copy Name",
    "owner_id": 1,
    "lokasi_project": "Jakarta",
    "tanggal_mulai": "2025-06-01",
    "durasi": 90,
    "status": "active"
  },
  "stats": {
    "parameter_copied": 2,
    "klasifikasi_copied": 3,
    "subklasifikasi_copied": 5,
    "pekerjaan_copied": 15,
    "volume_copied": 15,
    "harga_item_copied": 20,
    "ahsp_template_copied": 45,
    "rincian_ahsp_copied": 0,
    "tahapan_copied": 4,
    "jadwal_copied": 15
  }
}
```

### Response Error (400)

```json
{
  "ok": false,
  "error": "Field 'new_name' is required and cannot be empty"
}
```

### Response Error (500)

```json
{
  "ok": false,
  "error": "Deep copy failed: [error message]"
}
```

## FAQ

### Q: Apakah copy mempengaruhi project asli?

**A:** Tidak. Copy adalah operasi read-only terhadap project asli. Project asli tidak akan berubah sama sekali.

### Q: Apakah bisa copy ke user lain?

**A:** Saat ini, copy selalu menjadi milik user yang melakukan copy. Fitur share/copy ke user lain ada di roadmap (FASE 3.2+).

### Q: Apakah bisa undo copy?

**A:** Tidak ada undo. Jika ingin menghapus project copy, gunakan tombol "Hapus" di project detail.

### Q: Berapa kali bisa copy 1 project?

**A:** Unlimited. Anda bisa copy project sebanyak yang diperlukan.

### Q: Apakah ada limit ukuran project untuk copy?

**A:** Tidak ada hard limit, tapi sangat disarankan:
- Optimal: < 200 pekerjaan
- Maximum: < 1000 pekerjaan

### Q: Apakah bisa copy project yang statusnya inactive/archive?

**A:** Ya, bisa. Status tidak mempengaruhi kemampuan copy.

### Q: Apakah parameter formula ikut ter-copy?

**A:** Ya! Sejak FASE 3, semua ProjectParameter (panjang, lebar, dll) otomatis ter-copy.

## Version History

| Version | Release Date | Changes |
|---------|--------------|---------|
| 1.0 | 2025-11-06 | Initial release - FASE 3.1 Deep Copy Core |

## Support

Jika mengalami masalah atau punya pertanyaan:

1. Check dokumentasi ini terlebih dahulu
2. Check FASE_3_IMPLEMENTATION_PLAN.md untuk detail teknis
3. Hubungi admin/developer team

---

**Last Updated:** 2025-11-06
**Author:** Claude (AI Assistant)
**Status:** Production Ready ✅
