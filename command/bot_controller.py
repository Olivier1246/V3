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
from test.hyperliquid_complete_history_v4 import HyperliquidHistoryService
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
