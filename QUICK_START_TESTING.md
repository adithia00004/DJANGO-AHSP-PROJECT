# 🚀 QUICK START - TESTING GUIDE

**Goal:** Fix test errors & manually test all pages
**Timeline:** 8 days
**Status:** Ready to start

---

## 📋 TODAY'S TASKS (Day 1-2)

### ✅ Step 1: Fix Klasifikasi Field Name (30 min)

**File:** `detail_project/tests/test_phase5_integration.py`

**Lines to change:**
```bash
# Find lines with 'nama':
grep -n "'nama':" detail_project/tests/test_phase5_integration.py
```

**Change:**
```python
# Line 139-141, 175, etc.
'nama': 'Test'  →  'name': 'Test'
```

**Test:**
```bash
pytest detail_project/tests/test_phase5_integration.py::TestTransactionSafety -v
```

---

### ✅ Step 2: Fix tanggal_mulai Tests (2-3 hours)

**Find problematic tests:**
```bash
grep -r "Project.objects.create" detail_project/tests/*.py | grep -v "conftest\|tanggal_mulai"
```

**Fix pattern:**
```python
# Add this import
from datetime import date

# Add tanggal_mulai to all Project.objects.create()
Project.objects.create(
    ...,
    tanggal_mulai=date.today()  # ← ADD THIS
)
```

**Or better - use fixture:**
```python
# Change function signature
def test_something(project):  # ← Use fixture instead of (user)
    # project already has tanggal_mulai
```

**Test each fix:**
```bash
pytest detail_project/tests/test_api_numeric_endpoints.py -v
pytest detail_project/tests/test_weekly_canonical_validation.py -v
# etc.
```

---

### ✅ Step 3: Run Full Test Suite (30 min)

```bash
# Run all tests
pytest detail_project/tests/ -v --tb=short > test_results_day1.txt 2>&1

# Check pass rate
pytest detail_project/tests/ -v --tb=no | tail -1
```

**Target:** >95% passing (293+ of 308)

---

## 📝 DAY 3-4: MANUAL TESTING

### Priority Order:

1. **List Pekerjaan** (Most critical - CASCADE RESET feature)
   - Focus on source type changes
   - Verify cascade reset works
   - Test error handling

2. **Volume Pekerjaan**
   - Test formula mode
   - Verify cascade effect (volume reset when source changed)

3. **Template AHSP**
   - Test CUSTOM/REF/REF_MOD modes
   - Test bundle support

4. **Harga Items**
   - Test price editing
   - Test search/filter

5. **Rincian AHSP**
   - Test view/export

### How to Test:

1. Open browser to: `http://localhost:8000`
2. Login with test account
3. Create test project
4. Navigate to each page
5. Follow scenarios in `TESTING_AGENDA.md`
6. Log bugs in `MANUAL_TEST_RESULTS.md`

**Template for quick bug logging:**
```markdown
#### Bug [PAGE]-[###]: [Title] 🔴/🟡/🟢
**Steps:**
1. ...
2. ...

**Expected:** ...
**Actual:** ...
**Screenshot:** [paste or attach]
```

---

## 🔧 DAY 5-6: MORE MANUAL TESTING

Continue with remaining pages:
6. Rekap RAB
7. Rekap Kebutuhan
8. Jadwal Pekerjaan
9. Rincian RAB
10. Kelola Tahapan

---

## 💡 DAY 7: IMPLEMENT WARNING DIALOG

**File:** `detail_project/static/detail_project/js/list_pekerjaan.js`

**Add this code:**
```javascript
// Find the form submit handler
const form = document.querySelector('#list-pekerjaan-form');

form.addEventListener('submit', function(e) {
    const sourceSelects = document.querySelectorAll('[name*="source_type"]');

    for (let select of sourceSelects) {
        const row = select.closest('.pekerjaan-row');
        const oldSource = row.dataset.sourceType;
        const newSource = select.value;

        if (oldSource !== newSource) {
            const confirmed = confirm(
                "⚠️ PERHATIAN!\n\n" +
                "Mengubah tipe sumber akan menghapus:\n" +
                "• Volume Pekerjaan\n" +
                "• Jadwal (Tahapan)\n" +
                "• Template AHSP\n" +
                "• Formula State\n\n" +
                "Lanjutkan?"
            );

            if (!confirmed) {
                e.preventDefault();
                select.value = oldSource; // Revert
                return false;
            }
        }
    }
});
```

**Test:**
1. Edit pekerjaan
2. Change source type
3. Click save
4. ✅ Warning dialog should appear

---

## 📊 DAY 8: DOCUMENTATION

1. Update test results in `MANUAL_TEST_RESULTS.md`
2. Update `SOURCE_CHANGE_CASCADE_RESET.md` with warning dialog
3. Create bug backlog
4. Review with team

---

## 🎯 QUICK REFERENCE

### Most Important Files:
```
TESTING_AGENDA.md           ← Full agenda (this is comprehensive!)
MANUAL_TEST_RESULTS.md      ← Log bugs/tests here
QUICK_START_TESTING.md      ← This file (quick ref)
```

### Key Commands:
```bash
# Run specific test
pytest detail_project/tests/test_list_pekerjaan.py -v

# Run with coverage
pytest detail_project/tests/ --cov=detail_project

# Run server
python manage.py runserver

# Check migrations
python manage.py showmigrations detail_project

# Django shell
python manage.py shell
```

### Git Workflow:
```bash
# Create feature branch
git checkout -b fix/test-failures

# Commit each fix
git add detail_project/tests/test_phase5_integration.py
git commit -m "fix(test): change Klasifikasi nama → name field"

# After all fixes
git push -u origin fix/test-failures
```

---

## ✅ DAILY CHECKLIST

### Day 1
- [ ] Fix test_phase5_integration.py (nama → name)
- [ ] Commit & push
- [ ] Run those 3 tests - verify passing
- [ ] Celebrate small win! 🎉

### Day 2
- [ ] Fix tanggal_mulai in test files (5-10 files)
- [ ] Run full test suite
- [ ] Check pass rate (target: >95%)
- [ ] Commit & push
- [ ] Review `TESTING_AGENDA.md` for Day 3

### Day 3
- [ ] Manual test: List Pekerjaan (3 hours)
- [ ] Manual test: Volume Pekerjaan (1 hour)
- [ ] Log all bugs found
- [ ] Take screenshots

### Day 4
- [ ] Manual test: Template AHSP (2 hours)
- [ ] Manual test: Harga Items (1 hour)
- [ ] Manual test: Rincian AHSP (1 hour)
- [ ] Log all bugs

### Day 5
- [ ] Manual test: Rekap RAB (1 hour)
- [ ] Manual test: Rekap Kebutuhan (1 hour)
- [ ] Manual test: Jadwal Pekerjaan (2 hours)

### Day 6
- [ ] Manual test: Rincian RAB (1 hour)
- [ ] Manual test: Kelola Tahapan (1 hour)
- [ ] Review all bugs found (2 hours)
- [ ] Prioritize fixes

### Day 7
- [ ] Implement warning dialog (2 hours)
- [ ] Test warning dialog (1 hour)
- [ ] Fix critical bugs (4 hours)
- [ ] Commit & push

### Day 8
- [ ] Update documentation (2 hours)
- [ ] Final test run (2 hours)
- [ ] Create deployment checklist (1 hour)
- [ ] Team review (1 hour)

---

## 🆘 TROUBLESHOOTING

### Tests not running?
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install requirements
pip install -r requirements.txt
```

### Can't find file?
```bash
# Find file
find . -name "list_pekerjaan.js"

# Search content
grep -r "function syncFields" detail_project/
```

### Git conflicts?
```bash
# Stash changes
git stash

# Pull latest
git pull origin main

# Apply stash
git stash pop
```

---

## 📞 NEED HELP?

1. Check `TESTING_AGENDA.md` for detailed instructions
2. Check error message in terminal
3. Search error in documentation
4. Ask Claude for help (provide error message + context)

---

**Remember:**
- ✅ Fix automated tests FIRST (Day 1-2)
- ✅ Then manual test thoroughly (Day 3-6)
- ✅ Document everything you find
- ✅ Don't skip the warning dialog (Day 7)!

**You got this! 🚀**
