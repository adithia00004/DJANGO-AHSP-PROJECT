@echo off
REM AHSP Docker Helper Script - For Windows (PowerShell recommended)
REM Usage: docker-helper.ps1 [command]

REM Colors
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "NC=[0m"

setlocal enabledelayedexpansion

if "%1"=="" (
    call :help
    exit /b 0
)

if "%1"=="build" (
    call :build
) else if "%1"=="up" (
    call :up
) else if "%1"=="down" (
    call :down
) else if "%1"=="restart" (
    call :restart
) else if "%1"=="logs" (
    call :logs %2
) else if "%1"=="migrate" (
    call :migrate
) else if "%1"=="createsuperuser" (
    call :createsuperuser
) else if "%1"=="collectstatic" (
    call :collectstatic
) else if "%1"=="shell" (
    call :shell
) else if "%1"=="bash" (
    call :bash_shell
) else if "%1"=="status" (
    call :status
) else if "%1"=="setup" (
    call :setup
) else if "%1"=="help" (
    call :help
) else (
    echo Unknown command: %1
    call :help
    exit /b 1
)
exit /b 0

:build
echo [93m* Building Docker images...[0m
docker-compose build
echo [92m✓ Build completed[0m
exit /b 0

:up
call :check_env
echo [93m* Starting services...[0m
docker-compose up -d
echo [92m✓ Services started[0m
echo [93m* Waiting for services to be healthy...[0m
timeout /t 5 /nobreak
docker-compose ps
exit /b 0

:down
echo [93m* Stopping services...[0m
docker-compose down
echo [92m✓ Services stopped[0m
exit /b 0

:restart
echo [93m* Restarting services...[0m
docker-compose restart
echo [92m✓ Services restarted[0m
exit /b 0

:logs
set "SERVICE=%2"
if "%SERVICE%"=="" set "SERVICE=web"
docker-compose logs -f %SERVICE%
exit /b 0

:migrate
echo [93m* Running database migrations...[0m
docker-compose exec web python manage.py migrate
echo [92m✓ Migrations completed[0m
exit /b 0

:createsuperuser
echo [93m* Creating superuser...[0m
docker-compose exec web python manage.py createsuperuser
echo [92m✓ Superuser created[0m
exit /b 0

:collectstatic
echo [93m* Collecting static files...[0m
docker-compose exec web python manage.py collectstatic --noinput --clear
echo [92m✓ Static files collected[0m
exit /b 0

:shell
echo [93m* Opening Django shell...[0m
docker-compose exec web python manage.py shell
exit /b 0

:bash_shell
echo [93m* Opening bash shell in web container...[0m
docker-compose exec web bash
exit /b 0

:status
echo [93m* Checking service status...[0m
docker-compose ps
echo.
docker-compose exec web curl -s http://localhost:8000/health/ >nul
if !errorlevel! equ 0 (
    echo [92m✓ Web service is healthy[0m
) else (
    echo [91m✗ Web service is unhealthy[0m
)
exit /b 0

:setup
echo [93m* Running initial setup...[0m
call :check_env
call :build
call :up
call :migrate
call :collectstatic
echo [92m✓ Setup completed! Access app at http://localhost:8000[0m
exit /b 0

:check_env
if not exist .env (
    echo [91m✗ .env file not found![0m
    echo [93m* Creating .env from .env.example...[0m
    copy .env.example .env
    echo [92m✓ .env created. Please edit it with your values.[0m
    exit /b 1
)
exit /b 0

:help
echo AHSP Docker Helper Script for Windows
echo.
echo Usage: docker-helper.bat [command]
echo.
echo Commands:
echo   build             Build Docker images
echo   up                Start all services
echo   down              Stop all services
echo   restart           Restart all services
echo   logs [service]    View service logs (default: web)
echo   migrate           Run database migrations
echo   createsuperuser   Create Django superuser
echo   collectstatic     Collect static files
echo   shell             Open Django shell
echo   bash              Open bash shell in web container
echo   status            Check service status
echo   setup             Initial setup
echo   help              Show this help message
echo.
echo Examples:
echo   docker-helper.bat setup
echo   docker-helper.bat logs web
echo   docker-helper.bat migrate
exit /b 0
