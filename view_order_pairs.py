#!/usr/bin/env python3
"""
Visualiseur de la base de données des paires d'ordres
Compatible avec la NOUVELLE structure simplifiée
"""

from config import load_config
from DB.database import Database
from tabulate import tabulate
from datetime import datetime

def display_all_pairs():
    """Affiche toutes les paires d'ordres"""
    config = load_config()
    db = Database(config)
    
    # Nouvelle API: get_all_pairs au lieu de get_all_order_pairs
    pairs = db.get_all_pairs(limit=100)
    
    if not pairs:
        print("\n❌ Aucune paire trouvée dans la base de données.\n")
        return
    
    # Préparer les données pour tabulate
    headers = [
        'Index', 'Status', 'Qty BTC', 'Qty USDC', 'Buy Price', 
        'Sell Price', 'Gain %', 'Gain $', 'Buy ID', 'Sell ID', 
        'Offset', 'Market', 'UUID'
    ]
    
    rows = []
    for pair in pairs:
        rows.append([
            pair.index,
            pair.status,
            f"{pair.quantity_btc:.8f}",
            f"{pair.quantity_usdc:.2f}",
            f"{pair.buy_price_btc:.2f}",
            f"{pair.sell_price_btc:.2f}",
            f"{pair.gain_percent:.2f}%" if pair.gain_percent else "-",
            f"{pair.gain_usdc:.2f}$" if pair.gain_usdc else "-",
            pair.buy_order_id[:8] if pair.buy_order_id else "-",
            pair.sell_order_id[:8] if pair.sell_order_id else "-",
            pair.offset_display or "-",
            pair.market_type or "-",
            pair.uuid[:8]
        ])
    
    print("\n" + "="*160)
    print("📊 TOUTES LES PAIRES D'ORDRES")
    print("="*160)
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print(f"\nTotal: {len(pairs)} paires")
    print("="*160 + "\n")

def display_active_pairs():
    """Affiche les paires actives"""
    config = load_config()
    db = Database(config)
    
    # Nouvelle API: get_pending_buy_orders et get_pending_sell_orders
    buy_pending = db.get_pending_buy_orders()
    sell_pending = db.get_pending_sell_orders()
    
    all_active = buy_pending + sell_pending
    
    if not all_active:
        print("\n✅ Aucune paire active.\n")
        return
    
    headers = [
        'Index', 'Status', 'Qty BTC', 'Qty USDC', 'Buy Price', 
        'Sell Price', 'Buy ID', 'Sell ID', 'Offset', 'Market', 
        'Créé le', 'UUID'
    ]
    
    rows = []
    for pair in all_active:
        created = pair.created_at.strftime('%Y-%m-%d %H:%M:%S') if pair.created_at else '-'
        rows.append([
            pair.index,
            pair.status,
            f"{pair.quantity_btc:.8f}",
            f"{pair.quantity_usdc:.2f}",
            f"{pair.buy_price_btc:.2f}",
            f"{pair.sell_price_btc:.2f}",
            pair.buy_order_id[:8] if pair.buy_order_id else "-",
            pair.sell_order_id[:8] if pair.sell_order_id else "-",
            pair.offset_display or "-",
            pair.market_type or "-",
            created,
            pair.uuid[:8]
        ])
    
    print("\n" + "="*180)
    print("⏳ PAIRES ACTIVES (en attente)")
    print("="*180)
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print(f"\nTotal: {len(all_active)} paires actives")
    print(f"  - En attente d'achat (Buy): {len(buy_pending)}")
    print(f"  - En attente de vente (Sell): {len(sell_pending)}")
    print("="*180 + "\n")

def display_completed_pairs():
    """Affiche les paires complétées"""
    config = load_config()
    db = Database(config)
    
    # Récupérer toutes les paires et filtrer les complétées
    all_pairs = db.get_all_pairs(limit=100)
    pairs = [p for p in all_pairs if p.status == 'Complete']
    
    if not pairs:
        print("\n❌ Aucune paire complétée.\n")
        return
    
    headers = [
        'Index', 'Qty BTC', 'Qty USDC', 'Buy Price', 'Sell Price', 
        'Gain %', 'Gain $', 'Buy ID', 'Sell ID', 'Offset', 
        'Market', 'Complété le', 'UUID'
    ]
    
    rows = []
    total_gain = 0.0
    profitable = 0
    
    for pair in pairs:
        completed = pair.completed_at.strftime('%Y-%m-%d %H:%M:%S') if pair.completed_at else '-'
        
        if pair.gain_usdc:
            total_gain += pair.gain_usdc
            if pair.gain_usdc > 0:
                profitable += 1
        
        rows.append([
            pair.index,
            f"{pair.quantity_btc:.8f}",
            f"{pair.quantity_usdc:.2f}",
            f"{pair.buy_price_btc:.2f}",
            f"{pair.sell_price_btc:.2f}",
            f"{pair.gain_percent:.2f}%" if pair.gain_percent else "-",
            f"{pair.gain_usdc:.2f}$" if pair.gain_usdc else "-",
            pair.buy_order_id[:8] if pair.buy_order_id else "-",
            pair.sell_order_id[:8] if pair.sell_order_id else "-",
            pair.offset_display or "-",
            pair.market_type or "-",
            completed,
            pair.uuid[:8]
        ])
    
    print("\n" + "="*180)
    print("✅ PAIRES COMPLÉTÉES")
    print("="*180)
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print(f"\nStatistiques:")
    print(f"  Total paires: {len(pairs)}")
    print(f"  Paires profitables: {profitable}")
    print(f"  Paires perdantes: {len(pairs) - profitable}")
    print(f"  Gain total: {total_gain:.2f}$")
    if len(pairs) > 0:
        print(f"  Gain moyen: {total_gain/len(pairs):.2f}$")
        print(f"  Taux de réussite: {(profitable/len(pairs)*100):.1f}%")
    print("="*180 + "\n")

def display_statistics():
    """Affiche des statistiques globales"""
    config = load_config()
    db = Database(config)
    
    # Nouvelle API: get_statistics
    stats = db.get_statistics()
    
    print("\n" + "="*80)
    print("📈 STATISTIQUES GLOBALES")
    print("="*80)
    print(f"Total paires: {stats.get('total_pairs', 0)}")
    print(f"  ✅ Complétées: {stats.get('completed', 0)}")
    print(f"  ⏳ Actives: {stats.get('buy_pending', 0) + stats.get('sell_pending', 0)}")
    print(f"     - En attente d'achat (Buy): {stats.get('buy_pending', 0)}")
    print(f"     - En attente de vente (Sell): {stats.get('sell_pending', 0)}")
    
    print(f"\nPerformance:")
    print(f"  Gain total: {stats.get('total_gain_usdc', 0):.2f}$")
    print(f"  Paires profitables: {stats.get('profitable_trades', 0)}/{stats.get('completed', 0)}")
    
    if stats.get('completed', 0) > 0:
        print(f"  Taux de réussite: {stats.get('win_rate', 0):.1f}%")
        print(f"  Gain moyen: {stats.get('average_gain', 0):.2f}$")
    
    print("="*80 + "\n")

def export_to_csv():
    """Exporte toutes les paires vers CSV"""
    import csv
    config = load_config()
    db = Database(config)
    
    pairs = db.get_all_pairs(limit=1000)
    
    if not pairs:
        print("\n❌ Aucune paire à exporter.\n")
        return
    
    filename = f"order_pairs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='\t')
        
        # En-têtes - NOUVELLE STRUCTURE
        writer.writerow([
            'Index', 'Status', 'Quantity BTC', 'Quantity USDC', 
            'Buy Price BTC', 'Sell Price BTC', 'Gain %', 'Gain $', 
            'Buy Order ID', 'Sell Order ID', 'Offset Display', 
            'Market Type', 'Symbol', 'UUID', 
            'Créé le', 'Achat rempli le', 'Vente placée le', 'Complété le'
        ])
        
        # Données
        for pair in pairs:
            writer.writerow([
                pair.index,
                pair.status,
                pair.quantity_btc,
                pair.quantity_usdc,
                pair.buy_price_btc,
                pair.sell_price_btc,
                pair.gain_percent if pair.gain_percent else '',
                pair.gain_usdc if pair.gain_usdc else '',
                pair.buy_order_id or '',
                pair.sell_order_id or '',
                pair.offset_display or '',
                pair.market_type or '',
                pair.symbol or '',
                pair.uuid,
                pair.created_at.strftime('%Y-%m-%d %H:%M:%S') if pair.created_at else '',
                pair.buy_filled_at.strftime('%Y-%m-%d %H:%M:%S') if pair.buy_filled_at else '',
                pair.sell_placed_at.strftime('%Y-%m-%d %H:%M:%S') if pair.sell_placed_at else '',
                pair.completed_at.strftime('%Y-%m-%d %H:%M:%S') if pair.completed_at else ''
            ])
    
    print(f"\n✅ Export réussi: {filename}")
    print(f"   {len(pairs)} paires exportées\n")

def display_pair_details():
    """Affiche les détails d'une paire spécifique"""
    config = load_config()
    db = Database(config)
    
    try:
        index = int(input("\nEntrez l'index de la paire: "))
        pair = db.get_pair_by_index(index)
        
        if not pair:
            print(f"\n❌ Paire {index} introuvable.\n")
            return
        
        print("\n" + "="*80)
        print(f"📋 DÉTAILS DE LA PAIRE #{pair.index}")
        print("="*80)
        
        print(f"\n🔢 Identification:")
        print(f"   Index: {pair.index}")
        print(f"   UUID: {pair.uuid}")
        print(f"   Status: {pair.status}")
        print(f"   Marché: {pair.market_type or 'N/A'}")
        print(f"   Symbole: {pair.symbol}")
        
        print(f"\n💰 Quantités:")
        print(f"   BTC: {pair.quantity_btc:.8f}")
        print(f"   USDC: {pair.quantity_usdc:.2f}")
        
        print(f"\n📊 Prix:")
        print(f"   Achat: {pair.buy_price_btc:.2f}$")
        print(f"   Vente: {pair.sell_price_btc:.2f}$")
        print(f"   Offsets: {pair.offset_display or 'N/A'}")
        
        print(f"\n🆔 Order IDs:")
        print(f"   Buy: {pair.buy_order_id or 'N/A'}")
        print(f"   Sell: {pair.sell_order_id or 'N/A'}")
        
        if pair.gain_usdc is not None:
            print(f"\n💵 Gains:")
            print(f"   Montant: {pair.gain_usdc:.2f}$")
            print(f"   Pourcentage: {pair.gain_percent:.2f}%")
        
        print(f"\n⏰ Timestamps:")
        print(f"   Créé: {pair.created_at.strftime('%Y-%m-%d %H:%M:%S') if pair.created_at else 'N/A'}")
        print(f"   Achat rempli: {pair.buy_filled_at.strftime('%Y-%m-%d %H:%M:%S') if pair.buy_filled_at else 'N/A'}")
        print(f"   Vente placée: {pair.sell_placed_at.strftime('%Y-%m-%d %H:%M:%S') if pair.sell_placed_at else 'N/A'}")
        print(f"   Complété: {pair.completed_at.strftime('%Y-%m-%d %H:%M:%S') if pair.completed_at else 'N/A'}")
        
        print("="*80 + "\n")
        
    except ValueError:
        print("\n❌ Index invalide.\n")
    except Exception as e:
        print(f"\n❌ Erreur: {e}\n")

def main():
    """Menu principal"""
    while True:
        print("\n" + "="*80)
        print("📊 VISUALISEUR BASE DE DONNÉES - PAIRES D'ORDRES")
        print("Version 2.0 - Structure Simplifiée")
        print("="*80)
        print("1. Afficher toutes les paires")
        print("2. Afficher les paires actives")
        print("3. Afficher les paires complétées")
        print("4. Afficher les statistiques")
        print("5. Détails d'une paire")
        print("6. Exporter vers CSV")
        print("7. Quitter")
        print("="*80)
        
        choice = input("\nChoisissez une option (1-7): ").strip()
        
        if choice == '1':
            display_all_pairs()
        elif choice == '2':
            display_active_pairs()
        elif choice == '3':
            display_completed_pairs()
        elif choice == '4':
            display_statistics()
        elif choice == '5':
            display_pair_details()
        elif choice == '6':
            export_to_csv()
        elif choice == '7':
            print("\n👋 Au revoir!\n")
            break
        else:
            print("\n❌ Option invalide.\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption utilisateur. Au revoir!\n")
