@echo off
REM ============================================================================
REM Load Test Runner Script for Windows
REM ============================================================================
REM Usage: run_load_test.bat [light|medium|heavy|stress]
REM ============================================================================

setlocal

set HOST=http://localhost:8000
set LOCUSTFILE=load_testing/locustfile.py
set RESULTS_DIR=load_testing/results

REM Create results directory if not exists
if not exist "%RESULTS_DIR%" mkdir "%RESULTS_DIR%"

REM Get timestamp for results
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "timestamp=%dt:~0,8%_%dt:~8,6%"

REM Parse test level argument
set LEVEL=%1
if "%LEVEL%"=="" set LEVEL=light

if "%LEVEL%"=="light" (
    set USERS=10
    set SPAWN_RATE=2
    set DURATION=60s
) else if "%LEVEL%"=="medium" (
    set USERS=50
    set SPAWN_RATE=5
    set DURATION=300s
) else if "%LEVEL%"=="heavy" (
    set USERS=100
    set SPAWN_RATE=10
    set DURATION=300s
) else if "%LEVEL%"=="stress" (
    set USERS=200
    set SPAWN_RATE=20
    set DURATION=600s
) else (
    echo Unknown level: %LEVEL%
    echo Usage: run_load_test.bat [light^|medium^|heavy^|stress]
    exit /b 1
)

echo ============================================================================
echo LOAD TEST: %LEVEL% level
echo ============================================================================
echo Users: %USERS%
echo Spawn Rate: %SPAWN_RATE%/s
echo Duration: %DURATION%
echo Target: %HOST%
echo Results: %RESULTS_DIR%/%LEVEL%_%timestamp%
echo ============================================================================

REM Run Locust in headless mode
locust -f %LOCUSTFILE% ^
    --headless ^
    -u %USERS% ^
    -r %SPAWN_RATE% ^
    -t %DURATION% ^
    --host=%HOST% ^
    --csv=%RESULTS_DIR%/%LEVEL%_%timestamp% ^
    --html=%RESULTS_DIR%/%LEVEL%_%timestamp%.html

echo.
echo ============================================================================
echo TEST COMPLETED
echo Results saved to: %RESULTS_DIR%/%LEVEL%_%timestamp%
echo ============================================================================

endlocal
