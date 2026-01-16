# Export Pagination & Overflow Strategy
**Django AHSP Project - Smart Table Splitting**

**Date**: 2025-01-15
**Purpose**: Handle large datasets with intelligent row/column pagination

---

## 🎯 THE PROBLEM

### **Scenario 1: Too Many Columns (Weeks)**
- Project duration: 52 weeks
- A4 Landscape width: 277mm
- Static columns (No, Nama): ~80mm
- Available for weeks: ~197mm
- Week column width: ~12mm minimum
- **Maximum weeks per page: ~16 columns**
- **Result**: Need to split horizontally into 4 pages (52 ÷ 16 = 3.25 → 4 pages)

### **Scenario 2: Too Many Rows (Pekerjaan)**
- Project has: 150 pekerjaan
- A4 height: 210mm
- Header + margins: ~40mm
- Available for rows: ~170mm
- Row height: ~6mm
- **Maximum rows per page: ~28 rows**
- **Result**: Need to split vertically into 6 pages (150 ÷ 28 = 5.36 → 6 pages)

### **Scenario 3: Both Too Many (52 weeks × 150 rows)**
- **Horizontal splits**: 4 pages (week ranges)
- **Vertical splits**: 6 pages (row ranges)
- **Total pages**: 4 × 6 = **24 pages**

---

## ❌ BAD PAGINATION (Current Risk)

### **Problem 1: Random Column Cuts**
```
Page 1: W1, W2, W3, W4, W5, W6, W7, W8, W9, W10, W11, W12, W13, W14, W15, W16
Page 2: W17, W18, W19, W20, W21, ...
```
**Issues**:
- No logical grouping
- Hard to correlate weeks across pages
- Month boundaries split randomly

---

### **Problem 2: Mid-Hierarchy Row Cuts**
```
Page 1:
  Klasifikasi A
    Sub A.1
      Pekerjaan 1
      Pekerjaan 2
Page 2:
      Pekerjaan 3  <-- LOST CONTEXT! Where is parent?
      Pekerjaan 4
```
**Issues**:
- Parent context lost on page break
- Hierarchy broken
- Unclear which klasifikasi/sub-klasifikasi

---

## ✅ SMART PAGINATION STRATEGY

### **Strategy 1: Semantic Column Grouping**

**Monthly Boundaries** (Preferred for Weekly Mode)
```
Page 1: W1-W4   (Month 1)
Page 2: W5-W8   (Month 2)
Page 3: W9-W12  (Month 3)
Page 4: W13-W16 (Month 4)
...
```

**Benefits**:
- ✅ Natural monthly grouping
- ✅ Easy to correlate across pages
- ✅ Page headers clearly labeled: "Bulan 1 (W1-W4)"
- ✅ Consistent 4-week chunks

**Implementation**:
```javascript
/**
 * Split weeks into month-based chunks
 * @param {number} totalWeeks - Total project weeks
 * @param {number} weeksPerMonth - Weeks per month (default: 4)
 * @returns {Array} Array of {start, end, label}
 */
function splitWeeksIntoMonthChunks(totalWeeks, weeksPerMonth = 4) {
  const chunks = [];
  const totalMonths = Math.ceil(totalWeeks / weeksPerMonth);

  for (let m = 0; m < totalMonths; m++) {
    const start = m * weeksPerMonth + 1;
    const end = Math.min((m + 1) * weeksPerMonth, totalWeeks);

    chunks.push({
      month: m + 1,
      start,
      end,
      label: `Bulan ${m + 1} (W${start}-W${end})`,
      weeks: end - start + 1
    });
  }

  return chunks;
}

// Example:
// totalWeeks = 52
// Result:
// [
//   {month: 1, start: 1,  end: 4,  label: "Bulan 1 (W1-W4)",   weeks: 4},
//   {month: 2, start: 5,  end: 8,  label: "Bulan 2 (W5-W8)",   weeks: 4},
//   ...
//   {month: 13, start: 49, end: 52, label: "Bulan 13 (W49-W52)", weeks: 4}
// ]
```

---

### **Strategy 2: Hierarchy-Aware Row Splitting**

**Keep Parent Context on Page Breaks**

**Rule 1: Never Split Within Sub-Klasifikasi**
```
✅ GOOD:
Page 1:
  Klasifikasi A
    Sub A.1
      Pekerjaan 1
      Pekerjaan 2
      Pekerjaan 3
    [End of page - complete sub-klasifikasi]

Page 2:
  Klasifikasi A (continued)  <-- REPEAT PARENT
    Sub A.2                   <-- NEW SUB
      Pekerjaan 4
      Pekerjaan 5

❌ BAD:
Page 1:
  Klasifikasi A
    Sub A.1
      Pekerjaan 1
      Pekerjaan 2
Page 2:
      Pekerjaan 3  <-- NO CONTEXT!
```

**Rule 2: Repeat Parent Headers on Continuation**
```
Page N (continuation):
┌──────────────────────────────────────────┐
│ LANJUTAN - Klasifikasi A                 │  <-- Clear continuation marker
│          - Sub-Klasifikasi A.2           │
├──────────────────────────────────────────┤
│ No │ Nama Pekerjaan   │ W1  W2  W3 ...   │
├────┼──────────────────┼──────────────────┤
│ 15 │   Pekerjaan 4    │ 10% 20% 30% ...  │
│ 16 │   Pekerjaan 5    │ 15% 25% 35% ...  │
└────┴──────────────────┴──────────────────┘
```

**Implementation**:
```python
def split_rows_by_hierarchy(rows, max_rows_per_page=28):
    """
    Split rows intelligently by hierarchy boundaries

    Rules:
    1. Try to keep sub-klasifikasi complete on one page
    2. If sub-klasifikasi > max_rows, split but repeat parent headers
    3. Never orphan pekerjaan without parent context

    Returns:
        List of page chunks with metadata
    """
    pages = []
    current_page = []
    current_count = 0

    current_klasifikasi = None
    current_sub_klasifikasi = None

    for row in rows:
        row_type = row.get('type')  # 'klasifikasi', 'sub_klasifikasi', 'pekerjaan'

        # Update current context
        if row_type == 'klasifikasi':
            current_klasifikasi = row
            current_sub_klasifikasi = None
        elif row_type == 'sub_klasifikasi':
            current_sub_klasifikasi = row

        # Check if adding this row would exceed page limit
        if current_count > 0 and current_count + 1 > max_rows_per_page:
            # Check if we're in middle of sub-klasifikasi
            if row_type == 'pekerjaan' and current_sub_klasifikasi:
                # Look ahead to see if sub-klasifikasi ends soon
                remaining_in_sub = count_remaining_in_sub_klasifikasi(row, rows)

                if remaining_in_sub <= 3:
                    # Just a few more, keep on same page
                    pass
                else:
                    # Too many, split here and add continuation header
                    pages.append({
                        'rows': current_page,
                        'count': current_count,
                        'continuation': False
                    })

                    # Start new page with parent context
                    current_page = []
                    current_count = 0

                    # Add continuation header
                    if current_klasifikasi:
                        current_page.append({
                            'type': 'continuation_header',
                            'klasifikasi': current_klasifikasi['nama'],
                            'sub_klasifikasi': current_sub_klasifikasi['nama'] if current_sub_klasifikasi else None
                        })
                        current_count += 1

        # Add row to current page
        current_page.append(row)
        current_count += 1

    # Add last page
    if current_page:
        pages.append({
            'rows': current_page,
            'count': current_count,
            'continuation': False
        })

    return pages
```

---

### **Strategy 3: Grid Matrix Pagination**

**When BOTH rows and columns exceed limits, create matrix pagination**

**Example: 52 weeks × 150 rows → 4 horizontal × 6 vertical = 24 pages**

**Page Numbering**:
```
┌─────────────────────────────────────────────────────┐
│ Page 1/24: Rows 1-28, Bulan 1 (W1-W4)              │
│ Page 2/24: Rows 1-28, Bulan 2 (W5-W8)              │
│ Page 3/24: Rows 1-28, Bulan 3 (W9-W12)             │
│ Page 4/24: Rows 1-28, Bulan 4 (W13-W16)            │
│ Page 5/24: Rows 29-56, Bulan 1 (W1-W4)             │
│ ...                                                 │
│ Page 24/24: Rows 141-150, Bulan 13 (W49-W52)       │
└─────────────────────────────────────────────────────┘
```

**Page Headers Include**:
- Page number and total (1/24, 2/24, etc.)
- Row range ("Baris 1-28 dari 150")
- Week range ("Bulan 1: W1-W4 dari 52 minggu")
- Continuation markers if applicable

**Implementation**:
```python
def create_page_matrix(rows, weeks, max_rows=28, weeks_per_page=4):
    """
    Create matrix pagination for large datasets

    Args:
        rows: List of row data (with hierarchy)
        weeks: Total number of weeks
        max_rows: Maximum rows per page
        weeks_per_page: Weeks per horizontal chunk (usually 4 = 1 month)

    Returns:
        List of page specifications
    """
    # Split rows vertically (hierarchy-aware)
    row_chunks = split_rows_by_hierarchy(rows, max_rows)

    # Split weeks horizontally (month boundaries)
    week_chunks = split_weeks_into_month_chunks(weeks, weeks_per_page)

    # Create matrix
    pages = []
    page_num = 1
    total_pages = len(row_chunks) * len(week_chunks)

    for row_idx, row_chunk in enumerate(row_chunks):
        for week_idx, week_chunk in enumerate(week_chunks):
            page = {
                'page_number': page_num,
                'total_pages': total_pages,
                'row_chunk': row_chunk,
                'week_chunk': week_chunk,
                'row_range': {
                    'start': row_chunk['start_index'],
                    'end': row_chunk['end_index'],
                    'total': len(rows)
                },
                'week_range': {
                    'start': week_chunk['start'],
                    'end': week_chunk['end'],
                    'total': weeks,
                    'label': week_chunk['label']
                },
                'is_continuation': row_chunk.get('continuation', False)
            }

            pages.append(page)
            page_num += 1

    return pages
```

---

## 📄 PAGE HEADER DESIGN

### **Standard Page Header** (All Pages)

```
┌─────────────────────────────────────────────────────────────────┐
│ LAPORAN JADWAL PEKERJAAN                      Halaman 5 / 24    │
│ [Project Name]                                [Export Date]     │
├─────────────────────────────────────────────────────────────────┤
│ Periode: Bulan 2 (W5-W8)                                        │
│ Baris: 29-56 dari 150                                           │
├─────────────────────────────────────────────────────────────────┤
```

### **Continuation Header** (When Split Mid-Hierarchy)

```
┌─────────────────────────────────────────────────────────────────┐
│ ⚠️ LANJUTAN - Klasifikasi A > Sub-Klasifikasi A.2              │
├─────────────────────────────────────────────────────────────────┤
│ No │ Nama Pekerjaan              │ W5   W6   W7   W8           │
├────┼─────────────────────────────┼─────────────────────────────┤
```

### **Static Column Repetition** (Every Horizontal Split)

**Every horizontal page split repeats static columns**:
```
Page 1 (W1-W4):
┌────┬──────────────────┬────────────────┐
│ No │ Nama Pekerjaan   │ W1  W2  W3  W4 │
└────┴──────────────────┴────────────────┘

Page 2 (W5-W8):
┌────┬──────────────────┬────────────────┐  <-- REPEAT static columns
│ No │ Nama Pekerjaan   │ W5  W6  W7  W8 │
└────┴──────────────────┴────────────────┘
```

---

## 🎨 VISUAL INDICATORS

### **1. Page Break Markers** (PDF Only)

**Between Pages in Print View**:
```
─────────────────── End of Page 5 ───────────────────
─────────────────── Start of Page 6 ─────────────────
```

### **2. Continuation Arrows** (Excel/Word)

**In Excel**: Use frozen panes + cell comments
```
┌────┬──────────────────┬────────────────┐
│ No │ Nama Pekerjaan ↓ │ W5  W6  W7  W8 │  <-- Arrow indicates continuation
├────┼──────────────────┼────────────────┤
```

**In Word**: Use section breaks with repeated headers

### **3. Color Coding**

**Hierarchy Levels**:
- Klasifikasi row: Light blue background
- Sub-Klasifikasi row: Light yellow background
- Pekerjaan row: White background
- Continuation header: Light orange background (warning)

---

## 🔧 IMPLEMENTATION

### **Phase 1: Backend Pagination Logic** (2 hours)

#### **File**: `detail_project/exports/pagination_engine.py` (NEW)

```python
"""
Pagination Engine for Export System

Handles intelligent splitting of large datasets across pages
with hierarchy preservation and semantic grouping.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class WeekChunk:
    """Represents a horizontal chunk of weeks"""
    month: int
    start_week: int
    end_week: int
    label: str
    weeks_count: int


@dataclass
class RowChunk:
    """Represents a vertical chunk of rows"""
    start_index: int
    end_index: int
    rows: List[Dict]
    row_count: int
    is_continuation: bool
    parent_context: Dict = None


@dataclass
class PageSpec:
    """Complete page specification"""
    page_number: int
    total_pages: int
    row_chunk: RowChunk
    week_chunk: WeekChunk
    has_continuation: bool


class PaginationEngine:
    """
    Smart pagination engine for export system
    """

    def __init__(
        self,
        max_rows_per_page: int = 28,
        weeks_per_horizontal_chunk: int = 4,
        min_sub_klasifikasi_rows: int = 3
    ):
        """
        Initialize pagination engine

        Args:
            max_rows_per_page: Maximum rows per page (vertical)
            weeks_per_horizontal_chunk: Weeks per page (horizontal, usually 4 = 1 month)
            min_sub_klasifikasi_rows: Minimum rows to keep sub-klasifikasi together
        """
        self.max_rows_per_page = max_rows_per_page
        self.weeks_per_chunk = weeks_per_horizontal_chunk
        self.min_sub_rows = min_sub_klasifikasi_rows

    def split_weeks(self, total_weeks: int) -> List[WeekChunk]:
        """
        Split weeks into month-based chunks

        Args:
            total_weeks: Total project weeks

        Returns:
            List of WeekChunk objects
        """
        chunks = []
        total_months = (total_weeks + self.weeks_per_chunk - 1) // self.weeks_per_chunk

        for m in range(total_months):
            start = m * self.weeks_per_chunk + 1
            end = min((m + 1) * self.weeks_per_chunk, total_weeks)
            weeks_count = end - start + 1

            chunk = WeekChunk(
                month=m + 1,
                start_week=start,
                end_week=end,
                label=f"Bulan {m + 1} (W{start}-W{end})",
                weeks_count=weeks_count
            )
            chunks.append(chunk)

        return chunks

    def split_rows(self, rows: List[Dict]) -> List[RowChunk]:
        """
        Split rows with hierarchy awareness

        Args:
            rows: List of row dictionaries with 'type' field
                  ('klasifikasi', 'sub_klasifikasi', 'pekerjaan')

        Returns:
            List of RowChunk objects
        """
        chunks = []
        current_chunk_rows = []
        start_index = 0

        current_klasifikasi = None
        current_sub = None

        for i, row in enumerate(rows):
            row_type = row.get('type', 'pekerjaan')

            # Track hierarchy context
            if row_type == 'klasifikasi':
                current_klasifikasi = row
                current_sub = None
            elif row_type == 'sub_klasifikasi':
                current_sub = row

            # Check if page is full
            if len(current_chunk_rows) >= self.max_rows_per_page:
                # Check if we're mid sub-klasifikasi
                if row_type == 'pekerjaan' and current_sub:
                    # Look ahead
                    remaining = self._count_remaining_in_sub(i, rows)

                    if remaining > self.min_sub_rows:
                        # Too many remaining, split here
                        chunk = RowChunk(
                            start_index=start_index,
                            end_index=i - 1,
                            rows=current_chunk_rows,
                            row_count=len(current_chunk_rows),
                            is_continuation=False
                        )
                        chunks.append(chunk)

                        # Start new chunk with continuation
                        current_chunk_rows = []
                        start_index = i

                        # Add continuation context (will be rendered as header)
                        if current_klasifikasi and current_sub:
                            continuation_header = {
                                'type': 'continuation_header',
                                'klasifikasi': current_klasifikasi.get('nama'),
                                'sub_klasifikasi': current_sub.get('nama')
                            }
                            chunk.parent_context = continuation_header

            # Add row to current chunk
            current_chunk_rows.append(row)

        # Add final chunk
        if current_chunk_rows:
            chunk = RowChunk(
                start_index=start_index,
                end_index=len(rows) - 1,
                rows=current_chunk_rows,
                row_count=len(current_chunk_rows),
                is_continuation=False
            )
            chunks.append(chunk)

        return chunks

    def _count_remaining_in_sub(self, current_index: int, rows: List[Dict]) -> int:
        """Count remaining pekerjaan in current sub-klasifikasi"""
        count = 0
        for i in range(current_index, len(rows)):
            row_type = rows[i].get('type', 'pekerjaan')
            if row_type in ('klasifikasi', 'sub_klasifikasi'):
                break
            count += 1
        return count

    def create_page_matrix(
        self,
        rows: List[Dict],
        total_weeks: int
    ) -> List[PageSpec]:
        """
        Create complete page matrix

        Args:
            rows: All row data
            total_weeks: Total project weeks

        Returns:
            List of PageSpec objects (one per page)
        """
        row_chunks = self.split_rows(rows)
        week_chunks = self.split_weeks(total_weeks)

        pages = []
        page_num = 1
        total_pages = len(row_chunks) * len(week_chunks)

        for row_chunk in row_chunks:
            for week_chunk in week_chunks:
                page = PageSpec(
                    page_number=page_num,
                    total_pages=total_pages,
                    row_chunk=row_chunk,
                    week_chunk=week_chunk,
                    has_continuation=row_chunk.parent_context is not None
                )

                pages.append(page)
                page_num += 1

        return pages
```

---

### **Phase 2: PDF Renderer Integration** (2 hours)

#### **File**: `detail_project/exports/pdf_exporter.py` (MODIFY)

**Add Smart Pagination**:
```python
def _render_paginated_table(self, story, data):
    """
    Render table with smart pagination

    Args:
        story: ReportLab story
        data: Export data with rows and weeks
    """
    from .pagination_engine import PaginationEngine

    # Initialize pagination engine
    engine = PaginationEngine(
        max_rows_per_page=28,
        weeks_per_horizontal_chunk=4
    )

    # Create page matrix
    rows = data.get('rows', [])
    total_weeks = data.get('total_weeks', 0)
    pages = engine.create_page_matrix(rows, total_weeks)

    # Render each page
    for page in pages:
        # Add page header
        self._add_page_header(story, page)

        # Add continuation header if needed
        if page.has_continuation:
            self._add_continuation_header(story, page.row_chunk.parent_context)

        # Render table for this page
        self._render_table_page(
            story,
            rows=page.row_chunk.rows,
            start_week=page.week_chunk.start_week,
            end_week=page.week_chunk.end_week
        )

        # Add page break (except last page)
        if page.page_number < page.total_pages:
            story.append(PageBreak())
```

---

### **Phase 3: Excel Multi-Sheet Strategy** (1 hour)

**For Excel, use multi-sheet approach**:

**Sheet 1: Full Data (All Rows, Monthly Columns)**
- All rows visible
- Columns grouped by month (M1, M2, M3...)
- Frozen first 2 columns (No, Nama)
- Horizontal scroll for months

**Sheet 2-N: Monthly Detail Sheets**
- One sheet per month
- Sheet name: "Bulan 1 (W1-W4)", "Bulan 2 (W5-W8)", etc.
- All rows visible
- Weekly columns for that month only

---

## 📊 EXPECTED RESULTS

### **Before** (Poor Pagination):
❌ Weeks split randomly (W1-W16, W17-W32...)
❌ Rows cut mid-hierarchy
❌ No parent context on continuation
❌ Confusing page breaks
❌ Hard to correlate data across pages

### **After** (Smart Pagination):
✅ Weeks grouped by month (W1-W4, W5-W8...)
✅ Hierarchy preserved (sub-klasifikasi kept together)
✅ Clear continuation markers with parent context
✅ Professional page headers with ranges
✅ Easy to correlate data across pages
✅ Print-ready quality

---

## 🎯 IMPLEMENTATION CHECKLIST

- [ ] Create `pagination_engine.py` module
- [ ] Implement `split_weeks()` with month boundaries
- [ ] Implement `split_rows()` with hierarchy awareness
- [ ] Implement `create_page_matrix()`
- [ ] Integrate with PDF exporter
- [ ] Add page headers with ranges
- [ ] Add continuation headers
- [ ] Test with large dataset (100+ rows, 52 weeks)
- [ ] Test hierarchy preservation
- [ ] Test edge cases (odd week counts, single sub-klasifikasi)

---

**Effort**: **5 hours** (includes testing)

**Priority**: **CRITICAL** (Required for professional export quality)

---

**Ready to implement?** Sistem pagination ini akan memastikan export tetap rapi dan profesional bahkan untuk proyek besar dengan 100+ pekerjaan dan 52+ minggu.
