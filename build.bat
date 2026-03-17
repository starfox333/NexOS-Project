@echo off
echo.
echo  ╔═══════════════════════════════════════╗
echo  ║   NexOS v2 — Build Application        ║
echo  ╚═══════════════════════════════════════╝
echo.

REM Verifier les dependances
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  Installation de PyInstaller...
    pip install pyinstaller
)

echo  Lancement du build...
echo.

python -m PyInstaller --noconfirm NexOS.spec

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERREUR : Build echoue !
    pause
    exit /b 1
)

REM Copier config.yaml dans dist
copy config.yaml "dist\NexOS\_internal\config.yaml" >nul 2>&1

echo.
echo  ╔═══════════════════════════════════════╗
echo  ║  Build OK !                           ║
echo  ║  Exe: dist\NexOS\NexOS.exe            ║
echo  ╚═══════════════════════════════════════╝
echo.
pause
