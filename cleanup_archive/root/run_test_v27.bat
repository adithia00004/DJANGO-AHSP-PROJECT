@echo off
REM =============================================================================
REM V27 Load Test - Realistic Spawn Rate (1 user/s)
REM =============================================================================
REM
REM Purpose: Validate core endpoint performance with staggered login pattern
REM Changes from v26: Spawn rate reduced from 4 user/s to 1 user/s
REM Expected: Login spike distributed over 100s instead of 25s
REM
REM =============================================================================

echo.
echo ========================================================================
echo DJANGO AHSP PROJECT - Load Test v27
echo ========================================================================
echo Configuration:
echo   - Users: 100
echo   - Spawn Rate: 1 user/second (realistic staggered logins)
echo   - Duration: 300 seconds (5 minutes)
echo   - Tags: api, page, phase1
echo   - Excluded: export, admin
echo   - Pool: 140/20 connections
echo ========================================================================
echo.

REM Set environment variables
set ACCOUNT_RATE_LIMITS_DISABLED=true

echo [1/3] Checking prerequisites...
echo   - Django server should be running on http://localhost:8000
echo   - PgBouncer should be running and healthy
echo   - Redis should be running
echo.

pause

echo [2/3] Starting Locust load test...
echo   Test will complete in approximately 5-6 minutes
echo   Results will be saved to: hasil_test_v27_100u_r1_pool140_core_only.*
echo.

locust -f load_testing/locustfile.py --headless ^
  -u 100 ^
  -r 1 ^
  -t 300s ^
  --host=http://localhost:8000 ^
  --tags api page phase1 ^
  --exclude-tags export admin ^
  --csv=hasil_test_v27_100u_r1_pool140_core_only ^
  --html=hasil_test_v27_100u_r1_pool140_core_only.html

echo.
echo [3/3] Test completed!
echo.
echo Results saved:
echo   - Stats CSV: hasil_test_v27_100u_r1_pool140_core_only_stats.csv
echo   - Failures: hasil_test_v27_100u_r1_pool140_core_only_failures.csv
echo   - HTML Report: hasil_test_v27_100u_r1_pool140_core_only.html
echo.
echo ========================================================================
echo Next Step: Share the results with Claude for analysis
echo ========================================================================
echo.

pause
