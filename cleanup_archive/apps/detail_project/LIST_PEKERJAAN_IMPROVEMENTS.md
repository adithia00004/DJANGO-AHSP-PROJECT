# List Pekerjaan Improvements - Auto-populate, Cascade Delete, Search

## Overview

Three improvements implemented for List Pekerjaan page:
1. **Auto-populate kolom** saat user ganti sumber/ref_id
2. **Cascade delete** untuk SubKlasifikasi dan Klasifikasi
3. **Extended search scope** untuk searchbar

---

## 1. Auto-populate Kolom Saat Ganti Sumber/Ref_id

### Problem
User mengubah pekerjaan (ganti source_type atau ref_id), tapi kolom Referensi AHSP, Uraian Pekerjaan, dan Satuan tidak ter-update otomatis dari referensi baru.

### Solution

**Already implemented in `_adopt_tmp_into()` function** (detail_project/views_api.py:556-589)

When user changes ref_id or source_type, system automatically:

```python
def _adopt_tmp_into(pobj, tmp, s_obj, order: int):
    """Auto-populate from new reference."""
    # ... reset related data ...

    # Copy snapshot from tmp (which came from new reference)
    pobj.snapshot_kode = tmp.snapshot_kode      # ← Auto-populate kode AHSP
    pobj.snapshot_uraian = tmp.snapshot_uraian  # ← Auto-populate uraian
    pobj.snapshot_satuan = tmp.snapshot_satuan  # ← Auto-populate satuan
    pobj.ref_id = tmp.ref_id                    # ← Auto-populate ref_id

    pobj.save(update_fields=[...])
```

**What happens:**
1. User changes ref_id from 10 → 20
2. System calls `clone_ref_pekerjaan()` with ref_id=20
3. Creates temp pekerjaan with data from AHSP #20:
   - snapshot_kode: from AHSP #20
   - snapshot_uraian: from AHSP #20
   - snapshot_satuan: from AHSP #20
4. `_adopt_tmp_into()` copies all snapshot fields to original pekerjaan
5. **Result:** Kode, Uraian, Satuan automatically updated from new reference ✅

### Cascade Reset to Related Pages

**Also implemented in `_reset_pekerjaan_related_data()`** (detail_project/views_api.py:519-554)

When pekerjaan changes, ALL related data is reset:

```python
def _reset_pekerjaan_related_data(pobj):
    # 1. Reset Template AHSP
    DetailAHSPProject.objects.filter(...).delete()

    # 2. Reset Volume
    VolumePekerjaan.objects.filter(...).update(quantity=None, formula=None)

    # 3. Reset Jadwal
    PekerjaanTahapan.objects.filter(...).delete()

    # 4. Reset Formula State
    VolumeFormulaState.objects.filter(...).delete()

    # 5. Reset detail_ready flag
    pobj.detail_ready = False
```

**Pages affected by cascade reset:**
- ✅ **Template AHSP** - All detail items deleted
- ✅ **Volume Pekerjaan** - Volume reset to NULL
- ✅ **Jadwal** - Removed from all tahapan
- ✅ **Formula** - Formula state deleted
- ✅ **Rekap** - Recomputed with clean data (via cache invalidation)

### Example Scenario

**Before:**
- Pekerjaan A: ref_id=10, kode="1.1.1", uraian="Galian Tanah", satuan="m3"
- Volume: 100 m3
- Jadwal: Minggu 1-2

**User Action:** Change ref_id to 20 (AHSP "Timbunan Tanah")

**After (automatic):**
- Pekerjaan A: ref_id=20, kode="1.2.1", uraian="Timbunan Tanah", satuan="m3"  ✅ AUTO-POPULATED
- Volume: NULL (reset) ⚠️ User must re-enter
- Jadwal: Empty (reset) ⚠️ User must re-enter

---

## 2. Cascade Delete untuk SubKlasifikasi dan Klasifikasi

### Problem
User khawatir jika delete SubKlasifikasi atau Klasifikasi, pekerjaan di bawahnya tidak ikut terhapus atau data orphan terbentuk.

### Solution

**Already properly configured in Django models** (detail_project/models.py:30-76)

```python
class Klasifikasi(TimeStampedModel):
    project = models.ForeignKey(
        'dashboard.Project',
        on_delete=models.CASCADE,  # ← CASCADE DELETE
        related_name='klasifikasi_list'
    )
    # ...

class SubKlasifikasi(TimeStampedModel):
    project = models.ForeignKey(
        'dashboard.Project',
        on_delete=models.CASCADE,  # ← CASCADE DELETE
        related_name='subklasifikasi_list'
    )
    klasifikasi = models.ForeignKey(
        Klasifikasi,
        on_delete=models.CASCADE,  # ← CASCADE DELETE
        related_name='sub_list'
    )
    # ...

class Pekerjaan(TimeStampedModel):
    project = models.ForeignKey(
        'dashboard.Project',
        on_delete=models.CASCADE,  # ← CASCADE DELETE
        related_name='pekerjaan_list'
    )
    sub_klasifikasi = models.ForeignKey(
        SubKlasifikasi,
        on_delete=models.CASCADE,  # ← CASCADE DELETE
        related_name='pekerjaan_list'
    )
    # ...
```

### Cascade Chain

**When user deletes Klasifikasi:**
```
Delete Klasifikasi A
  ↓ CASCADE
Delete all SubKlasifikasi under A
  ↓ CASCADE
Delete all Pekerjaan under those SubKlasifikasi
  ↓ CASCADE (Django automatic)
Delete all related:
  - DetailAHSPProject (template AHSP)
  - VolumePekerjaan (volume)
  - PekerjaanTahapan (jadwal)
  - VolumeFormulaState (formula)
  - ... (all FK pointing to Pekerjaan with CASCADE)
```

**When user deletes SubKlasifikasi:**
```
Delete SubKlasifikasi B
  ↓ CASCADE
Delete all Pekerjaan under B
  ↓ CASCADE (Django automatic)
Delete all related data (same as above)
```

**When user deletes Pekerjaan directly:**
```
Delete Pekerjaan C
  ↓ CASCADE (Django automatic)
Delete all related data
```

### Testing

**Test 1: Delete Klasifikasi**
1. Create Klasifikasi "K1" with 2 SubKlasifikasi
2. Each SubKlasifikasi has 3 Pekerjaan
3. Fill volume, jadwal for all pekerjaan
4. Delete Klasifikasi "K1"
5. **Verify:**
   - All SubKlasifikasi deleted ✓
   - All 6 Pekerjaan deleted ✓
   - All volume records deleted ✓
   - All jadwal records deleted ✓
   - All detail AHSP deleted ✓

**Test 2: Delete SubKlasifikasi**
1. Create SubKlasifikasi "S1" with 5 Pekerjaan
2. Fill data for all pekerjaan
3. Delete SubKlasifikasi "S1"
4. **Verify:**
   - All 5 Pekerjaan deleted ✓
   - All related data deleted ✓
   - Klasifikasi remains (not deleted) ✓

**Test 3: Delete Pekerjaan**
1. Create Pekerjaan with volume, jadwal, detail AHSP
2. Delete Pekerjaan
3. **Verify:**
   - All related data deleted ✓
   - SubKlasifikasi remains ✓

### No Additional Implementation Needed

Django's `on_delete=models.CASCADE` automatically handles all cascade deletions.

**Confirmation:** ✅ Already properly configured, no code changes needed.

---

## 3. Extended Search Scope untuk Searchbar

### Problem
Searchbar di List Pekerjaan hanya mencari di nama klasifikasi/sub, tidak mencari di:
- Kode AHSP
- Nama referensi AHSP
- Uraian pekerjaan

User sulit menemukan pekerjaan jika tidak ingat nama klasifikasi.

### Solution

**Enhanced `api_get_list_pekerjaan_tree()` with search parameter** (detail_project/views_api.py:340-429)

```python
def api_get_list_pekerjaan_tree(request: HttpRequest, project_id: int):
    """
    Query params:
    - search (q): Filter pekerjaan by kode AHSP, referensi AHSP nama, atau uraian
    """
    # Get search query
    search_query = request.GET.get('search') or request.GET.get('q') or ''

    if search_query:
        # Search in 4 fields:
        p_qs = p_qs.filter(
            Q(snapshot_kode__icontains=search_query) |        # Kode AHSP
            Q(snapshot_uraian__icontains=search_query) |      # Uraian pekerjaan
            Q(ref__kode_ahsp__icontains=search_query) |       # Kode referensi AHSP
            Q(ref__nama_ahsp__icontains=search_query)         # Nama referensi AHSP
        )

        # Filter klasifikasi/sub to only show those with matching pekerjaan
        filtered_sub_ids = set(p_qs.values_list('sub_klasifikasi_id', flat=True))
        s_qs = s_qs.filter(id__in=filtered_sub_ids)

        filtered_klas_ids = set(s_qs.values_list('klasifikasi_id', flat=True))
        k_qs = k_qs.filter(id__in=filtered_klas_ids)
```

### Search Fields

| Field | Example | Location |
|-------|---------|----------|
| **snapshot_kode** | "1.1.1.a" | Pekerjaan.snapshot_kode |
| **snapshot_uraian** | "Galian Tanah Biasa" | Pekerjaan.snapshot_uraian |
| **ref__kode_ahsp** | "2.2.1.4.3" | AHSPReferensi.kode_ahsp (via FK) |
| **ref__nama_ahsp** | "1 m3 beton mutu rendah" | AHSPReferensi.nama_ahsp (via FK) |

### API Usage

**Without search:**
```
GET /api/project/1/list-pekerjaan/tree/
```

**With search:**
```
GET /api/project/1/list-pekerjaan/tree/?search=galian
GET /api/project/1/list-pekerjaan/tree/?q=2.2.1.4
GET /api/project/1/list-pekerjaan/tree/?search=beton mutu rendah
```

**Response includes search metadata:**
```json
{
  "ok": true,
  "klasifikasi": [...],
  "search_query": "galian",
  "match_count": 5
}
```

### Search Behavior

**Case-insensitive search:**
- "galian" matches "Galian", "GALIAN", "Galian Tanah"

**Partial match:**
- "beton" matches "1 m3 beton mutu rendah f'c 15 MPa"

**Multi-word search:**
- Search query: "beton mutu"
- Matches: "1 m3 beton mutu rendah" ✓
- Does not match: "beton" only (no "mutu") ✗

**Filtered tree structure:**
Only klasifikasi and subklasifikasi that contain matching pekerjaan are shown.

**Example:**
```
Search: "galian"

Before (all):
  Klasifikasi A
    Sub A.1
      - Pekerjaan: Galian Tanah
      - Pekerjaan: Timbunan Tanah
    Sub A.2
      - Pekerjaan: Urugan Pasir
  Klasifikasi B
    Sub B.1
      - Pekerjaan: Pekerjaan Beton

After search "galian":
  Klasifikasi A
    Sub A.1
      - Pekerjaan: Galian Tanah  ← Match
```

### Frontend Integration

**HTML searchbar:**
```html
<input
  type="text"
  id="searchbar"
  placeholder="Cari kode AHSP, referensi, atau uraian..."
>
```

**JavaScript:**
```javascript
// When user types in searchbar
$('#searchbar').on('input', function() {
    const query = $(this).val();

    // Call API with search parameter
    $.get(`/api/project/${projectId}/list-pekerjaan/tree/`, {
        search: query
    }, function(data) {
        // Update tree UI
        renderTree(data.klasifikasi);

        // Show match count
        if (data.search_query) {
            $('#match-count').text(`${data.match_count} pekerjaan ditemukan`);
        }
    });
});
```

### Performance

**Optimized with indexes:**
- `snapshot_kode` - indexed via CharField
- `snapshot_uraian` - TextField (full-text search possible)
- `ref__kode_ahsp` - indexed in AHSPReferensi table
- `ref__nama_ahsp` - indexed in AHSPReferensi table

**Query optimization:**
- Uses `icontains` (case-insensitive)
- Single database query for pekerjaan filter
- Two additional queries for subklasifikasi and klasifikasi filter
- Total: 3 queries (efficient)

---

## Summary

### ✅ Feature 1: Auto-populate
- **Status:** Already implemented
- **Location:** `_adopt_tmp_into()` in views_api.py
- **Behavior:** When ref_id changes, kode/uraian/satuan auto-update from new reference
- **Cascade:** All related data (volume, jadwal, template) automatically reset

### ✅ Feature 2: Cascade Delete
- **Status:** Already configured
- **Location:** Model ForeignKey definitions with `on_delete=CASCADE`
- **Behavior:**
  - Delete Klasifikasi → cascade to SubKlasifikasi → cascade to Pekerjaan → cascade to all related
  - Delete SubKlasifikasi → cascade to Pekerjaan → cascade to all related
  - Delete Pekerjaan → cascade to all related
- **No code changes needed:** Django handles automatically

### ✅ Feature 3: Extended Search
- **Status:** Newly implemented
- **Location:** `api_get_list_pekerjaan_tree()` in views_api.py:340-429
- **Search scope:**
  1. Kode AHSP (snapshot_kode)
  2. Uraian pekerjaan (snapshot_uraian)
  3. Kode referensi AHSP (ref__kode_ahsp)
  4. Nama referensi AHSP (ref__nama_ahsp)
- **API:** `GET /api/project/{id}/list-pekerjaan/tree/?search=query`
- **Response:** Filtered tree + search metadata (query, match_count)

---

## Testing Checklist

### Test Auto-populate:
- [ ] Change ref_id from A to B → verify kode/uraian/satuan updated
- [ ] Change source_type REF→CUSTOM → verify fields reset
- [ ] Change source_type CUSTOM→REF → verify fields populated from ref
- [ ] Verify volume reset after change
- [ ] Verify jadwal reset after change

### Test Cascade Delete:
- [ ] Delete Klasifikasi → verify all Sub and Pekerjaan deleted
- [ ] Delete SubKlasifikasi → verify all Pekerjaan deleted
- [ ] Delete Pekerjaan → verify all related data deleted
- [ ] Verify no orphan records in database

### Test Search:
- [ ] Search by kode AHSP ("1.1.1") → verify matching pekerjaan shown
- [ ] Search by uraian ("galian") → verify matching pekerjaan shown
- [ ] Search by referensi kode ("2.2.1.4") → verify matching pekerjaan shown
- [ ] Search by referensi nama ("beton mutu") → verify matching pekerjaan shown
- [ ] Search with no matches → verify empty tree returned
- [ ] Search case-insensitive ("GALIAN" = "galian") → verify works

---

## Files Modified

**detail_project/views_api.py:**
- `api_get_list_pekerjaan_tree()` (line 340-429): Added search functionality

**detail_project/models.py:**
- No changes (CASCADE already configured)

**detail_project/views_api.py:**
- `_reset_pekerjaan_related_data()` (line 519-554): Already implemented
- `_adopt_tmp_into()` (line 556-589): Already implements auto-populate

---

## API Changes

**New query parameter:**
```
GET /api/project/{project_id}/list-pekerjaan/tree/?search={query}
GET /api/project/{project_id}/list-pekerjaan/tree/?q={query}
```

**Response format (with search):**
```json
{
  "ok": true,
  "klasifikasi": [...],
  "search_query": "galian",  // NEW
  "match_count": 5           // NEW
}
```

**Backward compatible:** Works without search parameter (returns all).
