@echo off
title Super Ozono ERP — Iniciando...
color 0A
cls

echo.
echo  =========================================
echo   SUPER OZONO GLOBAL — ERP
echo   Iniciando sistema...
echo  =========================================
echo.

:: ── Backend (FastAPI) ─────────────────────
echo  [1/3] Arrancando backend (FastAPI)...
start "Backend — FastAPI :8000" cmd /k "cd /d "%~dp0backend" && venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

:: Esperar que el backend levante
timeout /t 4 /nobreak > /dev/null

:: ── Frontend (Vite) ───────────────────────
echo  [2/3] Arrancando frontend (Vite)...
start "Frontend — Vite :5173" cmd /k "cd /d "%~dp0frontend" && node node_modules\vite\bin\vite.js --host 0.0.0.0 --port 5173"

:: Esperar que el frontend levante
timeout /t 4 /nobreak > /dev/null

:: ── Navegador ─────────────────────────────
:: Usamos el mismo host que VITE_API_URL (frontend\.env), no "localhost":
:: si el navegador abre por "localhost" pero la API esta en la IP LAN, el
:: navegador los trata como sitios distintos y bloquea la cookie del
:: refresh token (SameSite). Sin frontend\.env, cae de vuelta a localhost.
echo  [3/3] Abriendo navegador...
set "BROWSER_HOST=localhost"
for /f "tokens=2 delims==" %%A in ('findstr /b "VITE_API_URL=" "%~dp0frontend\.env" 2^>nul') do set "API_URL=%%A"
if not defined API_URL goto :skip_host_parse
for /f "tokens=2 delims=/" %%H in ("%API_URL%") do set "HOST_PORT=%%H"
for /f "tokens=1 delims=:" %%I in ("%HOST_PORT%") do set "BROWSER_HOST=%%I"
:skip_host_parse
start "" "http://%BROWSER_HOST%:5173"

echo.
echo  =========================================
echo   Sistema iniciado correctamente
echo   Frontend : http://%BROWSER_HOST%:5173
echo   Backend  : http://%BROWSER_HOST%:8000/docs
echo  =========================================
echo.
echo  Cierra las ventanas "Backend" y "Frontend"
echo  para detener el sistema.
echo.
pause
