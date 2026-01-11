@echo off
REM ============================================================================
REM Load Test - 100 USERS SCALING TEST
REM ============================================================================
REM ONLY run this AFTER 50-user final test passes!
REM Final validation for production readiness
REM ============================================================================

echo ============================================================================
echo 100-USER SCALING TEST - PRODUCTION READINESS VALIDATION
echo ============================================================================
echo.
echo WARNING: Run this ONLY if 50-user final test PASSED!
echo.
echo Prerequisites:
echo   [✓] PostgreSQL max_connections = 200
echo   [✓] 50-user final test passed (^>99.5%% success)
echo   [✓] Auth login failures ^< 5
echo   [✓] Template export failures ^< 10
echo.
echo ============================================================================
echo.
echo Test Configuration:
echo   Users: 100 concurrent (2x previous test!)
echo   Spawn Rate: 10 users/sec
echo   Duration: 180 seconds (3 minutes)
echo   Endpoints: 88 (Phase 4 complete coverage)
echo.
echo Expected Results:
echo   - Success Rate: ^>98%% (acceptable for 100 users)
echo   - P95 Response Time: ^<2000ms
echo   - Throughput: ^>25 req/s
echo   - Total Failures: ^<50
echo.
echo This test will:
echo   - Validate system under 2x load
echo   - Identify final bottlenecks
echo   - Confirm production readiness
echo   - Test database connection pool limits
echo.
echo SUCCESS CRITERIA:
echo   [✓] Success Rate ^> 98%%
echo   [✓] P95 Response ^< 2000ms
echo   [✓] Throughput ^> 25 req/s
echo   [✓] No critical failures (auth, dashboard)
echo.
echo If criteria met -^> PRODUCTION READY!
echo.
echo ============================================================================
echo.

set /p continue="50-user final test PASSED? Ready to proceed? (y/n): "
if /i not "%continue%"=="y" (
    echo.
    echo Please run 50-user final test first!
    echo.
    echo Instructions:
    echo   1. Fix PostgreSQL: max_connections = 200
    echo   2. Run: run_test_scale_50u_final.bat
    echo   3. Verify success rate ^> 99.5%%
    echo   4. Then run this 100-user test
    echo.
    pause
    exit /b 1
)

echo.
echo IMPORTANT: Make sure Django server is running!
echo   python manage.py runserver
echo.
echo Note: 100 concurrent users is HEAVY load!
echo   - Server CPU usage will spike
echo   - Database connections will be high
echo   - This is normal for stress testing
echo.
pause

echo.
echo Starting 100-user scaling test...
echo This will take ~3 minutes...
echo.

locust -f load_testing/locustfile.py ^
    --headless ^
    -u 100 ^
    -r 10 ^
    -t 180s ^
    --host=http://localhost:8000 ^
    --csv=hasil_test_scale_100u ^
    --html=hasil_test_scale_100u.html

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Test failed to complete!
    echo Check if Django server is running.
    goto :error
)

echo.
echo ============================================================================
echo 100-USER TEST COMPLETED
echo ============================================================================
echo.
echo Results saved:
echo   - hasil_test_scale_100u_stats.csv
echo   - hasil_test_scale_100u_failures.csv
echo   - hasil_test_scale_100u_exceptions.csv
echo   - hasil_test_scale_100u.html
echo.
echo Next Steps:
echo   1. Review hasil_test_scale_100u.html in browser
echo   2. Check success criteria:
echo      - Success Rate ^> 98%%
echo      - P95 Response ^< 2000ms
echo      - Throughput ^> 25 req/s
echo   3. Compare with 50-user test:
echo      - 50 users: ??%% success, ?? req/s
echo      - 100 users: ??%% success, ?? req/s
echo   4. If SUCCESS CRITERIA MET:
echo      -^> SYSTEM IS PRODUCTION READY!
echo      -^> Can handle 100+ concurrent users
echo      -^> Database pool properly sized
echo      -^> All optimizations working
echo   5. If criteria NOT met:
echo      -^> Review failures by endpoint
echo      -^> Identify new bottlenecks
echo      -^> Consider Redis caching for heavy endpoints
echo      -^> May need read replica for database
echo.
echo Performance Benchmarks:
echo   - 10 users:  2.83 req/s,  99.06%% success
echo   - 30 users:  8.09 req/s,  99.01%% success
echo   - 50 users: ~13-14 req/s, ^>99.5%% success (if PG fixed)
echo   - 100 users: ^>25 req/s,  ^>98%% success (target)
echo.
echo Scaling Efficiency:
echo   - Linear scaling would be: 28.3 req/s (10x baseline)
echo   - Target: ^>25 req/s (^>88%% efficiency)
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
echo   1. Verify Django server is running and didn't crash
echo   2. Check server logs for errors
echo   3. Verify PostgreSQL max_connections = 200
echo   4. Check database connection pool not exhausted
echo   5. Monitor server resources (CPU, RAM, disk I/O)
echo.
echo Common Issues at 100 Users:
echo   - Database connection pool exhaustion
echo   - Server CPU/memory limits
echo   - Network bandwidth saturation
echo   - Disk I/O bottlenecks
echo.
echo ============================================================================

:end
pause
