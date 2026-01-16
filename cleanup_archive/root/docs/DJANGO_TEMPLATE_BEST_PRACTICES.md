# Django Template Best Practices - Mencegah Error Formatting

## 🚨 Masalah Umum yang Terjadi

### **Error: "Invalid block tag 'endblock', expected 'endfor'"**

**Penyebab:** Django template tags terpisah menjadi beberapa baris oleh auto-formatter (Prettier, Beautify, dll).

**Contoh Kode yang SALAH:**
```django
{% for err in form.errors %}<div>{{ err }}</div>{% endfor
%}
```

**Contoh Kode yang BENAR:**
```django
{% for err in form.errors %}<div>{{ err }}</div>{% endfor %}
```

---

## ✅ Solusi Permanen

### **1. Proteksi File dengan Prettier Comments**

Tambahkan di **AWAL** file template:
```html
<!-- prettier-ignore-start -->
```

Tambahkan di **AKHIR** file template:
```html
<!-- prettier-ignore-end -->
```

### **2. Konfigurasi VS Code Settings**

File: `.vscode/settings.json`

```json
{
  "editor.formatOnSave": true,

  "[django-html]": {
    "editor.defaultFormatter": null,
    "editor.formatOnSave": false,
    "javascript.validate.enable": false,
    "editor.wordWrap": "off",
    "editor.rulers": [120]
  },

  "files.associations": {
    "**/templates/**/*.html": "django-html"
  }
}
```

### **3. Proteksi dengan .prettierignore**

File: `.prettierignore`

```
# Django Templates - Contains {% %} and {{ }} syntax that Prettier breaks
**/templates/**/*.html
```

### **4. Install Extension yang Tepat**

File: `.vscode/extensions.json`

```json
{
  "recommendations": [
    "batisteo.vscode-django",
    "esbenp.prettier-vscode",
    "monosans.djlint"
  ]
}
```

---

## 📋 Aturan Django Template Tags

### **✅ BOLEH (Valid Syntax):**

```django
<!-- 1. Tag dalam satu baris -->
{% for item in items %}{{ item }}{% endfor %}

<!-- 2. Tag terpisah per elemen (tapi tag sendiri lengkap) -->
{% for item in items %}
  <div>{{ item }}</div>
{% endfor %}

<!-- 3. Filter tanpa spasi berlebih -->
{{ variable|default:"[]"|safe }}
```

### **❌ JANGAN (Invalid Syntax):**

```django
<!-- 1. Tag terpisah menjadi 2 baris -->
{% for item in items %}{{ item }}{% endfor
%}

<!-- 2. Spasi setelah colon di filter -->
{{ variable | default: "[]" | safe }}

<!-- 3. Tag terpisah dengan newline -->
{{ variable|default:"[]"|safe
}}
```

---

## 🛡️ Checklist Sebelum Save File

- [ ] Semua `{% for %}` memiliki `{% endfor %}` yang lengkap dalam satu baris
- [ ] Semua `{% if %}` memiliki `{% endif %}` yang lengkap
- [ ] Semua `{% block %}` memiliki `{% endblock %}` yang lengkap
- [ ] Filter tidak memiliki spasi berlebih (`|filter:value` bukan `| filter: value`)
- [ ] Tag `{{ variable }}` lengkap dalam satu baris
- [ ] File diawali dengan `<!-- prettier-ignore-start -->`
- [ ] File diakhiri dengan `<!-- prettier-ignore-end -->`

---

## 🔧 Quick Fix untuk File yang Rusak

### **Menggunakan Find & Replace (Regex):**

**VS Code → Find & Replace (Ctrl+H)**

1. **Enable Regex** (ikon `.*` di kotak find)

2. **Pattern 1: Fix endfor terpisah**
   - Find: `{%\s+endfor\s+%}`
   - Replace: `{% endfor %}`

3. **Pattern 2: Fix endif terpisah**
   - Find: `{%\s+endif\s+%}`
   - Replace: `{% endif %}`

4. **Pattern 3: Fix endblock terpisah**
   - Find: `{%\s+endblock\s+%}`
   - Replace: `{% endblock %}`

---

## 🎯 Workflow yang Aman

### **Saat Edit Django Template:**

1. **JANGAN** gunakan auto-format (Shift+Alt+F)
2. **JANGAN** save dengan "Format on Save" aktif
3. **Manual indentation** untuk readability
4. **Test rendering** setelah perubahan besar
5. **Commit** perubahan secara berkala

### **Saat Formatter Tidak Bisa Dihindari:**

Wrap bagian yang rawan rusak dengan comment:

```html
<table>
  <!-- prettier-ignore -->
  <tr>
    {% for form in formset %}
      <td>{{ form.field }}</td>
      {% for err in form.field.errors %}
        <div>{{ err }}</div>
      {% endfor %}
    {% endfor %}
  </tr>
</table>
```

---

## 📚 Referensi

- Django Template Language: https://docs.djangoproject.com/en/5.0/ref/templates/language/
- Prettier Ignore: https://prettier.io/docs/en/ignore.html
- djLint Documentation: https://djlint.com/

---

## ⚠️ PERINGATAN PENTING

**JANGAN PERNAH:**
- Manual break Django template tags menjadi beberapa baris
- Gunakan Prettier/Beautify langsung pada Django templates
- Copy-paste dari browser yang bisa merusak format
- Undo tanpa memeriksa kembali struktur tags

**SELALU:**
- Pastikan opening dan closing tags dalam satu baris
- Test template di browser setelah perubahan
- Backup file sebelum formatting besar-besaran
- Gunakan version control (Git) untuk rollback
