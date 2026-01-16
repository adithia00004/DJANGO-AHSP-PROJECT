@echo off
setlocal

:: Format timestamp untuk nama file (YYYYMMDD_HHMM)
set "YEAR=%date:~10,4%"
set "MONTH=%date:~4,2%"
set "DAY=%date:~7,2%"
set "HOUR=%time:~0,2%"
set "MINUTE=%time:~3,2%"
set "TIMESTAMP=%YEAR%%MONTH%%DAY%_%HOUR%%MINUTE%"
set "TIMESTAMP=%TIMESTAMP: =0%"
set "FILENAME=backup_ahsp_docker_%TIMESTAMP%.sql"

echo ==========================================
echo      BACKUP POSTGRESQL DOCKER KE SQL
echo ==========================================
echo.
echo [INFO] Target Container: ahsp_postgres
echo [INFO] Database Name   : ahsp_sni_db (Default)
echo [INFO] Output File     : %FILENAME%
echo.

echo [1/2] Mengecek status container...
docker ps | findstr "ahsp_postgres" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Container 'ahsp_postgres' tidak ditemukan atau mati.
    echo Solusi: Jalankan 'docker-compose up -d db'
    pause
    exit /b 1
)

echo [2/2] Menjalankan pg_dump...
:: -U postgres: User database
:: ahsp_sni_db: Nama database 
:: -c: Clean (drop table before create) - Opsional, aman untuk restore ulang
:: --if-exists: Mencegah error jika drop table tidak ada
docker exec -t ahsp_postgres pg_dump -U postgres --clean --if-exists ahsp_sni_db > "%FILENAME%"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Proses dump gagal. Cek log di atas.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo      BACKUP SELESAI!
echo ==========================================
echo File tersimpan di: %CD%\%FILENAME%
echo.
pause
