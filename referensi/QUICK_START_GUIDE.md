# 🚀 Quick Start Guide - AHSP Database Management

## 📍 Access
Navigate to: **`/referensi/admin/database/`**

---

## 🎯 Quick Actions

### 1️⃣ Hapus Data Berdasarkan Sumber

```
Toolbar → Tombol Merah "Hapus Berdasarkan Sumber"
│
├─ Pilih Sumber (dropdown) ATAU Ketik File Sumber
├─ Klik "Preview" → Lihat ringkasan data yang akan dihapus
└─ Klik "Hapus Data" → Konfirmasi → ✅ Done!
```

**⚠️ WARNING**: Operasi ini TIDAK BISA di-undo!

---

### 2️⃣ Sort Tabel (Urutkan Data)

```
Klik Header Kolom (yang ada icon ⇅)
│
├─ Klik 1x → Sort A-Z (↑)
└─ Klik 2x → Sort Z-A (↓)
```

**Tip**: Semua kolom bisa di-sort kecuali "Rincian" dan "Status"

---

### 3️⃣ Edit & Save dengan Tracking

```
1. Edit field apapun di tabel
   └─ Field berubah KUNING 🟨 (menandakan ada perubahan)

2. Button "Simpan" berubah KUNING dengan animasi
   └─ Menandakan ada perubahan yang belum disimpan

3. Klik "Simpan Perubahan"
   └─ Popup konfirmasi muncul
   └─ Klik "OK" → ✅ Tersimpan!
```

**Benefit**: Tidak akan accidental save jika tidak ada perubahan!

---

## 🎨 Visual Indicators

| Warna/Icon | Artinya |
|------------|---------|
| 🟨 Field Kuning | Field telah dimodifikasi, belum disimpan |
| 🟨 Button Kuning + Animasi | Ada perubahan yang belum disimpan |
| 🔵 Icon Biru (↑/↓) | Kolom sedang aktif di-sort |
| 🟠 Row Kuning | Data memiliki anomali (koefisien 0, satuan kosong, dll) |
| ✅ Badge Hijau | Data normal, tidak ada masalah |

---

## ⌨️ Keyboard Tips

- **Tab**: Navigate antar field
- **Enter**: Submit form (setelah edit)
- **Esc**: Close modal

---

## 📊 Tabs Explanation

### Tab "Pekerjaan AHSP"
- Menampilkan master data pekerjaan
- Edit: Nama, Klasifikasi, Satuan, dll.
- Sortable: Semua kolom kecuali "Rincian" & "Status"

### Tab "Rincian Item"
- Menampilkan detail item per pekerjaan
- Edit: Kategori, Kode Item, Uraian, Satuan, Koefisien
- Filter by: Pekerjaan, Kategori, Keyword

---

## 🔍 Filter Data

### Tab Pekerjaan
```
Filter Options:
├─ Search: Kode/Nama pekerjaan
├─ Sumber: Dropdown sumber data
├─ Klasifikasi: Dropdown klasifikasi
├─ Kategori Rincian: Filter pekerjaan yang punya rincian kategori tertentu
└─ Anomali Only: Checkbox untuk tampilkan data bermasalah saja
```

### Tab Rincian
```
Filter Options:
├─ Search: Kode/Uraian item
├─ Pekerjaan: Dropdown pekerjaan
└─ Kategori: TK/BHN/ALT/LAIN
```

---

## ⚡ Pro Tips

1. **Gunakan Sort untuk Cepat Menemukan Data**
   - Contoh: Sort by "Sumber" untuk grup data berdasarkan sumber

2. **Gunakan Anomali Filter untuk QA**
   - Check data dengan koefisien 0 atau satuan kosong

3. **Bulk Delete untuk Cleanup**
   - Hapus data import yang salah berdasarkan file sumber

4. **Edit Multiple Rows Sekaligus**
   - Edit beberapa baris, lalu save sekaligus (track semua perubahan)

5. **Preview Before Delete**
   - SELALU preview dulu sebelum delete untuk avoid kesalahan

---

## 🆘 Troubleshooting

### Problem: "Field tidak bisa diedit"
- ✅ Check: Field readonly (Kode AHSP, Sumber)
- ✅ Solution: Field dengan `readonly` memang tidak bisa diedit untuk menjaga integritas data

### Problem: "Button Hapus tidak muncul"
- ✅ Check: User permissions
- ✅ Solution: Minta admin untuk grant permission `referensi.delete_ahspreferensi`

### Problem: "Sort tidak bekerja"
- ✅ Check: Browser console untuk error
- ✅ Solution: Hard refresh (Ctrl+F5) untuk reload JavaScript

### Problem: "Perubahan tidak tersimpan"
- ✅ Check: Apakah muncul error di form?
- ✅ Solution: Pastikan semua field required terisi dan valid

---

## 🎓 Best Practices

1. ✅ **Selalu Preview sebelum Bulk Delete**
2. ✅ **Review perubahan sebelum Save**
3. ✅ **Gunakan Filter untuk batasi data yang ditampilkan**
4. ✅ **Sort untuk identifikasi pola/anomali**
5. ✅ **Backup database sebelum operasi besar**

---

## 📞 Need Help?

Contact: IT Support / Database Administrator

---

**Version**: 1.0.0 | **Last Updated**: 2025-11-03
