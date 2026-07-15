# Copia los backups cifrados a un destino fuera del disco principal (p. ej. OneDrive).
# Uso:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\copy_backups_offsite.ps1
#   powershell ... -File scripts\copy_backups_offsite.ps1 -Dest "D:\Backups\SuperOzono"
#
# No copia claves ni .env. Solo archivos .enc (y carpetas de auditoria si existen).

param(
    [string]$Source = "C:\SuperOzono-Backups",
    [string]$Dest = ""
)

$ErrorActionPreference = "Stop"

if (-not $Dest) {
    $oneDrive = Join-Path $env:USERPROFILE "OneDrive\SuperOzono-Backups-Offsite"
    $Dest = $oneDrive
}

if (-not (Test-Path $Source)) {
    throw "No existe el origen de backups: $Source"
}

New-Item -ItemType Directory -Force -Path $Dest | Out-Null

# Robocopy: /MIR no — solo /E para no borrar destinos antiguos a mano
$args = @(
    $Source,
    $Dest,
    "*.enc",
    "/E",
    "/R:2",
    "/W:3",
    "/NFL",
    "/NDL",
    "/NJH",
    "/NJS"
)
& robocopy @args | Out-Null
$code = $LASTEXITCODE
# robocopy: 0-7 = success-ish
if ($code -ge 8) {
    throw "robocopy failed with exit code $code"
}

$count = (Get-ChildItem -Path $Dest -Recurse -Filter *.enc -ErrorAction SilentlyContinue | Measure-Object).Count
Write-Host "Offsite OK -> $Dest ($count archivo(s) .enc)"
exit 0
