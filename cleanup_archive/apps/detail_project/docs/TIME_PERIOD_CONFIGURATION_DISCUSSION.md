# Time Period Configuration: Design Discussion

**Date**: 2025-11-23
**Status**: 🔄 **DISCUSSION DRAFT**
**Purpose**: Document design decisions for time period configuration and mode switching

---

## ✅ CURRENT STATUS

### What's Working
- ✅ Time columns appear in grid (12 weeks generated)
- ✅ TahapPelaksanaan records created successfully
- ✅ TimeColumnGenerator reads and displays columns
- ✅ Grid layout horizontal (left-right) ✅

### Issues to Discuss
1. **Week Boundaries**: Hari awal/akhir untuk sebuah week
2. **Project Boundaries**: Handling project start/end yang tidak tepat pada week boundary
3. **User Configuration**: Penentuan hari awal/akhir yang bisa dipilih user
4. **Mode Switching**: Interaksi saat switch week ↔ month
5. **Complexity Reduction**: Remove daily/custom modes untuk simplify sistem

---

## 📋 ISSUE #1: Week Boundaries (Hari Awal/Akhir)

### Current Implementation
**File**: [generate_sample_weekly_tahapan.py:94](d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\management\commands\generate_sample_weekly_tahapan.py#L94)

```python
for week_num in range(num_weeks):
    week_start = start_date + timedelta(weeks=week_num)
    week_end = week_start + timedelta(days=6)  # 7-day week (inclusive)
```

**Current Logic**:
- Week dimulai dari `start_date` (project start date)
- Week ends 6 days later (total 7 days inclusive)
- Example: Start Fri Jan 9 → End Thu Jan 15

**Problem**:
- Week tidak selalu dimulai dari hari yang sama (depends on project start date)
- Tidak ada standarisasi hari awal week (e.g., Senin atau Minggu)

### Options untuk Week Start Day

#### Option A: Fixed Week Start (e.g., Senin/Monday)
**Pros**:
- ✅ Consistent week boundaries across all projects
- ✅ Aligns with calendar weeks (ISO 8601: Monday = week start)
- ✅ Easy for user to understand (Week 1 = Senin-Minggu)
- ✅ Standard construction industry practice

**Cons**:
- ⚠️ Project start date might not align with Monday
- ⚠️ First/last weeks might be partial weeks

**Implementation**:
```python
def get_week_start(date, week_start_day=0):  # 0=Monday, 6=Sunday
    """Adjust date to nearest previous week_start_day"""
    days_since_start = (date.weekday() - week_start_day) % 7
    return date - timedelta(days=days_since_start)

# Example
project_start = datetime(2026, 1, 9).date()  # Friday
week_1_start = get_week_start(project_start, week_start_day=0)  # Monday Jan 5
week_1_end = week_1_start + timedelta(days=6)  # Sunday Jan 11
```

**Result**:
- Week 1: Mon Jan 5 - Sun Jan 11 (project starts Fri Jan 9, partial week)
- Week 2: Mon Jan 12 - Sun Jan 18
- Week 3: Mon Jan 19 - Sun Jan 25

---

#### Option B: Flexible Week Start (dari Project Start Date)
**Pros**:
- ✅ No partial weeks (always full 7 days)
- ✅ Simple calculation (just add 7 days)
- ✅ No need to adjust start date

**Cons**:
- ❌ Inconsistent week boundaries (depends on project start day)
- ❌ Week 1 might be Fri-Thu, Week 2 might be Fri-Thu
- ❌ Confusing for users (not aligned with calendar)

**Implementation**:
```python
# Current implementation
week_start = start_date + timedelta(weeks=week_num)
week_end = week_start + timedelta(days=6)
```

**Result** (Project starts Friday Jan 9):
- Week 1: Fri Jan 9 - Thu Jan 15
- Week 2: Fri Jan 16 - Thu Jan 22
- Week 3: Fri Jan 23 - Thu Jan 29

---

#### Option C: Configurable Week Start Day
**Pros**:
- ✅ User can choose week start day (Senin, Minggu, etc.)
- ✅ Flexibility per project
- ✅ Can align with company/team practices

**Cons**:
- ⚠️ More complex (need UI for configuration)
- ⚠️ Need to store configuration per project
- ⚠️ Still has partial week issue

**Implementation**:
```python
class ProjectTimeConfig(models.Model):
    project = models.OneToOneField('dashboard.Project')
    week_start_day = models.IntegerField(
        default=0,  # 0=Monday, 6=Sunday
        choices=[(i, day) for i, day in enumerate(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])]
    )
```

---

### 🎯 RECOMMENDATION: Option A (Fixed Monday Start)

**Rationale**:
1. **Industry Standard**: Construction projects typically track weekly progress Mon-Sun
2. **ISO 8601 Standard**: Monday is internationally recognized week start
3. **Consistency**: All projects have same week boundaries
4. **Partial Weeks Handling**: See Issue #2 below

**Proposed Implementation**:
```python
def generate_weekly_tahapan(project_start, project_end, week_start_day=0):
    """
    Generate weekly tahapan aligned to week_start_day.

    Args:
        project_start: Project start date
        project_end: Project end date
        week_start_day: 0=Monday, 6=Sunday (default: Monday)

    Returns:
        List of (week_start, week_end) tuples
    """
    # Adjust to nearest previous week_start_day
    week_start = get_week_start(project_start, week_start_day)

    weeks = []
    while week_start <= project_end:
        week_end = week_start + timedelta(days=6)

        # Only include weeks that overlap with project duration
        if week_end >= project_start:
            weeks.append((week_start, week_end))

        week_start += timedelta(days=7)

    return weeks
```

---

## 📋 ISSUE #2: Project Boundaries (Partial Weeks)

### Scenario

**Project Timeline**:
- Start: Friday, January 9, 2026
- End: Wednesday, April 2, 2026

**Week Boundaries (Monday start)**:
- Week 1: Mon Jan 5 - Sun Jan 11 (project starts Fri Jan 9, only 3 days)
- Week 2: Mon Jan 12 - Sun Jan 18 (full week)
- ...
- Week 13: Mon Mar 30 - Sun Apr 5 (project ends Wed Apr 2, only 4 days)

### Options for Partial Weeks

#### Option A: Include Partial Weeks (with visual indicators)
**Pros**:
- ✅ Complete coverage of project timeline
- ✅ No missing days
- ✅ Accurate for short-duration tasks

**Cons**:
- ⚠️ First/last weeks have fewer days
- ⚠️ Need visual indicators (e.g., grayed out days before/after project)

**Implementation**:
```python
# Mark partial weeks
tahapan = TahapPelaksanaan.objects.create(
    nama="Week 1",
    tanggal_mulai=week_start,  # Mon Jan 5
    tanggal_selesai=week_end,  # Sun Jan 11
    is_partial_week=True,  # NEW field
    project_overlap_start=project_start,  # Fri Jan 9
    project_overlap_end=min(week_end, project_end)  # Sun Jan 11
)
```

**UI Display**:
```
Week 1: Mon Jan 5 - Sun Jan 11 *
        (Project starts Fri Jan 9)

* Partial week
```

---

#### Option B: Exclude Partial Weeks
**Pros**:
- ✅ All weeks are full 7-day weeks
- ✅ Simpler calculation
- ✅ No special handling needed

**Cons**:
- ❌ Missing days at start/end of project
- ❌ Tasks starting in partial weeks have no place
- ❌ Inaccurate for short projects

**Not Recommended** for construction projects (need complete timeline coverage).

---

#### Option C: Trim to Project Boundaries
**Pros**:
- ✅ Exact project coverage (no days outside project)
- ✅ Clear start/end alignment

**Cons**:
- ⚠️ First/last weeks not standard 7-day duration
- ⚠️ Inconsistent week lengths

**Implementation**:
```python
# Trim weeks to project boundaries
actual_start = max(week_start, project_start)  # Fri Jan 9
actual_end = min(week_end, project_end)  # Wed Apr 2

tahapan = TahapPelaksanaan.objects.create(
    nama="Week 1",
    tanggal_mulai=actual_start,  # Fri Jan 9 (not Mon Jan 5)
    tanggal_selesai=actual_end,   # Sun Jan 11
)
```

**Result**:
- Week 1: **Fri Jan 9 - Sun Jan 11** (3 days)
- Week 2: Mon Jan 12 - Sun Jan 18 (7 days)
- Week 13: Mon Mar 30 - **Wed Apr 2** (4 days)

---

### 🎯 RECOMMENDATION: Option C (Trim to Project Boundaries)

**Rationale**:
1. **Accuracy**: Only includes days within project timeline
2. **Clarity**: No confusion about days outside project
3. **Simplicity**: No need for special "partial week" flags

**Visual Indicators**:
- Show actual day count in column header: "Week 1 (3 days)"
- Gray out or narrow column width for partial weeks
- Tooltip shows reason: "Partial week (project starts mid-week)"

---

## 📋 ISSUE #3: User Configuration (Hari Awal/Akhir Week)

### Options

#### Option A: Global System Default (Simplest)
**Implementation**:
- Hard-coded: Monday = week start
- No user configuration needed
- Consistent across all projects

**Settings**:
```python
# settings.py
JADWAL_PEKERJAAN_WEEK_START_DAY = 0  # 0=Monday
```

**Pros**: ✅ Simplest, no UI needed
**Cons**: ❌ No flexibility per project

---

#### Option B: Per-Project Configuration
**Implementation**:
- Add field to Project model or ProjectTimeConfig
- UI in project settings page

**Model**:
```python
class ProjectTimeConfig(models.Model):
    project = models.OneToOneField('dashboard.Project')
    week_start_day = models.IntegerField(
        default=0,
        choices=[
            (0, 'Senin (Monday)'),
            (1, 'Selasa (Tuesday)'),
            # ...
            (6, 'Minggu (Sunday)')
        ]
    )
```

**UI** (project settings page):
```html
<div class="form-group">
  <label>Hari Awal Minggu</label>
  <select name="week_start_day" class="form-control">
    <option value="0" selected>Senin (Monday)</option>
    <option value="1">Selasa (Tuesday)</option>
    <!-- ... -->
    <option value="6">Minggu (Sunday)</option>
  </select>
  <small class="form-text text-muted">
    Menentukan hari pertama dalam periode mingguan.
  </small>
</div>
```

**Pros**: ✅ Flexibility per project
**Cons**: ⚠️ More complex, needs UI

---

### 🎯 RECOMMENDATION: Option A (Global Default) → Option B (Later)

**Phase 1**: Start with global Monday default
**Phase 2**: Add per-project configuration if users request it

**Rationale**:
- Most construction projects use Monday as week start
- Avoid premature complexity
- Easy to add later if needed

---

## 📋 ISSUE #4: Mode Switching (Week ↔ Month)

### Current Architecture

**TahapPelaksanaan Model**:
```python
is_auto_generated = BooleanField(default=False)
generation_mode = CharField(
    choices=[('daily', 'Daily'), ('weekly', 'Weekly'),
             ('monthly', 'Monthly'), ('custom', 'Custom')]
)
```

**TimeColumnGenerator Filtering**:
```javascript
// Only show tahapan matching current mode
if (timeScale === 'weekly') {
  shouldInclude = (
    tahap.is_auto_generated === true &&
    tahap.generation_mode === 'weekly'
  );
}
```

### Scenario: User switches Weekly → Monthly

**Before Switch** (Weekly mode):
- 12 TahapPelaksanaan records (Week 1-12)
- is_auto_generated=True, generation_mode='weekly'
- Grid shows 12 columns

**After Switch** (Monthly mode):
- What should happen?

### Options

#### Option A: Keep All, Filter Display
**Behavior**:
- Keep weekly tahapan in database
- Generate new monthly tahapan
- Filter display based on `generation_mode`

**Pros**:
- ✅ No data loss
- ✅ Can switch back and forth
- ✅ Preserve user assignments

**Cons**:
- ⚠️ Database accumulates tahapan records
- ⚠️ Need to handle assignments to old tahapan
- ⚠️ Complex data migration when switching modes

**Implementation**:
```python
# On mode switch to monthly
def switch_to_monthly(project):
    # 1. Generate monthly tahapan (if not exist)
    generate_monthly_tahapan(project)

    # 2. Migrate assignments from weekly to monthly
    migrate_assignments_weekly_to_monthly(project)

    # 3. Keep weekly tahapan (just hide in UI)
    # Weekly tahapan still in DB, filtered out by TimeColumnGenerator
```

---

#### Option B: Delete Old, Generate New
**Behavior**:
- Delete auto-generated tahapan from old mode
- Generate new tahapan for new mode
- Migrate assignments to new structure

**Pros**:
- ✅ Clean database (no orphaned records)
- ✅ Simple logic

**Cons**:
- ❌ Data loss risk
- ❌ Cannot easily switch back
- ❌ Assignment migration complex

**Implementation**:
```python
def switch_to_monthly(project):
    # 1. Delete old auto-generated weekly tahapan
    TahapPelaksanaan.objects.filter(
        project=project,
        is_auto_generated=True,
        generation_mode='weekly'
    ).delete()  # ⚠️ This will cascade delete PekerjaanTahapan!

    # 2. Generate new monthly tahapan
    generate_monthly_tahapan(project)

    # 3. User must re-assign pekerjaan (assignments lost)
```

---

#### Option C: Use Canonical Storage (PekerjaanProgressWeekly)
**Behavior**:
- Assignments stored in PekerjaanProgressWeekly (canonical)
- PekerjaanTahapan derived/aggregated from canonical
- Switching modes = regenerate view layer only

**Pros**:
- ✅ No data loss (canonical storage preserved)
- ✅ Can switch modes freely
- ✅ Assignments recalculated automatically

**Cons**:
- ⚠️ Requires canonical storage implementation
- ⚠️ Complex aggregation logic (weekly → monthly)

**Implementation**:
```python
def switch_to_monthly(project):
    # 1. Canonical storage (PekerjaanProgressWeekly) is NEVER deleted

    # 2. Delete old tahapan and assignments (view layer only)
    TahapPelaksanaan.objects.filter(
        project=project,
        is_auto_generated=True,
        generation_mode='weekly'
    ).delete()

    # 3. Generate monthly tahapan
    monthly_tahapan = generate_monthly_tahapan(project)

    # 4. Regenerate PekerjaanTahapan by aggregating PekerjaanProgressWeekly
    for tahap in monthly_tahapan:
        # Find all weekly records that fall within this month
        weekly_records = PekerjaanProgressWeekly.objects.filter(
            project=project,
            week_start_date__gte=tahap.tanggal_mulai,
            week_end_date__lte=tahap.tanggal_selesai
        )

        # Aggregate by pekerjaan
        for pekerjaan in weekly_records.values('pekerjaan').distinct():
            total_proportion = weekly_records.filter(
                pekerjaan=pekerjaan['pekerjaan']
            ).aggregate(Sum('proportion'))['proportion__sum']

            PekerjaanTahapan.objects.create(
                pekerjaan_id=pekerjaan['pekerjaan'],
                tahapan=tahap,
                proporsi_volume=total_proportion
            )
```

---

### 🎯 RECOMMENDATION: Option C (Canonical Storage)

**Rationale**:
1. **Aligns with existing architecture** (PekerjaanProgressWeekly is already designed as canonical)
2. **No data loss** when switching modes
3. **Flexible** - can add more modes later (quarterly, etc.)

**Architecture**:
```
User Input (Grid)
    ↓
PekerjaanProgressWeekly (Canonical - NEVER deleted)
    ↓ aggregated/derived
PekerjaanTahapan (View Layer - regenerated on mode switch)
    ↓ filtered
TahapPelaksanaan (Time Periods - regenerated on mode switch)
    ↓ displayed
Grid Columns
```

**Mode Switch Flow**:
1. User clicks "Switch to Monthly"
2. Confirm dialog: "This will regenerate time periods. Continue?"
3. Backend:
   - Delete auto-generated tahapan (weekly)
   - Generate new tahapan (monthly)
   - Regenerate PekerjaanTahapan from PekerjaanProgressWeekly
4. Frontend:
   - Reload data
   - Refresh grid with new columns
   - Charts update automatically

---

## 📋 ISSUE #5: Complexity Reduction (Remove Daily/Custom)

### Current Modes
- ✅ **Weekly**: Auto-generated weekly periods
- ✅ **Monthly**: Auto-generated monthly periods
- ⚠️ **Daily**: Auto-generated daily periods
- ⚠️ **Custom**: Manually created periods

### Proposed: Keep Only Weekly + Monthly

#### Reasons to Remove Daily
1. **Performance**: Too many columns (30+ days × 3 months = 90+ columns)
2. **Usability**: Grid becomes unusable with 90+ columns
3. **Over-precision**: Construction rarely tracks daily (weekly is sufficient)
4. **Database Load**: 90+ TahapPelaksanaan records vs 12 weekly
5. **Frontend Load**: Rendering 90+ columns + cells very slow

#### Reasons to Remove Custom
1. **Complexity**: Mixing auto-generated and manual tahapan is confusing
2. **Mode Switching**: Custom tahapan cannot be regenerated
3. **Canonical Storage**: Custom periods don't fit weekly canonical model
4. **Edge Cases**: Too many special cases to handle

### 🎯 RECOMMENDATION: Keep Weekly + Monthly Only

**Simplified Modes**:
```python
GENERATION_MODE_CHOICES = [
    ('weekly', 'Mingguan (Weekly)'),
    ('monthly', 'Bulanan (Monthly)'),
]
```

**Benefits**:
- ✅ **Simple**: Only 2 modes to maintain
- ✅ **Performance**: Reasonable column counts (12 weeks or 3 months)
- ✅ **Canonical Storage**: Both fit weekly basis (monthly = 4-5 weeks aggregated)
- ✅ **User-Friendly**: Clear choice between granular (weekly) or summary (monthly)

**Migration**:
```python
# Remove daily and custom modes
TahapPelaksanaan.objects.filter(
    generation_mode__in=['daily', 'custom']
).update(generation_mode='weekly')  # or delete if unwanted
```

---

## 🎯 FINAL RECOMMENDATIONS SUMMARY

### 1. Week Boundaries
- ✅ **Use Fixed Monday Start** (ISO 8601 standard)
- ✅ **Trim to Project Boundaries** (no days outside project)
- ✅ **Show Partial Week Indicators** in UI (e.g., "Week 1 (3 days)")

### 2. User Configuration
- ✅ **Phase 1**: Global Monday default (simplest)
- ⏳ **Phase 2**: Per-project config (if users request)

### 3. Mode Switching
- ✅ **Use Canonical Storage** (PekerjaanProgressWeekly)
- ✅ **Regenerate View Layer** (TahapPelaksanaan + PekerjaanTahapan)
- ✅ **No Data Loss** when switching modes

### 4. Complexity Reduction
- ✅ **Remove Daily Mode** (performance + usability)
- ✅ **Remove Custom Mode** (complexity + canonical storage issues)
- ✅ **Keep Weekly + Monthly** (sufficient for construction)

---

## 📋 IMPLEMENTATION PLAN

### Phase 1: Week Boundaries (High Priority)
- [ ] Update `generate_sample_weekly_tahapan.py` to use Monday start
- [ ] Add `get_week_start()` helper function
- [ ] Trim weeks to project boundaries
- [ ] Add week day count to UI (e.g., "Week 1 (3 days)")

### Phase 2: Mode Switching (High Priority)
- [ ] Implement monthly tahapan generation
- [ ] Create canonical storage save handler (save to PekerjaanProgressWeekly)
- [ ] Create aggregation logic (weekly → monthly)
- [ ] Add mode switch API endpoint
- [ ] Add UI toggle for Weekly/Monthly

### Phase 3: Complexity Reduction (Medium Priority)
- [ ] Remove daily/custom modes from code
- [ ] Migrate existing daily/custom tahapan
- [ ] Update UI to show only Weekly/Monthly toggle
- [ ] Update documentation

### Phase 4: User Configuration (Low Priority)
- [ ] Add ProjectTimeConfig model (optional)
- [ ] Add project settings UI for week_start_day
- [ ] Update tahapan generation to use config

---

## 🔧 TECHNICAL DETAILS

### Updated Management Command
```python
def generate_weekly_tahapan(project, num_weeks=None, week_start_day=0):
    """
    Generate weekly tahapan aligned to week_start_day (default: Monday).
    Trim to project boundaries.
    """
    project_start = project.tanggal_mulai
    project_end = project.tanggal_selesai or (project_start + timedelta(weeks=12))

    # Align to week_start_day
    week_start = get_week_start(project_start, week_start_day)

    tahapan_list = []
    week_num = 1

    while week_start <= project_end:
        week_end = week_start + timedelta(days=6)

        # Only include weeks overlapping with project
        if week_end >= project_start:
            # Trim to project boundaries
            actual_start = max(week_start, project_start)
            actual_end = min(week_end, project_end)

            tahapan = TahapPelaksanaan.objects.create(
                project=project,
                nama=f"Week {week_num}",
                urutan=week_num - 1,
                tanggal_mulai=actual_start,
                tanggal_selesai=actual_end,
                is_auto_generated=True,
                generation_mode='weekly'
            )
            tahapan_list.append(tahapan)
            week_num += 1

        week_start += timedelta(days=7)

    return tahapan_list
```

---

## 📊 PERFORMANCE IMPACT

### Before (4 modes: daily/weekly/monthly/custom)
- Daily: 90+ tahapan (3 months)
- Weekly: 12 tahapan (3 months)
- Monthly: 3 tahapan (3 months)
- Custom: Unknown count

**Issues**:
- Grid rendering slow with 90+ columns
- Database queries for 90+ tahapan
- Frontend memory issues

### After (2 modes: weekly/monthly)
- Weekly: 12 tahapan (3 months) ✅
- Monthly: 3 tahapan (3 months) ✅

**Benefits**:
- ✅ Max 12 columns (reasonable)
- ✅ Fast grid rendering
- ✅ Simple canonical storage (weekly basis)

---

## 🎯 SUCCESS METRICS

### Performance
- [ ] Grid loads in < 2 seconds
- [ ] Mode switch completes in < 3 seconds
- [ ] No frontend memory issues

### Usability
- [ ] Clear week boundaries (Monday-Sunday)
- [ ] Partial weeks clearly indicated
- [ ] Mode switch preserves assignments

### Maintainability
- [ ] Only 2 modes to test (weekly/monthly)
- [ ] Simple canonical storage model
- [ ] Clear separation: canonical vs view layer

---

**Last Updated**: 2025-11-23
**Status**: Discussion Draft - Awaiting User Feedback
**Next**: Review recommendations and approve implementation plan
