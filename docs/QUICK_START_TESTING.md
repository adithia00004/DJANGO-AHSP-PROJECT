# Quick Start - Testing Dual Storage Implementation

**Time Required**: 20 minutes
**Status**: Ready to test

---

## 🚀 3-Step Quick Start

### **Step 1: Run Migration** (5 min)

```bash
# Navigate to project directory
cd /d/PORTOFOLIO\ ADIT/DJANGO\ AHSP\ PROJECT

# Activate virtual environment (if not already active)
source env/Scripts/activate  # Windows Git Bash
# or
# .\env\Scripts\activate  # Windows PowerShell

# Start PostgreSQL (if not running)
pg_ctl start

# Run migration (dry-run first)
python manage.py migrate_storage2 --project-id=94 --dry-run

# Review output, then run actual migration
python manage.py migrate_storage2 --project-id=94
```

**Expected Output**:
```
================================================================================
STORAGE 2 MIGRATION - Project 94
================================================================================

Found 7 pekerjaan to migrate:

ID     Kode                 Source          Storage1   Status
--------------------------------------------------------------------------------
359    2.2.2.1.1            ref             6          ✅ Can migrate
360    2.2.2.1.10           ref             6          ✅ Can migrate
361    1.3.1.1              ref             2          ✅ Can migrate
362    1.3.1.3              ref             3          ✅ Can migrate
363    CUST-0001            custom          2          ⚠️  AHSP Bundle (Skip)
364    3.6.1.7              ref             7          ✅ Can migrate
366    mod.1-3.7.3          ref_modified    6          ✅ Can migrate
--------------------------------------------------------------------------------

================================================================================
MIGRATION COMPLETE
================================================================================
✅ Success: 6
❌ Errors: 0
⚠️  Skipped (AHSP bundles): 1
```

**✅ Success Indicator**: "✅ Success: 6"

---

### **Step 2: Verify REF & REF_MODIFIED** (5 min)

**Test Pekerjaan ID 359** (REF):
1. Open browser: `http://localhost:8000/detail-project/94/harga-items/`
2. Filter untuk pekerjaan "2.2.2.1.1"
3. ✅ Should see **6 items**: TK-0001, TK-0002, TK-0010, B-0173, TK-0005, dll
4. ✅ NOT empty!

**Test Pekerjaan ID 366** (REF_MODIFIED):
1. Filter untuk pekerjaan "mod.1-3.7.3"
2. ✅ Should see **6 items**: TK-0001, TK-0002, B-0175, TK-0008, TK-0005, dll
3. ✅ NOT empty!

---

### **Step 3: Fix & Test CUSTOM** (10 min)

**Manual Fix for Pekerjaan ID 363**:
1. Navigate to Template AHSP page: `http://localhost:8000/detail-project/94/template-ahsp/`
2. Click pekerjaan "CUST-0001"
3. Delete existing LAIN items (yang error)
4. Add new LAIN item:
   - Kategori: **LAIN**
   - Kode: Type "2.2.1.3" dalam autocomplete
   - Select from **"Master AHSP"** dropdown (misalnya: 2.2.1.3.3)
   - Koefisien: **1.0**
5. Click **Save**

**Expected Response**:
```json
{
  "ok": true,
  "saved_raw_rows": 3,
  "saved_expanded_rows": 5,
  "errors": []
}
```

**Verification**:
1. Navigate to Harga Items page
2. Filter untuk "CUST-0001"
3. ✅ Should see **5+ items** (expanded dari AHSP bundle)
4. ✅ NOT empty!

---

## ✅ Success Criteria

All 3 scenarios should work:

| Pekerjaan | Type | Expected Harga Items | Status |
|-----------|------|----------------------|--------|
| 359 (2.2.2.1.1) | REF | 6 items (TK, BHN) | ⏳ Test |
| 366 (mod.1-3.7.3) | REF_MODIFIED | 6 items (TK, BHN) | ⏳ Test |
| 363 (CUST-0001) | CUSTOM | 5+ items (expanded) | ⏳ Test |

**100% Success = All pages show items (NOT empty)** ✅

---

## 🧪 Advanced Testing (Optional)

### **Test 4: Nested AHSP Bundle**

1. Create new CUSTOM pekerjaan
2. Add LAIN with nested AHSP (3 levels deep)
3. Verify expansion works
4. Check koefisien multiplication

### **Test 5: MAX_DEPTH Enforcement**

1. Try to create bundle deeper than 3 levels
2. Should get error: "Maksimum kedalaman... terlampaui (max 3)"

---

## 🐛 Troubleshooting

### **Problem: Migration fails**
```bash
# Run diagnostic
python manage.py diagnose_harga_items --project-id=94 --pekerjaan-id=359
```

### **Problem: Harga Items still empty**
1. Check Storage 2 count:
   ```sql
   SELECT COUNT(*) FROM detail_project_detailahspexpanded
   WHERE project_id=94 AND pekerjaan_id=359;
   ```
2. If 0 → Re-run migration
3. If > 0 → Check query in views_api.py:1944

### **Problem: AHSP bundle save fails**
1. Check browser console for errors
2. Check Django logs for `[EXPAND_AHSP_BUNDLE]` messages
3. Verify AHSP exists in database

---

## 📞 Next Steps After Testing

### **If All Tests Pass** ✅:
1. Document any issues found
2. Deploy to production (optional)
3. Monitor logs for errors
4. User training (if needed)

### **If Tests Fail** ❌:
1. Note which scenario failed
2. Run diagnostic command
3. Check logs for error messages
4. Report findings for debugging

---

## 📝 Test Results Template

Copy and fill this out:

```
Date: _____________
Tester: _____________

Migration (Step 1):
[ ] Success (6 pekerjaan migrated)
[ ] Failed (Error: _____________)

REF Test (Step 2):
[ ] Pekerjaan 359: ____ items shown
[ ] Pekerjaan 366: ____ items shown

CUSTOM Test (Step 3):
[ ] Pekerjaan 363: ____ items shown
[ ] AHSP bundle expansion worked

Overall Status:
[ ] All Pass ✅
[ ] Some Failed ❌ (Details: _____________)

Notes:
_____________________________________________
_____________________________________________
```

---

**Ready to start?** Follow Step 1 → Step 2 → Step 3 in order.

**Estimated Time**: 20 minutes total

**Questions?** Check `docs/DUAL_STORAGE_IMPLEMENTATION_COMPLETE.md` for detailed documentation.
