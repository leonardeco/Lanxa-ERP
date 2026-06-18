@echo off
title Super Ozono ERP — Crear acceso directo
echo.
echo  Creando acceso directo en el escritorio...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0crear-acceso-escritorio.ps1"
echo.
echo  Listo. Busca el icono "Super Ozono ERP" en tu escritorio.
echo.
pause
