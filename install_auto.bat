@echo off
REM ============================================================================
REM SCRIPT D'INSTALLATION AUTOMATIQUE - BOT TRADING HYPERLIQUID
REM Windows
REM
REM Ce script effectue TOUTE l'installation en UNE SEULE ACTION
REM ============================================================================

chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo.
echo ================================================================================
echo   🚀 INSTALLATION AUTOMATIQUE - BOT TRADING HYPERLIQUID
echo ================================================================================
echo.

REM Vérification des droits administrateur
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Ce script nécessite les droits administrateur
    echo     Faites un clic droit et sélectionnez "Exécuter en tant qu'administrateur"
    pause
    exit /b 1
)

REM 1. Vérification de Python
echo [ETAPE] Verification de Python...

where python >nul 2>&1
if %errorLevel% neq 0 (
    echo [X] Python n'est pas installe ou pas dans le PATH
    echo.
    echo Veuillez installer Python 3.8+ depuis:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Cochez "Add Python to PATH" lors de l'installation
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% detecte

REM 2. Vérification de pip
echo [ETAPE] Verification de pip...

python -m pip --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [X] pip n'est pas installe
    echo.
    echo Installation de pip...
    python -m ensurepip --default-pip
    if %errorLevel% neq 0 (
        echo [X] Impossible d'installer pip
        pause
        exit /b 1
    )
)

echo [OK] pip disponible

REM 3. Création de l'environnement virtuel
echo [ETAPE] Creation de l'environnement virtuel...

if exist "venv\" (
    echo [!] Environnement virtuel existant detecte
    set /p RECREATE="Voulez-vous le supprimer et le recreer ? (o/N) "
    if /i "!RECREATE!"=="o" (
        rmdir /s /q venv
        echo [OK] Ancien environnement supprime
    )
)

if not exist "venv\" (
    python -m venv venv
    if %errorLevel% neq 0 (
        echo [X] Echec de la creation de l'environnement virtuel
        pause
        exit /b 1
    )
    echo [OK] Environnement virtuel cree
) else (
    echo [OK] Environnement virtuel existant conserve
)

REM 4. Activation de l'environnement virtuel
echo [ETAPE] Activation de l'environnement virtuel...

call venv\Scripts\activate.bat
if %errorLevel% neq 0 (
    echo [X] Echec de l'activation de l'environnement virtuel
    pause
    exit /b 1
)

echo [OK] Environnement virtuel active

REM 5. Mise à jour de pip
echo [ETAPE] Mise a jour de pip...

python -m pip install --upgrade pip setuptools wheel >nul 2>&1
echo [OK] pip mis a jour

REM 6. Installation des dépendances
echo [ETAPE] Installation des dependances Python...

if not exist "requirements.txt" (
    echo [X] Fichier requirements.txt introuvable
    pause
    exit /b 1
)

echo    Cette etape peut prendre plusieurs minutes...
python -m pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo [X] Echec de l'installation des dependances
    echo.
    echo Essayez manuellement:
    echo   venv\Scripts\activate.bat
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

echo [OK] Dependances installees

REM 7. Création des dossiers nécessaires
echo [ETAPE] Creation de la structure des dossiers...

set DIRECTORIES=log doc static templates utils telegram DB command

for %%d in (%DIRECTORIES%) do (
    if not exist "%%d\" (
        mkdir "%%d"
        echo [OK] Dossier %%d cree
    )
)

REM 8. Configuration du fichier .env
echo [ETAPE] Configuration du fichier .env...

if not exist ".env" (
    if exist ".env-template" (
        copy .env-template .env >nul
        echo [OK] Fichier .env cree depuis le template
        echo [!] IMPORTANT: Vous devez editer le fichier .env et configurer:
        echo    - PRIVATE_KEY (votre cle privee Hyperliquid)
        echo    - TELEGRAM_BOT_TOKEN (optionnel)
        echo    - TELEGRAM_CHAT_ID (optionnel)
    ) else (
        echo [X] Fichier .env-template introuvable
        echo.
        echo Creez manuellement le fichier .env avec votre configuration
    )
) else (
    echo [!] Fichier .env existant - conservation
)

REM 9. Test de l'installation
echo [ETAPE] Verification de l'installation...

python utils\diagnostic.py
if %errorLevel% neq 0 (
    echo [!] Le diagnostic a detecte des problemes
    echo.
    echo Consultez les messages ci-dessus pour plus de details
)

REM 10. Récapitulatif
echo.
echo ================================================================================
echo ✅ INSTALLATION TERMINEE !
echo ================================================================================
echo.
echo 📋 PROCHAINES ETAPES:
echo.
echo 1. Editer le fichier .env avec votre configuration:
echo    notepad .env
echo.
echo 2. Configurer votre cle privee Hyperliquid:
echo    PRIVATE_KEY=0xVOTRE_CLE_PRIVEE_ICI
echo.
echo 3. Lancer le bot:
echo    deploy.bat                      # Mode interactif
echo    deploy.bat start mainnet bg     # Mainnet en tache de fond
echo    deploy.bat start testnet fg     # Testnet en temps reel
echo.
echo 4. Verifier le statut du bot:
echo    deploy.bat status
echo.
echo 5. Arreter le bot:
echo    deploy.bat stop
echo.
echo 📚 Documentation complete: README.md
echo 🔧 Diagnostic: python utils\diagnostic.py
echo.
echo ================================================================================
echo.

REM Demander si l'utilisateur veut éditer .env maintenant
set /p EDIT_ENV="Voulez-vous editer le fichier .env maintenant ? (o/N) "
if /i "!EDIT_ENV!"=="o" (
    notepad .env
)

echo [OK] Installation terminee avec succes !
echo.
pause
