"""
Module de gestion des ORDRES D'ACHAT
Logique: Attendre interval -> Créer ordre -> Enregistrer BDD -> Boucler
"""

import time
import threading
from datetime import datetime, timezone
from typing import Dict, Optional
from config import TradingConfig
from DB.database import Database
from command.trading_engine import TradingEngine
from command.market_analyzer import MarketAnalyzer
from command.logger import TradingLogger


class BuyOrderManager:
    """Gestionnaire simplifié des ordres d'achat - 1 THREAD UNIQUE"""
    
    def __init__(self, config: TradingConfig, database: Database, 
                 trading_engine: TradingEngine, market_analyzer: MarketAnalyzer, 
                 logger: TradingLogger, telegram=None):
        self.config = config
        self.database = database
        self.trading_engine = trading_engine
        self.market_analyzer = market_analyzer
        self.logger = logger
        self.telegram = telegram  # Notifier Telegram (optionnel)
        
        # État
        self.running = False
        self.thread = None
        self.last_buy_time = None
        
        self.logger.info("🟢 [BUY ORDERS] Module initialisé")
    
    def start(self):
        """Démarre le thread d'achat (1 SEUL THREAD)"""
        if self.running:
            self.logger.warning("⚠️  Thread d'achat déjà en cours")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._buy_loop, daemon=True, name="BuyThread")
        self.thread.start()
        self.logger.info("✅ Thread d'achat démarré")
    
    def stop(self):
        """Arrête le thread d'achat"""
        if not self.running:
            return
        
        self.logger.info("🛑 Arrêt du thread d'achat...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        self.logger.info("✅ Thread d'achat arrêté")
    
    def _buy_loop(self):
        """Boucle principale des achats - 1 SEUL THREAD"""
        self.logger.info("🔄 Boucle d'achat démarrée")
        
        while self.running:
            try:
                # 1. Attendre l'interval
                if not self._should_place_buy():
                    # Vérifier toutes les minutes si l'intervalle est atteint
                    time.sleep(60)
                    continue
                
                # 2. Analyser le marché
                analysis = self.market_analyzer.analyze_market()
                if 'error' in analysis:
                    self.logger.error(f"❌ Erreur analyse marché: {analysis['error']}")
                    time.sleep(60)
                    continue
                
                market_type = analysis['market_type']
                current_price = analysis['current_price']
                range_limits = analysis.get('range_limits', {})
                
                self.logger.info(f"\n📊 Marché: {market_type}, Prix: {current_price:.2f}$")
                
                # 3. Vérifier si on peut acheter pour ce type de marché
                if not self._can_buy_for_market(market_type):
                    # ⚠️ FIX: Marquer la tentative pour éviter les boucles infinies
                    self.last_buy_time = datetime.now(timezone.utc)
                    self.logger.warning(f"⚠️  Achat désactivé pour marché {market_type}")
                    
                    # Pause avant prochaine vérification
                    pause_minutes = self._get_time_pause_for_market(market_type)
                    time.sleep(pause_minutes * 60)
                    continue
                
                # 4. Calculer les paramètres d'achat
                buy_params = self._calculate_buy_parameters(market_type, current_price, range_limits)
                
                # 5. Placer l'ordre d'achat
                order_result = self._place_buy_order(buy_params, market_type)
                
                # ⚠️ FIX CRITIQUE: Mettre à jour last_buy_time TOUJOURS
                # (même en cas d'échec) pour éviter les boucles infinies
                self.last_buy_time = datetime.now(timezone.utc)
                
                if order_result:
                    self.logger.info("✅ Ordre d'achat placé avec succès")
                else:
                    self.logger.error("❌ Échec placement ordre d'achat")
                
                # 6. ⚠️ FIX: Pause selon TIME_PAUSE du marché (en minutes -> convertir en secondes)
                pause_minutes = self._get_time_pause_for_market(market_type)
                pause_seconds = pause_minutes * 60
                self.logger.info(f"⏸️  Pause de {pause_minutes} minutes avant prochaine vérification")
                time.sleep(pause_seconds)
                
            except Exception as e:
                self.logger.error(f"❌ Erreur dans boucle d'achat: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)
        
        self.logger.info("🔚 Boucle d'achat terminée")
    
    def _get_time_pause_for_market(self, market_type: str) -> int:
        """Retourne le TIME_PAUSE en minutes selon le type de marché"""
        if market_type == 'BULL':
            return self.config.bull_time_pause
        elif market_type == 'BEAR':
            return self.config.bear_time_pause
        else:  # RANGE
            return self.config.range_time_pause
    
    def _should_place_buy(self) -> bool:
        """Vérifie si on doit placer un ordre d'achat (intervalle atteint)"""
        if self.last_buy_time is None:
            return True  # Premier ordre
        
        # Récupérer l'intervalle depuis la config
        # On utilise le plus court intervalle pour être réactif
        min_interval = min(
            self.config.bull_auto_interval_new,
            self.config.bear_auto_interval_new,
            self.config.range_auto_interval_new
        )
        
        elapsed_minutes = (datetime.now(timezone.utc) - self.last_buy_time).total_seconds() / 60
        
        if elapsed_minutes >= min_interval:
            self.logger.info(f"⏰ Interval atteint ({elapsed_minutes:.1f}/{min_interval} min)")
            return True
        
        return False
    
    def _can_buy_for_market(self, market_type: str) -> bool:
        """Vérifie si on peut acheter pour ce type de marché"""
        # Vérifier si les achats sont activés globalement
        if not self.config.buy_enabled:
            return False
        
        # Vérifier selon le type de marché
        if market_type == 'BULL' and not self.config.bull_buy_enabled:
            return False
        elif market_type == 'BEAR' and not self.config.bear_buy_enabled:
            return False
        elif market_type == 'RANGE' and not self.config.range_buy_enabled:
            return False
        
        return True
    
    def _calculate_buy_parameters(self, market_type: str, current_price: float, 
                                   range_limits: dict = None) -> Dict:
        """Calcule les paramètres d'achat selon le type de marché"""
        
        if market_type == 'BULL':
            buy_offset = self.config.bull_buy_offset
            sell_offset = self.config.bull_sell_offset
            percent = self.config.bull_percent
            
        elif market_type == 'BEAR':
            buy_offset = self.config.bear_buy_offset
            sell_offset = self.config.bear_sell_offset
            percent = self.config.bear_percent
            
        else:  # RANGE
            # Calcul dynamique si disponible
            if range_limits and range_limits.get('delta', 0) > 0:
                offset_amplitude = range_limits['delta'] * (self.config.range_dynamic_percent / 100) / 2
                buy_offset = -offset_amplitude
                sell_offset = offset_amplitude
            else:
                buy_offset = self.config.range_buy_offset
                sell_offset = self.config.range_sell_offset
            
            percent = self.config.range_percent
        
        # Prix d'achat = prix spot + offset
        buy_price = current_price + buy_offset
        
        # Prix de vente cible = prix spot + sell_offset
        sell_price = current_price + sell_offset
        
        # Calculer la quantité
        balance_usdc = self.trading_engine.get_balance("USDC", available_only=True)
        quantity_usdc = balance_usdc * (percent / 100)
        quantity_btc = self.trading_engine.calculate_order_size(buy_price, percent)
        
        # Format d'affichage des offsets
        offset_display = f"{buy_offset:.2f}/{sell_offset:.2f}"
        
        return {
            'buy_price': buy_price,
            'sell_price': sell_price,
            'buy_offset': buy_offset,
            'sell_offset': sell_offset,
            'quantity_usdc': quantity_usdc,
            'quantity_btc': quantity_btc,
            'percent': percent,
            'market_type': market_type,
            'current_price': current_price,
            'offset_display': offset_display
        }
    
    def _place_buy_order(self, buy_params: Dict, market_type: str) -> Optional[Dict]:
        """Place un ordre d'achat et l'enregistre dans la BDD"""
        
        buy_price = buy_params['buy_price']
        quantity_btc = buy_params['quantity_btc']
        
        # Vérifier que la quantité est valide
        if quantity_btc <= 0:
            self.logger.error("❌ Quantité BTC invalide")
            return None
        
        # Vérifier la valeur minimale
        order_value = buy_price * quantity_btc
        if order_value < self.config.min_order_value_usdc:
            self.logger.error(f"❌ Valeur trop faible: {order_value:.2f}$ < {self.config.min_order_value_usdc}$")
            return None
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🟢 PLACEMENT ORDRE D'ACHAT")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"   Marché: {market_type}")
        self.logger.info(f"   Prix: {buy_price:.2f}$ (offset: {buy_params['buy_offset']:.2f}$)")
        self.logger.info(f"   Prix vente cible: {buy_params['sell_price']:.2f}$")
        self.logger.info(f"   Quantité: {quantity_btc:.8f} BTC")
        self.logger.info(f"   Valeur: {order_value:.2f} USDC")
        self.logger.info(f"   Pourcentage: {buy_params['percent']}%")
        self.logger.info(f"{'='*60}")
        
        # Placer l'ordre via le trading engine
        order_result = self.trading_engine.execute_buy_order(buy_price, quantity_btc)
        
        if not order_result:
            self.logger.error("❌ Échec placement ordre sur Hyperliquid")
            return None
        
        # Récupérer l'ID de l'ordre
        buy_order_id = str(order_result.get('id'))
        
        self.logger.info(f"✅ Ordre placé sur Hyperliquid - ID: {buy_order_id}")
        
        # 📱 Notification Telegram - ORDRE PLACÉ
        if self.telegram and self.config.telegram_on_order_placed:
            try:
                self.telegram.send_buy_order_placed(
                    order_id=buy_order_id,
                    price=buy_price,
                    size=quantity_btc,
                    market_type=market_type,
                    usdc_amount=order_value
                )
            except Exception as e:
                self.logger.error(f"❌ Erreur notification Telegram: {e}")
        
        # Enregistrer dans la BDD
        try:
            pair_index = self.database.create_buy_order_pair({
                'quantity_usdc': buy_params['quantity_usdc'],
                'quantity_btc': quantity_btc,
                'buy_price_btc': buy_price,
                'sell_price_btc': buy_params['sell_price'],
                'buy_order_id': buy_order_id,
                'market_type': market_type,
                'offset_display': buy_params['offset_display']
            })
            
            self.logger.info(f"✅ Paire enregistrée dans BDD - Index: {pair_index}")
            
            return {
                'pair_index': pair_index,
                'buy_order_id': buy_order_id,
                'buy_price': buy_price,
                'quantity_btc': quantity_btc,
                'sell_price': buy_params['sell_price']
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erreur enregistrement BDD: {e}")
            return None
