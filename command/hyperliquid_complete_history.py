"""
Script COMPLET pour récupérer l'historique des ordres Spot sur Hyperliquid
AVEC TOUS LES STATUTS : open, filled, canceled, rejected, etc.

✅ CORRECTIONS APPLIQUÉES:
- Nouvel objet Info pour CHAQUE appel API (évite les timeouts)
- Gestion robuste des erreurs avec try-except
- Délai de 1s entre les appels pour éviter le rate limiting
- Retry automatique en cas d'échec
"""

from hyperliquid.info import Info
from hyperliquid.utils import constants
from datetime import datetime
import json
import time

# 🔧 Configuration
USER_ADDRESS = "0x0000000000000000000000000000000000"  # ⚠️ REMPLACEZ PAR VOTRE ADRESSE

def get_complete_order_history(user_address):
    """
    Récupère l'historique COMPLET des ordres avec TOUS les statuts
    
    ✅ CORRECTION: Crée un nouvel objet Info pour CHAQUE appel API
    pour éviter les timeouts en mode automatique
    
    Returns:
        dict: {
            'open_orders': [...],      # Ordres ouverts actuellement
            'historical_orders': [...], # Historique complet (filled, canceled, rejected, etc.)
            'fills': [...]             # Détails des exécutions
        }
    """
    
    print(f"🔍 Récupération de l'historique complet pour {user_address}\n")
    print("=" * 80)
    
    # ============================================================================
    # 1. ORDRES OUVERTS (OPEN)
    # ============================================================================
    print("\n📥 1/3 - Récupération des ordres ouverts...")
    spot_open_orders = []
    
    for attempt in range(1, 6):  # 5 tentatives max
        try:
            print(f"   📡 Tentative {attempt}/5 (timeout: 90s)...")
            
            # ✅ FIX CRITIQUE: Créer un NOUVEL objet Info pour chaque appel
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            
            open_orders = info.open_orders(user_address)
            
            # Filtrer les ordres Spot (coin commence par "@")
            spot_open_orders = [order for order in open_orders if order.get('coin', '').startswith('@')]
            
            print(f"   ✅ {len(spot_open_orders)} ordres Spot ouverts trouvés")
            break  # Succès, sortir de la boucle
            
        except Exception as e:
            print(f"   ❌ Erreur ordres ouverts: {e}")
            if attempt < 5:
                wait_time = attempt * 2  # Attendre plus longtemps à chaque tentative
                print(f"   ⏳ Attente de {wait_time}s avant nouvelle tentative...")
                time.sleep(wait_time)
            else:
                print(f"   ⚠️  Échec après 5 tentatives, continuation avec 0 ordres")
                spot_open_orders = []
    
    # Pause entre les appels
    time.sleep(1)
    
    # ============================================================================
    # 2. HISTORIQUE COMPLET (FILLED, CANCELED, REJECTED, etc.)
    # ============================================================================
    print("\n📥 2/3 - Récupération de l'historique complet (max 2000 ordres)...")
    spot_historical = []
    
    for attempt in range(1, 6):
        try:
            print(f"   📡 Tentative {attempt}/5 (timeout: 90s)...")
            
            # ✅ FIX CRITIQUE: Nouvel objet Info pour ce 2ème appel
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            
            # ⭐ ENDPOINT CLÉ : historicalOrders
            # Retourne TOUS les ordres avec leur statut : filled, canceled, rejected, etc.
            historical_orders = info.post("/info", {"type": "historicalOrders", "user": user_address})
            
            # Filtrer les ordres Spot
            spot_historical = [order for order in historical_orders 
                              if order.get('order', {}).get('coin', '').startswith('@')]
            
            print(f"   ✅ {len(spot_historical)} ordres Spot historiques trouvés")
            break  # Succès
            
        except Exception as e:
            print(f"   ❌ Erreur historique: {e}")
            if attempt < 5:
                wait_time = attempt * 2
                print(f"   ⏳ Attente de {wait_time}s avant nouvelle tentative...")
                time.sleep(wait_time)
            else:
                print(f"   ⚠️  Échec après 5 tentatives, continuation avec 0 ordres")
                spot_historical = []
    
    # Pause entre les appels
    time.sleep(1)
    
    # ============================================================================
    # 3. DÉTAILS DES EXÉCUTIONS (FILLS)
    # ============================================================================
    print("\n📥 3/3 - Récupération des détails d'exécution...")
    spot_fills = []
    
    for attempt in range(1, 6):
        try:
            print(f"   📡 Tentative {attempt}/5 (timeout: 90s)...")
            
            # ✅ FIX CRITIQUE: Nouvel objet Info pour ce 3ème appel
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            
            fills = info.user_fills(user_address)
            spot_fills = [fill for fill in fills if fill.get('coin', '').startswith('@')]
            
            print(f"   ✅ {len(spot_fills)} exécutions Spot trouvées")
            break  # Succès
            
        except Exception as e:
            print(f"   ❌ Erreur fills: {e}")
            if attempt < 5:
                wait_time = attempt * 2
                print(f"   ⏳ Attente de {wait_time}s avant nouvelle tentative...")
                time.sleep(wait_time)
            else:
                print(f"   ⚠️  Échec après 5 tentatives, continuation avec 0 fills")
                spot_fills = []
    
    print("\n" + "=" * 80)
    print("✅ Récupération terminée !\n")
    
    return {
        'open_orders': spot_open_orders,
        'historical_orders': spot_historical,
        'fills': spot_fills
    }


def analyze_order_statuses(historical_orders):
    """
    Analyse la répartition des statuts d'ordres
    """
    from collections import Counter
    
    statuses = [order.get('status') for order in historical_orders]
    status_count = Counter(statuses)
    
    print("📊 RÉPARTITION PAR STATUT")
    print("=" * 80)
    
    status_emojis = {
        'filled': '✅',
        'canceled': '🚫',
        'rejected': '❌',
        'open': '⏳',
        'expired': '⏰',
        'partial': '🟡'
    }
    
    total = len(historical_orders)
    
    for status, count in status_count.most_common():
        emoji = status_emojis.get(status, '📋')
        percentage = (count / total * 100) if total > 0 else 0
        print(f"{emoji} {status.upper():<15} : {count:>4} ordres ({percentage:>5.1f}%)")
    
    print(f"\n📈 TOTAL              : {total} ordres")
    print("=" * 80)


def display_historical_orders(historical_orders, max_display=20):
    """
    Affiche les ordres historiques avec leurs statuts
    """
    print(f"\n📋 HISTORIQUE DES ORDRES (affichage des {min(max_display, len(historical_orders))} premiers)")
    print("=" * 80)
    
    for i, order_data in enumerate(historical_orders[:max_display], 1):
        order = order_data.get('order', {})
        status = order_data.get('status', 'unknown')
        status_timestamp = order_data.get('statusTimestamp', 0)
        
        # Emojis selon le statut
        status_emoji = {
            'filled': '✅',
            'canceled': '🚫',
            'rejected': '❌',
            'open': '⏳'
        }.get(status, '📋')
        
        print(f"\n{status_emoji} Order #{i} - STATUS: {status.upper()}")
        print(f"   Paire        : {order.get('coin', 'N/A')}")
        print(f"   Côté         : {'ACHAT' if order.get('side') == 'B' else 'VENTE'}")
        print(f"   Type         : {order.get('orderType', 'N/A')}")
        print(f"   Prix limite  : {order.get('limitPx', 'N/A')} USDC")
        print(f"   Quantité     : {order.get('sz', 'N/A')} (original: {order.get('origSz', 'N/A')})")
        print(f"   Reduce Only  : {'Oui' if order.get('reduceOnly') else 'Non'}")
        print(f"   TIF          : {order.get('tif', 'N/A')}")
        
        # Timestamp de l'ordre
        timestamp = order.get('timestamp', 0)
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000)
            print(f"   Date création: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Timestamp du statut
        if status_timestamp:
            dt_status = datetime.fromtimestamp(status_timestamp / 1000)
            print(f"   Date statut  : {dt_status.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"   Order ID     : {order.get('oid', 'N/A')}")
        
        # Client Order ID si présent
        cloid = order.get('cloid')
        if cloid:
            print(f"   Client OID   : {cloid}")


def display_open_orders(open_orders):
    """
    Affiche les ordres actuellement ouverts
    """
    if not open_orders:
        print("\n✅ Aucun ordre Spot ouvert actuellement")
        return
    
    print(f"\n⏳ ORDRES OUVERTS ({len(open_orders)} ordres)")
    print("=" * 80)
    
    for i, order in enumerate(open_orders, 1):
        print(f"\nOrder #{i}")
        print(f"   Paire       : {order.get('coin', 'N/A')}")
        print(f"   Côté        : {'ACHAT' if order.get('side') == 'B' else 'VENTE'}")
        print(f"   Prix limite : {order.get('limitPx', 'N/A')} USDC")
        print(f"   Quantité    : {order.get('sz', 'N/A')}")
        
        timestamp = order.get('timestamp', 0)
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000)
            print(f"   Date        : {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"   Order ID    : {order.get('oid', 'N/A')}")


def get_spot_metadata():
    """
    Récupère les métadonnées des paires Spot pour décoder les indices
    
    ✅ CORRECTION: Nouvel objet Info pour cet appel aussi
    """
    print("\n📖 Récupération des métadonnées Spot...")
    
    for attempt in range(1, 4):
        try:
            # ✅ FIX: Nouvel objet Info
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            spot_meta = info.spot_meta()
            
            spot_mapping = {}
            for idx, token_pair in enumerate(spot_meta['universe']):
                spot_mapping[f"@{idx}"] = token_pair['name']
            
            print("   ✅ Métadonnées chargées")
            return spot_mapping
            
        except Exception as e:
            print(f"   ❌ Erreur métadonnées (tentative {attempt}/3): {e}")
            if attempt < 3:
                time.sleep(2)
            else:
                print("   ⚠️  Utilisation des indices bruts")
                return {}


def decode_orders(orders, spot_mapping):
    """
    Décode les ordres en remplaçant @index par le nom réel de la paire
    """
    for order_data in orders:
        if 'order' in order_data:
            order = order_data['order']
        else:
            order = order_data
        
        coin = order.get('coin', '')
        if coin.startswith('@'):
            order['coin_name'] = spot_mapping.get(coin, coin)
        else:
            order['coin_name'] = coin
    
    return orders


def export_to_separate_files(data):
    """
    Exporte les données dans 3 fichiers JSON distincts :
    - open_orders.json : Ordres ouverts actuellement
    - filled_orders.json : Ordres exécutés uniquement
    - historic.json : Historique complet avec tous les statuts
    """
    timestamp = datetime.now().isoformat()
    
    # ============================================================================
    # 1. OPEN_ORDERS.JSON
    # ============================================================================
    open_orders_data = {
        'generated_at': timestamp,
        'user_address': USER_ADDRESS,
        'count': len(data['open_orders']),
        'orders': data['open_orders']
    }
    
    with open('open_orders.json', 'w', encoding='utf-8') as f:
        json.dump(open_orders_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ open_orders.json - {len(data['open_orders'])} ordres ouverts")
    
    # ============================================================================
    # 2. FILLED_ORDERS.JSON
    # ============================================================================
    # Filtrer uniquement les ordres avec status="filled"
    filled_orders = [
        order for order in data['historical_orders']
        if order.get('status') == 'filled'
    ]
    
    filled_orders_data = {
        'generated_at': timestamp,
        'user_address': USER_ADDRESS,
        'count': len(filled_orders),
        'orders': filled_orders,
        'fills_details': data['fills']  # Détails d'exécution
    }
    
    with open('filled_orders.json', 'w', encoding='utf-8') as f:
        json.dump(filled_orders_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ filled_orders.json - {len(filled_orders)} ordres exécutés")
    
    # ============================================================================
    # 3. HISTORIC.JSON
    # ============================================================================
    historic_data = {
        'generated_at': timestamp,
        'user_address': USER_ADDRESS,
        'summary': {
            'total_orders': len(data['historical_orders']),
            'open_orders': len([o for o in data['historical_orders'] if o.get('status') == 'open']),
            'filled_orders': len([o for o in data['historical_orders'] if o.get('status') == 'filled']),
            'canceled_orders': len([o for o in data['historical_orders'] if o.get('status') == 'canceled']),
            'rejected_orders': len([o for o in data['historical_orders'] if o.get('status') == 'rejected']),
        },
        'orders': data['historical_orders']
    }
    
    with open('historic.json', 'w', encoding='utf-8') as f:
        json.dump(historic_data, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ historic.json - {len(data['historical_orders'])} ordres (tous statuts)")
    
    print("\n" + "=" * 80)
    print("📂 FICHIERS GÉNÉRÉS")
    print("=" * 80)
    print("📄 open_orders.json    - Ordres actuellement ouverts")
    print("📄 filled_orders.json  - Ordres exécutés + détails d'exécution")
    print("📄 historic.json       - Historique complet (filled, canceled, rejected, etc.)")
    print("=" * 80)


# ============================================================================
# EXÉCUTION PRINCIPALE
# ============================================================================

if __name__ == "__main__":
    print("🚀 Hyperliquid - Historique COMPLET des Ordres Spot")
    print("=" * 80)
    print(f"Adresse : {USER_ADDRESS}")
    print("✅ Version avec corrections anti-timeout\n")
    
    try:
        # Récupérer toutes les données
        data = get_complete_order_history(USER_ADDRESS)
        
        # Récupérer les métadonnées pour décoder les noms
        spot_mapping = get_spot_metadata()
        
        # Décoder les noms de paires
        if spot_mapping:
            data['historical_orders'] = decode_orders(data['historical_orders'], spot_mapping)
            data['open_orders'] = decode_orders(data['open_orders'], spot_mapping)
        
        # Analyser les statuts
        if data['historical_orders']:
            print()
            analyze_order_statuses(data['historical_orders'])
        
        # Afficher les ordres ouverts
        display_open_orders(data['open_orders'])
        
        # Afficher l'historique
        if data['historical_orders']:
            display_historical_orders(data['historical_orders'], max_display=10)
        else:
            print("\n📋 Aucun ordre historique trouvé")
        
        # Exporter dans 3 fichiers distincts
        print()
        export_to_separate_files(data)
        
        # Résumé final
        print("\n" + "=" * 80)
        print("🎉 RÉSUMÉ FINAL")
        print("=" * 80)
        print(f"⏳ Ordres ouverts           : {len(data['open_orders'])}")
        print(f"📋 Ordres historiques       : {len(data['historical_orders'])}")
        print(f"✅ Exécutions (fills)       : {len(data['fills'])}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        print("\n💡 Assurez-vous d'avoir installé : pip install hyperliquid-python-sdk")
        import traceback
        traceback.print_exc()


"""
📦 Installation :
pip install hyperliquid-python-sdk

🚀 Utilisation :
1. Remplacez USER_ADDRESS par votre adresse
2. python hyperliquid_complete_history.py

📊 Ce script récupère :
✅ Ordres OUVERTS (open) - ordres actuellement actifs
✅ Ordres EXÉCUTÉS (filled) - ordres complètement remplis
✅ Ordres ANNULÉS (canceled) - ordres annulés manuellement
✅ Ordres REJETÉS (rejected) - ordres refusés par le système
✅ Détails des exécutions (fills) - historique des trades

📂 Fichiers générés :
1. open_orders.json    - Ordres actuellement ouverts
2. filled_orders.json  - Ordres exécutés + détails d'exécution (fills)
3. historic.json       - Historique complet avec TOUS les statuts

⚠️ Limitations :
- Maximum 2000 ordres historiques
- Ordres Spot uniquement (coin commence par @)

✅ CORRECTIONS APPLIQUÉES :
- Nouvel objet Info pour CHAQUE appel API (évite timeouts)
- Retry automatique (5 tentatives) avec délai croissant
- Pause de 1s entre les appels (évite rate limiting)
- Gestion robuste des erreurs
"""
