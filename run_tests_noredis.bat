@echo off
REM Quick test runner for Windows without Redis
REM TEMPORARY: Use this only for initial testing

echo ============================================================
echo   Quick Test (NO REDIS) - For Initial Testing Only
echo ============================================================
echo.

echo WARNING: This uses in-memory cache (LocMemCache)
echo For production, you MUST install Redis!
echo.
echo See REDIS_WINDOWS_SETUP.md for Redis installation options.
echo.
pause

echo Running tests with temporary cache...
echo.

set DJANGO_SETTINGS_MODULE=config.settings_test_noredis

REM Run Phase 4 tests only
pytest detail_project/tests/test_phase4_infrastructure.py -v --tb=short

echo.
echo ============================================================
echo   Tests Complete!
echo ============================================================
echo.
echo Next steps:
echo 1. Install Redis (see REDIS_WINDOWS_SETUP.md)
echo 2. Run full test suite: pytest detail_project/tests/ -v
echo 3. Run server: python manage.py runserver
echo.
pause
