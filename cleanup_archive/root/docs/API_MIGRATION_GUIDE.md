# API Migration Guide: v1 → v2
**Django AHSP Project - Jadwal Pekerjaan API**

## Overview

This guide documents the migration from API v1 (tahapan-based assignments) to API v2 (weekly canonical storage).

### Why Migrate?

**API v1 Issues:**
- ❌ Data stored in daily `TahapanPelaksanaan` records
- ❌ Inconsistent aggregation when switching time scales
- ❌ Complex logic to sync daily → weekly → monthly views
- ❌ Performance issues with large date ranges

**API v2 Benefits:**
- ✅ Single source of truth: `PekerjaanProgressWeekly` model
- ✅ Consistent data across all time scales (daily/weekly/monthly)
- ✅ Better performance (weekly aggregation only)
- ✅ Simpler logic, fewer bugs
- ✅ Supports week boundary preferences

---

## Deprecation Timeline

| Date | Milestone |
|------|-----------|
| **2025-01-15** | API v1 marked as deprecated (warnings added) |
| **2025-01-15 → 2025-02-14** | 30-day monitoring period (both APIs available) |
| **2025-02-14** | API v1 removed (sunset date) |

---

## Migration Paths

### 1. **Assign Progress to Pekerjaan**

#### v1 (Deprecated):
```http
POST /api/project/{project_id}/tahapan/{tahapan_id}/assign/
Content-Type: application/json

{
  "pekerjaan_id": 123,
  "nilai": 50.0,
  "tipe": "persentase"
}
```

**Issues**:
- Requires tahapan_id (daily/weekly/monthly dependent)
- Must manually create tahapan records first
- Data inconsistent when switching time scales

#### v2 (Recommended):
```http
POST /api/v2/project/{project_id}/assign-weekly/
Content-Type: application/json

{
  "pekerjaan_id": 123,
  "assignments": [
    {
      "week_number": 1,
      "week_start_date": "2025-01-06",
      "week_end_date": "2025-01-12",
      "planned_percentage": 25.0,
      "planned_volume": 100.0,
      "actual_percentage": 20.0,
      "actual_volume": 80.0
    },
    {
      "week_number": 2,
      "week_start_date": "2025-01-13",
      "week_end_date": "2025-01-19",
      "planned_percentage": 25.0,
      "planned_volume": 100.0
    }
  ]
}
```

**Benefits**:
- No tahapan_id needed
- Canonical weekly storage
- Supports both planned and actual progress
- Week boundaries preserved

**Migration Code:**
```javascript
// OLD (v1)
async function assignProgress(pekerjaanId, tahapanId, nilai) {
  return await fetch(`/api/project/${projectId}/tahapan/${tahapanId}/assign/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pekerjaan_id: pekerjaanId, nilai, tipe: 'persentase' })
  });
}

// NEW (v2)
async function assignProgressWeekly(pekerjaanId, weeklyAssignments) {
  return await fetch(`/api/v2/project/${projectId}/assign-weekly/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      pekerjaan_id: pekerjaanId,
      assignments: weeklyAssignments
    })
  });
}
```

---

### 2. **Get Pekerjaan Assignments**

#### v1 (Deprecated):
```http
GET /api/project/{project_id}/pekerjaan/{pekerjaan_id}/assignments/
```

**Returns**: Daily tahapan assignments (inconsistent across time scales)

#### v2 (Recommended):
```http
GET /api/v2/project/{project_id}/pekerjaan/{pekerjaan_id}/assignments/
  ?mode=weekly
  &week_start_day=0
  &week_end_day=6
```

**Returns**: Assignments in any view mode (daily/weekly/monthly) with consistent data

**Query Parameters:**
- `mode`: `daily` | `weekly` | `monthly` (default: `weekly`)
- `week_start_day`: 0-6 (Monday=0, default: 0)
- `week_end_day`: 0-6 (Sunday=6, default: 6)

**Response Format:**
```json
{
  "pekerjaan_id": 123,
  "mode": "weekly",
  "assignments": [
    {
      "week_number": 1,
      "week_start_date": "2025-01-06",
      "week_end_date": "2025-01-12",
      "planned_percentage": 25.0,
      "actual_percentage": 20.0,
      "cumulative_planned": 25.0,
      "cumulative_actual": 20.0
    }
  ],
  "total_planned": 100.0,
  "total_actual": 80.0
}
```

---

### 3. **Regenerate Tahapan (Timeline)**

#### v1 (Deprecated):
```http
POST /api/project/{project_id}/regenerate-tahapan/
Content-Type: application/json

{
  "time_scale": "weekly",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31"
}
```

**Issues**: Creates new tahapan records, but doesn't preserve existing assignments properly

#### v2 (Recommended):
```http
POST /api/v2/project/{project_id}/regenerate-tahapan/
Content-Type: application/json

{
  "time_scale": "weekly",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "week_start_day": 0,
  "week_end_day": 6,
  "sync_from_weekly": true
}
```

**Benefits**:
- Syncs assignments from canonical weekly storage
- Preserves week boundary preferences
- Maintains data consistency

---

### 4. **Get Weekly Progress (Canonical)**

#### v2 Only (New Endpoint):
```http
GET /api/v2/project/{project_id}/pekerjaan/{pekerjaan_id}/weekly-progress/
```

**Returns**: Raw canonical weekly storage data
```json
{
  "pekerjaan_id": 123,
  "weekly_progress": [
    {
      "id": 456,
      "week_number": 1,
      "week_start_date": "2025-01-06",
      "week_end_date": "2025-01-12",
      "planned_percentage": 25.0,
      "planned_volume": 100.0,
      "actual_percentage": 20.0,
      "actual_volume": 80.0,
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T14:30:00Z"
    }
  ]
}
```

---

## Response Header Changes

All v1 endpoints now return deprecation headers:

```http
HTTP/1.1 200 OK
X-API-Deprecated: true
X-API-Sunset: 2025-02-14
X-API-Migration-Endpoint: https://example.com/api/v2/project/123/assign-weekly/
X-API-Deprecation-Reason: Migrated to weekly canonical storage (v2)
X-API-Deprecation-Info: This endpoint is deprecated and will be removed on 2025-02-14. Migrate to: api_v2_assign_weekly
Link: <https://docs.example.com/api-migration-guide>; rel="deprecation"
```

**Client Action Required:**
1. Check for `X-API-Deprecated` header in responses
2. Log warnings to notify developers
3. Plan migration before sunset date
4. Use `X-API-Migration-Endpoint` to find replacement

---

## Complete Endpoint Mapping

| v1 Endpoint (Deprecated) | v2 Endpoint (Recommended) | Notes |
|--------------------------|---------------------------|-------|
| `POST /api/project/{id}/tahapan/{tid}/assign/` | `POST /api/v2/project/{id}/assign-weekly/` | Weekly canonical storage |
| `POST /api/project/{id}/tahapan/{tid}/unassign/` | `POST /api/v2/project/{id}/assign-weekly/` | Set assignment to 0 or omit |
| `GET /api/project/{id}/pekerjaan/{pid}/assignments/` | `GET /api/v2/project/{id}/pekerjaan/{pid}/assignments/` | Add `?mode=weekly` param |
| `POST /api/project/{id}/regenerate-tahapan/` | `POST /api/v2/project/{id}/regenerate-tahapan/` | Add `sync_from_weekly=true` |
| `GET /api/project/{id}/tahapan/` | `GET /api/v2/project/{id}/assignments/` | Get all project assignments |

---

## Frontend Migration Checklist

### 1. **Update API Client**

```javascript
// OLD: src/api/tahapan-api-v1.js (REMOVE)
class TahapanAPIv1 {
  async assignPekerjaan(projectId, tahapanId, pekerjaanId, nilai) {
    // ... v1 implementation
  }
}

// NEW: src/api/tahapan-api-v2.js (USE THIS)
class TahapanAPIv2 {
  async assignPekerjaanWeekly(projectId, pekerjaanId, assignments) {
    const response = await fetch(
      `/api/v2/project/${projectId}/assign-weekly/`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pekerjaan_id: pekerjaanId, assignments })
      }
    );
    return response.json();
  }

  async getAssignments(projectId, pekerjaanId, mode = 'weekly', weekBoundary = { start: 0, end: 6 }) {
    const params = new URLSearchParams({
      mode,
      week_start_day: weekBoundary.start,
      week_end_day: weekBoundary.end
    });

    const response = await fetch(
      `/api/v2/project/${projectId}/pekerjaan/${pekerjaanId}/assignments/?${params}`
    );
    return response.json();
  }
}
```

### 2. **Update State Manager**

```javascript
// File: state-manager.js

// OLD: Store tahapan assignments
class StateManagerV1 {
  constructor() {
    this.tahapanAssignments = new Map(); // tahapan_id → { pekerjaan_id, nilai }
  }
}

// NEW: Store weekly canonical data
class StateManagerV2 {
  constructor() {
    this.weeklyAssignments = new Map(); // pekerjaan_id → Map(week_number → assignment)
  }

  setWeeklyAssignment(pekerjaanId, weekNumber, assignment) {
    if (!this.weeklyAssignments.has(pekerjaanId)) {
      this.weeklyAssignments.set(pekerjaanId, new Map());
    }
    this.weeklyAssignments.get(pekerjaanId).set(weekNumber, assignment);
  }

  getWeeklyAssignments(pekerjaanId) {
    return this.weeklyAssignments.get(pekerjaanId) || new Map();
  }
}
```

### 3. **Update Chart Data Loaders**

```javascript
// OLD: Load from tahapan
async function loadChartDataV1() {
  const response = await fetch(`/api/project/${projectId}/pekerjaan/${pekerjaanId}/assignments/`);
  const data = await response.json();
  // Data inconsistent across time scales
  return data;
}

// NEW: Load from weekly canonical
async function loadChartDataV2(mode = 'weekly') {
  const response = await fetch(
    `/api/v2/project/${projectId}/pekerjaan/${pekerjaanId}/assignments/?mode=${mode}`
  );
  const data = await response.json();
  // Data consistent regardless of mode
  return data;
}
```

---

## Testing Migration

### 1. **Parallel Testing (Recommended)**

Run both APIs side-by-side during migration period:

```javascript
async function testMigration(projectId, pekerjaanId) {
  // Call both v1 and v2
  const [v1Response, v2Response] = await Promise.all([
    fetch(`/api/project/${projectId}/pekerjaan/${pekerjaanId}/assignments/`),
    fetch(`/api/v2/project/${projectId}/pekerjaan/${pekerjaanId}/assignments/?mode=weekly`)
  ]);

  const v1Data = await v1Response.json();
  const v2Data = await v2Response.json();

  // Compare results
  console.log('v1 Data:', v1Data);
  console.log('v2 Data:', v2Data);
  console.log('Deprecation Headers:', {
    deprecated: v1Response.headers.get('X-API-Deprecated'),
    sunset: v1Response.headers.get('X-API-Sunset'),
    migration: v1Response.headers.get('X-API-Migration-Endpoint')
  });
}
```

### 2. **Data Validation**

```javascript
// Verify weekly canonical storage matches tahapan assignments
async function validateMigration(projectId) {
  const response = await fetch(`/api/v2/project/${projectId}/assignments/`);
  const { assignments, validation_summary } = await response.json();

  console.log('Total Assignments:', assignments.length);
  console.log('Data Integrity:', validation_summary);

  // Check for discrepancies
  const issues = assignments.filter(a => a.has_discrepancy);
  if (issues.length > 0) {
    console.warn('Found data discrepancies:', issues);
  }
}
```

---

## Monitoring Deprecated API Usage

### Server-Side Logging

All v1 API calls are logged:

```python
# Check deprecation metrics
from detail_project.decorators import get_deprecation_metrics

metrics = get_deprecation_metrics()
for endpoint, stats in metrics.items():
    print(f"{endpoint}: {stats['count']} calls since {stats['first_seen']}")
```

**Sample Output:**
```
api_assign_pekerjaan_to_tahapan: 142 calls since 2025-01-15T10:30:00
api_unassign_pekerjaan_from_tahapan: 58 calls since 2025-01-15T11:00:00
api_get_pekerjaan_assignments: 1024 calls since 2025-01-15T10:00:00
```

### Client-Side Detection

```javascript
// Detect deprecated API usage in frontend
class APIClient {
  async request(url, options) {
    const response = await fetch(url, options);

    // Check for deprecation headers
    if (response.headers.get('X-API-Deprecated') === 'true') {
      const sunset = response.headers.get('X-API-Sunset');
      const migration = response.headers.get('X-API-Migration-Endpoint');
      const reason = response.headers.get('X-API-Deprecation-Reason');

      console.warn(`
        ⚠️ DEPRECATED API USED: ${url}
        Sunset Date: ${sunset}
        Migration: ${migration}
        Reason: ${reason}
      `);

      // Send to monitoring service
      trackDeprecation({ url, sunset, migration, reason });
    }

    return response;
  }
}
```

---

## Common Migration Issues

### Issue 1: Week Boundary Mismatch

**Problem**: v1 uses ISO weeks (Mon-Sun), v2 supports custom boundaries

**Solution**: Always specify week boundaries in v2 calls
```javascript
// Specify custom week boundary (e.g., Sun-Sat)
const response = await fetch(
  `/api/v2/project/${projectId}/pekerjaan/${pekerjaanId}/assignments/` +
  `?mode=weekly&week_start_day=6&week_end_day=5`
);
```

### Issue 2: Missing Canonical Data

**Problem**: Old projects may not have weekly canonical storage

**Solution**: Trigger one-time migration
```javascript
// Migrate existing tahapan data to weekly canonical
const response = await fetch(`/api/v2/project/${projectId}/regenerate-tahapan/`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    time_scale: 'weekly',
    start_date: '2025-01-01',
    end_date: '2025-12-31',
    sync_from_weekly: true,
    migrate_existing: true  // Migrate from tahapan → weekly
  })
});
```

### Issue 3: Cumulative Calculations

**Problem**: v1 didn't track cumulative progress, v2 does

**Solution**: v2 automatically calculates cumulative values
```json
{
  "week_number": 3,
  "planned_percentage": 25.0,
  "actual_percentage": 20.0,
  "cumulative_planned": 75.0,  // Auto-calculated
  "cumulative_actual": 60.0    // Auto-calculated
}
```

---

## Support & Questions

- **Documentation**: See [ROADMAP_IMPLEMENTASI_OPTIMISASI_JADWAL.md](ROADMAP_IMPLEMENTASI_OPTIMISASI_JADWAL.md)
- **Issues**: Report at project issue tracker
- **Migration Deadline**: 2025-02-14

---

**Last Updated**: 2025-01-15
**Status**: v1 Deprecated (30-day sunset period)
**Next Review**: 2025-02-14 (v1 removal)
