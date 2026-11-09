@echo off
title Compilador Portable EXE - Neo Video Optimizer
chcp 65001 > nul
cd /d "%~dp0"

echo ========================================================
echo   ◈ NEO•OPTIMIZER // GENERADOR DE EJECUTABLE STANDALONE
echo ========================================================
echo.
echo Compilando 'gui_app.py' en un unico archivo .exe independiente...
echo Icono embebido: app_icon.ico
echo.

pyinstaller --noconsole --onefile --clean --icon="app_icon.ico" --add-data "app_icon.ico;." --add-data "app_icon.png;." --add-data "down_arrow.png;." --add-data "down_arrow_hover.png;." --name="NeoVideoOptimizer" gui_app.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo  ¡COMPILACIÓN EXITOSA!
    echo ========================================================
    echo Tu ejecutable se encuentra listo en:
    echo    dist\NeoVideoOptimizer.exe
    echo.
    echo Abriendo la carpeta 'dist'...
    explorer dist
) else (
    echo.
    echo [ERROR] La compilacion con PyInstaller ha fallado.
    echo Asegurate de tener instaladas las dependencias:
    echo    pip install pyinstaller PyQt6 psutil
    echo.
)
pause
