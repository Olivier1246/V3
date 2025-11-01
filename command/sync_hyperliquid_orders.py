"""
Module de synchronisation des ordres Hyperliquid
Vérifie le statut réel des ordres et met à jour la BDD
"""

import time
import threading
from datetime import datetime, timezone
from typing import Dict, Optional, List
from config import TradingConfig
from DB.database import Database
from command.trading_engine import TradingEngine
from command.logger import TradingLogger


class OrderSynchronizer:
    """Synchronise les ordres avec Hyperliquid toutes les 5 minutes"""
    
    def __init__(self, config: TradingConfig, database: Database, 
                 trading_engine: TradingEngine, logger: TradingLogger, telegram=None):
        self.config = config
        self.database = database
        self.trading_engine = trading_engine
        self.logger = logger
        self.telegram = telegram
        
        self.running = False
        self.thread = None
        self.sync_interval = 300  # 5 minutes (en secondes)
        
        self.logger.info("🔄 [SYNC] Module de synchronisation initialisé")
    
    def start(self):
        """Démarre le thread de synchronisation"""
        if self.running:
            self.logger.warning("⚠️  Thread de synchronisation déjà en cours")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._sync_loop, daemon=True, name="SyncThread")
        self.thread.start()
        self.logger.info("✅ Thread de synchronisation démarré")
    
    def stop(self):
        """Arrête le thread de synchronisation"""
        if not self.running:
            return
        
        self.logger.info("🛑 Arrêt du thread de synchronisation...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        self.logger.info("✅ Thread de synchronisation arrêté")
    
    def _sync_loop(self):
        """Boucle principale de synchronisation"""
        self.logger.info("🔄 Boucle de synchronisation démarrée")
        
        while self.running:
            try:
                self.logger.info(f"\n{'='*60}")
                self.logger.info("🔄 Synchronisation avec Hyperliquid...")
                
                start_time = time.time()
                
                # Synchroniser les ordres
                self._sync_orders()
                
                elapsed = time.time() - start_time
                self.logger.info(f"✅ Synchronisation terminée ({elapsed:.1f}s)")
                
                # Attendre avant la prochaine synchronisation
                time.sleep(self.sync_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Erreur dans boucle de synchronisation: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)
        
        self.logger.info("🔚 Boucle de synchronisation terminée")
    
    def _sync_orders(self):
        """Synchronise tous les ordres actifs"""
        # Récupérer les ordres ouverts sur Hyperliquid
        open_orders = self.trading_engine.get_open_orders()
        
        if open_orders is None:
            self.logger.error("❌ Impossible de récupérer les ordres ouverts")
            return
        
        self.logger.info(f"📊 {len(open_orders)} ordre(s) ouvert(s) sur Hyperliquid")
        
        # Vérifier les ordres d'achat
        self._check_buy_orders(open_orders)
        
        # Vérifier les ordres de vente
        self._check_sell_orders(open_orders)
    
    def _check_buy_orders(self, open_orders: List[dict]):
        """Vérifie les ordres d'achat et met à jour leur statut"""
        
        # Récupérer les paires en attente d'achat
        buy_pairs = self.database.get_pairs_by_status('Buy')
        
        if not buy_pairs:
            return
        
        self.logger.info(f"📊 {len(buy_pairs)} paire(s) en attente d'achat dans BDD")
        
        # Récupérer l'historique des trades récents
        try:
            user_fills = self.trading_engine.info.user_fills(self.trading_engine.account_address)
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération user_fills: {e}")
            user_fills = []
        
        for pair in buy_pairs:
            buy_order_id = str(pair.buy_order_id)
            
            # 1. Vérifier si l'ordre est toujours ouvert
            is_open = any(str(order['id']) == buy_order_id for order in open_orders)
            
            if is_open:
                # L'ordre est toujours ouvert
                continue
            
            # 2. L'ordre n'est plus ouvert - vérifier s'il a été FILLED
            order_fills = [fill for fill in user_fills if str(fill.get('oid')) == buy_order_id]
            
            if order_fills:
                # ✅ L'ordre a été rempli
                total_filled = sum(float(fill.get('sz', 0)) for fill in order_fills)
                
                if total_filled >= pair.quantity_btc * 0.99:  # Tolérance 1%
                    self.logger.info(f"✅ Ordre d'achat {buy_order_id} rempli (Filled)")
                    self.logger.info(f"   Quantité: {total_filled:.8f} BTC")
                    
                    # Mettre à jour le statut
                    self.database.update_pair_status(pair.index, 'Sell')
                    self.logger.info(f"✅ Paire {pair.index} - Achat rempli, status -> Sell")
                    
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
                else:
                    self.logger.warning(f"⚠️  Ordre {buy_order_id} partiellement rempli")
                    self.logger.warning(f"   Attendu: {pair.quantity_btc:.8f}, Rempli: {total_filled:.8f}")
            else:
                # L'ordre n'est ni ouvert ni dans les fills - probablement annulé
                self.logger.warning(f"⚠️  Ordre d'achat {buy_order_id} introuvable")
                self.logger.warning(f"   Peut avoir été annulé - vérification manuelle requise")
    
    def _check_sell_orders(self, open_orders: List[dict]):
        """Vérifie les ordres de vente et met à jour leur statut"""
        
        # Récupérer les paires en attente de vente
        sell_pairs = self.database.get_pairs_by_status('Sell')
        
        if not sell_pairs:
            return
        
        self.logger.info(f"📊 {len(sell_pairs)} paire(s) en attente de vente dans BDD")
        
        # Récupérer l'historique des trades récents
        try:
            user_fills = self.trading_engine.info.user_fills(self.trading_engine.account_address)
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération user_fills: {e}")
            user_fills = []
        
        for pair in sell_pairs:
            sell_order_id = getattr(pair, 'sell_order_id', None)
            
            if not sell_order_id:
                # Ordre de vente pas encore placé
                continue
            
            sell_order_id = str(sell_order_id)
            
            # 1. Vérifier si l'ordre est toujours ouvert
            is_open = any(str(order['id']) == sell_order_id for order in open_orders)
            
            if is_open:
                # L'ordre est toujours ouvert
                continue
            
            # 2. L'ordre n'est plus ouvert - vérifier s'il a été FILLED
            order_fills = [fill for fill in user_fills if str(fill.get('oid')) == sell_order_id]
            
            if order_fills:
                # ✅ L'ordre a été rempli
                total_filled = sum(float(fill.get('sz', 0)) for fill in order_fills)
                
                if total_filled >= pair.quantity_btc * 0.99:  # Tolérance 1%
                    self.logger.info(f"✅ Ordre de vente {sell_order_id} rempli (Filled)")
                    self.logger.info(f"   Quantité: {total_filled:.8f} BTC")
                    
                    # Calculer le profit
                    profit = (pair.sell_price_btc - pair.buy_price_btc) * total_filled
                    profit_percent = ((pair.sell_price_btc - pair.buy_price_btc) / pair.buy_price_btc) * 100
                    
                    # Mettre à jour le statut
                    self.database.update_pair_status(pair.index, 'Complete')
                    self.logger.info(f"✅ Paire {pair.index} - Vente remplie, status -> Complete")
                    self.logger.info(f"💰 Profit: {profit:.2f}$ ({profit_percent:+.2f}%)")
                    
                    # Notification Telegram
                    if self.telegram and self.config.telegram_on_order_filled:
                        try:
                            self.telegram.send_sell_order_filled(
                                order_id=sell_order_id,
                                price=pair.sell_price_btc,
                                size=total_filled,
                                buy_price=pair.buy_price_btc,
                                profit=profit,
                                profit_percent=profit_percent
                            )
                        except Exception as e:
                            self.logger.error(f"❌ Erreur notification: {e}")
                else:
                    self.logger.warning(f"⚠️  Ordre {sell_order_id} partiellement rempli")
                    self.logger.warning(f"   Attendu: {pair.quantity_btc:.8f}, Rempli: {total_filled:.8f}")
            else:
                # L'ordre n'est ni ouvert ni dans les fills
                self.logger.warning(f"⚠️  Ordre de vente {sell_order_id} introuvable")
                self.logger.warning(f"   Peut avoir été annulé - vérification manuelle requise")
    
    def force_sync(self):
        """Force une synchronisation immédiate (pour debug)"""
        self.logger.info("🔄 Synchronisation forcée...")
        try:
            self._sync_orders()
        except Exception as e:
            self.logger.error(f"❌ Erreur synchronisation forcée: {e}")
            import traceback
            traceback.print_exc()