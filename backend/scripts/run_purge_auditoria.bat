@echo off
cd /d "%~dp0.."
"%~dp0..\venv\Scripts\python.exe" "%~dp0purge_auditoria.py"
exit /b %ERRORLEVEL%
