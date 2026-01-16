@echo off
REM ============================================================================
REM Load Test - 50 USERS RE-TEST (After Critical Fixes)
REM ============================================================================
REM Re-test after Skenario A fixes:
REM   1. Statement timeout increased to 60s
REM   2. Template export N+1 fixed with prefetch_related
REM   3. Dashboard query optimized with select_related
REM ============================================================================

echo ============================================================================
echo 50-USER RE-TEST - AFTER CRITICAL FIXES
echo ============================================================================
echo.
echo PREVIOUS RESULTS (Before Fixes):
echo   - Success Rate: 98.08%% (BELOW TARGET!)
echo   - Failures: 72 total
echo     * Template Export: 21 failures
echo     * Auth Login: 20 failures
echo     * Dashboard: 5 failures
echo     * Other 500 errors: 26
echo   - P95 Response: 1800ms
echo   - Max Response: 23.8 seconds
echo.
echo FIXES APPLIED:
echo   1. Statement Timeout: 30s -^> 60s
echo   2. Template Export: N+1 queries -^> 2 queries (prefetch_related)
echo   3. Dashboard: Added select_related('owner')
echo.
echo EXPECTED RESULTS (After Fixes):
echo   - Success Rate: ^>99.5%% (target: 99.5-99.8%%)
echo   - Template Export Failures: ^<5 (target: 0-2)
echo   - Auth Login Failures: ^<10 (target: 0-5)
echo   - Dashboard Failures: 0
echo   - P95 Response: ^<1000ms
echo   - Throughput: ^>13 req/s
echo.
echo ============================================================================
echo.
echo Test Configuration:
echo   Users: 50 concurrent
echo   Spawn Rate: 2 users/sec
echo   Duration: 300 seconds (5 minutes)
echo   Endpoints: 88 (Phase 4 complete coverage)
echo.
echo Results: hasil_test_v10_scalling50_phase4_fixed_*.csv
echo ============================================================================
echo.

echo IMPORTANT: Make sure Django server is running!
echo   python manage.py runserver
echo.
pause

echo.
echo Starting 50-user re-test...
echo.

locust -f load_testing/locustfile.py ^
    --headless ^
    -u 50 ^
    -r 2 ^
    -t 300s ^
    --host=http://localhost:8000 ^
    --csv=hasil_test_v10_scalling50_phase4_fixed ^
    --html=hasil_test_v10_scalling50_phase4_fixed.html

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Test failed to complete!
    echo Check if Django server is running.
    goto :error
)

echo.
echo ============================================================================
echo RE-TEST COMPLETED - 50 USERS
echo ============================================================================
echo.
echo Results saved:
echo   - hasil_test_v10_scalling50_phase4_fixed_stats.csv
echo   - hasil_test_v10_scalling50_phase4_fixed_failures.csv
echo   - hasil_test_v10_scalling50_phase4_fixed_exceptions.csv
echo   - hasil_test_v10_scalling50_phase4_fixed.html
echo.
echo Next Steps:
echo   1. Review hasil_test_v10_scalling50_phase4_fixed.html in browser
echo   2. Compare with previous 50-user test:
echo      - Before: 98.08%% success, 72 failures
echo      - After:  ??%% success, ?? failures
echo   3. Check critical metrics:
echo      - Template export failures (target: ^<5)
echo      - Auth login failures (target: ^<10)
echo      - Dashboard failures (target: 0)
echo      - Success rate (target: ^>99.5%%)
echo   4. If SUCCESS CRITERIA MET:
echo      -^> Proceed to 100-user test
echo   5. If STILL ISSUES:
echo      -^> Run: python check_postgres_config.py
echo      -^> Check PostgreSQL max_connections
echo      -^> Consider full Redis caching layer
echo.
echo SUCCESS CRITERIA:
echo   [✓] Success Rate ^> 99.5%%
echo   [✓] Template Export Failures ^< 5
echo   [✓] Auth Login Failures ^< 10
echo   [✓] Dashboard Failures = 0
echo   [✓] P95 Response ^< 1000ms
echo   [✓] Throughput ^> 13 req/s
echo.
echo ============================================================================
goto :end

:error
echo.
echo ============================================================================
echo RE-TEST FAILED
echo ============================================================================
echo.
echo Troubleshooting:
echo   1. Verify Django server is running
echo   2. Check server logs for errors
echo   3. Run: python check_postgres_config.py
echo   4. Review database connection pool settings
echo   5. Check for memory/CPU constraints
echo.
echo ============================================================================

:end
pause
