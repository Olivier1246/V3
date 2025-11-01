#!/bin/bash

################################################################################
# SCRIPT D'INSTALLATION AUTOMATIQUE - BOT TRADING HYPERLIQUID
# Linux / macOS
#
# Ce script effectue TOUTE l'installation en UNE SEULE ACTION
################################################################################

set -e  # Arrêter en cas d'erreur

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "================================================================================"
echo "  🚀 INSTALLATION AUTOMATIQUE - BOT TRADING HYPERLIQUID"
echo "================================================================================"
echo ""

# Fonction pour afficher les messages
print_step() {
    echo -e "${BLUE}[ÉTAPE]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# 1. Vérification de Python
print_step "Vérification de Python..."

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 n'est pas installé"
    echo ""
    echo "Veuillez installer Python 3.8+ depuis:"
    echo "  - Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  - macOS: brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]; }; then
    print_error "Python $PYTHON_VERSION détecté - Version 3.8+ requise"
    exit 1
fi

print_success "Python $PYTHON_VERSION détecté"

# 2. Vérification de pip
print_step "Vérification de pip..."

if ! command -v pip3 &> /dev/null; then
    print_error "pip3 n'est pas installé"
    echo ""
    echo "Installation de pip3..."
    python3 -m ensurepip --default-pip || {
        print_error "Impossible d'installer pip3"
        exit 1
    }
fi

print_success "pip3 disponible"

# 3. Création de l'environnement virtuel
print_step "Création de l'environnement virtuel..."

if [ -d "venv" ]; then
    print_warning "Environnement virtuel existant détecté"
    read -p "Voulez-vous le supprimer et le recréer ? (o/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Oo]$ ]]; then
        rm -rf venv
        print_success "Ancien environnement supprimé"
    fi
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv || {
        print_error "Échec de la création de l'environnement virtuel"
        exit 1
    }
    print_success "Environnement virtuel créé"
else
    print_success "Environnement virtuel existant conservé"
fi

# 4. Activation de l'environnement virtuel
print_step "Activation de l'environnement virtuel..."

source venv/bin/activate || {
    print_error "Échec de l'activation de l'environnement virtuel"
    exit 1
}

print_success "Environnement virtuel activé"

# 5. Mise à jour de pip
print_step "Mise à jour de pip..."

pip install --upgrade pip setuptools wheel > /dev/null 2>&1 || {
    print_warning "Impossible de mettre à jour pip (non critique)"
}

print_success "pip mis à jour"

# 6. Installation des dépendances
print_step "Installation des dépendances Python..."

if [ ! -f "requirements.txt" ]; then
    print_error "Fichier requirements.txt introuvable"
    exit 1
fi

echo "   Cette étape peut prendre plusieurs minutes..."
pip install -r requirements.txt || {
    print_error "Échec de l'installation des dépendances"
    echo ""
    echo "Essayez manuellement:"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
}

print_success "Dépendances installées"

# 7. Création des dossiers nécessaires
print_step "Création de la structure des dossiers..."

DIRECTORIES=(
    "log"
    "doc"
    "static"
    "templates"
    "utils"
    "telegram"
    "DB"
    "command"
)

for dir in "${DIRECTORIES[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_success "Dossier $dir créé"
    fi
done

# 8. Configuration du fichier .env
print_step "Configuration du fichier .env..."

if [ ! -f ".env" ]; then
    if [ -f ".env-template" ]; then
        cp .env-template .env
        print_success "Fichier .env créé depuis le template"
        print_warning "⚠️  IMPORTANT: Vous devez éditer le fichier .env et configurer:"
        echo "   - PRIVATE_KEY (votre clé privée Hyperliquid)"
        echo "   - TELEGRAM_BOT_TOKEN (optionnel)"
        echo "   - TELEGRAM_CHAT_ID (optionnel)"
    else
        print_error "Fichier .env-template introuvable"
        echo ""
        echo "Créez manuellement le fichier .env avec votre configuration"
    fi
else
    print_warning "Fichier .env existant - conservation"
fi

# 9. Rendre les scripts exécutables
print_step "Configuration des permissions..."

chmod +x deploy.sh 2>/dev/null || true
chmod +x run.sh 2>/dev/null || true
chmod +x install_auto.sh 2>/dev/null || true

print_success "Permissions configurées"

# 10. Test de l'installation
print_step "Vérification de l'installation..."

python utils/diagnostic.py || {
    print_warning "Le diagnostic a détecté des problèmes"
    echo ""
    echo "Consultez les messages ci-dessus pour plus de détails"
}

# 11. Récapitulatif
echo ""
echo "================================================================================"
echo -e "${GREEN}✅ INSTALLATION TERMINÉE !${NC}"
echo "================================================================================"
echo ""
echo "📋 PROCHAINES ÉTAPES:"
echo ""
echo "1. Éditer le fichier .env avec votre configuration:"
echo "   ${YELLOW}nano .env${NC}"
echo "   ou"
echo "   ${YELLOW}vim .env${NC}"
echo ""
echo "2. Configurer votre clé privée Hyperliquid:"
echo "   PRIVATE_KEY=0xVOTRE_CLE_PRIVEE_ICI"
echo ""
echo "3. Lancer le bot:"
echo "   ${GREEN}./deploy.sh${NC}                    # Mode interactif"
echo "   ${GREEN}./deploy.sh start mainnet bg${NC}   # Mainnet en tâche de fond"
echo "   ${GREEN}./deploy.sh start testnet fg${NC}   # Testnet en temps réel"
echo ""
echo "4. Vérifier le statut du bot:"
echo "   ${GREEN}./deploy.sh status${NC}"
echo ""
echo "5. Arrêter le bot:"
echo "   ${GREEN}./deploy.sh stop${NC}"
echo ""
echo "📚 Documentation complète: README.md"
echo "🔧 Diagnostic: python utils/diagnostic.py"
echo ""
echo "================================================================================"
echo ""

# Demander si l'utilisateur veut éditer .env maintenant
read -p "Voulez-vous éditer le fichier .env maintenant ? (o/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    if command -v nano &> /dev/null; then
        nano .env
    elif command -v vim &> /dev/null; then
        vim .env
    else
        print_warning "Aucun éditeur de texte trouvé"
        echo "Éditez manuellement le fichier .env"
    fi
fi

print_success "Installation terminée avec succès !"
echo ""
