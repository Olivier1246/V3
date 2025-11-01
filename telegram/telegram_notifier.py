"""
Module de notifications Telegram pour le bot de trading
Envoie des alertes en temps reel sur vos trades
"""

import requests
from datetime import datetime
from typing import Optional

class TelegramNotifier:
    """Gestion des notifications Telegram"""
    
    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        """
        Initialise le notifier Telegram
        
        Args:
            bot_token: Token du bot Telegram (obtenu via @BotFather)
            chat_id: ID du chat Telegram (obtenu via @userinfobot)
            enabled: Activer/desactiver les notifications
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        if self.enabled:
            self._test_connection()
    
    def _test_connection(self):
        """Test la connexion avec Telegram"""
        try:
            response = requests.get(f"{self.base_url}/getMe", timeout=5)
            if response.status_code == 200:
                bot_info = response.json()
                print(f"✅ Telegram connecte: @{bot_info['result']['username']}")
            else:
                print(f"⚠️  Erreur Telegram: {response.status_code}")
                self.enabled = False
        except Exception as e:
            print(f"⚠️  Erreur connexion Telegram: {e}")
            self.enabled = False
    
    def _send_message(self, message: str, parse_mode: str = "Markdown"):
        """Envoie un message Telegram"""
        if not self.enabled:
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"Erreur envoi Telegram: {e}")
            return False
    
    def send_bot_started(self, symbol: str, mode: str = "MAINNET"):
        """Notification de demarrage du bot"""
        message = f"""
🚀 *BOT DeMARRe*

📊 Symbole: `{symbol}`
🌐 Mode: `{mode}`
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Le bot est maintenant actif et surveille le marche.
"""
        self._send_message(message)
    
    def send_bot_stopped(self):
        """Notification d'arrêt du bot"""
        message = f"""
⏹️ *BOT ARRÊTe*

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Le bot a ete arrête manuellement.
"""
        self._send_message(message)
    
    def send_market_analysis(self, analysis: dict):
        """Notification d'analyse de marche"""
        market_type = analysis.get('market_type', 'UNKNOWN')
        
        # Emoji selon le type de marche
        emoji = {
            'BULL': '🐂',
            'BEAR': '🐻',
            'RANGE': '↔️'
        }.get(market_type, '❓')
        
        message = f"""
{emoji} *ANALYSE MARCHe: {market_type}*

💰 Prix: `${analysis['current_price']:,.2f}`
📈 MA4: `${analysis['ma4']:,.2f}`
📊 MA8: `${analysis['ma8']:,.2f}`
📉 MA12: `${analysis['ma12']:,.2f}`
📍 Tendance: `{analysis['trend']}`

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        self._send_message(message)
    
    def send_buy_order_placed(self, order_id: str, price: float, size: float, 
                              market_type: str, usdc_amount: float):
        """Notification d'ordre d'achat place"""
        message = f"""
🟢 *ORDRE D'ACHAT PLACe*

🆔 Order ID: `{order_id}`
💰 Prix: `${price:,.2f}`
📊 Quantite: `{size:.8f} BTC`
💵 Montant: `${usdc_amount:.2f}`
📈 Marche: `{market_type}`

⏰ {datetime.now().strftime('%H:%M:%S')}

_En attente de remplissage..._
"""
        self._send_message(message)
    
    def send_buy_order_filled(self, order_id: str, price: float, size: float):
        """Notification d'ordre d'achat rempli"""
        message = f"""
✅ *ACHAT REMPLI*

🆔 Order ID: `{order_id}`
💰 Prix: `${price:,.2f}`
📊 Quantite: `{size:.8f} BTC`

⏰ {datetime.now().strftime('%H:%M:%S')}

_Ordre de vente sera place automatiquement._
"""
        self._send_message(message)
    
    def send_sell_order_placed(self, order_id: str, price: float, size: float,
                               buy_price: float = None, market_type: str = None, usdc_amount: float = None):
        """Notification d'ordre de vente place"""
        message = f"""
🔴 *ORDRE DE VENTE PLACe*

🆔 Order ID: `{order_id}`
💰 Prix vente: `${price:,.2f}`
📊 Quantite: `{size:.8f} BTC`"""
        
        if usdc_amount:
            message += f"\n💵 Montant: `${usdc_amount:.2f}`"
        
        if buy_price:
            potential_profit = (price - buy_price) * size
            potential_percent = ((price - buy_price) / buy_price) * 100
            message += f"\n📈 Prix achat: `${buy_price:,.2f}`"
            message += f"\n💹 Profit potentiel: `${potential_profit:.2f}` ({potential_percent:+.2f}%)"
        
        if market_type:
            message += f"\n📈 Marche: `{market_type}`"
        
        message += f"""

⏰ {datetime.now().strftime('%H:%M:%S')}

_En attente de remplissage..._
"""
        self._send_message(message)
    
    def send_sell_order_filled(self, order_id: str, price: float, size: float,
                               buy_price: float, profit: float, profit_percent: float):
        """Notification d'ordre de vente rempli"""
        emoji = "💰" if profit > 0 else "⚠️"
        status = "PROFIT" if profit > 0 else "PERTE"
        
        message = f"""
{emoji} *VENTE REMPLIE - {status}*

🆔 Order ID: `{order_id}`
💰 Prix vente: `${price:,.2f}`
📊 Quantite: `{size:.8f} BTC`
📈 Prix achat: `${buy_price:,.2f}`

💹 *Profit NET: ${profit:.2f}* ({profit_percent:+.2f}%)

⏰ {datetime.now().strftime('%H:%M:%S')}

_Cycle de trading termine._
"""
        self._send_message(message)
    
    def send_order_cancelled(self, order_id: str, reason: str = "Annule manuellement"):
        """Notification d'ordre annule"""
        message = f"""
❌ *ORDRE ANNULe*

🆔 Order ID: `{order_id}`
📝 Raison: {reason}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        self._send_message(message)
    
    def send_error(self, error_type: str, error_message: str):
        """Notification d'erreur"""
        message = f"""
🚨 *ERREUR DeTECTeE*

⚠️ Type: `{error_type}`
📝 Message: {error_message}

⏰ {datetime.now().strftime('%H:%M:%S')}

_Verifiez les logs pour plus de details._
"""
        self._send_message(message)
    
    def send_daily_summary(self, stats: dict):
        """Notification du resume quotidien"""
        total_profit = stats.get('total_profit', 0)
        emoji = "📈" if total_profit >= 0 else "📉"
        
        message = f"""
{emoji} *ReSUMe QUOTIDIEN*

💰 Profit total: `${total_profit:.2f}`
📊 Trades: `{stats.get('total_trades', 0)}`
✅ Succes: `{stats.get('successful_trades', 0)}`
❌ echecs: `{stats.get('failed_trades', 0)}`
📈 Win Rate: `{stats.get('win_rate', 0):.1f}%`

⏰ {datetime.now().strftime('%Y-%m-%d')}
"""
        self._send_message(message)
    
    def send_config_reloaded(self, changes: dict):
        """Notification de rechargement de config"""
        changes_text = "\n".join([f"• {key}: `{value}`" for key, value in changes.items()])
        
        message = f"""
🔄 *CONFIGURATION RECHARGeE*

Changements detectes:
{changes_text}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        self._send_message(message)
    
    def send_stop_loss_triggered(self, order_id: str, loss: float, loss_percent: float):
        """Notification de stop loss declenche"""
        message = f"""
🛑 *STOP LOSS DeCLENCHe*

🆔 Order ID: `{order_id}`
💔 Perte: `${abs(loss):.2f}` ({loss_percent:.2f}%)

⏰ {datetime.now().strftime('%H:%M:%S')}

_Position fermee automatiquement pour limiter les pertes._
"""
        self._send_message(message)
    
    def send_take_profit_triggered(self, order_id: str, profit: float, profit_percent: float):
        """Notification de take profit declenche"""
        message = f"""
🎯 *TAKE PROFIT ATTEINT*

🆔 Order ID: `{order_id}`
💰 Profit: `${profit:.2f}` ({profit_percent:.2f}%)

⏰ {datetime.now().strftime('%H:%M:%S')}

_Position fermee automatiquement pour securiser le profit._
"""
        self._send_message(message)
    
    def send_custom_alert(self, title: str, message: str, emoji: str = "📢"):
        """Notification personnalisee"""
        full_message = f"""
{emoji} *{title}*

{message}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        self._send_message(full_message)


# Test du module
if __name__ == "__main__":
    # Configuration de test
    BOT_TOKEN = "YOUR_BOT_TOKEN"
    CHAT_ID = "YOUR_CHAT_ID"
    
    notifier = TelegramNotifier(BOT_TOKEN, CHAT_ID)
    
    # Test des notifications
    notifier.send_bot_started("BTC", "MAINNET")
    
    notifier.send_market_analysis({
        'market_type': 'BEAR',
        'current_price': 111027,
        'ma4': 111482,
        'ma8': 112030,
        'ma12': 112113,
        'trend': 'DOWNTREND'
    })
    
    notifier.send_buy_order_placed(
        order_id="123456",
        price=110527,
        size=0.0001,
        market_type="BEAR",
        usdc_amount=11.05
    )
