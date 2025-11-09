# 🗺️ PAGE-BY-PAGE TESTING ROADMAP WITH CODE REVIEW

**Purpose:** Manual testing dengan analisis mendalam untuk setiap page
**Approach:** Test → Analyze → Review → Recommend
**Timeline:** ~2 hours per page (20 hours total for 10 pages)

---

## 📋 WORKFLOW UNTUK SETIAP PAGE

### **Phase 1: Pre-Test Code Analysis (30 min)**
1. Identify all related files (views, templates, JS, CSS, models)
2. Review code structure and dependencies
3. Check for dead code / unused functions
4. Identify potential issues

### **Phase 2: Manual Testing (45 min)**
1. Execute test scenarios
2. Document bugs found
3. Note UI/UX issues
4. Test edge cases

### **Phase 3: Post-Test Code Review (30 min)**
1. Analyze findings in context of code
2. Identify cleanup opportunities
3. Propose improvements
4. List features to add/remove

### **Phase 4: Documentation & Action Items (15 min)**
1. Update findings document
2. Create cleanup checklist
3. Prioritize recommendations

---

# 📄 PAGE 1: LIST PEKERJAAN

**Priority:** 🔴 CRITICAL (Main CASCADE RESET feature)
**Estimated Time:** 2-3 hours
**Status:** ⏳ PENDING

---

## 1️⃣ PRE-TEST: CODE ANALYSIS

### Files to Analyze:

#### **Backend:**
```
detail_project/views.py
  └─ list_pekerjaan_view() [line ~XX]

detail_project/views_api.py
  ├─ api_save_list_pekerjaan() [line ~XX]
  ├─ api_get_list_pekerjaan_tree() [line ~XX]
  ├─ api_upsert_list_pekerjaan() [line 392+]
  ├─ _reset_pekerjaan_related_data() [line 564-596] ✅ CRITICAL
  ├─ _adopt_tmp_into() [line 598+]
  └─ clone_ref_pekerjaan()

detail_project/models.py
  ├─ Klasifikasi
  ├─ SubKlasifikasi
  ├─ Pekerjaan
  ├─ DetailAHSPProject
  ├─ VolumePekerjaan
  ├─ PekerjaanTahapan
  └─ VolumeFormulaState
```

#### **Frontend:**
```
detail_project/templates/detail_project/list_pekerjaan.html
detail_project/static/detail_project/js/list_pekerjaan.js
  ├─ syncFields() [line 795-813] ✅ CRITICAL (auto-reset)
  ├─ syncPreview()
  ├─ autoResize()
  └─ Form submission handlers
detail_project/static/detail_project/css/list_pekerjaan.css (if exists)
```

### Code Review Checklist:

**Before testing, check:**
- [ ] Are there duplicate functions?
- [ ] Is there commented-out code that should be removed?
- [ ] Are error messages user-friendly?
- [ ] Is validation comprehensive?
- [ ] Are there any console.log() statements left?
- [ ] Is there proper error handling?
- [ ] Are variable names clear?
- [ ] Is there proper documentation?

---

## 2️⃣ MANUAL TESTING SCENARIOS

### **Scenario 1.1: Basic CRUD Operations**

**Objective:** Test create, read, update, delete

**Test Steps:**
1. Create Klasifikasi "Pekerjaan Persiapan"
   - [ ] Created successfully
   - [ ] Appears in tree
   - [ ] ordering_index works

2. Create SubKlasifikasi "Mobilisasi"
   - [ ] Created under correct parent
   - [ ] Ordering works
   - [ ] Can expand/collapse

3. Create Pekerjaan CUSTOM
   - [ ] All fields editable
   - [ ] Kode auto-generated (CUST-XXX)
   - [ ] Uraian required
   - [ ] Satuan optional
   - [ ] Save successful

4. Edit Pekerjaan
   - [ ] Fields populated correctly
   - [ ] Can modify uraian
   - [ ] Can modify satuan
   - [ ] Save persists changes

5. Delete Pekerjaan
   - [ ] Confirmation shown (if implemented)
   - [ ] Deleted successfully
   - [ ] Removed from tree

6. Delete Klasifikasi (with children)
   - [ ] Cascade delete warning (if implemented)
   - [ ] All children deleted
   - [ ] Tree updated

**Notes/Bugs:**
```
[Document any issues found]
```

---

### **Scenario 1.2: CASCADE RESET - CUSTOM → REF**

**Objective:** Verify cascade reset works correctly

**Setup:**
```
Create CUSTOM pekerjaan:
- Uraian: "Pembuatan Kolom Praktis 12x12"
- Satuan: "unit"

Then add related data:
1. Volume: 50.000 (via Volume Pekerjaan page)
2. Template AHSP:
   - TK.CUSTOM (koef: 0.5)
   - BHN.CUSTOM (koef: 1.2)
3. Jadwal: Minggu 1 (100%) (via Jadwal page)
```

**Test Steps:**

**Step 1: Change Source Type**
1. Change dropdown: CUSTOM → REFERENSI
   - [ ] ✅ Uraian field auto-cleared immediately
   - [ ] ✅ Satuan field auto-cleared immediately
   - [ ] ✅ Ref dropdown enabled
   - [ ] ✅ Textarea resized after clear
   - [ ] ✅ Preview updated

**Step 2: Select Reference**
2. Select AHSP from dropdown: "TEST.001 - Test AHSP Balok"
   - [ ] Dropdown shows search results
   - [ ] Can select reference
   - [ ] ref_id populated

**Step 3: Save**
3. Click "Simpan" button
   - [ ] ✅ No Error 500
   - [ ] ✅ Success message shown
   - [ ] ✅ Page refreshes or updates
   - [ ] Check browser console for errors
     - [ ] No JavaScript errors
     - [ ] No network errors (check Network tab)

**Step 4: Verify CASCADE RESET**

4a. **Check Pekerjaan Still Exists**
   - Navigate to List Pekerjaan
   - [ ] ✅ Pekerjaan still in list (NOT deleted)
   - [ ] ✅ Source type = REF
   - [ ] ✅ Kode = "TEST.001" (from reference)
   - [ ] ✅ Uraian = "Test AHSP Balok" (from reference)
   - [ ] ✅ Satuan = "m3" (from reference)
   - [ ] ✅ ref_id = [ID of TEST.001]

4b. **Check Volume RESET**
   - Navigate to Volume Pekerjaan page
   - Find the pekerjaan
   - [ ] ✅ Volume = NULL or empty (was 50.000)
   - [ ] ✅ Formula cleared (if had formula)

4c. **Check Template AHSP REPLACED**
   - Navigate to Template AHSP page
   - Select the pekerjaan
   - [ ] ✅ Old items DELETED (TK.CUSTOM, BHN.CUSTOM)
   - [ ] ✅ New items LOADED from reference
   - [ ] ✅ Items are read-only (source=REF)
   - [ ] ✅ detail_ready flag = False or updated

4d. **Check Jadwal CLEARED**
   - Navigate to Jadwal Pekerjaan page
   - Find the pekerjaan
   - [ ] ✅ Tahapan assignment cleared (was Minggu 1 100%)
   - [ ] ✅ Pekerjaan shows as unassigned

4e. **Check Formula State CLEARED**
   - Check database or via Volume page
   - [ ] ✅ VolumeFormulaState record deleted

**Expected Result:** ✅ ALL CASCADE RESET VERIFIED

**Bugs Found:**
```
Bug ID:
Description:
Severity:
```

---

### **Scenario 1.3: CASCADE RESET - REF → CUSTOM**

**Setup:**
```
Use pekerjaan from Scenario 1.2 (now REF)
Add data again:
- Volume: 75.000
- Jadwal: Minggu 2 (50%), Minggu 3 (50%)
```

**Test Steps:**
1. Change source type: REF → CUSTOM
   - [ ] Fields NOT auto-cleared (expected behavior)
   - [ ] Uraian still shows reference value
   - [ ] Can edit uraian now (was read-only)

2. Modify uraian to: "Custom Kolom Modified"
   - [ ] Can type in uraian field
   - [ ] Preview updates

3. Click Save
   - [ ] No error
   - [ ] Saved successfully

4. Verify CASCADE RESET:
   - [ ] ref_id = NULL
   - [ ] Volume = NULL (reset)
   - [ ] Template AHSP = empty (all deleted)
   - [ ] Jadwal = empty
   - [ ] detail_ready = False

**Expected Result:** ✅ PASS

---

### **Scenario 1.4: CASCADE RESET - REF → REF (Change ref_id)**

**Setup:**
```
Create REF pekerjaan with ref_id = AHSP #1
Add volume, template, jadwal
```

**Test Steps:**
1. Keep source type = REF
2. Change ref dropdown to different AHSP (ref_id = AHSP #2)
3. Save

**Verify:**
- [ ] Old template from AHSP #1 DELETED
- [ ] New template from AHSP #2 LOADED
- [ ] Volume RESET
- [ ] Jadwal RESET
- [ ] Kode updated to AHSP #2 kode
- [ ] Uraian updated to AHSP #2 uraian

**Expected Result:** ✅ PASS

---

### **Scenario 1.5: Validation & Error Handling**

**Test Case 1.5.1: Missing ref_id when changing to REF**

**Steps:**
1. Edit CUSTOM pekerjaan
2. Change source type to REFERENSI
3. Do NOT select any AHSP from dropdown
4. Click Save

**Expected:**
- [ ] Clear error message shown
- [ ] Message: "Wajib diisi saat mengganti source type ke ref/ref_modified"
- [ ] HTTP Status: 207 or 400 (not 500)
- [ ] No data corrupted
- [ ] Can retry after fixing

**Actual:**
```
[Document what actually happens]
```

**Status:** ✅ PASS / 🔴 FAIL

---

**Test Case 1.5.2: Missing uraian for CUSTOM**

**Steps:**
1. Create new CUSTOM pekerjaan
2. Leave uraian empty
3. Save

**Expected:**
- [ ] Validation error
- [ ] Clear message
- [ ] Field highlighted

---

**Test Case 1.5.3: Duplicate kode**

**Steps:**
1. Try to create pekerjaan with existing kode
2. Save

**Expected:**
- [ ] Validation prevents
- [ ] Error message shown

---

### **Scenario 1.6: Search Functionality**

**Objective:** Test extended search (4 fields)

**Test Case 1.6.1: Search by kode**
1. Enter "TEST" in search box
2. Press Enter or click search
   - [ ] Tree filtered
   - [ ] Only matching pekerjaan shown
   - [ ] Parent klasifikasi/sub shown if child matches
   - [ ] Non-matching branches hidden

**Test Case 1.6.2: Search by uraian**
1. Enter "balok" (part of uraian)
   - [ ] Finds pekerjaan with "balok" in uraian
   - [ ] Case-insensitive

**Test Case 1.6.3: Search by AHSP ref kode**
1. Enter reference kode (e.g., "AHSP.001")
   - [ ] Finds pekerjaan using that reference
   - [ ] Works for REF and REF_MODIFIED

**Test Case 1.6.4: Search by AHSP ref nama**
1. Enter reference name
   - [ ] Finds matching pekerjaan
   - [ ] Shows correct results

**Test Case 1.6.5: Clear search**
1. Clear search box
2. Submit
   - [ ] All pekerjaan shown again
   - [ ] Tree restored to full view

---

### **Scenario 1.7: UI/UX Elements**

**Test Case 1.7.1: Dropdown not clipped**
- [ ] Select2 dropdown opens fully
- [ ] Not cut off by card-body
- [ ] Not cut off by sub-wrap
- [ ] Scrollable if many items

**Test Case 1.7.2: Textarea auto-resize**
1. Type long text in uraian
   - [ ] Textarea expands automatically
   - [ ] No scrollbar needed
   - [ ] Readable

**Test Case 1.7.3: Preview sync**
1. Edit uraian in edit mode
   - [ ] Preview cell updates immediately
   - [ ] Shows formatted text

**Test Case 1.7.4: Reordering (if implemented)**
1. Drag pekerjaan to reorder
   - [ ] Works smoothly
   - [ ] Order persists after save

---

### **Scenario 1.8: REF_MODIFIED Mode**

**Test Case 1.8.1: Create REF_MODIFIED**
1. Create pekerjaan with source = REF_MODIFIED
2. Select reference
3. Override uraian: "Modified Uraian"
4. Override satuan: "unit"
5. Save

**Verify:**
- [ ] Kode format: "mod.X-{kode_ref}"
- [ ] Uraian = custom override
- [ ] Satuan = custom override
- [ ] ref_id set correctly
- [ ] Template loaded from reference
- [ ] Can edit template koefisien

---

## 3️⃣ POST-TEST: CODE REVIEW & ANALYSIS

### **Review Findings:**

#### **What Works Well:**
```
[List positive findings]
Example:
- CASCADE RESET implementation is solid
- Error handling is comprehensive
- Frontend auto-reset works smoothly
```

#### **Issues Found:**
```
[List issues from testing]
Example:
Bug LP-001: Error 500 when...
Bug LP-002: No user warning...
```

#### **Code Smells / Technical Debt:**
```
[Note any code quality issues]
Example:
- Large function that should be split
- Duplicate code that could be refactored
- Complex logic that needs comments
- Performance concerns
```

---

## 4️⃣ CLEANUP RECOMMENDATIONS

### **Files/Functions to REMOVE:**

**Check for:**
```javascript
// In list_pekerjaan.js
- [ ] console.log() statements left in code
- [ ] Commented-out code blocks
- [ ] Unused event handlers
- [ ] Old function versions
```

**Candidates for removal:**
```
File: list_pekerjaan.js
Function: oldSyncFields() [if exists and unused]
Reason: Replaced by new syncFields()
Action: DELETE

File: views_api.py
Code: Commented validation block [line XXX]
Reason: Old validation, replaced by new
Action: DELETE
```

### **Code to REFACTOR:**

**Long functions:**
```
Function: api_upsert_list_pekerjaan() [line 392+]
Issue: 500+ lines, hard to maintain
Recommendation: Split into smaller functions:
  - validate_payload()
  - process_klasifikasi()
  - process_pekerjaan()
  - handle_source_change()
Priority: Medium
```

**Duplicate code:**
```
Lines: 710-730 and 815-832
Issue: Similar validation logic
Recommendation: Extract to _validate_source_change()
Priority: Low
```

### **Performance Issues:**

```
Issue: N+1 query problem in tree loading
Location: api_get_list_pekerjaan_tree()
Recommendation: Use select_related() and prefetch_related()
Priority: Medium
```

---

## 5️⃣ FEATURE GAPS & ADDITIONS

### **CRITICAL - Must Add:**

#### **1. User Warning Dialog**
```javascript
// BEFORE saving with source change
if (sourceTypeChanged && hasRelatedData) {
    const confirmed = confirm(
        "⚠️ PERHATIAN!\n\n" +
        "Mengubah tipe sumber akan menghapus:\n" +
        "• Volume Pekerjaan\n" +
        "• Jadwal (Tahapan)\n" +
        "• Template AHSP\n\n" +
        "Lanjutkan?"
    );
    if (!confirmed) return false;
}
```
**Priority:** 🔴 CRITICAL
**Effort:** 2 hours
**Impact:** Prevents accidental data loss

---

### **HIGH - Should Add:**

#### **2. Visual Indicators**
```html
<!-- Show badge if pekerjaan has data -->
<span class="badge badge-info" v-if="hasVolume">
    <i class="fa fa-database"></i> Vol
</span>
<span class="badge badge-success" v-if="hasJadwal">
    <i class="fa fa-calendar"></i> Jadwal
</span>
```
**Priority:** 🟡 HIGH
**Effort:** 3 hours
**Impact:** Better UX, clear visibility

---

#### **3. Undo Last Change**
```javascript
// Store state before cascade reset
const backup = {
    volume: currentVolume,
    jadwal: currentJadwal,
    template: currentTemplate,
    timestamp: Date.now()
};
localStorage.setItem('pekerjaan_backup_' + id, JSON.stringify(backup));

// Show "Undo" button for 5 minutes
if (canUndo) {
    showUndoButton();
}
```
**Priority:** 🟡 HIGH
**Effort:** 8 hours
**Impact:** Safety net for users

---

### **MEDIUM - Nice to Have:**

#### **4. Bulk Operations**
```
Feature: Select multiple pekerjaan and change source type
Use case: Changing 10 pekerjaan from CUSTOM to REF at once
Priority: 🟢 MEDIUM
Effort: 12 hours
```

#### **5. Import from Excel**
```
Feature: Import list pekerjaan from Excel file
Use case: Migrating from old system
Priority: 🟢 MEDIUM
Effort: 16 hours
```

---

### **LOW - Future:**

#### **6. Audit Trail**
```python
# Track all changes
class PekerjaanChangeLog(models.Model):
    pekerjaan = models.ForeignKey(Pekerjaan)
    user = models.ForeignKey(User)
    action = models.CharField()  # 'source_change', 'create', 'delete'
    old_value = models.JSONField()
    new_value = models.JSONField()
    timestamp = models.DateTimeField()
```
**Priority:** 🟢 LOW
**Effort:** 6 hours

---

## 6️⃣ DOCUMENTATION UPDATES NEEDED

Based on testing, update:

- [ ] SOURCE_CHANGE_CASCADE_RESET.md
  - Add user warning dialog section
  - Update screenshots
  - Add new edge cases found

- [ ] README.md (if exists)
  - Update feature list
  - Add troubleshooting section

- [ ] API documentation
  - Document error responses
  - Add examples

---

## 7️⃣ ACTION ITEMS SUMMARY

### **Immediate (Do Now):**
- [ ] Add user warning dialog (2 hours)
- [ ] Remove console.log statements (30 min)
- [ ] Remove commented code (30 min)
- [ ] Fix Bug LP-001 (if found) (1 hour)

### **Short-term (This Week):**
- [ ] Add visual indicators (3 hours)
- [ ] Refactor long functions (4 hours)
- [ ] Add inline documentation (2 hours)
- [ ] Performance optimization (3 hours)

### **Long-term (This Month):**
- [ ] Implement undo mechanism (8 hours)
- [ ] Add audit trail (6 hours)
- [ ] Bulk operations (12 hours)

---

## 8️⃣ TEST RESULTS TEMPLATE

**Page:** List Pekerjaan
**Test Date:** 2025-11-__
**Tester:** [Your Name]
**Duration:** ___ hours

### **Summary:**
- Test Scenarios: __ / __ PASS
- Bugs Found: __
- Features Needed: __
- Code Quality: ✅ Good / 🟡 Needs Work / 🔴 Poor

### **Detailed Results:**

| Scenario | Status | Notes |
|----------|--------|-------|
| Basic CRUD | ✅ PASS | All working |
| CASCADE RESET CUSTOM→REF | ✅ PASS | Perfect |
| CASCADE RESET REF→CUSTOM | ✅ PASS | - |
| CASCADE RESET REF→REF | ✅ PASS | - |
| Validation | 🔴 FAIL | Bug LP-001 |
| Search | ✅ PASS | All 4 fields work |
| UI/UX | 🟡 PASS* | Minor issues |
| REF_MODIFIED | ✅ PASS | - |

### **Bugs:**
1. LP-001: [Description]
2. LP-002: [Description]

### **Cleanup Needed:**
1. Remove 5 console.log statements
2. Delete commented code (lines 123-145)
3. Refactor api_upsert_list_pekerjaan()

### **Features to Add:**
1. 🔴 User warning dialog
2. 🟡 Visual indicators
3. 🟢 Undo mechanism

---

**Status:** ✅ TESTING COMPLETE
**Next Page:** Volume Pekerjaan

---
---

# 📄 PAGE 2: VOLUME PEKERJAAN

**Priority:** 🟡 HIGH
**Estimated Time:** 1.5 hours
**Status:** ⏳ PENDING

---

## 1️⃣ PRE-TEST: CODE ANALYSIS

### Files to Analyze:

#### **Backend:**
```
detail_project/views.py
  └─ volume_pekerjaan_view()

detail_project/views_api.py
  ├─ api_save_volume_pekerjaan()
  ├─ api_list_volume_pekerjaan()
  └─ api_volume_formula_state()

detail_project/models.py
  ├─ VolumePekerjaan
  │   └─ quantity (DecimalField, NOT NULL)
  └─ VolumeFormulaState
      ├─ raw (formula text)
      └─ is_fx (boolean)
```

#### **Frontend:**
```
detail_project/templates/detail_project/volume_pekerjaan.html
detail_project/static/detail_project/js/volume_pekerjaan.js
  ├─ Formula parser
  ├─ Number formatter (locale-aware)
  └─ Input handlers
```

### Code Review Questions:

- [ ] Is formula parser safe? (no eval() injection)
- [ ] Is decimal precision handled correctly? (3 decimal places)
- [ ] Is locale formatting working? (1.234,56 vs 1,234.56)
- [ ] Are there unused formula functions?
- [ ] Is validation comprehensive?

---

## 2️⃣ MANUAL TESTING SCENARIOS

### **Scenario 2.1: Basic Volume Input**

**Test Cases:**

**2.1.1: Input Decimal Volume**
1. Find pekerjaan "Test Pekerjaan 001"
2. Input: `123.456`
3. Save
   - [ ] Saved correctly
   - [ ] Display shows: "123.456" or "123,456" (check locale)
   - [ ] Database stores: 123.456 (3 decimal places)

**2.1.2: Input Integer Volume**
1. Input: `100`
2. Save
   - [ ] Saved as 100.000
   - [ ] Display correct

**2.1.3: Input with Thousands**
1. Input: `1234567.890`
2. Save
   - [ ] Saved correctly
   - [ ] Display formatted: "1.234.567,890" or "1,234,567.890"

**2.1.4: Edit Existing Volume**
1. Edit volume from 100.000 to 200.000
2. Save
   - [ ] Updated successfully
   - [ ] Old value replaced

**2.1.5: Clear Volume**
1. Clear volume field (make it empty)
2. Save
   - [ ] Record DELETED (because quantity is NOT NULL)
   - [ ] No error
   - [ ] Field shows empty after refresh

---

### **Scenario 2.2: Formula Mode**

**Test Cases:**

**2.2.1: Simple Formula**
1. Click formula toggle/button
2. Enter: `=10 * 5`
3. Save or calculate
   - [ ] Result: 50.000
   - [ ] Formula stored in VolumeFormulaState
   - [ ] Display shows result

**2.2.2: Complex Formula**
1. Enter: `=(10 + 5) * 2 - 3`
2. Calculate
   - [ ] Result: 27.000
   - [ ] Correct order of operations

**2.2.3: Formula with Decimals**
1. Enter: `=12.5 * 3.2`
2. Calculate
   - [ ] Result: 40.000
   - [ ] Decimal precision maintained

**2.2.4: Edit Formula**
1. Change formula from `=10*5` to `=10*6`
2. Save
   - [ ] Result updates to 60.000
   - [ ] Formula stored correctly

**2.2.5: Switch Formula → Manual**
1. Clear formula
2. Enter manual value: 75.000
3. Save
   - [ ] Formula state deleted
   - [ ] Manual value saved
   - [ ] is_fx = False

**2.2.6: Switch Manual → Formula**
1. Start with manual value
2. Enter formula
3. Save
   - [ ] Formula state created
   - [ ] Result calculated
   - [ ] is_fx = True

---

### **Scenario 2.3: Validation**

**2.3.1: Negative Volume**
1. Input: `-50`
2. Try to save
   - [ ] Validation error
   - [ ] Message: "Volume tidak boleh negatif"
   - [ ] Field highlighted

**2.3.2: Non-Numeric Input**
1. Input: `abc123`
2. Try to save
   - [ ] Validation error or prevented
   - [ ] Clear message

**2.3.3: Exceeds Max Digits**
1. Input: `99999999999999999999` (20 digits)
2. Try to save
   - [ ] Validation error
   - [ ] Message about max value

**2.3.4: Invalid Formula**
1. Enter: `=10 / 0`
2. Calculate
   - [ ] Error caught
   - [ ] Message: "Division by zero"

**2.3.5: Formula Syntax Error**
1. Enter: `=10 * * 5`
2. Calculate
   - [ ] Error caught
   - [ ] Message: "Invalid formula syntax"

---

### **Scenario 2.4: Cascade Effect Check**

**Objective:** Verify volume resets when source type changes

**Setup:**
1. Create pekerjaan with volume = 100.000
2. Go to List Pekerjaan page
3. Change source type (e.g., CUSTOM → REF)
4. Save
5. Return to Volume Pekerjaan page

**Verify:**
- [ ] Volume field is EMPTY
- [ ] VolumePekerjaan record DELETED from database
- [ ] No error shown
- [ ] Can enter new volume

**Expected Result:** ✅ CASCADE RESET WORKING

---

### **Scenario 2.5: Export Functions**

**2.5.1: Export to CSV**
1. Click "Export CSV" button
   - [ ] File downloads
   - [ ] Filename: "volume_pekerjaan_PROJECT-NAME_DATE.csv"
   - [ ] Opens in Excel/LibreOffice
   - [ ] Data accurate
   - [ ] Columns: Kode, Uraian, Satuan, Volume
   - [ ] Decimal format correct

**2.5.2: Export to PDF**
1. Click "Export PDF"
   - [ ] PDF generates
   - [ ] Formatting good
   - [ ] All data included
   - [ ] Header/footer present

**2.5.3: Export to Word**
1. Click "Export Word"
   - [ ] Document downloads
   - [ ] Opens in Word
   - [ ] Table formatted
   - [ ] Data complete

---

### **Scenario 2.6: UI/UX Elements**

**2.6.1: Input Field Behavior**
1. Focus on volume input
   - [ ] Cursor positioned correctly
   - [ ] Can type immediately
   - [ ] Accepts decimal separator (. or ,)

**2.6.2: Real-time Calculation**
1. Type formula
   - [ ] Result shows in real-time (if implemented)
   - [ ] Updates as you type

**2.6.3: Keyboard Navigation**
1. Use Tab to move between fields
   - [ ] Tab order logical
   - [ ] Enter saves (if implemented)

**2.6.4: Mobile Responsive**
1. Open on mobile device
   - [ ] Inputs accessible
   - [ ] Buttons not overlapping
   - [ ] Scrollable

---

## 3️⃣ POST-TEST: CODE REVIEW

### **Check for:**

#### **Unused Code:**
```javascript
// In volume_pekerjaan.js
- [ ] Old formula parser (if new one exists)
- [ ] Commented-out calculation logic
- [ ] Debug console.log statements
```

#### **Performance Issues:**
```javascript
// Check for N+1 queries
- [ ] Loading all pekerjaan without select_related()
- [ ] Loading formula state in loop
```

#### **Security Issues:**
```javascript
// Formula parser
- [ ] Check if using eval() ❌ DANGEROUS
- [ ] Should use safe parser (Function constructor or library)
```

#### **Code Quality:**
```python
# views_api.py - api_save_volume_pekerjaan()
- [ ] Is error handling comprehensive?
- [ ] Are edge cases handled?
- [ ] Is logging adequate?
```

---

## 4️⃣ CLEANUP RECOMMENDATIONS

### **To REMOVE:**

```javascript
// volume_pekerjaan.js
Function: legacyFormulaParser() [if exists]
Reason: Replaced by new parser
Action: DELETE

// Dead code
Lines: 150-200 [commented out validation]
Reason: No longer needed
Action: DELETE
```

### **To REFACTOR:**

```javascript
// Large function
Function: saveVolume() [if >100 lines]
Recommendation: Split into:
  - validateInput()
  - calculateFormula()
  - saveToServer()
Priority: Medium
```

### **To IMPROVE:**

```python
# views_api.py
Function: api_save_volume_pekerjaan()
Current: Basic try/except
Recommendation: Add specific exception handling
  - DecimalField validation
  - NOT NULL constraint
  - Concurrent update detection
Priority: High
```

---

## 5️⃣ FEATURE GAPS

### **CRITICAL:**

**1. Input Validation Feedback**
```javascript
// Show real-time validation
onInput() {
    if (value < 0) {
        showError("Volume tidak boleh negatif");
        disableSave();
    }
}
```
**Priority:** 🔴 CRITICAL
**Effort:** 2 hours

---

### **HIGH:**

**2. Bulk Volume Input**
```
Feature: Copy volume from another project
Use case: Similar projects with similar volumes
Priority: 🟡 HIGH
Effort: 6 hours
```

**3. Formula Library**
```javascript
// Predefined formulas
const formulaTemplates = {
    'luas_persegi': '=panjang * lebar',
    'volume_balok': '=panjang * lebar * tinggi',
    'volume_silinder': '=π * r² * tinggi'
};
```
**Priority:** 🟡 HIGH
**Effort:** 4 hours

---

### **MEDIUM:**

**4. Unit Conversion**
```
Feature: Auto-convert units (m² → cm², m³ → liter)
Priority: 🟢 MEDIUM
Effort: 8 hours
```

**5. Volume History**
```
Feature: Track volume changes over time
Use case: Audit trail, see who changed what
Priority: 🟢 MEDIUM
Effort: 6 hours
```

---

## 6️⃣ ACTION ITEMS

### **Immediate:**
- [ ] Add input validation feedback (2 hours)
- [ ] Remove console.log statements (30 min)
- [ ] Fix formula parser security (if using eval) (2 hours)

### **Short-term:**
- [ ] Add formula library (4 hours)
- [ ] Improve error messages (2 hours)
- [ ] Add loading indicators (2 hours)

### **Long-term:**
- [ ] Bulk volume input (6 hours)
- [ ] Volume history tracking (6 hours)
- [ ] Unit conversion (8 hours)

---

## 7️⃣ TEST RESULTS TEMPLATE

**Page:** Volume Pekerjaan
**Test Date:** 2025-11-__
**Duration:** ___ hours

| Scenario | Status | Notes |
|----------|--------|-------|
| Basic Volume Input | ✅ / 🔴 | |
| Formula Mode | ✅ / 🔴 | |
| Validation | ✅ / 🔴 | |
| Cascade Effect | ✅ / 🔴 | |
| Export | ✅ / 🔴 | |
| UI/UX | ✅ / 🔴 | |

**Bugs Found:** __
**Cleanup Items:** __
**Features Needed:** __

---

**Status:** ⏳ PENDING
**Next Page:** Template AHSP

---
---

# 📄 PAGE 3-10: TO BE COMPLETED

_[Similar detailed structure for each remaining page]_

Each page will follow the same format:
1. Pre-Test Code Analysis
2. Manual Testing Scenarios
3. Post-Test Code Review
4. Cleanup Recommendations
5. Feature Gaps
6. Action Items
7. Test Results

---

# 📊 OVERALL PROGRESS TRACKER

| Page | Analysis | Testing | Review | Status |
|------|----------|---------|--------|--------|
| 1. List Pekerjaan | ⏳ | ⏳ | ⏳ | ⏳ PENDING |
| 2. Volume Pekerjaan | ⏳ | ⏳ | ⏳ | ⏳ PENDING |
| 3. Template AHSP | ⏳ | ⏳ | ⏳ | ⏳ PENDING |
| 4. Harga Items | ⏳ | ⏳ | ⏳ | ⏳ PENDING |
| 5. Rincian AHSP | ⏳ | ⏳ | ⏳ | ⏳ PENDING |
| 6. Rekap RAB | ⏳ | ⏳ | ⏳ | ⏳ PENDING |
| 7. Rekap Kebutuhan | ⏳ | ⏳ | ⏳ | ⏳ PENDING |
| 8. Jadwal Pekerjaan | ⏳ | ⏳ | ⏳ | ⏳ PENDING |
| 9. Rincian RAB | ⏳ | ⏳ | ⏳ | ⏳ PENDING |
| 10. Kelola Tahapan | ⏳ | ⏳ | ⏳ | ⏳ PENDING |

---

# 🎯 HOW TO USE THIS ROADMAP

## **For Each Page:**

### **Step 1: Pre-Test (30 min)**
1. Read "Files to Analyze" section
2. Open each file mentioned
3. Review code structure
4. Fill out "Code Review Checklist"
5. Note any immediate concerns

### **Step 2: Manual Testing (45 min)**
1. Start development server
2. Navigate to page
3. Execute each test scenario
4. Mark checkboxes as you complete
5. Document bugs immediately
6. Take screenshots if needed

### **Step 3: Post-Test Review (30 min)**
1. Analyze bugs in context of code
2. Identify patterns
3. List cleanup opportunities
4. Propose improvements

### **Step 4: Documentation (15 min)**
1. Fill "Test Results Template"
2. Update "Action Items"
3. Commit findings to git
4. Prepare for next page

---

# 📝 DELIVERABLES PER PAGE

After testing each page, you will have:

1. ✅ **Test Results Report**
   - All scenarios executed
   - Bugs documented
   - Pass/fail status

2. ✅ **Code Review Report**
   - Files analyzed
   - Issues identified
   - Cleanup list

3. ✅ **Recommendations Document**
   - Features to add
   - Code to remove
   - Refactoring needed

4. ✅ **Action Items List**
   - Prioritized tasks
   - Time estimates
   - Assigned to sprints

---

# 🚀 STARTING GUIDE

## **Ready to Start?**

### **For Page 1 (List Pekerjaan):**

```bash
# 1. Open all related files
code detail_project/views_api.py:564  # _reset_pekerjaan_related_data()
code detail_project/static/detail_project/js/list_pekerjaan.js:795  # syncFields()
code detail_project/templates/detail_project/list_pekerjaan.html

# 2. Start server
python manage.py runserver

# 3. Open browser
http://localhost:8000/detail_project/{project_id}/list-pekerjaan/

# 4. Follow scenarios in this document

# 5. Document findings in MANUAL_TEST_RESULTS.md
```

---

**Last Updated:** 2025-11-09
**Owner:** [Your Name]
**Next Review:** After each page completion
