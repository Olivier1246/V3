#!/usr/bin/env python3
"""
Script pour recharger la configuration du bot en cours d'execution
"""

import requests
import sys

def reload_config(host='localhost', port=60000):
    """Recharge la configuration du bot via l'API"""
    
    url = f'http://{host}:{port}/api/control/reload_config'
    
    print("\n" + "="*60)
    print("🔄 RECHARGEMENT DE LA CONFIGURATION")
    print("="*60)
    print(f"URL: {url}")
    print()
    
    try:
        response = requests.post(url, timeout=5)
        data = response.json()
        
        if data.get('success'):
            print("✅ " + data.get('message', 'Configuration rechargee'))
            
            if 'config' in data:
                print("\n📊 CONFIGURATION ACTUELLE:")
                print("="*60)
                
                config = data['config']
                
                # Bear Market
                print("\n🐻 BEAR MARKET:")
                bear = config.get('bear_market', {})
                print(f"  Buy Offset: {bear.get('buy_offset')}$")
                print(f"  Sell Offset: {bear.get('sell_offset')}$")
                print(f"  Percent: {bear.get('percent')}%")
                print(f"  Time Pause: {bear.get('time_pause')} min")
                print(f"  Auto Interval: {bear.get('auto_interval_new')} min")
                
                # Bull Market
                print("\n🐂 BULL MARKET:")
                bull = config.get('bull_market', {})
                print(f"  Buy Offset: {bull.get('buy_offset')}$")
                print(f"  Sell Offset: {bull.get('sell_offset')}$")
                print(f"  Percent: {bull.get('percent')}%")
                print(f"  Time Pause: {bull.get('time_pause')} min")
                print(f"  Auto Interval: {bull.get('auto_interval_new')} min")
                
                # Range Market
                print("\n↔️  RANGE MARKET:")
                range_market = config.get('range_market', {})
                print(f"  Buy Offset: {range_market.get('buy_offset')}$")
                print(f"  Sell Offset: {range_market.get('sell_offset')}$")
                print(f"  Percent: {range_market.get('percent')}%")
                print(f"  Time Pause: {range_market.get('time_pause')} min")
                print(f"  Auto Interval: {range_market.get('auto_interval_new')} min")
                
                # Moving Averages
                print("\n📈 MOVING AVERAGES:")
                ma = config.get('moving_averages', {})
                print(f"  MA4 Period: {ma.get('ma4_period')}")
                print(f"  MA8 Period: {ma.get('ma8_period')}")
                print(f"  MA12 Period: {ma.get('ma12_period')}")
                print(f"  MA12 Flat Threshold: {ma.get('ma12_flat_threshold')}%")
                print(f"  MA12 Periods Check: {ma.get('ma12_periods_check')}")
                
                # Fees
                print("\n💰 FRAIS:")
                fees = config.get('fees', {})
                print(f"  Maker Fee: {fees.get('maker_fee')}%")
                print(f"  Taker Fee: {fees.get('taker_fee')}%")
                
                # Last Reload
                if config.get('last_reload'):
                    print(f"\n⏰ Dernier rechargement: {config.get('last_reload')}")
            
            print("\n" + "="*60)
            return True
        else:
            print("❌ " + data.get('message', 'Erreur inconnue'))
            print("="*60)
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter au bot")
        print("   Le bot est-il en cours d'execution ?")
        print(f"   Verifiez que le port {port} est correct")
        print("="*60)
        return False
    except requests.exceptions.Timeout:
        print("❌ Timeout - Le bot ne repond pas")
        print("="*60)
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print("="*60)
        return False

def main():
    """Fonction principale"""
    
    # Parametres par defaut
    host = 'localhost'
    port = 60000
    
    # Lire les arguments
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        host = sys.argv[2]
    
    success = reload_config(host, port)
    
    if success:
        print("\n💡 La nouvelle configuration sera appliquee:")
        print("   • Immediatement pour les nouveaux ordres")
        print("   • Les ordres en cours ne sont PAS affectes")
        print("   • Pas besoin de redemarrer le bot\n")
        sys.exit(0)
    else:
        print("\n❌ Le rechargement a echoue")
        print("   Verifiez les logs du bot pour plus de details\n")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption utilisateur\n")
        sys.exit(1)
