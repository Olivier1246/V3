import requests
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timezone
from config import TradingConfig
from command.logger import TradingLogger

class MarketAnalyzer:
    """Analyse le marche avec les moyennes mobiles et detection de range dynamique"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.base_url = config.base_url
        self.logger = TradingLogger(config)
    
    def get_candles(self) -> List[Dict]:
        """Recupere les donnees de chandeliers depuis l'API Hyperliquid"""
        url = f"{self.base_url}/info"
        
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": self.config.symbol,
                "interval": self.config.interval,
                "startTime": 0,
                "endTime": int(datetime.utcnow().timestamp() * 1000)
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'data' in data:
                return data['data']
            else:
                self.logger.info(f"Format de reponse inattendu: {type(data)}")
                return []
                
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Erreur HTTP lors de la recuperation des bougies: {e}")
            self.logger.info(f"Reponse: {e.response.text if hasattr(e, 'response') else 'N/A'}")
            return []
        except Exception as e:
            self.logger.error(f"Erreur lors de la recuperation des bougies: {e}")
            return []
    
    def calculate_moving_average(self, prices: List[float], period: int) -> float:
        """Calcule la moyenne mobile pour une periode donnee"""
        if len(prices) < period:
            return None
        return np.mean(prices[-period:])
    
    def get_closing_prices(self, candles: List) -> List[float]:
        """Extrait les prix de clôture des chandeliers"""
        prices = []
        
        if not candles:
            return prices
            
        for candle in candles:
            try:
                if isinstance(candle, dict) and 'c' in candle:
                    close_price = float(candle['c'])
                    if close_price > 0:
                        prices.append(close_price)
                elif isinstance(candle, list) and len(candle) >= 5:
                    close_price = float(candle[4])
                    if close_price > 0:
                        prices.append(close_price)
                        
            except (ValueError, TypeError, KeyError, IndexError) as e:
                self.logger.error(f"Erreur lors de l'extraction du prix: {e}")
                continue
        
        return prices
    
    def is_ma12_flat(self, prices: List[float]) -> bool:
        """Verifie si MA12 est plate (marche en range)"""
        if len(prices) < self.config.ma12_period + self.config.ma12_periods_check:
            return False
        
        ma12_values = []
        for i in range(self.config.ma12_periods_check):
            end_idx = len(prices) - i
            start_idx = end_idx - self.config.ma12_period
            if start_idx >= 0:
                ma12 = np.mean(prices[start_idx:end_idx])
                ma12_values.append(ma12)
        
        if len(ma12_values) < 2:
            return False
        
        max_ma12 = max(ma12_values)
        min_ma12 = min(ma12_values)
        variation_percent = ((max_ma12 - min_ma12) / min_ma12) * 100
        
        return variation_percent <= self.config.ma12_flat_threshold
    
    def calculate_range_limits(self, prices: List[float], periods: int = 20) -> dict:
        """Calcule les limites haute et basse du range DYNAMIQUEMENT
        
        Args:
            prices: Liste des prix
            periods: Nombre de periodes a analyser (par defaut 20)
            
        Returns:
            dict avec 'high', 'low', 'delta', 'mid'
        """
        if len(prices) < periods:
            periods = len(prices)
        
        if periods == 0:
            return {'high': 0, 'low': 0, 'delta': 0, 'mid': 0}
        
        recent_prices = prices[-periods:]
        
        high = max(recent_prices)
        low = min(recent_prices)
        delta = high - low
        mid = (high + low) / 2
        
        return {
            'high': high,
            'low': low,
            'delta': delta,
            'mid': mid
        }
    
    def analyze_market(self) -> Dict:
        """Analyse le marche et determine le type de marche"""
        candles = self.get_candles()
        
        if not candles:
            return {
                'error': 'Impossible de recuperer les donnees du marche',
                'market_type': 'UNKNOWN',
                'current_price': 0,
                'ma4': 0,
                'ma8': 0,
                'ma12': 0,
                'trend': 'UNKNOWN',
                'timestamp': datetime.now(timezone.utc),
                'symbol': self.config.symbol,
                'range_limits': {'high': 0, 'low': 0, 'delta': 0, 'mid': 0}
            }
        
        prices = self.get_closing_prices(candles)
        
        if not prices or len(prices) == 0:
            return {
                'error': 'Aucun prix disponible',
                'market_type': 'UNKNOWN',
                'current_price': 0,
                'ma4': 0,
                'ma8': 0,
                'ma12': 0,
                'trend': 'UNKNOWN',
                'timestamp': datetime.now(timezone.utc),
                'symbol': self.config.symbol,
                'range_limits': {'high': 0, 'low': 0, 'delta': 0, 'mid': 0}
            }
        
        current_price = prices[-1]
        
        # Calcul des moyennes mobiles
        ma4 = self.calculate_moving_average(prices, self.config.ma4_period)
        ma8 = self.calculate_moving_average(prices, self.config.ma8_period)
        ma12 = self.calculate_moving_average(prices, self.config.ma12_period)
        
        if ma4 is None:
            ma4 = current_price
        if ma8 is None:
            ma8 = current_price
        if ma12 is None:
            ma12 = current_price
        
        # Determination du type de marche
        market_type = self.determine_market_type(ma4, ma8, ma12, prices)
        
        # Determination de la tendance
        trend = self.determine_trend(ma4, ma8, ma12)
        
        # Calcul des limites du range (pour tous les types de marche)
        range_limits = self.calculate_range_limits(prices, periods=20)
        
        return {
            'timestamp': datetime.now(timezone.utc),
            'symbol': self.config.symbol,
            'current_price': current_price,
            'ma4': ma4,
            'ma8': ma8,
            'ma12': ma12,
            'market_type': market_type,
            'trend': trend,
            'range_limits': range_limits
        }
    
    def determine_market_type(self, ma4: float, ma8: float, ma12: float, prices: List[float]) -> str:
        """Determine le type de marche (BULL, BEAR, RANGE)"""
        if not all([ma4, ma8, ma12]):
            return 'UNKNOWN'
        
        # Marche en range si MA12 est plate
        if self.is_ma12_flat(prices):
            return 'RANGE'
        
        # Marche haussier si MA4 > MA8 > MA12
        if ma4 > ma8 > ma12:
            return 'BULL'
        
        # Marche baissier si MA4 < MA8 < MA12
        if ma4 < ma8 < ma12:
            return 'BEAR'
        
        return 'RANGE'
    
    def determine_trend(self, ma4: float, ma8: float, ma12: float) -> str:
        """Determine la tendance du marche"""
        if not all([ma4, ma8, ma12]):
            return 'UNKNOWN'
        
        if ma4 > ma8 and ma8 > ma12:
            return 'UPTREND'
        elif ma4 < ma8 and ma8 < ma12:
            return 'DOWNTREND'
        else:
            return 'SIDEWAYS'
    
    def get_trading_parameters(self, market_type: str, current_price: float, range_limits: dict = None) -> Dict:
        """Retourne les parametres de trading selon le type de marche
        
        NOUVELLE LOGIQUE:
        - RANGE: Calcul dynamique a 75% des limites
        - BULL: BUY_OFFSET = 0, SELL_OFFSET = 1000
        - BEAR: Pas de trading (sera gere dans bot_controller)
        """
        
        if market_type == 'BULL':
            # 🐂 BULL: Trading agressif - Offsets configurables via .env
            return {
                'buy_price': current_price + self.config.bull_buy_offset,
                'sell_price': current_price + self.config.bull_sell_offset,
                'quantity_percent': self.config.bull_percent,
                'time_pause': self.config.bull_time_pause,
                'market_type': market_type,
                'buy_offset': self.config.bull_buy_offset,
                'sell_offset': self.config.bull_sell_offset
            }
        
        elif market_type == 'BEAR':
            # 🐻 BEAR: Pas de trading (valeurs par defaut, ne seront pas utilisees)
            return {
                'buy_price': current_price + self.config.bear_buy_offset,
                'sell_price': current_price + self.config.bear_sell_offset,
                'quantity_percent': self.config.bear_percent,
                'time_pause': self.config.bear_time_pause,
                'market_type': market_type,
                'buy_offset': self.config.bear_buy_offset,
                'sell_offset': self.config.bear_sell_offset,
                'trading_enabled': False  # FLAG IMPORTANT
            }
        
        else:  # RANGE
            # ↔️ RANGE: Calcul dynamique a 75% des limites
            if range_limits and range_limits['delta'] > 0:
                # Calculer 75% de l'amplitude du range
                offset_amplitude = range_limits['delta'] * 0.75 / 2  # Divise par 2 pour avoir buy et sell
                
                # Buy offset negatif (acheter bas)
                buy_offset = -offset_amplitude
                
                # Sell offset positif (vendre haut)
                sell_offset = offset_amplitude
                
                self.logger.info(f"\n[RANGE DYNAMIQUE]")
                self.logger.info(f"  High: {range_limits['high']:.2f}$")
                self.logger.info(f"  Low: {range_limits['low']:.2f}$")
                self.logger.info(f"  Delta: {range_limits['delta']:.2f}$")
                self.logger.info(f"  BUY_OFFSET (75%): {buy_offset:.2f}$")
                self.logger.info(f"  SELL_OFFSET (75%): {sell_offset:.2f}$")
                
                return {
                    'buy_price': current_price + buy_offset,
                    'sell_price': current_price + sell_offset,
                    'quantity_percent': self.config.range_percent,
                    'time_pause': self.config.range_time_pause,
                    'market_type': market_type,
                    'buy_offset': buy_offset,
                    'sell_offset': sell_offset,
                    'range_limits': range_limits,
                    'trading_enabled': True
                }
            else:
                # Fallback sur les valeurs de config si pas de range detectable
                return {
                    'buy_price': current_price + self.config.range_buy_offset,
                    'sell_price': current_price + self.config.range_sell_offset,
                    'quantity_percent': self.config.range_percent,
                    'time_pause': self.config.range_time_pause,
                    'market_type': market_type,
                    'buy_offset': self.config.range_buy_offset,
                    'sell_offset': self.config.range_sell_offset,
                    'trading_enabled': True
                }
