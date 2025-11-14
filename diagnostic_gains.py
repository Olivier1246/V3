#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier l'affichage des gains
Vérifie si les paires sont correctement complétées dans la BDD
"""

import sys
import os

# Ajouter le répertoire parent au path pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DB.database import Database
from config import TradingConfig


def main():
    print("\n" + "="*70)
    print("🔍 DIAGNOSTIC - AFFICHAGE DES GAINS")
    print("="*70 + "\n")
    
    try:
        # Initialiser la config et la BDD
        config = TradingConfig()
        db = Database(config)
        
        # Récupérer toutes les paires
        all_pairs = db.get_all_pairs(limit=200)
        
        if not all_pairs:
            print("❌ Aucune paire trouvée dans la BDD")
            return
        
        print(f"📊 Total de paires trouvées: {len(all_pairs)}\n")
        
        # Statistiques par statut
        buy_count = sum(1 for p in all_pairs if p.status == 'Buy')
        sell_count = sum(1 for p in all_pairs if p.status == 'Sell')
        complete_count = sum(1 for p in all_pairs if p.status == 'Complete')
        
        print("📈 STATISTIQUES PAR STATUT:")
        print(f"   • Buy (en attente d'achat):  {buy_count}")
        print(f"   • Sell (en attente de vente): {sell_count}")
        print(f"   • Complete (terminées):       {complete_count}")
        print()
        
        # Vérifier les paires complètes
        complete_pairs = [p for p in all_pairs if p.status == 'Complete']
        
        if complete_count == 0:
            print("⚠️  PROBLÈME DÉTECTÉ:")
            print("   Aucune paire n'est marquée comme 'Complete'")
            print("   → Les gains ne peuvent pas s'afficher !\n")
            print("💡 SOLUTIONS:")
            print("   1. Vérifiez que le système de synchronisation fonctionne")
            print("   2. Vérifiez que database.complete_pair() est bien appelé")
            print("   3. Attendez qu'au moins un cycle achat+vente soit terminé")
            return
        
        # Analyser les paires complètes
        print(f"✅ {complete_count} paire(s) complétée(s) trouvée(s)\n")
        print("="*70)
        print("DÉTAIL DES PAIRES COMPLÈTES:")
        print("="*70 + "\n")
        
        pairs_with_gains = 0
        pairs_without_gains = 0
        total_gain = 0
        
        for pair in complete_pairs[:20]:  # Afficher max 20 paires
            print(f"📋 Paire #{pair.index}")
            print(f"   Status:          {pair.status}")
            print(f"   Buy Price:       ${pair.buy_price_btc:.2f}")
            print(f"   Sell Price:      ${pair.sell_price_btc:.2f}")
            print(f"   Quantity BTC:    {pair.quantity_btc:.8f}")
            print(f"   Buy Order ID:    {pair.buy_order_id or 'N/A'}")
            print(f"   Sell Order ID:   {pair.sell_order_id or 'N/A'}")
            
            # Vérifier les gains
            if pair.gain_usdc is not None and pair.gain_percent is not None:
                pairs_with_gains += 1
                total_gain += pair.gain_usdc
                
                color = "🟢" if pair.gain_usdc > 0 else "🔴"
                print(f"   {color} Gain USDC:      ${pair.gain_usdc:.2f}")
                print(f"   {color} Gain %:         {pair.gain_percent:.2f}%")
                print(f"   ✅ Les gains SONT calculés pour cette paire")
            else:
                pairs_without_gains += 1
                print(f"   ❌ Gain USDC:      NULL")
                print(f"   ❌ Gain %:         NULL")
                print(f"   ⚠️  Les gains ne sont PAS calculés pour cette paire")
            
            print()
        
        # Résumé
        print("="*70)
        print("📊 RÉSUMÉ DU DIAGNOSTIC:")
        print("="*70)
        print(f"   Paires complètes avec gains calculés:    {pairs_with_gains}")
        print(f"   Paires complètes SANS gains calculés:    {pairs_without_gains}")
        print(f"   Gain total (paires avec gains):          ${total_gain:.2f}")
        print()
        
        # Conclusion
        if pairs_without_gains > 0:
            print("⚠️  PROBLÈME DÉTECTÉ:")
            print(f"   {pairs_without_gains} paire(s) complète(s) n'ont pas de gains calculés")
            print("   → Ces paires apparaîtront avec '-' dans la colonne gains")
            print()
            print("💡 CAUSE PROBABLE:")
            print("   La fonction database.complete_pair() n'a pas été appelée")
            print("   lors de la complétion de ces paires")
            print()
            print("🔧 SOLUTION:")
            print("   1. Vérifiez json_sync_orders.py ou sync_hyperliquid_orders.py")
            print("   2. Cherchez où les paires sont marquées comme 'Complete'")
            print("   3. Assurez-vous que complete_pair() est appelé à ce moment")
            print()
            print("   Exemple de code correct:")
            print("   ```python")
            print("   # Quand un ordre de vente est rempli")
            print("   if sell_order_filled:")
            print("       # Appeler complete_pair pour calculer les gains")
            print("       self.database.complete_pair(pair.index, actual_sell_price)")
            print("   ```")
        else:
            print("✅ TOUT EST OK !")
            print("   Toutes les paires complètes ont leurs gains calculés")
            print("   Les gains devraient s'afficher correctement dans l'interface web")
            print()
            print("   Si les gains ne s'affichent toujours pas, vérifiez:")
            print("   1. Que les fichiers web_interface.py et index.html sont à jour")
            print("   2. Que le serveur web a été redémarré")
            print("   3. Que le cache du navigateur a été vidé (Ctrl+F5)")
        
        print()
        print("="*70)
        
        # Informations supplémentaires sur les paires en cours
        if sell_count > 0:
            print(f"\nℹ️  {sell_count} paire(s) en attente de vente")
            print("   Ces paires afficheront '-' pour les gains (normal)")
            
        if buy_count > 0:
            print(f"\nℹ️  {buy_count} paire(s) en attente d'achat")
            print("   Ces paires afficheront '-' pour les gains (normal)")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*70)
    print("✅ Diagnostic terminé")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
