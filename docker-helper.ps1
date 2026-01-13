# AHSP Docker Quick Start - PowerShell Version
# For Windows PowerShell users

# Color functions
function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Yellow
}

# Main functions
function Initialize-Project {
    Write-Info "Initializing Docker project..."
    
    if (-not (Test-Path ".env")) {
        Write-Info "Creating .env from .env.example..."
        Copy-Item ".env.example" ".env"
        Write-Success ".env created. Please edit it with your values."
    }
    
    Write-Info "Building Docker images..."
    docker-compose build
    
    Write-Info "Starting services..."
    docker-compose up -d
    
    Start-Sleep -Seconds 5
    
    Write-Info "Running migrations..."
    docker-compose exec web python manage.py migrate
    
    Write-Info "Collecting static files..."
    docker-compose exec web python manage.py collectstatic --noinput --clear
    
    Write-Success "Project initialized! Access at http://localhost:8000"
}

function Start-Services {
    if (-not (Test-Path ".env")) {
        Write-Error ".env file not found!"
        Write-Info "Run: Initialize-Project"
        return
    }
    
    Write-Info "Starting Docker services..."
    docker-compose up -d
    Write-Success "Services started"
    docker-compose ps
}

function Stop-Services {
    Write-Info "Stopping Docker services..."
    docker-compose down
    Write-Success "Services stopped"
}

function View-Logs {
    param([string]$Service = "web")
    docker-compose logs -f $Service
}

function Run-Migrations {
    Write-Info "Running migrations..."
    docker-compose exec web python manage.py migrate
    Write-Success "Migrations completed"
}

function Create-Superuser {
    Write-Info "Creating superuser..."
    docker-compose exec web python manage.py createsuperuser
    Write-Success "Superuser created"
}

function Enter-Django-Shell {
    Write-Info "Opening Django shell..."
    docker-compose exec web python manage.py shell
}

function Enter-Bash {
    Write-Info "Opening bash shell..."
    docker-compose exec web bash
}

function Backup-Database {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backup_file = "backup-$timestamp.sql.gz"
    Write-Info "Backing up database to $backup_file..."
    docker-compose exec db pg_dump -U postgres ahsp_sni_db | gzip | Out-File -FilePath $backup_file -Encoding Byte
    Write-Success "Database backed up to $backup_file"
}

function Check-Services {
    Write-Info "Checking service status..."
    docker-compose ps
    
    Write-Info "Testing connectivity..."
    try {
        $result = docker-compose exec web curl -s http://localhost:8000/health/
        Write-Success "Web service is healthy"
    } catch {
        Write-Error "Web service is unhealthy"
    }
}

# Export functions
Export-ModuleMember -Function @(
    'Initialize-Project',
    'Start-Services',
    'Stop-Services',
    'View-Logs',
    'Run-Migrations',
    'Create-Superuser',
    'Enter-Django-Shell',
    'Enter-Bash',
    'Backup-Database',
    'Check-Services'
)

Write-Host @"
╔════════════════════════════════════════════════════════════════╗
║         AHSP Docker Helper - PowerShell Module Loaded          ║
╚════════════════════════════════════════════════════════════════╝

Available Commands:

  Initialize-Project    - Setup dan start project (recommended for first time)
  Start-Services       - Start all Docker services
  Stop-Services        - Stop all Docker services
  View-Logs [service]  - View service logs (default: web)
  Run-Migrations       - Run Django migrations
  Create-Superuser     - Create Django superuser
  Enter-Django-Shell   - Open Django shell
  Enter-Bash           - Open bash shell in container
  Backup-Database      - Backup PostgreSQL database
  Check-Services       - Check service status

Examples:
  PS> Initialize-Project
  PS> Start-Services
  PS> View-Logs web
  PS> Run-Migrations
  PS> Backup-Database

"@ -ForegroundColor Cyan
