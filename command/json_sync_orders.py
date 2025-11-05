"""
Module de synchronisation des ordres via fichiers JSON
Lit les fichiers générés par hyperliquid_complete_history.py
Remplace sync_hyperliquid_orders.py avec une approche basée sur JSON

✅ AVANTAGES:
- Pas de surcharge API (lecture fichiers locaux)
- Données cohérentes (même snapshot pour tous les modules)
- Plus rapide (pas d'attente réseau)
- Meilleure observabilité (fichiers JSON consultables)
"""

import json
import os
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Optional, List
from config import TradingConfig
from DB.database import Database
from command.logger import TradingLogger


class JsonOrderSynchronizer:
    """Synchronise les ordres en lisant les fichiers JSON"""
    
    def __init__(self, config: TradingConfig, database: Database, 
                 logger: TradingLogger, telegram=None):
        self.config = config
        self.database = database
        self.logger = logger
        self.telegram = telegram
        
        # Chemins des fichiers JSON
        self.json_dir = 'log'
        self.open_orders_file = os.path.join(self.json_dir, 'open_orders.json')
        self.filled_orders_file = os.path.join(self.json_dir, 'filled_orders.json')
        self.historic_file = os.path.join(self.json_dir, 'historic.json')
        
        # État
        self.running = False
        self.thread = None
        
        # Intervalle de synchronisation (en secondes)
        # On vérifie toutes les minutes si les JSON ont été mis à jour
        self.sync_interval = 60
        
        # Cache des dernières modifications
        self.last_open_mtime = 0
        self.last_filled_mtime = 0
        self.last_historic_mtime = 0
        
        self.logger.info("🔄 [JSON SYNC] Module de synchronisation JSON initialisé")
        self.logger.info(f"   Dossier JSON: {self.json_dir}/")
    
    def start(self):
        """Démarre le thread de synchronisation"""
        if self.running:
            self.logger.warning("⚠️  Thread de synchronisation déjà en cours")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._sync_loop, daemon=True, name="JsonSyncThread")
        self.thread.start()
        self.logger.info("✅ Thread de synchronisation JSON démarré")
    
    def stop(self):
        """Arrête le thread de synchronisation"""
        if not self.running:
            return
        
        self.logger.info("🛑 Arrêt du thread de synchronisation JSON...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        self.logger.info("✅ Thread de synchronisation JSON arrêté")
    
    def _sync_loop(self):
        """Boucle principale de synchronisation"""
        self.logger.info("🔄 Boucle de synchronisation JSON démarrée")
        
        while self.running:
            try:
                # Vérifier si les fichiers JSON ont été mis à jour
                if self._check_json_updates():
                    self.logger.info(f"\n{'='*60}")
                    self.logger.info("🔄 Nouveaux JSON détectés - Synchronisation...")
                    
                    start_time = time.time()
                    
                    # Synchroniser les ordres
                    self._sync_orders()
                    
                    elapsed = time.time() - start_time
                    self.logger.info(f"✅ Synchronisation terminée ({elapsed:.1f}s)")
                    self.logger.info(f"{'='*60}")
                
                # Attendre avant la prochaine vérification
                time.sleep(self.sync_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Erreur dans boucle de synchronisation: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)
        
        self.logger.info("🔚 Boucle de synchronisation JSON terminée")
    
    def _check_json_updates(self) -> bool:
        """
        Vérifie si les fichiers JSON ont été mis à jour
        
        Returns:
            bool: True si au moins un fichier a été modifié
        """
        updated = False
        
        # Vérifier open_orders.json
        if os.path.exists(self.open_orders_file):
            mtime = os.path.getmtime(self.open_orders_file)
            if mtime > self.last_open_mtime:
                self.last_open_mtime = mtime
                updated = True
        
        # Vérifier filled_orders.json
        if os.path.exists(self.filled_orders_file):
            mtime = os.path.getmtime(self.filled_orders_file)
            if mtime > self.last_filled_mtime:
                self.last_filled_mtime = mtime
                updated = True
        
        # Vérifier historic.json
        if os.path.exists(self.historic_file):
            mtime = os.path.getmtime(self.historic_file)
            if mtime > self.last_historic_mtime:
                self.last_historic_mtime = mtime
                updated = True
        
        return updated
    
    def _load_json(self, filepath: str) -> Optional[Dict]:
        """
        Charge un fichier JSON
        
        Args:
            filepath: Chemin du fichier JSON
            
        Returns:
            dict ou None si erreur
        """
        try:
            if not os.path.exists(filepath):
                self.logger.warning(f"⚠️  Fichier non trouvé: {filepath}")
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lecture {filepath}: {e}")
            return None
    
    def _sync_orders(self):
        """Synchronise tous les ordres actifs depuis les JSON"""
        # Charger les JSON
        open_orders_data = self._load_json(self.open_orders_file)
        filled_orders_data = self._load_json(self.filled_orders_file)
        historic_data = self._load_json(self.historic_file)
        
        if not open_orders_data or not filled_orders_data or not historic_data:
            self.logger.error("❌ Impossible de charger tous les JSON")
            return
        
        # Synchroniser les ordres d'achat et de vente
        self._check_buy_orders(open_orders_data, filled_orders_data)
        self._check_sell_orders(open_orders_data, filled_orders_data)
    
    def _get_order_status_from_json(self, order_id: str, open_orders_data: Dict, 
                                     filled_orders_data: Dict) -> Dict:
        """
        Récupère le statut d'un ordre depuis les JSON
        
        Args:
            order_id: ID de l'ordre
            open_orders_data: Données de open_orders.json
            filled_orders_data: Données de filled_orders.json
            
        Returns:
            dict: {
                'status': 'open' | 'filled' | 'unknown',
                'timestamp': int,
                'size': float,
                'source': str
            }
        """
        try:
            # 1. Vérifier si l'ordre est OUVERT
            for order in open_orders_data.get('orders', []):
                if str(order.get('oid', order.get('id'))) == str(order_id):
                    self.logger.info(f"📊 Order ID {order_id} - Status: OPEN")
                    return {
                        'status': 'open',
                        'timestamp': order.get('timestamp', int(time.time() * 1000)),
                        'size': float(order.get('sz', order.get('amount', 0))),
                        'source': 'open_orders_json'
                    }
            
            # 2. Vérifier si l'ordre est REMPLI
            # Calculer la quantité totale remplie depuis fills_details
            total_filled = 0.0
            latest_fill_time = 0
            
            for fill in filled_orders_data.get('fills_details', []):
                if str(fill.get('oid')) == str(order_id):
                    total_filled += float(fill.get('sz', 0))
                    fill_time = fill.get('time', 0)
                    if fill_time > latest_fill_time:
                        latest_fill_time = fill_time
            
            if total_filled > 0:
                self.logger.info(f"📊 Order ID {order_id} - Status: FILLED")
                self.logger.info(f"   Quantité totale: {total_filled:.8f}")
                return {
                    'status': 'filled',
                    'timestamp': latest_fill_time,
                    'size': total_filled,
                    'source': 'filled_orders_json'
                }
            
            # 3. Aucun enregistrement trouvé
            self.logger.warning(f"⚠️  Order ID {order_id} - Aucun enregistrement trouvé dans les JSON")
            return {
                'status': 'unknown',
                'timestamp': 0,
                'size': 0,
                'source': 'none'
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur _get_order_status_from_json: {e}")
            import traceback
            traceback.print_exc()
            return {
                'status': 'unknown',
                'timestamp': 0,
                'size': 0,
                'source': 'error'
            }
    
    def _check_buy_orders(self, open_orders_data: Dict, filled_orders_data: Dict):
        """
        Vérifie les ordres d'achat
        ✅ CORRECTION: Met à jour la quantité BTC réelle après fill
        """
        # Récupérer les paires en attente d'achat
        buy_pairs = self.database.get_pairs_by_status('Buy')
        
        if not buy_pairs:
            return
        
        self.logger.info(f"📊 {len(buy_pairs)} paire(s) en attente d'achat dans BDD")
        
        for pair in buy_pairs:
            try:
                buy_order_id = str(pair.buy_order_id)
                
                # Récupérer le statut depuis les JSON
                order_status = self._get_order_status_from_json(
                    buy_order_id, open_orders_data, filled_orders_data
                )
                
                status = order_status['status']
                
                if status == 'open':
                    # Ordre encore ouvert - RAS
                    self.logger.info(f"⏳ Ordre d'achat {buy_order_id} - Toujours OUVERT")
                    
                elif status == 'filled':
                    # Ordre rempli - Passer en mode Sell
                    total_filled = order_status['size']
                    
                    self.logger.info(f"✅ Ordre d'achat {buy_order_id} REMPLI")
                    self.logger.info(f"   Quantité calculée: {pair.quantity_btc:.8f} BTC")
                    self.logger.info(f"   Quantité réelle: {total_filled:.8f} BTC")
                    
                    # 1️⃣ Mettre à jour la quantité BTC réelle
                    self.database.update_quantity_btc(pair.index, total_filled)
                    
                    # 2️⃣ Mettre à jour le statut
                    self.database.update_pair_status(pair.index, 'Sell')
                    self.logger.info(f"✅ Paire {pair.index} - Status mis à jour: Buy -> Sell")
                    
                    # Notification Telegram
                    if self.telegram and self.config.telegram_on_order_filled:
                        try:
                            self.telegram.send_buy_order_filled(
                                order_id=buy_order_id,
                                price=pair.buy_price_btc,
                                size=total_filled
                            )
                        except Exception as e:
                            self.logger.error(f"❌ Erreur notification: {e}")
                
                else:  # unknown
                    self.logger.warning(f"❓ Ordre d'achat {buy_order_id} - Statut INCONNU")
                    self.logger.warning(f"   Vérification manuelle recommandée pour paire {pair.index}")
                
            except Exception as e:
                self.logger.error(f"❌ Erreur vérification paire {pair.index}: {e}")
                import traceback
                traceback.print_exc()
    
    def _check_sell_orders(self, open_orders_data: Dict, filled_orders_data: Dict):
        """Vérifie les ordres de vente"""
        # Récupérer les paires en attente de vente
        sell_pairs = self.database.get_pairs_by_status('Sell')
        
        if not sell_pairs:
            return
        
        self.logger.info(f"📊 {len(sell_pairs)} paire(s) en attente de vente dans BDD")
        
        for pair in sell_pairs:
            try:
                sell_order_id = getattr(pair, 'sell_order_id', None)
                
                if not sell_order_id:
                    # Ordre de vente pas encore placé
                    continue
                
                sell_order_id = str(sell_order_id)
                
                # Récupérer le statut depuis les JSON
                order_status = self._get_order_status_from_json(
                    sell_order_id, open_orders_data, filled_orders_data
                )
                
                status = order_status['status']
                
                if status == 'open':
                    # Ordre encore ouvert - RAS
                    self.logger.info(f"⏳ Ordre de vente {sell_order_id} - Toujours OUVERT")
                    
                elif status == 'filled':
                    # Ordre rempli - Cycle complété
                    total_filled = order_status['size']
                    
                    # Vérifier si la quantité correspond
                    if total_filled >= pair.quantity_btc * 0.99:  # Tolérance 1%
                        self.logger.info(f"✅ Ordre de vente {sell_order_id} REMPLI")
                        self.logger.info(f"   Quantité: {total_filled:.8f} BTC")
                        
                        # Calculer le profit (AVEC frais maker uniquement)
                        maker_fee_percent = self.config.maker_fee / 100
                        
                        buy_cost = pair.buy_price_btc * pair.quantity_btc
                        sell_revenue = pair.sell_price_btc * pair.quantity_btc
                        gross_profit = sell_revenue - buy_cost
                        
                        buy_fee = buy_cost * maker_fee_percent
                        sell_fee = sell_revenue * maker_fee_percent
                        total_fees = buy_fee + sell_fee
                        
                        net_profit = gross_profit - total_fees
                        profit_percent = ((pair.sell_price_btc - pair.buy_price_btc) / pair.buy_price_btc) * 100
                        
                        # Mettre à jour le statut dans la BDD
                        self.database.update_pair_status(pair.index, 'Complete')
                        self.logger.info(f"✅ Paire {pair.index} - Status mis à jour: Sell -> Complete")
                        self.logger.info(f"💰 Profit brut: {gross_profit:.2f}$")
                        self.logger.info(f"💰 Frais maker: {total_fees:.4f}$")
                        self.logger.info(f"💰 Profit net: {net_profit:.2f}$ ({profit_percent:+.2f}%)")
                        
                        # Notification Telegram
                        if self.telegram and self.config.telegram_on_order_filled:
                            try:
                                self.telegram.send_sell_order_filled(
                                    order_id=sell_order_id,
                                    price=pair.sell_price_btc,
                                    size=total_filled,
                                    buy_price=pair.buy_price_btc,
                                    profit=net_profit,
                                    profit_percent=profit_percent
                                )
                            except Exception as e:
                                self.logger.error(f"❌ Erreur notification: {e}")
                    else:
                        self.logger.warning(f"⚠️  Ordre {sell_order_id} partiellement rempli")
                        self.logger.warning(f"   Attendu: {pair.quantity_btc:.8f}, Rempli: {total_filled:.8f}")
                
                else:  # unknown
                    self.logger.warning(f"❓ Ordre de vente {sell_order_id} - Statut INCONNU")
                    self.logger.warning(f"   Vérification manuelle recommandée pour paire {pair.index}")
                
            except Exception as e:
                self.logger.error(f"❌ Erreur vérification paire {pair.index}: {e}")
                import traceback
                traceback.print_exc()
    
    def force_sync(self):
        """Force une synchronisation immédiate (pour debug)"""
        self.logger.info("🔄 Synchronisation forcée...")
        try:
            # Forcer la détection de mise à jour
            self.last_open_mtime = 0
            self.last_filled_mtime = 0
            self.last_historic_mtime = 0
            
            # Charger et synchroniser
            open_orders_data = self._load_json(self.open_orders_file)
            filled_orders_data = self._load_json(self.filled_orders_file)
            historic_data = self._load_json(self.historic_file)
            
            if open_orders_data and filled_orders_data and historic_data:
                self._check_buy_orders(open_orders_data, filled_orders_data)
                self._check_sell_orders(open_orders_data, filled_orders_data)
                self.logger.info("✅ Synchronisation forcée terminée")
            else:
                self.logger.error("❌ Impossible de charger les JSON")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur synchronisation forcée: {e}")
            import traceback
            traceback.print_exc()
