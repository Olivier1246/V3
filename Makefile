# ==============================================================================
# MAKEFILE - BOT TRADING HYPERLIQUID
# ==============================================================================
# 
# Simplifie l'utilisation du bot avec des commandes courtes
# 
# USAGE:
#   make install           Installation complète
#   make start             Démarrer (mainnet, background)
#   make start-test        Démarrer (testnet, foreground)
#   make stop              Arrêter le bot
#   make restart           Redémarrer le bot
#   make status            Afficher le statut
#   make logs              Suivre les logs
#   make config            Éditer la configuration
#   make diagnostic        Lancer le diagnostic
#   make clean             Nettoyer les fichiers temporaires
#   make help              Afficher cette aide
#
# ==============================================================================

.PHONY: help install start start-test start-prod stop restart status logs config diagnostic clean

# Couleurs pour l'affichage
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

# Variables
DEPLOY_SCRIPT = ./deploy.sh
INSTALL_SCRIPT = ./install_auto.sh
ENV_FILE = .env
LOG_FILE = log/trading.log
DIAGNOSTIC = utils/diagnostic.py

# ==============================================================================
# COMMANDES PRINCIPALES
# ==============================================================================

## help: Afficher cette aide
help:
	@echo ""
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  🤖 BOT TRADING HYPERLIQUID - COMMANDES MAKE$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(GREEN)📦 INSTALLATION$(NC)"
	@echo "  make install           Installation complète du bot"
	@echo ""
	@echo "$(GREEN)🚀 DÉMARRAGE$(NC)"
	@echo "  make start             Démarrer (mainnet, background)"
	@echo "  make start-test        Démarrer (testnet, foreground - pour tests)"
	@echo "  make start-prod        Démarrer (mainnet, background - production)"
	@echo ""
	@echo "$(GREEN)🛑 CONTRÔLE$(NC)"
	@echo "  make stop              Arrêter le bot"
	@echo "  make restart           Redémarrer le bot"
	@echo ""
	@echo "$(GREEN)📊 SURVEILLANCE$(NC)"
	@echo "  make status            Afficher le statut du bot"
	@echo "  make logs              Suivre les logs en temps réel"
	@echo ""
	@echo "$(GREEN)⚙️  CONFIGURATION$(NC)"
	@echo "  make config            Éditer le fichier .env"
	@echo "  make diagnostic        Lancer le diagnostic complet"
	@echo ""
	@echo "$(GREEN)🧹 MAINTENANCE$(NC)"
	@echo "  make clean             Nettoyer les fichiers temporaires"
	@echo "  make clean-all         Réinitialisation complète"
	@echo ""
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════════════════════$(NC)"
	@echo ""

## install: Installation complète
install:
	@echo "$(BLUE)[Installation]$(NC) Lancement de l'installation automatique..."
	@chmod +x $(INSTALL_SCRIPT)
	@$(INSTALL_SCRIPT)

## start: Démarrer le bot (mainnet, background)
start:
	@echo "$(GREEN)[Démarrage]$(NC) Mainnet - Mode background"
	@chmod +x $(DEPLOY_SCRIPT)
	@$(DEPLOY_SCRIPT) start mainnet bg

## start-test: Démarrer en mode test (testnet, foreground)
start-test:
	@echo "$(YELLOW)[Test]$(NC) Testnet - Mode foreground"
	@chmod +x $(DEPLOY_SCRIPT)
	@$(DEPLOY_SCRIPT) start testnet fg

## start-prod: Démarrer en mode production (mainnet, background)
start-prod:
	@echo "$(GREEN)[Production]$(NC) Mainnet - Mode background"
	@chmod +x $(DEPLOY_SCRIPT)
	@$(DEPLOY_SCRIPT) start mainnet bg

## stop: Arrêter le bot
stop:
	@echo "$(RED)[Arrêt]$(NC) Arrêt du bot..."
	@chmod +x $(DEPLOY_SCRIPT)
	@$(DEPLOY_SCRIPT) stop

## restart: Redémarrer le bot
restart:
	@echo "$(BLUE)[Redémarrage]$(NC) Redémarrage du bot..."
	@chmod +x $(DEPLOY_SCRIPT)
	@$(DEPLOY_SCRIPT) restart mainnet bg

## status: Afficher le statut
status:
	@chmod +x $(DEPLOY_SCRIPT)
	@$(DEPLOY_SCRIPT) status

## logs: Suivre les logs en temps réel
logs:
	@chmod +x $(DEPLOY_SCRIPT)
	@$(DEPLOY_SCRIPT) logs

## config: Éditer la configuration
config:
	@echo "$(BLUE)[Configuration]$(NC) Édition du fichier .env..."
	@if command -v nano >/dev/null 2>&1; then \
		nano $(ENV_FILE); \
	elif command -v vim >/dev/null 2>&1; then \
		vim $(ENV_FILE); \
	else \
		echo "$(RED)[Erreur]$(NC) Aucun éditeur de texte trouvé (nano, vim)"; \
		exit 1; \
	fi

## diagnostic: Lancer le diagnostic
diagnostic:
	@echo "$(BLUE)[Diagnostic]$(NC) Vérification de l'installation..."
	@if [ -f "venv/bin/activate" ]; then \
		. venv/bin/activate && python $(DIAGNOSTIC); \
	else \
		python3 $(DIAGNOSTIC); \
	fi

## clean: Nettoyer les fichiers temporaires
clean:
	@echo "$(YELLOW)[Nettoyage]$(NC) Suppression des fichiers temporaires..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@rm -f trading_bot.pid 2>/dev/null || true
	@echo "$(GREEN)[OK]$(NC) Nettoyage terminé"

## clean-all: Réinitialisation complète
clean-all: clean
	@echo "$(RED)[Réinitialisation]$(NC) Suppression complète..."
	@read -p "Voulez-vous vraiment tout supprimer ? (y/N) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -rf venv log/*.log DB/*.db; \
		echo "$(GREEN)[OK]$(NC) Réinitialisation terminée"; \
		echo "$(YELLOW)[Info]$(NC) Exécutez 'make install' pour réinstaller"; \
	else \
		echo "$(YELLOW)[Annulé]$(NC) Réinitialisation annulée"; \
	fi

# ==============================================================================
# COMMANDES AVANCÉES
# ==============================================================================

## dev: Mode développement (testnet, foreground, reload auto)
dev:
	@echo "$(BLUE)[Développement]$(NC) Mode développement activé"
	@chmod +x $(DEPLOY_SCRIPT)
	@$(DEPLOY_SCRIPT) start testnet fg

## prod: Mode production (mainnet, background)
prod: start-prod

## tail: Afficher les dernières lignes du log
tail:
	@if [ -f "$(LOG_FILE)" ]; then \
		tail -50 $(LOG_FILE); \
	else \
		echo "$(RED)[Erreur]$(NC) Fichier de log introuvable"; \
	fi

## watch: Surveiller le statut toutes les 5 secondes
watch:
	@watch -n 5 "$(DEPLOY_SCRIPT) status"

# ==============================================================================
# VÉRIFICATIONS
# ==============================================================================

check-env:
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "$(RED)[Erreur]$(NC) Fichier .env introuvable"; \
		echo "$(YELLOW)[Info]$(NC) Exécutez 'make install' d'abord"; \
		exit 1; \
	fi

check-venv:
	@if [ ! -d "venv" ]; then \
		echo "$(RED)[Erreur]$(NC) Environnement virtuel introuvable"; \
		echo "$(YELLOW)[Info]$(NC) Exécutez 'make install' d'abord"; \
		exit 1; \
	fi

# ==============================================================================
# RACCOURCIS
# ==============================================================================

up: start
down: stop
s: status
l: logs

# ==============================================================================
# INFORMATIONS
# ==============================================================================

info:
	@echo ""
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  📊 INFORMATIONS DU SYSTÈME$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(GREEN)Python:$(NC)"
	@python3 --version 2>/dev/null || echo "  Non installé"
	@echo ""
	@echo "$(GREEN)Environnement virtuel:$(NC)"
	@if [ -d "venv" ]; then \
		echo "  ✅ Présent"; \
	else \
		echo "  ❌ Absent"; \
	fi
	@echo ""
	@echo "$(GREEN)Configuration:$(NC)"
	@if [ -f "$(ENV_FILE)" ]; then \
		echo "  ✅ .env présent"; \
	else \
		echo "  ❌ .env absent"; \
	fi
	@echo ""
	@echo "$(GREEN)Bot:$(NC)"
	@if [ -f "trading_bot.pid" ]; then \
		echo "  🟢 En cours d'exécution"; \
	else \
		echo "  🔴 Arrêté"; \
	fi
	@echo ""
	@echo "$(BLUE)═══════════════════════════════════════════════════════════════════════════════$(NC)"
	@echo ""

# ==============================================================================
# DÉFAUT
# ==============================================================================

.DEFAULT_GOAL := help
