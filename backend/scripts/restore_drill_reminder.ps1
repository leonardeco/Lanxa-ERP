# Recordatorio trimestral del drill de restore (#7a).
# No restaura nada solo: abre el checklist y deja un log con fecha.

$ErrorActionPreference = "Stop"
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not (Test-Path (Join-Path $repo "ops\ENTREGA-OPERATIVA-v030.md"))) {
    $repo = "C:\Users\MI PC\Documents\PROYECTOS\superozono-erp"
}

$checklist = Join-Path $repo "ops\ENTREGA-OPERATIVA-v030.md"
$logDir = "C:\SuperOzono-Backups"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$log = Join-Path $logDir "restore_drill_reminder_$stamp.txt"

@(
    "Super Ozono ERP — recordatorio drill de restore"
    "Fecha: $(Get-Date -Format o)"
    ""
    "1) Leer seccion #7a en: $checklist"
    "2) Ejecutar el drill FUERA de horario (stop.bat -> restore_db.py -> verificar)."
    "3) Anotar resultado en la tabla del checklist."
    "4) Confirmar que existen backups en C:\SuperOzono-Backups y en OneDrive offsite."
    ""
    "Backups locales recientes:"
) | Set-Content -Path $log -Encoding UTF8

Get-ChildItem "C:\SuperOzono-Backups\*.enc" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 5 |
    ForEach-Object { Add-Content $log ("  - " + $_.Name + "  " + $_.LastWriteTime) }

if (Test-Path $checklist) {
    Start-Process notepad.exe $checklist
}
Start-Process notepad.exe $log
Write-Host "Reminder written: $log"
