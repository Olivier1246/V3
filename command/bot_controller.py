"""
Module de contrôle principal du bot
Version JSON - Utilise hyperliquid_complete_history.py et json_sync_orders.py

✅ NOUVEAUTÉS:
- Service d'historique Hyperliquid en continu
- Synchronisation basée sur fichiers JSON (pas d'appels API directs)
- Meilleure observabilité (JSON consultables)
- Moins de charge API
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
from command.hyperliquid_complete_history import HyperliquidHistoryService
from command.json_sync_orders import JsonOrderSynchronizer

# Telegram (optionnel)
try:
    from telegram.telegram_notifier import TelegramNotifier
except ImportError:
    TelegramNotifier = None


class BotController:
    """Contrôleur principal du bot de trading
    
    Architecture JSON:
    - HyperliquidHistoryService: Récupère l'historique et génère les JSON
    - JsonOrderSynchronizer: Lit les JSON et synchronise la BDD
    - BuyOrderManager: Gère les achats
    - SellOrderManager: Gère les ventes
    """
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.logger = TradingLogger(config)
        
        self.logger.info("="*60)
        self.logger.info("🤖 INITIALISATION DU BOT (VERSION JSON)")
        self.logger.info("="*60)
        
        # Initialiser les modules
        self.database = Database(config)
        self.market_analyzer = MarketAnalyzer(config)
        self.trading_engine = TradingEngine(config)
        
        # Telegram (optionnel)
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
        
        # Service d'historique Hyperliquid
        try:
            self.history_service = HyperliquidHistoryService()
            self.logger.info("✅ Service d'historique initialisé")
        except Exception as e:
            self.logger.error(f"❌ Erreur initialisation service d'historique: {e}")
            raise
        
        # Synchroniseur JSON
        self.json_sync = JsonOrderSynchronizer(
            config, self.database, self.logger, self.telegram
        )
        
        # Gestionnaires d'ordres
        self.buy_manager = BuyOrderManager(
            config, self.database, self.trading_engine, 
            self.market_analyzer, self.logger, self.telegram
        )
        
        self.sell_manager = SellOrderManager(
            config, self.database, self.trading_engine, self.logger, self.telegram
        )
        
        # État
        self.is_running = False
        
        self.logger.info("="*60)
        self.logger.info("✅ BOT INITIALISÉ (VERSION JSON)")
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
        
        # 1. Démarrer le service d'historique Hyperliquid
        self.logger.info("\n📡 Démarrage du service d'historique...")
        self.history_service.start()
        
        # 2. Forcer une première récupération immédiate
        self.logger.info("🔄 Récupération initiale de l'historique...")
        self.history_service.fetch_now()
        
        # Attendre un peu que les JSON soient générés
        time.sleep(2)
        
        # 3. Forcer une première synchronisation
        self.logger.info("🔄 Synchronisation initiale de la BDD...")
        self.json_sync.force_sync()
        
        # 4. Démarrer le synchroniseur JSON
        self.logger.info("\n🔄 Démarrage du synchroniseur JSON...")
        self.json_sync.start()
        
        # 5. Démarrer les gestionnaires d'ordres
        self.logger.info("\n📊 Démarrage des threads de trading...")
        
        # Thread d'achat
        self.buy_manager.start()
        
        # Thread de vente
        self.sell_manager.start()
        
        self.logger.info("="*60)
        self.logger.info("✅ BOT DÉMARRÉ")
        self.logger.info("="*60)
        self.logger.info("\n💡 Architecture:")
        self.logger.info("   📡 HyperliquidHistoryService → génère JSON toutes les X minutes")
        self.logger.info("   🔄 JsonOrderSynchronizer → lit JSON et met à jour BDD")
        self.logger.info("   🟢 BuyOrderManager → place ordres d'achat")
        self.logger.info("   🔵 SellOrderManager → place ordres de vente")
        self.logger.info("="*60 + "\n")
        
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
        
        # Arrêter les threads dans l'ordre
        self.logger.info("🛑 Arrêt des modules...")
        
        # 1. Arrêter les gestionnaires d'ordres
        self.buy_manager.stop()
        self.sell_manager.stop()
        
        # 2. Arrêter le synchroniseur JSON
        self.json_sync.stop()
        
        # 3. Arrêter le service d'historique
        self.history_service.stop()
        
        self.logger.info("="*60)
        self.logger.info("✅ BOT ARRÊTÉ")
        self.logger.info("="*60)
        
        # Notification Telegram
        if self.telegram:
            self.telegram.send_bot_stopped()
    
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
            
            # Statut des managers
            buy_status = {'running': self.buy_manager.running}
            sell_status = self.sell_manager.get_status()
            
            return {
                'is_running': self.is_running,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'architecture': 'JSON-based',
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
                'health': health,
                'managers': {
                    'history_service': {
                        'running': self.history_service.running,
                        'interval_minutes': self.history_service.check_interval_minutes
                    },
                    'json_sync': {
                        'running': self.json_sync.running
                    },
                    'buy_manager': buy_status,
                    'sell_manager': sell_status
                }
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
                operator_action=True
            )
            
            if result:
                self.logger.info(f"✅ Ordre {order_id} annulé")
                # Forcer une nouvelle récupération de l'historique
                self.history_service.fetch_now()
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
                # Forcer une nouvelle récupération de l'historique
                self.history_service.fetch_now()
            else:
                self.logger.error("❌ Échec annulation des ordres")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur annulation ordres: {e}")
            return False
    
    def force_sync(self):
        """Force une synchronisation immédiate (pour debug/admin)"""
        self.logger.info("🔄 Synchronisation forcée...")
        
        # 1. Récupérer l'historique
        self.history_service.fetch_now()
        
        # 2. Synchroniser la BDD
        time.sleep(1)  # Laisser le temps aux fichiers d'être écrits
        self.json_sync.force_sync()
        
        self.logger.info("✅ Synchronisation forcée terminée")
    
    def reload_config(self) -> Dict:
        """Recharge la configuration depuis le fichier .env et propage aux modules
        
        Returns:
            dict: Résultat du rechargement avec succès et détails
        """
        try:
            self.logger.info("="*60)
            self.logger.info("🔄 RECHARGEMENT DE LA CONFIGURATION")
            self.logger.info("="*60)
            
            # Sauvegarder l'ancienne config pour comparaison
            old_config = {
                'bull_buy_offset': self.config.bull_buy_offset,
                'bull_sell_offset': self.config.bull_sell_offset,
                'bear_buy_offset': self.config.bear_buy_offset,
                'bear_sell_offset': self.config.bear_sell_offset,
                'range_buy_offset': self.config.range_buy_offset,
                'range_sell_offset': self.config.range_sell_offset,
                'bull_percent': self.config.bull_percent,
                'bear_percent': self.config.bear_percent,
                'range_percent': self.config.range_percent,
            }
            
            # 1. Recharger la configuration
            success = self.config.reload()
            
            if not success:
                self.logger.error("❌ Échec du rechargement de la configuration")
                return {
                    'success': False,
                    'message': 'Échec du rechargement de la configuration',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # 2. Propager la nouvelle config aux modules
            self.logger.info("📡 Propagation de la configuration aux modules...")
            
            # Market Analyzer
            if hasattr(self, 'market_analyzer') and self.market_analyzer:
                self.market_analyzer.config = self.config
                self.logger.info("   ✅ MarketAnalyzer mis à jour")
            
            # Trading Engine
            if hasattr(self, 'trading_engine') and self.trading_engine:
                self.trading_engine.config = self.config
                self.logger.info("   ✅ TradingEngine mis à jour")
            
            # Buy Manager
            if hasattr(self, 'buy_manager') and self.buy_manager:
                self.buy_manager.config = self.config
                self.logger.info("   ✅ BuyOrderManager mis à jour")
            
            # Sell Manager
            if hasattr(self, 'sell_manager') and self.sell_manager:
                self.sell_manager.config = self.config
                self.logger.info("   ✅ SellOrderManager mis à jour")
            
            # Database
            if hasattr(self, 'database') and self.database:
                self.database.config = self.config
                self.logger.info("   ✅ Database mis à jour")
            
            # JSON Sync
            if hasattr(self, 'json_sync') and self.json_sync:
                self.json_sync.config = self.config
                self.logger.info("   ✅ JsonOrderSynchronizer mis à jour")
            
            # 3. Préparer le résumé des changements
            new_config = {
                'bull_buy_offset': self.config.bull_buy_offset,
                'bull_sell_offset': self.config.bull_sell_offset,
                'bear_buy_offset': self.config.bear_buy_offset,
                'bear_sell_offset': self.config.bear_sell_offset,
                'range_buy_offset': self.config.range_buy_offset,
                'range_sell_offset': self.config.range_sell_offset,
                'bull_percent': self.config.bull_percent,
                'bear_percent': self.config.bear_percent,
                'range_percent': self.config.range_percent,
            }
            
            changes = {}
            for key in old_config:
                if old_config[key] != new_config[key]:
                    changes[key] = {
                        'old': old_config[key],
                        'new': new_config[key]
                    }
            
            self.logger.info("="*60)
            self.logger.info("✅ Configuration rechargée et propagée avec succès")
            self.logger.info("="*60)
            
            # Notification Telegram
            if self.telegram and changes:
                try:
                    changes_text = "\n".join([
                        f"{k}: {v['old']} → {v['new']}"
                        for k, v in changes.items()
                    ])
                    self.telegram.send_message(
                        f"🔄 Configuration rechargée\n\nChangements:\n{changes_text}"
                    )
                except Exception as e:
                    self.logger.error(f"❌ Erreur notification Telegram: {e}")
            
            return {
                'success': True,
                'message': 'Configuration rechargée avec succès',
                'changes': changes,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'config': {
                    'bull_market': {
                        'buy_offset': self.config.bull_buy_offset,
                        'sell_offset': self.config.bull_sell_offset,
                        'percent': self.config.bull_percent,
                        'time_pause': self.config.bull_time_pause,
                        'auto_interval_new': self.config.bull_auto_interval_new
                    },
                    'bear_market': {
                        'buy_offset': self.config.bear_buy_offset,
                        'sell_offset': self.config.bear_sell_offset,
                        'percent': self.config.bear_percent,
                        'time_pause': self.config.bear_time_pause,
                        'auto_interval_new': self.config.bear_auto_interval_new
                    },
                    'range_market': {
                        'buy_offset': self.config.range_buy_offset,
                        'sell_offset': self.config.range_sell_offset,
                        'percent': self.config.range_percent,
                        'time_pause': self.config.range_time_pause,
                        'auto_interval_new': self.config.range_auto_interval_new,
                        'dynamic_percent': self.config.range_dynamic_percent
                    },
                    'moving_averages': {
                        'ma4_period': self.config.ma4_period,
                        'ma8_period': self.config.ma8_period,
                        'ma12_period': self.config.ma12_period,
                        'ma12_flat_threshold': self.config.ma12_flat_threshold,
                        'ma12_periods_check': self.config.ma12_periods_check
                    },
                    'fees': {
                        'maker_fee': self.config.maker_fee,
                        'taker_fee': self.config.taker_fee
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du rechargement de la configuration: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'message': f'Erreur: {str(e)}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

