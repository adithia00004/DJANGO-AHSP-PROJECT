# 📚 AHSP Database Management - Fitur Baru

## 🎯 Overview

Dokumentasi ini menjelaskan fitur-fitur baru yang ditambahkan ke halaman **Kelola Database AHSP** (`/referensi/admin/database/`).

---

## ✨ Fitur yang Ditambahkan

### 1. **Bulk Delete by Source** 🗑️

#### Deskripsi
Menghapus data pekerjaan AHSP dan rinciannya berdasarkan filter **Sumber** atau **File Sumber**.

#### Cara Menggunakan
1. Klik tombol **"Hapus Berdasarkan Sumber"** (warna merah) di toolbar
2. Pilih filter:
   - **Sumber**: Pilih dari dropdown (contoh: "AHSP SNI 2025")
   - **File Sumber**: Ketik nama file (case-insensitive)
3. Klik **"Preview"** untuk melihat data yang akan dihapus
4. Review ringkasan:
   - Jumlah pekerjaan yang akan dihapus
   - Jumlah rincian yang akan dihapus
   - Sumber dan file yang terdampak
5. Klik **"Hapus Data"** dan konfirmasi

#### Teknologi
- **Backend (Python)**:
  - Service: `AdminPortalService.get_delete_preview()` & `bulk_delete_by_source()`
  - API: `/referensi/api/delete/preview` & `/referensi/api/delete/execute`
- **Frontend (JavaScript)**:
  - Modal Bootstrap
  - Fetch API untuk AJAX calls
  - Real-time preview

#### Keamanan
- ✅ Requires `referensi.delete_ahspreferensi` permission
- ✅ CSRF token validation
- ✅ Konfirmasi ganda (modal + browser confirm)
- ✅ Preview sebelum delete
- ✅ Cascade delete (rincian otomatis terhapus)

---

### 2. **Table Sorting** 🔄

#### Deskripsi
Sorting client-side pada kolom tabel dengan klik header.

#### Cara Menggunakan
1. Klik pada header kolom yang memiliki icon ⇅
2. Klik pertama: sort **ascending** (A→Z)
3. Klik kedua: sort **descending** (Z→A)
4. Icon berubah menjadi ↑ (asc) atau ↓ (desc) dengan warna biru

#### Kolom yang Sortable

**Tab Pekerjaan AHSP:**
- Kode AHSP
- Nama Pekerjaan
- Klasifikasi
- Sub-klasifikasi
- Satuan
- Sumber
- File Sumber

**Tab Rincian Item:**
- Pekerjaan
- Kategori
- Kode Item
- Uraian
- Satuan
- Koefisien

#### Teknologi
- **JavaScript**: Client-side sorting (fast, no server round-trip)
- **Algorithm**: Natural sort dengan support untuk angka dan teks
- **Performance**: O(n log n) - efficient untuk ribuan rows

---

### 3. **Change Tracking & Save Confirmation** 💾

#### Deskripsi
Melacak perubahan yang dilakukan admin pada form dan memberikan konfirmasi sebelum save.

#### Cara Kerja
1. **Auto-detect changes**:
   - Saat admin mengedit field (input, select, textarea)
   - Field yang berubah mendapat highlight **kuning** (`.is-modified`)

2. **Visual feedback**:
   - Field modified: border kuning + background kuning muda
   - Button "Simpan" berubah jadi **warning** (kuning) dengan animasi pulse
   - Icon berubah dari 💾 ke ⚠️

3. **Save confirmation**:
   - Klik "Simpan Perubahan"
   - Popup muncul dengan summary: "Anda akan menyimpan X perubahan"
   - Konfirmasi → Data tersimpan
   - Batal → Tidak ada perubahan

4. **Validation**:
   - Jika tidak ada perubahan → Muncul notifikasi "Tidak ada perubahan untuk disimpan"
   - Form tidak akan submit

#### Teknologi
- **JavaScript**:
  - `Map` untuk menyimpan nilai original
  - `Set` untuk track changed fields
  - Event listeners: `change` & `input`
- **CSS**:
  - `.is-modified` class untuk visual feedback
  - Animation `@keyframes pulse-warning`

#### Benefits
- ✅ Mencegah accidental save tanpa perubahan
- ✅ Visual feedback jelas untuk admin
- ✅ Audit trail (admin tahu apa yang diubah)
- ✅ Reduce unnecessary database writes

---

## 🛠️ Architecture

### Hybrid Approach

Fitur ini menggunakan **kombinasi Python (backend) dan JavaScript (frontend)** untuk pengalaman terbaik:

```
┌─────────────────────────────────────────────────────┐
│                    USER INTERFACE                    │
│  (HTML Template + Bootstrap + CSS)                  │
└──────────────┬──────────────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
   JavaScript        Python/Django
   (Frontend)        (Backend)
       │                │
       │                │
   ┌───▼────────┐   ┌───▼──────────┐
   │  UI Logic  │   │ Business     │
   │  - Sorting │   │ Logic        │
   │  - Track   │   │ - Delete     │
   │  - Modal   │   │ - Validate   │
   │  - Toast   │   │ - DB Ops     │
   └────────────┘   └──────────────┘
```

### Files Modified/Created

#### Python Files
- ✅ `referensi/services/admin_service.py` - Added bulk delete methods
- ✅ `referensi/views/api/bulk_ops.py` - **NEW** API endpoints
- ✅ `referensi/urls.py` - Added API routes

#### JavaScript Files
- ✅ `referensi/static/referensi/js/ahsp_database.js` - **NEW** All client-side logic

#### HTML Files
- ✅ `referensi/templates/referensi/ahsp_database.html` - Added modal, sortable headers, script tags

#### CSS Files
- ✅ `referensi/static/referensi/css/ahsp_database.css` - Added styles for new features

---

## 🔒 Permissions Required

Untuk menggunakan fitur-fitur ini, user harus memiliki permissions:

| Fitur | Permission |
|-------|-----------|
| View Database | `referensi.view_ahspreferensi` |
| Edit Records | `referensi.change_ahspreferensi` |
| **Bulk Delete** | `referensi.delete_ahspreferensi` |
| Table Sort | (No special permission - available if can view) |
| Change Tracking | (No special permission - available if can edit) |

---

## 📊 Performance Considerations

### Client-side Sorting
- ✅ **Fast**: No server requests
- ✅ **Instant**: Sorts in milliseconds
- ⚠️ **Limitation**: Only sorts currently loaded rows (max 1000 jobs or 5000 items)

### Change Tracking
- ✅ **Lightweight**: Uses native `Map` and `Set`
- ✅ **Memory efficient**: Only stores changed field keys
- ✅ **No network overhead**: All tracking is client-side

### Bulk Delete
- ✅ **Preview first**: Prevents accidental deletes
- ✅ **Efficient**: Uses Django ORM bulk delete
- ✅ **Cascade**: Database handles cascade automatically
- ⚠️ **Cache invalidation**: Clears cache after delete

---

## 🧪 Testing Checklist

### Bulk Delete
- [ ] Preview shows correct count
- [ ] Filter by sumber works
- [ ] Filter by source_file works
- [ ] Delete confirmation required
- [ ] Success message shows after delete
- [ ] Page reloads after delete
- [ ] Data actually deleted from database
- [ ] Permission check works (non-authorized users can't delete)

### Table Sorting
- [ ] Click header sorts ascending
- [ ] Click again sorts descending
- [ ] Icon changes correctly (↑/↓)
- [ ] Sorts correctly for text columns
- [ ] Sorts correctly for number columns
- [ ] Works on both tabs (Jobs & Items)
- [ ] Formset inputs maintain values after sort

### Change Tracking
- [ ] Field highlights yellow when changed
- [ ] Button turns yellow when changes exist
- [ ] Confirmation modal shows on save
- [ ] Shows "no changes" when nothing changed
- [ ] Resets after successful save
- [ ] Works across page reloads

---

## 🚀 Future Enhancements

Fitur-fitur yang bisa ditambahkan di masa depan:

1. **Export to Excel**: Export filtered data
2. **Bulk Edit**: Edit multiple records at once
3. **History View**: See change history with django-simple-history
4. **Advanced Filters**: More complex filter combinations
5. **Pagination**: Server-side pagination for large datasets
6. **Keyboard Shortcuts**: Ctrl+S to save, Ctrl+Z to undo, etc.
7. **Undo/Redo**: Undo changes before save
8. **Duplicate Detection**: Warn about potential duplicates

---

## 📞 Support

Jika ada masalah atau pertanyaan:
1. Check browser console untuk error messages
2. Check Django logs untuk backend errors
3. Verify permissions di Django Admin
4. Clear browser cache jika JavaScript tidak ter-load

---

## 📝 Changelog

### v1.0.0 (2025-11-03)
- ✅ Added Bulk Delete by Source feature
- ✅ Added Table Sorting on all columns
- ✅ Added Change Tracking with visual feedback
- ✅ Added Save Confirmation modal
- ✅ Enhanced CSS with animations and responsive design

---

**Happy Managing! 🎉**
