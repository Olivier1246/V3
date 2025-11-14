#!/usr/bin/env python3
"""
Script de correction pour recalculer les gains des paires complètes
Utilisation: python fix_completed_pairs_gains.py
"""

import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DB.database import Database
from config import TradingConfig


def fix_completed_pairs():
    """Recalcule les gains pour toutes les paires complètes sans gains"""
    
    print("\n" + "="*70)
    print("🔧 CORRECTION DES GAINS - PAIRES COMPLÈTES")
    print("="*70 + "\n")
    
    try:
        # Initialiser
        config = TradingConfig()
        db = Database(config)
        
        print("📊 Récupération des paires...")
        all_pairs = db.get_all_pairs(limit=500)
        
        if not all_pairs:
            print("❌ Aucune paire trouvée dans la BDD")
            return
        
        print(f"✅ {len(all_pairs)} paire(s) trouvée(s)\n")
        
        # Filtrer les paires complètes sans gains
        broken_pairs = [
            p for p in all_pairs 
            if p.status == 'Complete' and (p.gain_usdc is None or p.gain_percent is None)
        ]
        
        if not broken_pairs:
            print("✅ AUCUNE CORRECTION NÉCESSAIRE")
            print("   Toutes les paires complètes ont déjà leurs gains calculés !")
            return
        
        print(f"⚠️  {len(broken_pairs)} paire(s) complète(s) SANS gains détectée(s)")
        print("\nDétails des paires à corriger:")
        print("-" * 70)
        
        for pair in broken_pairs:
            print(f"   • Paire #{pair.index}: Buy=${pair.buy_price_btc:.2f}, "
                  f"Sell=${pair.sell_price_btc:.2f}, Qty={pair.quantity_btc:.8f} BTC")
        
        print("-" * 70)
        
        # Demander confirmation
        print("\n⚠️  Cette opération va recalculer les gains de ces paires.")
        response = input("Voulez-vous continuer ? (oui/non): ").strip().lower()
        
        if response not in ['oui', 'o', 'yes', 'y']:
            print("\n❌ Opération annulée par l'utilisateur")
            return
        
        print("\n🔧 Correction en cours...\n")
        
        fixed_count = 0
        failed_count = 0
        
        for pair in broken_pairs:
            print(f"Traitement paire #{pair.index}...", end=" ")
            
            try:
                # Recalculer les gains
                success = db.complete_pair(pair.index, pair.sell_price_btc)
                
                if success:
                    # Récupérer la paire mise à jour
                    updated_pair = db.get_pair_by_index(pair.index)
                    
                    if updated_pair and updated_pair.gain_usdc is not None:
                        fixed_count += 1
                        color = "🟢" if updated_pair.gain_usdc > 0 else "🔴"
                        print(f"✅ {color} Gain: ${updated_pair.gain_usdc:.2f} ({updated_pair.gain_percent:.2f}%)")
                    else:
                        failed_count += 1
                        print("❌ Échec (gains toujours NULL)")
                else:
                    failed_count += 1
                    print("❌ Échec (complete_pair retourné False)")
                    
            except Exception as e:
                failed_count += 1
                print(f"❌ Erreur: {e}")
        
        # Résumé
        print("\n" + "="*70)
        print("📊 RÉSUMÉ DE LA CORRECTION")
        print("="*70)
        print(f"   Paires à corriger:     {len(broken_pairs)}")
        print(f"   ✅ Corrections réussies: {fixed_count}")
        print(f"   ❌ Échecs:               {failed_count}")
        print("="*70)
        
        if fixed_count > 0:
            print("\n🎉 Succès ! Les gains ont été recalculés.")
            print("\n💡 Prochaines étapes:")
            print("   1. Vérifiez l'interface web (http://localhost:60000/)")
            print("   2. Les colonnes 'Gain %' et 'Gain $' devraient s'afficher")
            print("   3. Si besoin, videz le cache navigateur (Ctrl+F5)")
        
        if failed_count > 0:
            print("\n⚠️  Certaines corrections ont échoué.")
            print("   Vérifiez les logs pour plus de détails.")
            print("   Les paires concernées peuvent avoir des données incorrectes.")
        
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "="*70)
    print("✅ Script terminé")
    print("="*70 + "\n")


def show_status():
    """Affiche le statut actuel sans corriger"""
    
    print("\n" + "="*70)
    print("📊 STATUT DES GAINS - PAIRES COMPLÈTES")
    print("="*70 + "\n")
    
    try:
        config = TradingConfig()
        db = Database(config)
        
        all_pairs = db.get_all_pairs(limit=500)
        complete_pairs = [p for p in all_pairs if p.status == 'Complete']
        
        if not complete_pairs:
            print("ℹ️  Aucune paire complète trouvée")
            return
        
        print(f"📋 {len(complete_pairs)} paire(s) complète(s) trouvée(s)\n")
        
        with_gains = [p for p in complete_pairs if p.gain_usdc is not None and p.gain_percent is not None]
        without_gains = [p for p in complete_pairs if p.gain_usdc is None or p.gain_percent is None]
        
        print("✅ Paires avec gains calculés:")
        print(f"   {len(with_gains)} paire(s)")
        
        if with_gains:
            total_gain = sum(p.gain_usdc for p in with_gains)
            avg_gain = total_gain / len(with_gains)
            positive = sum(1 for p in with_gains if p.gain_usdc > 0)
            
            print(f"   • Gain total: ${total_gain:.2f}")
            print(f"   • Gain moyen: ${avg_gain:.2f}")
            print(f"   • Paires profitables: {positive}/{len(with_gains)} ({positive/len(with_gains)*100:.1f}%)")
        
        print(f"\n❌ Paires SANS gains calculés:")
        print(f"   {len(without_gains)} paire(s)")
        
        if without_gains:
            print("\n   Liste des paires problématiques:")
            for p in without_gains[:10]:  # Max 10
                print(f"   • Paire #{p.index}: Buy=${p.buy_price_btc:.2f}, Sell=${p.sell_price_btc:.2f}")
            
            if len(without_gains) > 10:
                print(f"   ... et {len(without_gains) - 10} autre(s)")
            
            print(f"\n   💡 Utilisez --fix pour corriger ces paires")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['--status', '-s']:
        show_status()
    elif len(sys.argv) > 1 and sys.argv[1] in ['--fix', '-f']:
        fix_completed_pairs()
    else:
        print("\n" + "="*70)
        print("🔧 SCRIPT DE CORRECTION DES GAINS")
        print("="*70)
        print("\nUtilisation:")
        print("   python fix_completed_pairs_gains.py --status   # Afficher le statut")
        print("   python fix_completed_pairs_gains.py --fix      # Corriger les paires")
        print("\nOu simplement:")
        print("   python fix_completed_pairs_gains.py            # Mode interactif")
        print("="*70 + "\n")
        
        # Mode interactif par défaut
        fix_completed_pairs()
