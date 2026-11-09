@echo off
title Subir Neo Optimizer a GitHub
chcp 65001 > nul
cd /d "%~dp0"

echo ========================================================
echo   ◈ NEO•OPTIMIZER // SUBIDA A GITHUB (Zylo-dev1)
echo ========================================================
echo.
echo 1. Preparando cambios y archivos...
git add .
git commit -m "Update Neo Optimizer v3.0" 2>nul
git branch -M main

echo.
echo 2. Subiendo a https://github.com/Zylo-dev1/neo-optimizer ...
echo (Si el repositorio no existe en tu cuenta de GitHub, crealo primero en https://github.com/new con el nombre 'neo-optimizer')
echo.
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo  ¡SUBIDA EXITOSA A GITHUB!
    echo ========================================================
    echo Tu repositorio está disponible en:
    echo    https://github.com/Zylo-dev1/neo-optimizer
) else (
    echo.
    echo ========================================================
    echo  [AVISO / ERROR DE SUBIDA]
    echo ========================================================
    echo Pasos rapidos para solucionarlo:
    echo  1. Ve a https://github.com/new
    echo  2. En Repository name pon: neo-optimizer
    echo  3. Elige Public o Private y haz clic en 'Create repository'
    echo  4. Vuelve a ejecutar este archivo 'subir_a_github.bat'
)
echo.
pause
