# Arranca staging LAN (API 8010, UI 5180) sin tocar produccion (8000/5173).
# Prerequisito: ops\setup-staging.ps1
# Uso: powershell -ExecutionPolicy Bypass -File ops\start-staging.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$CertKey = Join-Path $Root "certs\server.key"
$CertCrt = Join-Path $Root "certs\server.crt"
$DbStaging = Join-Path $Backend "superozono_staging.db"
$Py = Join-Path $Backend "venv\Scripts\python.exe"

if (-not (Test-Path $DbStaging)) {
    Write-Host "Primero ejecuta setup-staging.ps1" -ForegroundColor Yellow
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "setup-staging.ps1")
}

if (-not (Test-Path $Py)) { throw "No hay venv en backend" }

# Liberar puertos staging si quedaron colgados
foreach ($p in 8010, 5180) {
    Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

$env:DATABASE_URL = "sqlite+aiosqlite:///./superozono_staging.db"
# Preferir .env.staging si existe (uvicorn/app lee .env por defecto; forzamos URL por env)
$envFile = Join-Path $Backend ".env.staging"

Write-Host "Arrancando STAGING API :8010 ..." -ForegroundColor Cyan
$backendArgs = @(
    "-m", "uvicorn", "app.main:app",
    "--host", "127.0.0.1",
    "--port", "8010",
    "--ssl-keyfile", $CertKey,
    "--ssl-certfile", $CertCrt
)
Start-Process -FilePath $Py -ArgumentList $backendArgs -WorkingDirectory $Backend -WindowStyle Normal

Start-Sleep -Seconds 3

Write-Host "Arrancando STAGING UI :5180 ..." -ForegroundColor Cyan
$vite = Join-Path $Frontend "node_modules\vite\bin\vite.js"
# PowerShell 5: Start-Process no soporta -Environment; usamos cmd con set
$cmd = "set VITE_API_URL=https://127.0.0.1:8010/api&& node `"$vite`" --host 127.0.0.1 --port 5180"
Start-Process -FilePath "cmd.exe" -ArgumentList @("/c", $cmd) -WorkingDirectory $Frontend -WindowStyle Normal

Write-Host ""
Write-Host "Staging:" -ForegroundColor Green
Write-Host "  UI  https://127.0.0.1:5180"
Write-Host "  API https://127.0.0.1:8010/health"
Write-Host "Produccion sigue en 5173 / 8000 si estaba encendida."
