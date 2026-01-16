# 📋 Dokumentasi Fitur "Export dengan Opsi"

## 🎯 OVERVIEW

Fitur **"Export dengan Opsi"** memungkinkan user untuk export data Rekap Kebutuhan dengan **filtering periode waktu** dan **pilihan format export**.

**Lokasi UI:**
- Page: **Rekap Kebutuhan** (`/detail_project/rekap_kebutuhan/`)
- Button: **Export > Export dengan Opsi...**
- Modal ID: `#rk-export-modal`

---

## 🎨 USER INTERFACE

### 1. **Entry Point**

**Dropdown Menu Export:**
```
Export ▼
├── Export CSV          (direct export - no modal)
├── Export PDF          (direct export - no modal)
├── Export Word         (direct export - no modal)
├── ──────────────
├── Export dengan Opsi...  ⬅️ OPENS MODAL
├── ──────────────
└── Export JSON         (direct export - no modal)
```

**Template:** [rekap_kebutuhan.html:279-283](d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\templates\detail_project\rekap_kebutuhan.html#L279-L283)
```html
<button class="dropdown-item fw-semibold" type="button" id="btn-export-modal">
  <i class="bi bi-sliders text-secondary me-2"></i>
  Export dengan Opsi...
</button>
```

---

### 2. **Export Modal Structure**

**Modal ID:** `#rk-export-modal`
**Template:** [rekap_kebutuhan.html:581-678](d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\templates\detail_project\rekap_kebutuhan.html#L581-L678)

**3 Sections:**

#### **Section A: Periode Export** (REQUIRED SELECTION)

User memilih periode data yang akan di-export:

```
○ Keseluruhan Proyek       [DEFAULT]
  Export seluruh kebutuhan material tanpa filter waktu

○ Minggu Tertentu
  Export kebutuhan per minggu yang dipilih

○ Bulan Tertentu
  Export kebutuhan per bulan yang dipilih
```

**HTML:**
```html
<input type="radio" name="exportPeriod" value="all" checked>     <!-- Keseluruhan -->
<input type="radio" name="exportPeriod" value="week">            <!-- Minggu -->
<input type="radio" name="exportPeriod" value="month">           <!-- Bulan -->
```

---

#### **Section B: Pilih Periode** (CONDITIONAL - shown if week/month selected)

Jika user pilih "Minggu Tertentu" atau "Bulan Tertentu", muncul 2 dropdown:

```
Pilih Minggu / Bulan
┌─────────────────────┐  ┌─────────────────────┐
│ Dari                │  │ Sampai              │
│ ▼ Minggu 1 (...)    │  │ ▼ Minggu 10 (...)   │
└─────────────────────┘  └─────────────────────┘
```

**HTML:**
```html
<div id="rk-export-period-details" style="display: none;">  <!-- Hidden by default -->
  <select id="rk-export-period-start"></select>  <!-- Populated dynamically -->
  <select id="rk-export-period-end"></select>    <!-- Populated dynamically -->
</div>
```

**Data Source:** `filterMeta.periods.weeks` atau `filterMeta.periods.months`

---

#### **Section C: Format Export** (REQUIRED SELECTION)

User memilih format file export:

```
┌─────────┬─────────┬─────────┐
│ ● PDF   │ ○ Word  │ ○ CSV   │  (Radio buttons styled as buttons)
└─────────┴─────────┴─────────┘
```

**HTML:**
```html
<input type="radio" name="rkExportFormat" value="pdf" checked>
<input type="radio" name="rkExportFormat" value="word">
<input type="radio" name="rkExportFormat" value="csv">
```

---

### 3. **Status Message** (DYNAMIC)

Shown during export process:

```
ℹ️ Memproses export PDF...          (Info - during export)
✅ Export berhasil!                   (Success - after export)
❌ Export gagal: [error message]     (Error - if failed)
```

**HTML:**
```html
<div id="rk-export-status" class="alert d-none">
  <span id="rk-export-status-text"></span>
</div>
```

---

## ⚙️ JAVASCRIPT LOGIC

### 1. **Initialization**

**File:** [rekap_kebutuhan.js:1849-1874](d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\rekap_kebutuhan.js#L1849-L1874)

```javascript
const initExportModal = (triggerExport) => {
  const modal = $('#rk-export-modal');
  const periodRadios = $$('input[name="exportPeriod"]', modal);
  const periodDetails = $('#rk-export-period-details');

  // Event: Period type change (all / week / month)
  periodRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      const value = radio.value;  // "all", "week", or "month"

      if (value === 'all') {
        periodDetails.style.display = 'none';  // Hide period selectors
      } else {
        periodDetails.style.display = 'block';  // Show period selectors
        populateExportPeriodOptions(value);    // Populate dropdowns
      }
    });
  });
};
```

---

### 2. **Period Options Population**

**Function:** `populateExportPeriodOptions(mode)`
**File:** [rekap_kebutuhan.js:1877-1893](d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\rekap_kebutuhan.js#L1877-L1893)

```javascript
const populateExportPeriodOptions = (mode) => {
  // Get periods from filterMeta (loaded from backend)
  const options = mode === 'week'
    ? filterMeta.periods?.weeks || []   // e.g., [{value: "2024-W01", label: "Minggu 1 (1-7 Jan)"}]
    : filterMeta.periods?.months || []; // e.g., [{value: "2024-01", label: "Januari 2024"}]

  // Populate dropdowns
  const optionsHtml = options.map(opt =>
    `<option value="${opt.value}">${opt.label}</option>`
  ).join('');

  periodStart.innerHTML = optionsHtml;
  periodEnd.innerHTML = optionsHtml;

  // Set "Sampai" to last option by default
  periodEnd.selectedIndex = periodEnd.options.length - 1;
};
```

**Data Flow:**
```
Backend (views_api.py)
  → get_filter_metadata()
    → returns { periods: { weeks: [...], months: [...] } }
      → Stored in filterMeta (JavaScript)
        → Used to populate dropdowns
```

---

### 3. **Export Confirmation Handler**

**Event:** Click "Export" button in modal
**File:** [rekap_kebutuhan.js:1896-1951](d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\rekap_kebutuhan.js#L1896-L1951)

```javascript
confirmBtn.addEventListener('click', async () => {
  // 1️⃣ Get user selections
  const format = document.querySelector('input[name="rkExportFormat"]:checked')?.value || 'pdf';
  const periodType = document.querySelector('input[name="exportPeriod"]:checked')?.value || 'all';

  // 2️⃣ Build export parameters
  const exportParams = { ...buildQueryParams() };  // Include current filters

  if (periodType !== 'all') {
    exportParams.period_mode = periodType === 'week' ? 'week_range' : 'month_range';
    exportParams.period_start = periodStart?.value || '';  // e.g., "2024-W01"
    exportParams.period_end = periodEnd?.value || '';      // e.g., "2024-W10"
  }

  // 3️⃣ Add metadata
  exportParams.view_mode = currentViewMode;  // 'snapshot' or 'timeline'
  exportParams.filename = generateExportFilename(format).replace('.' + format, '');

  // 4️⃣ Show loading status
  statusEl.classList.remove('d-none');
  statusText.textContent = `Memproses export ${format.toUpperCase()}...`;
  confirmBtn.disabled = true;

  try {
    // 5️⃣ Create ExportManager WITHOUT modalId (important!)
    const modalExporter = new window.ExportManager(projectId, 'rekap-kebutuhan');

    // 6️⃣ Trigger export with custom params
    await modalExporter.exportAs(format, { query: exportParams });

    // 7️⃣ Show success
    statusText.textContent = 'Export berhasil!';
    statusEl.classList.replace('alert-info', 'alert-success');

    // 8️⃣ Close modal after 1.5s
    setTimeout(() => {
      bootstrap.Modal.getInstance(modal)?.hide();
      // Reset status for next time
      statusEl.classList.add('d-none');
      statusEl.classList.replace('alert-success', 'alert-info');
    }, 1500);

  } catch (error) {
    // Show error
    statusText.textContent = 'Export gagal: ' + error.message;
    statusEl.classList.replace('alert-info', 'alert-danger');
  } finally {
    confirmBtn.disabled = false;
  }
});
```

---

## 🔄 DATA FLOW

### **Complete Request Flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER ACTION                                                  │
└─────────────────────────────────────────────────────────────────┘
User clicks "Export dengan Opsi..."
  → Modal opens (#rk-export-modal)
  → User selects:
    - Period: "Minggu Tertentu"
    - Week Range: Minggu 5 → Minggu 10
    - Format: PDF
  → User clicks "Export" button

┌─────────────────────────────────────────────────────────────────┐
│ 2. JAVASCRIPT PROCESSING                                        │
└─────────────────────────────────────────────────────────────────┘
confirmBtn.click event fires
  → Collect form values:
    format = "pdf"
    periodType = "week"
    period_start = "2024-W05"
    period_end = "2024-W10"

  → Build exportParams object:
    {
      period_mode: "week_range",
      period_start: "2024-W05",
      period_end: "2024-W10",
      view_mode: "snapshot",
      filename: "Rekap_Kebutuhan_20260105",
      // ... plus current filters (klasifikasi, search, etc.)
    }

  → Call: modalExporter.exportAs('pdf', { query: exportParams })

┌─────────────────────────────────────────────────────────────────┐
│ 3. EXPORTMANAGER PROCESSING                                     │
└─────────────────────────────────────────────────────────────────┘
ExportManager.exportAs('pdf', { query: exportParams })
  → Build URL with query params:
    /detail_project/api/project/109/export/rekap-kebutuhan/pdf/
      ?period_mode=week_range
      &period_start=2024-W05
      &period_end=2024-W10
      &view_mode=snapshot
      &filename=Rekap_Kebutuhan_20260105
      &... (other filters)

  → Show loading modal (if configured)
  → fetch(url, { method: 'GET' })

┌─────────────────────────────────────────────────────────────────┐
│ 4. BACKEND PROCESSING (Django)                                  │
└─────────────────────────────────────────────────────────────────┘
View: export_rekap_kebutuhan_pdf(request, project_id)

  → Parse query params:
    params = parse_kebutuhan_query_params(request.GET)
    params['time_scope'] = {
      'mode': 'week_range',
      'start': '2024-W05',
      'end': '2024-W10'
    }

  → Call ExportManager:
    manager = ExportManager(project, user)
    response = manager.export_rekap_kebutuhan(
      'pdf',
      mode=params['mode'],
      filters=params['filters'],
      search=params['search'],
      time_scope=params['time_scope']  ⬅️ PERIOD FILTER
    )

  → Compute data with time filter:
    rows = compute_kebutuhan_items(
      project,
      mode='all',
      filters={...},
      time_scope={'mode': 'week_range', 'start': '2024-W05', 'end': '2024-W10'}
    )

    → Filter data by time range:
      - Get pekerjaan progress for weeks W05-W10
      - Only include items with progress in that range
      - Calculate totals for selected period only

  → Generate PDF:
    adapter = RekapKebutuhanAdapter(project, rows=rows, summary=summary)
    data = adapter.get_export_data()

    exporter = PDFExporter(config)
    response = exporter.export(data)  → HttpResponse with PDF file

┌─────────────────────────────────────────────────────────────────┐
│ 5. RESPONSE HANDLING                                            │
└─────────────────────────────────────────────────────────────────┘
ExportManager receives response
  → response.status = 200 OK
  → response.headers['Content-Disposition'] = "attachment; filename=\"...pdf\""
  → blob = await response.blob()
  → Download file to browser
  → Hide loading modal
  → Show success message

Modal shows:
  ✅ Export berhasil!
  → Auto-close after 1.5 seconds
```

---

## 🎛️ PARAMETER MAPPING

### **Frontend → Backend**

| User Selection | JavaScript Params | Backend Params | Backend Processing |
|---------------|-------------------|----------------|-------------------|
| **Keseluruhan Proyek** | *(no period params)* | `time_scope = None` | No time filtering, all data included |
| **Minggu 5 → 10** | `period_mode = "week_range"`<br>`period_start = "2024-W05"`<br>`period_end = "2024-W10"` | `time_scope = {`<br>`  'mode': 'week_range',`<br>`  'start': '2024-W05',`<br>`  'end': '2024-W10'`<br>`}` | Filter progress by weeks W05-W10 |
| **Bulan Jan → Mar** | `period_mode = "month_range"`<br>`period_start = "2024-01"`<br>`period_end = "2024-03"` | `time_scope = {`<br>`  'mode': 'month_range',`<br>`  'start': '2024-01',`<br>`  'end': '2024-03'`<br>`}` | Filter progress by months Jan-Mar |

---

## 📊 BACKEND IMPLEMENTATION

### **1. Parse Query Parameters**

**File:** `api_helpers.py`
**Function:** `parse_kebutuhan_query_params(query_dict)`

```python
def parse_kebutuhan_query_params(query_dict):
    """Parse query parameters for rekap kebutuhan export."""

    # ... other params ...

    # Time scope (period filtering)
    time_scope = {
        'mode': (query.get('period_mode') or 'all').strip().lower(),
        'start': (query.get('period_start') or '').strip(),
        'end': (query.get('period_end') or '').strip(),
    }

    return {
        'mode': mode,
        'tahapan_id': tahapan_id,
        'filters': filters,
        'search': search,
        'time_scope': time_scope,  # ⬅️ Period filtering
    }
```

---

### **2. Compute Data with Time Filter**

**File:** `kebutuhan_computed.py`
**Function:** `compute_kebutuhan_items(project, mode, tahapan_id, filters, time_scope)`

```python
def compute_kebutuhan_items(project, mode='all', tahapan_id=None, filters=None, time_scope=None):
    """
    Compute kebutuhan items with optional time filtering.

    Args:
        time_scope: dict with keys 'mode', 'start', 'end'
          - mode: 'all' | 'week_range' | 'month_range'
          - start: week/month start (e.g., "2024-W05" or "2024-01")
          - end: week/month end (e.g., "2024-W10" or "2024-03")
    """

    # ... compute items ...

    if time_scope and time_scope.get('mode') not in ('', 'all'):
        # Apply time filtering
        items = filter_items_by_time_scope(items, time_scope, project)

    return items
```

**Time Filtering Logic:**
```python
def filter_items_by_time_scope(items, time_scope, project):
    """Filter items by time range."""

    mode = time_scope.get('mode')  # 'week_range' or 'month_range'
    start = time_scope.get('start')  # '2024-W05' or '2024-01'
    end = time_scope.get('end')      # '2024-W10' or '2024-03'

    if mode == 'week_range':
        # Get week numbers from week IDs
        start_week = parse_week_id(start)  # W05 → 5
        end_week = parse_week_id(end)      # W10 → 10

        # Filter pekerjaan progress by week range
        progress_qs = PekerjaanProgressWeekly.objects.filter(
            project=project,
            week_number__gte=start_week,
            week_number__lte=end_week
        )

        # Only keep items with progress in this range
        pekerjaan_ids_in_range = progress_qs.values_list('pekerjaan_id', flat=True)
        items = [item for item in items if item['pekerjaan_id'] in pekerjaan_ids_in_range]

    elif mode == 'month_range':
        # Similar logic for months
        # ...

    return items
```

---

## ✅ VERIFICATION TESTING

### **Test Case 1: Keseluruhan Proyek**

**Steps:**
1. Open "Export dengan Opsi" modal
2. Select "Keseluruhan Proyek"
3. Select "PDF"
4. Click "Export"

**Expected:**
- URL params: NO `period_mode`, NO `period_start`, NO `period_end`
- Backend: `time_scope = None` → No filtering
- PDF includes: **ALL items** from entire project

---

### **Test Case 2: Minggu Tertentu (Week 5 → 10)**

**Steps:**
1. Open "Export dengan Opsi" modal
2. Select "Minggu Tertentu"
3. Select "Dari: Minggu 5" → "Sampai: Minggu 10"
4. Select "PDF"
5. Click "Export"

**Expected:**
- URL params:
  ```
  ?period_mode=week_range
  &period_start=2024-W05
  &period_end=2024-W10
  ```
- Backend filtering:
  ```python
  PekerjaanProgressWeekly.objects.filter(
    project=project,
    week_number__gte=5,  # Week 5
    week_number__lte=10  # Week 10
  )
  ```
- PDF includes: **ONLY items** with progress in weeks 5-10

---

### **Test Case 3: Bulan Tertentu (Jan → Mar)**

**Steps:**
1. Open "Export dengan Opsi" modal
2. Select "Bulan Tertentu"
3. Select "Dari: Januari 2024" → "Sampai: Maret 2024"
4. Select "Word"
5. Click "Export"

**Expected:**
- URL params:
  ```
  ?period_mode=month_range
  &period_start=2024-01
  &period_end=2024-03
  ```
- Backend filtering: Progress from January to March only
- Word file includes: **ONLY items** with progress in Jan-Mar

---

## 🔧 CURRENT STATUS & KNOWN ISSUES

### ✅ **Working Features:**

1. **UI/UX:**
   - ✅ Modal opens correctly
   - ✅ Period selection toggles period details visibility
   - ✅ Format selection works (PDF/Word/CSV)
   - ✅ Status messages display correctly

2. **JavaScript:**
   - ✅ Period options populated from `filterMeta`
   - ✅ Export params built correctly
   - ✅ ExportManager called without modal conflict (line 1918)
   - ✅ Modal closes automatically after success

3. **Backend:**
   - ✅ `parse_kebutuhan_query_params()` extracts time_scope
   - ✅ `compute_kebutuhan_items()` accepts time_scope parameter
   - ✅ Time filtering logic implemented

### ⚠️ **Potential Issues:**

1. **filterMeta availability:**
   - If `filterMeta.periods` is not loaded, dropdowns will be empty
   - Check: `get_filter_metadata()` API called on page load?

2. **Week/Month ID format:**
   - Week: Must be "YYYY-WNN" (e.g., "2024-W05")
   - Month: Must be "YYYY-MM" (e.g., "2024-01")
   - Backend parsing must match this format

3. **Empty results:**
   - If time range has no progress data, export will be empty
   - Should show warning message to user?

---

## 📝 SUMMARY

**"Export dengan Opsi"** adalah fitur lengkap untuk export data dengan filtering:

**✅ Strengths:**
- Complete UI/UX with modal
- Flexible period selection (all/week/month)
- Multi-format support (PDF/Word/CSV)
- Proper error handling and status messages
- Uses shared ExportManager (no duplication)

**🎯 Use Cases:**
1. Export kebutuhan material untuk periode tertentu (misal: bulan ini saja)
2. Export per minggu untuk purchase order planning
3. Export dengan filter custom (klasifikasi + periode)

**🔗 Integration:**
- Frontend: rekap_kebutuhan.html + rekap_kebutuhan.js
- Backend: views_api.py → ExportManager → compute_kebutuhan_items
- Shared component: ExportManager.js (modal loading handled correctly)
