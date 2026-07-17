@echo off
setlocal
set "ROOT=%~dp0.."
cd /d "%ROOT%"

REM /D fija el directorio; evita comillas rotas con "MI PC"
start "Backend-ERP" /D "%ROOT%\backend" cmd /k "venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile ..\certs\server.key --ssl-certfile ..\certs\server.crt"

start "Frontend-ERP" /D "%ROOT%\frontend" cmd /k "node node_modules\vite\bin\vite.js --host 0.0.0.0 --port 5173"

echo Detached Backend + Frontend launched from:
echo %ROOT%
endlocal
exit /b 0
