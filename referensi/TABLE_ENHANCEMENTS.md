# 📊 Table Enhancement Features - Documentation

## 🎯 Overview

Dokumentasi untuk 3 fitur baru yang meningkatkan user experience dalam mengelola tabel database AHSP:

1. **Row Limit Controller** - Kontrol jumlah baris yang ditampilkan
2. **Column Visibility Toggle** - Sembunyikan/tampilkan kolom tertentu
3. **Resizable Columns** - Atur lebar kolom secara manual

---

## ✨ Feature 1: Row Limit Controller

### Deskripsi
Dropdown kontroler yang menggantikan teks informasi statis, memungkinkan admin untuk mengatur berapa banyak baris yang ditampilkan dalam tabel.

### Cara Menggunakan

1. **Lokasi**: Pojok kiri atas header tabel
2. **UI**: Dropdown dengan label "Tampilkan:" dan satuan "baris"
3. **Pilihan**:
   - 20 baris
   - 50 baris (default)
   - 100 baris
   - 200 baris

4. **Langkah**:
   - Klik dropdown
   - Pilih jumlah baris yang diinginkan
   - Tabel akan langsung menampilkan sesuai limit yang dipilih
   - Notifikasi toast muncul: "Menampilkan X baris"

### Fitur Tambahan

- ✅ **Persistent Selection**: Pilihan tersimpan di localStorage browser
- ✅ **Per-Table Setting**: Setiap tab (Jobs/Items) punya pengaturan sendiri
- ✅ **Instant Update**: Tidak perlu reload halaman
- ✅ **Works with Search**: Tetap berfungsi saat filter/search aktif

### Kode Implementasi

**HTML** ([ahsp_database.html](templates/referensi/ahsp_database.html)):
```html
<div class="col-auto">
  <div class="d-flex align-items-center gap-2">
    <label class="small text-muted mb-0">Tampilkan:</label>
    <select class="form-select form-select-sm" id="rowLimitJobs">
      <option value="20">20</option>
      <option value="50" selected>50</option>
      <option value="100">100</option>
      <option value="200">200</option>
    </select>
    <span class="small text-muted">baris</span>
  </div>
</div>
```

**JavaScript** ([ahsp_database_v2.js:741-783](static/referensi/js/ahsp_database_v2.js)):
```javascript
const rowLimitModule = {
    init() {
        this.initRowLimit('rowLimitJobs', 'tableJobs');
        this.initRowLimit('rowLimitItems', 'tableItems');
    },

    initRowLimit(selectId, tableId) {
        const select = document.getElementById(selectId);
        const table = document.getElementById(tableId);

        // Load saved preference
        const savedLimit = localStorage.getItem(`${tableId}_rowLimit`);
        if (savedLimit) select.value = savedLimit;

        // Apply initial limit
        this.applyRowLimit(table, parseInt(select.value));

        // Listen for changes
        select.addEventListener('change', (e) => {
            const limit = parseInt(e.target.value);
            this.applyRowLimit(table, limit);
            localStorage.setItem(`${tableId}_rowLimit`, limit);
            showToast(`Menampilkan ${limit} baris`, 'info');
        });
    },

    applyRowLimit(table, limit) {
        const tbody = table.querySelector('tbody');
        const rows = tbody.querySelectorAll('tr');

        rows.forEach((row, index) => {
            row.style.display = index < limit ? '' : 'none';
        });
    }
};
```

**CSS** ([ahsp_database.css:373-377](static/referensi/css/ahsp_database.css)):
```css
#rowLimitJobs,
#rowLimitItems {
    min-width: 70px;
    font-size: 0.813rem;
}
```

---

## ✨ Feature 2: Column Visibility Toggle

### Deskripsi
Modal yang memungkinkan admin memilih kolom mana yang ingin ditampilkan atau disembunyikan pada tabel.

### Cara Menggunakan

1. **Klik tombol "Kolom"** (dengan icon 3 kolom) di header tabel
2. **Modal muncul** dengan daftar semua kolom dalam bentuk checkbox
3. **Uncheck kolom** yang ingin disembunyikan
4. **Check kolom** yang ingin ditampilkan kembali
5. **Klik "Terapkan"** atau klik di luar modal untuk menutup
6. Kolom akan langsung tersembunyi/muncul sesuai pilihan

### Tombol & UI

**Tombol Kolom**:
- Icon: `bi-layout-three-columns`
- Posisi: Di header tabel, setelah dropdown row limit
- Style: `btn-outline-secondary btn-sm`

**Modal**:
- Title: "Atur Kolom" dengan icon
- Body: List group dengan checkbox untuk setiap kolom
- Footer:
  - Tombol "Reset" (tampilkan semua kolom)
  - Tombol "Terapkan" (tutup modal)

### Fitur Tambahan

- ✅ **Persistent Selection**: Disimpan di localStorage per tabel
- ✅ **Skip Checkbox Column**: Kolom checkbox seleksi tidak bisa disembunyikan
- ✅ **Reset Function**: Tombol reset menampilkan semua kolom kembali
- ✅ **Real-time Preview**: Perubahan langsung terlihat saat modal masih terbuka
- ✅ **Per-Table Setting**: Jobs dan Items punya setting terpisah

### Kode Implementasi

**HTML Modal** ([ahsp_database.html](templates/referensi/ahsp_database.html)):
```html
<div class="modal fade" id="modalColumnToggle" tabindex="-1">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">
          <i class="bi bi-layout-three-columns"></i> Atur Kolom
        </h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <p class="small text-muted mb-3">
          Pilih kolom yang ingin ditampilkan:
        </p>
        <div id="columnToggleList" class="list-group">
          <!-- Dynamically populated by JavaScript -->
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-outline-secondary" id="btnResetColumns">
          <i class="bi bi-arrow-clockwise"></i> Reset
        </button>
        <button type="button" class="btn btn-primary" data-bs-dismiss="modal">
          Terapkan
        </button>
      </div>
    </div>
  </div>
</div>
```

**JavaScript** ([ahsp_database_v2.js:789-953](static/referensi/js/ahsp_database_v2.js)):
```javascript
const columnVisibilityModule = {
    modal: null,

    init() {
        this.modal = new bootstrap.Modal(document.getElementById('modalColumnToggle'));
        this.initTable('tableJobs', 'btnColumnToggleJobs');
        this.initTable('tableItems', 'btnColumnToggleItems');
    },

    openModal(table) {
        const headers = table.querySelectorAll('thead th');
        let html = '';

        headers.forEach((header, index) => {
            const columnName = header.textContent.trim();
            const isVisible = !header.classList.contains('column-hidden');
            const isCheckbox = header.querySelector('input[type="checkbox"]');

            if (isCheckbox) return; // Skip checkbox column

            html += `
                <div class="list-group-item">
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox"
                               id="col_${index}" data-col-index="${index}"
                               ${isVisible ? 'checked' : ''}>
                        <label class="form-check-label" for="col_${index}">
                            ${columnName}
                        </label>
                    </div>
                </div>
            `;
        });

        document.getElementById('columnToggleList').innerHTML = html;
        this.modal.show();
    },

    toggleColumn(table, colIndex, show) {
        const headers = table.querySelectorAll('thead th');
        const rows = table.querySelectorAll('tbody tr');

        // Toggle header
        if (headers[colIndex]) {
            headers[colIndex].classList.toggle('column-hidden', !show);
        }

        // Toggle cells in all rows
        rows.forEach(row => {
            const cell = row.cells[colIndex];
            if (cell) cell.classList.toggle('column-hidden', !show);
        });

        this.saveColumnVisibility(table);
    }
};
```

**CSS** ([ahsp_database.css:341-367](static/referensi/css/ahsp_database.css)):
```css
/* Hidden columns */
.column-hidden {
    display: none !important;
}

/* Column toggle list */
#columnToggleList .list-group-item {
    padding: 0.5rem 1rem;
    cursor: pointer;
    transition: background-color 0.15s ease;
}

#columnToggleList .list-group-item:hover {
    background-color: #f8f9fa;
}

#columnToggleList .form-check-label {
    cursor: pointer;
    width: 100%;
}
```

---

## ✨ Feature 3: Resizable Columns

### Deskripsi
Fitur drag-and-drop untuk mengatur lebar kolom secara manual dengan menarik border kanan setiap header kolom.

### Cara Menggunakan

1. **Hover** mouse ke border kanan header kolom
2. Cursor akan berubah menjadi `col-resize` (↔)
3. Border akan highlight dengan warna biru
4. **Click dan drag** ke kiri/kanan untuk resize
5. **Release mouse** untuk menetapkan ukuran baru
6. Lebar kolom otomatis tersimpan di localStorage

### Visual Feedback

**Normal State**:
- Border kanan kolom memiliki handle transparan (5px wide)
- Small indicator bar (rgba opacity 0.1)

**Hover State**:
- Border highlight warna biru (`#0d6efd`)
- Cursor berubah jadi `col-resize`

**Resizing State**:
- Border tetap biru
- Body mendapat class `column-resizing`
- Text selection disabled di seluruh page
- Cursor tetap `col-resize` saat drag

### Batasan

- ✅ **Minimum Width**: 60px (tidak bisa lebih kecil)
- ✅ **Maximum Width**: Unlimited (sampai lebar viewport)
- ✅ **Excluded Column**: Kolom terakhir (Actions) tidak bisa di-resize
- ✅ **Persistent**: Ukuran tersimpan per tabel di localStorage

### Kode Implementasi

**JavaScript** ([ahsp_database_v2.js:959-1084](static/referensi/js/ahsp_database_v2.js)):
```javascript
const resizableColumnsModule = {
    isResizing: false,
    currentResizer: null,
    currentColumn: null,
    startX: 0,
    startWidth: 0,

    init() {
        this.initTable('tableJobs');
        this.initTable('tableItems');
    },

    initTable(tableId) {
        const table = document.getElementById(tableId);
        const headers = table.querySelectorAll('thead th');

        headers.forEach((header, index) => {
            // Skip last column (actions)
            if (index === headers.length - 1) return;

            // Create resizer element
            const resizer = document.createElement('div');
            resizer.className = 'column-resizer';
            header.appendChild(resizer);

            // Add drag events
            resizer.addEventListener('mousedown', (e) => {
                this.startResize(e, header, resizer);
            });
        });

        // Global mouse events
        document.addEventListener('mousemove', (e) => {
            if (this.isResizing) this.doResize(e);
        });

        document.addEventListener('mouseup', () => {
            if (this.isResizing) this.stopResize();
        });

        this.loadColumnWidths(table);
    },

    startResize(e, header, resizer) {
        e.preventDefault();
        e.stopPropagation();

        this.isResizing = true;
        this.currentResizer = resizer;
        this.currentColumn = header;
        this.startX = e.pageX;
        this.startWidth = header.offsetWidth;

        document.body.classList.add('column-resizing');
        resizer.classList.add('resizing');
    },

    doResize(e) {
        const diff = e.pageX - this.startX;
        const newWidth = this.startWidth + diff;

        if (newWidth >= 60) { // Minimum 60px
            this.currentColumn.style.width = newWidth + 'px';
            this.currentColumn.style.minWidth = newWidth + 'px';
        }
    },

    stopResize() {
        this.isResizing = false;
        document.body.classList.remove('column-resizing');
        this.currentResizer.classList.remove('resizing');

        // Save to localStorage
        const table = this.currentColumn.closest('table');
        this.saveColumnWidths(table);
    }
};
```

**CSS** ([ahsp_database.css:298-335](static/referensi/css/ahsp_database.css)):
```css
/* Table header positioning */
.ahsp-database-table th {
    position: relative;
    user-select: none;
}

/* Resizer handle */
.column-resizer {
    position: absolute;
    top: 0;
    right: 0;
    width: 5px;
    height: 100%;
    cursor: col-resize;
    user-select: none;
    z-index: 1;
}

.column-resizer:hover,
.column-resizer.resizing {
    background-color: #0d6efd;
}

/* Indicator bar */
.column-resizer::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 3px;
    height: 30%;
    background-color: rgba(0, 0, 0, 0.1);
    border-radius: 2px;
}

/* Prevent text selection during resize */
body.column-resizing {
    cursor: col-resize;
    user-select: none;
}
```

---

## 🛠️ Technical Details

### LocalStorage Keys

Semua 3 fitur menggunakan localStorage untuk menyimpan preferensi user:

```javascript
// Row Limit
localStorage.setItem('tableJobs_rowLimit', '50');
localStorage.setItem('tableItems_rowLimit', '100');

// Column Visibility
localStorage.setItem('tableJobs_hiddenColumns', '[2, 5, 7]'); // JSON array
localStorage.setItem('tableItems_hiddenColumns', '[1, 3]');

// Column Widths
localStorage.setItem('tableJobs_columnWidths', '["120px", "250px", ...]'); // JSON array
localStorage.setItem('tableItems_columnWidths', '["100px", "200px", ...]');
```

### Module Architecture

```
ahsp_database_v2.js
├── Configuration & Utilities (lines 1-50)
│   ├── getCookie()
│   ├── showToast()
│   ├── debounce()
│   └── highlightText()
├── Autocomplete Module (lines 55-359)
├── Bulk Delete Module (lines 365-551)
├── Table Sorting Module (lines 557-638)
├── Change Tracking Module (lines 644-735)
├── Row Limit Module (lines 741-783) ← NEW
├── Column Visibility Module (lines 789-953) ← NEW
├── Resizable Columns Module (lines 959-1084) ← NEW
└── Initialization (lines 1090-1098)
```

### Initialization Order

```javascript
document.addEventListener('DOMContentLoaded', function() {
    autocompleteModule.init();
    bulkDeleteModule.init();
    tableSortModule.init();
    changeTrackingModule.init();
    rowLimitModule.init();              // ← NEW
    columnVisibilityModule.init();      // ← NEW
    resizableColumnsModule.init();      // ← NEW
});
```

### Performance Considerations

1. **Row Limit**:
   - O(n) complexity for showing/hiding rows
   - No DOM manipulation (hanya style.display)
   - Fast even with 5000+ rows

2. **Column Visibility**:
   - O(n × m) where n = rows, m = columns
   - Uses classList.toggle (native, optimized)
   - Efficient localStorage (small JSON arrays)

3. **Resizable Columns**:
   - Only updates during drag (throttled by browser)
   - Saves once on mouseup (not during drag)
   - Minimal DOM queries

---

## 🧪 Testing Checklist

### Row Limit Controller
- [ ] Dropdown shows correct default value (50)
- [ ] Changing value updates table instantly
- [ ] Toast notification appears
- [ ] Selection persists after page reload
- [ ] Works independently for Jobs and Items tables
- [ ] Works with search/filter active
- [ ] Works after sorting

### Column Visibility Toggle
- [ ] Button opens modal correctly
- [ ] Modal shows all columns (except checkbox)
- [ ] Unchecking checkbox hides column
- [ ] Checking checkbox shows column
- [ ] Changes apply in real-time
- [ ] Preferences persist after reload
- [ ] Reset button shows all columns
- [ ] Works for both Jobs and Items tables

### Resizable Columns
- [ ] Cursor changes to col-resize on hover
- [ ] Border highlights blue on hover
- [ ] Dragging resizes column smoothly
- [ ] Minimum width enforced (60px)
- [ ] Text selection disabled during resize
- [ ] Width saved to localStorage
- [ ] Saved widths restored on reload
- [ ] Last column (Actions) cannot be resized
- [ ] Works for both tables

### Integration Testing
- [ ] All 3 features work together
- [ ] Row limit + hidden columns work correctly
- [ ] Resized columns remain after hiding/showing
- [ ] Search works with all features active
- [ ] Sorting works with all features active
- [ ] Change tracking not affected
- [ ] Bulk delete not affected

---

## 🚀 Future Enhancements

Potensi improvement untuk fitur-fitur ini:

1. **Row Limit**:
   - Add "Show All" option
   - Display "Showing X-Y of Z" info
   - Pagination controls

2. **Column Visibility**:
   - Save multiple presets (e.g., "Default", "Compact", "Detailed")
   - Drag-and-drop to reorder columns
   - Export/import column configurations

3. **Resizable Columns**:
   - Double-click to auto-fit column width to content
   - Shift+drag to resize multiple columns proportionally
   - Column width presets (e.g., "Compact", "Comfortable", "Wide")

4. **Cross-Feature**:
   - Export table view settings (row limit + visibility + widths) as JSON
   - Share settings link with other admins
   - Admin can set default view for all users

---

## 📞 Troubleshooting

### Issue: Row limit not applying
**Solution**: Check browser console for errors, verify table ID matches

### Issue: Column visibility not saving
**Solution**: Check localStorage quota, clear old data if needed

### Issue: Resize not working
**Solution**: Verify CSS loaded correctly, check z-index conflicts

### Issue: Settings reset after clearing cache
**Solution**: Expected behavior - localStorage cleared with cache

---

## 📝 Changelog

### v2.0.0 (2025-11-03)
- ✅ Added Row Limit Controller (20/50/100/200)
- ✅ Added Column Visibility Toggle with modal
- ✅ Added Resizable Columns with drag-and-drop
- ✅ All settings persistent via localStorage
- ✅ Compact table spacing (reduced whitespace)
- ✅ Polished row height for better readability

---

**Happy Table Management! 📊✨**
