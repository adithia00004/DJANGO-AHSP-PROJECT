@echo off
REM ============================================================================
REM Load Test with PHASE 4 - Complete Coverage
REM ============================================================================
REM This script runs load test with Phase 1 + Phase 2 + Phase 3 + Phase 4
REM Total endpoints: ~88 (Phase 1-3: 63 + Phase 4: 25)
REM ============================================================================

echo ============================================================================
echo LOAD TEST V10 - PHASE 4 COMPLETE COVERAGE
echo ============================================================================
echo.
echo PHASE 4 Additions (25 new endpoints):
echo.
echo Tahapan Management APIs (6):
echo   1. /api/project/[id]/tahapan/[tahapan_id]/
echo   2. /api/project/[id]/tahapan/unassigned/
echo   3. /api/project/[id]/tahapan/[tahapan_id]/assign/
echo   4. /api/project/[id]/tahapan/[tahapan_id]/unassign/
echo   5. /api/project/[id]/tahapan/reorder/
echo   6. /api/project/[id]/tahapan/validate/
echo.
echo V2 Tahapan APIs (4):
echo   7. /api/v2/project/[id]/assign-weekly/
echo   8. /api/v2/project/[id]/regenerate-tahapan/
echo   9. /api/v2/project/[id]/reset-progress/
echo   10. /api/v2/project/[id]/week-boundary/
echo.
echo Rekap Kebutuhan Variants (2):
echo   11. /api/project/[id]/rekap-kebutuhan-timeline/
echo   12. /api/project/[id]/rekap-kebutuhan/filters/
echo.
echo Orphaned Items (2):
echo   13. /api/project/[id]/orphaned-items/
echo   14. /api/project/[id]/orphaned-items/cleanup/
echo.
echo Monitoring APIs (3):
echo   15. /api/monitoring/performance-metrics/
echo   16. /api/monitoring/deprecation-metrics/
echo   17. /api/monitoring/report-client-metric/
echo.
echo Remaining Exports (8):
echo   18. /api/project/[id]/export/rekap-rab/pdf/
echo   19. /api/project/[id]/export/rincian-ahsp/word/
echo   20. /api/project/[id]/export/rekap-kebutuhan/json/
echo   21. /api/project/[id]/export/rekap-kebutuhan/word/
echo   22. /api/project/[id]/export/jadwal-pekerjaan/pdf/
echo   23. /api/project/[id]/export/volume-pekerjaan/pdf/
echo   24. /api/project/[id]/export/volume-pekerjaan/word/
echo   25. /api/project/[id]/export/volume-pekerjaan/xlsx/
echo.
echo Expected Coverage Improvement:
echo   Before Phase 4: 63 endpoints (47.7%%)
echo   After Phase 4:  88 endpoints (66.7%%)
echo   Target: 70%% (almost there!)
echo.
echo Critical Gaps Filled:
echo   - Tahapan Coverage: 10%% -^> 70%% (+60%%)
echo   - Export Coverage: 67%% -^> 93%% (+26%%)
echo.
echo ============================================================================
echo.
echo IMPORTANT: Make sure Django server is running!
echo   python manage.py runserver
echo.
echo Test Configuration:
echo   Users: 10 concurrent
echo   Spawn Rate: 2/sec
echo   Duration: 150 seconds (2.5 minutes for more endpoints)
echo.
echo Results will be saved as: hasil_test_v10_phase4_*.csv
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
    -t 150s ^
    --host=http://localhost:8000 ^
    --csv=hasil_test_v10_phase4 ^
    --html=hasil_test_v10_phase4.html

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
echo   - hasil_test_v10_phase4_stats.csv
echo   - hasil_test_v10_phase4_failures.csv
echo   - hasil_test_v10_phase4_exceptions.csv
echo   - hasil_test_v10_phase4.html
echo.
echo Next Steps:
echo   1. Review hasil_test_v10_phase4.html in browser
echo   2. Compare with Phase 3 results:
echo      - Phase 3: 63 endpoints, 99.7%% success
echo      - Phase 4: 88 endpoints, ??%% success
echo   3. Check new operations:
echo      - Tahapan management (assign, unassign, validate)
echo      - V2 weekly assignments
echo      - Remaining export formats (PDF, Word, Excel)
echo      - Orphaned items cleanup
echo      - Monitoring APIs
echo   4. Expected 403 errors on write operations (acceptable!)
echo   5. If success rate ^> 95%%, proceed to performance optimization
echo.
echo Coverage Achievement:
echo   Phase 4 Target: 66.7%% coverage (2/3 complete!)
echo   Tahapan coverage: 70%% (critical gap filled!)
echo   Export operations: 93%% (nearly complete!)
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
echo   4. 403 errors on write operations are ACCEPTABLE (expected for non-owners)
echo   5. PDF export timeouts are ACCEPTABLE (very heavy operations)
echo.
echo ============================================================================

:end
pause
