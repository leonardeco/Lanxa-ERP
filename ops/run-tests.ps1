# Run backend tests against local PostgreSQL (Windows).
# Usage:
#   powershell -ExecutionPolicy Bypass -File ops\run-tests.ps1
#   powershell -ExecutionPolicy Bypass -File ops\run-tests.ps1 -NoDb
#   powershell -ExecutionPolicy Bypass -File ops\run-tests.ps1 -PytestArgs "tests/test_main.py -q"
param(
    [switch]$NoDb,
    [string]$PytestArgs = "tests/ -q --tb=line",
    [string]$PgUser = "postgres",
    [string]$PgPassword = "postgres",
    [string]$PgHost = "localhost",
    [int]$PgPort = 5432,
    [string]$TestDb = "superozono_test"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Python = Join-Path $Backend "venv\Scripts\python.exe"
$PsqlCandidates = @(
    "C:\Program Files\PostgreSQL\17\bin\psql.exe",
    "C:\Program Files\PostgreSQL\16\bin\psql.exe",
    "psql"
)

if (-not (Test-Path $Python)) {
    Write-Error "No hay venv en backend\venv. Crea el entorno e instala requirements."
}

if (-not $NoDb) {
    $psql = $PsqlCandidates | Where-Object {
        $_ -eq "psql" -or (Test-Path $_)
    } | Select-Object -First 1
    if (-not $psql) {
        Write-Error "No se encontro psql. Instala PostgreSQL o ajusta la ruta en ops\run-tests.ps1"
    }

    $env:PGPASSWORD = $PgPassword
    $tcp = Test-NetConnection -ComputerName $PgHost -Port $PgPort -WarningAction SilentlyContinue
    if (-not $tcp.TcpTestSucceeded) {
        Write-Host "Puerto $PgPort cerrado. Intentando Start-Service postgresql-x64-17..."
        try { Start-Service postgresql-x64-17 -ErrorAction SilentlyContinue } catch {}
        Start-Sleep -Seconds 2
        $tcp = Test-NetConnection -ComputerName $PgHost -Port $PgPort -WarningAction SilentlyContinue
        if (-not $tcp.TcpTestSucceeded) {
            Write-Error "PostgreSQL no responde en ${PgHost}:$PgPort. Ver ops\TESTES-LOCAL-POSTGRES.md"
        }
    }

    # Crear BD de test si no existe
    $exists = & $psql -U $PgUser -h $PgHost -p $PgPort -tAc "SELECT 1 FROM pg_database WHERE datname='$TestDb'" 2>$null
    if ($exists -ne "1") {
        Write-Host "Creando base $TestDb..."
        & $psql -U $PgUser -h $PgHost -p $PgPort -c "CREATE DATABASE $TestDb;"
    }

    $url = "postgresql+asyncpg://${PgUser}:${PgPassword}@${PgHost}:${PgPort}/$TestDb"
    $env:TEST_DATABASE_URL = $url
    $env:DATABASE_URL = $url
    Write-Host "TEST_DATABASE_URL -> $TestDb @ ${PgHost}:$PgPort"
} else {
    Write-Host "Modo -NoDb (solo tests @pytest.mark.no_db)"
    $PytestArgs = "tests/ -q -m no_db --tb=line"
}

$env:SECRET_KEY = if ($env:SECRET_KEY) { $env:SECRET_KEY } else { "ci-secret-key-solo-para-tests-0123456789abcdef" }
$env:SEED_ADMIN_PASSWORD = if ($env:SEED_ADMIN_PASSWORD) { $env:SEED_ADMIN_PASSWORD } else { "ci-admin-pass-no-produccion" }

Push-Location $Backend
try {
    $argList = $PytestArgs -split '\s+' | Where-Object { $_ }
    Write-Host "pytest $($argList -join ' ')"
    & $Python -m pytest @argList
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
