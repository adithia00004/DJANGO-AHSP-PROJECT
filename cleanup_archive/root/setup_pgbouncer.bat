@echo off
REM PgBouncer Setup Script for Windows
REM This script sets up PgBouncer using Docker

echo ========================================
echo PgBouncer Setup for Django AHSP Project
echo ========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop for Windows from:
    echo https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo [1/5] Docker detected successfully
echo.

REM Check if .env file exists
if not exist ".env" (
    if exist ".env.pgbouncer" (
        echo [2/5] Copying .env.pgbouncer to .env
        copy .env.pgbouncer .env
        echo.
        echo IMPORTANT: Please edit .env and set your POSTGRES_PASSWORD
        echo Then run this script again.
        pause
        exit /b 0
    ) else (
        echo ERROR: .env.pgbouncer file not found
        echo Please create .env file with POSTGRES_PASSWORD
        pause
        exit /b 1
    )
)

echo [2/5] Environment file (.env) found
echo.

REM Check if PostgreSQL password is set
findstr /C:"POSTGRES_PASSWORD=your_postgres_password_here" .env >nul
if not errorlevel 1 (
    echo ERROR: Please update POSTGRES_PASSWORD in .env file
    echo It's currently set to the default value
    pause
    exit /b 1
)

echo [3/5] PostgreSQL password configured
echo.

REM Stop existing PgBouncer container if running
echo [4/5] Stopping existing PgBouncer container (if any)...
docker stop ahsp_pgbouncer >nul 2>&1
docker rm ahsp_pgbouncer >nul 2>&1
echo.

REM Start PgBouncer using docker-compose
echo [5/5] Starting PgBouncer container...
docker-compose -f docker-compose-pgbouncer.yml up -d

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start PgBouncer container
    echo Please check the error messages above
    pause
    exit /b 1
)

echo.
echo ========================================
echo PgBouncer Started Successfully!
echo ========================================
echo.
echo PgBouncer is now running on port 6432
echo.
echo Next steps:
echo 1. Set PGBOUNCER_PORT=6432 in your .env file
echo 2. Run: python verify_pgbouncer.py
echo 3. Restart Django: python manage.py runserver
echo.
echo To view PgBouncer logs:
echo   docker logs ahsp_pgbouncer
echo.
echo To stop PgBouncer:
echo   docker-compose -f docker-compose-pgbouncer.yml down
echo.
pause
