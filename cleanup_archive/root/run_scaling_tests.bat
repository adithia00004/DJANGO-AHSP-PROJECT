@echo off
REM ============================================================================
REM Automated Scaling Test Suite - Django AHSP Application
REM ============================================================================
REM This script runs incremental load tests from 30 to 200 users
REM Each phase must pass before progressing to the next
REM ============================================================================

setlocal EnableDelayedExpansion

set HOST=http://localhost:8000
set LOCUSTFILE=load_testing/locustfile.py
set TIMESTAMP=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

echo ============================================================================
echo SCALING TEST SUITE - Django AHSP Application
echo ============================================================================
echo.
echo Target: %HOST%
echo Timestamp: %TIMESTAMP%
echo.
echo IMPORTANT: Make sure Django development server is running!
echo   python manage.py runserver
echo.
echo Test Phases:
echo   Phase 2: 30 users (3 min)
echo   Phase 3: 50 users (5 min)
echo   Phase 4: 100 users (5 min)
echo   Phase 5: 200 users (5 min) - STRESS TEST
echo.
echo Total estimated time: 20-25 minutes
echo ============================================================================
echo.

pause

REM Create results directory
if not exist "load_test_results" mkdir "load_test_results"
set RESULTS_DIR=load_test_results\scaling_%TIMESTAMP%
mkdir "%RESULTS_DIR%"

REM ============================================================================
echo.
echo ============================================================================
echo PHASE 2: LIGHT LOAD - 30 Users
echo ============================================================================
echo Configuration:
echo   Users: 30
echo   Spawn Rate: 3/sec
echo   Duration: 180 seconds (3 minutes)
echo.
echo Success Criteria:
echo   - Success rate ^> 99%%
echo   - P95 response time ^< 500ms (non-auth)
echo   - No server errors
echo ============================================================================
echo.

locust -f %LOCUSTFILE% ^
    --headless ^
    -u 30 ^
    -r 3 ^
    -t 180s ^
    --host=%HOST% ^
    --csv=%RESULTS_DIR%/phase2_30users ^
    --html=%RESULTS_DIR%/phase2_30users.html

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Phase 2 failed to complete!
    echo Check if Django server is running.
    goto :error
)

echo.
echo Phase 2 completed! Analyzing results...
echo Results saved to: %RESULTS_DIR%/phase2_30users.*
echo.

REM Check failure rate (simplified check)
echo Press any key to continue to Phase 3, or Ctrl+C to stop and review results...
pause >nul

REM ============================================================================
echo.
echo ============================================================================
echo PHASE 3: MEDIUM LOAD - 50 Users
echo ============================================================================
echo Configuration:
echo   Users: 50
echo   Spawn Rate: 5/sec
echo   Duration: 300 seconds (5 minutes)
echo.
echo Success Criteria:
echo   - Success rate ^> 98%%
echo   - P95 response time ^< 750ms
echo   - Error rate ^< 2%%
echo ============================================================================
echo.

locust -f %LOCUSTFILE% ^
    --headless ^
    -u 50 ^
    -r 5 ^
    -t 300s ^
    --host=%HOST% ^
    --csv=%RESULTS_DIR%/phase3_50users ^
    --html=%RESULTS_DIR%/phase3_50users.html

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Phase 3 failed to complete!
    goto :error
)

echo.
echo Phase 3 completed! Analyzing results...
echo Results saved to: %RESULTS_DIR%/phase3_50users.*
echo.
echo Press any key to continue to Phase 4, or Ctrl+C to stop and review results...
pause >nul

REM ============================================================================
echo.
echo ============================================================================
echo PHASE 4: HEAVY LOAD - 100 Users
echo ============================================================================
echo Configuration:
echo   Users: 100
echo   Spawn Rate: 10/sec
echo   Duration: 300 seconds (5 minutes)
echo.
echo Success Criteria:
echo   - Success rate ^> 95%%
echo   - P95 response time ^< 1000ms
echo   - Some degradation acceptable
echo.
echo Expected: First signs of bottlenecks will appear
echo ============================================================================
echo.

locust -f %LOCUSTFILE% ^
    --headless ^
    -u 100 ^
    -r 10 ^
    -t 300s ^
    --host=%HOST% ^
    --csv=%RESULTS_DIR%/phase4_100users ^
    --html=%RESULTS_DIR%/phase4_100users.html

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Phase 4 failed to complete!
    goto :error
)

echo.
echo Phase 4 completed! Analyzing results...
echo Results saved to: %RESULTS_DIR%/phase4_100users.*
echo.
echo ============================================================================
echo WARNING: Phase 5 is a STRESS TEST (200 users)
echo This may cause significant system load and some failures are expected.
echo ============================================================================
echo.
echo Press any key to continue to Phase 5 STRESS TEST, or Ctrl+C to stop...
pause >nul

REM ============================================================================
echo.
echo ============================================================================
echo PHASE 5: STRESS TEST - 200 Users
echo ============================================================================
echo Configuration:
echo   Users: 200
echo   Spawn Rate: 20/sec
echo   Duration: 300 seconds (5 minutes)
echo.
echo Success Criteria:
echo   - Success rate ^> 90%% (degradation expected)
echo   - System remains responsive (no crash)
echo   - Graceful degradation
echo.
echo Goal: Find the breaking point and identify bottlenecks
echo ============================================================================
echo.

locust -f %LOCUSTFILE% ^
    --headless ^
    -u 200 ^
    -r 20 ^
    -t 300s ^
    --host=%HOST% ^
    --csv=%RESULTS_DIR%/phase5_200users ^
    --html=%RESULTS_DIR%/phase5_200users.html

if %errorlevel% neq 0 (
    echo.
    echo [WARN] Phase 5 experienced issues (expected for stress test)
)

echo.
echo Phase 5 completed!
echo Results saved to: %RESULTS_DIR%/phase5_200users.*
echo.

REM ============================================================================
echo.
echo ============================================================================
echo ALL TESTS COMPLETED!
echo ============================================================================
echo.
echo Results Location: %RESULTS_DIR%
echo.
echo Next Steps:
echo   1. Review HTML reports in the results directory
echo   2. Analyze failure patterns and bottlenecks
echo   3. Check phase*_stats.csv for detailed metrics
echo   4. Compare performance across phases
echo   5. Identify optimization opportunities
echo.
echo Phase Summary:
echo   Phase 2 (30 users):  %RESULTS_DIR%/phase2_30users.html
echo   Phase 3 (50 users):  %RESULTS_DIR%/phase3_50users.html
echo   Phase 4 (100 users): %RESULTS_DIR%/phase4_100users.html
echo   Phase 5 (200 users): %RESULTS_DIR%/phase5_200users.html
echo.
echo Open these HTML files in your browser for visual analysis.
echo ============================================================================
goto :end

:error
echo.
echo ============================================================================
echo TEST SUITE STOPPED DUE TO ERROR
echo ============================================================================
echo.
echo Results saved so far in: %RESULTS_DIR%
echo.
echo Troubleshooting:
echo   1. Check if Django server is running (python manage.py runserver)
echo   2. Review the last HTML report for error details
echo   3. Check Django server logs for errors
echo   4. Verify database connectivity
echo   5. Check system resources (CPU, Memory, Disk)
echo.
echo After fixing issues, you can resume from where you left off by running
echo individual phase commands from this script.
echo ============================================================================

:end
endlocal
pause
