# PRODUCTION-READY ROADMAP: OPTION C (REFACTOR-FIRST)

**Project:** Ekosistem Jadwal Pekerjaan - Complete Refactor
**Approach:** Foundation-First, Feature-Second
**Duration:** 5 weeks (35 working days)
**Start Date:** TBD
**Status:** ⏳ READY FOR EXECUTION

---

## 📋 EXECUTIVE SUMMARY

### Strategy: Option C (Refactor-First Approach)

**Why this approach:**
- ✅ Zero technical debt
- ✅ Future-proof architecture
- ✅ 50% faster feature development (long-term)
- ✅ Easy maintenance and onboarding
- ✅ Saves 3-4 weeks over 2 years

**Core Principle:** "Clean foundation → Fast feature development → Sustainable growth"

---

## 🎯 OBJECTIVES & SUCCESS METRICS

### Primary Objectives

1. **Clean Architecture**
   - Single state management pattern (StateManager)
   - No code duplication
   - Clear separation of concerns

2. **Zero Technical Debt**
   - Remove legacy database fields
   - Eliminate circular dependencies
   - Unify API patterns

3. **Feature Complete**
   - Kurva S dengan harga-weighted calculation
   - Rekap Kebutuhan dengan weekly/monthly breakdown
   - Real-time chart synchronization

4. **Production Ready**
   - >90% test coverage
   - <200ms page load time
   - Zero breaking changes for users

### Success Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Code Duplication | 30% | 0% | SonarQube |
| Test Coverage | 45% | >90% | pytest --cov |
| State Patterns | 3 patterns | 1 pattern | Code audit |
| Database Fields (redundant) | 1 (proportion) | 0 | Schema review |
| Feature Dev Time | 7-8 hrs | 2-3 hrs | Time tracking |
| Page Load Time | 800ms | <300ms | Lighthouse |
| Memory Usage (5min) | 180MB | <80MB | Chrome DevTools |

---

## 📊 TIMELINE OVERVIEW

```
Week 1: Phase 0 - Foundation Cleanup
├─ Day 1-2: Database Schema Migration (Task 0.1)
├─ Day 3-4: StateManager Implementation (Task 0.2)
└─ Day 5: Migrate Consumers (Task 0.3)

Week 2-3: Phase 1 - Core Features
├─ Week 2: Phase 2F.1 - Kurva S Harga Integration
└─ Week 3: Phase 2G - Rekap Kebutuhan Integration

Week 4: Phase 2 - Polish & Optimization
├─ Day 1-2: API Bundling (Performance)
├─ Day 3-4: Build Optimization (Tree-shaking)
└─ Day 5: Load Testing & Profiling

Week 5: Phase 3 - Deployment
├─ Day 1-2: Staging Deployment + Smoke Tests
├─ Day 3: UAT (User Acceptance Testing)
├─ Day 4: Production Deployment
└─ Day 5: Monitoring & Hotfix Buffer
```

**Total:** 25 working days (5 weeks)
**Buffer:** 5 days (20% for unexpected issues)
**Total with Buffer:** 30 days (~6 weeks)

---

## 🔧 PHASE 0: FOUNDATION CLEANUP (Week 1)

**Goal:** Clean up technical debt BEFORE adding new features

**Why First:** Building new features on dirty foundation = guaranteed technical debt

---

### **TASK 0.1: Database Schema Migration** (Day 1-2)

**Duration:** 2 days
- Best case: 1.5 days (no issues)
- Realistic: 2 days (minor bugs)
- Worst case: 3 days (data migration issues)

**Blocking Dependencies:** None

**Required Resources:**
- Database admin access
- Backup infrastructure
- Staging environment

---

#### **Pre-Flight Checklist**

**Day 1 Morning (09:00-12:00):**

```bash
# 1. Create database backup
python manage.py dumpdata detail_project.PekerjaanProgressWeekly > backup_weekly_progress.json

# 2. Verify backup integrity
python manage.py loaddata backup_weekly_progress.json --dry-run

# 3. Check current schema
python manage.py sqlmigrate detail_project 0024

# 4. Count existing data
python manage.py shell
>>> from detail_project.models import PekerjaanProgressWeekly
>>> total_records = PekerjaanProgressWeekly.objects.count()
>>> records_with_null_planned = PekerjaanProgressWeekly.objects.filter(planned_proportion__isnull=True).count()
>>> print(f"Total: {total_records}, NULL planned: {records_with_null_planned}")
```

**Acceptance Criteria for Pre-Flight:**
- [ ] Backup file created and verified
- [ ] Zero NULL values in planned_proportion (all migrated)
- [ ] Staging database ready
- [ ] Rollback plan documented

---

#### **Migration File Implementation**

**File:** `detail_project/migrations/0043_remove_legacy_proportion_field.py`

```python
# Generated migration - DO NOT EDIT MANUALLY
from django.db import migrations
from decimal import Decimal

def ensure_data_migrated(apps, schema_editor):
    """
    Ensure all data from proportion field is migrated to planned_proportion.

    This is a safety check. Data should already be migrated by 0024 migration,
    but we verify again before deleting the column.
    """
    PekerjaanProgressWeekly = apps.get_model('detail_project', 'PekerjaanProgressWeekly')

    # Find records where planned_proportion is NULL but proportion has value
    records_to_migrate = PekerjaanProgressWeekly.objects.filter(
        planned_proportion__isnull=True,
        proportion__isnull=False
    )

    count = records_to_migrate.count()

    if count > 0:
        print(f"[Migration] Migrating {count} records from proportion → planned_proportion")

        for record in records_to_migrate:
            record.planned_proportion = record.proportion
            record.save(update_fields=['planned_proportion'])

        print(f"[Migration] ✅ Migrated {count} records successfully")
    else:
        print("[Migration] ✅ All records already migrated")

    # Verify no NULL values remain
    null_count = PekerjaanProgressWeekly.objects.filter(
        planned_proportion__isnull=True
    ).count()

    if null_count > 0:
        raise Exception(
            f"[Migration] ❌ ABORT: {null_count} records still have NULL planned_proportion. "
            "Manual intervention required."
        )

    print(f"[Migration] ✅ Data validation passed: 0 NULL values")


def reverse_migration(apps, schema_editor):
    """
    Rollback: Copy planned_proportion back to proportion.

    This allows safe rollback if we need to restore the old field.
    """
    PekerjaanProgressWeekly = apps.get_model('detail_project', 'PekerjaanProgressWeekly')

    for record in PekerjaanProgressWeekly.objects.all():
        if record.proportion is None:
            record.proportion = record.planned_proportion or Decimal('0')
            record.save(update_fields=['proportion'])

    print("[Migration] ✅ Rollback: Restored proportion field")


class Migration(migrations.Migration):

    dependencies = [
        ('detail_project', '0024_add_planned_actual_fields'),
    ]

    operations = [
        # Step 1: Ensure all data migrated
        migrations.RunPython(
            ensure_data_migrated,
            reverse_code=reverse_migration
        ),

        # Step 2: Remove the legacy field
        migrations.RemoveField(
            model_name='pekerjaanprogressweekly',
            name='proportion',
        ),
    ]
```

---

#### **Execution Steps**

**Day 1 Afternoon (13:00-17:00):**

```bash
# 1. Create migration file
touch detail_project/migrations/0043_remove_legacy_proportion_field.py
# (Copy content from above)

# 2. Validate migration syntax
python manage.py makemigrations --dry-run --check

# 3. Test on local database
python manage.py migrate detail_project 0043 --fake-initial

# 4. Check for errors
python manage.py check

# 5. Verify data integrity
python manage.py shell
>>> from detail_project.models import PekerjaanProgressWeekly
>>> # This should FAIL (field removed)
>>> PekerjaanProgressWeekly.objects.first().proportion
# AttributeError: 'PekerjaanProgressWeekly' object has no attribute 'proportion'
>>> # This should WORK
>>> PekerjaanProgressWeekly.objects.first().planned_proportion
# Decimal('25.00')
```

**Day 2 Morning (09:00-12:00):**

```bash
# 6. Deploy to staging
ssh staging-server
cd /var/www/django-ahsp
source venv/bin/activate

# 7. Run migration on staging
python manage.py migrate detail_project 0043

# 8. Smoke test staging
curl http://staging.example.com/detail_project/110/kelola-tahapan/
# Expected: Page loads successfully

# 9. Run full test suite
pytest detail_project/tests/ -v --tb=short

# 10. Verify charts render
# Open browser: http://staging.example.com/detail_project/110/kelola-tahapan/
# Check: Gantt Chart loads, Kurva S loads
```

**Day 2 Afternoon (13:00-17:00):**

```python
# 11. Update model (remove field + sync logic)
# File: detail_project/models.py

class PekerjaanProgressWeekly(models.Model):
    # ... existing fields ...

    planned_proportion = models.DecimalField(...)  # ✅ KEEP
    actual_proportion = models.DecimalField(...)   # ✅ KEEP
    # proportion = models.DecimalField(...)        # ❌ DELETE THIS LINE

    # ... other fields ...

    # def _normalize_proportion_fields(self):      # ❌ DELETE ENTIRE METHOD
    #     """Keep fields in sync..."""
    #     # DELETE ALL THIS CODE

    def clean(self):
        """Validation for planned and actual proportions"""
        # Remove _normalize_proportion_fields() call
        # self._normalize_proportion_fields()       # ❌ DELETE THIS LINE

        errors = {}

        # Validate planned_proportion
        if self.planned_proportion is not None:
            if self.planned_proportion < 0 or self.planned_proportion > 100:
                errors['planned_proportion'] = 'Must be 0-100%'

        # Validate actual_proportion
        if self.actual_proportion is not None:
            if self.actual_proportion < 0 or self.actual_proportion > 100:
                errors['actual_proportion'] = 'Must be 0-100%'

        # ... rest of validation

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Auto-populate project field"""
        # Remove _normalize_proportion_fields() call
        # self._normalize_proportion_fields()       # ❌ DELETE THIS LINE

        if not self.project_id:
            volume = self.pekerjaan.volume
            self.project = volume.project

        self.full_clean()
        super().save(*args, **kwargs)
```

```python
# 12. Update API (remove legacy field sync)
# File: detail_project/views_api_tahapan_v2.py (lines 219-233)

if not created:
    wp.project = project
    wp.week_start_date = week_start
    wp.week_end_date = week_end
    wp.notes = notes

    if progress_mode == 'actual':
        wp.actual_proportion = proportion_decimal
    else:  # 'planned'
        wp.planned_proportion = proportion_decimal
        # wp.proportion = proportion_decimal  # ❌ DELETE THIS LINE (no longer exists)

    wp.save()
```

**Checklist:**
- [ ] Migration file created
- [ ] Local migration successful
- [ ] Staging migration successful
- [ ] Model updated (field removed)
- [ ] Sync method removed
- [ ] API updated (no legacy field)
- [ ] All tests pass
- [ ] Smoke test passes
- [ ] Documentation updated

---

#### **Validation Queries**

Run these queries to verify data integrity:

```sql
-- 1. Check total records (should match pre-migration count)
SELECT COUNT(*) as total_records
FROM detail_project_pekerjaanprogressweekly;

-- 2. Check for NULL planned_proportion (should be 0)
SELECT COUNT(*) as null_planned
FROM detail_project_pekerjaanprogressweekly
WHERE planned_proportion IS NULL;

-- 3. Verify proportion column is gone (should error)
SELECT proportion
FROM detail_project_pekerjaanprogressweekly
LIMIT 1;
-- Expected: ERROR: column "proportion" does not exist

-- 4. Sample data check
SELECT id, pekerjaan_id, week_number,
       planned_proportion, actual_proportion
FROM detail_project_pekerjaanprogressweekly
ORDER BY id
LIMIT 10;
```

---

#### **Rollback Procedure**

**IF migration fails:**

```bash
# 1. Rollback migration
python manage.py migrate detail_project 0024

# 2. Verify rollback successful
python manage.py shell
>>> from detail_project.models import PekerjaanProgressWeekly
>>> PekerjaanProgressWeekly.objects.first().proportion
# Should work again (field restored)

# 3. Restore from backup (if data lost)
python manage.py loaddata backup_weekly_progress.json

# 4. Verify data count
python manage.py shell
>>> PekerjaanProgressWeekly.objects.count()
# Should match original count

# 5. Run smoke test
curl http://localhost:8000/detail_project/110/kelola-tahapan/

# 6. Document failure reason
# Create incident report: Why did migration fail?
# Update this roadmap with lessons learned
```

**Recovery Time Objective (RTO):** <30 minutes

---

#### **Acceptance Criteria (Task 0.1 DONE)**

- [x] Migration runs without errors (local + staging)
- [x] Zero data loss (row count matches)
- [x] Zero NULL values in planned_proportion
- [x] proportion field completely removed
- [x] _normalize_proportion_fields() method removed
- [x] API no longer references legacy field
- [x] Application loads without errors
- [x] Charts render correctly (Gantt + Kurva S)
- [x] Save functionality works
- [x] All tests pass (pytest >90% pass rate)
- [x] Documentation updated
- [x] Code review approved

**Sign-off:** ________________________ Date: __________

---

### **TASK 0.2: StateManager Implementation** (Day 3-4)

**Duration:** 2 days
- Best case: 1.5 days
- Realistic: 2 days
- Worst case: 2.5 days

**Blocking Dependencies:** Task 0.1 complete

**Required Resources:**
- Node.js development environment
- Vite dev server
- Jest (for unit testing)

---

#### **Architecture Design**

**State Management Pattern:**

```
┌─────────────────────────────────────────────────────────┐
│                    StateManager (Singleton)              │
│                                                          │
│  Responsibilities:                                       │
│  - Manage dual state (planned vs actual)                │
│  - Event-driven updates (pub/sub pattern)               │
│  - Cache merged cell values                             │
│  - Single source of truth for ALL consumers             │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
┌──────────────┐      ┌──────────────┐
│ Planned      │      │ Actual       │
│ ModeState    │      │ ModeState    │
│              │      │              │
│ - assignment │      │ - assignment │
│   Map        │      │   Map        │
│ - modified   │      │ - modified   │
│   Cells      │      │   Cells      │
│ - isDirty    │      │ - isDirty    │
└──────────────┘      └──────────────┘
        │                     │
        └──────────┬──────────┘
                   │ subscribers
        ┌──────────┴──────────────────┐
        │                             │
        ▼                             ▼
┌──────────────┐            ┌──────────────┐
│ SaveHandler  │            │ Charts       │
│              │            │ - Gantt      │
│ - Reads from │            │ - Kurva S    │
│   current    │            │              │
│   mode       │            │ - Subscribe  │
│              │            │   to updates │
└──────────────┘            └──────────────┘
```

---

#### **Implementation (Day 3)**

**File 1:** `detail_project/static/detail_project/js/src/modules/core/mode-state.js`

```javascript
/**
 * ModeState - Represents state for a single mode (planned or actual)
 *
 * Holds:
 * - assignmentMap: Saved data from API (Map<cellKey, percent>)
 * - modifiedCells: Unsaved user input (Map<cellKey, percent>)
 * - isDirty: Boolean flag for cache invalidation
 */
export class ModeState {
  constructor() {
    this.assignmentMap = new Map();  // Saved data
    this.modifiedCells = new Map();  // Unsaved changes
    this.isDirty = false;

    // Progress totals (cached)
    this.progressTotals = new Map();  // pekerjaanId → total %
    this.volumeTotals = new Map();    // pekerjaanId → total volume
  }

  /**
   * Clear all data (for reset)
   */
  clear() {
    this.assignmentMap.clear();
    this.modifiedCells.clear();
    this.progressTotals.clear();
    this.volumeTotals.clear();
    this.isDirty = true;
  }

  /**
   * Get total progress for a pekerjaan (across all columns)
   */
  getTotalProgress(pekerjaanId) {
    if (!this.isDirty && this.progressTotals.has(pekerjaanId)) {
      return this.progressTotals.get(pekerjaanId);
    }

    // Recalculate
    let total = 0;
    const prefix = `${pekerjaanId}-`;

    // Sum from assignmentMap
    this.assignmentMap.forEach((value, key) => {
      if (key.startsWith(prefix)) {
        total += parseFloat(value) || 0;
      }
    });

    // Override with modifiedCells
    this.modifiedCells.forEach((value, key) => {
      if (key.startsWith(prefix)) {
        // Subtract old value, add new value
        const oldValue = this.assignmentMap.get(key) || 0;
        total = total - oldValue + (parseFloat(value) || 0);
      }
    });

    this.progressTotals.set(pekerjaanId, total);
    return total;
  }
}
```

**File 2:** `detail_project/static/detail_project/js/src/modules/core/state-manager.js`

```javascript
/**
 * StateManager - Centralized state management for Jadwal Pekerjaan
 *
 * Replaces property delegation pattern with explicit state access.
 * Implements pub/sub for reactive updates.
 *
 * Usage:
 *   const stateManager = StateManager.getInstance();
 *   stateManager.setCellValue(pekerjaanId, columnId, 50);
 *   stateManager.on('cellChanged', (data) => chart.update());
 */

import { ModeState } from './mode-state.js';

class StateManager {
  static instance = null;

  /**
   * Singleton pattern
   */
  static getInstance() {
    if (!StateManager.instance) {
      StateManager.instance = new StateManager();
    }
    return StateManager.instance;
  }

  constructor() {
    if (StateManager.instance) {
      throw new Error('Use StateManager.getInstance() instead of new');
    }

    // Current mode: 'planned' or 'actual'
    this.currentMode = 'planned';

    // Dual state storage
    this.states = {
      planned: new ModeState(),
      actual: new ModeState()
    };

    // Cache for merged cells
    this._mergedCellsCache = new Map();

    // Event listeners (pub/sub)
    this._listeners = new Set();

    // Metadata (shared across modes)
    this.metadata = {
      volumeMap: new Map(),
      hargaMap: new Map(),
      totalBiayaProject: 0,
      timeColumns: [],
      pekerjaanTree: []
    };

    console.log('[StateManager] Initialized');
  }

  // ===================================================================
  // PUBLIC API - Cell Operations
  // ===================================================================

  /**
   * Get cell value (priority: modifiedCells > assignmentMap)
   *
   * @param {string|number} pekerjaanId - Pekerjaan ID
   * @param {string|number} columnId - Column ID
   * @returns {number} Cell value (0-100)
   */
  getCellValue(pekerjaanId, columnId) {
    const state = this._getCurrentState();
    const cellKey = `${pekerjaanId}-${columnId}`;

    // Priority: modifiedCells (unsaved) > assignmentMap (saved)
    if (state.modifiedCells.has(cellKey)) {
      return parseFloat(state.modifiedCells.get(cellKey)) || 0;
    }

    return parseFloat(state.assignmentMap.get(cellKey)) || 0;
  }

  /**
   * Set cell value (stores in modifiedCells)
   *
   * @param {string|number} pekerjaanId - Pekerjaan ID
   * @param {string|number} columnId - Column ID
   * @param {number} value - Progress percentage (0-100)
   */
  setCellValue(pekerjaanId, columnId, value) {
    const state = this._getCurrentState();
    const cellKey = `${pekerjaanId}-${columnId}`;

    // Store in modifiedCells
    state.modifiedCells.set(cellKey, value);
    state.isDirty = true;

    // Invalidate cache
    this._invalidateCache();

    // Emit event
    this._emit('cellChanged', {
      cellKey,
      pekerjaanId,
      columnId,
      value,
      mode: this.currentMode
    });

    console.log(`[StateManager] Cell changed: ${cellKey} = ${value}%`);
  }

  /**
   * Get ALL cells for a specific mode (for charts)
   * Returns merged Map (assignmentMap + modifiedCells)
   *
   * @param {string} mode - 'planned' or 'actual'
   * @returns {Map<string, number>} Merged cell values
   */
  getAllCellsForMode(mode) {
    const cacheKey = `cells:${mode}`;

    // Return cached if available
    if (this._mergedCellsCache.has(cacheKey)) {
      const cached = this._mergedCellsCache.get(cacheKey);
      if (!this.states[mode].isDirty) {
        return cached;
      }
    }

    // Build merged Map
    const state = this.states[mode];
    const merged = new Map(state.assignmentMap);

    // Override with modifiedCells
    state.modifiedCells.forEach((value, key) => {
      merged.set(key, value);
    });

    // Cache result
    this._mergedCellsCache.set(cacheKey, merged);
    state.isDirty = false;

    console.log(`[StateManager] Built merged cells for ${mode}: ${merged.size} cells`);
    return merged;
  }

  // ===================================================================
  // PUBLIC API - Mode Operations
  // ===================================================================

  /**
   * Switch between planned and actual mode
   *
   * @param {string} newMode - 'planned' or 'actual'
   */
  switchMode(newMode) {
    if (!['planned', 'actual'].includes(newMode)) {
      throw new Error(`Invalid mode: ${newMode}. Must be 'planned' or 'actual'`);
    }

    if (newMode === this.currentMode) {
      console.log(`[StateManager] Already in ${newMode} mode`);
      return;
    }

    const oldMode = this.currentMode;
    this.currentMode = newMode;

    this._emit('modeChanged', {
      oldMode,
      newMode,
      hasUnsavedChanges: this.hasUnsavedChanges()
    });

    console.log(`[StateManager] Mode switched: ${oldMode} → ${newMode}`);
  }

  /**
   * Get current mode name
   *
   * @returns {string} 'planned' or 'actual'
   */
  getCurrentMode() {
    return this.currentMode;
  }

  /**
   * Check if current mode has unsaved changes
   *
   * @returns {boolean} True if modifiedCells not empty
   */
  hasUnsavedChanges() {
    const state = this._getCurrentState();
    return state.modifiedCells.size > 0;
  }

  // ===================================================================
  // PUBLIC API - Save Operations
  // ===================================================================

  /**
   * Get cells to save (from modifiedCells)
   *
   * @returns {Map<string, number>} Modified cells
   */
  getCellsToSave() {
    const state = this._getCurrentState();
    return new Map(state.modifiedCells);
  }

  /**
   * Commit changes after successful save
   * Moves modifiedCells → assignmentMap
   */
  commitChanges() {
    const state = this._getCurrentState();

    // Move modified → assignment
    state.modifiedCells.forEach((value, key) => {
      state.assignmentMap.set(key, value);
    });

    // Clear modified
    const savedCount = state.modifiedCells.size;
    state.modifiedCells.clear();
    state.isDirty = true;

    // Invalidate cache
    this._invalidateCache();

    // Emit event
    this._emit('committed', {
      mode: this.currentMode,
      savedCount
    });

    console.log(`[StateManager] Committed ${savedCount} changes to ${this.currentMode} mode`);
  }

  /**
   * Discard unsaved changes
   */
  discardChanges() {
    const state = this._getCurrentState();
    const discardedCount = state.modifiedCells.size;

    state.modifiedCells.clear();
    state.isDirty = true;

    this._invalidateCache();

    this._emit('discarded', {
      mode: this.currentMode,
      discardedCount
    });

    console.log(`[StateManager] Discarded ${discardedCount} unsaved changes`);
  }

  // ===================================================================
  // PUBLIC API - Data Loading
  // ===================================================================

  /**
   * Load assignments from API
   *
   * @param {string} mode - 'planned' or 'actual'
   * @param {Array} assignments - [{pekerjaan_id, column_id, proportion}, ...]
   */
  loadAssignmentsForMode(mode, assignments) {
    const state = this.states[mode];

    state.assignmentMap.clear();

    assignments.forEach(item => {
      const cellKey = `${item.pekerjaan_id}-${item.column_id}`;
      state.assignmentMap.set(cellKey, item.proportion);
    });

    state.isDirty = true;
    this._invalidateCache();

    this._emit('dataLoaded', {
      mode,
      count: assignments.length
    });

    console.log(`[StateManager] Loaded ${assignments.length} assignments for ${mode} mode`);
  }

  /**
   * Load metadata (volumeMap, hargaMap, etc.)
   *
   * @param {Object} data - {volumeMap, hargaMap, totalBiayaProject, ...}
   */
  loadMetadata(data) {
    if (data.volumeMap) {
      this.metadata.volumeMap = new Map(Object.entries(data.volumeMap));
    }

    if (data.hargaMap) {
      this.metadata.hargaMap = new Map(Object.entries(data.hargaMap));
    }

    if (data.totalBiayaProject) {
      this.metadata.totalBiayaProject = data.totalBiayaProject;
    }

    if (data.timeColumns) {
      this.metadata.timeColumns = data.timeColumns;
    }

    if (data.pekerjaanTree) {
      this.metadata.pekerjaanTree = data.pekerjaanTree;
    }

    this._emit('metadataLoaded', {
      volumeMapSize: this.metadata.volumeMap.size,
      hargaMapSize: this.metadata.hargaMap.size,
      columnsCount: this.metadata.timeColumns.length
    });

    console.log('[StateManager] Metadata loaded:', {
      volumes: this.metadata.volumeMap.size,
      harga: this.metadata.hargaMap.size,
      columns: this.metadata.timeColumns.length
    });
  }

  // ===================================================================
  // PUBLIC API - Event System
  // ===================================================================

  /**
   * Subscribe to events
   *
   * Events:
   * - cellChanged: {cellKey, pekerjaanId, columnId, value, mode}
   * - modeChanged: {oldMode, newMode, hasUnsavedChanges}
   * - committed: {mode, savedCount}
   * - discarded: {mode, discardedCount}
   * - dataLoaded: {mode, count}
   * - metadataLoaded: {volumeMapSize, hargaMapSize, columnsCount}
   *
   * @param {string} event - Event name
   * @param {Function} callback - Event handler
   */
  on(event, callback) {
    this._listeners.add({ event, callback });
  }

  /**
   * Unsubscribe from events
   *
   * @param {string} event - Event name
   * @param {Function} callback - Event handler to remove
   */
  off(event, callback) {
    this._listeners.forEach(listener => {
      if (listener.event === event && listener.callback === callback) {
        this._listeners.delete(listener);
      }
    });
  }

  // ===================================================================
  // INTERNAL HELPERS
  // ===================================================================

  _getCurrentState() {
    return this.states[this.currentMode];
  }

  _invalidateCache() {
    this._mergedCellsCache.clear();
  }

  _emit(event, data) {
    this._listeners.forEach(listener => {
      if (listener.event === event) {
        try {
          listener.callback(data);
        } catch (error) {
          console.error(`[StateManager] Error in ${event} listener:`, error);
        }
      }
    });
  }
}

// Export singleton instance
export default StateManager;
```

---

#### **Unit Tests (Day 3 Afternoon)**

**File:** `detail_project/tests/frontend/test_state_manager.js`

```javascript
import { describe, it, expect, beforeEach } from '@jest/globals';
import StateManager from '../../static/detail_project/js/src/modules/core/state-manager.js';

describe('StateManager', () => {
  let stateManager;

  beforeEach(() => {
    stateManager = StateManager.getInstance();
    stateManager.states.planned.clear();
    stateManager.states.actual.clear();
    stateManager.currentMode = 'planned';
  });

  describe('Singleton Pattern', () => {
    it('should return same instance', () => {
      const instance1 = StateManager.getInstance();
      const instance2 = StateManager.getInstance();
      expect(instance1).toBe(instance2);
    });

    it('should throw error on direct instantiation', () => {
      expect(() => new StateManager()).toThrow();
    });
  });

  describe('Cell Operations', () => {
    it('should set and get cell value', () => {
      stateManager.setCellValue(123, 'col_1', 50);
      expect(stateManager.getCellValue(123, 'col_1')).toBe(50);
    });

    it('should return 0 for non-existent cell', () => {
      expect(stateManager.getCellValue(999, 'col_999')).toBe(0);
    });

    it('should prioritize modifiedCells over assignmentMap', () => {
      // Set in assignmentMap (saved)
      stateManager.states.planned.assignmentMap.set('123-col_1', 30);

      // Override in modifiedCells (unsaved)
      stateManager.setCellValue(123, 'col_1', 50);

      // Should return modified value
      expect(stateManager.getCellValue(123, 'col_1')).toBe(50);
    });
  });

  describe('Mode Switching', () => {
    it('should switch mode successfully', () => {
      stateManager.switchMode('actual');
      expect(stateManager.getCurrentMode()).toBe('actual');
    });

    it('should emit modeChanged event', () => {
      let eventData = null;
      stateManager.on('modeChanged', (data) => {
        eventData = data;
      });

      stateManager.switchMode('actual');

      expect(eventData).toEqual({
        oldMode: 'planned',
        newMode: 'actual',
        hasUnsavedChanges: false
      });
    });

    it('should isolate data between modes', () => {
      stateManager.setCellValue(123, 'col_1', 50);
      stateManager.switchMode('actual');

      // Should be 0 in actual mode
      expect(stateManager.getCellValue(123, 'col_1')).toBe(0);
    });
  });

  describe('Save Operations', () => {
    it('should commit changes correctly', () => {
      stateManager.setCellValue(123, 'col_1', 50);
      stateManager.setCellValue(123, 'col_2', 30);

      expect(stateManager.hasUnsavedChanges()).toBe(true);

      stateManager.commitChanges();

      expect(stateManager.hasUnsavedChanges()).toBe(false);
      expect(stateManager.states.planned.assignmentMap.get('123-col_1')).toBe(50);
    });

    it('should discard changes correctly', () => {
      stateManager.setCellValue(123, 'col_1', 50);
      stateManager.discardChanges();

      expect(stateManager.hasUnsavedChanges()).toBe(false);
      expect(stateManager.getCellValue(123, 'col_1')).toBe(0);
    });
  });

  describe('Cache Management', () => {
    it('should cache merged cells', () => {
      stateManager.setCellValue(123, 'col_1', 50);

      const cells1 = stateManager.getAllCellsForMode('planned');
      const cells2 = stateManager.getAllCellsForMode('planned');

      // Should return same instance (cached)
      expect(cells1).toBe(cells2);
    });

    it('should invalidate cache on cell change', () => {
      const cells1 = stateManager.getAllCellsForMode('planned');

      stateManager.setCellValue(123, 'col_1', 50);

      const cells2 = stateManager.getAllCellsForMode('planned');

      // Should be different instance (cache invalidated)
      expect(cells1).not.toBe(cells2);
    });
  });

  describe('Event System', () => {
    it('should emit cellChanged event', () => {
      let eventFired = false;
      stateManager.on('cellChanged', () => {
        eventFired = true;
      });

      stateManager.setCellValue(123, 'col_1', 50);

      expect(eventFired).toBe(true);
    });

    it('should unsubscribe events', () => {
      let eventCount = 0;
      const handler = () => { eventCount++; };

      stateManager.on('cellChanged', handler);
      stateManager.setCellValue(123, 'col_1', 50);
      expect(eventCount).toBe(1);

      stateManager.off('cellChanged', handler);
      stateManager.setCellValue(123, 'col_2', 30);
      expect(eventCount).toBe(1); // Still 1 (not incremented)
    });
  });
});
```

**Run tests:**
```bash
npm test -- test_state_manager.js
```

**Target:** >95% coverage

---

#### **Acceptance Criteria (Task 0.2 DONE)**

- [x] StateManager class implemented
- [x] ModeState class implemented
- [x] Singleton pattern working
- [x] Cell get/set operations working
- [x] Mode switching working
- [x] Commit/discard operations working
- [x] Cache invalidation working
- [x] Event system working (pub/sub)
- [x] Unit tests pass (>95% coverage)
- [x] JSDoc documentation complete
- [x] Integration test with mock data passes
- [x] No console errors
- [x] Code review approved

**Sign-off:** ________________________ Date: __________

---

### **TASK 0.3: Migrate All Consumers** (Day 5)

**Duration:** 1 day
- Best case: 0.8 days
- Realistic: 1 day
- Worst case: 1.5 days

**Blocking Dependencies:** Task 0.2 complete

**Files to Migrate:**

| File | Lines to Change | Complexity | Priority |
|------|----------------|------------|----------|
| `jadwal_kegiatan_app.js` | ~150 lines | HIGH | P0 (core) |
| `save-handler.js` | ~80 lines | MEDIUM | P0 (save) |
| `data-loader-v2.js` | ~60 lines | MEDIUM | P0 (load) |
| `gantt/frappe-gantt-setup.js` | ~40 lines | LOW | P1 (chart) |
| `kurva-s/echarts-setup.js` | ~50 lines | LOW | P1 (chart) |
| `chart-utils.js` | REMOVE | N/A | P2 (cleanup) |

**Total:** ~380 lines to refactor

---

#### **Migration Sequence (Order Matters!)**

**09:00-10:30: Step 1 - Initialize StateManager**

**File:** `jadwal_kegiatan_app.js`

```javascript
// REMOVE old delegation pattern (lines 244-343)
// DELETE:
// - _setupStateDelegation()
// - _ensureStateCollections()
// - Property getters/setters

// ADD new StateManager initialization
import StateManager from './modules/core/state-manager.js';

class JadwalKegiatanApp {
  constructor() {
    // REPLACE this.state = { ... }
    // WITH:
    this.stateManager = StateManager.getInstance();

    // Initialize metadata (will be populated by DataLoader)
    this.stateManager.metadata = {
      volumeMap: new Map(),
      hargaMap: new Map(),
      totalBiayaProject: 0,
      timeColumns: [],
      pekerjaanTree: []
    };

    // Subscribe to state changes
    this.stateManager.on('cellChanged', () => {
      this._updateCharts();  // Real-time chart update
    });

    this.stateManager.on('committed', () => {
      this._renderGrid();  // Refresh after save
    });

    console.log('[App] StateManager initialized');
  }

  // ... rest of methods
}
```

**10:30-12:00: Step 2 - Update SaveHandler**

**File:** `save-handler.js`

```javascript
// OLD (REMOVE):
_buildPayload() {
  const payload = [];
  this.state.modifiedCells.forEach((value, cellKey) => {
    // ...
  });
}

// NEW (ADD):
_buildPayload() {
  const payload = [];
  const cellsToSave = this.stateManager.getCellsToSave();

  cellsToSave.forEach((value, cellKey) => {
    const [pekerjaanId, columnId] = cellKey.split('-');
    const weekNumber = this._getWeekNumber(columnId);

    payload.push({
      pekerjaan_id: parseInt(pekerjaanId),
      week_number: weekNumber,
      proportion: parseFloat(value)
    });
  });

  return payload;
}

// OLD (REMOVE):
_updateAssignmentMap() {
  const modeState = this._getCurrentModeState();
  modeState.modifiedCells.forEach((value, key) => {
    modeState.assignmentMap.set(key, value);
  });
  modeState.modifiedCells.clear();
}

// NEW (ADD):
_handleSaveSuccess(response) {
  // Commit changes (moves modifiedCells → assignmentMap)
  this.stateManager.commitChanges();

  toast.success('Progress saved successfully');
  this._renderGrid();
}
```

**13:00-14:30: Step 3 - Update DataLoader**

**File:** `data-loader-v2.js`

```javascript
// OLD (REMOVE):
_populateState(data) {
  this.state.assignmentMap.clear();
  data.assignments.forEach(item => {
    const key = `${item.pekerjaan_id}-${item.column_id}`;
    this.state.assignmentMap.set(key, item.proportion);
  });
}

// NEW (ADD):
_populateState(data) {
  // Load assignments into correct mode
  const mode = this.stateManager.getCurrentMode();
  this.stateManager.loadAssignmentsForMode(mode, data.assignments);

  // Load metadata
  this.stateManager.loadMetadata({
    volumeMap: data.volumeMap,
    hargaMap: data.hargaMap,
    totalBiayaProject: data.totalBiayaProject,
    timeColumns: this.state.timeColumns,
    pekerjaanTree: this.state.pekerjaanTree
  });
}
```

**14:30-16:00: Step 4 - Update Gantt Chart**

**File:** `gantt/frappe-gantt-setup.js`

```javascript
// OLD (REMOVE):
_buildAssignmentBuckets() {
  const buckets = new Map();
  this.state.assignmentMap.forEach((value, key) => {
    // ...
  });
}

// NEW (ADD):
_buildAssignmentBuckets() {
  const buckets = new Map();

  // Get merged cells for current mode
  const mode = this.stateManager.getCurrentMode();
  const cells = this.stateManager.getAllCellsForMode(mode);

  cells.forEach((value, key) => {
    const [pekerjaanId, columnId] = key.split('-');

    if (!buckets.has(pekerjaanId)) {
      buckets.set(pekerjaanId, {
        pekerjaanId,
        totalPercent: 0,
        segments: []
      });
    }

    const bucket = buckets.get(pekerjaanId);
    bucket.totalPercent += parseFloat(value) || 0;
    // ... rest of logic
  });

  return buckets;
}
```

**16:00-17:00: Step 5 - Update Kurva S**

**File:** `kurva-s/echarts-setup.js`

```javascript
// OLD (REMOVE):
_buildDataset() {
  const plannedState = this.state.plannedState;
  const actualState = this.state.actualState;

  const plannedCells = buildCellValueMap(plannedState);
  const actualCells = buildCellValueMap(actualState);
  // ...
}

// NEW (ADD):
_buildDataset() {
  // Get cells from StateManager
  const plannedCells = this.stateManager.getAllCellsForMode('planned');
  const actualCells = this.stateManager.getAllCellsForMode('actual');

  // Get metadata
  const volumeLookup = this.stateManager.metadata.volumeMap;
  const hargaLookup = this.stateManager.metadata.hargaMap;
  const totalBiaya = this.stateManager.metadata.totalBiayaProject;

  // Calculate curves (rest of logic unchanged)
  // ...
}
```

**17:00-17:30: Step 6 - Remove Legacy Code**

**File:** `chart-utils.js`

```javascript
// DELETE entire buildCellValueMap() function (lines 327-350)
// This is now handled by StateManager.getAllCellsForMode()

// REMOVE exports:
// export function buildCellValueMap(state) { ... }
```

---

#### **Verification Checklist**

After migration, verify:

**Functional Tests:**
- [ ] Page loads without errors
- [ ] Can input values in grid cells
- [ ] Real-time validation works
- [ ] Save button saves successfully
- [ ] Gantt Chart renders correctly
- [ ] Kurva S renders correctly
- [ ] Charts update in real-time on cell change
- [ ] Mode switch (planned ↔ actual) works
- [ ] Unsaved changes warning works

**Console Checks:**
```javascript
// Open browser console:
console.log(window.kelolaTahapanPageState);
// Should NOT have:
// - assignmentMap (old delegation)
// - modifiedCells (old delegation)
// Should HAVE:
// - stateManager (new pattern)

console.log(stateManager.getAllCellsForMode('planned').size);
// Should show number of cells with data

console.log(stateManager.metadata.hargaMap.size);
// Should show number of pekerjaan with harga data
```

**Performance Tests:**
```javascript
// Measure cell set performance
console.time('setCellValue');
for (let i = 0; i < 1000; i++) {
  stateManager.setCellValue(123, `col_${i}`, 50);
}
console.timeEnd('setCellValue');
// Should be <100ms for 1000 operations
```

---

#### **Acceptance Criteria (Task 0.3 DONE)**

- [x] All consumers migrated to StateManager
- [x] No references to old delegation pattern
- [x] buildCellValueMap() removed
- [x] Page loads without errors
- [x] All features working (grid, save, charts)
- [x] Real-time updates working
- [x] Mode switching working
- [x] Performance acceptable (<100ms for 1000 ops)
- [x] All tests pass
- [x] Code review approved
- [x] Documentation updated

**Sign-off:** ________________________ Date: __________

---

## END OF PHASE 0

**When Phase 0 is complete:**
- Database schema clean (legacy proportion fields removed)
- StateManager implemented and tested
- All consumers using single pattern (StateManager instead of assignmentMap)
- Zero technical debt blocking feature work
- Ready for feature development

**Proceed to:** Phase 1 (Week 2-3) - Core Features

### Current Baseline (November 2025)
- AG Grid stack (`static/detail_project/js/src/modules/grid/*.js`) already handles loading/saving via API v2 but still depends on legacy per-module state.
- Chart adapters (`modules/gantt/frappe-gantt-setup.js` and `modules/kurva-s/echarts-setup.js`) render successfully yet still read from `this.state` and duplicate calculations.
- Backend canonical sources exist: `views_api.api_kurva_s_data` builds harga maps, `services.compute_kebutuhan_items()` aggregates kebutuhan material/alat/tenaga, and Rekap Kebutuhan exports run through `exports/rekap_kebutuhan.py`.
- Documentation stubs (`PHASE_2F_*`, `PHASE_2G_*`) describe desired output but are not reflected in production code.

---

## Phase 1: Core Features (Week 2-3)

**Goal:** Port Kurva S dan Rekap Kebutuhan ke fondasi baru agar dua fitur memakai data mingguan kanonik + StateManager.

### Task 1 - Phase 2F.1: Kurva S Harga Integration (Week 2, Days 1-3)
**Scope (sesuai script saat ini):**
- Backend API sudah ada di `detail_project/views_api.py:4169` namun masih bergantung pada `compute_rekap_for_project` tanpa cache metadata dan belum punya tes.
- Modul frontend `static/detail_project/js/src/modules/kurva-s/echarts-setup.js` masih membaca `this.state`.
- Belum ada automated test (`detail_project/tests/test_kurva_s_harga.py` belum dibuat).

**Langkah Implementasi**
1. Stabilisasi response API
   - Reuse `compute_rekap_for_project()` tetapi tambah deterministic ordering, hint cache, dan trimming `pekerjaanMeta` supaya payload <1 MB.
   - Tambahkan permission check (reuse `dashboard.permissions.can_view_project` bila tersedia).
2. Hubungkan ke StateManager
   - Setelah Phase 0, ambil data sel melalui `stateManager.getAllCellsForMode()` dan gunakan payload API hanya untuk metadata.
   - Pindahkan format mata uang + builder tooltip ke `modules/kurva-s/curve-calculations.js` agar adapter ringan.
3. Testing + dokumentasi
   - Buat `detail_project/tests/test_kurva_s_harga.py` yang mengunci total harga, perbandingan planned/actual, dan metadata.
   - Update `JADWAL_KEGIATAN_CLIENT_GUIDE.md` dengan penjelasan kurva planned/actual serta harga-weighted.

**Acceptance Criteria**
- `/api/v2/project/<id>/kurva-s-data/` mengembalikan total harga yang match Rekap RAB +/-0.1%.
- `echarts-setup.js` hanya membaca melalui StateManager; tidak ada lagi referensi `this.state.plannedState`.
- Toggle planned/actual/both merender ulang tanpa kehilangan tooltip atau scale.
- Modul pytest baru berjalan dan dimasukkan ke CI (`pytest detail_project/tests/test_kurva_s_harga.py`).

### Task 2 - Phase 2G: Rekap Kebutuhan Integration (Week 3, Days 1-3)
**Scope (sesuai script saat ini):**
- Helper `services.compute_kebutuhan_items()` sudah menghitung bundle multiplier (lihat `services.py:1763`).
- Template `templates/detail_project/rekap_kebutuhan.html` dan skrip `static/detail_project/js/rekap_kebutuhan_enhanced.js` masih bergantung pada endpoint legacy.

**Langkah Implementasi**
1. Penyelarasan API
   - Tambah view `/api/v2/project/<id>/rekap-kebutuhan/` yang memanggil `compute_kebutuhan_items()` dengan opsi `mode=weekly|monthly|tahapan`.
   - Tambah pagination + streaming export via `exports/rekap_kebutuhan_adapter.py`.
2. Refresh frontend
   - Ganti dataset inline di template dengan fetch asinron + hydrasi dataset seperti Jadwal grid.
   - Update `rekap_kebutuhan_enhanced.js` agar toggle weekly/monthly memakai `StateManager.metadata.volumeMap`.
3. Tests & fixtures
   - Perluas `detail_project/tests/test_tahapan.py` dan `test_bundle_quantity_semantic.py` untuk memukul endpoint baru.
   - Ambil baseline CSV/PDF export untuk dibandingkan setelah rilis.

**Acceptance Criteria**
- Halaman Rekap Kebutuhan render <500 ms memakai data kanonik (cek Chrome DevTools).
- Toggle weekly/monthly memakai dataset yang sama tanpa re-fetch server.
- CSV/PDF/Word export memakai adapter baru dan match baseline fixtures.
- Checklist QA manual (`TESTING_AGENDA.md` Page 7) selesai.

### Task 3 - Chart & Documentation QA (Week 3, Day 4-5)
- Regression test Jadwal grid + Kurva S + Rekap Kebutuhan (edit grid -> chart dan rekap ikut berubah tanpa reload).
- Update `JADWAL_KEGIATAN_CLIENT_GUIDE.md`, `FINAL_IMPLEMENTATION_PLAN.md`, dan changelog dengan screenshot + contoh API.
- Tag release candidate `option-c-phase1` lalu freeze sebelum sprint optimasi.

---

## Phase 2: Optimization & Build Hardening (Week 4)

### Task 2.1 - API Bundling & Performance (Days 1-2)
- Konsolidasikan endpoint Jadwal agar `/api/v2/project/<id>/assignments/`, `/kurva-s-data/`, dan `/rekap-kebutuhan/` berbagi helper memoized di `services.py` (target <=3 query per load).
- Aktifkan cache Redis (`cache.set('kurva_s:<project_id>', ...)`) dengan invalidasi di `services.invalidate_rekap_cache`.
- Tambahkan hook monitoring `monitoring_helpers.log_operation`.

### Task 2.2 - Build Optimization (Days 3-4)
- Update `vite.config.js` untuk manual chunking (pisahkan grid, gantt, kurva) dan aktifkan treeshaking `echarts` + `ag-grid`.
- Gunakan bundle modern AG Grid (ESM) dan bersihkan renderer yang tidak dipakai.
- Jalankan `npm run build` + `npm run benchmark` untuk menyimpan statistik (<250 KB gzipped untuk `jadwal-kegiatan.js`).

### Task 2.3 - Load Testing & Profiling (Day 5)
- Seed proyek 10k baris, profilkan scroll/edit (Chrome Performance + Lighthouse).
- Jalankan `python manage.py test detail_project/tests/test_hsp_fix.py` serta suite baru guna memastikan tidak ada regresi.
- Catat temuan di `PERFORMANCE_OPTIMIZATION_ROADMAP.md`.

---

## Phase 3: Deployment & Monitoring (Week 5)

### Task 3.1 - Staging Deployment & Smoke Tests (Days 1-2)
- Deploy ke staging, jalankan `collectstatic`, `npm run build`, serta migration Phase 0.
- Smoke test: Jadwal grid edit/save, Kurva S toggle, Rekap Kebutuhan export, plus regresi Bundle Quantity (lihat `REFACTOR_PROGRESS_TRACKER.md` Phase 7).

### Task 3.2 - UAT & Sign-off (Day 3)
- Demo ke klien memakai `JADWAL_KEGIATAN_CLIENT_GUIDE.md`.
- Rekap feedback ke `RELEASE_NOTES_OPTION_C.md` sebelum release.

### Task 3.3 - Production Deployment & Monitoring (Days 4-5)
- Deploy (blue/green atau maintenance window), aktifkan `USE_AG_GRID=True`, jalankan `python manage.py collectstatic`.
- Monitor log (`log_operation`) dan metrik (memory, page load). Siapkan branch hotfix selama 48 jam.

---

## Rollback Strategy

### Data & Schema
1. Restore `backup_weekly_progress.json` via `python manage.py loaddata` bila migrasi gagal.
2. Downgrade ke migration `0024` (`python manage.py migrate detail_project 0024`) lalu ulangi smoke test.

### Frontend & Build
1. Revert ke tag stabil sebelumnya (`git checkout v1.0.0-jadwal && npm install && npm run build`).
2. Set `ENABLE_AG_GRID=False` di `config/settings/base.py` bila perlu fallback ke grid legacy.

### Monitoring & Communication
- Target RTO: 30 menit untuk rollback schema, 15 menit untuk frontend.
- Dokumentasikan akar masalah di `ROLLBACK_PLAN_OPTION_C.md` dan revisi roadmap.

---

## TOTAL DURATION: 5 weeks

**Week 1:** Phase 0 - Foundation Cleanup  
**Week 2-3:** Phase 1 - Core Features  
**Week 4:** Phase 2 - Optimization  
**Week 5:** Phase 3 - Deployment

---

**Last Updated:** 2025-11-27  
**Status:** PRODUCTION READY - AWAITING EXECUTION APPROVAL  
**Next Action:** User approval + start Phase 0.1
