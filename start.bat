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

:: ── Certificado HTTPS (CA local autofirmada) ──────────
:: Si no existe todavia, se genera una sola vez. La CA (certs\superozono-ca.crt)
:: hay que instalarla como confiable en cada PC cliente (ver DOCUMENTACION.md).
if not exist "%~dp0certs\server.crt" (
    echo  [1/4] Generando certificado HTTPS local ^(primera vez^)...
    "%~dp0backend\venv\Scripts\python.exe" "%~dp0backend\scripts\generate_tls_cert.py"
) else (
    echo  [1/4] Certificado HTTPS ya existe, usando el actual.
)

:: ── Backend (FastAPI) ──────────────────────
echo  [2/4] Arrancando backend (FastAPI, HTTPS)...
start "Backend — FastAPI :8000" cmd /k "cd /d "%~dp0backend" && venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile "%~dp0certs\server.key" --ssl-certfile "%~dp0certs\server.crt""

:: Esperar que el backend levante
timeout /t 4 /nobreak > nul

:: ── Frontend (Vite) ────────────────────────
echo  [3/4] Arrancando frontend (Vite, HTTPS)...
start "Frontend — Vite :5173" cmd /k "cd /d "%~dp0frontend" && node node_modules\vite\bin\vite.js --host 0.0.0.0 --port 5173"

:: Esperar que el frontend levante
timeout /t 4 /nobreak > nul

:: ── Navegador ─────────────────────────────
:: Usamos el mismo host que VITE_API_URL (frontend\.env), no "localhost":
:: si el navegador abre por "localhost" pero la API esta en la IP LAN, el
:: navegador los trata como sitios distintos y bloquea la cookie del
:: refresh token (SameSite). Sin frontend\.env, cae de vuelta a localhost.
echo  [4/4] Abriendo navegador...
set "BROWSER_HOST=localhost"
for /f "tokens=2 delims==" %%A in ('findstr /b "VITE_API_URL=" "%~dp0frontend\.env" 2^>nul') do set "API_URL=%%A"
if not defined API_URL goto :skip_host_parse
for /f "tokens=2 delims=/" %%H in ("%API_URL%") do set "HOST_PORT=%%H"
for /f "tokens=1 delims=:" %%I in ("%HOST_PORT%") do set "BROWSER_HOST=%%I"
:skip_host_parse
start "" "https://%BROWSER_HOST%:5173"

echo.
echo  =========================================
echo   Sistema iniciado correctamente
echo   Frontend : https://%BROWSER_HOST%:5173
echo   Backend  : https://%BROWSER_HOST%:8000/docs
echo  =========================================
echo.
echo  Si el navegador muestra "conexion no segura", hay que instalar
echo  certs\superozono-ca.crt como confiable en este PC (una sola vez).
echo  En los otros 4 PCs hay que copiar ese mismo archivo e instalarlo
echo  igual (ver DOCUMENTACION.md, seccion HTTPS).
echo.
echo  Cierra las ventanas "Backend" y "Frontend"
echo  para detener el sistema.
echo.
pause
