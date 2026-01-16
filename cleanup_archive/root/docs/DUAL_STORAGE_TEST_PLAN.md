# 🧪 Dual Storage Test Plan - 3 Scenarios

**Created**: 2025-11-09
**Purpose**: Validate dual storage implementation for REF/REF_MODIFIED/CUSTOM pekerjaan
**Test Framework**: pytest + pytest-django

---

## 📋 Test Scenarios Overview

| Scenario | Source Type | Expected Behavior |
|----------|-------------|-------------------|
| **1. REF** | Referensi (read-only) | Items from AHSPReferensi → DetailAHSPProject → DetailAHSPExpanded → Harga Items |
| **2. REF_MODIFIED** | Referensi Modified (editable) | Same as REF + user can edit |
| **3. CUSTOM** | Custom with Bundle | Bundle (LAIN) → Expand to components → Harga Items shows components only |

---

## 🎯 Test Case 1: REF - Pekerjaan Referensi

### **Setup**
```python
# Given: AHSP Referensi exists in database
ahsp_ref = AHSPReferensi.objects.create(
    kode_ahsp='1.1.4.1',
    nama_ahsp='Pekerjaan Beton f\'c 15 MPa',
    satuan='m3'
)

# With rincian (components)
RincianReferensi.objects.create(ahsp=ahsp_ref, kategori='TK', kode_item='L.01', uraian_item='Pekerja', satuan_item='OH', koefisien=0.66)
RincianReferensi.objects.create(ahsp=ahsp_ref, kategori='BHN', kode_item='C.01', uraian_item='Semen', satuan_item='kg', koefisien=326)
RincianReferensi.objects.create(ahsp=ahsp_ref, kategori='BHN', kode_item='D.01', uraian_item='Pasir', satuan_item='m3', koefisien=0.52)
```

### **Action**
```python
# When: User creates pekerjaan from referensi
pekerjaan = clone_ref_pekerjaan(
    project=project,
    sub=sub_klasifikasi,
    ref_obj=ahsp_ref,
    source_type='ref',
    ordering_index=1,
    auto_load_rincian=True
)
```

### **Expected Results**

#### ✅ **DetailAHSPProject (Storage 1 - Raw)**
```python
assert DetailAHSPProject.objects.filter(project=project, pekerjaan=pekerjaan).count() == 3
rows = DetailAHSPProject.objects.filter(project=project, pekerjaan=pekerjaan)
assert rows[0].kategori == 'TK'
assert rows[0].kode == 'L.01'
assert rows[0].koefisien == Decimal('0.66')
```

#### ✅ **DetailAHSPExpanded (Storage 2 - Expanded)**
```python
assert DetailAHSPExpanded.objects.filter(project=project, pekerjaan=pekerjaan).count() == 3
expanded = DetailAHSPExpanded.objects.filter(project=project, pekerjaan=pekerjaan)
assert expanded[0].kategori == 'TK'
assert expanded[0].kode == 'L.01'
assert expanded[0].koefisien == Decimal('0.66')
assert expanded[0].source_bundle_kode is None  # Direct input, not from bundle
assert expanded[0].expansion_depth == 0
```

#### ✅ **Harga Items API**
```python
response = client.get(f'/detail_project/api/project/{project.id}/harga-items/list/?canon=1')
assert response.status_code == 200
data = response.json()
assert data['ok'] == True
assert len(data['items']) == 3
assert data['items'][0]['kode_item'] == 'L.01'
```

#### ✅ **HargaItemProject Created**
```python
assert HargaItemProject.objects.filter(project=project, kode_item='L.01').exists()
assert HargaItemProject.objects.filter(project=project, kode_item='C.01').exists()
assert HargaItemProject.objects.filter(project=project, kode_item='D.01').exists()
```

---

## 🎯 Test Case 2: REF_MODIFIED - Pekerjaan Referensi Modified

### **Setup**
Same as Test Case 1

### **Action**
```python
# When: User creates pekerjaan from referensi with modified flag
pekerjaan = clone_ref_pekerjaan(
    project=project,
    sub=sub_klasifikasi,
    ref_obj=ahsp_ref,
    source_type='ref_modified',  # MODIFIED!
    ordering_index=1,
    auto_load_rincian=True,
    override_uraian='Modified Beton f\'c 25 MPa'  # Custom uraian
)
```

### **Expected Results**

#### ✅ **Pekerjaan Metadata**
```python
assert pekerjaan.source_type == 'ref_modified'
assert pekerjaan.snapshot_kode.startswith('mod.')  # e.g., mod.1-1.1.4.1
assert pekerjaan.snapshot_uraian == 'Modified Beton f\'c 25 MPa'
```

#### ✅ **DetailAHSPProject (Storage 1)**
Same as Test Case 1 - should have 3 rows

#### ✅ **DetailAHSPExpanded (Storage 2)**
Same as Test Case 1 - should have 3 expanded rows

#### ✅ **Harga Items API**
Same as Test Case 1 - should return 3 items

---

## 🎯 Test Case 3: CUSTOM - Pekerjaan Custom dengan Bundle

### **Setup - Create Bundle Pekerjaan First**
```python
# Given: Bundle pekerjaan exists
bundle_pekerjaan = Pekerjaan.objects.create(
    project=project,
    sub_klasifikasi=sub,
    source_type='custom',
    snapshot_kode='CUST-0001',
    snapshot_uraian='Bundle - 1 m2 Bekisting',
    satuan='m2'
)

# With components
DetailAHSPProject.objects.create(
    project=project, pekerjaan=bundle_pekerjaan,
    harga_item=hip_tk, kategori='TK', kode='L.01', uraian='Pekerja', satuan='OH', koefisien=Decimal('0.66')
)
DetailAHSPProject.objects.create(
    project=project, pekerjaan=bundle_pekerjaan,
    harga_item=hip_bhn1, kategori='BHN', kode='M.01', uraian='Kayu', satuan='m3', koefisien=Decimal('0.04')
)
DetailAHSPProject.objects.create(
    project=project, pekerjaan=bundle_pekerjaan,
    harga_item=hip_bhn2, kategori='BHN', kode='N.01', uraian='Paku', satuan='kg', koefisien=Decimal('0.40')
)

# CRITICAL: Populate expanded for bundle too!
_populate_expanded_from_raw(project, bundle_pekerjaan)
```

### **Action - Create Pekerjaan that Uses Bundle**
```python
# When: User creates custom pekerjaan with bundle reference
pekerjaan = Pekerjaan.objects.create(
    project=project,
    sub_klasifikasi=sub,
    source_type='custom',
    snapshot_kode='CUST-0002',
    snapshot_uraian='Pekerjaan Custom 1',
    satuan='m2'
)

# User adds LAIN item referencing bundle (via API save)
payload = {
    'rows': [
        {
            'kategori': 'LAIN',
            'kode': 'Bundle - 1 m2 Bekisting',
            'uraian': 'Pemasangan Bekisting',
            'satuan': 'm2',
            'koefisien': '10.0',
            'ref_pekerjaan_id': bundle_pekerjaan.id  # CRITICAL!
        }
    ]
}

response = client.post(
    f'/detail_project/api/project/{project.id}/detail-ahsp/{pekerjaan.id}/save/',
    data=json.dumps(payload),
    content_type='application/json'
)
```

### **Expected Results**

#### ✅ **API Response**
```python
assert response.status_code == 200
data = response.json()
assert data['ok'] == True
assert data['saved_raw_rows'] == 1  # 1 bundle item
assert data['saved_expanded_rows'] == 3  # 3 components (TK, BHN, BHN)
assert len(data['errors']) == 0
```

#### ✅ **DetailAHSPProject (Storage 1 - Raw)**
```python
# Should have 1 row (bundle item, NOT expanded)
assert DetailAHSPProject.objects.filter(project=project, pekerjaan=pekerjaan).count() == 1
bundle_row = DetailAHSPProject.objects.get(project=project, pekerjaan=pekerjaan)
assert bundle_row.kategori == 'LAIN'
assert bundle_row.ref_pekerjaan == bundle_pekerjaan
assert bundle_row.koefisien == Decimal('10.0')
```

#### ✅ **DetailAHSPExpanded (Storage 2 - Expanded)**
```python
# Should have 3 rows (expanded components)
assert DetailAHSPExpanded.objects.filter(project=project, pekerjaan=pekerjaan).count() == 3

expanded = DetailAHSPExpanded.objects.filter(project=project, pekerjaan=pekerjaan).order_by('kode')
assert expanded[0].kategori == 'TK'
assert expanded[0].kode == 'L.01'
assert expanded[0].koefisien == Decimal('6.60')  # 10 × 0.66
assert expanded[0].source_bundle_kode == 'Bundle - 1 m2 Bekisting'
assert expanded[0].expansion_depth == 1

assert expanded[1].kategori == 'BHN'
assert expanded[1].kode == 'M.01'
assert expanded[1].koefisien == Decimal('0.40')  # 10 × 0.04

assert expanded[2].kategori == 'BHN'
assert expanded[2].kode == 'N.01'
assert expanded[2].koefisien == Decimal('4.00')  # 10 × 0.40
```

#### ✅ **Harga Items API**
```python
response = client.get(f'/detail_project/api/project/{project.id}/harga-items/list/?canon=1')
data = response.json()

# Should return 3 items (expanded components), NOT bundle item
assert len(data['items']) == 3
kodes = [item['kode_item'] for item in data['items']]
assert 'L.01' in kodes  # Pekerja
assert 'M.01' in kodes  # Kayu
assert 'N.01' in kodes  # Paku
assert 'Bundle - 1 m2 Bekisting' not in kodes  # Bundle NOT in list!
```

---

## 🎯 Test Case 4: CRITICAL - Override Bug Fix Validation

### **Purpose**: Validate that multiple bundles with same component kode don't override

### **Setup**
```python
# Given: Two bundle pekerjaan with overlapping components
bundle_a = create_bundle_pekerjaan(
    kode='CUST-0001', uraian='Bundle A',
    components=[
        ('TK', 'TK.001', 'Pekerja', 'OH', 2.5),  # Same TK.001
        ('BHN', 'BHN.001', 'Bahan A', 'kg', 10.0),
    ]
)

bundle_b = create_bundle_pekerjaan(
    kode='CUST-0002', uraian='Bundle B',
    components=[
        ('TK', 'TK.001', 'Pekerja', 'OH', 3.0),  # Same TK.001 (overlap!)
        ('BHN', 'BHN.002', 'Bahan B', 'kg', 5.0),
    ]
)
```

### **Action**
```python
# When: User adds BOTH bundles to same pekerjaan
pekerjaan = create_custom_pekerjaan('CUST-0003', 'Test Override')

payload = {
    'rows': [
        {
            'kategori': 'LAIN',
            'kode': 'Bundle A',
            'uraian': 'Bundle A',
            'satuan': 'ls',
            'koefisien': '2.0',  # Bundle A × 2.0
            'ref_pekerjaan_id': bundle_a.id
        },
        {
            'kategori': 'LAIN',
            'kode': 'Bundle B',
            'uraian': 'Bundle B',
            'satuan': 'ls',
            'koefisien': '1.5',  # Bundle B × 1.5
            'ref_pekerjaan_id': bundle_b.id
        }
    ]
}

response = save_detail_ahsp(project, pekerjaan, payload)
```

### **Expected Results - NO OVERRIDE!**

#### ✅ **DetailAHSPExpanded - Multiple Rows with Same Kode**
```python
# Should have 4 rows (2 from Bundle A + 2 from Bundle B)
assert DetailAHSPExpanded.objects.filter(project=project, pekerjaan=pekerjaan).count() == 4

# Bundle A components
tk_from_a = DetailAHSPExpanded.objects.get(
    project=project, pekerjaan=pekerjaan,
    kode='TK.001', source_bundle_kode='Bundle A'
)
assert tk_from_a.koefisien == Decimal('5.0')  # 2.0 × 2.5

bhn_from_a = DetailAHSPExpanded.objects.get(
    project=project, pekerjaan=pekerjaan,
    kode='BHN.001', source_bundle_kode='Bundle A'
)
assert bhn_from_a.koefisien == Decimal('20.0')  # 2.0 × 10.0

# Bundle B components
tk_from_b = DetailAHSPExpanded.objects.get(
    project=project, pekerjaan=pekerjaan,
    kode='TK.001', source_bundle_kode='Bundle B'
)
assert tk_from_b.koefisien == Decimal('4.5')  # 1.5 × 3.0

bhn_from_b = DetailAHSPExpanded.objects.get(
    project=project, pekerjaan=pekerjaan,
    kode='BHN.002', source_bundle_kode='Bundle B'
)
assert bhn_from_b.koefisien == Decimal('7.5')  # 1.5 × 5.0

# CRITICAL: Both TK.001 rows exist (NO OVERRIDE!)
assert DetailAHSPExpanded.objects.filter(
    project=project, pekerjaan=pekerjaan, kode='TK.001'
).count() == 2  # Both preserved!
```

#### ✅ **Rekap Computation - Aggregates Both TK.001**
```python
# When computing rekap kebutuhan
rekap = compute_kebutuhan_items(project, [pekerjaan.id])

# TK.001 should aggregate from BOTH bundles
tk_rekap = next(r for r in rekap if r['kode'] == 'TK.001')
assert tk_rekap['qty'] == Decimal('9.5')  # 5.0 + 4.5 (NOT just 4.5!)
```

---

## 🔧 Test Execution

### **Run All Tests**
```bash
# From project root
pytest detail_project/tests/test_dual_storage.py -v

# Run specific test
pytest detail_project/tests/test_dual_storage.py::test_ref_pekerjaan_dual_storage -v

# Run with logging
pytest detail_project/tests/test_dual_storage.py -v -s
```

### **Expected Output (All Pass)**
```
test_dual_storage.py::test_ref_pekerjaan_dual_storage PASSED
test_dual_storage.py::test_ref_modified_pekerjaan_dual_storage PASSED
test_dual_storage.py::test_custom_bundle_dual_storage PASSED
test_dual_storage.py::test_override_bug_fixed PASSED

==================== 4 passed in 2.34s ====================
```

---

## 📊 Coverage Matrix

| Test Case | Storage 1 | Storage 2 | Harga Items API | Override Fix |
|-----------|-----------|-----------|-----------------|--------------|
| REF | ✅ | ✅ | ✅ | N/A |
| REF_MODIFIED | ✅ | ✅ | ✅ | N/A |
| CUSTOM Bundle | ✅ | ✅ | ✅ | N/A |
| Override Bug | ✅ | ✅ | ✅ | ✅ |

---

## 🎯 Success Criteria

All tests must pass with:
- ✅ DetailAHSPProject populated correctly (raw input)
- ✅ DetailAHSPExpanded populated correctly (expanded components)
- ✅ Harga Items API returns expected items
- ✅ No override conflict (multiple bundles with same kode)
- ✅ Koefisien multiplication correct (hierarchical)
- ✅ source_bundle_kode tracked correctly
- ✅ expansion_depth tracked correctly

**Status**: Ready for implementation
