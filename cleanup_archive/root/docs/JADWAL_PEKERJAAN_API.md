# Jadwal Pekerjaan - API Documentation

## Overview

This document describes all API endpoints used by the Jadwal Pekerjaan (Work Schedule) feature. All endpoints require authentication and project ownership validation.

**Base Path**: `/detail_project/api/project/<project_id>/`

**Authentication**: All endpoints require `@login_required` decorator

**Authorization**: User must be the project owner (validated via `_owner_or_404()`)

---

## Table of Contents

1. [Tahapan Management](#tahapan-management)
2. [Pekerjaan Assignments](#pekerjaan-assignments)
3. [Time Scale Mode Switching](#time-scale-mode-switching)
4. [Volume Data](#volume-data)
5. [Summary & Reporting](#summary--reporting)
6. [Error Handling](#error-handling)

---

## Tahapan Management

### 1. List / Create Tahapan

**Endpoint**: `GET/POST /api/project/<project_id>/tahapan/`

**File**: `views_api_tahapan.py:api_list_create_tahapan`

#### GET Request

Returns list of all tahapan for the project with summary data.

**Response**:
```json
{
  "ok": true,
  "tahapan": [
    {
      "tahapan_id": 855,
      "nama": "Week 1: 26 Oct - 27 Oct",
      "urutan": 1,
      "deskripsi": "Auto-generated weekly tahapan",
      "jumlah_pekerjaan": 5,
      "total_assigned_proportion": 89.52,
      "tanggal_mulai": "2025-10-26",
      "tanggal_selesai": "2025-10-27",
      "created_at": "2025-10-26T10:30:00Z",
      "is_auto_generated": true,
      "generation_mode": "weekly"
    }
  ],
  "count": 11
}
```

**Field Descriptions**:
- `tahapan_id`: Unique identifier for tahapan
- `nama`: Tahapan name/label
- `urutan`: Sort order (integer)
- `deskripsi`: Optional description
- `jumlah_pekerjaan`: Number of distinct pekerjaan assigned
- `total_assigned_proportion`: Sum of all assignment proportions (%)
- `tanggal_mulai/tanggal_selesai`: Date range for tahapan
- `created_at`: Timestamp when tahapan was created
- `is_auto_generated`: Boolean flag (true = system-generated, false = user-created)
- `generation_mode`: Mode used to generate tahapan (daily/weekly/monthly/custom)

#### POST Request

Creates a new custom tahapan.

**Request Body**:
```json
{
  "nama": "Tahap Persiapan Lanjutan",
  "deskripsi": "Tahap persiapan tambahan",
  "urutan": 5,
  "tanggal_mulai": "2025-11-01",
  "tanggal_selesai": "2025-11-07"
}
```

**Response (Success)**:
```json
{
  "ok": true,
  "tahapan": {
    "tahapan_id": 870,
    "nama": "Tahap Persiapan Lanjutan",
    "urutan": 5,
    ...
  },
  "message": "Tahapan created successfully"
}
```

**Response (Error)**:
```json
{
  "ok": false,
  "error": "Nama tahapan harus diisi"
}
```

**Validation Rules**:
- `nama`: Required, must be unique within project
- `urutan`: Auto-incremented if not provided
- Dates must be valid ISO format

---

### 2. Update / Delete Tahapan

**Endpoint**: `PUT/DELETE /api/project/<project_id>/tahapan/<tahapan_id>/`

**File**: `views_api_tahapan.py:api_update_delete_tahapan`

#### PUT Request

Updates an existing tahapan.

**Request Body**:
```json
{
  "nama": "Updated Name",
  "deskripsi": "Updated description",
  "tanggal_mulai": "2025-11-01",
  "tanggal_selesai": "2025-11-07"
}
```

**Response**:
```json
{
  "ok": true,
  "tahapan": { ... },
  "message": "Tahapan updated successfully"
}
```

#### DELETE Request

Deletes a tahapan and all its assignments.

**Response**:
```json
{
  "ok": true,
  "message": "Tahapan deleted successfully"
}
```

**Notes**:
- Deleting tahapan will CASCADE delete all `PekerjaanTahapan` records
- Cannot be undone

---

### 3. Reorder Tahapan

**Endpoint**: `POST /api/project/<project_id>/tahapan/reorder/`

**File**: `views_api_tahapan.py:api_reorder_tahapan`

Updates the sort order of multiple tahapan.

**Request Body**:
```json
{
  "order": [
    {"id": 855, "urutan": 1},
    {"id": 856, "urutan": 2},
    {"id": 857, "urutan": 3}
  ]
}
```

**Response**:
```json
{
  "ok": true,
  "message": "Tahapan reordered successfully",
  "updated_count": 3
}
```

**Notes**:
- All tahapan IDs must belong to the project
- Updates are performed in a transaction

---

## Pekerjaan Assignments

### 4. Assign Pekerjaan to Tahapan

**Endpoint**: `POST /api/project/<project_id>/tahapan/<tahapan_id>/assign/`

**File**: `views_api_tahapan.py:api_assign_pekerjaan_to_tahapan`

Assigns pekerjaan to a tahapan with a proportion percentage.

**Request Body**:
```json
{
  "assignments": [
    {
      "pekerjaan_id": 322,
      "proporsi": 33.33
    },
    {
      "pekerjaan_id": 324,
      "proporsi": 66.67
    }
  ]
}
```

**Response**:
```json
{
  "ok": true,
  "message": "2 assignments created/updated",
  "assignments": [
    {
      "pekerjaan_id": 322,
      "tahapan_id": 855,
      "proporsi": 33.33
    },
    {
      "pekerjaan_id": 324,
      "tahapan_id": 855,
      "proporsi": 66.67
    }
  ]
}
```

**Validation**:
- `proporsi`: Must be between 0.01 and 100.00
- Duplicate assignments are UPDATE-d (upsert behavior)
- Pekerjaan must belong to the same project

---

### 5. Unassign Pekerjaan from Tahapan

**Endpoint**: `POST /api/project/<project_id>/tahapan/<tahapan_id>/unassign/`

**File**: `views_api_tahapan.py:api_unassign_pekerjaan_from_tahapan`

Removes pekerjaan assignments from a tahapan.

**Request Body**:
```json
{
  "pekerjaan_ids": [322, 324, 330]
}
```

**Response**:
```json
{
  "ok": true,
  "message": "3 assignments removed",
  "deleted_count": 3
}
```

---

### 6. Get Pekerjaan Assignments

**Endpoint**: `GET /api/project/<project_id>/pekerjaan/<pekerjaan_id>/assignments/`

**File**: `views_api_tahapan.py:api_get_pekerjaan_assignments`

Returns all tahapan assignments for a specific pekerjaan.

**Response**:
```json
{
  "ok": true,
  "pekerjaan_id": 322,
  "assignments": [
    {
      "tahapan_id": 855,
      "tahapan_nama": "Week 1: 26 Oct - 27 Oct",
      "proporsi": 33.33,
      "urutan": 1
    },
    {
      "tahapan_id": 856,
      "tahapan_nama": "Week 2: 28 Oct - 03 Nov",
      "proporsi": 66.67,
      "urutan": 2
    }
  ],
  "total_proporsi": 100.00
}
```

**Uses**:
- Used by frontend to populate grid cells
- Called during initial data load
- Returns assignments sorted by `urutan`

---

## Time Scale Mode Switching

### 7. Regenerate Tahapan

**Endpoint**: `POST /api/project/<project_id>/regenerate-tahapan/`

**File**: `views_api_tahapan.py:api_regenerate_tahapan`

Regenerates tahapan based on time scale mode and optionally converts existing assignments.

**Request Body**:
```json
{
  "mode": "weekly",
  "week_end_day": 0,
  "convert_assignments": true
}
```

**Parameters**:
- `mode`: One of `daily`, `weekly`, `monthly`, `custom` (required)
- `week_end_day`: Integer 0-6 representing day of week for week boundary (0=Sunday, 6=Saturday)
- `convert_assignments`: Boolean - if true, distributes existing assignments to new tahapan

**Response (Success)**:
```json
{
  "ok": true,
  "message": "Generated 11 weekly tahapan and converted assignments",
  "mode": "weekly",
  "tahapan_count": 11,
  "converted_assignments": 45
}
```

**Response (Error)**:
```json
{
  "ok": false,
  "error": "Invalid mode. Must be one of: daily, weekly, monthly, custom"
}
```

**Backend Process**:

1. **Delete Old Auto-Generated Tahapan**:
   - Deletes all tahapan with `is_auto_generated=True`
   - Preserves custom (user-created) tahapan

2. **Generate New Tahapan**:
   - **Daily**: One tahapan per day from project start to end
   - **Weekly**: One tahapan per week (week boundary based on `week_end_day`)
   - **Monthly**: One tahapan per month
   - **Custom**: No generation, keeps existing custom tahapan only

3. **Assignment Conversion** (if `convert_assignments=True`):
   - Reads old assignments before deletion
   - Distributes proportions to new tahapan using daily distribution algorithm
   - Preserves total proportion per pekerjaan (±0.5% tolerance)

**Daily Distribution Algorithm**:
```
For each pekerjaan:
  1. Calculate total volume assigned: V_total = sum(old_assignments.proporsi)
  2. Get old tahapan date ranges: [(start1, end1), (start2, end2), ...]
  3. Create daily distribution:
     - For each day in old_tahapan: daily_vol[date] += proporsi
  4. Map daily volumes to new tahapan:
     - For each new_tahapan:
         new_proporsi = sum(daily_vol[date] for date in new_tahapan.date_range)
  5. Create new assignments with calculated proportions
```

**Notes**:
- Conversion is LOSSY if switching from finer to coarser granularity (daily → weekly → monthly)
- Conversion is EXACT if switching from coarser to finer granularity (monthly → weekly → daily)
- Total proportions are preserved within ±0.5% rounding error

---

## Volume Data

### 8. List Volume Pekerjaan

**Endpoint**: `GET /api/project/<project_id>/volume-pekerjaan/list/`

**File**: `views_api.py:api_list_volume_pekerjaan`

Returns volume data for all pekerjaan.

**Response**:
```json
{
  "ok": true,
  "volumes": [
    {
      "pekerjaan_id": 322,
      "volume": 45.50,
      "satuan": "m³"
    },
    {
      "pekerjaan_id": 324,
      "volume": 120.00,
      "satuan": "m²"
    }
  ]
}
```

**Uses**:
- Used by frontend to calculate volume values (when displayMode = 'volume')
- Formula: `volume_value = (pekerjaan.volume * proporsi) / 100`

---

## Summary & Reporting

### 9. Validate All Assignments

**Endpoint**: `GET /api/project/<project_id>/tahapan/validate/`

**File**: `views_api_tahapan.py:api_validate_all_assignments`

Validates that all pekerjaan have complete assignments (total proporsi = 100%).

**Response**:
```json
{
  "ok": true,
  "valid": false,
  "issues": [
    {
      "pekerjaan_id": 330,
      "pekerjaan_nama": "Galian Tanah",
      "total_proporsi": 75.50,
      "missing": 24.50
    },
    {
      "pekerjaan_id": 332,
      "pekerjaan_nama": "Urugan Pasir",
      "total_proporsi": 110.00,
      "excess": 10.00
    }
  ],
  "valid_count": 18,
  "invalid_count": 2
}
```

**Use Cases**:
- Data validation before generating reports
- Identifying incomplete schedules

---

### 10. Get Unassigned Pekerjaan

**Endpoint**: `GET /api/project/<project_id>/tahapan/unassigned/`

**File**: `views_api_tahapan.py:api_get_unassigned_pekerjaan`

Returns list of pekerjaan with no assignments or incomplete assignments (total < 100%).

**Response**:
```json
{
  "ok": true,
  "unassigned": [
    {
      "pekerjaan_id": 330,
      "kode_pekerjaan": "1.1.02",
      "uraian": "Galian Tanah",
      "volume": 50.00,
      "satuan": "m³",
      "total_assigned": 0.00,
      "remaining": 100.00
    },
    {
      "pekerjaan_id": 332,
      "kode_pekerjaan": "1.1.03",
      "uraian": "Urugan Pasir",
      "volume": 30.00,
      "satuan": "m³",
      "total_assigned": 75.50,
      "remaining": 24.50
    }
  ],
  "count": 2
}
```

**Uses**:
- Identifying work items that need scheduling
- Data completeness reporting

---

### 11. Get Rekap Kebutuhan Enhanced

**Endpoint**: `GET /api/project/<project_id>/rekap-kebutuhan-enhanced/`

**File**: `views_api_tahapan.py:api_get_rekap_kebutuhan_enhanced`

Returns material/labor requirements broken down by tahapan.

**Response**:
```json
{
  "ok": true,
  "data": [
    {
      "tahapan_id": 855,
      "tahapan_nama": "Week 1: 26 Oct - 27 Oct",
      "tanggal_mulai": "2025-10-26",
      "tanggal_selesai": "2025-10-27",
      "items": [
        {
          "kode": "U.0001",
          "uraian": "Pasir Beton",
          "satuan": "m³",
          "quantity": 12.50,
          "harga_satuan": 150000.00,
          "jumlah_harga": 1875000.00
        },
        {
          "kode": "T.0001",
          "uraian": "Pekerja",
          "satuan": "OH",
          "quantity": 8.00,
          "harga_satuan": 100000.00,
          "jumlah_harga": 800000.00
        }
      ],
      "total_biaya": 2675000.00
    }
  ],
  "grand_total": 25450000.00
}
```

**Uses**:
- Material procurement planning
- Labor scheduling
- Cost analysis per tahapan
- S-Curve data generation

---

## Error Handling

### Standard Error Response Format

All endpoints return errors in this format:

```json
{
  "ok": false,
  "error": "Error message describing what went wrong"
}
```

### HTTP Status Codes

- **200 OK**: Successful GET request
- **201 Created**: Successful POST creation
- **400 Bad Request**: Validation error or invalid input
- **403 Forbidden**: User is not project owner
- **404 Not Found**: Project or resource not found
- **405 Method Not Allowed**: Wrong HTTP method used
- **500 Internal Server Error**: Server-side error

### Common Error Messages

| Error Message | Cause | Solution |
|--------------|-------|----------|
| "Project not found" | User is not owner or project doesn't exist | Check project_id and ownership |
| "Nama tahapan harus diisi" | Empty nama field in POST | Provide valid nama |
| "Tahapan dengan nama X sudah ada" | Duplicate nama | Use unique nama |
| "Invalid mode. Must be one of: daily, weekly, monthly, custom" | Invalid mode parameter | Use valid mode value |
| "Proporsi must be between 0.01 and 100.00" | Invalid proporsi value | Provide valid percentage |
| "Pekerjaan not found or doesn't belong to this project" | Invalid pekerjaan_id | Check pekerjaan exists in project |

---

## Frontend Integration

### CSRF Protection

All POST/PUT/DELETE requests require CSRF token in headers:

```javascript
headers: {
  'X-CSRFToken': getCookie('csrftoken'),
  'Content-Type': 'application/json'
}
```

### Example: Save Assignments

```javascript
// Group changes by pekerjaan
const changesByPekerjaan = new Map();
state.modifiedCells.forEach((value, key) => {
  const [pekerjaanId, colId] = parseCellKey(key);
  const column = state.timeColumns.find(c => c.id === colId);

  if (!changesByPekerjaan.has(pekerjaanId)) {
    changesByPekerjaan.set(pekerjaanId, {});
  }

  changesByPekerjaan.get(pekerjaanId)[column.tahapanId] = value;
});

// Save each pekerjaan
for (const [pekerjaanId, assignments] of changesByPekerjaan.entries()) {
  const tahapanIds = Object.keys(assignments);

  // Assign non-zero proportions
  const toAssign = tahapanIds
    .filter(tid => parseFloat(assignments[tid]) > 0)
    .map(tid => ({
      pekerjaan_id: parseInt(pekerjaanId),
      proporsi: parseFloat(assignments[tid])
    }));

  // Unassign zero proportions
  const toUnassign = tahapanIds
    .filter(tid => parseFloat(assignments[tid]) === 0)
    .map(tid => parseInt(tid));

  // Call assign API for each tahapan
  for (const assignment of toAssign) {
    await apiCall(
      `/detail_project/api/project/${projectId}/tahapan/${assignment.tahapan_id}/assign/`,
      {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          assignments: [{
            pekerjaan_id: pekerjaanId,
            proporsi: assignment.proporsi
          }]
        })
      }
    );
  }

  // Call unassign API
  for (const tahapanId of toUnassign) {
    await apiCall(
      `/detail_project/api/project/${projectId}/tahapan/${tahapanId}/unassign/`,
      {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          pekerjaan_ids: [parseInt(pekerjaanId)]
        })
      }
    );
  }
}
```

---

## API Rate Limiting

**Currently**: No rate limiting implemented

**Recommendation**: For production:
- Implement rate limiting per user (e.g., 100 requests/minute)
- Add request throttling for expensive operations (regenerate-tahapan)
- Use Django Rest Framework's throttling classes

---

## Testing

### Running API Tests

```bash
# Run all tahapan API tests
pytest detail_project/tests/test_api_tahapan.py -v

# Run specific test
pytest detail_project/tests/test_api_tahapan.py::test_regenerate_weekly -v

# Run with coverage
pytest detail_project/tests/test_api_tahapan.py --cov=detail_project.views_api_tahapan
```

### Example Test Case

```python
def test_assign_pekerjaan_to_tahapan(client_logged, project, pekerjaan, tahapan):
    url = f'/detail_project/api/project/{project.id}/tahapan/{tahapan.id}/assign/'

    response = client_logged.post(
        url,
        data=json.dumps({
            'assignments': [
                {'pekerjaan_id': pekerjaan.id, 'proporsi': 50.0}
            ]
        }),
        content_type='application/json'
    )

    assert response.status_code == 200
    data = response.json()
    assert data['ok'] == True
    assert len(data['assignments']) == 1
    assert data['assignments'][0]['proporsi'] == 50.0
```

---

## Changelog

### Version 1.0 (2025-10-26)

- Initial API documentation
- Added `is_auto_generated` and `generation_mode` fields to tahapan serialization
- Implemented assignment conversion during mode switching
- Enhanced error handling and validation

---

**Document Version**: 1.0
**Last Updated**: 26 Oktober 2025
**Maintained By**: Development Team
