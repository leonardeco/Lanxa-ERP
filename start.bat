@echo off
setlocal EnableExtensions
title Super Ozono ERP — Iniciando...
color 0A
cls

echo.
echo  =========================================
echo   SUPER OZONO GLOBAL — ERP
echo   Iniciando sistema...
echo  =========================================
echo.

cd /d "%~dp0"

:: ── 0) Validar venv ───────────────────────────────────
if not exist "%~dp0backend\venv\Scripts\python.exe" (
    echo  [ERROR] No existe backend\venv. Crea el entorno virtual primero.
    pause
    exit /b 1
)

:: ── 0b) Sincronizar IP LAN + .env UTF-8 + cert ────────
echo  [0/4] Sincronizando IP LAN y certificado...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ops\sync-lan-ip.ps1"
if errorlevel 1 (
    echo  [AVISO] No se pudo sincronizar IP automaticamente. Se intenta igual.
)

:: ── 1) Certificado HTTPS ─────────────────────────────
if not exist "%~dp0certs\server.crt" (
    echo  [1/4] Generando certificado HTTPS local...
    "%~dp0backend\venv\Scripts\python.exe" "%~dp0backend\scripts\generate_tls_cert.py"
) else (
    echo  [1/4] Certificado HTTPS listo.
)

:: ── 1b) Probar que el backend carga .env ─────────────
echo  [1b] Validando configuracion backend...
pushd "%~dp0backend"
"%~dp0backend\venv\Scripts\python.exe" -c "from app.core.config import get_settings; s=get_settings(); print('config OK')" 2>nul
if errorlevel 1 (
    echo.
    echo  [ERROR] backend\.env no se puede leer ^(encoding o variables^).
    echo  Ejecuta: powershell -ExecutionPolicy Bypass -File ops\sync-lan-ip.ps1
    echo  O reescribe backend\.env en UTF-8 sin caracteres raros.
    popd
    pause
    exit /b 1
)
popd

:: ── 2) Backend ───────────────────────────────────────
echo  [2/4] Arrancando backend (FastAPI, HTTPS :8000)...
:: /D + rutas relativas de certs: evita rotura por espacios en "MI PC"
start "Backend-FastAPI" /D "%~dp0backend" cmd /k "venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile ..\certs\server.key --ssl-certfile ..\certs\server.crt"

:: Esperar health (hasta ~40s)
echo  [2b] Esperando backend...
set "READY=0"
for /L %%i in (1,1,20) do (
    timeout /t 2 /nobreak > nul
    "%~dp0backend\venv\Scripts\python.exe" -c "import ssl,urllib.request; ctx=ssl._create_unverified_context(); urllib.request.urlopen('https://127.0.0.1:8000/health', context=ctx, timeout=2); print('ok')" 2>nul | findstr /i ok >nul
    if not errorlevel 1 (
        set "READY=1"
        goto :backend_ready
    )
)
:backend_ready
if "%READY%"=="0" (
    echo  [ERROR] El backend no respondio en :8000.
    echo  Mira la ventana "Backend — FastAPI" por el error.
    pause
    exit /b 1
)
echo  Backend: OK

:: ── 3) Frontend ──────────────────────────────────────
echo  [3/4] Arrancando frontend (Vite, HTTPS :5173)...
where node >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Node.js no esta en el PATH.
    pause
    exit /b 1
)
if not exist "%~dp0frontend\node_modules\vite\bin\vite.js" (
    echo  [ERROR] Falta frontend\node_modules. Ejecuta: cd frontend ^&^& npm install
    pause
    exit /b 1
)
start "Frontend-Vite" /D "%~dp0frontend" cmd /k "node node_modules\vite\bin\vite.js --host 0.0.0.0 --port 5173"
timeout /t 5 /nobreak > nul

:: ── 4) Navegador (misma host que VITE_API_URL) ───────
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
echo   Sistema iniciado
echo   Frontend : https://%BROWSER_HOST%:5173
echo   Backend  : https://%BROWSER_HOST%:8000/health
echo  =========================================
echo.
echo  Smoke: ops\smoke-diario.bat
echo  Si el navegador avisa de certificado: instala certs\superozono-ca.crt
echo  certutil -user -addstore Root certs\superozono-ca.crt
echo.
echo  Cierra las ventanas Backend y Frontend para detener, o stop.bat
echo.
pause
endlocal
