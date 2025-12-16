# Export Requirements Specification - Jadwal Pekerjaan
**Django AHSP Project - Complete Export Solution**

**Date**: 2025-01-15
**Status**: Requirements Gathering Complete

---

## 📋 EXPORT REQUIREMENTS

### **A. Rekap Laporan (FULL REPORT)** 📊

**Tujuan**: Laporan lengkap untuk dokumentasi proyek dan review manajemen

**Konten**:
- **A.1 Grid Views Full** - Tabel jadwal lengkap (semua pekerjaan, semua minggu)
- **A.2 Gantt Chart Full** - Visualisasi timeline lengkap (bar chart per pekerjaan)
- **A.3 Kurva S Full** - Progress kumulatif lengkap (planned vs actual)

**Format Output**:
- PDF (multi-page, professional layout)
- Word/DOCX (editable untuk presentasi)
- Excel/XLSX (data + chart sheets)

**Use Case**:
- Monthly progress report ke client
- Final project documentation
- Management review meeting

---

### **B. Laporan Bulanan (MONTHLY REPORT)** 📅

**Tujuan**: Laporan ringkas per bulan untuk monitoring progres bulanan

**Konten**:
- **B.1 Progress Bulanan Grid** - Tabel dalam mode monthly (agregasi 4 minggu)
  - Kolom: No, Nama Pekerjaan, M1 (W1-W4), M2 (W5-W8), M3 (W9-W12), dst.
  - Nilai: Total progress per bulan (sum dari 4 minggu)

- **B.2 Progress Bulanan Kurva S** - Kurva S dengan granularity bulanan
  - X-axis: M1, M2, M3, M4, ... (bukan W1, W2, W3)
  - Y-axis: Cumulative progress %
  - Series: Planned vs Actual (per bulan)

**Format Output**:
- PDF (compact, 1-2 halaman jika memungkinkan)
- Excel/XLSX (monthly summary sheet)

**Use Case**:
- Monthly stakeholder meeting
- Quick progress review
- Trend analysis per bulan

---

### **C. Laporan Mingguan (WEEKLY REPORT)** 📆

**Tujuan**: Laporan detail per minggu untuk monitoring progres harian/mingguan

**Konten**:
- **C.1 Progress Mingguan Grid** - Tabel dalam mode weekly (detail per minggu)
  - Kolom: No, Nama Pekerjaan, W1, W2, W3, W4, ... (semua minggu)
  - Nilai: Progress per minggu (canonical weekly data)

- **C.2 Progress Mingguan Kurva S** - Kurva S dengan granularity mingguan
  - X-axis: W1, W2, W3, W4, ... (semua minggu)
  - Y-axis: Cumulative progress %
  - Series: Planned vs Actual (per minggu)

**Format Output**:
- PDF (detailed, bisa multi-page)
- Excel/XLSX (weekly detail sheet)

**Use Case**:
- Weekly team meeting
- Detailed progress tracking
- Issue identification per minggu

---

## 🎯 TECHNICAL SPECIFICATIONS

### **A. Rekap Laporan (Full Report)**

#### **A.1 Grid Views Full**

**Data Source**: `PekerjaanProgressWeekly` (canonical storage)

**Table Structure**:
```
┌────┬─────────────────────────┬────────────────────────────────────────────┐
│ No │ Nama Pekerjaan          │ W1  W2  W3  W4  W5  ... W52                │
├────┼─────────────────────────┼────────────────────────────────────────────┤
│ 1  │ Pekerjaan Persiapan     │ 10% 20% 30% 40% 50% ... 100%               │
│ 2  │ Pekerjaan Tanah         │ 5%  10% 15% 20% 25% ... 100%               │
│    │ ...                     │ ... ... ... ... ... ... ...               │
└────┴─────────────────────────┴────────────────────────────────────────────┘
```

**Features**:
- Show ALL pekerjaan (hierarchy preserved: Klasifikasi → SubKlasifikasi → Pekerjaan)
- Show ALL weeks from project start to end
- Display both Planned and Actual progress (dual-row or color-coded)
- Auto page splitting for wide tables (12 weeks per page)
- Tree indentation for hierarchy

**Page Layout**:
- Orientation: Landscape (A3 recommended for wide table)
- Auto split horizontally (weeks) dan vertically (rows)
- Page headers with week ranges: "Minggu 1-12", "Minggu 13-24", dst.

---

#### **A.2 Gantt Chart Full**

**Data Source**: Canvas dari `GanttCanvasOverlay` atau `GanttChartRedesign`

**Chart Specifications**:
- Show ALL pekerjaan bars
- Time range: Project start → end (all weeks visible)
- Bar colors: Planned (blue), Actual (green), Behind schedule (red)
- Milestones markers (if any)
- Today line indicator

**Capture Method**:
```javascript
// High-resolution capture (2x DPI for print quality)
const ganttCanvas = this.ganttChart.overlay.canvas;
const dataURL = await ChartExporter.exportCanvasToPNG(ganttCanvas, {
  scale: 2,  // 2x resolution for print
  backgroundColor: '#ffffff',
  width: 3508,  // A3 landscape @ 300 DPI (297mm = 3508px)
  height: 2480  // A3 landscape @ 300 DPI (210mm = 2480px)
});
```

**PDF Rendering**:
- Full-page chart (dedicated page)
- Caption: "Gantt Chart - Jadwal Pekerjaan [Project Name]"
- Legend included
- Print-quality (300 DPI equivalent)

---

#### **A.3 Kurva S Full**

**Data Source**: Canvas dari `KurvaSUPlotChart` (uPlot)

**Chart Specifications**:
- X-axis: ALL weeks (W1, W2, W3, ... W52)
- Y-axis: Cumulative progress % (0-100%)
- Series:
  - Planned progress (blue line)
  - Actual progress (green line)
  - Ideal S-curve reference (dotted gray line)
- Grid lines for readability
- Data labels at key points

**Capture Method**:
```javascript
const kurvaSCanvas = this.kurvaSChart.chartInstance.ctx.canvas;
const dataURL = await ChartExporter.exportCanvasToPNG(kurvaSCanvas, {
  scale: 2,
  backgroundColor: '#ffffff',
  width: 2480,  // A4 landscape @ 300 DPI
  height: 1754  // A4 landscape @ 300 DPI
});
```

**PDF Rendering**:
- Full-page chart
- Caption: "Kurva S - Progress Kumulatif [Project Name]"
- Legend: Planned, Actual, Ideal
- Performance summary table below chart:
  ```
  ┌──────────────────────┬──────────┬──────────┐
  │ Metric               │ Planned  │ Actual   │
  ├──────────────────────┼──────────┼──────────┤
  │ Current Week         │ W24      │ W24      │
  │ Cumulative Progress  │ 65%      │ 58%      │
  │ Variance             │ -        │ -7%      │
  │ Status               │ -        │ Behind   │
  └──────────────────────┴──────────┴──────────┘
  ```

---

### **B. Laporan Bulanan (Monthly Report)**

#### **B.1 Progress Bulanan Grid**

**Data Transformation**: Weekly → Monthly aggregation

**Aggregation Logic**:
```javascript
// Group weeks into months (every 4 weeks)
const monthlyData = [];
for (let m = 0; m < totalMonths; m++) {
  const weekStart = m * 4 + 1;  // M1: W1-W4, M2: W5-W8, dst.
  const weekEnd = Math.min((m + 1) * 4, totalWeeks);

  const monthProgress = {
    month: m + 1,
    label: `M${m + 1}`,
    weeks: `W${weekStart}-W${weekEnd}`,
    planned: sumWeeks(weekStart, weekEnd, 'planned'),
    actual: sumWeeks(weekStart, weekEnd, 'actual')
  };

  monthlyData.push(monthProgress);
}
```

**Table Structure**:
```
┌────┬─────────────────────────┬────────────────────────────────────┐
│ No │ Nama Pekerjaan          │ M1      M2      M3      M4         │
│    │                         │ (W1-4)  (W5-8)  (W9-12) (W13-16)   │
├────┼─────────────────────────┼────────────────────────────────────┤
│ 1  │ Pekerjaan Persiapan     │ 40%     30%     20%     10%        │
│    │                         │ (35%)   (28%)   (22%)   (15%)      │
│    │                         │ Planned / (Actual)                 │
└────┴─────────────────────────┴────────────────────────────────────┘
```

**Features**:
- Compact: Max 12-16 months per page
- Each cell shows: Planned% / (Actual%)
- Color coding: Green (on track), Yellow (warning), Red (behind)
- Totals row at bottom

---

#### **B.2 Progress Bulanan Kurva S**

**Data Transformation**: Aggregate weekly cumulative to monthly cumulative

**Chart Specifications**:
- X-axis: M1, M2, M3, M4, ... (NOT W1, W2, W3)
- Y-axis: Cumulative progress %
- Data points: End of each month (week 4, 8, 12, 16, ...)

**Processing**:
```javascript
// Sample weekly cumulative data at month boundaries
const monthlyCumulativeData = [];
for (let m = 1; m <= totalMonths; m++) {
  const weekIndex = m * 4;  // Week 4, 8, 12, 16, ...
  const weeklyData = weeklyCumulativeProgress[weekIndex];

  monthlyCumulativeData.push({
    month: m,
    label: `M${m}`,
    planned: weeklyData.planned,
    actual: weeklyData.actual
  });
}
```

**Chart Rendering**:
- Fewer data points = cleaner chart
- Easier to see monthly trends
- Same visual style as full Kurva S

---

### **C. Laporan Mingguan (Weekly Report)**

#### **C.1 Progress Mingguan Grid**

**Data Source**: `PekerjaanProgressWeekly` (no aggregation)

**Table Structure**: Same as A.1 Grid Views Full

**Difference from Full Report**:
- May include **date ranges** for each week:
  ```
  W1 (06-12 Jan) | W2 (13-19 Jan) | W3 (20-26 Jan)
  ```
- May highlight **current week** with bold/color
- May include **week-over-week delta**:
  ```
  W3: 15% (+5% from W2)
  ```

---

#### **C.2 Progress Mingguan Kurva S**

**Data Source**: Weekly cumulative progress (canonical)

**Chart Specifications**: Same as A.3 Kurva S Full

**Difference from Full Report**:
- X-axis labels more detailed: "W1\n06-12 Jan"
- May include **annotations** for key events:
  - Milestones reached
  - Major delays
  - Catch-up periods
- May include **forecast line** (projected completion)

---

## 🎨 EXPORT MODAL UI DESIGN

### **Export Modal - Updated Design**

```html
<div class="modal-body">
  <!-- Step 1: Select Report Type -->
  <div class="mb-4">
    <label class="form-label fw-bold">Jenis Laporan</label>
    <div class="list-group">
      <label class="list-group-item">
        <input class="form-check-input me-2" type="radio" name="reportType" value="full" checked>
        <div>
          <strong>A. Rekap Laporan (Full Report)</strong>
          <p class="mb-0 text-muted small">Grid lengkap + Gantt Chart + Kurva S (semua minggu)</p>
        </div>
      </label>

      <label class="list-group-item">
        <input class="form-check-input me-2" type="radio" name="reportType" value="monthly">
        <div>
          <strong>B. Laporan Bulanan (Monthly Report)</strong>
          <p class="mb-0 text-muted small">Grid agregasi bulanan + Kurva S per bulan (M1, M2, M3...)</p>
        </div>
      </label>

      <label class="list-group-item">
        <input class="form-check-input me-2" type="radio" name="reportType" value="weekly">
        <div>
          <strong>C. Laporan Mingguan (Weekly Report)</strong>
          <p class="mb-0 text-muted small">Grid detail mingguan + Kurva S per minggu (W1, W2, W3...)</p>
        </div>
      </label>
    </div>
  </div>

  <!-- Step 2: Select Export Format -->
  <div class="mb-4">
    <label class="form-label fw-bold">Format Export</label>
    <div class="btn-group w-100" role="group">
      <input type="radio" class="btn-check" name="exportFormat" id="formatPDF" value="pdf" checked>
      <label class="btn btn-outline-primary" for="formatPDF">
        <i class="bi bi-file-pdf"></i> PDF
      </label>

      <input type="radio" class="btn-check" name="exportFormat" id="formatWord" value="word">
      <label class="btn btn-outline-primary" for="formatWord">
        <i class="bi bi-file-word"></i> Word
      </label>

      <input type="radio" class="btn-check" name="exportFormat" id="formatXLSX" value="xlsx">
      <label class="btn btn-outline-primary" for="formatXLSX">
        <i class="bi bi-file-excel"></i> Excel
      </label>
    </div>
  </div>

  <!-- Step 3: Export Preview -->
  <div class="alert alert-info mb-0" id="exportPreview">
    <strong>Yang akan di-export:</strong>
    <ul class="mb-0 mt-2" id="previewContent">
      <!-- Dynamic content based on selection -->
    </ul>
    <div class="mt-2">
      <small class="text-muted">
        <i class="bi bi-info-circle"></i> <span id="exportEstimate">Estimasi ukuran: ~5 MB</span>
      </small>
    </div>
  </div>
</div>
```

### **Export Preview Content (Dynamic)**

**Rekap Laporan (Full)**:
```
✓ Grid Views Full - Tabel lengkap semua minggu (52 minggu)
✓ Gantt Chart Full - Timeline lengkap semua pekerjaan
✓ Kurva S Full - Progress kumulatif lengkap (W1-W52)
✓ Metadata Proyek + Tanda Tangan
```

**Laporan Bulanan**:
```
✓ Grid Bulanan - Agregasi 4 minggu (M1, M2, M3... = 13 bulan)
✓ Kurva S Bulanan - Progress per bulan (M1-M13)
✓ Metadata Proyek + Tanda Tangan
```

**Laporan Mingguan**:
```
✓ Grid Mingguan - Detail per minggu dengan tanggal (W1-W52)
✓ Kurva S Mingguan - Progress per minggu (W1-W52)
✓ Metadata Proyek + Tanda Tangan
```

---

## 🔧 IMPLEMENTATION PLAN - REVISED

### **Phase 1: Data Preparation** (3 hours)

#### **Task 1.1: Monthly Aggregation Logic**

**File**: `detail_project/static/detail_project/js/src/modules/shared/data-aggregator.js` (NEW)

```javascript
/**
 * Aggregate weekly progress to monthly
 * @param {Array} weeklyData - Weekly progress data
 * @param {number} weeksPerMonth - Weeks per month (default: 4)
 * @returns {Array} Monthly aggregated data
 */
export function aggregateWeeklyToMonthly(weeklyData, weeksPerMonth = 4) {
  const monthlyData = [];
  const totalWeeks = weeklyData.length;
  const totalMonths = Math.ceil(totalWeeks / weeksPerMonth);

  for (let m = 0; m < totalMonths; m++) {
    const weekStart = m * weeksPerMonth;
    const weekEnd = Math.min((m + 1) * weeksPerMonth, totalWeeks);
    const weeksInMonth = weekEnd - weekStart;

    const monthData = {
      month: m + 1,
      label: `M${m + 1}`,
      weeks: `W${weekStart + 1}-W${weekEnd}`,
      weekStart: weekStart + 1,
      weekEnd: weekEnd,
      planned: 0,
      actual: 0
    };

    // Sum progress for weeks in this month
    for (let w = weekStart; w < weekEnd; w++) {
      monthData.planned += weeklyData[w]?.planned || 0;
      monthData.actual += weeklyData[w]?.actual || 0;
    }

    monthlyData.push(monthData);
  }

  return monthlyData;
}

/**
 * Sample weekly cumulative at month boundaries
 * @param {Array} weeklyCumulative - Weekly cumulative progress
 * @param {number} weeksPerMonth - Weeks per month (default: 4)
 * @returns {Array} Monthly cumulative data
 */
export function sampleMonthlyCumulative(weeklyCumulative, weeksPerMonth = 4) {
  const monthlyCumulative = [];
  const totalMonths = Math.ceil(weeklyCumulative.length / weeksPerMonth);

  for (let m = 1; m <= totalMonths; m++) {
    const weekIndex = Math.min(m * weeksPerMonth - 1, weeklyCumulative.length - 1);
    const weekData = weeklyCumulative[weekIndex];

    monthlyCumulative.push({
      month: m,
      label: `M${m}`,
      week: weekIndex + 1,
      planned: weekData.planned,
      actual: weekData.actual
    });
  }

  return monthlyCumulative;
}
```

---

#### **Task 1.2: Chart Rendering Modes**

**File**: `detail_project/static/detail_project/js/src/modules/kurva-s/uplot-chart.js` (MODIFY)

**Add Method**:
```javascript
/**
 * Render chart with monthly granularity
 * @param {Array} monthlyData - Monthly cumulative data
 */
renderMonthlyMode(monthlyData) {
  // Transform monthly data to uPlot format
  const xValues = monthlyData.map(m => m.month);
  const plannedValues = monthlyData.map(m => m.planned);
  const actualValues = monthlyData.map(m => m.actual);

  const data = [
    xValues,
    plannedValues,
    actualValues
  ];

  // Update chart options for monthly mode
  const monthlyOptions = {
    ...this.baseOptions,
    axes: [
      {
        ...this.baseOptions.axes[0],
        values: (u, vals) => vals.map(v => `M${v}`)  // Format as M1, M2, M3
      },
      this.baseOptions.axes[1]
    ]
  };

  // Render chart
  if (this.chartInstance) {
    this.chartInstance.setData(data);
  } else {
    this.chartInstance = new uPlot(monthlyOptions, data, this.container);
  }
}
```

---

### **Phase 2: Export Orchestration** (4 hours)

#### **Task 2.1: Export Coordinator**

**File**: `detail_project/static/detail_project/js/src/modules/shared/export-coordinator.js` (NEW)

```javascript
import { ChartExporter } from './chart-exporter.js';
import { aggregateWeeklyToMonthly, sampleMonthlyCumulative } from './data-aggregator.js';

/**
 * Export Coordinator - Manages different report types
 */
export class ExportCoordinator {
  constructor(app) {
    this.app = app;
  }

  /**
   * Export based on report type
   * @param {string} reportType - 'full', 'monthly', or 'weekly'
   * @param {string} format - 'pdf', 'word', or 'xlsx'
   * @param {Object} options - Additional options
   */
  async export(reportType, format, options = {}) {
    switch (reportType) {
      case 'full':
        return await this.exportFullReport(format, options);
      case 'monthly':
        return await this.exportMonthlyReport(format, options);
      case 'weekly':
        return await this.exportWeeklyReport(format, options);
      default:
        throw new Error(`Unknown report type: ${reportType}`);
    }
  }

  /**
   * Export A: Rekap Laporan (Full Report)
   */
  async exportFullReport(format, options) {
    const attachments = [];

    // A.1: Grid Views Full (handled by backend)
    // No capture needed - backend generates from database

    // A.2: Gantt Chart Full
    if (this.app.ganttChart) {
      const ganttURL = await ChartExporter.exportGanttChart(this.app.ganttChart, {
        scale: 2,
        backgroundColor: '#ffffff'
      });
      attachments.push({
        title: 'A.2 - Gantt Chart Full',
        data_url: ganttURL
      });
    }

    // A.3: Kurva S Full (weekly granularity)
    if (this.app.kurvaSChart) {
      const kurvaSURL = await ChartExporter.exportKurvaSChart(this.app.kurvaSChart, {
        scale: 2,
        backgroundColor: '#ffffff'
      });
      attachments.push({
        title: 'A.3 - Kurva S Full (Weekly)',
        data_url: kurvaSURL
      });
    }

    // Send to backend
    return await this._sendExportRequest(format, {
      report_type: 'full',
      mode: 'weekly',  // Grid in weekly mode
      attachments
    });
  }

  /**
   * Export B: Laporan Bulanan (Monthly Report)
   */
  async exportMonthlyReport(format, options) {
    const attachments = [];

    // B.1: Grid Bulanan (handled by backend with mode='monthly')
    // Backend will aggregate 4 weeks into 1 month

    // B.2: Kurva S Bulanan
    // Need to render chart in monthly mode first
    if (this.app.kurvaSChart) {
      // Get weekly cumulative data
      const weeklyCumulative = this.app.state.kurvaSData || [];

      // Sample at month boundaries
      const monthlyCumulative = sampleMonthlyCumulative(weeklyCumulative, 4);

      // Temporarily switch chart to monthly mode
      await this._renderKurvaSMonthly(monthlyCumulative);

      // Capture monthly chart
      const kurvaSURL = await ChartExporter.exportKurvaSChart(this.app.kurvaSChart, {
        scale: 2,
        backgroundColor: '#ffffff'
      });
      attachments.push({
        title: 'B.2 - Kurva S Bulanan (Monthly)',
        data_url: kurvaSURL
      });

      // Restore original weekly chart
      await this._restoreKurvaSWeekly();
    }

    return await this._sendExportRequest(format, {
      report_type: 'monthly',
      mode: 'monthly',  // Grid in monthly mode
      weeks_per_month: 4,
      attachments
    });
  }

  /**
   * Export C: Laporan Mingguan (Weekly Report)
   */
  async exportWeeklyReport(format, options) {
    const attachments = [];

    // C.1: Grid Mingguan (same as Full but with date ranges)
    // Backend handles with mode='weekly' + include_dates=true

    // C.2: Kurva S Mingguan (same as Full)
    if (this.app.kurvaSChart) {
      const kurvaSURL = await ChartExporter.exportKurvaSChart(this.app.kurvaSChart, {
        scale: 2,
        backgroundColor: '#ffffff'
      });
      attachments.push({
        title: 'C.2 - Kurva S Mingguan (Weekly)',
        data_url: kurvaSURL
      });
    }

    return await this._sendExportRequest(format, {
      report_type: 'weekly',
      mode: 'weekly',
      include_dates: true,  // Include date ranges for each week
      attachments
    });
  }

  /**
   * Send export request to backend
   * @private
   */
  async _sendExportRequest(format, payload) {
    const response = await fetch(
      `/api/project/${this.app.state.projectId}/export/jadwal-pekerjaan/${format}/`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.app.getCsrfToken()
        },
        body: JSON.stringify(payload)
      }
    );

    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }

    return response.blob();
  }

  /**
   * Temporarily render Kurva S in monthly mode
   * @private
   */
  async _renderKurvaSMonthly(monthlyData) {
    if (!this.app.kurvaSChart) return;

    // Save current state
    this._savedKurvaSData = this.app.state.kurvaSData;

    // Render monthly
    this.app.kurvaSChart.renderMonthlyMode(monthlyData);

    // Wait for render
    await new Promise(resolve => setTimeout(resolve, 100));
  }

  /**
   * Restore Kurva S to weekly mode
   * @private
   */
  async _restoreKurvaSWeekly() {
    if (!this.app.kurvaSChart || !this._savedKurvaSData) return;

    // Restore weekly mode
    this.app.kurvaSChart.renderWeeklyMode(this._savedKurvaSData);

    // Wait for render
    await new Promise(resolve => setTimeout(resolve, 100));
  }
}
```

---

### **Phase 3: Backend Enhancements** (4 hours)

#### **Task 3.1: Support Report Types in Backend**

**File**: `detail_project/views_api.py` (MODIFY)

**Update Export Functions**:
```python
@login_required
@require_http_methods(["GET", "POST"])
def export_jadwal_pekerjaan_pdf(request: HttpRequest, project_id: int):
    """Export Jadwal Pekerjaan to PDF with report type support"""
    try:
        project = _owner_or_404(project_id, request.user)
        from .exports.export_manager import ExportManager

        # Parse payload
        payload = {}
        if request.method == 'POST':
            try:
                payload = json.loads(request.body.decode('utf-8'))
            except:
                payload = {}

        # Extract parameters
        report_type = payload.get('report_type', 'full')  # 'full', 'monthly', 'weekly'
        mode = payload.get('mode', 'weekly')  # 'weekly', 'monthly'
        weeks_per_month = payload.get('weeks_per_month', 4)
        include_dates = payload.get('include_dates', False)
        attachments = _parse_export_attachments_from_payload(payload)

        manager = ExportManager(project, request.user)
        return manager.export_jadwal_pekerjaan(
            format_type='pdf',
            report_type=report_type,
            mode=mode,
            weeks_per_month=weeks_per_month,
            include_dates=include_dates,
            attachments=attachments
        )
    except Http404:
        raise
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'status': 'error', 'message': f'Export PDF gagal: {str(e)}'}, status=500)


def _parse_export_attachments_from_payload(payload: dict):
    """Parse attachments from JSON payload (not just request.body)"""
    attachments = []
    for att in payload.get("attachments", []):
        data_url = att.get("data_url") or att.get("dataUrl")
        title = att.get("title") or "Lampiran"
        if not data_url or not isinstance(data_url, str):
            continue
        if "base64," not in data_url:
            continue
        try:
            b64 = data_url.split("base64,", 1)[1]
            blob = base64.b64decode(b64)
            attachments.append({"title": title, "bytes": blob})
        except Exception:
            continue
    return attachments
```

---

#### **Task 3.2: Update Export Manager**

**File**: `detail_project/exports/export_manager.py` (MODIFY)

**Update Method Signature**:
```python
def export_jadwal_pekerjaan(
    self,
    format_type: str,
    report_type: str = 'full',
    mode: str = 'weekly',
    weeks_per_month: int = 4,
    include_dates: bool = False,
    attachments: list | None = None
) -> HttpResponse:
    """
    Export Jadwal Pekerjaan with different report types

    Args:
        format_type: 'csv', 'pdf', 'word', or 'xlsx'
        report_type: 'full', 'monthly', or 'weekly'
        mode: 'weekly' or 'monthly' (for grid aggregation)
        weeks_per_month: Number of weeks per month (default: 4)
        include_dates: Include date ranges for weeks (default: False)
        attachments: List of chart images

    Returns:
        HttpResponse with exported file
    """
    # Create config with report type metadata
    config = self._create_config()
    config.report_type = report_type
    config.mode = mode

    # Get data from adapter
    adapter = JadwalPekerjaanExportAdapter(
        self.project,
        include_monthly=(mode == 'monthly'),
        weeks_per_month=weeks_per_month,
        include_dates=include_dates
    )
    data = adapter.get_export_data()

    # Add report type to data
    data['report_type'] = report_type
    data['mode'] = mode

    # Add attachments
    if attachments:
        data["attachments"] = attachments

    # Export
    exporter_class = self.EXPORTER_MAP.get(format_type)
    if not exporter_class:
        raise ValueError(f"Unsupported format: {format_type}")

    exporter = exporter_class(config)
    return exporter.export(data)
```

---

### **Phase 4: PDF Layout Enhancements** (3 hours)

#### **Task 4.1: Report Type Headers**

**File**: `detail_project/exports/pdf_exporter.py` (MODIFY)

**Add Report Type Title Pages**:
```python
def _add_report_type_cover(self, story, report_type):
    """Add cover page based on report type"""
    from reportlab.platypus import Paragraph, Spacer, PageBreak
    from reportlab.lib.units import mm

    titles = {
        'full': 'REKAP LAPORAN JADWAL PEKERJAAN\n(Full Report)',
        'monthly': 'LAPORAN BULANAN JADWAL PEKERJAAN\n(Monthly Report)',
        'weekly': 'LAPORAN MINGGUAN JADWAL PEKERJAAN\n(Weekly Report)'
    }

    subtitles = {
        'full': 'Berisi: Grid Lengkap (Weekly) + Gantt Chart + Kurva S',
        'monthly': 'Berisi: Grid Bulanan (4 Minggu) + Kurva S Bulanan',
        'weekly': 'Berisi: Grid Mingguan (Detail) + Kurva S Mingguan'
    }

    title = titles.get(report_type, 'LAPORAN JADWAL PEKERJAAN')
    subtitle = subtitles.get(report_type, '')

    title_style = ParagraphStyle(
        'ReportTitle',
        fontSize=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=10*mm
    )

    subtitle_style = ParagraphStyle(
        'ReportSubtitle',
        fontSize=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4a5568'),
        spaceAfter=20*mm
    )

    story.append(Spacer(1, 50*mm))
    story.append(Paragraph(title, title_style))
    story.append(Paragraph(subtitle, subtitle_style))
    story.append(PageBreak())
```

---

## 📊 IMPLEMENTATION SUMMARY

### **Total Effort**: **14 hours**

| Phase | Tasks | Hours |
|-------|-------|-------|
| **Phase 1: Data Preparation** | Monthly aggregation, Chart modes | 3 |
| **Phase 2: Export Orchestration** | Export coordinator, Report logic | 4 |
| **Phase 3: Backend Enhancements** | API updates, Mode support | 4 |
| **Phase 4: PDF Layout** | Report type covers, Sections | 3 |

---

## ✅ DELIVERABLES CHECKLIST

### **A. Rekap Laporan (Full)**
- [ ] A.1 - Grid Views Full (Weekly mode, all weeks)
- [ ] A.2 - Gantt Chart Full (Canvas capture @ 2x DPI)
- [ ] A.3 - Kurva S Full (Weekly granularity, W1-W52)
- [ ] Professional PDF layout with cover page
- [ ] Word export with editable charts
- [ ] Excel export with data + chart sheets

### **B. Laporan Bulanan (Monthly)**
- [ ] B.1 - Grid Bulanan (4-week aggregation, M1-M13)
- [ ] B.2 - Kurva S Bulanan (Monthly granularity, M1-M13)
- [ ] Monthly data aggregation logic
- [ ] Compact PDF layout (1-2 pages)
- [ ] Excel monthly summary sheet

### **C. Laporan Mingguan (Weekly)**
- [ ] C.1 - Grid Mingguan (Weekly mode with dates)
- [ ] C.2 - Kurva S Mingguan (Weekly granularity, W1-W52)
- [ ] Week date ranges in headers
- [ ] Detailed PDF layout

### **UI/UX**
- [ ] Export modal with report type selection
- [ ] Format selection (PDF/Word/Excel)
- [ ] Export preview
- [ ] Progress indicator
- [ ] Success/error feedback

---

**Ready to implement?** Ini adalah rencana lengkap untuk 3 jenis laporan export. Apakah ada yang perlu disesuaikan sebelum saya mulai implementasi?
