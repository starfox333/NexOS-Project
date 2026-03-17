@echo off
title NexOS v4 -- Vie Artificielle Emergente
color 0B
mode con: cols=80 lines=30

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║                                                              ║
echo  ║      ███╗   ██╗███████╗██╗  ██╗ ██████╗ ███████╗            ║
echo  ║      ████╗  ██║██╔════╝╚██╗██╔╝██╔═══██╗██╔════╝            ║
echo  ║      ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗            ║
echo  ║      ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║            ║
echo  ║      ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║            ║
echo  ║      ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝            ║
echo  ║                                                              ║
echo  ║           Vie Artificielle Emergente v4.0                    ║
echo  ║         Moteur : Python 3.11 + Godot 4.6.1                  ║
echo  ║                                                              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

set PROJECT_DIR=%~dp0
set GODOT_EXE=%USERPROFILE%\Desktop\Godot\Godot_v4.6.1-stable_win64.exe
set PYTHON_EXE=python

:: Fallback si Godot pas sur le Bureau
if not exist "%GODOT_EXE%" set GODOT_EXE=C:\Godot\Godot_v4.6.1-stable_win64.exe

echo  [1/3] Demarrage du backend Python...
cd /d "%PROJECT_DIR%"
start /min "NexOS Backend" %PYTHON_EXE% nexos_main.py

echo  [2/3] Attente initialisation serveur (3s)...
timeout /t 3 /nobreak >nul

echo  [3/3] Lancement de Godot 4...
start "" "%GODOT_EXE%" --path "%PROJECT_DIR%nexos_godot"

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║  NexOS est en cours d'execution !                            ║
echo  ║                                                              ║
echo  ║  Backend : http://127.0.0.1:5000                             ║
echo  ║  WebSocket : ws://127.0.0.1:5001                             ║
echo  ║                                                              ║
echo  ║  Appuyez sur une touche pour arreter le backend...           ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.
pause >nul

echo.
echo  Arret du backend Python...
taskkill /fi "WINDOWTITLE eq NexOS Backend" /f >nul 2>&1
taskkill /im python.exe /fi "WINDOWTITLE eq NexOS Backend" >nul 2>&1
echo  NexOS arrete. A bientot dans la Grille !
timeout /t 2 >nul
