@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0restore_drill_reminder.ps1"
exit /b %ERRORLEVEL%
