# Registra tarea diaria de backup PostgreSQL (02:05).
#   powershell -ExecutionPolicy Bypass -File backend\scripts\registrar-backup-pg.ps1
#
# Solo tiene sentido cuando hay Postgres de verdad (DATABASE_URL postgresql
# o variable de usuario PG_BACKUP_DATABASE_URL). Si no, la tarea fallara al correr.

$ErrorActionPreference = "Stop"
$Backend = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Backend "venv\Scripts\python.exe"
$Script = Join-Path $PSScriptRoot "backup_pg.py"
$TaskName = "SuperOzonoERP-BackupPG"

if (-not (Test-Path $Py)) { throw "No existe $Py — crea el venv del backend" }
if (-not (Test-Path $Script)) { throw "No existe $Script" }

$action = New-ScheduledTaskAction -Execute $Py -Argument "`"$Script`"" -WorkingDirectory $Backend
$trigger = New-ScheduledTaskTrigger -Daily -At 2:05am
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Tarea registrada: $TaskName (diario 02:05)"
Write-Host "Probar: Start-ScheduledTask -TaskName $TaskName"
Write-Host "Doc: backend\scripts\BACKUP-POSTGRES.md"
