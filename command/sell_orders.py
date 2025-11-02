"""
Module de gestion des ORDRES DE VENTE
Logique: Surveiller ordres d'achat exécutés -> Placer ordre -> Surveiller exécution -> Mettre à jour BDD

✅ CORRECTIONS APPLIQUÉES:
- Utilise la quantité BTC RÉELLE de la BDD (déjà ajustée après frais d'achat)
- Vérifie que le solde BTC disponible est suffisant
- Mode spot limit: ordres maker uniquement, pas besoin d'ajuster pour les frais de vente
"""

import time
import threading
from datetime import datetime, timezone
from typing import Dict, Optional
from config import TradingConfig
from DB.database import Database
from command.trading_engine import TradingEngine
from command.logger import TradingLogger


class SellOrderManager:
    """Gestionnaire des ordres de vente - 1 THREAD UNIQUE
    
    Gère automatiquement :
    - Le placement des ordres de vente quand l'achat est marqué comme 'Sell' dans la BDD
    - La vérification du solde BTC disponible avant placement
    
    Stratégie :
    - La synchronisation du statut des ordres (Buy -> Sell -> Complete) est gérée
      par sync_hyperliquid_orders.py qui interroge l'API Hyperliquid
    - Ce manager se concentre uniquement sur le placement des ordres de vente
    
    Sécurités :
    - Vérifie le solde BTC disponible avant de placer une vente
    - Cache les paires en échec pour éviter les boucles infinies (retry après 5min)
    - Délai de 2s entre chaque traitement pour éviter de saturer l'API
    """
    
    def __init__(self, config: TradingConfig, database: Database, 
                 trading_engine: TradingEngine, logger: TradingLogger, telegram=None):
        self.config = config
        self.database = database
        self.trading_engine = trading_engine
        self.logger = logger
        self.telegram = telegram
        
        # État
        self.running = False
        self.thread = None
        
        # Cache pour éviter les vérifications répétées
        self.failed_pairs = {}  # {pair_index: timestamp_dernier_echec}
        self.retry_delay = 300  # 5 minutes avant de réessayer une paire en échec
        
        self.logger.info("🔵 [SELL ORDERS] Module initialisé")
    
    def start(self):
        """Démarre le thread de vente (1 SEUL THREAD)"""
        if self.running:
            self.logger.warning("⚠️ Thread de vente déjà en cours")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._sell_loop, daemon=True, name="SellThread")
        self.thread.start()
        self.logger.info("✅ Thread de vente démarré")
    
    def stop(self):
        """Arrête le thread de vente"""
        if not self.running:
            return
        
        self.logger.info("🛑 Arrêt du thread de vente...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        self.logger.info("✅ Thread de vente arrêté")
    
    def _sell_loop(self):
        """Boucle principale de gestion des ventes - 1 SEUL THREAD"""
        self.logger.info("🔄 Boucle de vente démarrée")
        
        while self.running:
            try:
                # 1. Récupérer les paires actives (buy exécuté, sell pas encore placé ou en cours)
                active_pairs = self._get_active_pairs()
                
                if not active_pairs:
                    # Aucune paire active, attendre avant de revérifier
                    time.sleep(30)
                    continue
                
                # 2. Traiter chaque paire avec un délai entre chaque traitement
                for pair in active_pairs:
                    try:
                        self._process_pair(pair)
                        
                        # ⚠️ IMPORTANT : Attendre 2 secondes entre chaque paire
                        # pour éviter de saturer l'API et déclencher le circuit breaker
                        time.sleep(2)
                        
                    except Exception as e:
                        pair_index = getattr(pair, 'index', 'UNKNOWN')
                        self.logger.error(f"❌ Erreur traitement paire {pair_index}: {e}")
                        import traceback
                        traceback.print_exc()
                
                # 3. Attendre avant la prochaine vérification
                time.sleep(30)  # Vérifier toutes les 30 secondes
                
            except Exception as e:
                self.logger.error(f"❌ Erreur dans boucle de vente: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(30)
        
        self.logger.info("🔚 Boucle de vente terminée")
    
    def _get_active_pairs(self):
        """Récupère les paires d'ordres actives depuis la BDD
        
        Paires actives = status 'Buy' ou 'Sell'
        - 'Buy': Ordre d'achat placé mais pas encore exécuté
        - 'Sell': Ordre d'achat exécuté, prêt pour placer l'ordre de vente
        
        Note: On récupère aussi les 'Buy' même si on ne les traite pas,
        au cas où le status change pendant le traitement.
        """
        try:
            # Récupérer toutes les paires non complétées (status='Buy' ou 'Sell')
            pairs = self.database.get_active_order_pairs()
            return pairs
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération paires actives: {e}")
            return []
    
    def _process_pair(self, pair):
        """Traite une paire d'ordres (placer vente si nécessaire)
        
        Seul le placement des ordres de vente est géré ici.
        La synchronisation du statut est gérée par sync_hyperliquid_orders.py
        """
        pair_index = pair.index
        
        # Vérifier si cette paire a échoué récemment
        if pair_index in self.failed_pairs:
            last_failure = self.failed_pairs[pair_index]
            elapsed = (datetime.now(timezone.utc) - last_failure).total_seconds()
            if elapsed < self.retry_delay:
                # Trop tôt pour réessayer
                return
            else:
                # Délai écoulé, retirer du cache et réessayer
                del self.failed_pairs[pair_index]
        
        sell_order_id = getattr(pair, 'sell_order_id', None)
        status = pair.status  # 'Buy', 'Sell', 'Complete'
        
        # On ne traite que les paires avec status='Sell' et sans sell_order_id
        # (= achat exécuté, vente pas encore placée)
        if status == 'Sell' and not sell_order_id:
            success = self._place_sell_order_for_pair(pair)
            # Si échec, marquer dans le cache
            if not success:
                self.failed_pairs[pair_index] = datetime.now(timezone.utc)
    
    def _place_sell_order_for_pair(self, pair) -> bool:
        """✅ Place un ordre de vente pour une paire dont l'achat est exécuté
        
        NOUVELLE LOGIQUE (mode spot limit):
        1. Prendre la quantité BTC de la BDD (déjà ajustée après frais d'achat)
        2. Vérifier que le solde BTC disponible est >= quantité BTC
        3. Placer l'ordre de vente avec cette quantité exacte
        
        Note: Pas besoin d'ajuster pour les frais maker de vente car :
        - On vend la quantité BTC qu'on possède réellement
        - Les frais maker seront déduits du montant USDC reçu, pas de la quantité BTC
        
        Returns:
            bool: True si succès, False si échec
        """
        pair_index = pair.index
        sell_price = pair.sell_price_btc
        quantity_btc = pair.quantity_btc  # ✅ Quantité RÉELLE (déjà ajustée par sync)
        buy_order_id = pair.buy_order_id
        market_type = getattr(pair, 'market_type', 'UNKNOWN')
        
        # ✅ VÉRIFICATION CRITIQUE : Vérifier le solde BTC disponible
        available_btc = self.trading_engine.get_balance("BTC", available_only=True)
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔵 VÉRIFICATION PAIRE {pair_index}")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"   Quantité BTC requise: {quantity_btc:.8f} BTC")
        self.logger.info(f"   Solde BTC disponible: {available_btc:.8f} BTC")
        
        # Vérifier avec une tolérance de 0.1% pour les arrondis
        if available_btc < quantity_btc * 0.999:
            self.logger.warning(f"⚠️  Solde BTC insuffisant pour paire {pair_index}")
            self.logger.warning(f"   Manquant: {(quantity_btc - available_btc):.8f} BTC")
            self.logger.warning(f"   L'ordre d'achat {buy_order_id} n'est peut-être pas encore totalement rempli")
            self.logger.warning(f"   Réessai dans {self.retry_delay} secondes")
            return False
        
        self.logger.info(f"✅ Solde suffisant ({available_btc:.8f} >= {quantity_btc:.8f})")
        
        # Vérifier que la quantité est valide
        if quantity_btc <= 0:
            self.logger.error(f"❌ Quantité BTC invalide pour paire {pair_index}")
            return False
        
        # Vérifier la valeur minimale
        order_value = sell_price * quantity_btc
        if order_value < self.config.min_order_value_usdc:
            self.logger.error(f"❌ Valeur trop faible: {order_value:.2f}$ < {self.config.min_order_value_usdc}$")
            return False
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔵 PLACEMENT ORDRE DE VENTE")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"   Paire: {pair_index}")
        self.logger.info(f"   Ordre d'achat: {buy_order_id}")
        self.logger.info(f"   Marché: {market_type}")
        self.logger.info(f"   Prix vente: {sell_price:.2f}$")
        self.logger.info(f"   Quantité: {quantity_btc:.8f} BTC (quantité RÉELLE)")
        self.logger.info(f"   Valeur estimée: {order_value:.2f} USDC")
        self.logger.info(f"   Note: Frais maker seront déduits du montant USDC reçu")
        self.logger.info(f"{'='*60}")
        
        # Placer l'ordre via le trading engine
        order_result = self.trading_engine.execute_sell_order(sell_price, quantity_btc)
        
        if not order_result:
            self.logger.error(f"❌ Échec placement ordre de vente pour paire {pair_index}")
            return False
        
        # Récupérer l'ID de l'ordre
        sell_order_id = str(order_result.get('id'))
        
        self.logger.info(f"✅ Ordre de vente placé sur Hyperliquid - ID: {sell_order_id}")
        
        # 📱 Notification Telegram - ORDRE DE VENTE PLACÉ
        if self.telegram and self.config.telegram_on_order_placed:
            try:
                self.telegram.send_sell_order_placed(
                    order_id=sell_order_id,
                    price=sell_price,
                    size=quantity_btc,
                    buy_price=pair.buy_price_btc,
                    market_type=market_type,
                    usdc_amount=order_value
                )
            except Exception as e:
                self.logger.error(f"❌ Erreur notification Telegram: {e}")
        
        # Mettre à jour la BDD avec l'ID de l'ordre de vente
        try:
            self.database.update_sell_order_id(pair_index, sell_order_id)
            self.logger.info(f"✅ Ordre de vente enregistré dans BDD - Paire: {pair_index}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Erreur mise à jour BDD: {e}")
            return False
    
    def get_status(self) -> Dict:
        """Retourne le statut du gestionnaire de ventes"""
        try:
            active_pairs = self._get_active_pairs()
            
            # Compter les paires par statut
            waiting_buy = sum(1 for p in active_pairs if p.status == 'Buy')
            waiting_sell_placement = sum(1 for p in active_pairs if p.status == 'Sell' and not getattr(p, 'sell_order_id', None))
            waiting_sell_fill = sum(1 for p in active_pairs if p.status == 'Sell' and getattr(p, 'sell_order_id', None))
            
            return {
                'running': self.running,
                'active_pairs_total': len(active_pairs),
                'waiting_buy_execution': waiting_buy,
                'waiting_sell_placement': waiting_sell_placement,
                'waiting_sell_execution': waiting_sell_fill,
                'failed_pairs_count': len(self.failed_pairs),
                'failed_pairs_indexes': list(self.failed_pairs.keys()),
                'thread_alive': self.thread.is_alive() if self.thread else False
            }
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération statut: {e}")
            return {
                'running': self.running,
                'error': str(e)
            }
    
    def force_check_pair(self, pair_index: int) -> bool:
        """Force la vérification d'une paire spécifique (pour debug/admin)"""
        try:
            pair = self.database.get_pair_by_index(pair_index)
            if not pair:
                self.logger.error(f"❌ Paire {pair_index} introuvable")
                return False
            
            self.logger.info(f"🔍 Vérification forcée de la paire {pair_index}")
            
            # Retirer du cache si présente
            if pair_index in self.failed_pairs:
                del self.failed_pairs[pair_index]
                self.logger.info(f"🗑️ Paire {pair_index} retirée du cache d'échecs")
            
            self._process_pair(pair)
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur vérification forcée paire {pair_index}: {e}")
            return False
    
    def clear_failed_pairs(self, pair_index: int = None):
        """Nettoie le cache des paires en échec
        
        Args:
            pair_index: Si spécifié, retire uniquement cette paire du cache.
                       Sinon, nettoie tout le cache.
        """
        if pair_index is not None:
            if pair_index in self.failed_pairs:
                del self.failed_pairs[pair_index]
                self.logger.info(f"🗑️ Paire {pair_index} retirée du cache d'échecs")
            else:
                self.logger.info(f"ℹ️ Paire {pair_index} n'était pas dans le cache d'échecs")
        else:
            count = len(self.failed_pairs)
            self.failed_pairs.clear()
            self.logger.info(f"🗑️ Cache d'échecs nettoyé ({count} paires retirées)")
