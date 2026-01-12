@echo off
REM ============================================================================
REM Load Test with PHASE 1 Critical Endpoints
REM ============================================================================
REM This script runs load test with 15 newly added critical endpoints
REM ============================================================================

echo ============================================================================
echo LOAD TEST V7 - PHASE 1 CRITICAL ENDPOINTS
echo ============================================================================
echo.
echo PHASE 1 Additions (15 new endpoints):
echo.
echo API Endpoints (9 new):
echo   1. /api/project/[id]/search-ahsp/ - Autocomplete (HIGH FREQUENCY!)
echo   2. /api/project/[id]/pricing/ - Project pricing
echo   3. /api/project/[id]/pekerjaan/[id]/pricing/ - Per-pekerjaan pricing
echo   4. /api/project/[id]/rekap-kebutuhan/validate/ - Data validation
echo   5. /api/project/[id]/rincian-rab/ - NEW rincian RAB API
echo   6. /api/project/[id]/rekap-kebutuhan-enhanced/ - Enhanced rekap
echo   7. /api/v2/project/[id]/kurva-s-harga/ - V2 cost curve
echo   8. /api/v2/project/[id]/rekap-kebutuhan-weekly/ - V2 weekly breakdown
echo   9. /api/project/[id]/audit-trail/ - Change tracking
echo.
echo Page Views (4 new):
echo   10. /detail_project/[id]/rincian-ahsp/ - Detailed AHSP
echo   11. /detail_project/[id]/rekap-kebutuhan/ - Material requirements
echo   12. /detail_project/[id]/rincian-rab/ - NEW RAB details
echo   13. /detail_project/[id]/audit-trail/ - Audit trail page
echo.
echo Write Operations (2 new - DISABLED by default):
echo   14. /api/project/[id]/list-pekerjaan/save/ - Tree save
echo   15. /api/project/[id]/harga-items/save/ - Bulk item save
echo.
echo Expected Coverage Improvement:
echo   Before: 26 endpoints (19.7%%)
echo   After:  41 endpoints (31.1%%)
echo   CRITICAL APIs: 38%% -^> 100%%
echo.
echo ============================================================================
echo.
echo IMPORTANT: Make sure Django server is running!
echo   python manage.py runserver
echo.
echo Test Configuration:
echo   Users: 10 concurrent
echo   Spawn Rate: 2/sec
echo   Duration: 60 seconds
echo.
echo Results will be saved as: hasil_test_v7_phase1_*.csv
echo ============================================================================
echo.

pause

echo.
echo Starting test...
echo.

locust -f load_testing/locustfile.py ^
    --headless ^
    -u 10 ^
    -r 2 ^
    -t 60s ^
    --host=http://localhost:8000 ^
    --csv=hasil_test_v7_phase1 ^
    --html=hasil_test_v7_phase1.html

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Test failed to complete!
    echo Check if Django server is running.
    goto :error
)

echo.
echo ============================================================================
echo TEST COMPLETED!
echo ============================================================================
echo.
echo Results saved:
echo   - hasil_test_v7_phase1_stats.csv
echo   - hasil_test_v7_phase1_failures.csv
echo   - hasil_test_v7_phase1_exceptions.csv
echo   - hasil_test_v7_phase1.html
echo.
echo Next Steps:
echo   1. Review hasil_test_v7_phase1.html in browser
echo   2. Compare with v6 results:
echo      - v6: 26 endpoints, 100%% success
echo      - v7: 41 endpoints, ??%% success
echo   3. Check new critical endpoints performance:
echo      - Search autocomplete should be ^<100ms
echo      - Pricing APIs should be ^<300ms
echo      - V2 APIs performance baseline
echo   4. If all pass, proceed to scaling tests (30-200 users)
echo.
echo Coverage Achievement:
echo   Phase 1 Target: 31.1%% coverage - CHECK!
echo   CRITICAL APIs: 100%% coverage - CHECK!
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
echo   3. Review failures.csv for specific endpoint errors
echo   4. Ensure test projects exist in database
echo.
echo ============================================================================

:end
pause
