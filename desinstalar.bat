@echo off
title Desinstalador - Neo Video Optimizer
chcp 65001 > nul

echo ========================================================
echo   ◈ NEO•OPTIMIZER // ASISTENTE DE DESINSTALACIÓN
echo ========================================================
echo.
set /p confirm=¿Deseas eliminar los accesos directos y archivos instalados de Neo Video Optimizer? (S/N): 
if /i not "%confirm%"=="s" (
    echo Desinstalacion cancelada.
    pause
    exit /b
)

set "TARGET_DIR=%LOCALAPPDATA%\NeoVideoOptimizer"
set "DESKTOP_LNK=%USERPROFILE%\Desktop\Neo Video Optimizer.lnk"
set "START_MENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Neo Video Optimizer"

echo.
echo [1/3] Eliminando acceso directo del Escritorio...
if exist "%DESKTOP_LNK%" (
    del /f /q "%DESKTOP_LNK%"
    echo      Acceso directo del Escritorio eliminado.
) else (
    echo      No se encontro acceso directo en el Escritorio.
)

echo.
echo [2/3] Eliminando accesos directos del Menu Inicio...
if exist "%START_MENU_DIR%" (
    rmdir /s /q "%START_MENU_DIR%"
    echo      Carpeta del Menu Inicio eliminada.
) else (
    echo      No se encontro carpeta en el Menu Inicio.
)

echo.
echo [3/3] Eliminando archivos de la aplicacion en LocalAppData...
if exist "%TARGET_DIR%" (
    rmdir /s /q "%TARGET_DIR%"
    echo      Archivos eliminados de %TARGET_DIR%.
) else (
    echo      No se encontro la carpeta de instalacion por defecto.
)

echo.
echo ========================================================
echo  ¡Desinstalacion completada exitosamente!
echo ========================================================
pause
