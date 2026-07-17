@echo off
cd /d "%~dp0.."
backend\venv\Scripts\python.exe ops\preflight-entrega-7.py
echo.
pause
