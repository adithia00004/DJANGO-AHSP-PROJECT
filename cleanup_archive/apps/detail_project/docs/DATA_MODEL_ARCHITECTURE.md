# Data Model Architecture: Time Columns & Progress Tracking

**Date**: 2025-11-23
**Purpose**: Document the data model architecture for time columns and progress tracking

---

## 📊 ARCHITECTURE OVERVIEW

### Three-Layer Model

```
┌─────────────────────────────────────────────────────────────────┐
│                     TIME PERIODS (TahapPelaksanaan)             │
│  - Defines project time periods/stages                          │
│  - Auto-generated (daily/weekly/monthly) OR manual              │
│  - Source for TimeColumnGenerator                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              ASSIGNMENTS (PekerjaanTahapan)                     │
│  - Links pekerjaan to tahapan with volume proportion            │
│  - DERIVED from PekerjaanProgressWeekly (view layer)            │
│  - Can be regenerated when switching time scale modes           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         CANONICAL STORAGE (PekerjaanProgressWeekly)             │
│  - Single source of truth for progress data                     │
│  - Weekly granularity (never deleted on mode switch)            │
│  - Independent of TahapPelaksanaan                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ MODEL DETAILS

### 1. TahapPelaksanaan (Time Periods)

**Purpose**: Defines time periods/stages for the project

**Fields**:
```python
class TahapPelaksanaan(models.Model):
    project = ForeignKey('dashboard.Project')
    nama = CharField(max_length=200)  # e.g., "Week 1"
    urutan = IntegerField()  # Sort order
    deskripsi = TextField(blank=True)
    tanggal_mulai = DateField(null=True, blank=True)
    tanggal_selesai = DateField(null=True, blank=True)

    # Auto-generation tracking
    is_auto_generated = BooleanField(default=False)
    generation_mode = CharField(
        max_length=10,
        choices=[('daily', 'Daily'), ('weekly', 'Weekly'),
                 ('monthly', 'Monthly'), ('custom', 'Custom')],
        null=True, blank=True
    )
```

**Key Points**:
- ✅ This is what TimeColumnGenerator reads from
- ✅ Can be auto-generated or manually created
- ✅ Filtered by `is_auto_generated` and `generation_mode` in different time scale modes
- ✅ Each tahapan becomes a column in the grid

**Generation Modes**:
- **Daily**: Auto-generated daily periods
- **Weekly**: Auto-generated weekly periods (7 days)
- **Monthly**: Auto-generated monthly periods
- **Custom**: Manually created periods (any duration)

**Management Command**:
```bash
# Generate 12 weekly tahapan
python manage.py generate_sample_weekly_tahapan 110 --weeks 12
```

---

### 2. PekerjaanTahapan (Assignments)

**Purpose**: Links pekerjaan to tahapan with volume proportion

**Fields**:
```python
class PekerjaanTahapan(models.Model):
    pekerjaan = ForeignKey('Pekerjaan')
    tahapan = ForeignKey(TahapPelaksanaan)
    proporsi_volume = DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.01), MaxValueValidator(100.00)]
    )
    catatan = TextField(blank=True)
```

**Key Points**:
- ⚠️ This is a **VIEW LAYER** - derived from PekerjaanProgressWeekly
- ⚠️ Can be regenerated when switching time scale modes
- ✅ Used by frontend to display assignments in grid cells
- ✅ Total proportion per pekerjaan should sum to 100%

**Important Notes**:
> Starting from the weekly canonical storage implementation, this model is DERIVED from PekerjaanProgressWeekly and should be considered a VIEW layer for backward compatibility.
>
> Data in this table can be regenerated from PekerjaanProgressWeekly when switching time scale modes.

---

### 3. PekerjaanProgressWeekly (Canonical Storage)

**Purpose**: Single source of truth for weekly progress data

**Fields**:
```python
class PekerjaanProgressWeekly(models.Model):
    pekerjaan = ForeignKey('Pekerjaan')
    project = ForeignKey('dashboard.Project')

    week_number = PositiveIntegerField()  # Week 1, 2, 3, etc.
    week_start_date = DateField()
    week_end_date = DateField()

    proportion = DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.01), MaxValueValidator(100.00)]
    )
    notes = TextField(blank=True)
```

**Key Points**:
- ✅ **CANONICAL STORAGE** - never deleted when switching modes
- ✅ Weekly is the base unit (most construction projects track weekly)
- ✅ Other views (daily/monthly) are calculated from this
- ✅ Independent of TahapPelaksanaan structure
- ⚠️ Requires both `pekerjaan` FK and `proportion >= 0.01`

**Why Weekly?**:
1. Most construction projects track progress per week
2. Avoids rounding errors when switching between time scale modes
3. Simple and maintainable
4. Can be aggregated up (monthly) or disaggregated down (daily)

**Important**:
> This data is NEVER deleted when switching time scale modes!
> Only TahapPelaksanaan records are regenerated, not this canonical data.

---

## 🔄 DATA FLOW

### Frontend Grid Display

```javascript
// 1. Load tahapan (time periods)
DataLoader.loadTahapan()
  → GET /api/project/110/tahapan/
  → Returns TahapPelaksanaan records

// 2. Generate time columns from tahapan
TimeColumnGenerator.generate()
  → Filters tahapan by generation_mode and is_auto_generated
  → Creates column objects for grid header

// 3. Load assignments (progress data)
DataLoader.loadAssignments()
  → GET /api/project/110/pekerjaan/{id}/assignments/
  → Returns PekerjaanTahapan records
  → Maps to time columns by tahapan_id

// 4. Render grid
GridRenderer.render()
  → Left panel: Pekerjaan tree
  → Right panel: Time columns (from step 2)
  → Cell values: Assignments (from step 3)
```

### TimeColumnGenerator Filtering Logic

```javascript
// For daily/weekly/monthly modes: Show ONLY auto-generated tahapan
if (timeScale !== 'custom') {
  shouldInclude = (
    tahap.is_auto_generated === true &&
    tahap.generation_mode === timeScale
  );
}

// For custom mode: Show ALL tahapan
if (timeScale === 'custom') {
  shouldInclude = true;
}

// FALLBACK: If no columns generated, show all tahapan
if (timeColumns.length === 0 && tahapanList.length > 0) {
  // Show all tahapan regardless of generation_mode
}
```

---

## ✅ CORRECT APPROACH: Sample Data Generation

### Step 1: Create TahapPelaksanaan (Time Periods)

```bash
# Generate 12 weekly tahapan for project 110
python manage.py generate_sample_weekly_tahapan 110 --weeks 12

# Custom start date
python manage.py generate_sample_weekly_tahapan 110 --weeks 16 --start-date 2025-01-01

# Clear existing auto-generated weekly tahapan first
python manage.py generate_sample_weekly_tahapan 110 --clear-auto
```

**This creates**:
- 12 `TahapPelaksanaan` records
- `is_auto_generated=True`
- `generation_mode='weekly'`
- Sequential dates (week_start → week_end)

### Step 2: (Optional) Create Sample Assignments

Once tahapan exist, you can:
1. Manually assign pekerjaan to tahapan via UI
2. Create management command to generate sample PekerjaanTahapan records
3. Let users assign naturally through the grid

---

## ❌ WRONG APPROACH: Direct PekerjaanProgressWeekly Creation

**What I initially tried**:
```python
# WRONG: Tried to create PekerjaanProgressWeekly without pekerjaan
PekerjaanProgressWeekly.objects.create(
    project=project,
    week_number=1,
    week_start_date=...,
    week_end_date=...,
    proportion=0.0  # ← Also wrong: must be >= 0.01
)
```

**Why it failed**:
1. ❌ `pekerjaan` field cannot be null (requires FK to Pekerjaan)
2. ❌ `proportion` must be >= 0.01 (cannot be 0.0)
3. ❌ PekerjaanProgressWeekly is per-pekerjaan, NOT project-wide
4. ❌ TimeColumnGenerator doesn't read from PekerjaanProgressWeekly

**Correct understanding**:
- `PekerjaanProgressWeekly` is for storing PROGRESS data (which pekerjaan, how much)
- `TahapPelaksanaan` is for defining TIME PERIODS (which weeks exist)
- TimeColumnGenerator reads from `TahapPelaksanaan`, NOT `PekerjaanProgressWeekly`

---

## 🎯 TESTING WORKFLOW

### 1. Generate Time Periods
```bash
python manage.py generate_sample_weekly_tahapan 110 --weeks 12
```

### 2. Refresh Page
- Open: `http://localhost:8000/detail_project/110/kelola-tahapan/`
- Check console logs for:
  ```
  [DataLoader] ✅ Loaded 12 tahapan, mode: weekly
  [TimeColumnGenerator] ✅ Generated 12 time columns
  ```

### 3. Verify Grid Display
- ✅ Grid header shows 12 week columns (Week 1 → Week 12)
- ✅ Date ranges displayed correctly
- ✅ Cells are editable (can enter percentages)

### 4. Create Sample Assignments
- Manually enter percentages in grid cells
- Or create management command to generate sample data
- Total per pekerjaan should sum to 100%

### 5. Test Charts
- After assignments exist:
  - Kurva-S should render S-curve
  - Gantt should render task timeline
- Charts auto-update on save

---

## 📋 FILES CREATED

### Management Command
**File**: `detail_project/management/commands/generate_sample_weekly_tahapan.py`

**Features**:
- ✅ Generates TahapPelaksanaan records (NOT PekerjaanProgressWeekly)
- ✅ Auto-detects project start date (tanggal_mulai or start_date)
- ✅ Creates sequential weekly periods (7 days each)
- ✅ Sets `is_auto_generated=True` and `generation_mode='weekly'`
- ✅ Skips existing tahapan (checks by name)
- ✅ Option to clear existing auto-generated weekly tahapan

**Usage**:
```bash
# Generate 12 weeks from project start
python manage.py generate_sample_weekly_tahapan <project_id>

# Custom weeks and start date
python manage.py generate_sample_weekly_tahapan <project_id> --weeks 16 --start-date 2025-01-01

# Clear existing first
python manage.py generate_sample_weekly_tahapan <project_id> --clear-auto
```

---

## 🔍 KEY LEARNINGS

### 1. Data Model Architecture
- ✅ **TahapPelaksanaan** = Time periods (what TimeColumnGenerator reads)
- ✅ **PekerjaanTahapan** = Assignments (view layer, can be regenerated)
- ✅ **PekerjaanProgressWeekly** = Canonical storage (never deleted)

### 2. TimeColumnGenerator Source
- ✅ Reads from `state.tahapanList` (loaded from TahapPelaksanaan API)
- ❌ Does NOT read from PekerjaanProgressWeekly
- ✅ Filters by `is_auto_generated` and `generation_mode`

### 3. Sample Data Strategy
- ✅ **Step 1**: Create TahapPelaksanaan (time periods)
- ✅ **Step 2**: Create PekerjaanTahapan (assignments)
- ❌ **NOT**: Create PekerjaanProgressWeekly (requires pekerjaan FK)

### 4. Field Name Variations
- Indonesian: `tanggal_mulai`, `nama`
- English: `start_date`, `name`
- TahapPelaksanaan: `tanggal_mulai`, `tanggal_selesai`
- PekerjaanProgressWeekly: `week_start_date`, `week_end_date`

### 5. Validation Rules
- `proportion` / `proporsi_volume`: Must be >= 0.01 and <= 100.00
- Cannot create PekerjaanProgressWeekly without pekerjaan FK
- Total proporsi per pekerjaan should sum to 100%

---

## 📊 TESTING RESULTS

### Project 110: Generated Tahapan

**Command Run**:
```bash
python manage.py generate_sample_weekly_tahapan 110 --weeks 12
```

**Result**: ✅ **SUCCESS**
- Created 12 tahapan (IDs: 2240-2251)
- Date range: 2026-01-09 to 2026-04-02
- All with `is_auto_generated=True` and `generation_mode='weekly'`

**Created Records**:
```
Week  1: 2026-01-09 to 2026-01-15 [ID: 2240]
Week  2: 2026-01-16 to 2026-01-22 [ID: 2241]
Week  3: 2026-01-23 to 2026-01-29 [ID: 2242]
Week  4: 2026-01-30 to 2026-02-05 [ID: 2243]
Week  5: 2026-02-06 to 2026-02-12 [ID: 2244]
Week  6: 2026-02-13 to 2026-02-19 [ID: 2245]
Week  7: 2026-02-20 to 2026-02-26 [ID: 2246]
Week  8: 2026-02-27 to 2026-03-05 [ID: 2247]
Week  9: 2026-03-06 to 2026-03-12 [ID: 2248]
Week 10: 2026-03-13 to 2026-03-19 [ID: 2249]
Week 11: 2026-03-20 to 2026-03-26 [ID: 2250]
Week 12: 2026-03-27 to 2026-04-02 [ID: 2251]
```

**Next Steps**:
1. Refresh jadwal-pekerjaan page
2. Verify time columns appear in grid header
3. Test assigning pekerjaan to periods
4. Verify charts render

---

**Last Updated**: 2025-11-23
**Phase**: 2D Testing & Sample Data Generation
**Status**: ✅ Data model architecture understood, sample tahapan generated successfully
