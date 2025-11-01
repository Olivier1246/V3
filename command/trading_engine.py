"""
Trading Engine Amélioré avec gestion robuste des connexions
CORRECTIFS:
- get_open_orders() retourne None en cas d'erreur (au lieu de [])
- Meilleure distinction entre "pas d'ordres" et "erreur API"
- Circuit breaker avec réinitialisation automatique
- NOUVEAU: Retry automatique intégré pour erreurs réseau (ConnectionResetError, etc.)
"""

import ccxt
import time
from hyperliquid.info import Info
from hyperliquid.utils import constants
from typing import Dict, Optional, Callable, Any, List
from config import TradingConfig
from functools import wraps


class CircuitBreaker:
    """Pattern Circuit Breaker pour protéger contre les API défaillantes
    
    AMÉLIORATION: Intègre le retry avec backoff pour les erreurs réseau transitoires
    """
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60, half_open_attempts: int = 2,
                 retry_on_network_error: bool = True, max_retries: int = 3):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_attempts = half_open_attempts
        self.retry_on_network_error = retry_on_network_error
        self.max_retries = max_retries
        self.failures = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half_open
        self.half_open_successes = 0
    
    def _is_network_error(self, exception: Exception) -> bool:
        """Détermine si l'erreur est une erreur réseau transitoire"""
        import ccxt
        
        # Erreurs réseau connues
        network_errors = (
            ConnectionResetError,
            ConnectionError,
            TimeoutError,
            ccxt.NetworkError,
            ccxt.RequestTimeout,
        )
        
        # Vérifier si c'est une instance directe
        if isinstance(exception, network_errors):
            return True
        
        # Vérifier les messages d'erreur spécifiques
        error_msg = str(exception).lower()
        network_keywords = [
            'connection reset',
            'connection aborted',
            'connection refused',
            'timeout',
            'timed out',
            'network error',
            'remote end closed',
            'connexion existante'
        ]
        
        return any(keyword in error_msg for keyword in network_keywords)
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Exécute une fonction avec protection circuit breaker et retry automatique"""
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'half_open'
                self.half_open_successes = 0
                print(f"🔄 Circuit breaker: passage en mode half_open (test)")
            else:
                raise Exception(f"Circuit breaker OPEN - Attente {self.timeout}s")
        
        # Tentatives avec backoff pour les erreurs réseau
        last_exception = None
        delay = 2.0  # Délai initial en secondes
        
        for attempt in range(self.max_retries):
            try:
                result = func(*args, **kwargs)
                
                # Succès - gérer les états du circuit breaker
                if self.state == 'half_open':
                    self.half_open_successes += 1
                    if self.half_open_successes >= self.half_open_attempts:
                        self.state = 'closed'
                        self.failures = 0
                        print(f"✅ Circuit breaker: connexion rétablie (closed)")
                elif self.state == 'closed':
                    # Réinitialiser les échecs si succès en mode closed
                    if self.failures > 0:
                        self.failures = 0
                
                return result
                
            except Exception as e:
                last_exception = e
                is_network_error = self._is_network_error(e)
                
                # Si c'est une erreur réseau et qu'on peut retry
                if is_network_error and self.retry_on_network_error and attempt < self.max_retries - 1:
                    print(f"⚠️  Erreur réseau transitoire détectée (tentative {attempt + 1}/{self.max_retries})")
                    print(f"   Type: {type(e).__name__}")
                    print(f"   Message: {str(e)[:100]}")
                    print(f"   ⏳ Nouvelle tentative dans {delay:.1f}s...")
                    time.sleep(delay)
                    delay *= 2  # Backoff exponentiel
                    continue
                
                # Erreur non-réseau ou dernière tentative - comptabiliser l'échec
                self.failures += 1
                self.last_failure_time = time.time()
                
                if self.failures >= self.failure_threshold:
                    self.state = 'open'
                    print(f"⚠️  Circuit breaker OPEN après {self.failures} échecs")
                    print(f"    Prochaine tentative dans {self.timeout}s")
                elif self.state == 'half_open':
                    self.state = 'open'
                    print(f"⚠️  Circuit breaker: retour en OPEN après échec en half_open")
                
                # Si c'était une erreur réseau et qu'on a épuisé les retries
                if is_network_error:
                    print(f"❌ Échec après {self.max_retries} tentatives - Erreur réseau persistante")
                    print(f"   L'API Hyperliquid peut être surchargée ou temporairement indisponible")
                
                raise e
        
        # Si on arrive ici, on a épuisé toutes les tentatives
        raise last_exception
    
    def get_state(self) -> dict:
        """Retourne l'état actuel du circuit breaker"""
        return {
            'state': self.state,
            'failures': self.failures,
            'last_failure_time': self.last_failure_time,
            'max_retries': self.max_retries
        }


def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0):
    """Décorateur pour retry avec exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except ConnectionResetError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        print(f"⚠️  Tentative {attempt + 1}/{max_retries} échouée: ConnectionResetError")
                        print(f"   L'API Hyperliquid a fermé la connexion")
                        print(f"   Nouvelle tentative dans {delay:.1f}s...")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        print(f"❌ Échec après {max_retries} tentatives - ConnectionResetError persistante")
                        print(f"   L'API Hyperliquid peut être surchargée ou avoir des problèmes")
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries - 1:
                        print(f"⚠️  Tentative {attempt + 1}/{max_retries} échouée: {str(e)[:100]}")
                        print(f"   Nouvelle tentative dans {delay:.1f}s...")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        print(f"❌ Échec après {max_retries} tentatives")
            
            raise last_exception
        
        return wrapper
    return decorator


class TradingEngineImproved:
    """Moteur de trading avec gestion robuste des connexions"""
    
    MIN_ORDER_VALUE_USDC = 10.0
    DEFAULT_TIMEOUT = 60  # ⚡ Timeout augmenté à 60 secondes
    SDK_TIMEOUT = 55  # Timeout spécifique pour SDK Hyperliquid
    REQUEST_DELAY = 2.5  # ⚡ Délai MINIMUM entre les requêtes (en secondes)
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.last_request_time = 0  # ⚡ Pour respecter REQUEST_DELAY
        
        # Circuit breakers pour chaque API avec paramètres ajustés
        self.sdk_circuit_breaker = CircuitBreaker(
            failure_threshold=3,  # ⚡ Réduit à 3 échecs (plus réactif)
            timeout=180,  # ⚡ 3 minutes avant de réessayer
            half_open_attempts=2,
            retry_on_network_error=True,  # ✅ NOUVEAU: Retry automatique sur erreur réseau
            max_retries=3  # ✅ NOUVEAU: 3 tentatives avec backoff
        )
        self.ccxt_circuit_breaker = CircuitBreaker(
            failure_threshold=3,  # ⚡ Réduit à 3 échecs
            timeout=180,  # ⚡ 3 minutes avant de réessayer
            half_open_attempts=2,
            retry_on_network_error=True,  # ✅ NOUVEAU: Retry automatique sur erreur réseau
            max_retries=3  # ✅ NOUVEAU: 3 tentatives avec backoff exponentiel
        )
        
        print(f"\n🔧 CONFIGURATION DU TRADING ENGINE (CORRIGÉ)")
        print(f"=" * 60)
        print(f"💼 Wallet Address: {config.wallet_address}")
        print(f"🔑 API Wallet: {config.api_wallet_address}")
        print(f"⏱️  Timeout CCXT: {self.DEFAULT_TIMEOUT}s")
        print(f"⏱️  Timeout SDK: {self.SDK_TIMEOUT}s")
        print(f"🔄 Retry automatique: 3 tentatives avec backoff exponentiel (2s, 4s, 8s)")
        print(f"🔌 Circuit breaker: 3 échecs → OPEN pour 180s")
        print(f"🌐 Gestion erreurs réseau: ✅ Retry automatique pour ConnectionReset")
        
        # SDK Hyperliquid avec timeout
        print(f"\n📊 Initialisation SDK Hyperliquid avec timeout...")
        if config.testnet:
            base_url = constants.TESTNET_API_URL
        else:
            base_url = constants.MAINNET_API_URL
        
        self.info = Info(base_url, skip_ws=True)
        if hasattr(self.info, 'session') and self.info.session:
            self.info.session.timeout = self.SDK_TIMEOUT
        
        self.account_address = config.wallet_address
        
        # CCXT avec timeout et session keep-alive
        print(f"📊 Initialisation CCXT avec timeout et session management...")
        self.exchange = ccxt.hyperliquid({
            'walletAddress': config.wallet_address,
            'privateKey': config.private_key,
            'enableRateLimit': True,
            'rateLimit': 500,  # ⚡ Minimum 500ms entre requêtes
            'timeout': self.DEFAULT_TIMEOUT * 1000,  # CCXT utilise ms
            'options': {
                'defaultType': 'spot',
            }
        })
        
        # ⚡ Configurer la session avec keep-alive et pool de connexions
        if hasattr(self.exchange, 'session'):
            import requests
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=5,  # ✅ Augmenté de 1 à 5
                pool_maxsize=10,  # ✅ Augmenté de 1 à 10
                max_retries=0,  # On gère les retries nous-mêmes
                pool_block=False
            )
            self.exchange.session.mount('http://', adapter)
            self.exchange.session.mount('https://', adapter)
            self.exchange.session.keep_alive = True
            # ✅ Configurer les timeouts par défaut
            self.exchange.session.timeout = (10, 60)  # (connect timeout, read timeout)
            print(f"✅ Session HTTP configurée avec keep-alive et pool étendu")
        
        # Mapping des symboles
        self.spot_symbol_mapping = {
            'BTC': 'UBTC',
            'ETH': 'UETH',
            'SOL': 'USOL',
        }
        
        self.sdk_symbol = config.symbol
        self.spot_symbol = self.spot_symbol_mapping.get(config.symbol, f"U{config.symbol}")
        self.ccxt_spot_symbol = f"{self.spot_symbol}/USDC"
        
        print(f"\n🎯 MAPPING DES SYMBOLES:")
        print(f"   Config symbol: {self.sdk_symbol}")
        print(f"   Spot symbol: {self.spot_symbol}")
        print(f"   CCXT symbol: {self.ccxt_spot_symbol}")
        print(f"=" * 60)
    
    def _wait_for_rate_limit(self):
        """Attend le délai minimum entre les requêtes pour éviter le rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.REQUEST_DELAY:
            wait_time = self.REQUEST_DELAY - elapsed
            time.sleep(wait_time)
        self.last_request_time = time.time()
    
    def get_balance(self, asset: str = "USDC", available_only: bool = False) -> float:
        """Récupère le solde d'un actif SPOT via SDK"""
        # ⚡ Respecter le délai entre requêtes
        self._wait_for_rate_limit()
        
        def _get_balance():
            # ✅ CORRECTION: Utiliser spot_user_state pour SPOT
            spot_state = self.info.spot_user_state(self.account_address)
            
            if not spot_state or 'balances' not in spot_state:
                return 0.0
            
            balances = spot_state['balances']
            
            for balance_item in balances:
                # ✅ Utiliser le champ 'coin' (ex: "USDC", "UBTC")
                coin = balance_item.get('coin', '')
                
                # Vérifier si c'est l'asset recherché (USDC, BTC via UBTC, etc.)
                if coin == asset or (asset == "BTC" and coin == "UBTC"):
                    # ✅ Les valeurs sont des strings, il faut les convertir
                    total = float(balance_item.get('total', '0'))
                    hold = float(balance_item.get('hold', '0'))
                    
                    if available_only:
                        return max(0, total - hold)
                    return total
            
            return 0.0
        
        try:
            balance = self.sdk_circuit_breaker.call(_get_balance)
            return balance
        except Exception as e:
            print(f"❌ Erreur get_balance: {e}")
            return 0.0

    def get_balance_details(self, asset: str = "USDC") -> dict:
        """Récupère les détails du solde SPOT (total, hold, available)"""
        # ⚡ Respecter le délai entre requêtes
        self._wait_for_rate_limit()
        
        def _get_details():
            # ✅ CORRECTION: Utiliser spot_user_state pour SPOT
            spot_state = self.info.spot_user_state(self.account_address)
            
            if not spot_state or 'balances' not in spot_state:
                return {'total': 0.0, 'hold': 0.0, 'available': 0.0}
            
            balances = spot_state['balances']
            
            for balance_item in balances:
                coin = balance_item.get('coin', '')
                
                # Vérifier si c'est l'asset recherché
                if coin == asset or (asset == "BTC" and coin == "UBTC"):
                    # ✅ Convertir les strings en float
                    total = float(balance_item.get('total', '0'))
                    hold = float(balance_item.get('hold', '0'))
                    available = max(0, total - hold)
                    
                    # 💡 Message amélioré
                    print(f"\n💰 Balance SPOT ({coin}):")
                    print(f"   Total: {total:.8f}")
                    print(f"   Hold (ordres en cours): {hold:.8f}")
                    print(f"   Disponible: {available:.8f}")
                    
                    return {
                        'total': total,
                        'hold': hold,
                        'available': available
                    }
            
            return {'total': 0.0, 'hold': 0.0, 'available': 0.0}
        
        try:
            details = self.sdk_circuit_breaker.call(_get_details)
            return details
        except Exception as e:
            print(f"❌ Erreur get_balance_details: {e}")
            return {'total': 0.0, 'hold': 0.0, 'available': 0.0}

    def get_position(self, symbol: str = None) -> dict:
        """Récupère la position SPOT actuelle (quantité détenue)"""
        if symbol is None:
            symbol = self.sdk_symbol
        
        # ⚡ Respecter le délai entre requêtes
        self._wait_for_rate_limit()
        
        def _get_position():
            # ✅ CORRECTION: Utiliser spot_user_state pour SPOT
            spot_state = self.info.spot_user_state(self.account_address)
            
            if not spot_state or 'balances' not in spot_state:
                return {'size': 0.0, 'available': 0.0, 'hold': 0.0, 'entry_price': 0.0, 'unrealized_pnl': 0.0}
            
            balances = spot_state['balances']
            
            # Pour SPOT, chercher le coin correspondant (ex: UBTC pour BTC)
            target_coin = self.spot_symbol  # Ex: "UBTC" pour BTC
            
            for balance_item in balances:
                coin = balance_item.get('coin', '')
                
                if coin == target_coin:
                    # ✅ Convertir les strings en float
                    total = float(balance_item.get('total', '0'))
                    hold = float(balance_item.get('hold', '0'))
                    available = max(0, total - hold)
                    
                    return {
                        'size': total,  # Quantité totale
                        'available': available,  # Quantité disponible
                        'hold': hold,  # Quantité bloquée dans les ordres
                        'entry_price': 0.0,  # N/A pour SPOT
                        'unrealized_pnl': 0.0  # N/A pour SPOT
                    }
            
            return {'size': 0.0, 'available': 0.0, 'hold': 0.0, 'entry_price': 0.0, 'unrealized_pnl': 0.0}
        
        try:
            position = self.sdk_circuit_breaker.call(_get_position)
            return position
        except Exception as e:
            print(f"❌ Erreur get_position: {e}")
            return {'size': 0.0, 'available': 0.0, 'hold': 0.0, 'entry_price': 0.0, 'unrealized_pnl': 0.0}
    
    def get_open_orders(self) -> Optional[List[dict]]:
        """Récupère les ordres ouverts via CCXT
        
        CORRECTIF CRITIQUE:
        - Retourne None en cas d'erreur (au lieu de [])
        - Retourne [] seulement s'il n'y a vraiment aucun ordre
        - Permet au code appelant de distinguer "pas d'ordres" vs "erreur API"
        """
        # ⚡ Respecter le délai entre requêtes
        self._wait_for_rate_limit()
        
        def _get_orders():
            orders = self.exchange.fetch_open_orders(self.ccxt_spot_symbol)
            
            # S'assurer que tous les IDs sont des strings
            for order in orders:
                if 'id' in order:
                    order['id'] = str(order['id'])
            
            return orders
        
        try:
            orders = self.ccxt_circuit_breaker.call(_get_orders)
            print(f"✅ get_open_orders réussi: {len(orders)} ordre(s)")
            return orders
            
        except Exception as e:
            print(f"❌ Erreur get_open_orders après retries: {e}")
            print(f"   Circuit breaker state: {self.ccxt_circuit_breaker.state}")
            # ⚠️ CORRECTIF: Retourner None pour indiquer une erreur
            return None
    
    def cancel_order(self, order_id: str, symbol: str = None, operator_action: bool = False) -> bool:
        """Annule un ordre avec confirmation opérateur"""
        if not operator_action:
            error_msg = "❌ ERREUR: cancel_order() appelé sans confirmation opérateur!"
            print(error_msg)
            raise Exception(error_msg)
        
        @retry_with_backoff(max_retries=2)
        def _cancel():
            self.exchange.cancel_order(str(order_id), self.ccxt_spot_symbol)
        
        try:
            _cancel()
            print(f"✅ Ordre {order_id} annulé PAR L'OPÉRATEUR")
            return True
        except Exception as e:
            print(f"❌ Erreur cancel_order: {e}")
            return False
    
    def cancel_all_orders(self, symbol: str = None, operator_action: bool = False) -> bool:
        """Annule tous les ordres avec confirmation opérateur"""
        if not operator_action:
            error_msg = "❌ ERREUR: cancel_all_orders() appelé sans confirmation opérateur!"
            print(error_msg)
            raise Exception(error_msg)
        
        try:
            open_orders = self.get_open_orders()
            
            if open_orders is None:
                print("❌ Impossible de récupérer les ordres ouverts")
                return False
            
            if not open_orders:
                print("ℹ️  Aucun ordre à annuler")
                return True
            
            print(f"🗑️  Annulation de {len(open_orders)} ordre(s) PAR L'OPÉRATEUR...")
            
            for order in open_orders:
                self.cancel_order(order['id'], operator_action=True)
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur cancel_all_orders: {e}")
            return False
    
    def place_limit_order(self, symbol: str, is_buy: bool, price: float, size: float) -> Optional[dict]:
        """Place un ordre SPOT avec retry géré par le circuit breaker"""
        try:
            # ⚡ CRITIQUE: Respecter le délai entre requêtes
            self._wait_for_rate_limit()
            
            size_rounded = round(size, 5)
            
            if size_rounded < 0.00001:
                print(f"⚠️  Taille trop petite: {size_rounded}")
                return None
            
            # Vérification valeur minimale
            order_value = size_rounded * price
            if order_value < self.MIN_ORDER_VALUE_USDC:
                print(f"\n❌ ORDRE REFUSÉ: Valeur trop faible")
                print(f"   Valeur de l'ordre: {order_value:.2f} USDC")
                print(f"   Minimum requis: {self.MIN_ORDER_VALUE_USDC} USDC")
                return None
            
            print(f"\n📤 PLACEMENT ORDRE SPOT (AVEC RETRY)")
            print(f"   Symbole CCXT: {self.ccxt_spot_symbol}")
            print(f"   Type: {'ACHAT' if is_buy else 'VENTE'}")
            print(f"   Taille: {size_rounded}")
            print(f"   Prix: {price}")
            print(f"   Valeur: {order_value:.2f} USDC ✅")
            
            side = 'buy' if is_buy else 'sell'
            
            def _place():
                return self.exchange.create_order(
                    symbol=self.ccxt_spot_symbol,
                    type='limit',
                    side=side,
                    amount=size_rounded,
                    price=price
                )
            
            order_result = self.ccxt_circuit_breaker.call(_place)
            
            # Convertir l'ID en string
            if 'id' in order_result:
                order_result['id'] = str(order_result['id'])
            
            print(f"✅ Ordre SPOT placé!")
            print(f"📊 Order ID: {order_result.get('id')}")
            print(f"   Status: {order_result.get('status')}")
            
            return order_result
            
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ ERREUR PLACEMENT ORDRE: {error_msg}")
            import traceback
            traceback.print_exc()
            return None
    
    def calculate_order_size(self, price: float, percent: float) -> float:
        """Calcule la taille de l'ordre"""
        balance_details = self.get_balance_details("USDC")
        usdc_available = balance_details['available']
        
        if usdc_available <= 0:
            print(f"\n⚠️  Balance USDC disponible insuffisante")
            print(f"   Total: {balance_details['total']:.2f}$")
            print(f"   Bloqué (hold): {balance_details['hold']:.2f}$")
            print(f"   Disponible: {usdc_available:.2f}$")
            return 0.0
        
        order_value = usdc_available * (percent / 100)
        
        if order_value < self.MIN_ORDER_VALUE_USDC:
            print(f"\n⚠️  Ordre trop petit: {order_value:.2f}$ < {self.MIN_ORDER_VALUE_USDC}$")
            return 0.0
        
        size = order_value / price
        
        final_value = size * price
        if final_value < self.MIN_ORDER_VALUE_USDC:
            print(f"⚠️  Valeur finale trop petite: {final_value:.2f}$ < {self.MIN_ORDER_VALUE_USDC}$")
            return 0.0
        
        return round(size, 5)
    
    def execute_buy_order(self, price: float, size: float) -> Optional[dict]:
        """Exécute un ordre d'achat avec retry"""
        print(f"\n📊 PLACEMENT ORDRE ACHAT (AVEC RETRY)")
        
        return self.place_limit_order(
            symbol=self.sdk_symbol,
            is_buy=True,
            price=price,
            size=size
        )
    
    def execute_sell_order(self, price: float, size: float) -> Optional[dict]:
        """Exécute un ordre de vente avec retry"""
        print(f"\n📊 PLACEMENT ORDRE VENTE (AVEC RETRY)")
        
        position = self.get_position(self.sdk_symbol)
        
        if position['size'] <= 0:
            print("⚠️  Aucune position à vendre")
            return None
        
        actual_size = min(size, abs(position['size']))
        
        return self.place_limit_order(
            symbol=self.sdk_symbol,
            is_buy=False,
            price=price,
            size=actual_size
        )
    
    def get_health_status(self) -> dict:
        """Retourne le statut de santé des connexions"""
        return {
            'sdk_circuit_breaker': self.sdk_circuit_breaker.get_state(),
            'ccxt_circuit_breaker': self.ccxt_circuit_breaker.get_state()
        }


# Alias pour compatibilité
TradingEngine = TradingEngineImproved