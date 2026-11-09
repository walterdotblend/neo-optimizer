@echo off
title Asistente de Instalacion - Neo Video Optimizer
chcp 65001 > nul
cd /d "%~dp0"

echo ========================================================
echo   ◈ NEO•OPTIMIZER // ASISTENTE DE INSTALACIÓN
echo ========================================================
echo.
echo Iniciando el instalador grafico...
echo.

python installer_gui.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] No se pudo ejecutar el instalador con 'python'.
    echo Intentando con 'py'...
    py installer_gui.py
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERROR CRÍTICO] Python no esta disponible en tu variable PATH o faltan dependencias.
        echo Asegúrate de tener Python 3.10+ y ejecuta:
        echo    pip install customtkinter pillow psutil PyQt6
        echo.
        pause
    )
)
