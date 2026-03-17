@echo off
title NexOS v4 -- Launcher
echo.
echo   =========================================
echo        NexOS v4 -- Launcher
echo        Python Backend + Godot 4 Frontend
echo   =========================================
echo.

:: Aller dans le repertoire du projet
cd /d "%~dp0"

:: Verifier Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   [ERREUR] Python non trouve dans le PATH
    pause
    exit /b 1
)

:: Installer websockets si necessaire
pip show websockets >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   Installation de websockets...
    pip install websockets
)

:: Lancer le backend Python
echo   Demarrage du backend Python...
start /min "NexOS Backend" python nexos_main.py

:: Attendre que le serveur soit pret
echo   Attente du serveur WebSocket (port 5001)...
timeout /t 3 /nobreak >nul

:: Lancer Godot 4 (chercher dans les emplacements courants)
set GODOT_EXE=
if exist "%LOCALAPPDATA%\Godot\Godot_v4*" (
    for /f "delims=" %%G in ('dir /b /s "%LOCALAPPDATA%\Godot\Godot_v4*console.exe" 2^>nul') do set GODOT_EXE=%%G
)
if "%GODOT_EXE%"=="" (
    if exist "C:\Godot\Godot_v4*" (
        for /f "delims=" %%G in ('dir /b /s "C:\Godot\Godot_v4*console.exe" 2^>nul') do set GODOT_EXE=%%G
    )
)
if "%GODOT_EXE%"=="" (
    where godot >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set GODOT_EXE=godot
    )
)

if "%GODOT_EXE%"=="" (
    echo.
    echo   [INFO] Godot 4 non trouve automatiquement.
    echo   Ouvrez le projet manuellement dans Godot :
    echo     %~dp0nexos_godot\project.godot
    echo.
    echo   Le backend Python tourne en arriere-plan.
    echo   Appuyez sur une touche pour fermer ce launcher.
    pause >nul
) else (
    echo   Demarrage de Godot 4 : %GODOT_EXE%
    start "" "%GODOT_EXE%" --path "%~dp0nexos_godot"
    echo.
    echo   NexOS v4 lance !
    echo   Fermez cette fenetre pour arreter le backend.
    pause >nul
)

:: Arreter le backend Python
taskkill /fi "WINDOWTITLE eq NexOS Backend" /f >nul 2>&1
