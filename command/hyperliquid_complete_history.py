"""
Service de récupération de l'historique des ordres Hyperliquid
Version Service Continu - Génère des fichiers JSON toutes les X minutes
AVEC TOUS LES STATUTS : open, filled, canceled, rejected, etc.
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
        
        # Configurer un timeout pour les requêtes (30 secondes)
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
                
                # Récupérer les données
                data = self._fetch_complete_history()
                
                if data and (data['open_orders'] or data['historical_orders'] or data['fills']):
                    # Exporter vers JSON seulement si on a des données
                    self._export_to_json(data)
                    
                    elapsed = time.time() - start_time
                    print(f"\n✅ Récupération terminée en {elapsed:.1f}s")
                else:
                    print("\n⚠️  Aucune donnée récupérée (possiblement timeout ou erreur réseau)")
                    print("   Réessai à la prochaine récupération...")
                
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
        Récupère l'historique COMPLET des ordres avec timeout
        
        Returns:
            dict: {
                'open_orders': [...],
                'historical_orders': [...],
                'fills': [...]
            }
        """
        # Timeout pour chaque requête (en secondes)
        TIMEOUT = 30
        
        try:
            # 1. Ordres ouverts (avec timeout et retry)
            print("\n📥 1/3 - Récupération des ordres ouverts...")
            open_orders = []
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    # Ajouter timeout explicite
                    original_timeout = getattr(self.info, 'timeout', None)
                    self.info.timeout = TIMEOUT
                    
                    open_orders = self.info.open_orders(self.user_address)
                    
                    # Restaurer timeout original
                    if original_timeout is not None:
                        self.info.timeout = original_timeout
                    
                    # Succès - sortir de la boucle
                    break
                    
                except (ConnectionResetError, ConnectionError) as e:
                    if attempt < max_retries - 1:
                        print(f"   ⚠️  Tentative {attempt + 1}/{max_retries} échouée, réessai dans 2s...")
                        time.sleep(2)
                    else:
                        print(f"   ⚠️  Erreur ordres ouverts après {max_retries} tentatives: {e}")
                        open_orders = []
                        
                except Exception as e:
                    print(f"   ⚠️  Erreur ordres ouverts: {e}")
                    open_orders = []
                    break
            
            spot_open_orders = [order for order in open_orders if order.get('coin', '').startswith('@')]
            print(f"   ✅ {len(spot_open_orders)} ordres Spot ouverts")
            
            # 2. Historique complet (avec timeout et retry)
            print("\n📥 2/3 - Récupération de l'historique complet...")
            historical_orders = []
            
            for attempt in range(max_retries):
                try:
                    self.info.timeout = TIMEOUT
                    
                    historical_orders = self.info.post("/info", {
                        "type": "historicalOrders",
                        "user": self.user_address
                    })
                    
                    if original_timeout is not None:
                        self.info.timeout = original_timeout
                    
                    # Succès - sortir de la boucle
                    break
                    
                except (ConnectionResetError, ConnectionError) as e:
                    if attempt < max_retries - 1:
                        print(f"   ⚠️  Tentative {attempt + 1}/{max_retries} échouée, réessai dans 2s...")
                        time.sleep(2)
                    else:
                        print(f"   ⚠️  Erreur historique après {max_retries} tentatives: {e}")
                        historical_orders = []
                        
                except Exception as e:
                    print(f"   ⚠️  Erreur historique: {e}")
                    historical_orders = []
                    break
            
            spot_historical = [order for order in historical_orders 
                              if order.get('order', {}).get('coin', '').startswith('@')]
            print(f"   ✅ {len(spot_historical)} ordres Spot historiques")
            
            # 3. Fills (avec timeout et retry)
            print("\n📥 3/3 - Récupération des fills...")
            fills = []
            
            for attempt in range(max_retries):
                try:
                    self.info.timeout = TIMEOUT
                    
                    fills = self.info.user_fills(self.user_address)
                    
                    if original_timeout is not None:
                        self.info.timeout = original_timeout
                    
                    # Succès - sortir de la boucle
                    break
                    
                except (ConnectionResetError, ConnectionError) as e:
                    if attempt < max_retries - 1:
                        print(f"   ⚠️  Tentative {attempt + 1}/{max_retries} échouée, réessai dans 2s...")
                        time.sleep(2)
                    else:
                        print(f"   ⚠️  Erreur fills après {max_retries} tentatives: {e}")
                        fills = []
                        
                except Exception as e:
                    print(f"   ⚠️  Erreur fills: {e}")
                    fills = []
                    break
            
            spot_fills = [fill for fill in fills if fill.get('coin', '').startswith('@')]
            print(f"   ✅ {len(spot_fills)} fills Spot")
            
            # Décoder les noms de paires
            self._decode_orders(spot_open_orders)
            self._decode_orders(spot_historical)
            
            return {
                'open_orders': spot_open_orders,
                'historical_orders': spot_historical,
                'fills': spot_fills
            }
            
        except Exception as e:
            print(f"❌ Erreur récupération historique: {e}")
            # En cas d'erreur, retourner des listes vides plutôt que None
            return {
                'open_orders': [],
                'historical_orders': [],
                'fills': []
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
    
    def _export_to_json(self, data):
        """
        Exporte les données dans 3 fichiers JSON dans /log
        
        Args:
            data: dict avec open_orders, historical_orders, fills
        """
        timestamp = datetime.now().isoformat()
        
        try:
            # 1. open_orders.json
            open_orders_path = os.path.join(self.output_dir, 'open_orders.json')
            open_orders_data = {
                'generated_at': timestamp,
                'user_address': self.user_address,
                'count': len(data['open_orders']),
                'orders': data['open_orders']
            }
            
            with open(open_orders_path, 'w', encoding='utf-8') as f:
                json.dump(open_orders_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"\n📄 {open_orders_path}")
            print(f"   ✅ {len(data['open_orders'])} ordres ouverts")
            
            # 2. filled_orders.json
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
                'fills_details': data['fills']
            }
            
            with open(filled_orders_path, 'w', encoding='utf-8') as f:
                json.dump(filled_orders_data, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"\n📄 {filled_orders_path}")
            print(f"   ✅ {len(filled_orders)} ordres exécutés")
            
            # 3. historic.json
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
                'orders': data['historical_orders']
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
            
            data = self._fetch_complete_history()
            
            if data and (data['open_orders'] or data['historical_orders'] or data['fills']):
                self._export_to_json(data)
                print("\n✅ Récupération forcée terminée")
                return True
            else:
                print("\n⚠️  Échec récupération forcée (timeout ou aucune donnée)")
                print("   Vérifiez votre connexion réseau")
                return False
                
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            print("   Vérifiez votre connexion à api.hyperliquid.xyz")
            return False


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

⚠️  Notes :
   - Maximum 2000 ordres historiques par récupération
   - Les JSON sont écrasés à chaque récupération (toujours à jour)
   - Le service tourne en daemon thread (ne bloque pas l'arrêt du bot)
"""
