#!/usr/bin/env python3
"""
Point d'entrée principal du bot de trading Hyperliquid
Version 3.0 - Architecture Modulaire Réorganisée
"""

import sys
import os
import time
import signal
import threading
from datetime import datetime

# Imports depuis la nouvelle structure
from config import load_config
from DB.database import Database
from command.bot_controller import BotController
from command.web_interface import WebInterface

# Variables globales
bot_instance = None
web_instance = None
shutdown_event = threading.Event()


def signal_handler(sig, frame):
    """Gère l'arrêt propre du bot"""
    print("\n\n⚠️  Signal d'arrêt reçu (Ctrl+C)")
    print("🛑 Arrêt du bot en cours...")
    
    shutdown_event.set()
    
    if bot_instance:
        bot_instance.stop()
    
    if web_instance:
        print("🌐 Arrêt de l'interface web...")
        # Flask s'arrête automatiquement
    
    print("✅ Bot arrêté proprement\n")
    sys.exit(0)


def print_banner():
    """Affiche la bannière de démarrage"""
    print("\n" + "="*60)
    print("🤖 BOT DE TRADING HYPERLIQUID - HL-SPOT V3.0")
    print("="*60)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🏗️  Architecture Modulaire Réorganisée")
    print("="*60 + "\n")


def main():
    """Fonction principale"""
    global bot_instance, web_instance
    
    # Enregistrer le gestionnaire de signaux
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Afficher la bannière
    print_banner()
    
    try:
        # 1. Charger la configuration
        print("📋 Chargement de la configuration...")
        config = load_config()
        print("✅ Configuration chargée\n")
        
        # 2. Initialiser la base de données
        print("🗄️  Initialisation de la base de données...")
        database = Database(config)
        print("✅ Base de données initialisée\n")
        
        # 3. Initialiser le contrôleur du bot
        print("🤖 Initialisation du bot...")
        bot_instance = BotController(config)
        print("✅ Bot initialisé\n")
        
        # 4. Initialiser l'interface web (thread séparé)
        print("🌐 Démarrage de l'interface web...")
        web_instance = WebInterface(config, database, bot_instance)
        web_thread = threading.Thread(
            target=web_instance.run,
            daemon=True,
            name="WebInterface"
        )
        web_thread.start()
        print(f"✅ Interface web démarrée sur {config.addresse}:{config.port}\n")
        
        # 5. Démarrer le bot
        print("🚀 Démarrage du bot de trading...")
        bot_instance.start()
        
        # 6. Attendre l'arrêt
        print("\n" + "="*60)
        print("✅ BOT EN COURS D'EXÉCUTION")
        print("="*60)
        print(f"📊 Dashboard: http://localhost:{config.port}")
        print(f"📝 Logs: {config.log_file}")
        print("🛑 Arrêt: Ctrl+C")
        print("="*60 + "\n")
        
        # Boucle principale
        while not shutdown_event.is_set():
            time.sleep(1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption clavier détectée")
        signal_handler(signal.SIGINT, None)
        
    except Exception as e:
        print(f"\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        
        if bot_instance:
            bot_instance.stop()
        
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        sys.exit(1)
