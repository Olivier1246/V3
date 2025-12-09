#!/usr/bin/env python3
"""
Script de correction pour recalculer les gains des paires complètes
Utilise la méthode complete_order_pair() existante dans database.py
"""

import sys
import os

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import TradingConfig
from DB.database import Database


def main():
    print("\n" + "="*70)
    print("🔧 CORRECTION DES GAINS - PAIRES COMPLÈTES")
    print("="*70)
    
    # Charger la configuration
    print("\n📋 Chargement de la configuration...")
    try:
        config = TradingConfig()
        print(f"✅ Configuration chargée (Frais maker: {config.maker_fee}%)")
    except Exception as e:
        print(f"❌ Erreur chargement configuration: {e}")
        return False
    
    # Initialiser la base de données
    print("\n🗄️  Connexion à la base de données...")
    try:
        db = Database(config)
    except Exception as e:
        print(f"❌ Erreur connexion base de données: {e}")
        return False
    
    # Récupérer toutes les paires
    print("\n📊 Récupération des paires...")
    all_pairs = db.get_all_pairs(limit=1000)
    
    if not all_pairs:
        print("ℹ️  Aucune paire trouvée dans la base de données")
        return True
    
    print(f"✅ {len(all_pairs)} paire(s) trouvée(s)")
    
    # Identifier les paires complètes sans gains
    pairs_to_fix = []
    for pair in all_pairs:
        if pair.status == 'Complete' and pair.gain_usdc is None:
            pairs_to_fix.append(pair)
    
    if not pairs_to_fix:
        print("\n✅ Toutes les paires complètes ont déjà leurs gains calculés")
        return True
    
    print(f"\n⚠️  {len(pairs_to_fix)} paire(s) complète(s) SANS gains détectée(s)")
    
    # Afficher les détails
    print("\nDétails des paires à corriger:")
    print("-" * 70)
    for pair in pairs_to_fix:
        print(f"   • Paire #{pair.index}: " +
              f"Buy=${pair.buy_price_btc:.2f}, " +
              f"Sell=${pair.sell_price_btc:.2f}, " +
              f"Qty={pair.quantity_btc:.8f} BTC")
    print("-" * 70)
    
    # Demander confirmation
    print(f"\n⚠️  Cette opération va recalculer les gains de ces {len(pairs_to_fix)} paires.")
    response = input("Voulez-vous continuer ? (oui/non): ").strip().lower()
    
    if response not in ['oui', 'o', 'yes', 'y']:
        print("\n❌ Opération annulée par l'utilisateur")
        return False
    
    # Correction des paires
    print(f"\n🔧 Correction en cours...\n")
    
    success_count = 0
    error_count = 0
    
    for pair in pairs_to_fix:
        try:
            print(f"Traitement paire #{pair.index}... ", end='', flush=True)
            
            # Utiliser la méthode complete_order_pair() avec le prix de vente réel
            result = db.complete_order_pair(
                index=pair.index,
                sell_price_actual=pair.sell_price_btc
            )
            
            if result:
                print("✅ Corrigé")
                success_count += 1
            else:
                print("❌ Échec")
                error_count += 1
                
        except Exception as e:
            print(f"❌ Erreur: {e}")
            error_count += 1
    
    # Résumé
    print("\n" + "="*70)
    print("📊 RÉSUMÉ DE LA CORRECTION")
    print("="*70)
    print(f"   Paires à corriger:       {len(pairs_to_fix)}")
    print(f"   ✅ Corrections réussies: {success_count}")
    print(f"   ❌ Échecs:               {error_count}")
    print("="*70)
    
    if error_count > 0:
        print("\n⚠️  Certaines corrections ont échoué.")
        print("   Vérifiez les logs ci-dessus pour plus de détails.")
    else:
        print("\n✅ Toutes les corrections ont réussi !")
        print("\n💡 Vous pouvez maintenant:")
        print("   • Actualiser votre interface web pour voir les gains")
        print("   • Relancer diagnostic_gains.py pour vérifier")
    
    print("\n" + "="*70)
    print("✅ Script terminé")
    print("="*70 + "\n")
    
    return error_count == 0


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
