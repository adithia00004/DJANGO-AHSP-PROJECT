Param(
  [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

# Resolve paths
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$VenvPath    = Join-Path $ProjectRoot ".venv"

# Detect private LAN IPv4
$ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
  Where-Object { $_.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)' } |
  Select-Object -First 1 -ExpandProperty IPAddress)

if (-not $ip) { Write-Error "Tidak menemukan IP LAN. Pastikan terhubung ke Wi‑Fi." }

Write-Host "LAN IP: $ip"

# Set environment variables for this session
$env:DJANGO_DEBUG = "True"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,$ip"
$env:DJANGO_CSRF_TRUSTED_ORIGINS = "http://$ip:$Port,http://127.0.0.1:$Port"

# Create virtualenv if missing
if (-not (Test-Path $VenvPath)) {
  Write-Host "Membuat virtualenv di $VenvPath"
  Push-Location $ProjectRoot
  python -m venv .venv
  Pop-Location
}

# Activate venv
. (Join-Path $VenvPath "Scripts/Activate.ps1")

# Install deps
Push-Location $ProjectRoot
pip install --upgrade pip
pip install -r requirements.txt

# Migrate database (jika Postgres belum siap, perbarui .env atau jalankan server dulu)
try {
  python manage.py migrate
} catch {
  Write-Warning "Migrate gagal. Pastikan database siap atau gunakan SQLite sementara."
}

Write-Host "Menjalankan server di 0.0.0.0:$Port (akses dari klien: http://$ip:$Port)"
python manage.py runserver 0.0.0.0:$Port
Pop-Location

