# 🐛 Mass Edit Debugging Guide

## Masalah yang Dilaporkan
- User mengedit nama project
- Klik "Simpan Semua"
- Alert muncul: "Changes you made may not be saved"
- Perubahan tidak tersimpan ke database

---

## 🔍 Cara Melakukan Debugging

### **Langkah 1: Buka Browser Developer Tools**

1. **Chrome/Edge/Brave:**
   - Tekan `F12` atau `Ctrl + Shift + I`
   - Atau klik kanan → Inspect

2. **Firefox:**
   - Tekan `F12` atau `Ctrl + Shift + K`

3. **Safari:**
   - Enable Developer Menu: Safari → Preferences → Advanced → "Show Develop menu"
   - Tekan `Cmd + Option + I`

---

### **Langkah 2: Buka Tab Console**

Di Developer Tools, klik tab **Console**. Ini adalah tempat semua log JavaScript muncul.

---

### **Langkah 3: Reproduksi Masalah**

1. Refresh halaman dashboard (untuk clear log)
2. Centang checkbox project yang ingin diedit
3. Klik tombol **"Mass Edit"**
4. Edit nama project (atau field lainnya)
5. Klik **"Simpan Semua"**
6. **PERHATIKAN CONSOLE!** Akan muncul log seperti ini:

```
📤 Sending bulk update...
Changes to send: [{id: 123, nama: "Project Baru", ...}]
CSRF Token: Found
Request body: {
  "changes": [
    {
      "id": 123,
      "nama": "Project Baru",
      ...
    }
  ]
}
Response status: 200
Response ok: true
Response data: {success: true, updated_count: 1}
✅ Success! Updated count: 1
```

---

### **Langkah 4: Identifikasi Error**

#### **Scenario A: CSRF Token NOT FOUND**
```
CSRF Token: NOT FOUND
❌ Error saving changes: ...
```

**Penyebab:** Django CSRF token tidak tersedia di halaman

**Solusi:**
```django
<!-- Pastikan ada di template -->
{% csrf_token %}
```

---

#### **Scenario B: HTTP Error 403 Forbidden**
```
Response status: 403
Response ok: false
❌ Error: HTTP 403: Forbidden (CSRF verification failed)
```

**Penyebab:** CSRF token tidak valid atau sudah expired

**Solusi:**
1. Refresh halaman (Ctrl+R)
2. Coba lagi

---

#### **Scenario C: HTTP Error 404 Not Found**
```
Response status: 404
Response ok: false
❌ Error: HTTP 404: Not Found
```

**Penyebab:** URL endpoint `/dashboard/mass-edit-bulk/` tidak ditemukan

**Solusi:**
```bash
# Cek URL routing
python manage.py show_urls | grep mass-edit
```

---

#### **Scenario D: JSON Parse Error**
```
Response status: 200
❌ Error: Unexpected token < in JSON at position 0
```

**Penyebab:** Server mengembalikan HTML (bukan JSON), biasanya error page Django

**Solusi:**
1. Lihat tab **Network** di DevTools
2. Klik request `mass-edit-bulk`
3. Lihat **Response** tab
4. Cari error message Django

---

#### **Scenario E: Backend Error**
```
Response status: 500
Response ok: false
Response data: {success: false, message: "Error updating projects: ..."}
```

**Penyebab:** Error di Django view (database, validation, etc)

**Solusi:** Lihat Django logs (Langkah 5)

---

#### **Scenario F: Network Error**
```
❌ Error saving changes: TypeError: Failed to fetch
```

**Penyebab:**
- Server Django tidak running
- Network connection problem
- CORS issue

**Solusi:**
```bash
# Pastikan Django server running
python manage.py runserver
```

---

### **Langkah 5: Check Django Logs**

Buka terminal tempat Django server running, cari log seperti ini:

```
📥 Mass edit bulk update request received
User: admin
Method: POST
Request body: b'{"changes":[{"id":123,"nama":"Project Baru"}]}'
Parsed data: {'changes': [{'id': 123, 'nama': 'Project Baru'}]}
Number of changes: 1
Processing change 1/1: {'id': 123, 'nama': 'Project Baru'}
Found project: Old Name (ID: 123)
Saving project 123...
✅ Successfully saved project 123
✅ All changes saved successfully. Total updated: 1
```

**Jika ada error:**
```
❌ Unexpected error: ...
Traceback (most recent call last):
  File "...", line ..., in mass_edit_bulk_update
    ...
```

Ini akan menunjukkan error spesifik yang terjadi.

---

### **Langkah 6: Check Network Tab**

1. Di DevTools, klik tab **Network**
2. Refresh halaman
3. Lakukan mass edit lagi
4. Cari request `mass-edit-bulk`
5. Klik request tersebut
6. Lihat:
   - **Headers:** Method, Status Code, Request Headers
   - **Payload:** Data yang dikirim
   - **Response:** Data yang diterima

---

## 🔧 Common Issues & Solutions

### **Issue 1: Changes Not Sent**
**Symptom:** Log "Changes to send: []" (array kosong)

**Cause:** Tidak ada cell yang ter-mark sebagai edited

**Solution:** Pastikan user benar-benar edit field (bukan hanya klik)

---

### **Issue 2: Project ID Missing**
**Symptom:** Log "Skipping change: No project ID"

**Cause:** Data attributes di table row tidak ada

**Solution:** Cek template `_project_stats_and_table.html`:
```html
<tr data-project-id="{{ project.pk }}" ...>
```

---

### **Issue 3: Field Not Updated**
**Symptom:** Django log tidak show field change

**Cause:** Field name mismatch antara JavaScript dan Django

**Solution:** Cek field mapping di `mass-edit-toggle.js`:
```javascript
ALL_FIELDS = [
  { name: 'nama', ... },  // Must match Django model field
]
```

---

### **Issue 4: Database Not Saving**
**Symptom:** Django log shows "Saving project..." tapi tidak ada error, tapi database tidak berubah

**Cause:** Transaction rollback atau validation error

**Solution:**
1. Check Django model validation
2. Check required fields
3. Add `try-except` around `project.save()`

---

## 📋 Checklist Debugging

- [ ] Browser console terbuka
- [ ] Console menunjukkan "📤 Sending bulk update..."
- [ ] CSRF Token: Found
- [ ] Request body berisi changes yang benar
- [ ] Response status: 200
- [ ] Response data: {success: true}
- [ ] Django log menunjukkan "📥 Mass edit bulk update request received"
- [ ] Django log menunjukkan "✅ Successfully saved project"
- [ ] Database benar-benar berubah

---

## 🚀 Next Steps

Setelah menjalankan debugging di atas, **copy-paste semua log dari Console** dan kirim ke developer dengan informasi:

1. **Browser Console Log** (copy semua dari console)
2. **Django Server Log** (copy dari terminal)
3. **Network Tab Screenshot** (screenshot request/response)
4. **Deskripsi langkah yang dilakukan**

Dengan informasi ini, developer bisa mengidentifikasi masalah dengan tepat.

---

## 📞 Developer Contact

Jika masih mengalami masalah setelah debugging, hubungi developer dengan menyertakan:
- Screenshot console
- Django log
- Langkah-langkah yang dilakukan
- Expected vs Actual result

---

**Last Updated:** 2025-11-07
