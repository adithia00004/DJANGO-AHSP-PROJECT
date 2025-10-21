@echo off
title Django Test Server - 192.168.1.164:8000
echo ========================================
echo     DJANGO TEST SERVER LAUNCHER
echo ========================================
echo.

:: Activate virtual environment
call env\Scripts\activate

:: Check for migrations
echo [1/3] Checking migrations...
python manage.py makemigrations --noinput
python manage.py migrate --noinput

:: Collect static files
echo.
echo [2/3] Collecting static files...
python manage.py collectstatic --noinput

:: Display server info
echo.
echo ========================================
echo     SERVER READY!
echo ========================================
echo.
echo   Local Access : http://localhost:8000
echo   LAN Access   : http://192.168.1.164:8000
echo   Admin Panel  : http://192.168.1.164:8000/admin
echo.
echo   Press Ctrl+C to stop server
echo ========================================
echo.

:: Start server
echo [3/3] Starting server...
python manage.py runserver 192.168.1.164:8000