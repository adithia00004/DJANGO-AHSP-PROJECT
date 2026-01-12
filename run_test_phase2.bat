@echo off
REM ============================================================================
REM Load Test with PHASE 2 Additional Endpoints
REM ============================================================================
REM This script runs load test with Phase 1 + Phase 2 additions
REM Total endpoints: ~50 (Phase 1: 35 + Phase 2: 15)
REM ============================================================================

echo ============================================================================
echo LOAD TEST V8 - PHASE 2 ADDITIONAL ENDPOINTS
echo ============================================================================
echo.
echo PHASE 2 Additions (15 new endpoints):
echo.
echo API Endpoints (8 new):
echo   1. /api/project/[id]/parameters/ - Project parameters
echo   2. /api/project/[id]/parameters/[id]/ - Parameter detail
echo   3. /api/project/[id]/conversion-profiles/ - Conversion profiles
echo   4. /api/project/[id]/pekerjaan/[id]/bundle/[id]/expansion/ - Bundle expand
echo   5. /api/v2/project/[id]/pekerjaan/[id]/weekly-progress/ - V2 weekly progress
echo   6. /api/project/[id]/parameters/sync/ - Parameters sync
echo   7. /api/project/[id]/export/template-ahsp/json/ - Template export
echo.
echo Page Views (1 new):
echo   8. /detail_project/[id]/export-test/ - Export test page
echo.
echo Export Operations (6 new):
echo   9. /api/project/[id]/export/full-backup/json/ - Full backup (VERY HEAVY!)
echo   10. /api/project/[id]/export/harga-items/pdf/ - Harga items PDF
echo   11. /api/project/[id]/export/harga-items/xlsx/ - Harga items Excel
echo   12. /api/project/[id]/export/harga-items/word/ - Harga items Word
echo   13. /api/project/[id]/export/harga-items/json/ - Harga items JSON
echo   14. /api/project/[id]/export/jadwal-pekerjaan/csv/ - Jadwal CSV
echo.
echo Expected Coverage Improvement:
echo   Before Phase 2: 35 endpoints (31.1%%)
echo   After Phase 2:  50 endpoints (37.9%%)
echo   Target: 50.8%% (needs Phase 3)
echo.
echo ============================================================================
echo.
echo IMPORTANT: Make sure Django server is running!
echo   python manage.py runserver
echo.
echo Test Configuration:
echo   Users: 10 concurrent
echo   Spawn Rate: 2/sec
echo   Duration: 90 seconds (longer for more endpoints)
echo.
echo Results will be saved as: hasil_test_v8_phase2_*.csv
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
    -t 90s ^
    --host=http://localhost:8000 ^
    --csv=hasil_test_v8_phase2 ^
    --html=hasil_test_v8_phase2.html

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
echo   - hasil_test_v8_phase2_stats.csv
echo   - hasil_test_v8_phase2_failures.csv
echo   - hasil_test_v8_phase2_exceptions.csv
echo   - hasil_test_v8_phase2.html
echo.
echo Next Steps:
echo   1. Review hasil_test_v8_phase2.html in browser
echo   2. Compare with Phase 1 results:
echo      - Phase 1: 35 endpoints, 100%% success
echo      - Phase 2: 50 endpoints, ??%% success
echo   3. Check new endpoints performance:
echo      - Parameters APIs should be ^<200ms
echo      - Conversion profiles ^<300ms
echo      - Export operations (check if any timeout)
echo   4. If all pass, proceed to Phase 3 or scaling tests
echo.
echo Coverage Achievement:
echo   Phase 2 Target: 37.9%% coverage
echo   New endpoint types tested:
echo     - Parameters and configuration
echo     - Conversion profiles
echo     - Bundle expansion
echo     - V2 weekly progress
echo     - Additional export formats
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
echo   4. Some new endpoints may not exist - check Django URLs
echo.
echo ============================================================================

:end
pause
