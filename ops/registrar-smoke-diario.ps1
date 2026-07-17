# Registra (o actualiza) una tarea programada de smoke diario en Windows.
# No requiere Admin si la tarea es del usuario actual.
#
#   powershell -ExecutionPolicy Bypass -File ops\registrar-smoke-diario.ps1
#   powershell -ExecutionPolicy Bypass -File ops\registrar-smoke-diario.ps1 -Hour 8 -Minute 30
#   powershell -ExecutionPolicy Bypass -File ops\registrar-smoke-diario.ps1 -Remove

param(
    [int]$Hour = 8,
    [int]$Minute = 0,
    [switch]$Remove,
    [switch]$StrictAlegra
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Bat = Join-Path $Root "ops\smoke-diario.bat"
$TaskName = "SuperOzonoERP-SmokeDiario"
$LogDir = Join-Path $env:USERPROFILE "SuperOzono-Smoke-Logs"
$LogFile = Join-Path $LogDir "smoke-latest.txt"

if (-not (Test-Path $Bat)) {
    Write-Error "No se encontro $Bat"
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Tarea '$TaskName' eliminada (si existia)."
    exit 0
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$args = if ($StrictAlegra) { "--strict-alegra" } else { "" }
# cmd /c bat > log 2>&1
$action = New-ScheduledTaskAction -Execute "cmd.exe" `
    -Argument "/c `"$Bat $args > `"$LogFile`" 2>&1`"" `
    -WorkingDirectory $Root

$trigger = New-ScheduledTaskTrigger -Daily -At (Get-Date -Hour $Hour -Minute $Minute -Second 0)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force | Out-Null

Write-Host "Tarea registrada: $TaskName"
Write-Host "  Hora: cada dia a las $('{0:D2}:{1:D2}' -f $Hour, $Minute)"
Write-Host "  Log:  $LogFile"
Write-Host "  Manual: ops\smoke-diario.bat"
Write-Host ""
Write-Host "Nota: el ERP debe estar corriendo (start.bat) o el smoke fallara."
if ($StrictAlegra) {
    Write-Host "Modo --strict-alegra: falla si no hay token Alegra conectado."
}
