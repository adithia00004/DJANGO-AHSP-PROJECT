# ISSUE: Bundle Harga Satuan Tidak Konsisten Saat Koef Bundle Diubah

## PROBLEM DESCRIPTION

**Reported by User:**
> "Saya masalah muncul ketika mengganti koef bundle, nilai yang dihasilkan oleh kolom harga satuan menjadi tidak konsisten dan selaras dengan koefisien bundle yang saya ganti"

**Symptoms:**
1. User mengubah koefisien bundle (e.g., dari 2.0 → 3.0)
2. Kolom "Harga Satuan" menampilkan nilai yang tidak sesuai
3. Division `bundle_total / koef_bundle` menggunakan koef lama

---

## ROOT CAUSE ANALYSIS

### Current Flow (PROBLEM):

```
1. USER CHANGES BUNDLE KOEF
   DetailAHSPProject: koef = 2.0 → 3.0

2. SAVE API TRIGGERED
   views_api.py:api_save_detail_ahsp_for_pekerjaan()

3. ✅ EXPANSION HAPPENS (lines 1827-1920)
   - Delete old DetailAHSPExpanded for this bundle
   - Create new DetailAHSPExpanded with NEW koef
   - expanded_koef = component.koef × 3.0 (CORRECT)

4. ✅ BUNDLE TOTAL CALCULATED (views_api.py:1335-1338)
   - bundle_total = Σ(expanded_koef × harga)
   - Uses NEW expanded components (CORRECT)

5. ❌ DIVISION USES WRONG KOEF (views_api.py:1374)
   koef_decimal = it.get("koefisien")  # ← FROM QUERY, NOT FROM DB!
```

---

## THE BUG: Query Timing Issue

### Code Analysis (views_api.py:1288-1325):

```python
# Line 1288-1304: Query DetailAHSPProject
raw_details = (DetailAHSPProject.objects
               .filter(project=project, pekerjaan=pkj)
               .values(
                   "id", "kategori", "kode", "uraian", "satuan", "koefisien",  # ← koefisien queried
                   "ref_pekerjaan_id", "ref_ahsp_id",
                   "harga_item__harga_satuan"
               )
               .order_by('kategori', 'kode'))

# Line 1326-1338: Query DetailAHSPExpanded (for bundle_total)
expanded_qs = (DetailAHSPExpanded.objects
               .filter(project=project, pekerjaan=pkj, source_detail_id__in=detail_ids)
               .select_related('harga_item'))

# Line 1341-1376: Process each item
for it in raw_details:
    koef_decimal = it.get("koefisien") or Decimal("0")  # ← FROM VALUES() QUERY
    bundle_total = expanded_totals.get(it.get("id"), Decimal("0"))

    # Line 1374: DIVISION
    if koef_decimal > Decimal("0"):
        effective_price = bundle_total / koef_decimal  # ← USES QUERIED KOEF
```

---

### Scenario: Bundle Koef Changed in Same Request

**Initial State:**
```
DetailAHSPProject:
  - id: 123
  - koef: 2.0
  - ref_pekerjaan_id: 42

DetailAHSPExpanded (old):
  - Component A: koef = 0.018 × 2.0 = 0.036, harga = 65,000 → 2,340
  - Component B: koef = 0.039 × 2.0 = 0.078, harga = 65,000 → 5,070
  - bundle_total = 7,410
```

**User Changes Koef to 3.0:**

**SAVE API Flow:**
```
1. Save API receives: koef = 3.0

2. DetailAHSPProject UPDATED:
   UPDATE detail_ahsp SET koefisien = 3.0 WHERE id = 123

3. DELETE old DetailAHSPExpanded:
   DELETE FROM detail_ahsp_expanded WHERE source_detail_id = 123

4. CREATE new DetailAHSPExpanded:
   Component A: koef = 0.018 × 3.0 = 0.054
   Component B: koef = 0.039 × 3.0 = 0.117
   bundle_total = 0.054×65k + 0.117×65k = 11,115

5. API GET (immediately after save):
   a. Query DetailAHSPProject:
      koef_decimal = 3.0 ✅ (from DB)

   b. Query DetailAHSPExpanded:
      bundle_total = 11,115 ✅ (from DB)

   c. Division:
      effective_price = 11,115 / 3.0 = 3,705 ✅ CORRECT!
```

**This should work!** 🤔

---

## WAIT - Let Me Re-Check the Flow...

Actually, if save API is called **separately** from get API:

```
REQUEST 1: POST /api/save-detail-ahsp/
  - Saves koef = 3.0
  - Re-expands DetailAHSPExpanded
  - Returns {ok: true}

REQUEST 2: GET /api/detail-ahsp/{pekerjaan_id}/
  - Queries DetailAHSPProject (koef = 3.0) ✅
  - Queries DetailAHSPExpanded (bundle_total = 11,115) ✅
  - Divides: 11,115 / 3.0 = 3,705 ✅
```

**This should also work!** 🤔

---

## HYPOTHESIS 1: Cache Issue?

**Check:** `views_api.py:1289`

```python
def api_get_detail_ahsp(request: HttpRequest, project_id: int, pekerjaan_id: int):
    # No caching decorator visible...
```

**No caching in GET API.** ✅

---

## HYPOTHESIS 2: Transaction Isolation?

**Check:** Save API uses `@transaction.atomic`

If frontend queries **BEFORE** save transaction commits:
```
T1: Save API (in transaction)
  - UPDATE DetailAHSPProject SET koef = 3.0
  - DELETE old DetailAHSPExpanded
  - INSERT new DetailAHSPExpanded
  - (not committed yet)

T2: Get API (concurrent request)
  - Query DetailAHSPProject → koef = 2.0 (old, uncommitted)
  - Query DetailAHSPExpanded → bundle_total = 7,410 (old)
  - Division: 7,410 / 2.0 = 3,705
```

**But wait...** Frontend should wait for save response before fetching!

---

## HYPOTHESIS 3: Frontend Not Refreshing After Save?

**Most Likely Cause:**

Frontend saves bundle koef change, but:
1. ❌ Doesn't wait for save response
2. ❌ Doesn't re-fetch detail AHSP after save
3. ❌ Uses stale cached data

**Solution:** Frontend must re-fetch detail after successful save!

---

## HYPOTHESIS 4: Division Using Stale Koef from Frontend State?

**Check:** Where does division happen?

**Backend:** `views_api.py:1374`
```python
effective_price = bundle_total / koef_decimal
```

where `koef_decimal` comes from:
```python
koef_decimal = it.get("koefisien")  # From DB query ✅
```

**So backend is correct!** ✅

**Frontend:** `rincian_ahsp.js:812`
```javascript
const jm = kf * hr;
```

where:
```javascript
const kf = num(it.koefisien);  // From API response
const hr = num(it.harga_satuan);  // From API response
```

**So frontend is also correct!** ✅

---

## ACTUAL ROOT CAUSE (FOUND!)

After re-reading user's report: **"nilai yang dihasilkan oleh kolom harga satuan menjadi tidak konsisten"**

**AHA!** The issue is:

When user **EDITS koef in the UI** (e.g., inline edit or modal):
1. Koef changes from 2.0 → 3.0
2. Frontend updates local state
3. Frontend re-calculates `jumlah = koef × harga_satuan`
4. **BUT** `harga_satuan` is STILL using OLD bundle_total / OLD koef!

**Example:**

**Before Edit:**
```
koef: 2.0
bundle_total (backend): 7,410
harga_satuan (API): 7,410 / 2.0 = 3,705
jumlah (display): 2.0 × 3,705 = 7,410 ✅
```

**User Edits Koef to 3.0 (in UI, before save):**
```
koef: 3.0 (NEW, frontend state)
bundle_total (backend): 7,410 (OLD, not re-expanded yet!)
harga_satuan (API): 7,410 / 2.0 = 3,705 (STALE! Still using old koef)
jumlah (display): 3.0 × 3,705 = 11,115 ❌ WRONG!
```

**Expected After Edit:**
```
koef: 3.0
bundle_total (backend): 11,115 (should re-expand)
harga_satuan (API): 11,115 / 3.0 = 3,705
jumlah (display): 3.0 × 3,705 = 11,115 ✅
```

---

## THE REAL PROBLEM: Reactive Calculation Without Re-Expansion

**Issue:** Frontend shows **live calculation** when koef changes, but:
1. `bundle_total` is NOT re-calculated (needs backend expansion)
2. `harga_satuan` still uses OLD bundle_total / OLD koef
3. `jumlah` uses NEW koef × OLD harga_satuan → **INCONSISTENT!**

---

## SOLUTION OPTIONS

### OPTION 1: Disable Live Calculation for Bundles ⭐ (Recommended)

**Implementation:**

When user edits bundle koef in frontend:
1. Show koef as editable (user can type)
2. Show harga_satuan as **grayed out / disabled** with tooltip:
   > "Bundle harga satuan akan dihitung ulang setelah save"
3. Show jumlah as **grayed out / disabled** with same tooltip
4. After save → re-fetch → display correct values

**Pros:**
- ✅ No misleading values during edit
- ✅ Clear UX (user knows it needs save)
- ✅ No backend changes needed

**Cons:**
- ⚠️ User can't preview jumlah before save

---

### OPTION 2: Optimistic Update with Warning

Show calculated value with warning indicator:

```
Koefisien: [3.0] ← editable
Harga Satuan: Rp 3,705 ⚠️ (belum final)
Jumlah Harga: Rp 11,115 ⚠️ (belum final)

Tooltip: "Nilai ini adalah estimasi. Simpan untuk mendapatkan nilai final."
```

**Pros:**
- ✅ User can preview
- ✅ Clear that it's temporary

**Cons:**
- ⚠️ Misleading if bundle components change
- ⚠️ Complex UI logic

---

### OPTION 3: Real-time Re-expansion API ❌ (Not Recommended)

Create API endpoint for "preview bundle koef change":

```
POST /api/project/{id}/pekerjaan/{id}/bundle-preview/
{
  "bundle_id": 123,
  "new_koef": 3.0
}

Response:
{
  "bundle_total": 11115,
  "harga_satuan": 3705,
  "jumlah": 11115
}
```

**Pros:**
- ✅ Accurate preview

**Cons:**
- ❌ Performance overhead (expansion on every koef change)
- ❌ Complex backend implementation
- ❌ Not worth it for edge case

---

## RECOMMENDED FIX: Option 1 (Disable Live Calc)

### Frontend Changes (rincian_ahsp.js)

**Detect if row is being edited:**

```javascript
// In renderDetailTable()
arr.forEach((it) => {
  const kf = num(it.koefisien);
  const hr = num(it.harga_satuan);
  const isBundle = sectionKategori === 'LAIN' && (it.ref_pekerjaan_id || it.ref_ahsp_id);

  // Check if this row is being edited (from state)
  const isEditing = editingRowId === it.id;

  let jm;
  let hargaCell;
  let jumlahCell;

  if (isBundle && isEditing) {
    // Bundle being edited - show placeholder values
    hargaCell = '<span class="text-muted" title="Akan dihitung ulang setelah save">-</span>';
    jumlahCell = '<span class="text-muted" title="Akan dihitung ulang setelah save">-</span>';
  } else {
    // Normal display
    jm = kf * hr;
    hargaCell = isBundle
      ? `<span class="text-info" title="Harga satuan bundle (total komponen ÷ koef bundle)">${fmt(hr)}</span>`
      : fmt(hr);
    jumlahCell = fmt(jm);
  }

  tr.innerHTML = `
    <td>${no++}</td>
    <td>${bundleIcon}${esc(it.uraian)}</td>
    <td>${esc(it.kode)}</td>
    <td>${esc(it.satuan)}</td>
    <td>${kf.toLocaleString(...)}</td>
    <td>${hargaCell}</td>
    <td>${jumlahCell}</td>
  `;
});
```

---

### Alternative: Show Last Saved Value

```javascript
if (isBundle && isEditing) {
  // Show ORIGINAL values (before edit) with note
  const originalKf = it._originalKoefisien || kf;
  const originalHr = it._originalHargaSatuan || hr;
  const originalJm = originalKf * originalHr;

  hargaCell = `<span class="text-muted">${fmt(originalHr)} <small>(nilai lama)</small></span>`;
  jumlahCell = `<span class="text-muted">${fmt(originalJm)} <small>(nilai lama)</small></span>`;
}
```

---

## TESTING CHECKLIST

After implementing fix:

- [ ] **Test 1:** Edit bundle koef (2.0 → 3.0)
  - [ ] Harga Satuan shows placeholder or old value (grayed)
  - [ ] Jumlah Harga shows placeholder or old value (grayed)
  - [ ] No misleading calculated values

- [ ] **Test 2:** Save after edit
  - [ ] API re-expands bundle with new koef
  - [ ] Frontend re-fetches detail
  - [ ] Harga Satuan = bundle_total / 3.0 (correct)
  - [ ] Jumlah Harga = 3.0 × harga_satuan (correct)

- [ ] **Test 3:** Edit then cancel
  - [ ] Koef reverts to original
  - [ ] Harga Satuan and Jumlah restore to original

- [ ] **Test 4:** Edit non-bundle item koef
  - [ ] Live calculation works normally (not affected)

---

## DOCUMENTATION UPDATE

Update `BUNDLE_SYSTEM_ARCHITECTURE.md`:

**Section: UI/UX Considerations**

```markdown
### Bundle Koefisien Editing

When user edits bundle koefisien in the UI:

1. **Before Save:**
   - Koefisien field: Editable ✅
   - Harga Satuan: Disabled/Grayed (shows "-" or last saved value)
   - Jumlah Harga: Disabled/Grayed (shows "-" or last saved value)
   - Tooltip: "Bundle akan dihitung ulang setelah save"

2. **After Save:**
   - Backend re-expands bundle with new koef
   - API returns updated bundle_total
   - Frontend re-fetches and displays correct values

**Rationale:** Bundle harga satuan depends on expansion (backend process).
Live calculation would show inconsistent values because bundle_total is
not updated until save triggers re-expansion.
```

---

## SUMMARY

**Root Cause:** Frontend shows live-calculated values when bundle koef changes, but `harga_satuan` uses stale `bundle_total` (not re-expanded yet).

**Fix:** Disable live calculation for bundle rows during edit. Show placeholder or grayed-out values until save completes.

**Status:** Ready for implementation

**Files to Modify:**
1. `rincian_ahsp.js` - Add edit state detection and conditional rendering
2. `BUNDLE_SYSTEM_ARCHITECTURE.md` - Document UX behavior

**Estimated Effort:** 1-2 hours

---

## RESOLVED (2025-11-19)

### Final Fix

1. `DetailAHSPExpanded` menyimpan koef komponen **per 1 unit bundle** sehingga data mentah stabil walau koef bundle berubah. Lapisan agregasi (`compute_rekap_for_project`, `compute_kebutuhan_items`) mengalikan kembali dengan `DetailAHSPProject.koefisien`.
2. `api_get_detail_ahsp` mengirim `harga_satuan` per unit tanpa pembagian/multiplikasi tambahan; frontend mempertahankan rumus generik `jumlah = koef × harga`.
3. Full regression `pytest detail_project/tests/ -v` (473 pass, 1 skipped; coverage 71.91%) memastikan dual storage, cascade, dan halaman Rincian AHSP mengikuti perilaku baru (lihat `logs/phase5_test_run_20251119_full.md` dan `logs/phase5_test_run_20251119_1635.md`).

### Verification Checklist

- [x] `pytest detail_project/tests/test_bundle_quantity_semantic.py`
- [x] `pytest detail_project/tests/test_dual_storage.py -k bundle`
- [x] `pytest detail_project/tests/test_workflow_baseline.py -k cascade`
- [x] `pytest detail_project/tests/ -v` (Nov 19, 2025)
- [x] Manual check: edit koef bundle di Template/Rincian AHSP → `harga_satuan` tetap, `jumlah` mengikuti koef baru.

### Diagnostic Script

- `diagnose_bundle_koef_issue.py` diperbarui untuk:
  - Menunjukkan subtotal per-unit (`DetailAHSPExpanded`) dan jumlah akhir (`bundle.koefisien × subtotal`).
  - Menandai `NO_EXPANSION` atau `STALE_EXPANSION` jika timestamp tidak sinkron.
  - Memberi rekomendasi troubleshooting sesuai flow quantity semantic.
- Jalankan via `python manage.py shell --command="exec(open('diagnose_bundle_koef_issue.py').read())"` sebelum/ sesudah migrasi untuk memastikan data bundle sehat.
