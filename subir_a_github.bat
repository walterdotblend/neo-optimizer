@echo off
title ◈ Subir Neo Optimizer a GitHub
chcp 65001 > nul
cd /d "%~dp0"

echo ========================================================
echo   ◈ NEO•OPTIMIZER // SINCRONIZADOR GITHUB Y GITHUB PAGES
echo ========================================================
echo.
echo Repositorio destino: https://github.com/Zylo-dev1/neo-optimizer
echo.
echo 1. Preparando commits locales...
git add .
git commit -m "feat(release): update Neo Optimizer v3.0 with Tokyo Night rice and GitHub Pages" 2>nul
git branch -M main
git branch -f gh-pages main 2>nul

echo.
echo 2. Subiendo rama principal 'main' a GitHub...
git push -u origin main

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================================
    echo  [AVISO IMPORTANTE DE AUTENTICACION / REPOSITORIO]
    echo ========================================================
    echo  Si ves 'Repository not found':
    echo   1. Asegurate de haber creado el repositorio en tu cuenta:
    echo      https://github.com/new
    echo      Nombre exacto: neo-optimizer
    echo   2. Cuando Git te pida iniciar sesion en el navegador,
    echo      haz clic en 'Sign in with your browser' y autoriza.
    echo.
    pause
    exit /b 1
)

echo.
echo 3. Subiendo rama 'gh-pages' para GitHub Pages...
git push -u origin gh-pages --force

echo.
echo ========================================================
echo  ¡SUBIDA EXITOSA A GITHUB!
echo ========================================================
echo.
echo  Repositorio:
echo    https://github.com/Zylo-dev1/neo-optimizer
echo.
echo  Para activar tu pagina web en GitHub Pages:
echo   1. Entra a: https://github.com/Zylo-dev1/neo-optimizer/settings/pages
echo   2. En 'Build and deployment' -> 'Source':
echo      Elige 'Deploy from a branch'
echo   3. En 'Branch': Elige 'main' y carpeta '/docs' (o rama 'gh-pages')
echo   4. Haz clic en 'Save'.
echo.
echo  Tu pagina estara online en:
echo    https://zylo-dev1.github.io/neo-optimizer/
echo.
pause
