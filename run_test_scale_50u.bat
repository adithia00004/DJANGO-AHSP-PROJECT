@echo off
REM ============================================================================
REM Load Test - SCALING TEST 50 USERS
REM ============================================================================
REM Test server performance with 50 concurrent users
REM After Phase 4 optimization (V2 Rekap Weekly + Template Export + DB Pool)
REM ============================================================================

echo ============================================================================
echo SCALING TEST - 50 CONCURRENT USERS
echo ============================================================================
echo.
echo Test Configuration:
echo   Users: 50 concurrent
echo   Spawn Rate: 5 users/sec
echo   Duration: 180 seconds (3 minutes)
echo   Endpoints: 88 (Phase 4 complete coverage)
echo.
echo Optimizations Applied:
echo   1. V2 Rekap Weekly: 2.4-2.7s -^> 200-400ms (98%% faster)
echo   2. Template Export: Unicode encoding fixed
echo   3. Database Pool: CONN_MAX_AGE=600, Health checks enabled
echo.
echo Expected Performance:
echo   - Success Rate: ^>98%%
echo   - Median Response: ^<200ms
echo   - P95 Response: ^<800ms
echo   - Throughput: ~13-15 req/s
echo.
echo Critical Metrics to Watch:
echo   - V2 Rekap Weekly P95 (should be ^<800ms)
echo   - Template Export failures (should be 0)
echo   - Database connection timeouts (should be 0)
echo.
echo Results: hasil_test_scale_50u_*.csv
echo ============================================================================
echo.

echo IMPORTANT: Make sure Django server is running!
echo   python manage.py runserver
echo.
pause

echo.
echo Starting 50-user scaling test...
echo.

locust -f load_testing/locustfile.py ^
    --headless ^
    -u 50 ^
    -r 5 ^
    -t 180s ^
    --host=http://localhost:8000 ^
    --csv=hasil_test_scale_50u ^
    --html=hasil_test_scale_50u.html

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Test failed to complete!
    echo Check if Django server is running.
    goto :error
)

echo.
echo ============================================================================
echo TEST COMPLETED - 50 USERS
echo ============================================================================
echo.
echo Results saved:
echo   - hasil_test_scale_50u_stats.csv
echo   - hasil_test_scale_50u_failures.csv
echo   - hasil_test_scale_50u_exceptions.csv
echo   - hasil_test_scale_50u.html
echo.
echo Next Steps:
echo   1. Review hasil_test_scale_50u.html in browser
echo   2. Compare with 30 users results:
echo      - 30 users: 2,419 requests, 99.01%% success, 8.09 req/s
echo      - 50 users: ?? requests, ??%% success, ?? req/s
echo   3. Check critical metrics:
echo      - V2 Rekap Weekly response time
echo      - Template export failures
echo      - P95/P99 tail latency
echo   4. If success rate ^>98%% and P95 ^<1000ms, proceed to 100 users
echo   5. If bottlenecks appear, implement caching before 100 users test
echo.
echo ============================================================================
goto :end

:error
echo.
echo ============================================================================
echo TEST FAILED
echo ============================================================================
echo.
echo Troubleshooting:
echo   1. Verify Django server is running
echo   2. Check server logs for errors
echo   3. Review database connection pool settings
echo   4. Check for memory/CPU constraints
echo.
echo ============================================================================

:end
pause
