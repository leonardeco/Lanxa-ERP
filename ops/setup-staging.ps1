# Prepara un entorno de staging LAN en la copia actual del repo.
# No toca producción: solo crea .env.staging y una BD SQLite de staging.
# Uso: powershell -ExecutionPolicy Bypass -File ops\setup-staging.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$EnvStaging = Join-Path $Backend ".env.staging"
$DbProd = Join-Path $Backend "superozono.db"
$DbStaging = Join-Path $Backend "superozono_staging.db"

Write-Host "== Super Ozono — setup staging LAN ==" -ForegroundColor Cyan
Write-Host "Root: $Root"

if (-not (Test-Path $Backend)) {
    Write-Error "No se encuentra backend/ en $Root"
}

# 1) BD staging
if (Test-Path $DbStaging) {
    Write-Host "BD staging ya existe: $DbStaging (no se sobrescribe)"
} elseif (Test-Path $DbProd) {
    Copy-Item $DbProd $DbStaging
    Write-Host "Copiada BD prod -> staging: $DbStaging"
} else {
    Write-Host "No hay superozono.db local; staging arrancara vacia (seed al primer start si aplica)"
}

# 2) .env.staging
if (Test-Path $EnvStaging) {
    Write-Host ".env.staging ya existe (no se sobrescribe)"
} else {
    $EnvProd = Join-Path $Backend ".env"
    $lines = @()
    if (Test-Path $EnvProd) {
        $lines = Get-Content $EnvProd
    }
    $out = New-Object System.Collections.Generic.List[string]
    $hasDb = $false
    $hasCors = $false
    $hasDebug = $false
    foreach ($line in $lines) {
        if ($line -match '^\s*DATABASE_URL\s*=') {
            $out.Add('DATABASE_URL=sqlite+aiosqlite:///./superozono_staging.db')
            $hasDb = $true
        } elseif ($line -match '^\s*CORS_ORIGINS\s*=') {
            $out.Add('CORS_ORIGINS=https://127.0.0.1:5180,https://localhost:5180')
            $hasCors = $true
        } elseif ($line -match '^\s*DEBUG\s*=') {
            $out.Add('DEBUG=true')
            $hasDebug = $true
        } else {
            $out.Add($line)
        }
    }
    if (-not $hasDb) { $out.Insert(0, 'DATABASE_URL=sqlite+aiosqlite:///./superozono_staging.db') }
    if (-not $hasCors) { $out.Add('CORS_ORIGINS=https://127.0.0.1:5180,https://localhost:5180') }
    if (-not $hasDebug) { $out.Add('DEBUG=true') }
    $out | Set-Content -Path $EnvStaging -Encoding UTF8
    Write-Host "Creado $EnvStaging"
}

Write-Host ""
Write-Host "Siguiente: arrancar en puertos 8010 (API) y 5180 (UI). Ver ops\STAGING.md" -ForegroundColor Green
Write-Host "  Backend:  cargar .env.staging o set DATABASE_URL=sqlite+aiosqlite:///./superozono_staging.db"
Write-Host "  uvicorn  --port 8010"
Write-Host "  Vite     --port 5180  VITE_API_URL=https://127.0.0.1:8010/api"
