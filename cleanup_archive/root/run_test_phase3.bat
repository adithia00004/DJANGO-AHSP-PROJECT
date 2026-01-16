@echo off
REM ============================================================================
REM Load Test with PHASE 3 Export Coverage
REM ============================================================================
REM This script runs load test with Phase 1 + Phase 2 + Phase 3 additions
REM Total endpoints: ~63 (Phase 1: 35 + Phase 2: 15 + Phase 3: 13)
REM ============================================================================

echo ============================================================================
echo LOAD TEST V9 - PHASE 3 EXPORT COVERAGE
echo ============================================================================
echo.
echo PHASE 3 Additions (13 new export operations):
echo.
echo Rekap RAB Exports (3):
echo   1. /api/project/[id]/export/rekap-rab/csv/
echo   2. /api/project/[id]/export/rekap-rab/word/
echo   3. /api/project/[id]/export/rekap-rab/json/
echo.
echo Rincian AHSP Exports (3):
echo   4. /api/project/[id]/export/rincian-ahsp/csv/
echo   5. /api/project/[id]/export/rincian-ahsp/pdf/ (HEAVY!)
echo   6. /api/project/[id]/export/rincian-ahsp/xlsx/
echo.
echo Rekap Kebutuhan Exports (2):
echo   7. /api/project/[id]/export/rekap-kebutuhan/xlsx/
echo   8. /api/project/[id]/export/rekap-kebutuhan/pdf/
echo.
echo Jadwal Exports (2):
echo   9. /api/project/[id]/export/jadwal-pekerjaan/xlsx/
echo   10. /api/project/[id]/export/jadwal-pekerjaan/word/
echo.
echo Other Exports (3):
echo   11. /api/project/[id]/export/list-pekerjaan/json/
echo   12. /api/project/[id]/export/volume-pekerjaan/json/
echo   13. /api/project/[id]/export/template-ahsp/json/ (FIXED!)
echo.
echo Expected Coverage Improvement:
echo   Before Phase 3: 50 endpoints (37.9%%)
echo   After Phase 3:  63 endpoints (47.7%%)
echo   Target: 50.8%% (almost there!)
echo.
echo ============================================================================
echo.
echo IMPORTANT: Make sure Django server is running!
echo   python manage.py runserver
echo.
echo Test Configuration:
echo   Users: 10 concurrent
echo   Spawn Rate: 2/sec
echo   Duration: 120 seconds (longer for more exports)
echo.
echo Results will be saved as: hasil_test_v9_phase3_*.csv
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
    -t 120s ^
    --host=http://localhost:8000 ^
    --csv=hasil_test_v9_phase3 ^
    --html=hasil_test_v9_phase3.html

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
echo   - hasil_test_v9_phase3_stats.csv
echo   - hasil_test_v9_phase3_failures.csv
echo   - hasil_test_v9_phase3_exceptions.csv
echo   - hasil_test_v9_phase3.html
echo.
echo Next Steps:
echo   1. Review hasil_test_v9_phase3.html in browser
echo   2. Compare with Phase 2 results:
echo      - Phase 2: 50 endpoints, 99.6%% success
echo      - Phase 3: 63 endpoints, ??%% success
echo   3. Check new export operations:
echo      - Rekap RAB exports (CSV/Word/JSON)
echo      - Rincian AHSP exports (CSV/PDF/Excel)
echo      - Rekap Kebutuhan exports (Excel/PDF)
echo      - Jadwal exports (Excel/Word)
echo   4. Template export should now work (FIXED!)
echo   5. If all pass, proceed to scaling tests (30-200 users)
echo.
echo Coverage Achievement:
echo   Phase 3 Target: 47.7%% coverage (almost 50%%!)
echo   Export operations: 20/30 (67%% coverage!)
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
echo   4. Export operations may timeout (acceptable for very heavy exports)
echo.
echo ============================================================================

:end
pause
