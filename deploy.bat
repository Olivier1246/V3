@echo off
REM ============================================================================
REM SCRIPT DE DÉPLOIEMENT - BOT TRADING HYPERLIQUID
REM Windows
REM
REM Gère le lancement, l'arrêt et le statut du bot
REM Modes: mainnet/testnet, foreground/background
REM ============================================================================

chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM Configuration
set BOT_NAME=trading_bot
set PID_FILE=%BOT_NAME%.pid
set LOG_FILE=log\trading.log
set PYTHON_SCRIPT=main.py

REM Couleurs (ANSI codes pour Windows 10+)
set "ESC="
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "CYAN=[96m"
set "RESET=[0m"

REM ============================================================================
REM FONCTIONS
REM ============================================================================

:print_header
echo.
echo ================================================================================
echo   🤖 BOT TRADING HYPERLIQUID - DÉPLOIEMENT
echo ================================================================================
echo.
goto :eof

:print_success
echo [OK] %~1
goto :eof

:print_error
echo [X] %~1
goto :eof

:print_warning
echo [!] %~1
goto :eof

:print_info
echo [i] %~1
goto :eof

:is_running
if exist "%PID_FILE%" (
    set /p PID=<"%PID_FILE%"
    tasklist /FI "PID eq !PID!" 2>nul | find "!PID!" >nul
    if !errorLevel! equ 0 (
        exit /b 0
    ) else (
        del /f /q "%PID_FILE%" 2>nul
        exit /b 1
    )
)
exit /b 1

:get_pid
if exist "%PID_FILE%" (
    set /p PID=<"%PID_FILE%"
    echo !PID!
) else (
    echo N/A
)
goto :eof

:show_usage
call :print_header
echo USAGE:
echo   %~nx0 ^<commande^> [mode] [execution]
echo.
echo COMMANDES:
echo   start     Demarrer le bot
echo   stop      Arreter le bot
echo   restart   Redemarrer le bot
echo   status    Afficher le statut
echo   logs      Afficher les logs
echo   help      Afficher cette aide
echo.
echo MODES (pour start/restart):
echo   mainnet   Mode production (defaut)
echo   testnet   Mode test
echo.
echo EXECUTION (pour start/restart):
echo   fg        Foreground (temps reel, console)
echo   bg        Background (tache de fond) (defaut)
echo.
echo EXEMPLES:
echo   %~nx0 start                    # Mainnet en background
echo   %~nx0 start mainnet bg         # Mainnet en background (explicite)
echo   %~nx0 start testnet fg         # Testnet en foreground
echo   %~nx0 start mainnet fg         # Mainnet en foreground
echo   %~nx0 stop                     # Arreter le bot
echo   %~nx0 status                   # Voir le statut
echo   %~nx0 logs                     # Voir les logs
echo.
echo ================================================================================
goto :eof

:start_bot
set MODE=%~1
set EXEC=%~2

if "%MODE%"=="" set MODE=mainnet
if "%EXEC%"=="" set EXEC=bg

REM Vérifier si déjà en cours
call :is_running
if !errorLevel! equ 0 (
    call :get_pid
    call :print_error "Le bot est deja en cours d'execution (PID: !PID!)"
    echo.
    echo Utilisez: %~nx0 stop       pour l'arreter
    echo Ou:       %~nx0 restart    pour le redemarrer
    exit /b 1
)

REM Vérifier l'environnement virtuel
if not exist "venv\" (
    call :print_error "Environnement virtuel non trouve"
    echo.
    echo Executez d'abord: install_auto.bat
    exit /b 1
)

REM Vérifier le fichier .env
if not exist ".env" (
    call :print_error "Fichier .env non trouve"
    echo.
    echo Creez le fichier .env avec votre configuration
    exit /b 1
)

REM Créer le dossier log si nécessaire
if not exist "log\" mkdir log

call :print_header
call :print_info "Mode: %MODE%"
if "%EXEC%"=="fg" (
    call :print_info "Execution: Foreground (temps reel)"
) else (
    call :print_info "Execution: Background (tache de fond)"
)
echo.

REM Activer l'environnement virtuel
call venv\Scripts\activate.bat

REM Configurer l'environnement
if /i "%MODE%"=="testnet" (
    set TESTNET=true
    call :print_info "🧪 Mode TESTNET active"
) else (
    set TESTNET=false
    call :print_info "💰 Mode MAINNET active"
)

REM Démarrer en fonction du mode d'exécution
if "%EXEC%"=="fg" (
    REM Foreground - affichage en temps réel
    call :print_success "Demarrage du bot en mode foreground..."
    echo.
    echo Appuyez sur Ctrl+C pour arreter le bot
    echo.
    echo ================================================================================
    python "%PYTHON_SCRIPT%"
) else (
    REM Background - tâche de fond
    call :print_success "Demarrage du bot en mode background..."
    
    REM Démarrer le bot en arrière-plan avec pythonw
    start /B pythonw "%PYTHON_SCRIPT%" >> "%LOG_FILE%" 2>&1
    
    REM Trouver le PID du processus pythonw
    timeout /t 2 /nobreak >nul
    
    for /f "tokens=2" %%a in ('tasklist ^| findstr pythonw.exe ^| findstr /v findstr') do (
        set LAST_PID=%%a
    )
    
    REM Sauvegarder le PID
    echo !LAST_PID! > "%PID_FILE%"
    
    timeout /t 2 /nobreak >nul
    
    call :is_running
    if !errorLevel! equ 0 (
        call :get_pid
        call :print_success "Bot demarre avec succes"
        call :print_info "PID: !PID!"
        call :print_info "Logs: %LOG_FILE%"
        echo.
        echo Commandes utiles:
        echo   %~nx0 status         Voir le statut
        echo   %~nx0 logs           Voir les logs
        echo   %~nx0 stop           Arreter le bot
    ) else (
        call :print_error "Le bot n'a pas pu demarrer"
        echo.
        echo Consultez les logs: type %LOG_FILE%
        del /f /q "%PID_FILE%" 2>nul
        exit /b 1
    )
)

echo.
echo ================================================================================
goto :eof

:stop_bot
call :print_header

call :is_running
if !errorLevel! neq 0 (
    call :print_warning "Le bot n'est pas en cours d'execution"
    goto :eof
)

call :get_pid
call :print_info "Arret du bot (PID: !PID!)..."

REM Tuer le processus
taskkill /PID !PID! /F >nul 2>&1

REM Attendre et vérifier
timeout /t 2 /nobreak >nul

call :is_running
if !errorLevel! neq 0 (
    del /f /q "%PID_FILE%" 2>nul
    call :print_success "Bot arrete avec succes"
) else (
    call :print_error "Impossible d'arreter le bot"
)

echo.
goto :eof

:restart_bot
set MODE=%~1
set EXEC=%~2

if "%MODE%"=="" set MODE=mainnet
if "%EXEC%"=="" set EXEC=bg

call :print_header
call :print_info "Redemarrage du bot..."
echo.

call :stop_bot
timeout /t 2 /nobreak >nul
call :start_bot "%MODE%" "%EXEC%"
goto :eof

:show_status
call :print_header

call :is_running
if !errorLevel! equ 0 (
    call :get_pid
    
    call :print_success "Le bot est EN COURS D'EXECUTION"
    echo.
    echo 📊 Informations:
    echo   PID: !PID!
    echo   Logs: %LOG_FILE%
    echo.
    
    REM Afficher les informations du processus
    echo 💻 Ressources:
    tasklist /FI "PID eq !PID!" /V 2>nul
    echo.
    
    REM Afficher les dernières lignes du log
    if exist "%LOG_FILE%" (
        echo 📋 Dernieres lignes du log:
        echo ---
        powershell -Command "Get-Content '%LOG_FILE%' -Tail 10"
        echo ---
    )
    
    echo.
    echo Commandes:
    echo   %~nx0 logs     Voir les logs
    echo   %~nx0 stop     Arreter le bot
    
) else (
    call :print_warning "Le bot N'EST PAS en cours d'execution"
    echo.
    echo Pour demarrer le bot:
    echo   %~nx0 start                # Mainnet en background
    echo   %~nx0 start testnet fg     # Testnet en foreground
)

echo.
echo ================================================================================
goto :eof

:show_logs
call :print_header

if not exist "%LOG_FILE%" (
    call :print_error "Fichier de log introuvable: %LOG_FILE%"
    exit /b 1
)

call :print_info "Affichage des logs (appuyez sur Ctrl+C pour quitter)..."
echo.
echo ================================================================================

REM Afficher les logs en continu
powershell -Command "Get-Content '%LOG_FILE%' -Wait -Tail 50"
goto :eof

REM ============================================================================
REM MAIN
REM ============================================================================

set COMMAND=%1
set MODE=%2
set EXEC=%3

if "%COMMAND%"=="" set COMMAND=help

if /i "%COMMAND%"=="start" (
    call :start_bot "%MODE%" "%EXEC%"
) else if /i "%COMMAND%"=="stop" (
    call :stop_bot
) else if /i "%COMMAND%"=="restart" (
    call :restart_bot "%MODE%" "%EXEC%"
) else if /i "%COMMAND%"=="status" (
    call :show_status
) else if /i "%COMMAND%"=="logs" (
    call :show_logs
) else if /i "%COMMAND%"=="help" (
    call :show_usage
) else if /i "%COMMAND%"=="--help" (
    call :show_usage
) else if /i "%COMMAND%"=="-h" (
    call :show_usage
) else (
    call :print_error "Commande inconnue: %COMMAND%"
    echo.
    call :show_usage
    exit /b 1
)

endlocal
