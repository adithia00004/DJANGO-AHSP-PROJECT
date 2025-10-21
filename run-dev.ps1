Param(
  [int]$Port = 8000,
  [switch]$Migrate
)

function Get-LanIPv4 {
  try {
    $ip = Get-NetIPAddress -AddressFamily IPv4 |
      Where-Object { $_.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)' -and $_.PrefixOrigin -ne 'WellKnown' } |
      Sort-Object -Property InterfaceMetric |
      Select-Object -First 1 -ExpandProperty IPAddress
    if (-not $ip) {
      $ipconfig = ipconfig | Select-String -Pattern 'IPv4 Address' | Select-Object -Last 1
      if ($ipconfig) { $ip = ($ipconfig -split ':')[-1].Trim() }
    }
    if (-not $ip) { $ip = '127.0.0.1' }
    return $ip
  } catch { return '127.0.0.1' }
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$ip = Get-LanIPv4

if (-not $env:DJANGO_DEBUG) { $env:DJANGO_DEBUG = "True" }
if (-not $env:DJANGO_ALLOWED_HOSTS) { $env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,$ip" }

Write-Host "Using LAN IP: $ip"
Write-Host "DJANGO_ALLOWED_HOSTS=$env:DJANGO_ALLOWED_HOSTS"

try {
  if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Warning "Python not found in PATH."
  }
} catch {}

if ($Migrate) {
  Write-Host "Running migrations..."
  python manage.py migrate
}

# Try open firewall (best effort; may require admin)
try {
  if (-not (Get-NetFirewallRule -DisplayName "Django Dev $Port" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "Django Dev $Port" -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port | Out-Null
    Write-Host "Firewall rule created for port $Port"
  }
} catch {
  Write-Warning "Could not create firewall rule automatically (need admin?)."
}

Write-Host "Starting server on 0.0.0.0:$Port ..."
python manage.py runserver 0.0.0.0:$Port
