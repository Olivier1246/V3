#!/usr/bin/env python3
"""
Script de configuration pour HL-Spot-3.0
Ce script vous aide à configurer votre bot de trading étape par étape.
"""

import os
import re
from pathlib import Path

def print_header():
    print("=" * 80)
    print("🚀 CONFIGURATION HL-SPOT-3.0 BOT DE TRADING")
    print("=" * 80)
    print()

def print_section(title):
    print(f"\n📋 {title}")
    print("-" * (len(title) + 4))

def validate_wallet_address(address):
    """Valide le format d'une adresse de portefeuille"""
    if not address or address == "0x...":
        return False
    return address.startswith("0x") and len(address) == 42

def validate_private_key(key):
    """Valide le format d'une clé privée"""
    if not key or key == "0x...":
        return False
    return key.startswith("0x") and len(key) == 66

def get_user_input(prompt, default="", validator=None, required=True):
    """Obtient une entrée utilisateur avec validation"""
    while True:
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            if not user_input:
                user_input = default
        else:
            user_input = input(f"{prompt}: ").strip()
        
        if not user_input and required:
            print("❌ Cette valeur est requise.")
            continue
        
        if validator and user_input:
            if not validator(user_input):
                print("❌ Format invalide. Veuillez réessayer.")
                continue
        
        return user_input

def setup_api_configuration():
    """Configure les paramètres API"""
    print_section("Configuration API Hyperliquid")
    print("ℹ️  Vous devez fournir vos adresses de portefeuille et clé privée.")
    print("⚠️  IMPORTANT: Gardez ces informations CONFIDENTIELLES!")
    print()
    
    wallet_address = get_user_input(
        "Adresse du portefeuille principal", 
        validator=validate_wallet_address
    )
    
    api_wallet_address = get_user_input(
        "Adresse du portefeuille API (peut être la même)", 
        default=wallet_address,
        validator=validate_wallet_address
    )
    
    private_key = get_user_input(
        "Clé privée de l'agent API", 
        validator=validate_private_key
    )
    
    testnet = get_user_input(
        "Utiliser le testnet? (true/false)", 
        default="true"
    ).lower() == "true"
    
    return {
        'WALLET_ADDRESS': wallet_address,
        'API_WALLET_ADDRESS': api_wallet_address,
        'PRIVATE_KEY': private_key,
        'TESTNET': str(testnet).lower()
    }

def setup_trading_configuration():
    """Configure les paramètres de trading"""
    print_section("Configuration Trading")
    
    symbol = get_user_input("Symbole à trader", default="BTC")
    interval = get_user_input("Intervalle de temps", default="1h")
    
    return {
        'SYMBOL': symbol,
        'INTERVAL': interval
    }

def setup_telegram_configuration():
    """Configure les notifications Telegram"""
    print_section("Configuration Telegram (Optionnel)")
    print("ℹ️  Pour configurer Telegram:")
    print("   1. Contactez @BotFather sur Telegram")
    print("   2. Créez un nouveau bot avec /newbot")
    print("   3. Obtenez votre Chat ID avec @userinfobot")
    print()
    
    telegram_enabled = get_user_input(
        "Activer les notifications Telegram? (true/false)", 
        default="false"
    ).lower() == "true"
    
    config = {'TELEGRAM_ENABLED': str(telegram_enabled).lower()}
    
    if telegram_enabled:
        config['TELEGRAM_BOT_TOKEN'] = get_user_input(
            "Token du bot Telegram", 
            default="YOUR_BOT_TOKEN_HERE"
        )
        config['TELEGRAM_CHAT_ID'] = get_user_input(
            "ID du chat Telegram", 
            default="YOUR_CHAT_ID_HERE"
        )
    else:
        config['TELEGRAM_BOT_TOKEN'] = "YOUR_BOT_TOKEN_HERE"
        config['TELEGRAM_CHAT_ID'] = "YOUR_CHAT_ID_HERE"
    
    return config

def update_env_file(config_updates):
    """Met à jour le fichier .env avec les nouvelles configurations"""
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ Fichier .env introuvable!")
        return False
    
    # Lire le fichier actuel
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Mettre à jour chaque valeur
    for key, value in config_updates.items():
        pattern = f'^{key}=.*$'
        replacement = f'{key}={value}'
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Écrire le fichier mis à jour
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def show_configuration_summary(config):
    """Affiche un résumé de la configuration"""
    print_section("Résumé de la Configuration")
    
    # Masquer les informations sensibles
    sensitive_keys = ['PRIVATE_KEY', 'TELEGRAM_BOT_TOKEN']
    
    for key, value in config.items():
        if key in sensitive_keys and value not in ["0x...", "YOUR_BOT_TOKEN_HERE"]:
            display_value = value[:10] + "..." if len(value) > 10 else "***"
        else:
            display_value = value
        print(f"  {key}: {display_value}")

def main():
    """Fonction principale"""
    print_header()
    
    # Vérifier que nous sommes dans le bon répertoire
    if not Path('.env').exists() and not Path('.env-template').exists():
        print("❌ Erreur: Exécutez ce script dans le répertoire HL-Spot-3.0")
        return
    
    try:
        # Créer .env depuis le template si nécessaire
        if not Path('.env').exists():
            if Path('.env-template').exists():
                import shutil
                shutil.copy('.env-template', '.env')
                print("✅ Fichier .env créé depuis le template")
            else:
                print("❌ Aucun fichier template trouvé")
                return
        
        # Collecter toutes les configurations
        all_config = {}
        
        # Configuration API (obligatoire)
        api_config = setup_api_configuration()
        all_config.update(api_config)
        
        # Configuration Trading
        trading_config = setup_trading_configuration()
        all_config.update(trading_config)
        
        # Configuration Telegram (optionnel)
        telegram_config = setup_telegram_configuration()
        all_config.update(telegram_config)
        
        # Afficher le résumé
        show_configuration_summary(all_config)
        
        # Confirmer la sauvegarde
        print()
        confirm = get_user_input(
            "Sauvegarder cette configuration? (yes/no)", 
            default="yes"
        ).lower()
        
        if confirm in ['yes', 'y', 'oui', 'o']:
            if update_env_file(all_config):
                print("\n✅ Configuration sauvegardée avec succès!")
                print("\n🚀 Vous pouvez maintenant lancer le bot avec:")
                print("   python main.py")
                print("\n⚠️  N'oubliez pas de:")
                print("   - Vérifier vos adresses et clés")
                print("   - Commencer avec le testnet")
                print("   - Surveiller les premiers trades")
            else:
                print("\n❌ Erreur lors de la sauvegarde")
        else:
            print("\n❌ Configuration annulée")
    
    except KeyboardInterrupt:
        print("\n\n❌ Configuration interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")

if __name__ == "__main__":
    main()
