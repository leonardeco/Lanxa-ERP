@echo off
REM Smoke diario Super Ozono ERP (doble clic o Task Scheduler)
setlocal
cd /d "%~dp0.."
if not exist "backend\venv\Scripts\python.exe" (
  echo FAIL: no hay venv en backend\venv
  exit /b 1
)
backend\venv\Scripts\python.exe ops\smoke-prod.py %*
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo.
  echo SMOKE FALLO. Si el ERP no esta arriba: start.bat
  exit /b %ERR%
)
exit /b 0
