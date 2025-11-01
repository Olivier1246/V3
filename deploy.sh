#!/bin/bash

################################################################################
# SCRIPT DE DÉPLOIEMENT - BOT TRADING HYPERLIQUID
# Linux / macOS
#
# Gère le lancement, l'arrêt et le statut du bot
# Modes: mainnet/testnet, foreground/background
################################################################################

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
BOT_NAME="trading_bot"
PID_FILE="$BOT_NAME.pid"
LOG_FILE="log/trading.log"
PYTHON_SCRIPT="main.py"

# Fonctions d'affichage
print_header() {
    echo ""
    echo "================================================================================"
    echo -e "  ${CYAN}🤖 BOT TRADING HYPERLIQUID - DÉPLOIEMENT${NC}"
    echo "================================================================================"
    echo ""
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Fonction pour vérifier si le bot tourne
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # Le bot tourne
        else
            # PID file existe mais processus mort
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Fonction pour obtenir le PID
get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    else
        echo "N/A"
    fi
}

# Fonction pour afficher l'utilisation
show_usage() {
    print_header
    echo "USAGE:"
    echo "  $0 <commande> [mode] [execution]"
    echo ""
    echo "COMMANDES:"
    echo "  start     Démarrer le bot"
    echo "  stop      Arrêter le bot"
    echo "  restart   Redémarrer le bot"
    echo "  status    Afficher le statut"
    echo "  logs      Afficher les logs en temps réel"
    echo "  help      Afficher cette aide"
    echo ""
    echo "MODES (pour start/restart):"
    echo "  mainnet   Mode production (défaut)"
    echo "  testnet   Mode test"
    echo ""
    echo "EXÉCUTION (pour start/restart):"
    echo "  fg        Foreground (temps réel, console)"
    echo "  bg        Background (tâche de fond) (défaut)"
    echo ""
    echo "EXEMPLES:"
    echo "  $0 start                    # Mainnet en background"
    echo "  $0 start mainnet bg         # Mainnet en background (explicite)"
    echo "  $0 start testnet fg         # Testnet en foreground"
    echo "  $0 start mainnet fg         # Mainnet en foreground"
    echo "  $0 stop                     # Arrêter le bot"
    echo "  $0 status                   # Voir le statut"
    echo "  $0 logs                     # Suivre les logs"
    echo ""
    echo "================================================================================"
}

# Fonction pour démarrer le bot
start_bot() {
    local MODE=${1:-mainnet}
    local EXEC=${2:-bg}
    
    # Vérifier si déjà en cours
    if is_running; then
        print_error "Le bot est déjà en cours d'exécution (PID: $(get_pid))"
        echo ""
        echo "Utilisez: $0 stop       pour l'arrêter"
        echo "Ou:       $0 restart    pour le redémarrer"
        return 1
    fi
    
    # Vérifier l'environnement virtuel
    if [ ! -d "venv" ]; then
        print_error "Environnement virtuel non trouvé"
        echo ""
        echo "Exécutez d'abord: ./install_auto.sh"
        return 1
    fi
    
    # Vérifier le fichier .env
    if [ ! -f ".env" ]; then
        print_error "Fichier .env non trouvé"
        echo ""
        echo "Créez le fichier .env avec votre configuration"
        return 1
    fi
    
    # Créer le dossier log si nécessaire
    mkdir -p log
    
    print_header
    print_info "Mode: $MODE"
    print_info "Exécution: $([ "$EXEC" = "fg" ] && echo "Foreground (temps réel)" || echo "Background (tâche de fond)")"
    echo ""
    
    # Activer l'environnement virtuel
    source venv/bin/activate
    
    # Configurer l'environnement
    if [ "$MODE" = "testnet" ]; then
        export TESTNET=true
        print_info "🧪 Mode TESTNET activé"
    else
        export TESTNET=false
        print_info "💰 Mode MAINNET activé"
    fi
    
    # Démarrer en fonction du mode d'exécution
    if [ "$EXEC" = "fg" ]; then
        # Foreground - affichage en temps réel
        print_success "Démarrage du bot en mode foreground..."
        echo ""
        echo "Appuyez sur Ctrl+C pour arrêter le bot"
        echo ""
        echo "================================================================================"
        python "$PYTHON_SCRIPT"
    else
        # Background - tâche de fond
        print_success "Démarrage du bot en mode background..."
        
        # Démarrer le bot en arrière-plan
        nohup python "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1 &
        
        # Sauvegarder le PID
        echo $! > "$PID_FILE"
        
        sleep 2
        
        if is_running; then
            print_success "Bot démarré avec succès"
            print_info "PID: $(get_pid)"
            print_info "Logs: $LOG_FILE"
            echo ""
            echo "Commandes utiles:"
            echo "  $0 status         Voir le statut"
            echo "  $0 logs           Suivre les logs"
            echo "  $0 stop           Arrêter le bot"
        else
            print_error "Le bot n'a pas pu démarrer"
            echo ""
            echo "Consultez les logs: tail -f $LOG_FILE"
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    
    echo ""
    echo "================================================================================"
}

# Fonction pour arrêter le bot
stop_bot() {
    print_header
    
    if ! is_running; then
        print_warning "Le bot n'est pas en cours d'exécution"
        return 0
    fi
    
    local PID=$(get_pid)
    print_info "Arrêt du bot (PID: $PID)..."
    
    # Envoyer SIGTERM
    kill "$PID" 2>/dev/null || true
    
    # Attendre jusqu'à 10 secondes
    local count=0
    while [ $count -lt 10 ]; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            rm -f "$PID_FILE"
            print_success "Bot arrêté avec succès"
            echo ""
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    
    # Si toujours en cours, forcer l'arrêt
    print_warning "Arrêt forcé du bot..."
    kill -9 "$PID" 2>/dev/null || true
    rm -f "$PID_FILE"
    print_success "Bot arrêté (forcé)"
    echo ""
}

# Fonction pour redémarrer le bot
restart_bot() {
    local MODE=${1:-mainnet}
    local EXEC=${2:-bg}
    
    print_header
    print_info "Redémarrage du bot..."
    echo ""
    
    stop_bot
    sleep 2
    start_bot "$MODE" "$EXEC"
}

# Fonction pour afficher le statut
show_status() {
    print_header
    
    if is_running; then
        local PID=$(get_pid)
        
        print_success "Le bot est EN COURS D'EXÉCUTION"
        echo ""
        echo "📊 Informations:"
        echo "  PID: $PID"
        echo "  Logs: $LOG_FILE"
        echo ""
        
        # Afficher l'utilisation mémoire et CPU
        if command -v ps &> /dev/null; then
            echo "💻 Ressources:"
            ps -p "$PID" -o pid,ppid,%cpu,%mem,etime,cmd 2>/dev/null || true
            echo ""
        fi
        
        # Afficher les dernières lignes du log
        if [ -f "$LOG_FILE" ]; then
            echo "📋 Dernières lignes du log:"
            echo "---"
            tail -10 "$LOG_FILE"
            echo "---"
        fi
        
        echo ""
        echo "Commandes:"
        echo "  $0 logs     Suivre les logs en temps réel"
        echo "  $0 stop     Arrêter le bot"
        
    else
        print_warning "Le bot N'EST PAS en cours d'exécution"
        echo ""
        echo "Pour démarrer le bot:"
        echo "  $0 start                # Mainnet en background"
        echo "  $0 start testnet fg     # Testnet en foreground"
    fi
    
    echo ""
    echo "================================================================================"
}

# Fonction pour suivre les logs
follow_logs() {
    print_header
    
    if [ ! -f "$LOG_FILE" ]; then
        print_error "Fichier de log introuvable: $LOG_FILE"
        return 1
    fi
    
    print_info "Suivi des logs en temps réel (Ctrl+C pour quitter)..."
    echo ""
    echo "================================================================================"
    tail -f "$LOG_FILE"
}

# Fonction principale
main() {
    local COMMAND=${1:-help}
    local MODE=${2:-mainnet}
    local EXEC=${3:-bg}
    
    case "$COMMAND" in
        start)
            start_bot "$MODE" "$EXEC"
            ;;
        stop)
            stop_bot
            ;;
        restart)
            restart_bot "$MODE" "$EXEC"
            ;;
        status)
            show_status
            ;;
        logs)
            follow_logs
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Commande inconnue: $COMMAND"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Exécution
main "$@"
