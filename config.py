"""
Configuration du bot de trading
Toutes les variables proviennent du fichier .env
"""

import os
from dotenv import load_dotenv
from typing import Optional


class TradingConfig:
    """Classe de configuration qui charge TOUTES les variables depuis .env"""
    
    def __init__(self, env_file: str = '.env'):
        """Charge la configuration depuis le fichier .env"""
        
        # Charger le fichier .env
        load_dotenv(env_file)
        
        print(f"📋 Chargement de la configuration depuis: {env_file}")
        
        # ============================================
        # API CONFIGURATION
        # ============================================
        self.wallet_address = self._get_required_env('WALLET_ADDRESS')
        self.api_wallet_address = self._get_required_env('API_WALLET_ADDRESS')
        self.private_key = self._get_required_env('PRIVATE_KEY')
        
        # ============================================
        # TRADING CONFIGURATION
        # ============================================
        self.symbol = self._get_env('SYMBOL', 'BTC')
        self.interval = self._get_env('INTERVAL', '1h')
        self.limit = self._get_int_env('LIMIT', 100)
        self.testnet = self._get_bool_env('TESTNET', False)
        self.base_url = self._get_env('BASE_URL', 'https://api.hyperliquid.xyz')
        
        # ============================================
        # TRADING FEES
        # ============================================
        self.maker_fee = self._get_float_env('MAKER_FEE', 0.04)
        self.taker_fee = self._get_float_env('TAKER_FEE', 0.07)
        
        # ============================================
        # ORDER CONSTRAINTS
        # ============================================
        self.min_order_value_usdc = self._get_float_env('MIN_ORDER_VALUE_USDC', 10.0)
        
        # ============================================
        # BUY ORDERS CONTROL
        # ============================================
        self.buy_enabled = self._get_bool_env('BUY_ENABLED', True)
        self.bull_buy_enabled = self._get_bool_env('BULL_BUY_ENABLED', True)
        self.bear_buy_enabled = self._get_bool_env('BEAR_BUY_ENABLED', False)
        self.range_buy_enabled = self._get_bool_env('RANGE_BUY_ENABLED', True)
        
        # ============================================
        # SELL ORDERS CONTROL
        # ============================================
        self.sell_enabled = self._get_bool_env('SELL_ENABLED', True)
        self.bull_sell_enabled = self._get_bool_env('BULL_SELL_ENABLED', True)
        self.bear_sell_enabled = self._get_bool_env('BEAR_SELL_ENABLED', False)
        self.range_sell_enabled = self._get_bool_env('RANGE_SELL_ENABLED', True)
        
        # ============================================
        # MOVING AVERAGES
        # ============================================
        self.ma4_period = self._get_int_env('MA4_PERIOD', 4)
        self.ma8_period = self._get_int_env('MA8_PERIOD', 8)
        self.ma12_period = self._get_int_env('MA12_PERIOD', 12)
        self.ma12_flat_threshold = self._get_float_env('MA12_FLAT_THRESHOLD', 0.25)
        self.ma12_periods_check = self._get_int_env('MA12_PERIODS_CHECK', 5)
        
        # ============================================
        # BULL MARKET PARAMETERS
        # ============================================
        self.bull_buy_offset = self._get_float_env('BULL_BUY_OFFSET', 0)
        self.bull_sell_offset = self._get_float_env('BULL_SELL_OFFSET', 1000)
        self.bull_percent = self._get_float_env('BULL_PERCENT', 3)
        self.bull_time_pause = self._get_int_env('BULL_TIME_PAUSE', 10)
        self.bull_auto_interval_new = self._get_int_env('BULL_AUTO_INTERVAL_NEW', 360)
        
        # ============================================
        # BEAR MARKET PARAMETERS
        # ============================================
        self.bear_buy_offset = self._get_float_env('BEAR_BUY_OFFSET', -1000)
        self.bear_sell_offset = self._get_float_env('BEAR_SELL_OFFSET', 0)
        self.bear_percent = self._get_float_env('BEAR_PERCENT', 3)
        self.bear_time_pause = self._get_int_env('BEAR_TIME_PAUSE', 10)
        self.bear_auto_interval_new = self._get_int_env('BEAR_AUTO_INTERVAL_NEW', 360)
        
        # ============================================
        # RANGE MARKET PARAMETERS
        # ============================================
        self.range_buy_offset = self._get_float_env('RANGE_BUY_OFFSET', -400)
        self.range_sell_offset = self._get_float_env('RANGE_SELL_OFFSET', 400)
        self.range_percent = self._get_float_env('RANGE_PERCENT', 5)
        self.range_time_pause = self._get_int_env('RANGE_TIME_PAUSE', 10)
        self.range_auto_interval_new = self._get_int_env('RANGE_AUTO_INTERVAL_NEW', 180)
        self.range_dynamic_percent = self._get_float_env('RANGE_DYNAMIC_PERCENT', 75)
        self.range_calculation_periods = self._get_int_env('RANGE_CALCULATION_PERIODS', 20)
        
        # ============================================
        # BOT TIMING
        # ============================================
        self.initial_delay_minutes = self._get_int_env('INITIAL_DELAY_MINUTES', 0)
        self.min_check_interval_minutes = self._get_float_env('MIN_CHECK_INTERVAL_MINUTES', 10)
        self.short_sleep_minutes = self._get_float_env('SHORT_SLEEP_MINUTES', 1)
        self.sell_check_interval_seconds = self._get_int_env('SELL_CHECK_INTERVAL_SECONDS', 120)
        
        # ============================================
        # TELEGRAM NOTIFICATIONS
        # ============================================
        self.telegram_enabled = self._get_bool_env('TELEGRAM_ENABLED', False)
        self.telegram_bot_token = self._get_env('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = self._get_env('TELEGRAM_CHAT_ID', '')
        self.telegram_on_order_placed = self._get_bool_env('TELEGRAM_ON_ORDER_PLACED', True)
        self.telegram_on_order_filled = self._get_bool_env('TELEGRAM_ON_ORDER_FILLED', True)
        self.telegram_on_profit = self._get_bool_env('TELEGRAM_ON_PROFIT', True)
        self.telegram_on_error = self._get_bool_env('TELEGRAM_ON_ERROR', True)
        self.telegram_daily_summary = self._get_bool_env('TELEGRAM_DAILY_SUMMARY', True)
        
        # ============================================
        # DATABASE
        # ============================================
        self.db_type = self._get_env('DB_TYPE', 'sqlite')
        self.db_file = self._get_env('DB_FILE', 'DB/trading_history.db')
        
        # ============================================
        # WEBSITE
        # ============================================
        self.addresse = self._get_env('ADDRESSE', 'http://0.0.0.0')
        self.port = self._get_int_env('PORT', 60000)
        
        # ============================================
        # FILES
        # ============================================
        self.config_file = self._get_env('CONFIG_FILE', '.env')
        self.bot_directory = self._get_env('BOT_DIRECTORY', '.')
        self.log_file = self._get_env('LOG_FILE', 'log/trading.log')
        
        # Afficher le résumé de la configuration
        self._print_summary()
    
    def _get_env(self, key: str, default: str = '') -> str:
        """Récupère une variable d'environnement string"""
        value = os.getenv(key, default)
        return value
    
    def _get_required_env(self, key: str) -> str:
        """Récupère une variable d'environnement obligatoire"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Variable d'environnement requise manquante: {key}")
        return value
    
    def _get_int_env(self, key: str, default: int = 0) -> int:
        """Récupère une variable d'environnement int"""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            print(f"⚠️  Erreur conversion {key}='{value}' en int, utilisation de {default}")
            return default
    
    def _get_float_env(self, key: str, default: float = 0.0) -> float:
        """Récupère une variable d'environnement float"""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            print(f"⚠️  Erreur conversion {key}='{value}' en float, utilisation de {default}")
            return default
    
    def _get_bool_env(self, key: str, default: bool = False) -> bool:
        """Récupère une variable d'environnement boolean"""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    def _print_summary(self):
        """Affiche un résumé de la configuration"""
        print(f"\n{'='*60}")
        print(f"📋 CONFIGURATION DU BOT")
        print(f"{'='*60}")
        
        print(f"\n🔧 TRADING:")
        print(f"   Symbole: {self.symbol}")
        print(f"   Intervalle: {self.interval}")
        print(f"   Testnet: {self.testnet}")
        
        print(f"\n💰 FRAIS:")
        print(f"   Maker: {self.maker_fee}%")
        print(f"   Taker: {self.taker_fee}%")
        print(f"   Valeur min ordre: {self.min_order_value_usdc} USDC")
        
        print(f"\n🟢 ACHATS:")
        print(f"   Global: {self.buy_enabled}")
        print(f"   BULL: {self.bull_buy_enabled}")
        print(f"   BEAR: {self.bear_buy_enabled}")
        print(f"   RANGE: {self.range_buy_enabled}")
        
        print(f"\n🔴 VENTES:")
        print(f"   Global: {self.sell_enabled}")
        print(f"   BULL: {self.bull_sell_enabled}")
        print(f"   BEAR: {self.bear_sell_enabled}")
        print(f"   RANGE: {self.range_sell_enabled}")
        
        print(f"\n🐂 BULL MARKET:")
        print(f"   Buy Offset: {self.bull_buy_offset}$")
        print(f"   Sell Offset: {self.bull_sell_offset}$")
        print(f"   Pourcentage: {self.bull_percent}%")
        
        print(f"\n🐻 BEAR MARKET:")
        print(f"   Buy Offset: {self.bear_buy_offset}$")
        print(f"   Sell Offset: {self.bear_sell_offset}$")
        print(f"   Pourcentage: {self.bear_percent}%")
        
        print(f"\n↔️  RANGE MARKET:")
        print(f"   Buy Offset (fallback): {self.range_buy_offset}$")
        print(f"   Sell Offset (fallback): {self.range_sell_offset}$")
        print(f"   Dynamic Percent: {self.range_dynamic_percent}%")
        print(f"   Calculation Periods: {self.range_calculation_periods}")
        print(f"   Pourcentage: {self.range_percent}%")
        
        print(f"\n⏱️  TIMING:")
        print(f"   Délai initial: {self.initial_delay_minutes} min")
        print(f"   Intervalle vérif: {self.min_check_interval_minutes} min")
        print(f"   Vérif vente: {self.sell_check_interval_seconds} sec")
        
        print(f"\n📱 TELEGRAM:")
        print(f"   Activé: {self.telegram_enabled}")
        if self.telegram_enabled:
            print(f"   Token: {'✓' if self.telegram_bot_token else '✗'}")
            print(f"   Chat ID: {'✓' if self.telegram_chat_id else '✗'}")
        
        print(f"\n🗄️  DATABASE:")
        print(f"   Type: {self.db_type}")
        print(f"   Fichier: {self.db_file}")
        
        print(f"\n🌐 WEB:")
        print(f"   URL: {self.addresse}:{self.port}")
        
        print(f"\n{'='*60}")
    
    def reload(self) -> bool:
        """Recharge la configuration depuis le fichier .env
        
        Returns:
            bool: True si le rechargement a réussi, False sinon
        """
        try:
            print(f"\n{'='*60}")
            print(f"🔄 RECHARGEMENT DE LA CONFIGURATION")
            print(f"{'='*60}")
            
            # Sauvegarder l'ancienne config pour comparaison
            old_values = {
                'bull_buy_offset': self.bull_buy_offset,
                'bull_sell_offset': self.bull_sell_offset,
                'bear_buy_offset': self.bear_buy_offset,
                'bear_sell_offset': self.bear_sell_offset,
                'range_buy_offset': self.range_buy_offset,
                'range_sell_offset': self.range_sell_offset,
            }
            
            # Recharger le fichier .env (avec override=True pour forcer)
            load_dotenv(self.config_file, override=True)
            
            print(f"📋 Rechargement depuis: {self.config_file}")
            
            # Recharger toutes les variables d'environnement
            # API CONFIGURATION
            self.wallet_address = self._get_required_env('WALLET_ADDRESS')
            self.api_wallet_address = self._get_required_env('API_WALLET_ADDRESS')
            self.private_key = self._get_required_env('PRIVATE_KEY')
            
            # TRADING CONFIGURATION
            self.symbol = self._get_env('SYMBOL', 'BTC')
            self.interval = self._get_env('INTERVAL', '1h')
            self.limit = self._get_int_env('LIMIT', 100)
            self.testnet = self._get_bool_env('TESTNET', False)
            self.base_url = self._get_env('BASE_URL', 'https://api.hyperliquid.xyz')
            
            # TRADING FEES
            self.maker_fee = self._get_float_env('MAKER_FEE', 0.04)
            self.taker_fee = self._get_float_env('TAKER_FEE', 0.07)
            
            # ORDER CONSTRAINTS
            self.min_order_value_usdc = self._get_float_env('MIN_ORDER_VALUE_USDC', 10.0)
            
            # BUY ORDERS CONTROL
            self.buy_enabled = self._get_bool_env('BUY_ENABLED', True)
            self.bull_buy_enabled = self._get_bool_env('BULL_BUY_ENABLED', True)
            self.bear_buy_enabled = self._get_bool_env('BEAR_BUY_ENABLED', False)
            self.range_buy_enabled = self._get_bool_env('RANGE_BUY_ENABLED', True)
            
            # SELL ORDERS CONTROL
            self.sell_enabled = self._get_bool_env('SELL_ENABLED', True)
            self.bull_sell_enabled = self._get_bool_env('BULL_SELL_ENABLED', True)
            self.bear_sell_enabled = self._get_bool_env('BEAR_SELL_ENABLED', False)
            self.range_sell_enabled = self._get_bool_env('RANGE_SELL_ENABLED', True)
            
            # MOVING AVERAGES
            self.ma4_period = self._get_int_env('MA4_PERIOD', 4)
            self.ma8_period = self._get_int_env('MA8_PERIOD', 8)
            self.ma12_period = self._get_int_env('MA12_PERIOD', 12)
            self.ma12_flat_threshold = self._get_float_env('MA12_FLAT_THRESHOLD', 0.25)
            self.ma12_periods_check = self._get_int_env('MA12_PERIODS_CHECK', 5)
            
            # BULL MARKET PARAMETERS
            self.bull_buy_offset = self._get_float_env('BULL_BUY_OFFSET', 0)
            self.bull_sell_offset = self._get_float_env('BULL_SELL_OFFSET', 1000)
            self.bull_percent = self._get_float_env('BULL_PERCENT', 3)
            self.bull_time_pause = self._get_int_env('BULL_TIME_PAUSE', 10)
            self.bull_auto_interval_new = self._get_int_env('BULL_AUTO_INTERVAL_NEW', 360)
            
            # BEAR MARKET PARAMETERS
            self.bear_buy_offset = self._get_float_env('BEAR_BUY_OFFSET', -1000)
            self.bear_sell_offset = self._get_float_env('BEAR_SELL_OFFSET', 0)
            self.bear_percent = self._get_float_env('BEAR_PERCENT', 3)
            self.bear_time_pause = self._get_int_env('BEAR_TIME_PAUSE', 10)
            self.bear_auto_interval_new = self._get_int_env('BEAR_AUTO_INTERVAL_NEW', 360)
            
            # RANGE MARKET PARAMETERS
            self.range_buy_offset = self._get_float_env('RANGE_BUY_OFFSET', -400)
            self.range_sell_offset = self._get_float_env('RANGE_SELL_OFFSET', 400)
            self.range_percent = self._get_float_env('RANGE_PERCENT', 5)
            self.range_time_pause = self._get_int_env('RANGE_TIME_PAUSE', 10)
            self.range_auto_interval_new = self._get_int_env('RANGE_AUTO_INTERVAL_NEW', 180)
            self.range_dynamic_percent = self._get_float_env('RANGE_DYNAMIC_PERCENT', 75)
            self.range_calculation_periods = self._get_int_env('RANGE_CALCULATION_PERIODS', 20)
            
            # BOT TIMING
            self.initial_delay_minutes = self._get_int_env('INITIAL_DELAY_MINUTES', 0)
            self.min_check_interval_minutes = self._get_float_env('MIN_CHECK_INTERVAL_MINUTES', 10)
            self.short_sleep_minutes = self._get_float_env('SHORT_SLEEP_MINUTES', 1)
            self.sell_check_interval_seconds = self._get_int_env('SELL_CHECK_INTERVAL_SECONDS', 120)
            
            # TELEGRAM NOTIFICATIONS
            self.telegram_enabled = self._get_bool_env('TELEGRAM_ENABLED', False)
            self.telegram_bot_token = self._get_env('TELEGRAM_BOT_TOKEN', '')
            self.telegram_chat_id = self._get_env('TELEGRAM_CHAT_ID', '')
            self.telegram_on_order_placed = self._get_bool_env('TELEGRAM_ON_ORDER_PLACED', True)
            self.telegram_on_order_filled = self._get_bool_env('TELEGRAM_ON_ORDER_FILLED', True)
            self.telegram_on_profit = self._get_bool_env('TELEGRAM_ON_PROFIT', True)
            self.telegram_on_error = self._get_bool_env('TELEGRAM_ON_ERROR', True)
            self.telegram_daily_summary = self._get_bool_env('TELEGRAM_DAILY_SUMMARY', True)
            
            # DATABASE
            self.db_type = self._get_env('DB_TYPE', 'sqlite')
            self.db_file = self._get_env('DB_FILE', 'DB/trading_history.db')
            
            # WEBSITE
            self.addresse = self._get_env('ADDRESSE', 'http://0.0.0.0')
            self.port = self._get_int_env('PORT', 60000)
            
            # FILES
            self.config_file = self._get_env('CONFIG_FILE', '.env')
            self.bot_directory = self._get_env('BOT_DIRECTORY', '.')
            self.log_file = self._get_env('LOG_FILE', 'log/trading.log')
            
            # Afficher les changements
            print(f"\n📊 CHANGEMENTS DÉTECTÉS:")
            changes_found = False
            
            if old_values['bull_buy_offset'] != self.bull_buy_offset:
                print(f"   BULL_BUY_OFFSET: {old_values['bull_buy_offset']} → {self.bull_buy_offset}")
                changes_found = True
            if old_values['bull_sell_offset'] != self.bull_sell_offset:
                print(f"   BULL_SELL_OFFSET: {old_values['bull_sell_offset']} → {self.bull_sell_offset}")
                changes_found = True
            if old_values['bear_buy_offset'] != self.bear_buy_offset:
                print(f"   BEAR_BUY_OFFSET: {old_values['bear_buy_offset']} → {self.bear_buy_offset}")
                changes_found = True
            if old_values['bear_sell_offset'] != self.bear_sell_offset:
                print(f"   BEAR_SELL_OFFSET: {old_values['bear_sell_offset']} → {self.bear_sell_offset}")
                changes_found = True
            if old_values['range_buy_offset'] != self.range_buy_offset:
                print(f"   RANGE_BUY_OFFSET: {old_values['range_buy_offset']} → {self.range_buy_offset}")
                changes_found = True
            if old_values['range_sell_offset'] != self.range_sell_offset:
                print(f"   RANGE_SELL_OFFSET: {old_values['range_sell_offset']} → {self.range_sell_offset}")
                changes_found = True
            
            if not changes_found:
                print(f"   ℹ️  Aucun changement détecté dans les paramètres principaux")
            
            print(f"\n{'='*60}")
            print(f"✅ Configuration rechargée avec succès")
            print(f"{'='*60}\n")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Erreur lors du rechargement: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def validate(self) -> bool:
        """Valide que la configuration est correcte"""
        errors = []
        
        # Vérifier les valeurs critiques
        if not self.wallet_address or self.wallet_address == '0x...':
            errors.append("WALLET_ADDRESS non configuré")
        
        if not self.api_wallet_address or self.api_wallet_address == '0x...':
            errors.append("API_WALLET_ADDRESS non configuré")
        
        if not self.private_key or self.private_key == '0x...':
            errors.append("PRIVATE_KEY non configurée")
        
        if self.min_order_value_usdc < 10.0:
            errors.append("MIN_ORDER_VALUE_USDC doit être >= 10.0")
        
        if self.telegram_enabled:
            if not self.telegram_bot_token or self.telegram_bot_token == 'YOUR_BOT_TOKEN_HERE':
                errors.append("TELEGRAM_BOT_TOKEN non configuré")
            if not self.telegram_chat_id or self.telegram_chat_id == 'YOUR_CHAT_ID_HERE':
                errors.append("TELEGRAM_CHAT_ID non configuré")
        
        # Afficher les erreurs
        if errors:
            print(f"\n❌ ERREURS DE CONFIGURATION:")
            for error in errors:
                print(f"   - {error}")
            print(f"\n💡 Vérifiez votre fichier .env")
            return False
        
        print(f"\n✅ Configuration valide")
        return True


# Fonction utilitaire pour charger la configuration
def load_config(env_file: str = '.env') -> TradingConfig:
    """Charge et valide la configuration"""
    config = TradingConfig(env_file)
    
    if not config.validate():
        raise ValueError("Configuration invalide. Vérifiez votre fichier .env")
    
    return config
