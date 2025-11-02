"""
Module de contrôle principal du bot

✅ CORRECTIONS APPLIQUÉES:
- Lock pour éviter synchronisations concurrentes
- Vérification si get_open_orders() retourne None (erreur API)
- Récupération de la QUANTITÉ RÉELLE depuis user_fills()
- Mise à jour de la quantité BTC réelle dans la BDD
- Ne pas marquer les ordres comme filled si erreur API
"""

import time
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional
from config import TradingConfig
from DB.database import Database
from command.market_analyzer import MarketAnalyzer
from command.trading_engine import TradingEngine
from command.logger import TradingLogger
from command.buy_orders import BuyOrderManager
from command.sell_orders import SellOrderManager

# Telegram (optionnel)
try:
    from telegram.telegram_notifier import TelegramNotifier
except ImportError:
    TelegramNotifier = None


class BotController:
    """Contrôleur principal du bot de trading
    
    Responsabilités:
    - Lire la configuration depuis .env
    - Synchroniser BDD avec Hyperliquid (Direction + Status + Quantité réelle)
    - Lancer 1 thread d'achat
    - Lancer 1 thread de vente
    - Gérer l'arrêt propre
    """
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.logger = TradingLogger(config)
        
        self.logger.info("="*60)
        self.logger.info("🤖 INITIALISATION DU BOT (VERSION CORRIGÉE)")
        self.logger.info("="*60)
        
        # Initialiser les modules
        self.database = Database(config)
        self.market_analyzer = MarketAnalyzer(config)
        self.trading_engine = TradingEngine(config)
        
        # Telegram (optionnel) - INITIALISER EN PREMIER
        self.telegram = None
        if TelegramNotifier and config.telegram_enabled:
            try:
                self.telegram = TelegramNotifier(
                    bot_token=config.telegram_bot_token,
                    chat_id=config.telegram_chat_id,
                    enabled=config.telegram_enabled
                )
                self.logger.info("✅ Notifications Telegram activées")
            except Exception as e:
                self.logger.error(f"❌ Erreur Telegram: {e}")
        
        # Initialiser les gestionnaires d'ordres AVEC telegram
        self.buy_manager = BuyOrderManager(
            config, self.database, self.trading_engine, 
            self.market_analyzer, self.logger, self.telegram
        )
        
        self.sell_manager = SellOrderManager(
            config, self.database, self.trading_engine, self.logger, self.telegram
        )
        
        # État
        self.is_running = False
        self.sync_thread = None
        
        # Lock pour éviter synchronisations concurrentes
        self.sync_lock = threading.Lock()
        self.last_sync_time = None
        self.sync_failure_count = 0
        
        self.logger.info("="*60)
        self.logger.info("✅ BOT INITIALISÉ")
        self.logger.info("="*60)
    
    def start(self):
        """Démarre le bot"""
        if self.is_running:
            self.logger.warning("⚠️  Bot déjà en cours d'exécution")
            return
        
        self.logger.info("\n" + "="*60)
        self.logger.info("🚀 DÉMARRAGE DU BOT")
        self.logger.info("="*60)
        
        self.is_running = True
        
        # Synchroniser avec Hyperliquid au démarrage
        self.logger.info("🔄 Synchronisation initiale avec Hyperliquid...")
        self.sync_with_hyperliquid()
        
        # Démarrer les threads
        self.logger.info("\n📊 Démarrage des threads...")
        
        # Thread d'achat (1 seul)
        self.buy_manager.start()
        
        # Thread de vente (1 seul)
        self.sell_manager.start()
        
        # Thread de synchronisation périodique
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True, name="SyncThread")
        self.sync_thread.start()
        
        self.logger.info("="*60)
        self.logger.info("✅ BOT DÉMARRÉ")
        self.logger.info("="*60)
        
        # Notification Telegram
        if self.telegram:
            self.telegram.send_bot_started(
                self.config.symbol,
                "TESTNET" if self.config.testnet else "MAINNET"
            )
    
    def stop(self):
        """Arrête le bot proprement"""
        if not self.is_running:
            self.logger.warning("⚠️  Bot non démarré")
            return
        
        self.logger.info("\n" + "="*60)
        self.logger.info("🛑 ARRÊT DU BOT")
        self.logger.info("="*60)
        
        self.is_running = False
        
        # Arrêter les threads
        self.logger.info("🛑 Arrêt des threads...")
        
        self.buy_manager.stop()
        self.sell_manager.stop()
        
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=5)
        
        self.logger.info("="*60)
        self.logger.info("✅ BOT ARRÊTÉ")
        self.logger.info("="*60)
        
        # Notification Telegram
        if self.telegram:
            self.telegram.send_bot_stopped()
    
    def _get_filled_quantity(self, order_id: str) -> float:
        """✅ NOUVELLE MÉTHODE : Récupère la quantité RÉELLE remplie pour un ordre
        
        Args:
            order_id: ID de l'ordre
            
        Returns:
            float: Quantité réelle remplie (0 si erreur)
        """
        try:
            # Récupérer l'historique des fills pour cet utilisateur
            user_fills = self.trading_engine.info.user_fills(self.trading_engine.account_address)
            
            if not user_fills:
                return 0
            
            # Rechercher tous les fills pour cet ordre
            total_filled = 0
            for fill in user_fills:
                if str(fill.get('oid')) == str(order_id):
                    total_filled += float(fill.get('sz', 0))
            
            return total_filled
            
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération quantité filled: {e}")
            return 0
    
    def sync_with_hyperliquid(self):
        """✅ SYNCHRONISE la BDD avec l'état réel sur Hyperliquid
        
        CORRECTIONS APPLIQUÉES:
        - Lock pour éviter synchronisations concurrentes
        - Vérification si get_open_orders() retourne None (erreur API)
        - Récupération de la QUANTITÉ RÉELLE depuis user_fills()
        - Mise à jour de la quantité BTC réelle dans la BDD
        - Ne pas marquer les ordres comme filled si erreur API
        
        Vérifie Direction + Status + Quantité réelle pour chaque ordre:
        - Buy + Open = Paire en attente d'achat (status='Buy')
        - Buy + Filled = Mise à jour quantité réelle + status='Sell'
        - Sell + Filled = Paire complétée (status='Complete')
        """
        # Utiliser un lock pour éviter les sync concurrentes
        if not self.sync_lock.acquire(blocking=False):
            self.logger.warning("⚠️  Synchronisation déjà en cours, skip")
            return
        
        try:
            self.logger.info("\n🔄 Synchronisation avec Hyperliquid...")
            sync_start_time = time.time()
            
            # Récupérer les ordres ouverts (Open orders)
            open_orders = self.trading_engine.get_open_orders()
            
            # CORRECTIF CRITIQUE: Vérifier si la récupération a échoué
            if open_orders is None:
                self.logger.error("❌ Impossible de récupérer les ordres ouverts (erreur API)")
                self.logger.error("   La synchronisation est abandonnée pour éviter les erreurs")
                self.sync_failure_count += 1
                
                if self.sync_failure_count >= 3:
                    self.logger.error(f"⚠️  {self.sync_failure_count} échecs de sync consécutifs")
                    self.logger.error("   Vérifiez votre connexion internet et l'état de l'API Hyperliquid")
                
                return
            
            # Réinitialiser le compteur d'échecs si succès
            if self.sync_failure_count > 0:
                self.logger.info(f"✅ Synchronisation réussie après {self.sync_failure_count} échec(s)")
                self.sync_failure_count = 0
            
            self.logger.info(f"📊 {len(open_orders)} ordre(s) ouvert(s) sur Hyperliquid")
            self.last_sync_time = datetime.now(timezone.utc)
            
            # Créer des maps pour accès rapide
            open_orders_map = {}
            for order in open_orders:
                order_id = str(order.get('id', order.get('oid', '')))
                side = order.get('side', '').upper()
                direction = 'BUY' if side == 'B' else 'SELL'
                
                open_orders_map[order_id] = {
                    'direction': direction,
                    'order': order
                }
            
            # Vérifier les paires en attente d'achat (status='Buy')
            pending_buy = self.database.get_pending_buy_orders()
            self.logger.info(f"📊 {len(pending_buy)} paire(s) en attente d'achat dans BDD")
            
            for pair in pending_buy:
                buy_order_id = str(pair.buy_order_id)
                
                # Vérifier si l'ordre d'achat est encore ouvert
                if buy_order_id in open_orders_map:
                    order_info = open_orders_map[buy_order_id]
                    if order_info['direction'] == 'BUY':
                        # Ordre d'achat toujours Open, pas de changement
                        self.logger.info(f"⏳ Ordre d'achat {buy_order_id} toujours Open")
                        continue
                
                # L'ordre n'est plus ouvert = il est Filled
                self.logger.info(f"✅ Ordre d'achat {buy_order_id} rempli (Filled)")
                
                # ✅ CORRECTION : Récupérer la quantité RÉELLE remplie
                filled_quantity = self._get_filled_quantity(buy_order_id)
                
                if filled_quantity > 0:
                    self.logger.info(f"   Quantité calculée: {pair.quantity_btc:.8f} BTC")
                    self.logger.info(f"   Quantité réelle: {filled_quantity:.8f} BTC")
                    self.logger.info(f"   Différence (frais maker): {pair.quantity_btc - filled_quantity:.8f} BTC")
                    
                    # ✅ CORRECTION : Mettre à jour la quantité réelle dans la BDD
                    self.database.update_quantity_btc(pair.index, filled_quantity)
                    
                    # Notification Telegram
                    if self.telegram and self.config.telegram_on_order_filled:
                        try:
                            self.telegram.send_buy_order_filled(
                                order_id=buy_order_id,
                                price=pair.buy_price_btc,
                                size=filled_quantity
                            )
                        except Exception as e:
                            self.logger.error(f"❌ Erreur notification: {e}")
                else:
                    self.logger.warning(f"⚠️  Impossible de récupérer la quantité réelle pour {buy_order_id}")
                    self.logger.warning(f"   Utilisation de la quantité calculée: {pair.quantity_btc:.8f} BTC")
                
                # Mettre à jour le statut
                self.database.update_pair_status(pair.index, 'Sell')
            
            # Vérifier les paires en attente de vente (status='Sell')
            pending_sell = self.database.get_pending_sell_orders()
            self.logger.info(f"📊 {len(pending_sell)} paire(s) en attente de vente dans BDD")
            
            for pair in pending_sell:
                if not pair.sell_order_id:
                    # Pas encore d'ordre de vente placé
                    continue
                
                sell_order_id = str(pair.sell_order_id)
                
                # Vérifier si l'ordre de vente est encore ouvert
                if sell_order_id in open_orders_map:
                    order_info = open_orders_map[sell_order_id]
                    if order_info['direction'] == 'SELL':
                        # Ordre de vente toujours Open, pas de changement
                        self.logger.info(f"⏳ Ordre de vente {sell_order_id} toujours Open")
                        continue
                
                # L'ordre n'est plus ouvert = il est Filled
                self.logger.info(f"✅ Ordre de vente {sell_order_id} rempli (Filled)")
                
                # Calculer le profit (avec frais maker)
                maker_fee_percent = self.config.maker_fee / 100
                
                buy_cost = pair.buy_price_btc * pair.quantity_btc
                sell_revenue = pair.sell_price_btc * pair.quantity_btc
                gross_profit = sell_revenue - buy_cost
                
                buy_fee = buy_cost * maker_fee_percent
                sell_fee = sell_revenue * maker_fee_percent
                total_fees = buy_fee + sell_fee
                
                net_profit = gross_profit - total_fees
                profit_percent = ((pair.sell_price_btc - pair.buy_price_btc) / pair.buy_price_btc) * 100
                
                self.logger.info(f"💰 Profit brut: {gross_profit:.2f}$")
                self.logger.info(f"💰 Frais maker: {total_fees:.4f}$")
                self.logger.info(f"💰 Profit net: {net_profit:.2f}$ ({profit_percent:+.2f}%)")
                
                # Notification Telegram
                if self.telegram and self.config.telegram_on_order_filled:
                    try:
                        self.telegram.send_sell_order_filled(
                            order_id=sell_order_id,
                            price=pair.sell_price_btc,
                            size=pair.quantity_btc,
                            buy_price=pair.buy_price_btc,
                            profit=net_profit,
                            profit_percent=profit_percent
                        )
                    except Exception as e:
                        self.logger.error(f"❌ Erreur notification: {e}")
                
                # Marquer comme complete
                self.database.complete_order_pair(pair.index)
            
            sync_duration = time.time() - sync_start_time
            self.logger.info(f"✅ Synchronisation terminée ({sync_duration:.1f}s)")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur synchronisation: {e}")
            import traceback
            traceback.print_exc()
            self.sync_failure_count += 1
            
        finally:
            # Toujours libérer le lock
            self.sync_lock.release()
    
    def _sync_loop(self):
        """Boucle de synchronisation périodique"""
        self.logger.info("🔄 Thread de synchronisation démarré")
        
        SYNC_INTERVAL = self.config.sell_check_interval_seconds
        
        while self.is_running:
            try:
                time.sleep(SYNC_INTERVAL)
                
                if self.is_running:
                    self.sync_with_hyperliquid()
                    
            except Exception as e:
                self.logger.error(f"❌ Erreur dans boucle de sync: {e}")
                time.sleep(60)
        
        self.logger.info("🔕 Thread de synchronisation terminé")
    
    def get_status(self) -> Dict:
        """Retourne le statut actuel du bot"""
        try:
            # Statistiques BDD
            stats = self.database.get_statistics()
            
            # Balances
            usdc_balance = self.trading_engine.get_balance("USDC")
            btc_position = self.trading_engine.get_position(self.config.symbol)
            
            # Analyse marché actuelle
            market_analysis = self.market_analyzer.analyze_market()
            
            # État de santé des connexions
            health = self.trading_engine.get_health_status()
            
            return {
                'is_running': self.is_running,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'last_sync': self.last_sync_time.isoformat() if self.last_sync_time else None,
                'sync_failures': self.sync_failure_count,
                'statistics': stats,
                'balances': {
                    'usdc': usdc_balance,
                    'btc': btc_position.get('size', 0)
                },
                'market': {
                    'type': market_analysis.get('market_type'),
                    'price': market_analysis.get('current_price'),
                    'trend': market_analysis.get('trend')
                },
                'health': health
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur get_status: {e}")
            return {
                'is_running': self.is_running,
                'error': str(e)
            }
    
    def get_pending_orders(self) -> Dict:
        """Retourne les ordres en attente"""
        try:
            pending_buy = self.database.get_pending_buy_orders()
            pending_sell = self.database.get_pending_sell_orders()
            
            return {
                'buy_orders': [
                    {
                        'index': p.index,
                        'buy_order_id': p.buy_order_id,
                        'buy_price': p.buy_price_btc,
                        'quantity': p.quantity_btc,
                        'created_at': p.created_at.isoformat() if p.created_at else None
                    }
                    for p in pending_buy
                ],
                'sell_orders': [
                    {
                        'index': p.index,
                        'sell_order_id': p.sell_order_id,
                        'buy_price': p.buy_price_btc,
                        'sell_price': p.sell_price_btc,
                        'quantity': p.quantity_btc,
                        'created_at': p.created_at.isoformat() if p.created_at else None
                    }
                    for p in pending_sell
                ]
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur get_pending_orders: {e}")
            return {
                'buy_orders': [],
                'sell_orders': [],
                'error': str(e)
            }
    
    def get_completed_pairs(self, limit: int = 50) -> List[Dict]:
        """Retourne les paires complétées"""
        try:
            all_pairs = self.database.get_all_pairs(limit=limit)
            
            completed = [p for p in all_pairs if p.status == 'Complete']
            
            return [
                {
                    'index': p.index,
                    'buy_price': p.buy_price_btc,
                    'sell_price': p.sell_price_btc,
                    'quantity': p.quantity_btc,
                    'gain_usdc': p.gain_usdc,
                    'gain_percent': p.gain_percent,
                    'market_type': p.market_type,
                    'completed_at': p.completed_at.isoformat() if p.completed_at else None
                }
                for p in completed
            ]
            
        except Exception as e:
            self.logger.error(f"❌ Erreur get_completed_pairs: {e}")
            return []
    
    def cancel_order(self, order_id: str) -> bool:
        """Annule un ordre manuellement (opérateur uniquement)"""
        try:
            self.logger.info(f"🗑️  Annulation manuelle de l'ordre {order_id}")
            
            result = self.trading_engine.cancel_order(
                order_id=order_id,
                operator_action=True  # Confirmation explicite
            )
            
            if result:
                self.logger.info(f"✅ Ordre {order_id} annulé")
                # Re-synchroniser
                self.sync_with_hyperliquid()
            else:
                self.logger.error(f"❌ Échec annulation ordre {order_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur annulation ordre: {e}")
            return False
    
    def cancel_all_orders(self) -> bool:
        """Annule tous les ordres manuellement (opérateur uniquement)"""
        try:
            self.logger.info("🗑️  Annulation manuelle de TOUS les ordres")
            
            result = self.trading_engine.cancel_all_orders(operator_action=True)
            
            if result:
                self.logger.info("✅ Tous les ordres annulés")
                # Re-synchroniser
                self.sync_with_hyperliquid()
            else:
                self.logger.error("❌ Échec annulation des ordres")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur annulation ordres: {e}")
            return False
