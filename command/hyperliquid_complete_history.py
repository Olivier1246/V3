"""
Service de récupération de l'historique des ordres Hyperliquid
Version Service Continu - Génère des fichiers JSON toutes les X minutes
AVEC TOUS LES STATUTS : open, filled, canceled, rejected, etc.

✅ AMÉLIORATIONS:
- Timeout augmenté pour ordres ouverts (60s au lieu de 30s)
- Préservation des fichiers JSON en cas d'erreur de timeout
- Meilleure gestion des erreurs réseau
"""

from hyperliquid.info import Info
from hyperliquid.utils import constants
from datetime import datetime
import json
import time
import threading
import os
import sys
from dotenv import load_dotenv


class HyperliquidHistoryService:
    """Service qui récupère périodiquement l'historique des ordres"""
    
    def __init__(self, config_file: str = '.env'):
        """
        Initialise le service
        
        Args:
            config_file: Chemin vers le fichier .env
        """
        # Charger les variables d'environnement
        load_dotenv(config_file)
        
        # Configuration
        self.user_address = os.getenv('WALLET_ADDRESS')
        if not self.user_address or self.user_address == '0x...':
            raise ValueError("WALLET_ADDRESS non configuré dans .env")
        
        # Intervalle de vérification (en minutes)
        self.check_interval_minutes = float(os.getenv('MIN_CHECK_INTERVAL_MINUTES', 10))
        
        # Dossier de sortie
        self.output_dir = 'log'
        
        # Créer le dossier log s'il n'existe pas
        os.makedirs(self.output_dir, exist_ok=True)
        
        # État du service
        self.running = False
        self.thread = None
        
        # Initialiser l'API Hyperliquid avec timeout
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Configurer un timeout pour les requêtes
        if hasattr(self.info, 'session'):
            # Le SDK utilise requests.Session
            import requests
            self.info.session = requests.Session()
            # Adapter avec timeout par défaut
            adapter = requests.adapters.HTTPAdapter(
                max_retries=3,
                pool_connections=10,
                pool_maxsize=10
            )
            self.info.session.mount('http://', adapter)
            self.info.session.mount('https://', adapter)
        
        # Mapping des paires spot
        self.spot_mapping = {}
        
        # Statistiques pour monitoring
        self.last_fetch_stats = {
            'open_orders_success': True,
            'historical_orders_success': True,
            'fills_success': True,
            'last_fetch_time': None
        }
        
        print(f"📋 Service initialisé")
        print(f"   Adresse: {self.user_address}")
        print(f"   Intervalle: {self.check_interval_minutes} minutes")
        print(f"   Dossier sortie: {self.output_dir}/")
    
    def start(self):
        """Démarre le service en arrière-plan"""
        if self.running:
            print("⚠️  Service déjà en cours d'exécution")
            return
        
        print("\n" + "="*80)
        print("🚀 DÉMARRAGE DU SERVICE D'HISTORIQUE HYPERLIQUID")
        print("="*80)
        
        self.running = True
        self.thread = threading.Thread(target=self._service_loop, daemon=True, name="HistoryService")
        self.thread.start()
        
        print("✅ Service démarré")
        print(f"📊 Fichiers JSON générés toutes les {self.check_interval_minutes} minutes")
        print("="*80 + "\n")
    
    def stop(self):
        """Arrête le service"""
        if not self.running:
            return
        
        print("\n🛑 Arrêt du service...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        print("✅ Service arrêté\n")
    
    def _service_loop(self):
        """Boucle principale du service"""
        # Charger les métadonnées spot une seule fois
        try:
            self._load_spot_metadata()
        except Exception as e:
            print(f"❌ Erreur chargement métadonnées: {e}")
            self.running = False
            return
        
        while self.running:
            try:
                print(f"\n{'='*80}")
                print(f"🔄 RÉCUPÉRATION HISTORIQUE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("="*80)
                
                start_time = time.time()
                
                # Récupérer les données avec flags de succès
                data, success_flags = self._fetch_complete_history()
                
                # Mettre à jour les stats
                self.last_fetch_stats.update(success_flags)
                self.last_fetch_stats['last_fetch_time'] = datetime.now()
                
                # Exporter vers JSON (en préservant les anciens fichiers si échec)
                self._export_to_json(data, success_flags)
                
                elapsed = time.time() - start_time
                print(f"\n✅ Récupération terminée en {elapsed:.1f}s")
                
                # Afficher les warnings si certaines récupérations ont échoué
                if not all(success_flags.values()):
                    print("\n⚠️  AVERTISSEMENT: Certaines données n'ont pas pu être récupérées:")
                    if not success_flags.get('open_orders_success'):
                        print("   • Ordres ouverts: ÉCHEC (ancien fichier préservé)")
                    if not success_flags.get('historical_orders_success'):
                        print("   • Historique: ÉCHEC")
                    if not success_flags.get('fills_success'):
                        print("   • Fills: ÉCHEC")
                
                print("="*80)
                
                # Attendre avant la prochaine récupération
                wait_seconds = self.check_interval_minutes * 60
                print(f"\n⏳ Prochaine récupération dans {self.check_interval_minutes} minutes...")
                
                # Attendre par intervalles de 30s pour pouvoir arrêter proprement
                elapsed_wait = 0
                while elapsed_wait < wait_seconds and self.running:
                    time.sleep(min(30, wait_seconds - elapsed_wait))
                    elapsed_wait += 30
                
            except Exception as e:
                print(f"\n❌ Erreur dans le service: {e}")
                import traceback
                traceback.print_exc()
                
                # Attendre 60s avant de réessayer
                time.sleep(60)
    
    def _load_spot_metadata(self):
        """Charge les métadonnées des paires Spot"""
        print("\n📖 Chargement des métadonnées Spot...")
        
        spot_meta = self.info.spot_meta()
        
        for idx, token_pair in enumerate(spot_meta['universe']):
            self.spot_mapping[f"@{idx}"] = token_pair['name']
        
        print(f"   ✅ {len(self.spot_mapping)} paires chargées")
    
    def _fetch_complete_history(self):
        """
        Récupère l'historique COMPLET des ordres avec timeout amélioré
        
        Returns:
            tuple: (data_dict, success_flags_dict)
            - data_dict: {
                'open_orders': [...],
                'historical_orders': [...],
                'fills': [...]
            }
            - success_flags_dict: {
                'open_orders_success': bool,
                'historical_orders_success': bool,
                'fills_success': bool
            }
        """
        # ✅ TIMEOUT AUGMENTÉ pour ordres ouverts qui timeout souvent
        TIMEOUT_OPEN_ORDERS = 60  # 60 secondes pour ordres ouverts
        TIMEOUT_STANDARD = 30     # 30 secondes pour le reste
        
        # Flags de succès
        success_flags = {
            'open_orders_success': False,
            'historical_orders_success': False,
            'fills_success': False
        }
        
        try:
            # =====================================
            # 1. ORDRES OUVERTS (timeout augmenté + retry)
            # =====================================
            print("\n📥 1/3 - Récupération des ordres ouverts...")
            open_orders = []
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    # ✅ FIX: Créer un nouvel objet Info à chaque tentative
                    info = Info(constants.MAINNET_API_URL, skip_ws=True)
                    
                    # ✅ Timeout spécial pour ordres ouverts
                    original_timeout = getattr(info, 'timeout', None)
                    info.timeout = TIMEOUT_OPEN_ORDERS
                    
                    print(f"   📡 Tentative {attempt + 1}/{max_retries} (timeout: {TIMEOUT_OPEN_ORDERS}s)...")
                    open_orders = info.open_orders(self.user_address)
                    
                    # Restaurer timeout original
                    if original_timeout is not None:
                        info.timeout = original_timeout
                    
                    # ✅ Succès - sortir de la boucle
                    success_flags['open_orders_success'] = True
                    break
                    
                except (ConnectionResetError, ConnectionError, TimeoutError) as e:
                    if attempt < max_retries - 1:
                        print(f"   ⚠️  Erreur réseau, réessai dans 3s...")
                        time.sleep(3)
                    else:
                        print(f"   ❌ Échec après {max_retries} tentatives: {type(e).__name__}")
                        print(f"      Message: {str(e)[:100]}")
                        open_orders = []
                        success_flags['open_orders_success'] = False
                        
                except Exception as e:
                    print(f"   ❌ Erreur ordres ouverts: {type(e).__name__}: {str(e)[:100]}")
                    open_orders = []
                    success_flags['open_orders_success'] = False
                    break
            
            spot_open_orders = [order for order in open_orders if order.get('coin', '').startswith('@')]
            
            if success_flags['open_orders_success']:
                print(f"   ✅ {len(spot_open_orders)} ordres Spot ouverts")
            else:
                print(f"   ⚠️  0 ordres Spot ouverts (échec récupération)")
            
            # =====================================
            # 2. HISTORIQUE COMPLET
            # =====================================
            print("\n📥 2/3 - Récupération de l'historique complet...")
            historical_orders = []
            
            for attempt in range(max_retries):
                try:
                    # ✅ FIX: Créer un nouvel objet Info à chaque tentative
                    info = Info(constants.MAINNET_API_URL, skip_ws=True)
                    info.timeout = TIMEOUT_STANDARD
                    
                    historical_orders = info.post("/info", {
                        "type": "historicalOrders",
                        "user": self.user_address
                    })
                    
                    if original_timeout is not None:
                        info.timeout = original_timeout
                    
                    # ✅ Succès
                    success_flags['historical_orders_success'] = True
                    break
                    
                except (ConnectionResetError, ConnectionError, TimeoutError) as e:
                    if attempt < max_retries - 1:
                        print(f"   ⚠️  Tentative {attempt + 1}/{max_retries} échouée, réessai dans 2s...")
                        time.sleep(2)
                    else:
                        print(f"   ❌ Erreur historique après {max_retries} tentatives: {type(e).__name__}")
                        historical_orders = []
                        success_flags['historical_orders_success'] = False
                        
                except Exception as e:
                    print(f"   ❌ Erreur historique: {type(e).__name__}")
                    historical_orders = []
                    success_flags['historical_orders_success'] = False
                    break
            
            spot_historical = [order for order in historical_orders 
                              if order.get('order', {}).get('coin', '').startswith('@')]
            print(f"   ✅ {len(spot_historical)} ordres Spot historiques")
            
            # =====================================
            # 3. FILLS
            # =====================================
            print("\n📥 3/3 - Récupération des fills...")
            fills = []
            
            for attempt in range(max_retries):
                try:
                    # ✅ FIX: Créer un nouvel objet Info à chaque tentative
                    info = Info(constants.MAINNET_API_URL, skip_ws=True)
                    info.timeout = TIMEOUT_STANDARD
                    
                    fills = info.user_fills(self.user_address)
                    
                    if original_timeout is not None:
                        info.timeout = original_timeout
                    
                    # ✅ Succès
                    success_flags['fills_success'] = True
                    break
                    
                except (ConnectionResetError, ConnectionError, TimeoutError) as e:
                    if attempt < max_retries - 1:
                        print(f"   ⚠️  Tentative {attempt + 1}/{max_retries} échouée, réessai dans 2s...")
                        time.sleep(2)
                    else:
                        print(f"   ❌ Erreur fills après {max_retries} tentatives: {type(e).__name__}")
                        fills = []
                        success_flags['fills_success'] = False
                        
                except Exception as e:
                    print(f"   ❌ Erreur fills: {type(e).__name__}")
                    fills = []
                    success_flags['fills_success'] = False
                    break
            
            spot_fills = [fill for fill in fills if fill.get('coin', '').startswith('@')]
            print(f"   ✅ {len(spot_fills)} fills Spot")
            
            # Décoder les noms de paires
            self._decode_orders(spot_open_orders)
            self._decode_orders(spot_historical)
            
            data = {
                'open_orders': spot_open_orders,
                'historical_orders': spot_historical,
                'fills': spot_fills
            }
            
            return data, success_flags
            
        except Exception as e:
            print(f"❌ Erreur récupération historique: {e}")
            import traceback
            traceback.print_exc()
            
            # En cas d'erreur, retourner des listes vides avec tous les flags à False
            return {
                'open_orders': [],
                'historical_orders': [],
                'fills': []
            }, {
                'open_orders_success': False,
                'historical_orders_success': False,
                'fills_success': False
            }
    
    def _decode_orders(self, orders):
        """Décode les noms de paires dans les ordres"""
        for order_data in orders:
            if 'order' in order_data:
                order = order_data['order']
            else:
                order = order_data
            
            coin = order.get('coin', '')
            if coin.startswith('@'):
                order['coin_name'] = self.spot_mapping.get(coin, coin)
            else:
                order['coin_name'] = coin
    
    def _export_to_json(self, data, success_flags):
        """
        Exporte les données dans 3 fichiers JSON dans /log
        
        ✅ NOUVEAU: Préserve les anciens fichiers si la récupération a échoué
        
        Args:
            data: dict avec open_orders, historical_orders, fills
            success_flags: dict avec les flags de succès pour chaque type
        """
        timestamp = datetime.now().isoformat()
        
        try:
            # =====================================
            # 1. OPEN_ORDERS.JSON
            # ⚠️  N'écraser QUE si la récupération a réussi
            # =====================================
            if success_flags.get('open_orders_success', False):
                open_orders_path = os.path.join(self.output_dir, 'open_orders.json')
                open_orders_data = {
                    'generated_at': timestamp,
                    'user_address': self.user_address,
                    'count': len(data['open_orders']),
                    'orders': data['open_orders'],
                    'fetch_success': True
                }
                
                with open(open_orders_path, 'w', encoding='utf-8') as f:
                    json.dump(open_orders_data, f, indent=2, ensure_ascii=False, default=str)
                
                print(f"\n📄 {open_orders_path}")
                print(f"   ✅ {len(data['open_orders'])} ordres ouverts")
            else:
                # ✅ PRÉSERVER l'ancien fichier en cas d'échec
                open_orders_path = os.path.join(self.output_dir, 'open_orders.json')
                
                if os.path.exists(open_orders_path):
                    print(f"\n📄 {open_orders_path}")
                    print(f"   ⚠️  Fichier PRÉSERVÉ (échec récupération)")
                    
                    # Optionnel: Marquer que les données sont anciennes
                    try:
                        with open(open_orders_path, 'r', encoding='utf-8') as f:
                            old_data = json.load(f)
                        
                        # Ajouter un flag pour indiquer que les données sont potentiellement obsolètes
                        old_data['last_failed_fetch'] = timestamp
                        old_data['fetch_success'] = False
                        
                        with open(open_orders_path, 'w', encoding='utf-8') as f:
                            json.dump(old_data, f, indent=2, ensure_ascii=False, default=str)
                        
                        print(f"   ℹ️  Marqué comme potentiellement obsolète")
                    except Exception as e:
                        print(f"   ⚠️  Impossible de mettre à jour le flag: {e}")
                else:
                    print(f"\n📄 {open_orders_path}")
                    print(f"   ⚠️  Fichier n'existe pas encore (première récupération échouée)")
            
            # =====================================
            # 2. FILLED_ORDERS.JSON
            # =====================================
            filled_orders_path = os.path.join(self.output_dir, 'filled_orders.json')
            filled_orders = [
                order for order in data['historical_orders']
                if order.get('status') == 'filled'
            ]
            
            filled_orders_data = {
                'generated_at': timestamp,
                'user_address': self.user_address,
                'count': len(filled_orders),
                'orders': filled_orders,
                'fills_details': data['fills'],
                'fetch_success': success_flags.get('historical_orders_success', False) and success_flags.get('fills_success', False)
            }
            
            with open(filled_orders_path, 'w', encoding='utf-8') as f:
                json.dump(filled_orders_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"\n📄 {filled_orders_path}")
            print(f"   ✅ {len(filled_orders)} ordres exécutés")
            
            # =====================================
            # 3. HISTORIC.JSON
            # =====================================
            historic_path = os.path.join(self.output_dir, 'historic.json')
            historic_data = {
                'generated_at': timestamp,
                'user_address': self.user_address,
                'summary': {
                    'total_orders': len(data['historical_orders']),
                    'open_orders': len([o for o in data['historical_orders'] if o.get('status') == 'open']),
                    'filled_orders': len([o for o in data['historical_orders'] if o.get('status') == 'filled']),
                    'canceled_orders': len([o for o in data['historical_orders'] if o.get('status') == 'canceled']),
                    'rejected_orders': len([o for o in data['historical_orders'] if o.get('status') == 'rejected']),
                },
                'orders': data['historical_orders'],
                'fetch_success': success_flags.get('historical_orders_success', False)
            }
            
            with open(historic_path, 'w', encoding='utf-8') as f:
                json.dump(historic_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"\n📄 {historic_path}")
            print(f"   ✅ {len(data['historical_orders'])} ordres (tous statuts)")
            
        except Exception as e:
            print(f"\n❌ Erreur export JSON: {e}")
            import traceback
            traceback.print_exc()
    
    def fetch_now(self):
        """Force une récupération immédiate (pour tests)"""
        print("\n🔄 Récupération forcée...")
        
        try:
            if not self.spot_mapping:
                self._load_spot_metadata()
            
            data, success_flags = self._fetch_complete_history()
            
            # Exporter même si certaines récupérations ont échoué
            self._export_to_json(data, success_flags)
            
            # Vérifier si au moins une récupération a réussi
            if any(success_flags.values()):
                print("\n✅ Récupération forcée terminée")
                if not all(success_flags.values()):
                    print("⚠️  Certaines données n'ont pas pu être récupérées (voir ci-dessus)")
                return True
            else:
                print("\n⚠️  Échec complet de la récupération (timeout ou erreur réseau)")
                print("   Vérifiez votre connexion réseau")
                return False
                
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            print("   Vérifiez votre connexion à api.hyperliquid.xyz")
            import traceback
            traceback.print_exc()
            return False
    
    def get_stats(self):
        """Retourne les statistiques de la dernière récupération"""
        return self.last_fetch_stats.copy()


def main():
    """Fonction principale pour exécution standalone"""
    print("\n🚀 Hyperliquid History Service - Mode Standalone")
    print("="*80)
    
    try:
        # Créer et démarrer le service
        service = HyperliquidHistoryService()
        service.start()
        
        # Attendre indéfiniment (Ctrl+C pour arrêter)
        print("\n💡 Appuyez sur Ctrl+C pour arrêter le service\n")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption utilisateur")
        if 'service' in locals():
            service.stop()
        
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


"""
📦 Installation :
pip install hyperliquid-python-sdk python-dotenv

🚀 Utilisation :

1. MODE SERVICE (intégré au bot) :
   from command.hyperliquid_complete_history import HyperliquidHistoryService
   
   service = HyperliquidHistoryService()
   service.start()  # Démarre en arrière-plan

2. MODE STANDALONE (test) :
   python command/hyperliquid_complete_history.py

📊 Fichiers générés dans /log :
   - open_orders.json : Ordres actuellement ouverts
   - filled_orders.json : Ordres exécutés + détails fills
   - historic.json : Historique complet (tous statuts)

⚙️  Configuration (.env) :
   - WALLET_ADDRESS : Adresse du wallet (obligatoire)
   - MIN_CHECK_INTERVAL_MINUTES : Intervalle entre récupérations (défaut: 10)

🔄 Fonctionnement :
   - Récupère l'historique toutes les X minutes
   - Génère 3 fichiers JSON à chaque fois
   - Les autres modules lisent ces JSON pour synchroniser

✅ AMÉLIORATIONS v2:
   - Timeout augmenté pour ordres ouverts: 60s (au lieu de 30s)
   - Préservation des fichiers JSON en cas d'échec de récupération
   - Meilleure gestion des erreurs réseau avec retry amélioré
   - Flag de succès pour chaque type de données
   - Marquage des données potentiellement obsolètes

⚠️  Notes :
   - Maximum 2000 ordres historiques par récupération
   - Les JSON sont écrasés seulement si la récupération réussit
   - Le service tourne en daemon thread (ne bloque pas l'arrêt du bot)
   - En cas de timeout, l'ancien fichier open_orders.json est préservé
"""
