#!/usr/bin/env python3
"""
Script de diagnostic amélioré - Affiche les gains manquants avec simulation
"""

import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TradingConfig
from DB.database import Database


def calculate_expected_gain(buy_price, sell_price, quantity_btc, maker_fee_percent=0.04):
    """Calcule le gain attendu pour une paire"""
    buy_cost = buy_price * quantity_btc
    sell_revenue = sell_price * quantity_btc
    gross_profit = sell_revenue - buy_cost
    
    # Frais maker
    buy_fee = buy_cost * (maker_fee_percent / 100)
    sell_fee = sell_revenue * (maker_fee_percent / 100)
    total_fees = buy_fee + sell_fee
    
    # Profit net
    net_profit = gross_profit - total_fees
    profit_percent = (net_profit / buy_cost) * 100 if buy_cost > 0 else 0
    
    return {
        'gross_profit': gross_profit,
        'total_fees': total_fees,
        'net_profit': net_profit,
        'profit_percent': profit_percent,
        'buy_cost': buy_cost,
        'sell_revenue': sell_revenue
    }


def main():
    print("\n" + "="*70)
    print("🔍 DIAGNOSTIC DÉTAILLÉ - GAINS MANQUANTS")
    print("="*70)
    
    # Charger la configuration
    print("\n📋 Chargement de la configuration...")
    try:
        config = TradingConfig()
        maker_fee = config.maker_fee
        print(f"✅ Configuration chargée (Frais maker: {maker_fee}%)")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    # Connexion base de données
    print("\n🗄️  Connexion à la base de données...")
    try:
        db = Database(config)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    # Récupérer toutes les paires
    print("\n📊 Analyse des paires...")
    all_pairs = db.get_all_pairs(limit=1000)
    
    if not all_pairs:
        print("ℹ️  Aucune paire trouvée")
        return True
    
    # Analyser les paires
    total_pairs = len(all_pairs)
    completed_pairs = [p for p in all_pairs if p.status == 'Complete']
    pairs_with_gains = [p for p in completed_pairs if p.gain_usdc is not None]
    pairs_without_gains = [p for p in completed_pairs if p.gain_usdc is None]
    
    print(f"✅ {total_pairs} paire(s) au total")
    print(f"   • Complètes: {len(completed_pairs)}")
    print(f"   • Avec gains: {len(pairs_with_gains)}")
    print(f"   • SANS gains: {len(pairs_without_gains)}")
    
    if not pairs_without_gains:
        print("\n✅ Parfait ! Toutes les paires complètes ont leurs gains calculés.")
        return True
    
    # Afficher les détails des paires sans gains avec simulation
    print("\n" + "="*70)
    print(f"⚠️  {len(pairs_without_gains)} PAIRE(S) SANS GAINS DÉTECTÉE(S)")
    print("="*70)
    
    total_missing_gain = 0
    
    for pair in pairs_without_gains:
        # Simuler le gain attendu
        expected = calculate_expected_gain(
            pair.buy_price_btc,
            pair.sell_price_btc,
            pair.quantity_btc,
            maker_fee
        )
        
        total_missing_gain += expected['net_profit']
        
        print(f"\n📋 Paire #{pair.index}")
        print(f"   ├─ Status: {pair.status}")
        print(f"   ├─ Marché: {pair.market_type or 'N/A'}")
        print(f"   ├─ Buy Order ID: {pair.buy_order_id}")
        print(f"   ├─ Sell Order ID: {pair.sell_order_id or 'N/A'}")
        print(f"   │")
        print(f"   ├─ Prix achat: ${pair.buy_price_btc:,.2f}")
        print(f"   ├─ Prix vente: ${pair.sell_price_btc:,.2f}")
        print(f"   ├─ Quantité: {pair.quantity_btc:.8f} BTC")
        print(f"   │")
        print(f"   ├─ 💰 SIMULATION DU GAIN ATTENDU:")
        print(f"   │   ├─ Coût achat: ${expected['buy_cost']:.2f}")
        print(f"   │   ├─ Revenu vente: ${expected['sell_revenue']:.2f}")
        print(f"   │   ├─ Gain brut: ${expected['gross_profit']:.2f}")
        print(f"   │   ├─ Frais maker: ${expected['total_fees']:.4f}")
        print(f"   │   └─ Gain net: ${expected['net_profit']:.2f} ({expected['profit_percent']:.2f}%)")
        print(f"   │")
        
        if pair.created_at:
            print(f"   ├─ Créé: {pair.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        if pair.completed_at:
            print(f"   └─ Complété: {pair.completed_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        else:
            print(f"   └─ Complété: N/A")
    
    # Résumé final
    print("\n" + "="*70)
    print("📊 RÉSUMÉ")
    print("="*70)
    print(f"   Paires complètes sans gains: {len(pairs_without_gains)}")
    print(f"   Gain total manquant estimé: ${total_missing_gain:.2f}")
    print(f"   Gain moyen par paire: ${total_missing_gain/len(pairs_without_gains):.2f}")
    
    # Comparaison avec les paires ayant des gains
    if pairs_with_gains:
        actual_total_gain = sum(p.gain_usdc for p in pairs_with_gains if p.gain_usdc)
        print(f"\n   📈 Paires avec gains calculés:")
        print(f"      • Nombre: {len(pairs_with_gains)}")
        print(f"      • Gain total: ${actual_total_gain:.2f}")
        print(f"      • Gain moyen: ${actual_total_gain/len(pairs_with_gains):.2f}")
    
    print("\n" + "="*70)
    print("💡 SOLUTION")
    print("="*70)
    print("   Pour corriger ces paires, exécutez:")
    print("   ")
    print("   $ python3 fix_missing_gains.py")
    print("   ")
    print("   Ce script recalculera automatiquement les gains")
    print("   pour toutes les paires manquantes.")
    print("="*70 + "\n")
    
    return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption utilisateur\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
