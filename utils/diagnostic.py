#!/usr/bin/env python3
"""
Script de diagnostic pour le bot de trading Hyperliquid
Vérifie l'installation et la configuration

🆕 VERSION 3.0 - Architecture Modulaire
Vérifie aussi buy_orders.py et sell_orders.py
"""

import os
import sys

def print_header(text):
    """Affiche un en-tête"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_check(condition, success_msg, error_msg):
    """Affiche le résultat d'une vérification"""
    if condition:
        print(f"✅ {success_msg}")
        return True
    else:
        print(f"❌ {error_msg}")
        return False

def check_python_version():
    """Vérifie la version de Python"""
    version = sys.version_info
    is_valid = version.major == 3 and version.minor >= 8
    return print_check(
        is_valid,
        f"Python {version.major}.{version.minor}.{version.micro} detecte",
        f"Python {version.major}.{version.minor}.{version.micro} - Version 3.8+ requise"
    )

def check_files():
    """Vérifie la présence des fichiers nécessaires"""
    print_header("Verification des fichiers")
    
    required_files = [
        'main.py',
        'config.py',
        'bot_controller.py',
        'trading_engine.py',
        'market_analyzer.py',
        'database.py',
        'logger.py',
        'web_interface.py',
        'requirements.txt',
        '.env'
    ]
    
    # 🆕 NOUVEAUX MODULES
    new_modules = [
        'buy_orders.py',
        'sell_orders.py'
    ]
    
    all_present = True
    
    # Fichiers requis
    for file in required_files:
        exists = os.path.isfile(file)
        all_present = all_present and print_check(
            exists,
            f"{file} present",
            f"{file} MANQUANT"
        )
    
    # Nouveaux modules (optionnels mais recommandés)
    for file in new_modules:
        exists = os.path.isfile(file)
        if exists:
            print_check(True, f"🆕 {file} present (Architecture modulaire)", "")
        else:
            print_check(False, "", f"⚠️  {file} MANQUANT (recommandé pour architecture modulaire)")
    
    # Vérifier le dossier templates
    templates_exists = os.path.isdir('templates')
    all_present = all_present and print_check(
        templates_exists,
        "Dossier templates/ present",
        "Dossier templates/ MANQUANT"
    )
    
    if templates_exists:
        dashboard_exists = os.path.isfile('templates/index.html')
        all_present = all_present and print_check(
            dashboard_exists,
            "templates/index.html present",
            "templates/index.html MANQUANT"
        )
    
    return all_present

def check_venv():
    """Vérifie l'environnement virtuel"""
    print_header("Verification de l'environnement virtuel")
    
    venv_exists = os.path.isdir('venv')
    return print_check(
        venv_exists,
        "Environnement virtuel 'venv' trouve",
        "Environnement virtuel 'venv' NON TROUVE - Executez install.sh/install.bat"
    )

def check_dependencies():
    """Vérifie les dépendances Python"""
    print_header("Verification des dependances")
    
    dependencies = [
        'hyperliquid',
        'dotenv',
        'requests',
        'flask',
        'sqlalchemy',
        'pandas',
        'numpy',
        'eth_account'
    ]
    
    all_installed = True
    for dep in dependencies:
        try:
            if dep == 'dotenv':
                __import__('dotenv')
            elif dep == 'hyperliquid':
                __import__('hyperliquid')
            else:
                __import__(dep)
            print_check(True, f"{dep} installe", "")
        except ImportError:
            all_installed = False
            print_check(False, "", f"{dep} NON INSTALLE")
    
    return all_installed

def check_config():
    """Vérifie la configuration"""
    print_header("Verification de la configuration")
    
    if not os.path.isfile('.env'):
        print_check(False, "", "Fichier .env NON TROUVE")
        return False
    
    all_valid = True
    
    # Charger la config avec le module config
    try:
        from config import load_config
        config = load_config()
        
        # Vérifier PRIVATE_KEY
        has_valid_key = (
            config.private_key and 
            config.private_key.startswith('0x') and
            'VOTRE_CLE_PRIVEE_ICI' not in config.private_key and
            len(config.private_key) == 66
        )
        all_valid = all_valid and print_check(
            has_valid_key,
            f"PRIVATE_KEY configuree (longueur: {len(config.private_key) if config.private_key else 0})",
            "PRIVATE_KEY NON CONFIGUREE ou INVALIDE - Doit commencer par 0x et faire 66 caracteres"
        )
        
        # Vérifier les paramètres de base
        required_checks = [
            (config.symbol, "SYMBOL"),
            (config.interval, "INTERVAL"),
            (config.base_url, "BASE_URL"),
            (config.port > 0, "PORT")
        ]
        
        for check, param_name in required_checks:
            all_valid = all_valid and print_check(
                check,
                f"{param_name} configure",
                f"{param_name} MANQUANT ou INVALIDE"
            )
        
        # 🆕 Vérifier les nouveaux paramètres
        print("\n🆕 Nouveaux paramètres (Architecture Modulaire):")
        new_params = [
            (hasattr(config, 'buy_enabled'), "BUY_ENABLED"),
            (hasattr(config, 'sell_enabled'), "SELL_ENABLED"),
            (hasattr(config, 'min_order_value_usdc'), "MIN_ORDER_VALUE_USDC"),
            (hasattr(config, 'range_dynamic_percent'), "RANGE_DYNAMIC_PERCENT")
        ]
        
        for check, param_name in new_params:
            if check:
                print_check(True, f"  {param_name} present", "")
            else:
                print_check(False, "", f"  {param_name} MANQUANT (ajoutez-le au .env)")
        
    except Exception as e:
        print_check(False, "", f"Erreur lors du chargement de la config: {str(e)[:100]}")
        return False
    
    return all_valid

def check_database_permissions():
    """Vérifie les permissions d'écriture"""
    print_header("Verification des permissions")
    
    try:
        test_file = 'test_write_permission.tmp'
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        return print_check(
            True,
            "Permissions d'ecriture OK",
            ""
        )
    except:
        return print_check(
            False,
            "",
            "Permissions d'ecriture INSUFFISANTES"
        )

def test_imports():
    """Test des imports Python"""
    print_header("Test des imports")
    
    all_ok = True
    
    # Modules principaux
    modules = [
        ('config', 'load_config'),
        ('database', 'Database'),
        ('market_analyzer', 'MarketAnalyzer'),
        ('trading_engine', 'TradingEngine'),
        ('logger', 'TradingLogger'),
        ('bot_controller', 'BotController'),
        ('web_interface', 'WebInterface')
    ]
    
    for module, cls in modules:
        try:
            exec(f"from {module} import {cls}")
            print_check(True, f"Import {module}.{cls} OK", "")
        except Exception as e:
            all_ok = False
            error_msg = str(e)[:80]
            print_check(False, "", f"Import {module}.{cls} ECHOUE: {error_msg}")
    
    # 🆕 Nouveaux modules
    print("\n🆕 Nouveaux modules (Architecture Modulaire):")
    new_modules = [
        ('buy_orders', 'BuyOrderManager'),
        ('sell_orders', 'SellOrderManager')
    ]
    
    for module, cls in new_modules:
        try:
            exec(f"from {module} import {cls}")
            print_check(True, f"  Import {module}.{cls} OK", "")
        except Exception as e:
            # Ne pas marquer comme erreur critique si les nouveaux modules sont absents
            error_msg = str(e)[:80]
            print(f"⚠️   Import {module}.{cls} ECHOUE: {error_msg}")
            print(f"      💡 Ajoutez {module}.py pour utiliser l'architecture modulaire")
    
    return all_ok

def test_new_architecture():
    """Teste la nouvelle architecture modulaire"""
    print_header("Test Architecture Modulaire (Optionnel)")
    
    has_new_arch = True
    
    # Vérifier fichiers
    if not os.path.isfile('buy_orders.py'):
        print("⚠️   buy_orders.py absent")
        has_new_arch = False
    
    if not os.path.isfile('sell_orders.py'):
        print("⚠️   sell_orders.py absent")
        has_new_arch = False
    
    if has_new_arch:
        try:
            from command.buy_orders import BuyOrderManager
            from command.sell_orders import SellOrderManager
            print_check(True, "Architecture modulaire disponible", "")
            print("\n💡 Avantages:")
            print("   • Ordres d'achat et vente séparés")
            print("   • Toutes variables dans .env")
            print("   • Contrôle granulaire par marché")
            return True
        except Exception as e:
            print_check(False, "", f"Erreur import modules: {str(e)[:80]}")
            return False
    else:
        print("\n💡 Pour activer l'architecture modulaire:")
        print("   1. Ajoutez buy_orders.py et sell_orders.py")
        print("   2. Mettez à jour config.py")
        print("   3. Complétez le .env avec les nouvelles variables")
        return False

def main():
    """Fonction principale"""
    print_header("🔍 DIAGNOSTIC DU BOT DE TRADING HYPERLIQUID")
    print("Version 3.0 - Architecture Modulaire")
    
    results = {
        'Python': check_python_version(),
        'Fichiers': check_files(),
        'Environnement virtuel': check_venv(),
        'Dependances': check_dependencies(),
        'Configuration': check_config(),
        'Permissions': check_database_permissions(),
        'Imports': test_imports()
    }
    
    # Test architecture optionnel
    has_new_arch = test_new_architecture()
    
    print_header("📊 RESUME DU DIAGNOSTIC")
    
    all_ok = True
    for category, status in results.items():
        symbol = "✅" if status else "❌"
        print(f"{symbol} {category}: {'OK' if status else 'PROBLEME'}")
        all_ok = all_ok and status
    
    # Status architecture
    arch_symbol = "✅" if has_new_arch else "ℹ️ "
    arch_status = "Disponible" if has_new_arch else "Non disponible (optionnel)"
    print(f"{arch_symbol} Architecture Modulaire: {arch_status}")
    
    print("\n" + "="*60)
    if all_ok:
        print("✅ TOUT EST OK ! Le bot est prêt à être lancé.")
        print("\nPour démarrer le bot :")
        print("  Linux/Mac: ./run.sh")
        print("  Windows: run.bat")
        print("  Manuel: python main.py")
        
        if has_new_arch:
            print("\n🎉 Architecture modulaire active!")
            print("   Les ordres d'achat et vente sont séparés")
        else:
            print("\n💡 Architecture modulaire non détectée")
            print("   Le bot fonctionnera avec l'architecture classique")
    else:
        print("❌ DES PROBLEMES ONT ETE DETECTES")
        print("\nActions recommandées :")
        if not results['Environnement virtuel']:
            print("  1. Exécutez install.sh ou install.bat")
        if not results['Configuration']:
            print("  2. Éditez le fichier .env et configurez PRIVATE_KEY")
        if not results['Dependances']:
            print("  3. Installez les dépendances: pip install -r requirements.txt")
        if not results['Fichiers']:
            print("  4. Vérifiez que tous les fichiers sont présents")
    print("="*60 + "\n")
    
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
