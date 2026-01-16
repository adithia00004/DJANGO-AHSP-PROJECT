@echo off
setlocal

echo ==========================================
echo      MIGRATE LOCAL DATABASE TO DOCKER
echo ==========================================

:: 1. Cek apakah Docker container berjalan
docker ps | findstr "ahsp_web" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Container 'ahsp_web' tidak ditemukan atau tidak berjalan.
    echo Silakan jalankan 'docker-compose up -d' terlebih dahulu.
    exit /b 1
)

:: 2. Dump database lokal
echo.
echo [1/4] Mengekstrak data dari database lokal (dumpdata)...
echo Note: Mengabaikan contenttypes, auth.permission, admin.log, sessions untuk menghindari konflik.
REM Force POSTGRES_HOST to localhost
set POSTGRES_HOST=127.0.0.1
python manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --exclude admin.logentry --exclude sessions.session --indent 2 -o full_export.json
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gagal melakukan dumpdata. Pastikan virtual environment aktif dan database lokal valid.
    exit /b 1
)
echo [OK] Data berhasil diekstrak ke 'full_export.json'.

:: 3. Copy ke container
echo.
echo [2/4] Menyalin file dump ke container Docker...
docker cp full_export.json ahsp_web:/app/full_export.json
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gagal copy file ke docker.
    exit /b 1
)
echo [OK] File disalin.

:: 4. Load data di container
echo.
echo [3/4] Membersihkan database Docker lama (Flush)...
set /p FLUSH_CONFIRM="Apakah Anda yakin ingin MENGHAPUS semua data di Docker sebelum import? (y/n): "
if /i "%FLUSH_CONFIRM%"=="y" (
    docker exec -it ahsp_web python manage.py flush --no-input
    echo [OK] Database Docker dibersihkan.
) else (
    echo [INFO] Skip cleaning. Data akan di-merge (potensi error duplicate key).
)

echo.
echo [4/4] Mengimport data ke Docker (loaddata)...
docker exec -it ahsp_web python manage.py loaddata full_export.json
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Gagal import data. Cek error di atas.
    exit /b 1
)

echo.
echo ==========================================
echo      MIGRASI SELESAI! SUKSES!
echo ==========================================
del full_export.json
echo [INFO] File temporary 'full_export.json' telah dihapus.
pause
