# Dokumentasi Halaman Jadwal Kegiatan

## Daftar Isi
- [Overview](#overview)
- [Arsitektur Sistem](#arsitektur-sistem)
- [Grid View](#grid-view)
- [Gantt Chart](#gantt-chart)
- [Kurva S](#kurva-s)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

---

## Overview

### Tujuan Halaman
Halaman **Jadwal Kegiatan** (Kelola Tahapan) adalah modul manajemen proyek untuk:
- Merencanakan distribusi progress pekerjaan per periode waktu
- Memvisualisasikan timeline proyek dalam bentuk Gantt Chart
- Menganalisis kinerja proyek dengan Kurva S
- Mengelola jadwal dengan time scale fleksibel (Daily/Weekly/Monthly/Custom)

### URL Pattern
```
/detail_project/project/<project_id>/jadwal-pekerjaan/
```

### Technologies Stack
| Komponen | Technology |
|----------|------------|
| Frontend Framework | Vanilla JavaScript (Modular) |
| Grid Rendering | Custom HTML Table |
| Gantt Chart | Frappe Gantt v0.6.1 |
| S-Curve Chart | ECharts v5.4.3 |
| Styling | Bootstrap 5 + Custom CSS |
| State Management | Global State Object |

### Status Implementasi (November 2025)
- **Template aktif**: `kelola_tahapan_grid_vite.html` (digunakan oleh `jadwal_pekerjaan_view`). Template legacy masih tersedia sebagai fallback namun tidak lagi dirender.
- **Controller JavaScript**: entry Vite `static/detail_project/js/src/jadwal_kegiatan_app.js` terhubung ke endpoint Django melalui atribut `data-api-*`. Kode legacy `static/detail_project/js/kelola_tahapan_grid.js` masih ada untuk referensi sampai AG Grid menggantikan grid HTML sepenuhnya.
- **AG Grid**: dependensi berada di `package.json`, tetapi modul `modules/grid/ag-grid-setup.js` masih **TODO** (Phase 2). Saat ini grid HTML dua panel masih aktif.
- **Penyimpanan progress**: perubahan dari AG Grid dikirim ke endpoint canonical `/detail_project/api/v2/project/<project_id>/assign-weekly/` dengan payload weekly assignments (pekerjaan, week_number, proportion). Pipeline API `api_assign_pekerjaan_weekly` menjadi jalur utama save.
- **Skrip npm**: baru tersedia `dev`, `build`, `preview`, dan `watch`. Skrip `npm test`, `npm run test:integration`, dan `npm run benchmark` masih direncanakan.
- **Testing**: gunakan `pytest detail_project -n auto` untuk regresi backend. Uji manual UI diperlukan sampai harness frontend siap.

---

## Arsitektur Sistem

### File Structure
```
detail_project/
  templates/detail_project/
     kelola_tahapan_grid.html          # Template yang masih dipakai di production
     kelola_tahapan_grid_vite.html     # Template baru (belum di-wire ke view)
     kelola_tahapan/
         _grid_tab.html                # Grid view tab content
         _gantt_tab.html               # Gantt chart tab content
         _kurva_s_tab.html             # S-curve tab content

  static/detail_project/
     css/
        kelola_tahapan_grid.css        # Styling utama
        validation-enhancements.css    # Tambahan Phase 1

     js/
        kelola_tahapan_grid.js         # Legacy orchestrator (1700+ lines)
        jadwal_pekerjaan/
            kelola_tahapan_page_bootstrap.js
            kelola_tahapan/            # Legacy module folder
                module_manifest.js
                data_loader_module.js
                time_column_generator_module.js
                validation_module.js
                save_handler_module.js
                grid_module.js
                gantt_module.js
                kurva_s_module.js
                grid_tab.js
                gantt_tab.js
                kurva_s_tab.js

        # Struktur baru berbasis Vite (Phase 1)
        js/src/
            main.js
            modules/
                grid/
                    grid-event-handlers.js
                    # ag-grid-setup.js -- TODO Phase 2
                shared/
                    event-delegation.js
                    performance-utils.js
                    validation-utils.js
                gantt/
                kurva-s/
                export/
```

### State Management

#### Global State Object
```javascript
window.kelolaTahapanPageState = {
  // Project metadata
  projectId: number,
  projectStart: "YYYY-MM-DD",
  projectEnd: "YYYY-MM-DD",

  // Data collections
  tahapanList: Array<Tahapan>,      // Time periods
  pekerjaanTree: Array<TreeNode>,   // Hierarchical pekerjaan
  flatPekerjaan: Array<TreeNode>,   // Flattened pekerjaan
  timeColumns: Array<Column>,       // Generated time columns
  ganttTasks: Array<GanttTask>,     // Gantt task objects

  // Data mappings
  volumeMap: Map<pekerjaanId, volume>,
  assignmentMap: Map<"pekerjaanId-columnId", percentage>,
  modifiedCells: Map<cellKey, newValue>,
  tahapanProgressMap: Map<tahapanId, progress>,
  expandedNodes: Set<nodeId>,
  volumeResetJobs: Set<pekerjaanId>,

  // Configuration
  timeScale: "daily|weekly|monthly|custom",
  displayMode: "percentage|volume",
  weekStartDay: 0-6,  // 0=Sunday
  weekEndDay: 0-6,

  // UI references
  ganttInstance: Gantt | null,
  scurveChart: EChartsInstance | null,
  domRefs: {
    leftThead, rightThead, leftTbody, rightTbody,
    leftPanelScroll, rightPanelScroll, ganttChart, scurveChart
  },

  // Runtime state
  currentCell: HTMLElement | null,
  cache: Object,
  flags: Map
}
```

### Data Flow

#### Initialization Sequence
```
1. Page Load
   
2. kelola_tahapan_page_bootstrap.js
   - Creates app context
   - Initializes event emitter
   
3. module_manifest.js
   - Declares module metadata
   
4. kelola_tahapan_grid.js (Main Orchestrator)
   
    loadAllData() via data_loader_module
       loadTahapan()      # GET /api/project/{id}/tahapan/
       loadPekerjaan()    # GET /api/project/{id}/pekerjaan/
       loadVolumes()      # GET /api/project/{id}/volumes/
       loadAssignments()  # GET /api/v2/project/{id}/pekerjaan-progress-weekly/
   
    generateTimeColumns() via time_column_generator
       Creates column headers based on timeScale mode
   
    renderGrid() via grid_module
       renderTables() - Generates HTML
       syncHeaderHeights()
       syncRowHeights()
       setupScrollSync()
       attachEvents()
   
    initGanttChart() via gantt_module
       buildTasks()
       calculateProgress()
       new Gantt(...)
   
    initScurveChart() via kurva_s_module
        buildDataset()
        echarts.init(...)
```

#### Edit  Save Workflow
```
User clicks cell
   
enterEditMode()
   - Creates <input> element
   - Focuses and selects value
   
User enters value & presses Enter/Tab/Blur
   
exitEditMode()
   - Validates input (0-100)
   - Updates modifiedCells Map
   - Applies CSS classes (saved/modified)
   - Triggers onProgressChange event
   
onProgressChange()
   - Updates status bar counters
   - Refreshes Gantt chart
   - Refreshes S-curve chart
   
User clicks "Save All"
   
saveAllChanges() via save_handler_module
   - Groups changes by pekerjaanId
   - Validates total progress  100%
   - Converts to canonical weekly format
   - Batch POST to API
   
API Response
   - Updates assignmentMap
   - Clears modifiedCells
   - Updates cell CSS to "saved" state
   - Refreshes all views
```

#### Time Scale Switch Workflow
```
User selects new mode (e.g., Weekly  Monthly)
   
switchTimeScaleMode(newMode)
   - Shows loading overlay
   
POST /api/v2/project/{id}/regenerate-tahapan/
   - Backend converts canonical weekly data to target mode
   - Returns new tahapan list
   
Reload Data
    loadTahapan()      # New periods
    loadAssignments()  # Converted values
   
Regenerate UI
    generateTimeColumns()  # New headers
    renderGrid()           # Re-render table
    refreshGanttView()     # Update timeline
    refreshKurvaS()        # Update curve
   
Hide loading overlay
```

---

## Grid View

### Overview
Grid View adalah interface utama untuk input dan edit data progress pekerjaan. Menggunakan desain **split-panel** dengan:
- **Left Panel (Frozen)**: Hierarki pekerjaan, volume, satuan
- **Right Panel (Scrollable)**: Progress per periode waktu

### Features

#### 1. Split Panel Layout
```

 LEFT PANEL (Frozen)      RIGHT PANEL (Scrollable)             

 Tree  Uraian  Vol  Sat W1  W2  W3  W4  ...  W52      

      Klasifikasi A                                    
         Sub Klas 1                                     
           Pekerjaan 1  15% 25% 30% 20% ...             
           Pekerjaan 2   5% 10%  0%  0% ...             

```

**Keuntungan**:
- Uraian pekerjaan selalu terlihat saat scroll horizontal
- Excel-like experience
- Mudah navigate large datasets

**Implementation**: [kelola_tahapan_grid.css:143-201](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\css\kelola_tahapan_grid.css#L143-L201)

#### 2. Hierarchical Tree Structure
```javascript
// Example tree data structure
{
  id: 1,
  nama: "Pekerjaan Struktur",
  type: "klasifikasi",
  level: 0,
  children: [
    {
      id: 2,
      nama: "Pondasi",
      type: "sub-klasifikasi",
      level: 1,
      children: [
        {
          id: 101,
          nama: "Galian Tanah",
          type: "pekerjaan",
          level: 2,
          volume: 150.5,
          satuan: "m3",
          children: []
        }
      ]
    }
  ]
}
```

**Features**:
- Expand/collapse nodes dengan click icon caret
- 3 level hierarchy: Klasifikasi  Sub-Klasifikasi  Pekerjaan
- Indentation visual dengan CSS classes: `level-0`, `level-1`, `level-2`, `level-3`
- State persistence: Expanded nodes tracked di `state.expandedNodes` Set

**Implementation**: [grid_module.js:114-165](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\grid_module.js#L114-L165)

#### 3. Cell State System (3 States)

| State | Visual | Condition | CSS Class |
|-------|--------|-----------|-----------|
| **Default** | White background | No value, never saved | `.time-cell.editable` |
| **Modified** | Yellow background + left border | Changed but not saved | `.time-cell.modified` |
| **Saved** | Light blue background + bold | Persisted to database | `.time-cell.saved` |

**State Transitions**:
```
    User enters value    
 Default > Modified 
                          
                                          
                                 Save All 
                                          
                                     
                                      Saved  
                                     
                                          
                                 Edit val 
                                          
                                     
                                      Saved +  
                                      Modified 
                                     
```

**Implementation**: [kelola_tahapan_grid.css:478-540](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\css\kelola_tahapan_grid.css#L478-L540)

#### 4. Keyboard Navigation

| Key | Action |
|-----|--------|
| **Enter** | Enter edit mode |
| **Esc** | Cancel edit (restore original value) |
| **Tab** | Move to next cell (right) |
| **Shift+Tab** | Move to previous cell (left) |
| **Arrow Up** | Move to cell above |
| **Arrow Down** | Move to cell below |
| **Arrow Left/Right** | Move to adjacent cell |
| **0-9** | Enter edit mode with initial digit |

**Excel-like Behavior**:
- Pressing number key langsung masuk edit mode dengan digit tersebut
- Enter di edit mode  Save & move down
- Tab di edit mode  Save & move right

**Implementation**: [grid_module.js:385-427](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\grid_module.js#L385-L427)

#### 5. Display Mode Toggle

**Percentage Mode** (Default):
```
Cell displays: 25.0%
Meaning: 25% dari volume pekerjaan
```

**Volume Mode**:
```
Cell displays: 37.50 (m3)
Calculation: (volume  percentage) / 100
Example: 150 m3  25% = 37.50 m3
```

**Use Cases**:
- **Percentage**: Untuk planning dan tracking progress
- **Volume**: Untuk estimasi material dan resource requirements

**Implementation**: [grid_module.js:234-244](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\grid_module.js#L234-L244)

#### 6. Progress Validation Visual Feedback

Grid memberikan visual feedback untuk validasi progress total per pekerjaan:

| Status | Border Color | Background | Condition |
|--------|-------------|------------|-----------|
| **Over 100%** | Red (4px left) | Light red | Total progress > 100% |
| **Under 100%** | Yellow (4px left) | Light yellow | Total progress < 100% |
| **Complete** | Green (4px left) | Light green | Total progress = 100% |

**Purpose**:
- Mencegah alokasi berlebih (over-allocation)
- Warning untuk pekerjaan yang belum selesai dialokasikan
- Visual confirmation untuk pekerjaan yang sudah complete

**Implementation**: [kelola_tahapan_grid.css:817-847](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\css\kelola_tahapan_grid.css#L817-L847)

#### 7. Volume Reset Warning

Ketika volume pekerjaan berubah di halaman lain (Volume Pekerjaan), sistem mendeteksi:

```

  Galian Tanah  [Perlu update volume]        
   Volume: 150.5 m3                            

```

**Warning Pill**: Orange badge menunjukkan pekerjaan dengan volume yang berubah
**Purpose**: User tahu bahwa distribusi progress mungkin perlu disesuaikan

**Implementation**: [grid_module.js:118-125](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\grid_module.js#L118-L125)

#### 8. Synchronized Scrolling

**Vertical Scroll Sync**:
```javascript
// Right panel scroll triggers left panel sync
rightPanel.addEventListener('scroll', () => {
  leftPanel.scrollTop = rightPanel.scrollTop;
}, { passive: true });
```

**Row Height Sync**:
- Otomatis menyamakan tinggi row left-right panel
- Handles multi-line text di uraian pekerjaan
- Triggered on render dan tree collapse/expand

**Implementation**: [grid_module.js:655-691](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\grid_module.js#L655-L691)

### Toolbar Controls

#### Time Scale Selector
```
[ Daily ] [ Weekly ] [ Monthly ] [ Custom ]
```
- **Daily**: Satu kolom per hari
- **Weekly**: Satu kolom per minggu
- **Monthly**: Satu kolom per bulan
- **Custom**: Berdasarkan tahapan yang sudah didefinisikan

**Backend Integration**: Switching mode memanggil `/regenerate-tahapan/` API

#### Display Mode Toggle
```
[ % Percentage ] [ 123 Volume ]
```
Toggle antara tampilan persentase atau nilai volume

#### Collapse/Expand All
```
[ Collapse ] [ Expand ]
```
Mengontrol semua tree nodes sekaligus

#### Reset Progress
```
[ Reset Progress ]
```
**DESTRUCTIVE ACTION**: Menghapus semua progress assignments
- Menampilkan modal konfirmasi
- Irreversible operation
- Clears database records

#### Export Excel
```
[ Export ]
```
Generate Excel file dari grid data (future feature)

#### Save All
```
[ Save All ]
```
Batch save semua modified cells ke database dengan canonical conversion

### User Workflows

#### Workflow 1: Input Progress Baru
1. User double-click cell atau tekan Enter
2. Input field muncul dengan focus
3. User ketik nilai (0-100)
4. Tekan Enter/Tab untuk confirm
5. Cell berubah jadi state "modified" (yellow)
6. Gantt & S-curve otomatis refresh
7. Click "Save All" button
8. System validates total  100%
9. Converts to weekly canonical format
10. POST ke API
11. Cell berubah jadi state "saved" (blue bold)

#### Workflow 2: Edit Progress Existing
1. User click cell yang sudah saved (blue)
2. Double-click atau Enter untuk edit
3. Ganti nilai
4. Confirm dengan Enter/Tab
5. Cell state jadi "saved + modified" (kombinasi)
6. Follow save workflow

#### Workflow 3: Switch Time Scale Mode
1. User pilih mode baru (e.g., Weekly  Monthly)
2. System cek ada unsaved changes atau tidak
3. Jika ada, tampilkan warning confirmation
4. POST to `/regenerate-tahapan/` dengan target mode
5. Backend converts dari canonical weekly storage
6. Reload tahapan list
7. Regenerate time columns
8. Re-render entire grid
9. Refresh Gantt & S-curve

#### Workflow 4: Collapse/Expand Tree
1. User click caret icon di column tree
2. Icon rotate animation (-90deg)
3. Find all child rows based on level hierarchy
4. Toggle `.row-hidden` class
5. Re-sync row heights (karena row count berubah)
6. Update `state.expandedNodes` Set

### API Integration

#### Load Assignments
```http
GET /detail_project/api/v2/project/{project_id}/pekerjaan-progress-weekly/
```

**Response**:
```json
{
  "pekerjaan_id": {
    "tahapan_id": {
      "percentage": 25.5
    }
  }
}
```

**Transformation**: Converted to `Map<"pekerjaanId-columnId", percentage>`

#### Save Assignments
```http
POST /detail_project/api/v2/project/{project_id}/pekerjaan/{pekerjaan_id}/assignment/
Content-Type: application/json

{
  "assignments": [
    {
      "tahapan_id": 123,
      "percentage": 25.5
    }
  ]
}
```

**Canonical Storage**: All modes converted to weekly before save

### Performance Considerations

**Current Bottlenecks**:
1. **Large Datasets**: 100 pekerjaan  52 weeks = 5,200 cells
   - DOM size: ~10-15 MB
   - Render time: 2-5 seconds
2. **Scroll Sync**: No debouncing, fires on every scroll event
3. **Row Height Sync**: Forces reflow on every row (layout thrashing)

**Optimization Needed**:
- Virtual scrolling (render only visible rows)
- Debounced scroll handlers
- Batch DOM reads/writes

---

## Gantt Chart

### Overview
Gantt Chart memberikan visualisasi timeline proyek dalam format bar chart horizontal. Menampilkan:
- Timeline pekerjaan (start - end date)
- Progress bar per pekerjaan
- Hierarchical task structure
- Interactive tooltips dengan detail distribusi

### Technology
**Frappe Gantt v0.6.1**
- Open-source library
- Lightweight (~15KB gzipped)
- SVG-based rendering
- Limited customization options

### Features

#### 1. Task Building Algorithm

**Data Source**: Grid assignments (assignmentMap)

**Process**:
```javascript
1. Group assignments by pekerjaanId
2. For each pekerjaan:
   a. Find MIN startDate across all assigned columns
   b. Find MAX endDate across all assigned columns
   c. Calculate weighted average progress
   d. Build segments array (detail per period)
3. Convert to Gantt task format
4. Add hierarchical indentation
```

**Implementation**: [gantt_module.js:298-463](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\gantt_module.js#L298-L463)

#### 2. Progress Calculation (Volume-Weighted)

**Formula**:
```
Progress per Tahapan = (volume  percentage) / (volume)
```

**Example**:
```
Tahapan Week 1:
- Pekerjaan A (100 m3): 50%  Contribution: 50 m3
- Pekerjaan B (200 m3): 25%  Contribution: 50 m3
- Pekerjaan C (100 m3): 100%  Contribution: 100 m3

Total: 200 m3 completed out of 400 m3
Progress: 200/400 = 50%
```

**Why Volume-Weighted?**:
- Pekerjaan dengan volume besar memiliki impact lebih besar
- Lebih akurat untuk project dengan heterogeneous tasks
- Industry standard calculation

**Fallback**: Jika semua volume = 0, gunakan simple average

**Implementation**: [gantt_module.js:193-296](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\gantt_module.js#L193-L296)

#### 3. Task Structure

**Gantt Task Object**:
```javascript
{
  id: "pekerjaan-123",
  name: "  Galian Tanah",  // Indented for hierarchy
  start: "2024-01-15",     // ISO date format
  end: "2024-02-15",
  progress: 65.5,          // Percentage (0-100)
  custom_class: "gantt-task-complete",  // If progress >= 100
  metadata: {
    pekerjaanId: "123",
    label: "Pekerjaan Struktur / Pondasi / Galian Tanah",
    pathParts: ["Pekerjaan Struktur", "Pondasi", "Galian Tanah"],
    segments: [
      {
        label: "Week 1",
        start: "2024-01-15",
        end: "2024-01-21",
        percent: 25.0
      },
      // ... more segments
    ]
  }
}
```

**Name Indentation**:
```javascript
const indentPrefix = '\u00A0\u00A0'.repeat(Math.max(0, level - 2));
// Level 0 (Klasifikasi): No indent
// Level 1 (Sub-Klas): 2 spaces
// Level 2 (Pekerjaan): 4 spaces
```

#### 4. Custom Popup HTML

Saat user click task bar, muncul popup dengan info:

```

 Galian Tanah                        
  
 Periode: 15 Jan 2024 - 15 Feb 2024 
 Progress: 65.5%                     
                                     
 Distribusi:                         
  Week 1: 25.0%                     
  Week 2: 20.5%                     
  Week 3: 15.0%                     
  Week 4: 5.0%                      

```

**Implementation**: [gantt_module.js:484-518](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\gantt_module.js#L484-L518)

#### 5. View Mode Switching

```
[ Day ] [ Week ] [ Month ]
```

**Day Mode**: Granular view, banyak columns
**Week Mode**: Balanced (default)
**Month Mode**: High-level overview

**State Persistence**: `moduleStore.viewMode` dan `state.cache.ganttViewMode`

#### 6. Complete Task Styling

```css
.gantt .bar-wrapper.gantt-task-complete .bar {
  fill: #198754 !important;  /* Green */
  stroke: #146c43 !important;
}
```

Tasks dengan progress  100% otomatis berwarna hijau

### Toolbar Controls

#### View Mode Buttons
Click untuk switch antara Day/Week/Month granularity

### Event Handling

#### On Task Click
```javascript
on_click(task) {
  // Extract pekerjaanId from task.id
  // Emit event to app context
  window.KelolaTahapanPage.events.emit('gantt:select', {
    pekerjaanId,
    task
  });
}
```

**Potential Use Cases**:
- Highlight corresponding grid row
- Show detail panel
- Filter S-curve by selected task

#### On View Change
```javascript
on_view_change(mode) {
  // Update module state
  moduleStore.viewMode = normalizeViewMode(mode);
  // Emit event for other components
  moduleStore.emitViewChange?.(normalized);
}
```

### Resize Handling

```javascript
window.addEventListener('resize', () => {
  ganttInstance.refresh(tasks);
  ganttInstance.change_view_mode(currentViewMode);
});
```

**Issue**: No debouncing - fires on every pixel resize

### Frappe Gantt Limitations

**No Support For**:
1. Task dependencies (finish-to-start, start-to-finish)
2. Critical path highlighting
3. Drag-and-drop reschedule
4. Resource allocation view
5. Baseline comparison
6. Milestone markers
7. Zoom levels beyond Day/Week/Month

**Alternative Libraries**:
- **DHTMLX Gantt**: Commercial, full-featured
- **Bryntum Gantt**: Enterprise-grade
- **FullCalendar Timeline**: Good for scheduling
- **Custom D3.js**: Full control, high development effort

### API Integration

Gantt tidak punya API endpoint sendiri, menggunakan data dari Grid:
- `state.assignmentMap`  Source data
- `state.timeColumns`  Period definitions
- `state.volumeMap`  Volume weights

### Performance

**Good**:
- Lightweight library (~15KB)
- SVG rendering (hardware accelerated)
- Lazy rendering (only visible viewport)

**Concerns**:
- Large task count (200+) bisa slow
- Resize handler tidak debounced

---

## Kurva S

### Overview
Kurva S (S-Curve) adalah analitik chart untuk membandingkan progress **planned** vs **actual**. Bentuk kurva menyerupai huruf "S" yang merepresentasikan lifecycle proyek:
- **Start (0-25%)**: Slow ramp-up (mobilisasi, setup)
- **Middle (25-75%)**: Steep acceleration (peak productivity)
- **End (75-100%)**: Tapering (closeout, finishing)

### Technology
**ECharts v5.4.3**
- Powerful visualization library by Apache
- Feature-rich (100+ chart types)
- Excellent performance
- Responsive & interactive

### Mathematical Foundation

#### 1. Planned Curve (Hybrid Algorithm)

**Strategy Selection** (Automatic):
```
Has assignment data?
     Yes  Volume-Based Calculation
     No   Ideal S-Curve (Sigmoid)
          Fallback  Linear Distribution
```

##### Strategy 1: Volume-Based Planned Curve

**Algorithm**:
```javascript
For each time period (column):
  1. Identify pekerjaan assigned to this period
  2. Sum their TOTAL volumes (not partial)
  3. Accumulate to get cumulative planned volume
  4. Convert to percentage of total project volume
```

**Assumption**: Jika pekerjaan assigned ke period, seluruh volume-nya harus selesai di akhir period

**Example**:
```
Project: 400 m3 total
- Pekerjaan A (100 m2): Assigned to Week 1
- Pekerjaan B (200 m2): Assigned to Week 2
- Pekerjaan C (100 m2): Assigned to Week 3

Planned Curve:
Week 1: 25%  (100/400)
Week 2: 75%  (300/400)
Week 3: 100% (400/400)
```

**Implementation**: [kurva_s_module.js:205-254](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\kurva_s_module.js#L205-L254)

##### Strategy 2: Ideal S-Curve (Sigmoid Function)

**Mathematical Formula**:
```
P(t) = 100 / (1 + e^(-k(t - t0)))

Where:
  t  = time period index (0 to n-1)
  t0 = midpoint of timeline (n/2)
  k  = steepness factor (default: 0.8)
  P(t) = cumulative percentage at time t
```

**Steepness Factor Effects**:
- `k = 0.5`: Gentle S-curve (conservative schedule)
- `k = 0.8`: Moderate S-curve (**default**, balanced)
- `k = 1.2`: Steep S-curve (aggressive schedule)

**Visual Shape**:
```
100%            ___---
             _-/
           _/
 50%     _/
       _/
     _/
  0% 
     0   t0   n-1
```

**When Used**: New projects tanpa assignment data

**Research Basis**: Empirically matches typical construction project curves (Perry & Hayes, 1985)

**Implementation**: [kurva_s_module.js:287-305](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\kurva_s_module.js#L287-L305)

##### Strategy 3: Linear Fallback

**Formula**:
```
P(t) = (100 / n)  (t + 1)

Where:
  n = total periods
  t = period index (0-based)
```

**Example** (4 periods):
```
Week 1: 25%
Week 2: 50%
Week 3: 75%
Week 4: 100%
```

**When Used**: Ultimate fallback jika metode lain gagal

**Limitation**: Tidak realistis (proyek jarang linear)

**Implementation**: [kurva_s_module.js:329-339](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\kurva_s_module.js#L329-L339)

#### 2. Actual Curve (Volume-Weighted Cumulative)

**Algorithm**:
```javascript
For each time period (column):
  1. Calculate completed volume in this period:
     volume_completed = (pekerjaan_volume  percentage / 100)
  2. Add to cumulative total
  3. Convert to percentage of total project volume
```

**Example**:
```
Total Project: 400 m3

Week 1 assignments:
- Pekerjaan A (100 m3): 50%  50 m3
- Pekerjaan B (200 m3): 25%  50 m3
Total Week 1: 100 m3 (25% cumulative)

Week 2 assignments:
- Pekerjaan A: +30%  30 m3
- Pekerjaan B: +50%  100 m3
- Pekerjaan C (100 m3): 40%  40 m3
Total Week 2: 170 m3 (67.5% cumulative)

Actual Curve:
Week 1: 25.0%
Week 2: 67.5%
```

**Implementation**: [kurva_s_module.js:471-481](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\kurva_s_module.js#L471-L481)

### Variance Analysis

**Calculation**:
```javascript
Variance = Actual% - Planned%
```

**Interpretation** (with 5% tolerance):

| Variance | Status | Color | Meaning |
|----------|--------|-------|---------|
| > +5% | Ahead of Schedule | Green (#22c55e) | Faster than planned |
| -5% to +5% | On Track | Blue (#3b82f6) | Within tolerance |
| < -5% | Behind Schedule | Red (#ef4444) | Slower than planned |

**Tooltip Display**:
```
Week 5: 15 Feb - 21 Feb

Rencana: 45.0%
Aktual:  38.5%
Variance: -6.5% (Behind schedule)
```

**Implementation**: [kurva_s_module.js:549-561](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\kurva_s_module.js#L549-L561)

### Features

#### 1. Dual Line Chart

**Planned Line** (Dashed):
- Color: Blue (#0d6efd light, #60a5fa dark)
- Line style: Dashed (2px)
- Area fill: Semi-transparent blue

**Actual Line** (Solid):
- Color: Green (#198754 light, #34d399 dark)
- Line style: Solid (3px, thicker)
- Area fill: Semi-transparent green

**Visual Priority**: Actual line lebih tebal  focus on reality

#### 2. Dark Mode Support

```javascript
function getThemeColors() {
  const theme = document.documentElement.getAttribute('data-bs-theme');
  if (theme === 'dark') {
    return {
      text: '#f8fafc',
      plannedLine: '#60a5fa',  // Lighter for dark bg
      actualLine: '#34d399',
      gridLine: '#334155'      // Subtle gray
    };
  }
  // Light mode colors...
}
```

**Auto-Updates**: Detects theme changes dan re-render

#### 3. Interactive Tooltips

**Hover Behavior**:
- Trigger: Hover pada chart area
- Shows: Label, periode dates, planned%, actual%, variance
- Multi-series: Shows both lines simultaneously

**Tooltip Content**:
```html
<strong>Week 5</strong>
<div style="font-size:0.85em;color:#6b7280;">
  Periode: 15 Feb 2024 - 21 Feb 2024
</div>

Rencana: <strong>45.0%</strong>
Aktual: <strong>38.5%</strong>
Variance: <strong style="color:#ef4444;">-6.5% (Behind schedule)</strong>
```

**Implementation**: [kurva_s_module.js:536-572](D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\jadwal_pekerjaan\kelola_tahapan\kurva_s_module.js#L536-L572)

#### 4. Smooth Curves

```javascript
series: [{
  type: 'line',
  smooth: true,  // Bezier curve interpolation
  // ...
}]
```

**Effect**: Lines appear smooth rather than jagged

#### 5. Responsive Design

```javascript
function resize() {
  state.scurveChart.resize();
}
window.addEventListener('resize', resize);
```

Chart auto-adjusts dimensions saat window resize

### Chart Configuration

**ECharts Option Structure**:
```javascript
{
  backgroundColor: 'transparent',
  tooltip: { /* ... */ },
  legend: {
    data: ['Planned', 'Actual'],
    textStyle: { color: colors.text }
  },
  grid: {
    left: '4%',
    right: '4%',
    top: '12%',
    bottom: '6%',
    containLabel: true  // Prevent label clipping
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,  // Lines start at edge
    data: ['Week 1', 'Week 2', ...]
  },
  yAxis: {
    type: 'value',
    min: 0,
    max: 100,
    axisLabel: { formatter: '{value}%' }
  },
  series: [
    { name: 'Planned', /* ... */ },
    { name: 'Actual', /* ... */ }
  ]
}
```

### Use Cases

#### 1. Progress Monitoring
**Question**: "Are we on track?"
**Answer**: Compare planned vs actual curve positions

#### 2. Schedule Performance
**Question**: "Are we ahead or behind?"
**Answer**: Check variance at current period

#### 3. Trend Analysis
**Question**: "Is gap widening or narrowing?"
**Answer**: Observe slope changes over time

#### 4. Forecasting (Manual)
**Method**: Extend actual curve slope to estimate completion
**Example**: If current SPI (actual/planned) = 0.85, project will finish ~15% late

### API Integration

No dedicated API - uses grid data:
- `state.assignmentMap`  Actual progress
- `state.timeColumns`  X-axis labels
- `state.volumeMap`  Weights for calculation

### Performance

**Excellent**:
- ECharts highly optimized
- Canvas rendering (GPU accelerated)
- Handles 1000+ data points smoothly

**Optimization**: Dataset pre-calculated, chart hanya render

### Missing Features (Industry Standard)

#### 1. Earned Value Management (EVM)

**Metrics Not Implemented**:
- **PV (Planned Value)**: Budgeted cost of planned work
- **EV (Earned Value)**: Budgeted cost of completed work
- **AC (Actual Cost)**: Real cost incurred
- **SPI (Schedule Performance Index)**: EV / PV
- **CPI (Cost Performance Index)**: EV / AC
- **EAC (Estimate at Completion)**: Forecasted final cost
- **ETC (Estimate to Complete)**: Remaining cost

**Current Limitation**: Hanya schedule tracking, tidak ada cost integration

**Example EVM Chart**:
```
              EV 
            /    AC 
100%      /       PV   
        /
 50%  /
     /
  0% 
```

#### 2. Forecast Line

**What It Is**: Projected completion based on current trend

**Algorithm**:
```javascript
currentSPI = actualProgress / plannedProgress
projectedDuration = totalDuration / currentSPI
forecastCompletion = startDate + projectedDuration
```

**Visual**:
```
100%                Forecast
                  (projected)
             
 50%       Actual (current)
        
  0% 
     Now         Estimated End
```

#### 3. Baseline Comparison

**What It Is**: Compare current plan vs original baseline

**Use Case**: Track how schedule changed over time

**Visual**:
```
      Original   
      Current  
      Actual   
```

**Implementation Need**: Store historical baseline snapshots

#### 4. Multiple Scenarios

**What It Is**: Show best/worst/likely case scenarios

**Example**:
- Optimistic (SPI=1.2): Complete 2 weeks early
- Baseline (SPI=1.0): On schedule
- Pessimistic (SPI=0.8): 2 weeks late

#### 5. Export Options

**Missing**:
- Export to Excel/CSV
- Print-optimized view
- PDF report with annotations
- PNG/SVG image export

---

## API Reference

> Catatan: implementasi Vite baru masih memakai endpoint placeholder `/api/jadwal-kegiatan/...`. Seluruh endpoint resmi berada di namespace `/detail_project/api/project/<project_id>/tahapan/`. Pastikan frontend diarahkan ke endpoint resmi sebelum UAT.

### Endpoints

#### 1. Load Tahapan (Time Periods)
```http
GET /detail_project/api/project/{project_id}/tahapan/
```

**Response**:
```json
[
  {
    "id": 123,
    "tanggal_mulai": "2024-01-15",
    "tanggal_selesai": "2024-01-21",
    "nama": "Week 1",
    "tipe": "weekly",
    "tahap": 1,
    "metadata": {}
  }
]
```

#### 2. Load Pekerjaan (Tree Structure)
```http
GET /detail_project/api/project/{project_id}/pekerjaan/
```

**Response**:
```json
[
  {
    "id": 1,
    "nama": "Pekerjaan Struktur",
    "type": "klasifikasi",
    "level": 0,
    "children": [...]
  }
]
```

#### 3. Load Volumes
```http
GET /detail_project/api/project/{project_id}/volumes/
```

**Response**:
```json
{
  "123": 150.5,
  "124": 200.0
}
```

#### 4. Load Assignments (Canonical Weekly)
```http
GET /detail_project/api/v2/project/{project_id}/pekerjaan-progress-weekly/
```

**Response**:
```json
{
  "123": {
    "456": {
      "percentage": 25.5
    }
  }
}
```

**Format**: `{ pekerjaanId: { tahapanId: { percentage } } }`

#### 5. Save Assignments (Canonical Weekly)
```http
POST /detail_project/api/v2/project/{project_id}/pekerjaan/{pekerjaan_id}/assignment/
Content-Type: application/json
X-CSRFToken: {token}

{
  "assignments": [
    {
      "tahapan_id": 456,
      "percentage": 25.5
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "message": "Progress saved successfully",
  "saved_count": 5
}
```

#### 6. Regenerate Tahapan (Mode Switch)
```http
POST /detail_project/api/v2/project/{project_id}/regenerate-tahapan/
Content-Type: application/json
X-CSRFToken: {token}

{
  "time_scale": "monthly"
}
```

**Response**:
```json
{
  "success": true,
  "tahapan_count": 12,
  "message": "Tahapan regenerated successfully"
}
```

**Backend Logic**: Converts canonical weekly storage to target mode

#### 7. Reset All Progress
```http
POST /detail_project/api/v2/project/{project_id}/reset-all-progress/
Content-Type: application/json
X-CSRFToken: {token}
```

**Response**:
```json
{
  "success": true,
  "deleted_count": 150,
  "message": "All progress reset successfully"
}
```

**WARNING**: IRREVERSIBLE operation

### Canonical Storage System

#### Concept
**All time scales convert to weekly format before saving to database**

#### Why Weekly?
- Industry standard granularity
- Balance antara detail dan practicality
- Easy conversion to/from daily, monthly
- Lossless data preservation

#### Conversion Logic

**Daily  Weekly**:
```
Daily assignments already at week-level granularity
Direct 1:1 mapping to weekly canonical storage
```

**Weekly  Weekly**:
```
No conversion needed (native format)
```

**Monthly  Weekly**:
```
1. Split monthly percentage evenly to days
2. Aggregate daily values to weeks
3. Store as weekly canonical

Example:
Month 1 (31 days, 4.43 weeks): 40% progress
 Daily: 40% / 31 = 1.29% per day
 Week 1 (7 days): 1.29%  7 = 9.03%
 Week 2 (7 days): 9.03%
 Week 3 (7 days): 9.03%
 Week 4 (7 days): 9.03%
 Week 5 (3 days): 1.29%  3 = 3.87%
Total: 39.99%  40%
```

**Custom  Weekly**:
```
1. Calculate week number from tahapan start date
2. Map assignment to corresponding week
3. Store as weekly canonical
```

#### Reconstruction (Weekly  Display Mode)

**Weekly  Daily**:
```
Split week percentage evenly across 7 days
Week 1 (25%)  Mon-Sun each 3.57%
```

**Weekly  Monthly**:
```
Aggregate weeks to months
Jan: Week 1-4  Sum percentages
Feb: Week 5-8  Sum percentages
```

**Benefits**:
- Switch modes without data loss
- Single source of truth in database
- Backwards compatible

---

## Troubleshooting

### Issue 1: Grid Not Rendering

**Symptoms**:
- Blank grid area
- Console error: "Cannot read property 'pekerjaanTree' of undefined"

**Causes**:
1. Data loading failed
2. State object not initialized
3. DOM elements not found

**Debug Steps**:
```javascript
// Check state
console.log(window.kelolaTahapanPageState);

// Check data loaded
console.log(state.pekerjaanTree);
console.log(state.timeColumns);

// Check DOM
console.log(document.getElementById('left-tbody'));
console.log(document.getElementById('right-tbody'));
```

**Solution**:
- Ensure API endpoints returning valid data
- Check CSRF token present
- Verify DOM structure matches expected IDs

### Issue 2: Gantt Chart Not Showing

**Symptoms**:
- Grid works, but Gantt tab blank
- Console error: "Gantt is not defined"

**Causes**:
1. Frappe Gantt library not loaded
2. No assignments data
3. Chart container not found

**Debug Steps**:
```javascript
// Check library loaded
console.log(typeof window.Gantt);  // Should be "function"

// Check tasks built
console.log(state.ganttTasks);

// Check container
console.log(document.getElementById('gantt-chart'));
```

**Solution**:
```html
<!-- Verify script tag exists -->
<script src="https://cdn.jsdelivr.net/npm/frappe-gantt@0.6.1/dist/frappe-gantt.min.js"></script>
```

### Issue 3: S-Curve Shows Flat Lines

**Symptoms**:
- Chart renders, but both lines at 0%
- No curve shape

**Causes**:
1. No assignment data
2. All volumes = 0
3. Calculation error

**Debug Steps**:
```javascript
// Check dataset
const dataset = moduleStore.buildDataset(state);
console.log(dataset.planned);  // Should have values
console.log(dataset.actual);

// Check volumes
console.log(state.volumeMap);
```

**Solution**:
- Add some progress assignments
- Ensure volumes > 0 for pekerjaan
- Check calculation logic

### Issue 4: Save Button Not Working

**Symptoms**:
- Click "Save All"  nothing happens
- No API call in Network tab

**Causes**:
1. No modified cells
2. CSRF token missing
3. Validation failed

**Debug Steps**:
```javascript
// Check modified cells
console.log(state.modifiedCells);  // Should have entries

// Check validation
const validation = validateProgressTotals(state);
console.log(validation);

// Check CSRF
console.log(document.querySelector('[name=csrfmiddlewaretoken]'));
```

**Solution**:
- Ensure cells actually modified (yellow background)
- Verify total progress  100%
- Add CSRF token to page template

### Issue 5: Scroll Sync Not Working

**Symptoms**:
- Left and right panels scroll independently

**Causes**:
1. Event listeners not attached
2. DOM references incorrect
3. Script loaded before DOM ready

**Debug Steps**:
```javascript
// Check scroll sync bound
console.log(state.cache.gridScrollSyncBound);

// Test manually
const left = document.querySelector('.left-panel-scroll');
const right = document.querySelector('.right-panel-scroll');
left.scrollTop = 100;
console.log(right.scrollTop);  // Should be 100
```

**Solution**:
- Ensure `setupScrollSync()` called after DOM ready
- Verify panel classes correct
- Re-bind on re-render

### Issue 6: Time Scale Switch Fails

**Symptoms**:
- Select new mode  loading overlay stuck
- Console error

**Causes**:
1. API endpoint error
2. Backend conversion failed
3. Network timeout

**Debug Steps**:
```javascript
// Check API response
// Network tab  /regenerate-tahapan/
// Look for 500 errors

// Check backend logs
// Django console should show traceback
```

**Solution**:
- Check backend API implementation
- Ensure tahapan model has required fields
- Verify conversion logic handles edge cases

### Issue 7: Performance Lag with Large Datasets

**Symptoms**:
- Grid rendering takes 5+ seconds
- Scroll is janky
- Browser freezes

**Causes**:
1. Too many DOM elements (10,000+ cells)
2. No virtualization
3. Synchronous rendering blocks UI

**Temporary Workarounds**:
```javascript
// Reduce time columns
// Use Monthly instead of Daily (52 cols vs 365)

// Collapse klasifikasi
// Reduce visible rows

// Disable auto-refresh
// Prevent Gantt/S-curve refresh on every cell change
```

**Long-term Solution**:
- Implement virtual scrolling
- Batch DOM updates
- Use Web Workers for calculations

### Issue 8: Export Excel Button Does Nothing

**Symptoms**:
- Click "Export"  no download

**Cause**:
Feature not implemented yet (future)

**Workaround**:
```javascript
// Manual export via console
const data = collectGridData(state);
console.table(data);  // Copy-paste to Excel
```

### Issue 9: Memory Leak Over Time

**Symptoms**:
- Browser memory usage grows
- Page becomes slower after 10+ minutes
- Eventually crashes

**Causes**:
1. Event listeners not cleaned
2. ECharts instances not disposed
3. Circular references in state

**Debug**:
```javascript
// Chrome DevTools  Memory  Take Heap Snapshot
// Look for detached DOM nodes
// Look for large arrays/maps

// Check listeners
getEventListeners(document.querySelector('.time-cell'));
```

**Solution**:
```javascript
// Add cleanup on destroy
function cleanup() {
  // Remove event listeners
  // Dispose chart instances
  if (state.ganttInstance?.destroy) {
    state.ganttInstance.destroy();
  }
  if (state.scurveChart?.dispose) {
    state.scurveChart.dispose();
  }
}
```

### Issue 10: Dark Mode Colors Wrong

**Symptoms**:
- Switch to dark theme  chart colors not updating

**Cause**:
Chart initialized before theme switch

**Solution**:
```javascript
// Listen to theme changes
const observer = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    if (mutation.attributeName === 'data-bs-theme') {
      // Refresh charts with new colors
      refreshKurvaS();
      refreshGanttView();
    }
  });
});

observer.observe(document.documentElement, {
  attributes: true,
  attributeFilter: ['data-bs-theme']
});
```

---

## Best Practices

### For Users

1. **Save Frequently**: Modified cells (yellow) tidak otomatis saved
2. **Check Validation**: Pastikan total progress per pekerjaan = 100%
3. **Use Appropriate Time Scale**:
   - Daily untuk short projects (<3 months)
   - Weekly untuk typical projects (3-12 months)
   - Monthly untuk long projects (1+ years)
4. **Leverage Keyboard Navigation**: Lebih cepat dari mouse untuk data entry
5. **Monitor S-Curve**: Check variance weekly untuk early warning
6. **Export Before Major Changes**: Backup data sebelum reset atau mode switch

### For Developers

1. **Modular Architecture**: Keep modules loosely coupled
2. **State Immutability**: Avoid direct state mutations
3. **Event-Driven**: Use event emitter untuk cross-module communication
4. **Performance First**: Profile before adding features
5. **Graceful Degradation**: Handle missing data elegantly
6. **Error Boundaries**: Catch exceptions, don't crash entire app
7. **Logging**: Use structured logging untuk debugging
8. **Documentation**: Update docs when changing APIs

---

## Glossary

| Term | Definition |
|------|------------|
| **Tahapan** | Time period (week, month, or custom range) |
| **Pekerjaan** | Work item / task |
| **Klasifikasi** | Top-level category (level 0) |
| **Sub-Klasifikasi** | Secondary category (level 1) |
| **Assignment** | Progress percentage allocated to a time period |
| **Canonical Storage** | Weekly format in database (single source of truth) |
| **Time Scale** | Granularity mode (daily/weekly/monthly/custom) |
| **Volume** | Quantity of work (e.g., 150 m3, 200 m2) |
| **Weighted Average** | Average calculated using volume as weight |
| **S-Curve** | Cumulative progress chart shaped like letter "S" |
| **Variance** | Difference between planned and actual progress |
| **SPI** | Schedule Performance Index (Actual / Planned) |
| **Sigmoid Function** | Mathematical function creating S-shaped curve |

---

**Document Version**: 1.0
**Last Updated**: 2025-01-19
**Maintained By**: Development Team
