@echo off
REM ============================================================================
REM FINAL 50-USER VALIDATION TEST
REM ============================================================================
REM Run AFTER fixing PostgreSQL max_connections
REM This is the final validation before 100-user test
REM ============================================================================

echo ============================================================================
echo FINAL 50-USER VALIDATION TEST
echo ============================================================================
echo.
echo CRITICAL: Run this ONLY AFTER fixing PostgreSQL configuration!
echo.
echo Required PostgreSQL Changes:
echo   - max_connections = 200
echo   - shared_buffers = 256MB
echo   - PostgreSQL restarted
echo.
echo To verify PostgreSQL fix:
echo   python check_postgres_config.py
echo.
echo ============================================================================
echo.
echo Test Configuration:
echo   Users: 50 concurrent
echo   Spawn Rate: 2 users/sec
echo   Duration: 300 seconds (5 minutes)
echo   Endpoints: 88 (Phase 4 complete coverage)
echo.
echo Code Fixes Applied:
echo   1. Template Export: prefetch_related + only() + limit 1000
echo   2. Dashboard: select_related('owner')
echo   3. Statement Timeout: 60 seconds
echo   4. PostgreSQL: max_connections = 200 (IF YOU DID THE FIX!)
echo.
echo Expected Results (After PostgreSQL Fix):
echo   - Success Rate: ^>99.5%% (was 98.25%%)
echo   - Auth Login Failures: ^<5 (was 20)
echo   - Template Export Failures: ^<10 (was 15)
echo   - Dashboard Failures: ^<3 (was 3)
echo   - Total Failures: ^<20 (was 65)
echo.
echo SUCCESS CRITERIA:
echo   [✓] Success Rate ^> 99.5%%
echo   [✓] Auth Login Failures ^< 5
echo   [✓] Template Export Failures ^< 10
echo   [✓] Dashboard Failures ^< 3
echo   [✓] Total Failures ^< 20
echo.
echo If ALL criteria met -^> Ready for 100-user test!
echo.
echo ============================================================================
echo.

set /p continue="Have you fixed PostgreSQL max_connections? (y/n): "
if /i not "%continue%"=="y" (
    echo.
    echo Please fix PostgreSQL first!
    echo.
    echo Instructions:
    echo   1. Run: python check_postgres_config.py
    echo   2. Follow the instructions shown
    echo   3. Restart PostgreSQL
    echo   4. Run this script again
    echo.
    pause
    exit /b 1
)

echo.
echo Verifying PostgreSQL configuration...
python check_postgres_config.py

echo.
set /p proceed="PostgreSQL configuration looks good? (y/n): "
if /i not "%proceed%"=="y" (
    echo.
    echo Please fix PostgreSQL configuration first.
    pause
    exit /b 1
)

echo.
echo IMPORTANT: Make sure Django server is running!
echo   python manage.py runserver
echo.
pause

echo.
echo Starting FINAL 50-user validation test...
echo.

locust -f load_testing/locustfile.py ^
    --headless ^
    -u 50 ^
    -r 2 ^
    -t 300s ^
    --host=http://localhost:8000 ^
    --csv=hasil_test_v10_scalling50_final ^
    --html=hasil_test_v10_scalling50_final.html

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Test failed to complete!
    echo Check if Django server is running.
    goto :error
)

echo.
echo ============================================================================
echo FINAL 50-USER TEST COMPLETED
echo ============================================================================
echo.
echo Results saved:
echo   - hasil_test_v10_scalling50_final_stats.csv
echo   - hasil_test_v10_scalling50_final_failures.csv
echo   - hasil_test_v10_scalling50_final_exceptions.csv
echo   - hasil_test_v10_scalling50_final.html
echo.
echo Next Steps:
echo   1. Review hasil_test_v10_scalling50_final.html in browser
echo   2. Check success criteria:
echo      - Success Rate ^> 99.5%%
echo      - Auth Login Failures ^< 5
echo      - Template Export Failures ^< 10
echo      - Total Failures ^< 20
echo   3. Compare with previous test:
echo      - Before PG fix: 98.25%% success, 65 failures
echo      - After PG fix:  ??%% success, ?? failures
echo   4. If ALL criteria met:
echo      -^> Proceed to 100-user test
echo      -^> Run: run_test_scale_100u.bat
echo   5. If criteria NOT met:
echo      -^> Review failures.csv
echo      -^> Check PostgreSQL max_connections again
echo      -^> May need additional optimizations
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
echo   3. Verify PostgreSQL max_connections = 200
echo   4. Run: python check_postgres_config.py
echo.
echo ============================================================================

:end
pause
