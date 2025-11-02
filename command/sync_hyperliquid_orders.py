"""
Module de synchronisation des ordres Hyperliquid
Vérifie le statut réel des ordres et met à jour la BDD

✅ CORRECTIONS APPLIQUÉES:
- Met à jour la quantité BTC RÉELLE après fill de l'ordre d'achat
- Prend en compte les frais MAKER uniquement (mode spot limit)
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
        # Vérifier les ordres d'achat
        self._check_buy_orders()
        
        # Vérifier les ordres de vente
        self._check_sell_orders()
    
    def _get_order_status_from_history(self, order_id: str) -> Dict:
        """🆕 Récupère le statut le plus récent d'un Order ID depuis l'historique
        
        Logique:
        1. Récupérer TOUS les enregistrements avec cet Order ID
        2. Trier par Time (le plus récent en premier)
        3. Retourner le statut du plus récent
        
        Returns:
            dict: {
                'status': 'open' | 'filled' | 'cancelled' | 'unknown',
                'timestamp': int,
                'size': float,
                'is_recent': bool
            }
        """
        try:
            # 1. Récupérer les ordres ouverts
            open_orders = self.trading_engine.get_open_orders()
            if open_orders is None:
                open_orders = []
            
            # 2. Récupérer l'historique des fills
            try:
                user_fills = self.trading_engine.info.user_fills(self.trading_engine.account_address)
            except Exception as e:
                self.logger.error(f"❌ Erreur récupération user_fills: {e}")
                user_fills = []
            
            # 3. Construire l'historique complet pour cet Order ID
            order_history = []
            
            # Ajouter l'ordre s'il est ouvert (statut le plus récent possible)
            for order in open_orders:
                if str(order.get('id')) == str(order_id):
                    order_history.append({
                        'status': 'open',
                        'timestamp': order.get('timestamp', int(time.time() * 1000)),
                        'size': float(order.get('amount', 0)),
                        'source': 'open_orders'
                    })
            
            # Ajouter les fills
            for fill in user_fills:
                if str(fill.get('oid')) == str(order_id):
                    order_history.append({
                        'status': 'filled',
                        'timestamp': fill.get('time', 0),
                        'size': float(fill.get('sz', 0)),
                        'source': 'user_fills'
                    })
            
            # 4. Trier par timestamp (le plus récent en premier)
            order_history.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # 5. Prendre le statut le plus récent
            if order_history:
                most_recent = order_history[0]
                
                self.logger.info(f"📊 Order ID {order_id} - Status le plus récent:")
                self.logger.info(f"   Status: {most_recent['status']}")
                self.logger.info(f"   Time: {datetime.fromtimestamp(most_recent['timestamp']/1000)}")
                self.logger.info(f"   Source: {most_recent['source']}")
                self.logger.info(f"   Total events: {len(order_history)}")
                
                return most_recent
            else:
                # Aucun enregistrement trouvé
                self.logger.warning(f"⚠️  Order ID {order_id} - Aucun enregistrement trouvé")
                return {
                    'status': 'unknown',
                    'timestamp': 0,
                    'size': 0,
                    'source': 'none'
                }
        
        except Exception as e:
            self.logger.error(f"❌ Erreur _get_order_status_from_history: {e}")
            return {
                'status': 'unknown',
                'timestamp': 0,
                'size': 0,
                'source': 'error'
            }
    
    def _check_buy_orders(self):
        """🆕 Vérifie les ordres d'achat avec la nouvelle logique
        
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
                
                # 🆕 Récupérer le statut le plus récent depuis l'historique
                order_status = self._get_order_status_from_history(buy_order_id)
                
                status = order_status['status']
                
                # Décision basée sur le statut le plus récent
                if status == 'open':
                    # ✅ Ordre encore ouvert - RAS
                    self.logger.info(f"⏳ Ordre d'achat {buy_order_id} - Toujours OUVERT")
                    # Status reste 'Buy' dans la BDD
                    
                elif status == 'filled':
                    # ✅ Ordre rempli - Passer en mode Sell
                    total_filled = order_status['size']
                    
                    # ✅ CORRECTION: Mettre à jour la quantité BTC RÉELLE dans la BDD
                    self.logger.info(f"✅ Ordre d'achat {buy_order_id} REMPLI")
                    self.logger.info(f"   Quantité calculée: {pair.quantity_btc:.8f} BTC")
                    self.logger.info(f"   Quantité réelle: {total_filled:.8f} BTC")
                    self.logger.info(f"   Différence (frais maker): {pair.quantity_btc - total_filled:.8f} BTC")
                    
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
                
                elif status == 'cancelled':
                    # ⚠️ Ordre annulé
                    self.logger.warning(f"⚠️  Ordre d'achat {buy_order_id} ANNULÉ")
                    self.logger.warning(f"   Paire {pair.index} nécessite une action manuelle")
                
                else:  # unknown
                    # ❌ Statut inconnu
                    self.logger.warning(f"❓ Ordre d'achat {buy_order_id} - Statut INCONNU")
                    self.logger.warning(f"   Vérification manuelle recommandée pour paire {pair.index}")
                
            except Exception as e:
                self.logger.error(f"❌ Erreur vérification paire {pair.index}: {e}")
                import traceback
                traceback.print_exc()
    
    def _check_sell_orders(self):
        """🆕 Vérifie les ordres de vente avec la nouvelle logique"""
        
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
                
                # 🆕 Récupérer le statut le plus récent depuis l'historique
                order_status = self._get_order_status_from_history(sell_order_id)
                
                status = order_status['status']
                
                # Décision basée sur le statut le plus récent
                if status == 'open':
                    # ✅ Ordre encore ouvert - RAS
                    self.logger.info(f"⏳ Ordre de vente {sell_order_id} - Toujours OUVERT")
                    # Status reste 'Sell' dans la BDD
                    
                elif status == 'filled':
                    # ✅ Ordre rempli - Cycle complété
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
                
                elif status == 'cancelled':
                    # ⚠️ Ordre annulé
                    self.logger.warning(f"⚠️  Ordre de vente {sell_order_id} ANNULÉ")
                    self.logger.warning(f"   Paire {pair.index} nécessite une action manuelle")
                
                else:  # unknown
                    # ❌ Statut inconnu
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
            self._sync_orders()
        except Exception as e:
            self.logger.error(f"❌ Erreur synchronisation forcée: {e}")
            import traceback
            traceback.print_exc()
