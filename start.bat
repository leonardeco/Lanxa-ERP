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
echo  [3/3] Abriendo navegador...
start "" "http://localhost:5173"

echo.
echo  =========================================
echo   Sistema iniciado correctamente
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8000/docs
echo  =========================================
echo.
echo  Cierra las ventanas "Backend" y "Frontend"
echo  para detener el sistema.
echo.
pause
