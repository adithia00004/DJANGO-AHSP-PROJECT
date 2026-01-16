@echo off
REM ============================================================================
REM Quick Load Test Runner - Version 5 (Fixed URL Prefix)
REM ============================================================================
REM This script runs a quick load test with corrected URL configuration
REM ============================================================================

echo ============================================================================
echo LOAD TEST V5 - URL PREFIX FIX
echo ============================================================================
echo.
echo IMPORTANT: Make sure Django development server is running!
echo   python manage.py runserver
echo.
echo Test Configuration:
echo   - Users: 10 concurrent
echo   - Spawn Rate: 2 users/second
echo   - Duration: 60 seconds
echo   - Target: http://localhost:8000
echo   - Prefix: /detail_project (FIXED - underscore not dash)
echo.
echo Results will be saved as: hasil_test_v5_*.csv
echo ============================================================================
echo.

pause

REM Run Locust in headless mode
locust -f load_testing/locustfile.py ^
    --headless ^
    -u 10 ^
    -r 2 ^
    -t 60s ^
    --host=http://localhost:8000 ^
    --csv=hasil_test_v5 ^
    --html=hasil_test_v5.html

echo.
echo ============================================================================
echo TEST COMPLETED
echo ============================================================================
echo.
echo Results saved:
echo   - hasil_test_v5_stats.csv       (Performance statistics)
echo   - hasil_test_v5_failures.csv    (Failed requests)
echo   - hasil_test_v5_exceptions.csv  (Exceptions)
echo   - hasil_test_v5.html            (HTML report)
echo.
echo Next steps:
echo   1. Check hasil_test_v5_failures.csv for any remaining errors
echo   2. Compare with v4 results to verify improvement
echo   3. Open hasil_test_v5.html for visual report
echo ============================================================================

pause
