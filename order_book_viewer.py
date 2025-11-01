#!/usr/bin/env python3
"""
Visualiseur du carnet d'ordres
Utilise database.py au lieu d'un fichier CSV
Compatible avec la nouvelle architecture
"""

from config import load_config
from DB.database import Database
from tabulate import tabulate
from datetime import datetime


def display_completed_pairs():
    """Affiche les paires complétées depuis la base de données"""
    config = load_config()
    db = Database(config)
    
    # Utiliser database.py au lieu de CSV
    pairs = db.get_recent_trades(limit=100)
    
    if not pairs:
        print("\n❌ Aucune paire complétée trouvée.\n")
        return
    
    # Préparer les données pour tabulate
    headers = ['Index', 'Status', 'Quantity BTC', 'Quantity USDC', 
               'Buy Price', 'Sell Price', 'Gain %', 'Gain $', 'UUID']
    rows = []
    
    total_gain = 0.0
    
    for pair in pairs:
        if pair.gain_usdc:
            total_gain += pair.gain_usdc
        
        rows.append([
            pair.index,
            pair.status,
            f"{pair.quantity_btc:.8f}",
            f"{pair.quantity_usdc:.2f}",
            f"{pair.buy_price_btc:.2f}",
            f"{pair.sell_price_btc:.2f}",
            f"{pair.gain_percent:.2f}%" if pair.gain_percent else "-",
            f"{pair.gain_usdc:.2f}$" if pair.gain_usdc else "-",
            pair.uuid[:8]
        ])
    
    print("\n" + "="*120)
    print("📊 PAIRES COMPLÉTÉES")
    print("="*120)
    print(tabulate(rows, headers=headers, tablefmt='grid'))
    print(f"\n💰 Total des gains: {total_gain:.2f}$")
    print(f"📈 Nombre de paires: {len(pairs)}")
    print("="*120 + "\n")


def display_statistics():
    """Affiche des statistiques depuis la base de données"""
    config = load_config()
    db = Database(config)
    
    # Utiliser la méthode get_statistics de database.py
    stats = db.get_statistics()
    
    if not stats or stats.get('total_pairs', 0) == 0:
        print("\n❌ Aucune donnée disponible.\n")
        return
    
    print("\n" + "="*60)
    print("📊 STATISTIQUES")
    print("="*60)
    print(f"Total paires: {stats.get('total_pairs', 0)}")
    print(f"  ✅ Complétées: {stats.get('completed', 0)}")
    print(f"  ⏳ Actives: {stats.get('buy_pending', 0) + stats.get('sell_pending', 0)}")
    print(f"     - En attente d'achat: {stats.get('buy_pending', 0)}")
    print(f"     - En attente de vente: {stats.get('sell_pending', 0)}")
    
    print(f"\n💰 Performance:")
    print(f"  Paires profitables: {stats.get('profitable_trades', 0)}")
    print(f"  Paires perdantes: {stats.get('losing_trades', 0)}")
    
    if stats.get('completed', 0) > 0:
        print(f"  Taux de réussite: {stats.get('win_rate', 0):.1f}%")
        print(f"  Gain total: {stats.get('total_gain_usdc', 0):.2f}$")
        print(f"  Gain moyen par paire: {stats.get('average_gain', 0):.2f}$")
    
    print("="*60 + "\n")


def export_to_excel():
    """Exporte les paires vers un fichier Excel depuis la base de données"""
    try:
        import pandas as pd
        from openpyxl import Workbook
        
        config = load_config()
        db = Database(config)
        
        pairs = db.get_all_pairs(limit=1000)
        
        if not pairs:
            print("\n❌ Aucune paire à exporter.\n")
            return
        
        # Convertir en dictionnaire pour pandas
        data = []
        for pair in pairs:
            data.append({
                'Index': pair.index,
                'Status': pair.status,
                'Quantity BTC': pair.quantity_btc,
                'Quantity USDC': pair.quantity_usdc,
                'Buy Price': pair.buy_price_btc,
                'Sell Price': pair.sell_price_btc,
                'Gain %': pair.gain_percent if pair.gain_percent else '',
                'Gain $': pair.gain_usdc if pair.gain_usdc else '',
                'Buy Order ID': pair.buy_order_id or '',
                'Sell Order ID': pair.sell_order_id or '',
                'Market Type': pair.market_type or '',
                'Offset': pair.offset_display or '',
                'UUID': pair.uuid,
                'Created': pair.created_at.strftime('%Y-%m-%d %H:%M:%S') if pair.created_at else '',
                'Completed': pair.completed_at.strftime('%Y-%m-%d %H:%M:%S') if pair.completed_at else ''
            })
        
        df = pd.DataFrame(data)
        excel_file = f'trading_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Toutes les paires', index=False)
            
            # Feuille pour les paires complétées uniquement
            completed = df[df['Status'] == 'Complete']
            if not completed.empty:
                completed.to_excel(writer, sheet_name='Paires complétées', index=False)
            
            # Feuille pour les statistiques
            config_obj = load_config()
            stats_db = Database(config_obj)
            stats = stats_db.get_statistics()
            
            stats_data = pd.DataFrame([{
                'Métrique': k,
                'Valeur': v
            } for k, v in stats.items()])
            stats_data.to_excel(writer, sheet_name='Statistiques', index=False)
        
        print(f"\n✅ Rapport exporté vers: {excel_file}")
        print(f"   📊 {len(pairs)} paires exportées\n")
        
    except ImportError:
        print("\n❌ pandas et openpyxl requis pour l'export Excel")
        print("   Installez avec: pip install pandas openpyxl\n")
    except Exception as e:
        print(f"\n❌ Erreur export Excel: {e}\n")


def export_to_csv():
    """Exporte les paires vers CSV depuis la base de données"""
    import csv
    
    try:
        config = load_config()
        db = Database(config)
        
        pairs = db.get_all_pairs(limit=1000)
        
        if not pairs:
            print("\n❌ Aucune paire à exporter.\n")
            return
        
        filename = f'trading_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='\t')
            
            # En-têtes
            writer.writerow([
                'Index', 'Status', 'Quantity BTC', 'Quantity USDC',
                'Buy Price', 'Sell Price', 'Gain %', 'Gain $',
                'Buy Order ID', 'Sell Order ID', 'Market Type',
                'Offset', 'UUID', 'Created', 'Completed'
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
                    pair.market_type or '',
                    pair.offset_display or '',
                    pair.uuid,
                    pair.created_at.strftime('%Y-%m-%d %H:%M:%S') if pair.created_at else '',
                    pair.completed_at.strftime('%Y-%m-%d %H:%M:%S') if pair.completed_at else ''
                ])
        
        print(f"\n✅ Export CSV réussi: {filename}")
        print(f"   📊 {len(pairs)} paires exportées\n")
        
    except Exception as e:
        print(f"\n❌ Erreur export CSV: {e}\n")


def main():
    """Menu principal"""
    print("\n" + "="*60)
    print("📊 VISUALISEUR DU CARNET D'ORDRES")
    print("Version 2.0 - Utilise database.py")
    print("="*60)
    
    while True:
        print("\n1. Afficher les paires complétées")
        print("2. Afficher les statistiques")
        print("3. Exporter vers Excel")
        print("4. Exporter vers CSV")
        print("5. Quitter")
        print("="*60)
        
        choice = input("\nChoisissez une option (1-5): ").strip()
        
        if choice == '1':
            display_completed_pairs()
        elif choice == '2':
            display_statistics()
        elif choice == '3':
            export_to_excel()
        elif choice == '4':
            export_to_csv()
        elif choice == '5':
            print("\n👋 Au revoir!\n")
            break
        else:
            print("\n❌ Option invalide.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption utilisateur. Au revoir!\n")
    except Exception as e:
        print(f"\n❌ Erreur: {e}\n")
        import traceback
        traceback.print_exc()
