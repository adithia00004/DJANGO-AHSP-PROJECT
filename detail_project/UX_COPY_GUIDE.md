# 📝 UX COPY GUIDE: Template AHSP, Harga Items, Rincian AHSP

## Purpose
This guide provides **user-friendly copy, tooltips, and help text** for all 3 pages to help users understand Segment D (LAIN/Bundle) workflow.

---

## 🎯 TEMPLATE AHSP PAGE

### **Page Header**
```
Title: Template AHSP
Subtitle: Definisikan komponen AHSP untuk setiap pekerjaan (TK, BHN, ALT, dan Bundle)
```

### **Segment Tabs**

#### **Tab: LAIN (Bundle)**
```html
<button class="segment-tab" data-segment="LAIN">
  📦 LAIN (Pekerjaan Gabungan)
  <span class="info-icon" data-tooltip="
    Segment LAIN digunakan untuk mereferensi pekerjaan lain sebagai 'bundle'.
    Bundle otomatis di-expand menjadi komponen TK/BHN/ALT.
    Cocok untuk pekerjaan berulang atau komposit.
  ">ℹ️</span>
</button>
```

### **Bundle Reference Field**
```html
<label for="ref-pekerjaan">
  Referensi Pekerjaan
  <span class="required">*</span>
  <span class="help-icon" data-tooltip="
    Pilih pekerjaan yang sudah memiliki komponen AHSP.
    Komponen dari pekerjaan tersebut akan otomatis ditambahkan
    ke pekerjaan ini dengan koefisien yang Anda tentukan.
  ">?</span>
</label>

<select id="ref-pekerjaan" class="form-control">
  <option value="">-- Pilih Pekerjaan --</option>
  <option value="123">PKJ.001 - Galian Tanah (5 komponen)</option>
  <option value="456" disabled>PKJ.002 - Urugan (Kosong - tidak bisa dipilih)</option>
</select>

<small class="form-text text-muted">
  💡 Tip: Pastikan pekerjaan target sudah memiliki komponen sebelum dijadikan bundle.
</small>
```

### **Koefisien Field (Bundle)**
```html
<label for="koefisien">
  Koefisien Bundle
  <span class="help-icon" data-tooltip="
    Koefisien ini akan dikalikan dengan koefisien komponen dari pekerjaan target.

    Contoh:
    - Pekerjaan Target: L.01 (koef 5.0), B.02 (koef 10.0)
    - Koefisien Bundle: 3.0
    - Hasil Ekspansi: L.01 (15.0), B.02 (30.0)
  ">?</span>
</label>

<input type="number" id="koefisien" step="0.000001" min="0" value="1.0">

<small class="form-text text-muted">
  📊 Pratinjau: Bundle akan menghasilkan ~5 komponen (sesuai pekerjaan target)
</small>
```

### **Save Button with Preview**
```html
<button class="btn btn-primary" onclick="previewBundleBeforeSave()">
  💾 Simpan & Expand Bundle
</button>

<button class="btn btn-outline-secondary" onclick="showBundlePreview()">
  👁️ Pratinjau Ekspansi
</button>
```

### **Bundle Preview Modal**
```html
<div class="modal" id="bundle-preview-modal">
  <div class="modal-header">
    <h4>👁️ Pratinjau Ekspansi Bundle</h4>
  </div>
  <div class="modal-body">
    <div class="alert alert-info">
      <strong>Bundle:</strong> {{ bundle.kode }}<br>
      <strong>Referensi:</strong> {{ ref_pekerjaan.kode }} - {{ ref_pekerjaan.uraian }}<br>
      <strong>Koefisien:</strong> {{ bundle.koefisien }}
    </div>

    <h5>Komponen yang akan ditambahkan:</h5>
    <table class="table table-sm">
      <thead>
        <tr>
          <th>Kode</th>
          <th>Uraian</th>
          <th>Koef Asli</th>
          <th>×</th>
          <th>Koef Bundle</th>
          <th>=</th>
          <th>Koef Final</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="comp in expandedComponents">
          <td>{{ comp.kode }}</td>
          <td>{{ comp.uraian }}</td>
          <td class="text-right">{{ comp.koef_original }}</td>
          <td>×</td>
          <td class="text-right">{{ bundle.koefisien }}</td>
          <td>=</td>
          <td class="text-right"><strong>{{ comp.koef_final }}</strong></td>
        </tr>
      </tbody>
    </table>

    <div class="alert alert-success">
      ✅ Total: {{ expandedComponents.length }} komponen akan ditambahkan
    </div>
  </div>
  <div class="modal-footer">
    <button class="btn btn-secondary" onclick="closePreview()">Batal</button>
    <button class="btn btn-primary" onclick="confirmSave()">✓ Lanjutkan Simpan</button>
  </div>
</div>
```

### **Post-Save Success Message**
```html
<div class="toast toast-success">
  <div class="toast-icon">✅</div>
  <div class="toast-content">
    <strong>Data Berhasil Disimpan!</strong>
    <ul class="mb-0">
      <li>5 komponen AHSP tersimpan</li>
      <li>1 bundle di-expand → 3 komponen ditambahkan</li>
      <li>2 item harga baru dibuat (harga: Rp 0)</li>
    </ul>
    <div class="toast-actions">
      <a href="/harga-items?highlight=PKJ.001" class="btn btn-sm btn-warning">
        → Lengkapi Harga (2 items)
      </a>
      <button class="btn btn-sm btn-outline" onclick="dismissToast()">OK</button>
    </div>
  </div>
</div>
```

### **Error Messages**

#### **Empty Bundle**
```html
<div class="alert alert-danger">
  <strong>❌ Gagal Menyimpan</strong>
  <p>
    Pekerjaan "{{ ref_pekerjaan.kode }}" tidak memiliki komponen AHSP.
    Bundle harus mereferensi pekerjaan yang sudah memiliki komponen.
  </p>
  <p class="mb-0">
    <strong>Solusi:</strong>
  </p>
  <ul class="mb-0">
    <li>Pilih pekerjaan lain yang sudah memiliki komponen, atau</li>
    <li>
      <a href="/template-ahsp?pekerjaan={{ ref_pekerjaan.id }}">
        Isi komponen pekerjaan "{{ ref_pekerjaan.kode }}" terlebih dahulu →
      </a>
    </li>
  </ul>
</div>
```

#### **Circular Dependency**
```html
<div class="alert alert-danger">
  <strong>❌ Circular Reference Terdeteksi</strong>
  <p>
    Bundle yang Anda buat akan menyebabkan circular reference:
  </p>
  <pre class="bg-light p-2">{{ cycle_path }}</pre>
  <p class="mb-0">
    <strong>Solusi:</strong> Pilih pekerjaan lain yang tidak mereferensi kembali ke pekerjaan ini.
  </p>
</div>
```

---

## 💰 HARGA ITEMS PAGE

### **Page Header**
```
Title: Harga Items
Subtitle: Kelola harga satuan untuk komponen AHSP yang digunakan dalam project
Help Text: Item yang ditampilkan berasal dari komponen yang sudah di-expand. Bundle (LAIN) tidak ditampilkan karena sudah diuraikan menjadi komponen TK/BHN/ALT.
```

### **Missing Price Alert**
```html
<div class="alert alert-warning alert-dismissible">
  <button type="button" class="close" data-dismiss="alert">×</button>
  <strong>⚠️ Perhatian: {{ unpricedCount }} item belum memiliki harga</strong>
  <p class="mb-2">
    Item dengan harga Rp 0 akan menghasilkan total Rp 0 di Rincian AHSP.
    Mohon lengkapi harga untuk semua item.
  </p>
  <button class="btn btn-sm btn-warning" onclick="filterUnpriced()">
    📋 Tampilkan Item Belum Dihargai ({{ unpricedCount }})
  </button>
</div>
```

### **Filter Controls**
```html
<div class="filter-controls">
  <label>Status Harga:</label>
  <select class="form-control" onchange="filterByPriceStatus(this.value)">
    <option value="all">Semua Item</option>
    <option value="priced">✅ Sudah Ada Harga</option>
    <option value="unpriced">⚠️ Belum Ada Harga (Rp 0)</option>
  </select>

  <span class="help-icon ml-2" data-tooltip="
    Unpriced items (Rp 0) biasanya baru dibuat saat Anda menambah komponen di Template AHSP.
    Filter ini membantu Anda fokus pada item yang perlu dilengkapi harganya.
  ">?</span>
</div>

<div class="filter-controls mt-2">
  <label>Sumber Item:</label>
  <select class="form-control" onchange="filterBySource(this.value)">
    <option value="all">Semua Sumber</option>
    <option value="direct">Input Langsung</option>
    <option value="bundle">Dari Bundle (📦)</option>
    <option value="orphaned">⚠️ Tidak Digunakan (Orphan)</option>
  </select>

  <span class="help-icon ml-2" data-tooltip="
    • Input Langsung: Komponen TK/BHN/ALT yang diinput manual
    • Dari Bundle: Komponen hasil ekspansi bundle (LAIN)
    • Orphan: Item yang tidak lagi digunakan (bisa dihapus)
  ">?</span>
</div>
```

### **Table Row - Unpriced Item**
```html
<tr class="unpriced-item">
  <td>
    <span class="badge badge-warning">💰 Harga Belum Diisi</span>
    {{ item.kode }}
  </td>
  <td>{{ item.uraian }}</td>
  <td>{{ item.kategori }}</td>
  <td>
    <input
      type="number"
      class="form-control form-control-lg"
      style="border: 2px solid #ffc107; font-weight: bold"
      value="0"
      placeholder="Masukkan harga satuan..."
      data-kode="{{ item.kode }}"
      autofocus
    >
    <small class="form-text text-muted">
      Contoh: 150000 (tanpa titik/koma)
    </small>
  </td>
  <td>
    <div class="usage-info">
      <span class="badge badge-info">Digunakan 2x</span>
      <button class="btn btn-sm btn-link" onclick="showUsageDetail('{{ item.kode }}')">
        Detail →
      </button>
    </div>
  </td>
</tr>
```

### **Table Row - Orphaned Item**
```html
<tr class="orphaned-item" style="opacity: 0.5; background: #f8f9fa">
  <td>
    <span class="badge badge-secondary">⚠️ Tidak Digunakan</span>
    {{ item.kode }}
  </td>
  <td>{{ item.uraian }}</td>
  <td>{{ item.kategori }}</td>
  <td>{{ formatCurrency(item.harga_satuan) }}</td>
  <td>
    <div class="orphan-actions">
      <span class="text-muted">Tidak ada pekerjaan yang menggunakan item ini</span>
      <button class="btn btn-sm btn-danger" onclick="deleteOrphan('{{ item.id }}')">
        🗑️ Hapus
      </button>
    </div>
  </td>
</tr>
```

### **Table Row - From Bundle**
```html
<tr class="bundle-item">
  <td>
    <span class="badge badge-info">📦 Dari Bundle</span>
    {{ item.kode }}
  </td>
  <td>
    {{ item.uraian }}
    <small class="text-muted d-block">
      Source: Bundle "{{ item.source_bundle }}" di PKJ.{{ item.source_pekerjaan }}
    </small>
  </td>
  <td>{{ item.kategori }}</td>
  <td>
    <input
      type="number"
      class="form-control"
      value="{{ item.harga_satuan }}"
      data-kode="{{ item.kode }}"
    >
  </td>
  <td>
    <button class="btn btn-sm btn-link" onclick="showUsageDetail('{{ item.kode }}')">
      Digunakan {{ item.usage_count }}x →
    </button>
  </td>
</tr>
```

### **Usage Detail Modal**
```html
<div class="modal" id="usage-detail-modal">
  <div class="modal-header">
    <h4>📊 Item Usage: {{ item.kode }}</h4>
  </div>
  <div class="modal-body">
    <table class="table table-sm">
      <thead>
        <tr>
          <th>Pekerjaan</th>
          <th>Koefisien</th>
          <th>Sumber</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="usage in usages">
          <td>
            <a :href="'/template-ahsp?pekerjaan=' + usage.pekerjaan_id">
              {{ usage.pekerjaan_kode }}
            </a>
          </td>
          <td class="text-right">{{ usage.koefisien }}</td>
          <td>
            <span v-if="usage.source_bundle" class="badge badge-info">
              📦 Bundle: {{ usage.source_bundle }}
            </span>
            <span v-else class="badge badge-secondary">
              Input Langsung
            </span>
          </td>
        </tr>
      </tbody>
    </table>

    <div class="alert alert-info mt-3">
      <strong>Total Kebutuhan:</strong><br>
      Koefisien Total: {{ totalKoef }}<br>
      Biaya Total: {{ formatCurrency(totalKoef * item.harga_satuan) }}
    </div>
  </div>
</div>
```

### **Save Success with Next Steps**
```html
<div class="toast toast-success">
  <div class="toast-icon">✅</div>
  <div class="toast-content">
    <strong>Harga Berhasil Disimpan!</strong>
    <ul class="mb-0">
      <li>{{ savedCount }} item updated</li>
      <li v-if="unpricedCount > 0">
        ⚠️ Masih ada {{ unpricedCount }} item dengan harga Rp 0
      </li>
      <li v-else>
        ✅ Semua item sudah memiliki harga!
      </li>
    </ul>
    <div class="toast-actions mt-2">
      <a href="/rincian-ahsp" class="btn btn-sm btn-primary" v-if="unpricedCount == 0">
        → Lanjut ke Rincian AHSP
      </a>
      <button class="btn btn-sm btn-warning" onclick="filterUnpriced()" v-else>
        → Lengkapi {{ unpricedCount }} Item Lagi
      </button>
    </div>
  </div>
</div>
```

---

## 📊 RINCIAN AHSP PAGE

### **Page Header with Status**
```
Title: Rincian AHSP: {{ pekerjaan.kode }}

Status Badge:
  - All prices filled: ✅ Lengkap
  - Some missing: ⚠️ {{ unpricedCount }} item belum ada harga
  - Empty: ❌ Tidak ada komponen
```

### **Missing Price Alert (Top of Table)**
```html
<div class="alert alert-danger" v-if="hasUnpricedItems">
  <strong>❌ Tidak Dapat Menghitung Total yang Akurat</strong>
  <p>
    {{ unpricedCount }} item belum memiliki harga (Rp 0).
    Total yang ditampilkan di bawah tidak akurat.
  </p>
  <p class="mb-0">
    <strong>Action Required:</strong>
  </p>
  <a href="/harga-items?pekerjaan={{ pekerjaan.id }}" class="btn btn-warning">
    → Lengkapi Harga ({{ unpricedCount }} items)
  </a>
</div>
```

### **Table - Zero Price Row**
```html
<tr class="zero-price-row" style="background: #fff3cd; border-left: 4px solid #ffc107">
  <td>
    <span class="badge badge-warning">💰</span>
    {{ item.kode }}
  </td>
  <td>{{ item.uraian }}</td>
  <td class="text-right">{{ item.koefisien }}</td>
  <td class="text-right zero-price">
    <strong style="color: #dc3545">Rp 0</strong>
    <small class="d-block text-muted">(belum diisi)</small>
  </td>
  <td class="text-right zero-total">
    <strong style="color: #dc3545">Rp 0</strong>
  </td>
</tr>
```

### **Table - Bundle-Expanded Row**
```html
<tr class="bundle-expanded-row" style="background: #e7f3ff; border-left: 4px solid #007bff">
  <td>
    <span class="badge badge-info" title="Item ini berasal dari bundle expansion">
      📦
    </span>
    {{ item.kode }}
  </td>
  <td>
    {{ item.uraian }}
    <small class="text-muted d-block">
      dari Bundle: "{{ item.source_bundle }}"
    </small>
  </td>
  <td class="text-right">{{ item.koefisien }}</td>
  <td class="text-right">{{ formatCurrency(item.harga_satuan) }}</td>
  <td class="text-right">
    <strong>{{ formatCurrency(item.jumlah_harga) }}</strong>
  </td>
</tr>
```

### **Total Section**
```html
<div class="total-section">
  <table class="table table-sm">
    <tr>
      <td class="text-right"><strong>Subtotal:</strong></td>
      <td class="text-right" style="width: 200px">
        {{ formatCurrency(subtotal) }}
      </td>
    </tr>
    <tr>
      <td class="text-right">
        <strong>BUK ({{ markup_percent }}%):</strong>
        <span class="help-icon ml-2" data-tooltip="
          Biaya Umum & Keuntungan (Profit/Margin).
          Bisa di-override khusus untuk pekerjaan ini atau menggunakan setting project.
        ">?</span>
      </td>
      <td class="text-right">
        {{ formatCurrency(buk) }}
      </td>
    </tr>
    <tr class="total-row">
      <td class="text-right"><strong>GRAND TOTAL:</strong></td>
      <td class="text-right">
        <strong style="font-size: 1.2em; color: #28a745">
          {{ formatCurrency(grand_total) }}
        </strong>
      </td>
    </tr>
  </table>

  <div class="alert alert-warning" v-if="hasUnpricedItems">
    ⚠️ Total di atas tidak akurat karena {{ unpricedCount }} item belum memiliki harga.
  </div>
</div>
```

### **Audit Trail Button**
```html
<div class="toolbar">
  <button class="btn btn-outline-secondary" onclick="showAuditTrail()">
    📜 Lihat History Perubahan
  </button>

  <span class="help-icon ml-2" data-tooltip="
    Audit Trail menampilkan semua perubahan yang terjadi pada pekerjaan ini,
    termasuk bundle expansion, re-expansion, dan modifikasi komponen.
    Berguna untuk troubleshooting jika angka tiba-tiba berubah.
  ">?</span>
</div>
```

---

## 🎓 ONBOARDING GUIDE (TEST_PHASE2_GUIDE.md)

### **Quick Start: Segment D (Bundle) Workflow**

```markdown
## 📦 Segment D (LAIN) - Bundle Workflow

### Apa itu Bundle?
Bundle adalah cara untuk **mereferensi pekerjaan lain** sebagai komponen.
Cocok untuk:
- Pekerjaan berulang (misal: kolom struktural yang sama dipakai berkali-kali)
- Pekerjaan komposit (misal: "Pekerjaan Finishing Lengkap" yang terdiri dari beberapa sub-pekerjaan)

### Alur Kerja Bundle

#### **Step 1: Persiapkan Pekerjaan Target**
Sebelum membuat bundle, pastikan pekerjaan target sudah memiliki komponen:

```
Template AHSP → Pilih Pekerjaan B
├─ Add komponen: TK L.01 (koef 5.0)
├─ Add komponen: BHN B.02 (koef 10.0)
└─ Save ✓
```

#### **Step 2: Buat Bundle di Pekerjaan Sumber**
```
Template AHSP → Pilih Pekerjaan A
├─ Tab "LAIN (Bundle)"
├─ Kode: "Bundle_B"
├─ Uraian: "Pekerjaan Gabungan B"
├─ Ref Pekerjaan: Pilih "Pekerjaan B" dari dropdown
├─ Koefisien: 3.0
└─ Klik "Pratinjau Ekspansi" untuk melihat hasil
```

#### **Step 3: Save & Verifikasi**
Setelah save, system akan:
1. ✅ Expand bundle → Komponen dari Pekerjaan B di-copy
2. ✅ Kalikan koefisien: L.01 (5.0 × 3.0 = 15.0), B.02 (10.0 × 3.0 = 30.0)
3. ✅ Create HargaItemProject untuk L.01 dan B.02 (jika belum ada)

Verifikasi:
- **Harga Items:** L.01 dan B.02 muncul (Bundle_B TIDAK muncul)
- **Rincian AHSP:** L.01 (koef 15.0) dan B.02 (koef 30.0) ditandai dengan 📦

#### **Step 4: Set Harga**
```
Harga Items → Filter "Belum Ada Harga"
├─ L.01: Rp 150,000
├─ B.02: Rp 50,000
└─ Save
```

#### **Step 5: Review Total**
```
Rincian AHSP → Pilih Pekerjaan A
├─ L.01: 15.0 × 150,000 = Rp 2,250,000 (📦 dari Bundle_B)
├─ B.02: 30.0 × 50,000 = Rp 1,500,000 (📦 dari Bundle_B)
└─ Total: Rp 3,750,000
```

### Common Pitfalls

❌ **"Bundle saya tidak muncul di Harga Items"**
→ Ini NORMAL! Bundle di-expand menjadi komponen TK/BHN/ALT.
   Yang muncul di Harga Items adalah komponen hasil ekspansi, bukan bundle itu sendiri.

❌ **"Saya pilih pekerjaan tapi error 'tidak memiliki komponen'"**
→ Pekerjaan target harus sudah memiliki komponen sebelum dijadikan bundle.
   Isi komponen dulu di Template AHSP untuk pekerjaan tersebut.

❌ **"Total di Rincian AHSP tiba-tiba berubah"**
→ Kemungkinan pekerjaan target (yang di-reference) telah dimodifikasi.
   System otomatis re-expand bundle. Lihat Audit Trail untuk detail.

❌ **"Ada item 'orphan' di Harga Items"**
→ Item orphan terjadi ketika Anda rename kode atau delete item.
   Gunakan filter "Tidak Digunakan" untuk menemukannya, lalu hapus manual.

### Tips & Best Practices

✅ **Use Preview Before Save**
Selalu klik "Pratinjau Ekspansi" sebelum save bundle untuk memastikan hasil ekspansi sesuai harapan.

✅ **Naming Convention**
Gunakan prefix "Bundle_" untuk bundle items agar mudah diidentifikasi.

✅ **Limit Nesting**
Hindari bundle bertingkat > 2 levels (A → B → C sudah cukup).
Lebih dari itu akan sulit di-maintain.

✅ **Document Bundle Purpose**
Gunakan field "Uraian" untuk menjelaskan tujuan bundle, misal:
"Bundle Kolom Struktural 30x30cm - Dipakai untuk semua kolom utama"

✅ **Check Audit Trail**
Jika angka berubah tanpa sebab jelas, lihat Audit Trail (📜 button) untuk melihat history.

---

## QA Testing Checklist

### Bundle Creation
- [ ] Can create bundle with valid target
- [ ] Cannot create bundle with empty target (error shown)
- [ ] Cannot create circular reference (error shown)
- [ ] Preview shows correct expansion before save
- [ ] Post-save toast shows expansion summary

### Bundle Expansion
- [ ] Components created in DetailAHSPExpanded
- [ ] Koefisien calculated correctly (multiplied)
- [ ] HargaItemProject auto-created for new items
- [ ] Bundle itself NOT shown in Harga Items
- [ ] Expanded components shown with 📦 icon in Rincian AHSP

### Cascade Re-Expansion
- [ ] Edit bundle target → referencing pekerjaan auto re-expanded
- [ ] Multi-level (A→B→C): Edit C → B and A both updated
- [ ] Audit trail records cascade events
- [ ] Totals in Rincian AHSP reflect new values

### Error Handling
- [ ] Empty bundle: Clear error message
- [ ] Circular reference: Clear error with cycle path
- [ ] Missing price: Alert shown in Rincian AHSP with CTA
- [ ] Orphaned items: Filterable and deletable

### Cross-Page Indicators
- [ ] Template AHSP sidebar shows price completion status
- [ ] Harga Items shows unpriced item count
- [ ] Rincian AHSP shows missing price alert
- [ ] Workflow stepper reflects current step
```

---

## 📚 Additional Resources

### Tooltips Reference
All tooltips use this format:
```html
<span class="help-icon" data-tooltip="[Help text here]">?</span>
```

### Icon Legend
- 📦 = Bundle/from bundle expansion
- 💰 = Price/money related
- ⚠️ = Warning/attention needed
- ✅ = Success/complete
- ❌ = Error/failed
- 📜 = History/audit trail
- 👁️ = Preview/view
- 🗑️ = Delete
- → = Action/next step

### Color Codes
- **Yellow (#ffc107):** Unpriced items, warnings
- **Red (#dc3545):** Errors, critical issues
- **Blue (#007bff):** Bundle-related, info
- **Green (#28a745):** Success, complete
- **Gray (#6c757d):** Orphaned, disabled

---

**Last Updated:** 2025-01-XX
**Maintainer:** UX Team
**Status:** Living Document
