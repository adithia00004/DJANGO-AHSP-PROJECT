# Multi-User Test POST Missing - Diagnostic Report
**Date**: 2026-01-11
**Status**: ROOT CAUSE IDENTIFIED
**Reporter**: Claude (crosscheck with Codex findings)

---

## PROBLEM STATEMENT

During auth-only load test with rate limits disabled and multi-user configuration:
- **Test**: 50 users, 120s duration, `TEST_USER_POOL` with multiple users
- **Expected**: POST metrics for `/accounts/login/` showing authentication requests
- **Actual**: Only GET requests recorded in CSV, no POST rows present
- **File**: `hasil_test_auth_only_50u_multi_nolimit_stats.csv`

---

## ROOT CAUSE ANALYSIS

### Issue #1: TEST_USER_POOL Format Mismatch ⭐⭐⭐⭐⭐

**Evidence**:
```bash
# Weekly Report Line 35: Codex's test command
export TEST_USER_POOL="aditf96,testuser1,testuser2,testuser3,testuser4"
```

**Expected Format** ([locustfile.py:48-59](load_testing/locustfile.py#L48-L59)):
```python
def _parse_user_pool(raw: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for item in raw.split(","):
        item = item.strip()
        if not item or ":" not in item:  # <-- REJECTS items without colon!
            continue  # <-- Skips invalid entries silently
        username, password = item.split(":", 1)
        ...
```

**What Happened**:
1. Test command set `TEST_USER_POOL="aditf96,testuser1,testuser2,testuser3,testuser4"`
2. Parser checked each item: `"aditf96"`, `"testuser1"`, etc.
3. None contain `":"` → all rejected via `continue` (line 52-53)
4. Result: `USER_POOL = []` (empty list)
5. Fallback triggered (line 63-64): `USER_POOL = [(TEST_USERNAME, TEST_PASSWORD)]`
6. Test ran with **single user** despite multi-user configuration

**Severity**: CRITICAL - Test configuration silently failed without error message

---

### Issue #2: Silent Failure Design ⭐⭐⭐⭐☆

**Problem**: Parser silently rejects invalid entries without warning

**Current Behavior**:
```python
if not item or ":" not in item:
    continue  # <-- No error, no warning, no log
```

**Impact**:
- User thinks they're testing multi-user scenario
- Actually testing single-user (fallback)
- No indication that configuration was invalid
- Misleading test results

**Recommendation**: Add validation logging
```python
if not item or ":" not in item:
    _login_logger.warning(
        "Invalid TEST_USER_POOL entry (missing password): %s (expected format: username:password)",
        item
    )
    continue
```

---

### Issue #3: Missing POST Metrics (Secondary) ⭐⭐⭐☆☆

**Hypothesis**: If test actually ran as single-user due to Issue #1:
- Rate limits still disabled → 0 failures expected
- Single user making sequential requests
- Locust CSV aggregation might group/deduplicate similar requests
- Or: Test duration too short for enough POST samples

**Status**: UNCONFIRMED - needs verification after fixing Issue #1

---

## VERIFICATION STEPS

### Step 1: Confirm Parser Behavior
```python
# Python shell test
import os
os.environ['TEST_USER_POOL'] = "aditf96,testuser1,testuser2"

# Reproduce parser logic
def _parse_user_pool(raw: str):
    entries = []
    for item in raw.split(","):
        item = item.strip()
        if not item or ":" not in item:
            print(f"REJECTED: {item}")
            continue
        username, password = item.split(":", 1)
        entries.append((username, password))
    return entries

result = _parse_user_pool(os.environ['TEST_USER_POOL'])
print(f"USER_POOL: {result}")
# Expected output:
# REJECTED: aditf96
# REJECTED: testuser1
# REJECTED: testuser2
# USER_POOL: []
```

### Step 2: Run Corrected Multi-User Test
```bash
# CORRECT FORMAT: username:password pairs
set TEST_USER_POOL=aditf96:Ph@ntomk1d,testuser1:password1,testuser2:password2

set ACCOUNT_RATE_LIMITS_DISABLED=true
set LOCUST_AUTH_ONLY=true

locust -f load_testing/locustfile.py --headless \
  -u 50 -r 4 -t 180s \
  --host=http://localhost:8000 \
  --csv=hasil_test_auth_only_50u_multi_nolimit_v2_CORRECTED \
  --loglevel DEBUG
```

**Expected Result**:
- `logs/locust_login_failures.log` shows "multi_user_pool active (5 users)" message
- CSV shows POST requests with `/accounts/login/` name
- Auth success rate ~100% (with rate limits disabled)

---

## CORRECTED MULTI-USER CONFIGURATION

### Environment Variable Format
```bash
# Format: username1:password1,username2:password2,...
TEST_USER_POOL=aditf96:Ph@ntomk1d,testuser1:TestPass1,testuser2:TestPass2,testuser3:TestPass3

# Or use actual user credentials from database

---

## VERIFICATION UPDATE (2026-01-11)

### Retest With Correct Format

Command (user-provided):
```
export ACCOUNT_RATE_LIMITS_DISABLED=true
export LOCUST_AUTH_ONLY=true
export TEST_USER_POOL="aditf96:Ph@ntomk1d,loadtest01:LoadTest123!,loadtest02:LoadTest123!,loadtest03:LoadTest123!,loadtest04:LoadTest123!"
locust -f load_testing/locustfile.py --headless -u 50 -r 4 -t 180s --host=http://localhost:8000 --csv=hasil_test_auth_only_50u_multi_nolimit_v2 --loglevel DEBUG
```

Results (from `hasil_test_auth_only_50u_multi_nolimit_v2_stats.csv`):
- Aggregated: 100 requests, 20 failures
- Login POST: 50 requests, 20 failures (HTTP 500)
- Avg login: ~50.6s, P95 ~121s, max ~120.6s

Interpretation:
- POST metrics are now present -> multi-user run is producing login POST requests.
- Failures are now dominated by server errors (`query_wait_timeout`), not rate limits.

### Fix Applied (Logging Safety)
- `load_testing/locustfile.py` was updated to initialize `_login_logger` before `_parse_user_pool`.
- This avoids NameError and ensures pool validation messages are logged.

---

## VERIFICATION UPDATE (2026-01-11)

### Retest After Pool Increase (100/20)
- CSV: `hasil_test_auth_only_50u_multi_nolimit_v3_pool100_stats.csv`
- Aggregated: 100 requests, 0 failures
- Login POST: 50 requests, 0 failures (avg ~795ms, P95 ~1.1s)

Interpretation:
- With corrected TEST_USER_POOL format and higher pool, auth-only multi-user succeeds.
# Ensure all users exist in Django auth_user table
```

### Validation Checklist
- [ ] Each entry contains `username:password` with colon separator
- [ ] No spaces around colons (or use quotes if needed)
- [ ] Usernames match database records
- [ ] Passwords are correct
- [ ] Test users created in Django admin if missing

---

## RECOMMENDED FIXES

### Priority 1: Add Validation Logging (IMMEDIATE)

**File**: [load_testing/locustfile.py:48-66](load_testing/locustfile.py#L48-L66)

**Before**:
```python
def _parse_user_pool(raw: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for item in raw.split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue  # Silent failure
        username, password = item.split(":", 1)
        username = username.strip()
        password = password.strip()
        if username and password:
            entries.append((username, password))
    return entries
```

**After**:
```python
def _parse_user_pool(raw: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            _login_logger.warning(
                "TEST_USER_POOL invalid entry (missing ':password'): '%s' - skipped",
                item
            )
            continue
        username, password = item.split(":", 1)
        username = username.strip()
        password = password.strip()
        if username and password:
            entries.append((username, password))
        else:
            _login_logger.warning(
                "TEST_USER_POOL empty username or password: '%s' - skipped",
                item
            )
    return entries
```

### Priority 2: Update Documentation

**File**: [GETTING_STARTED_NOW.md](GETTING_STARTED_NOW.md)

Update line 276 from:
```bash
set TEST_USER_POOL=aditf96,testuser1,testuser2,testuser3,testuser4
```

To:
```bash
# CORRECT FORMAT: Each user needs password separated by colon
set TEST_USER_POOL=aditf96:Ph@ntomk1d,testuser1:TestPass1,testuser2:TestPass2
```

---

## IMPACT ASSESSMENT

### On Previous Test Results

**Test**: `hasil_test_auth_only_50u_multi_nolimit_stats.csv`
- **Intended**: Multi-user test with 5 users
- **Actual**: Single-user test (fallback to aditf96)
- **Validity**: Result is VALID but MISLABELED
- **Conclusion**: Re-run required with correct format

### On Other Tests
- **Single-user tests**: UNAFFECTED (don't use TEST_USER_POOL)
- **Load tests v18**: UNAFFECTED (use default single user)
- **Auth probe tests**: NEED REVIEW if TEST_USER_POOL was set

---

## NEXT STEPS

1. **Update locustfile.py** with validation logging (5 min)
2. **Update GETTING_STARTED_NOW.md** with correct format example (2 min)
3. **Run corrected multi-user test** (180s + 5 min analysis)
4. **Compare results**:
   - Single-user (existing): `hasil_test_auth_only_50u_single_nolimit_stats.csv`
   - Multi-user (corrected): `hasil_test_auth_only_50u_multi_nolimit_v2_CORRECTED_stats.csv`
5. **Update weekly report** with findings

---

## EXPECTED OUTCOMES (After Fix)

### With Correct Multi-User Configuration
```
User Distribution:
- aditf96: 10 Locust users
- testuser1: 10 Locust users
- testuser2: 10 Locust users
- testuser3: 10 Locust users
- testuser4: 10 Locust users
Total: 50 concurrent Locust users across 5 Django users
```

### CSV Metrics Expected
```
Name,# Requests,# Failures,%
[AUTH] Get Login Page,50,0,0%
[AUTH] Login POST,50,0,0%
```

### Log Evidence
```
logs/locust_login_failures.log:
2026-01-11T... INFO multi_user_pool active size=5 (aditf96,testuser1,testuser2,testuser3,testuser4)
```

---

## CONCLUSION

**Root Cause**: TEST_USER_POOL format mismatch - missing `:password` separator

**Fix Difficulty**: TRIVIAL (documentation update + rerun test)

**Learning**: Silent validation failures in test configuration can lead to misleading results

**Status**: READY TO FIX - No code changes required, only configuration correction
