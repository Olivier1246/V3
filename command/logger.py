import logging
import sys
import os
from datetime import datetime
from config import TradingConfig

class TradingLogger:
    """Gestion des logs pour le bot de trading"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.setup_logger()
    
    def setup_logger(self):
        """Configure le logger avec support UTF-8"""
        self.logger = logging.getLogger('TradingBot')
        self.logger.setLevel(logging.INFO)
        
        # ⚠️ FIX: Éviter les doublons - ne pas ajouter de handlers si le logger en a déjà
        if self.logger.handlers:
            # Logger déjà configuré, ne rien faire
            return
        
        # Format des logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Créer le dossier log s'il n'existe pas
        log_dir = os.path.dirname(self.config.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            print(f"📁 Dossier créé: {log_dir}")
        
        # Handler pour fichier avec encodage UTF-8
        file_handler = logging.FileHandler(
            self.config.log_file, 
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Handler pour console avec gestion des emojis
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Force UTF-8 pour la console si possible
        if sys.platform == 'win32':
            try:
                # Essayer de configurer UTF-8 pour Windows
                sys.stdout.reconfigure(encoding='utf-8')
            except:
                pass
        
        # Ajouter les handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Empêcher la propagation aux loggers parents pour éviter les doublons
        self.logger.propagate = False
    
    def _safe_log(self, level, message: str):
        """Log avec gestion robuste des caracteres speciaux"""
        try:
            # Essayer de logger normalement
            getattr(self.logger, level)(message)
        except (UnicodeEncodeError, UnicodeDecodeError):
            # En cas d'erreur, remplacer les emojis par du texte
            emoji_replacements = {
                '⏳': '[WAIT]',
                '✅': '[OK]',
                '❌': '[ERROR]',
                '⚠️': '[WARN]',
                '💰': '[MONEY]',
                '🛒': '[BUY]',
                '📊': '[CHART]',
                '🚀': '[START]',
                '👋': '[STOP]',
                '📋': '[INFO]',
                '🔧': '[CONFIG]',
                '💼': '[WALLET]',
                '🔑': '[KEY]',
                '🎯': '[TARGET]',
                '🔡': '[TEXT]',
                '📤': '[SEND]',
                '🗑️': '[DELETE]',
                '⏱️': '[TIME]',
            }
            
            safe_message = message
            for emoji, replacement in emoji_replacements.items():
                safe_message = safe_message.replace(emoji, replacement)
            
            # Si encore des erreurs, forcer ASCII
            safe_message = safe_message.encode('ascii', 'replace').decode('ascii')
            getattr(self.logger, level)(safe_message)
    
    def info(self, message: str):
        """Log une information"""
        self._safe_log('info', message)
    
    def warning(self, message: str):
        """Log un avertissement"""
        self._safe_log('warning', message)
    
    def error(self, message: str):
        """Log une erreur"""
        self._safe_log('error', message)
    
    def debug(self, message: str):
        """Log un message de debug"""
        self._safe_log('debug', message)
    
    def log_market_analysis(self, analysis: dict):
        """Log l'analyse du marche"""
        self.info(
            f"Analyse Marche - Prix: {analysis['current_price']:.2f} | "
            f"MA4: {analysis['ma4']:.2f} | MA8: {analysis['ma8']:.2f} | "
            f"MA12: {analysis['ma12']:.2f} | Type: {analysis['market_type']} | "
            f"Tendance: {analysis['trend']}"
        )
    
    def log_order(self, order_type: str, symbol: str, price: float, size: float, result: dict = None):
        """Log un ordre"""
        status = "SUCCES" if result else "ECHEC"
        self.info(
            f"Ordre {order_type} - {symbol} | Prix: {price:.2f} | "
            f"Taille: {size:.4f} | Statut: {status}"
        )
        if result:
            self.debug(f"Resultat de l'ordre: {result}")
    
    def log_cancel_order(self, order_id: str, success: bool = True):
        """Log l'annulation d'un ordre"""
        status = "SUCCES" if success else "ECHEC"
        self.info(f"Annulation ordre {order_id} - Statut: {status}")
    
    def log_position(self, symbol: str, size: float, entry_price: float):
        """Log la position actuelle"""
        self.info(
            f"Position - {symbol} | Taille: {size:.4f} | "
            f"Prix d'entree: {entry_price:.2f}"
        )
    
    def log_balance(self, asset: str, balance: float):
        """Log le solde"""
        self.info(f"Solde {asset}: {balance:.2f}")
    
    def log_trade_result(self, profit_loss: float, success: bool):
        """Log le resultat d'un trade"""
        result = "PROFIT" if profit_loss > 0 else "PERTE"
        self.info(f"Resultat du trade: {result} de {abs(profit_loss):.2f} USDC")
    
    def log_bot_start(self):
        """Log le demarrage du bot"""
        self.info("=" * 60)
        self.info("BOT DE TRADING HYPERLIQUID - DEMARRAGE")
        self.info(f"Symbole: {self.config.symbol}")
        self.info(f"Intervalle: {self.config.interval}")
        self.info(f"Testnet: {self.config.testnet}")
        self.info("=" * 60)
    
    def log_bot_stop(self):
        """Log l'arrêt du bot"""
        self.info("=" * 60)
        self.info("BOT DE TRADING HYPERLIQUID - ARRET")
        self.info("=" * 60)
