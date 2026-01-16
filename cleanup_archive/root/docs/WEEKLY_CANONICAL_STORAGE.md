# Weekly Canonical Storage - Implementation Guide

**Version:** 1.0
**Date:** 27 Oktober 2025
**Status:** ✅ Implemented

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Solution Architecture](#solution-architecture)
4. [Database Schema](#database-schema)
5. [API Endpoints](#api-endpoints)
6. [Migration Guide](#migration-guide)
7. [Frontend Integration](#frontend-integration)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

**Weekly Canonical Storage** adalah solusi untuk bug konsistensi data progress yang terjadi saat switching antara time scale modes (daily/weekly/monthly).

### Key Features

✅ **Single Source of Truth** - Progress disimpan dalam unit weekly
✅ **Lossless Mode Switching** - Tidak ada data loss saat ganti mode
✅ **No Rounding Errors** - Tidak ada rounding error akumulatif
✅ **Backward Compatible** - Existing code tetap berfungsi
✅ **Maintainable** - Arsitektur simpel dan mudah di-maintain

### Why Weekly?

- Kebanyakan proyek konstruksi track progress per minggu
- Balance antara granularitas (daily terlalu detail) dan aggregasi (monthly terlalu kasar)
- Unit yang natural untuk input manual oleh user

---

## 🐛 Problem Statement

### Bug Sebelumnya

**Gejala:**
```
User input: 100% di Week 1 (7 hari)
Saved to DB: PekerjaanTahapan { tahapan_id: Week1, proporsi: 100.00 }

User switch ke Daily mode:
→ Backend DELETE tahapan lama, CONVERT assignments
→ Algoritma: 100% / 7 days = 14.285714% per day
→ Rounded: 14.29% × 7 = 100.03% ❌ ROUNDING ERROR!

User switch kembali ke Weekly:
→ Backend CONVERT lagi: 14.29% × 7 = ???
→ Hasil bisa 99.97%, 100.03%, atau nilai lain
```

**Akar Masalah:**
1. ❌ Tidak ada "single source of truth"
2. ❌ Setiap mode switch = DELETE + RECREATE + REDISTRIBUTE
3. ❌ Rounding error akumulatif
4. ❌ Data tied to tahapan (yang bisa dihapus)

---

## 🏗️ Solution Architecture

### Konsep: Canonical Storage + View Layer

```
┌─────────────────────────────────────────────────────┐
│         CANONICAL STORAGE (Never Deleted)           │
│                                                     │
│  PekerjaanProgressWeekly                           │
│  ┌──────────┬──────────┬────────────┐             │
│  │ Week 1   │ Week 2   │ Week 3     │             │
│  │ 25.50%   │ 50.00%   │ 24.50%     │             │
│  └──────────┴──────────┴────────────┘             │
│           ↑ SINGLE SOURCE OF TRUTH                 │
└──────────────────┬──────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
    ▼              ▼              ▼
┌─────────┐  ┌──────────┐  ┌───────────┐
│ DAILY   │  │ WEEKLY   │  │ MONTHLY   │
│  VIEW   │  │  VIEW    │  │   VIEW    │
├─────────┤  ├──────────┤  ├───────────┤
│ Day 1   │  │ Week 1   │  │ Oct 2025  │
│ 3.64%   │  │ 25.50%   │  │ 100.00%   │
│ Day 2   │  │ Week 2   │  │           │
│ 3.64%   │  │ 50.00%   │  │           │
│ ...     │  │ Week 3   │  │           │
│         │  │ 24.50%   │  │           │
└─────────┘  └──────────┘  └───────────┘
  ↑              ↑              ↑
  Calculated     Direct         Aggregated
```

### Data Flow

**SAVE (Weekly Mode):**
```python
1. User input 25.50% di Week 1
2. Save ke PekerjaanProgressWeekly (canonical)
3. Sync ke PekerjaanTahapan (view layer)
```

**READ (Daily Mode):**
```python
1. Get Week 1 dari PekerjaanProgressWeekly (25.50%)
2. Calculate: 25.50% / 7 days = 3.64% per day
3. Return daily view (calculated on-the-fly)
```

**MODE SWITCH:**
```python
1. DELETE auto-generated TahapPelaksanaan ONLY
2. CREATE new tahapan structure for new mode
3. SYNC from PekerjaanProgressWeekly (canonical) → PekerjaanTahapan
4. ✅ NO DATA LOSS - canonical storage never touched!
```

---

## 💾 Database Schema

### Model: PekerjaanProgressWeekly (NEW)

**Purpose:** Canonical storage for progress data

```python
class PekerjaanProgressWeekly(models.Model):
    """
    CANONICAL STORAGE: Weekly progress (single source of truth)

    This data is NEVER deleted when switching time scale modes!
    """
    pekerjaan = ForeignKey(Pekerjaan)
    project = ForeignKey(Project)  # Denormalized for querying

    # Week identification
    week_number = IntegerField()  # 1-indexed from project start
    week_start_date = DateField()
    week_end_date = DateField()

    # Progress data
    proportion = DecimalField(max_digits=5, decimal_places=2)  # 0.01-100.00
    notes = TextField(blank=True)

    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('pekerjaan', 'week_number')]
```

### Model: PekerjaanTahapan (EXISTING - Now View Layer)

**Purpose:** View layer for backward compatibility

```python
class PekerjaanTahapan(models.Model):
    """
    Junction table - NOW CONSIDERED A VIEW LAYER

    Data here is DERIVED from PekerjaanProgressWeekly and can be
    regenerated when switching time scale modes.
    """
    pekerjaan = ForeignKey(Pekerjaan)
    tahapan = ForeignKey(TahapPelaksanaan)
    proporsi_volume = DecimalField(...)
    # ... existing fields ...
```

### Migration Path

```bash
# Step 1: Create new table
python manage.py migrate

# Step 2: Migrate existing data
python manage.py migrate_to_weekly_canonical --project-id 123

# Or migrate all projects
python manage.py migrate_to_weekly_canonical
```

---

## 🔌 API Endpoints

### API V2 (NEW - Canonical Storage)

#### 1. Assign Weekly Progress (Canonical)

**Endpoint:** `POST /api/v2/project/<project_id>/assign-weekly/`

**Request:**
```json
{
  "assignments": [
    {
      "pekerjaan_id": 322,
      "week_number": 1,
      "proportion": 25.50,
      "notes": "Optional notes"
    },
    {
      "pekerjaan_id": 322,
      "week_number": 2,
      "proportion": 50.00
    }
  ]
}
```

**Response:**
```json
{
  "ok": true,
  "message": "2 weekly progress records saved",
  "created_count": 2,
  "updated_count": 0,
  "assignments": [...]
}
```

#### 2. Get Weekly Progress (Canonical)

**Endpoint:** `GET /api/v2/project/<project_id>/pekerjaan/<pekerjaan_id>/weekly-progress/`

**Response:**
```json
{
  "ok": true,
  "pekerjaan_id": 322,
  "weekly_progress": [
    {
      "week_number": 1,
      "week_start_date": "2025-10-26",
      "week_end_date": "2025-11-01",
      "proportion": 25.50,
      "notes": "..."
    }
  ],
  "total_proportion": 100.00,
  "is_complete": true
}
```

#### 3. Get Assignments in View Mode

**Endpoint:** `GET /api/v2/project/<project_id>/pekerjaan/<pekerjaan_id>/assignments/?mode=weekly`

**Query Params:**
- `mode`: `daily` | `weekly` | `monthly` | `custom`

**Response:**
```json
{
  "ok": true,
  "pekerjaan_id": 322,
  "mode": "daily",
  "assignments": [
    {
      "tahapan_id": 855,
      "tahapan_nama": "Day 1",
      "proporsi": 3.64,
      "urutan": 1
    }
  ],
  "total_proporsi": 100.00
}
```

#### 4. Regenerate Tahapan V2 (Lossless)

**Endpoint:** `POST /api/v2/project/<project_id>/regenerate-tahapan/`

**Request:**
```json
{
  "mode": "daily",
  "week_end_day": 0
}
```

**Response:**
```json
{
  "ok": true,
  "mode": "daily",
  "message": "Generated 70 tahapan and synced 150 assignments",
  "tahapan_deleted": 11,
  "tahapan_created": 70,
  "assignments_synced": 150
}
```

**Key Difference from V1:**
- ✅ Does NOT convert assignments (preserves canonical data)
- ✅ Only regenerates tahapan structure
- ✅ Syncs from PekerjaanProgressWeekly (lossless!)

---

## 🚀 Migration Guide

### For New Projects

Just use API V2 endpoints directly. No migration needed!

### For Existing Projects

#### Step 1: Run Database Migration

```bash
python manage.py migrate
```

This creates the `PekerjaanProgressWeekly` table.

#### Step 2: Migrate Data

**Option A: Migrate Single Project**

```bash
python manage.py migrate_to_weekly_canonical --project-id 123
```

**Option B: Migrate All Projects**

```bash
python manage.py migrate_to_weekly_canonical
```

**Option C: Dry Run First**

```bash
python manage.py migrate_to_weekly_canonical --dry-run
```

#### Step 3: Verify Migration

```bash
# Check Django admin
http://localhost:8000/admin/detail_project/pekerjaanprogressweekly/

# Or via Django shell
python manage.py shell

>>> from detail_project.models import PekerjaanProgressWeekly
>>> PekerjaanProgressWeekly.objects.filter(project_id=123).count()
45  # Should show migrated records
```

#### Step 4: Update Frontend (See next section)

---

## 🎨 Frontend Integration

### Current Frontend (OLD - V1 API)

**File:** `kelola_tahapan_grid.js`

**Current save logic:**
```javascript
// OLD: Saves to tahapan directly (lossy on mode switch)
async function savePekerjaanAssignments(pekerjaanId, assignments) {
    for (const [tahapanId, proporsi] of Object.entries(assignments)) {
        await apiCall(`/api/tahapan/${tahapanId}/assign/`, {
            method: 'POST',
            body: JSON.stringify({
                assignments: [{pekerjaan_id: pekerjaanId, proporsi}]
            })
        });
    }
}
```

### NEW Frontend (V2 API) - RECOMMENDED

**Update save logic to use weekly canonical:**

```javascript
// NEW: Saves to weekly canonical storage (lossless)
async function savePekerjaanAssignmentsV2(pekerjaanId, assignments) {
    // Convert tahapan assignments to weekly format
    const weeklyAssignments = [];

    for (const [tahapanId, proporsi] of Object.entries(assignments)) {
        const tahapan = state.tahapanList.find(t => t.id === tahapanId);

        // Calculate week number from tahapan date
        const weekNum = calculateWeekNumber(
            tahapan.tanggal_mulai,
            state.project.tanggal_mulai
        );

        weeklyAssignments.push({
            pekerjaan_id: pekerjaanId,
            week_number: weekNum,
            proportion: proporsi
        });
    }

    // Save to canonical storage (V2 API)
    await apiCall(`/api/v2/project/${projectId}/assign-weekly/`, {
        method: 'POST',
        body: JSON.stringify({ assignments: weeklyAssignments })
    });
}
```

**Update mode switching:**

```javascript
// OLD regenerate (lossy - converts assignments)
await apiCall(`/api/project/${projectId}/regenerate-tahapan/`, {
    method: 'POST',
    body: JSON.stringify({ mode: newMode, convert_assignments: true })
});

// NEW regenerate V2 (lossless - syncs from canonical)
await apiCall(`/api/v2/project/${projectId}/regenerate-tahapan/`, {
    method: 'POST',
    body: JSON.stringify({ mode: newMode, week_end_day: 0 })
});
```

**Update load logic:**

```javascript
// NEW: Load from canonical with mode conversion
async function loadAssignmentsV2(pekerjaanId, mode) {
    const response = await apiCall(
        `/api/v2/project/${projectId}/pekerjaan/${pekerjaanId}/assignments/?mode=${mode}`
    );

    return response.assignments;
}
```

---

## 🧪 Testing

### Manual Testing Checklist

- [ ] **Create new project with weekly data**
  - Input 100% progress across multiple weeks
  - Verify total = 100%

- [ ] **Switch to Daily mode**
  - Verify daily values calculated correctly
  - Check total still = 100%

- [ ] **Switch to Monthly mode**
  - Verify monthly aggregation
  - Check total still = 100%

- [ ] **Switch back to Weekly**
  - ✅ **CRITICAL:** Verify exact same values as before (no loss!)
  - Check proportion precision (should be exact, not rounded)

- [ ] **Edit progress in Weekly mode**
  - Update Week 2 from 50% to 60%
  - Switch to Daily → verify new daily values
  - Switch back to Weekly → verify Week 2 = 60% (not lost!)

### Automated Tests

```python
# tests/test_weekly_canonical.py

def test_lossless_mode_switching(project, pekerjaan):
    """Test that mode switching preserves exact data"""

    # Save weekly progress
    PekerjaanProgressWeekly.objects.create(
        pekerjaan=pekerjaan,
        project=project,
        week_number=1,
        week_start_date=date(2025, 1, 1),
        week_end_date=date(2025, 1, 7),
        proportion=Decimal('33.33')
    )

    # Switch to daily mode
    regenerate_tahapan_v2(project.id, mode='daily')

    # Switch back to weekly
    regenerate_tahapan_v2(project.id, mode='weekly')

    # Verify data preserved
    weekly = PekerjaanProgressWeekly.objects.get(
        pekerjaan=pekerjaan,
        week_number=1
    )

    assert weekly.proportion == Decimal('33.33')  # ✅ EXACT!
```

---

## 🔧 Troubleshooting

### Issue: Migration fails with "Cannot determine project"

**Cause:** PekerjaanProgressWeekly.save() tries to auto-populate project field from pekerjaan.volume.project

**Solution:**
```python
# Ensure all Pekerjaan have VolumePekerjaan
python manage.py shell
>>> from detail_project.models import Pekerjaan, VolumePekerjaan
>>> orphaned = Pekerjaan.objects.filter(volume__isnull=True)
>>> print(f"Found {orphaned.count()} orphaned pekerjaan")
```

### Issue: Frontend shows inconsistent data after mode switch

**Cause:** Frontend still using old API (V1) which is lossy

**Solution:** Update frontend to use V2 API endpoints (see Frontend Integration section)

### Issue: "Week number calculation incorrect"

**Cause:** Project tanggal_mulai not set

**Solution:**
```python
# Set project start date
project = Project.objects.get(id=123)
project.tanggal_mulai = date(2025, 1, 1)
project.tanggal_selesai = date(2025, 12, 31)
project.save()
```

---

## 📊 Performance Considerations

### Database Queries

**Before (V1):**
```sql
-- Load assignments (N+1 queries)
SELECT * FROM detail_project_pekerjaantahapan WHERE pekerjaan_id = 322;  -- For each pekerjaan
```

**After (V2):**
```sql
-- Load canonical weekly data (more efficient)
SELECT * FROM detail_project_pekerjaanprogressweekly WHERE project_id = 123;  -- Single query for all pekerjaan
```

### Indexes

The migration automatically creates these indexes:
- `(pekerjaan, week_number)` - For fast lookups
- `(project, week_number)` - For project-wide queries
- `(week_start_date, week_end_date)` - For date range queries

---

## 📚 References

- [Original API Documentation](./JADWAL_PEKERJAAN_API.md)
- [User Guide](./JADWAL_PEKERJAAN_USER_GUIDE.md)
- [GitHub Issue: Progress Mode Bug](https://github.com/.../issues/...)

---

## ✅ Checklist: Implementation Complete

- [x] Create PekerjaanProgressWeekly model
- [x] Database migration
- [x] Helper functions (progress_utils.py)
- [x] API V2 endpoints (views_api_tahapan_v2.py)
- [x] URL routing
- [x] Django admin integration
- [x] Management command for data migration
- [x] Documentation
- [ ] Frontend integration (TO DO)
- [ ] Automated tests (TO DO)
- [ ] Production deployment (TO DO)

---

**Document Version:** 1.0
**Last Updated:** 27 Oktober 2025
**Maintained By:** Development Team
