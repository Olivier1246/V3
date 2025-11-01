# 🤖 HL-SPOT Trading Bot - Hyperliquid

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Trading Bot](https://img.shields.io/badge/Trading-Automated-green.svg)](https://github.com)

Bot de trading automatisé pour la plateforme **Hyperliquid** avec stratégie de market making basée sur les moyennes mobiles et détection de type de marché (BULL/BEAR/RANGE).

---

## 📋 Table des Matières

- [✨ Fonctionnalités](#-fonctionnalités)
- [🏗️ Architecture](#️-architecture)
- [📦 Prérequis](#-prérequis)
- [⚙️ Installation](#️-installation)
- [🔧 Configuration](#-configuration)
- [🚀 Utilisation](#-utilisation)
- [📊 Interface Web](#-interface-web)
- [🔍 Modules](#-modules)
- [📈 Stratégies de Trading](#-stratégies-de-trading)
- [🛡️ Sécurité](#️-sécurité)
- [❓ FAQ](#-faq)
- [⚠️ Avertissement](#️-avertissement)
- [📄 Licence](#-licence)

---

## ✨ Fonctionnalités

### 🎯 Trading Automatisé
- **Détection automatique du type de marché** : BULL, BEAR, ou RANGE
- **Moyennes mobiles adaptatives** : MA4, MA8, MA12 pour l'analyse
- **Offsets dynamiques en RANGE** : Calcul automatique des zones d'achat/vente
- **Gestion séparée** : Threads indépendants pour achats et ventes
- **Synchronisation Hyperliquid** : Vérification automatique du statut des ordres

### 📊 Monitoring & Interface
- **Dashboard web interactif** : Vue en temps réel des positions et ordres
- **Statistiques détaillées** : Profit/perte, taux de réussite, historique
- **Visualisation des paires** : Suivi complet du cycle Buy → Sell → Complete
- **Logs structurés** : Traçabilité complète de toutes les opérations

### 🔔 Notifications
- **Telegram intégré** : Alertes en temps réel sur vos trades
- **Notifications configurables** : Ordres placés, exécutés, profits, erreurs
- **Résumés quotidiens** : Bilan automatique de performance

### 🛠️ Gestion Avancée
- **Configuration hot-reload** : Modification sans redémarrage
- **Base de données SQLite** : Historique complet des trades
- **Gestion des erreurs robuste** : Circuit breakers et retry logic
- **Mode Testnet** : Test sans risque avant production

---

## 🏗️ Architecture

```
HL-SPOT-BOT/
│
├── main.py                          # Point d'entrée principal
├── config.py                        # Gestion centralisée de la configuration
├── requirements.txt                 # Dépendances Python
├── .env                            # Configuration (PRIVÉE - ne pas partager!)
│
├── command/                        # Modules principaux
│   ├── bot_controller.py          # Contrôleur principal du bot
│   ├── trading_engine.py          # Interface avec Hyperliquid API
│   ├── market_analyzer.py         # Analyse de marché et moyennes mobiles
│   ├── buy_orders.py              # Gestion des ordres d'achat
│   ├── sell_orders.py             # Gestion des ordres de vente
│   ├── sync_hyperliquid_orders.py # Synchronisation des ordres
│   ├── web_interface.py           # Dashboard Flask
│   └── logger.py                  # Système de logs
│
├── DB/                            # Base de données
│   ├── database.py                # ORM et gestion BDD
│   └── trading_history.db         # SQLite (créé automatiquement)
│
├── telegram/                      # Notifications
│   └── telegram_notifier.py       # Intégration Telegram
│
├── templates/                     # Interface web
│   └── index.html                 # Dashboard HTML
│
├── static/                        # Assets web
│   └── style.css                  # Styles CSS
│
├── log/                           # Logs
│   └── trading.log                # Journal des opérations
│
└── utils/                         # Utilitaires
    └── diagnostic.py              # Vérification de l'installation
```

### 🔄 Flux de Trading

```
1. ANALYSE → MarketAnalyzer détecte le type de marché (BULL/BEAR/RANGE)
                    ↓
2. ACHAT → BuyOrderManager place un ordre d'achat avec offset
                    ↓
3. BDD → Enregistrement de la paire (status: 'Buy')
                    ↓
4. SYNC → OrderSynchronizer vérifie l'exécution (Buy → Sell)
                    ↓
5. VENTE → SellOrderManager place l'ordre de vente automatiquement
                    ↓
6. BDD → Mise à jour (status: 'Sell')
                    ↓
7. SYNC → Vérification de l'exécution (Sell → Complete)
                    ↓
8. PROFIT → Calcul et enregistrement du gain/perte
```

---

## 📦 Prérequis

### Système
- **Python** : 3.8 ou supérieur
- **OS** : Linux, macOS, Windows (WSL recommandé)
- **RAM** : 512 MB minimum
- **Connexion Internet** : Stable et permanente

### Compte Hyperliquid
- ✅ Compte créé sur [Hyperliquid](https://hyperliquid.xyz)
- ✅ Wallet configuré avec des fonds (USDC)
- ✅ Clé privée disponible (format 0x...)

### Optionnel
- Bot Telegram (via [@BotFather](https://t.me/BotFather))
- Serveur dédié ou VPS pour exécution 24/7

---

## ⚙️ Installation

### 1️⃣ Cloner le Projet

```bash
git clone https://github.com/votre-repo/hl-spot-bot.git
cd hl-spot-bot
```

### 2️⃣ Installation Automatique

**Linux / macOS** :
```bash
chmod +x install.sh
./install.sh
```

**Windows** :
```cmd
install.bat
```

### 3️⃣ Installation Manuelle

```bash
# Créer l'environnement virtuel
python3 -m venv venv

# Activer l'environnement
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements.txt
```

### 4️⃣ Vérification

```bash
python diagnostic.py
```

Ce script vérifie :
- ✅ Version Python
- ✅ Présence de tous les fichiers
- ✅ Installation des dépendances
- ✅ Configuration du .env

---

## 🔧 Configuration

### 1️⃣ Créer le Fichier .env

```bash
cp .env-template .env
nano .env  # ou votre éditeur préféré
```

### 2️⃣ Configuration Obligatoire

```ini
# ============================================
# API HYPERLIQUID (OBLIGATOIRE)
# ============================================
WALLET_ADDRESS=0x...                    # Votre adresse de wallet
API_WALLET_ADDRESS=0x...                # Adresse API (souvent identique)
PRIVATE_KEY=0x...                       # Votre clé privée (GARDEZ SECRÈTE!)

# ============================================
# TRADING CONFIGURATION
# ============================================
SYMBOL=BTC                              # Symbole à trader
INTERVAL=1h                             # Intervalle des bougies (1m, 5m, 15m, 1h, 4h)
TESTNET=False                           # True pour tester sans risque
BASE_URL=https://api.hyperliquid.xyz    # URL de l'API
```

### 3️⃣ Configuration Avancée

#### 🐂 BULL MARKET (Marché Haussier)
```ini
BULL_BUY_ENABLED=True                   # Activer les achats en BULL
BULL_SELL_ENABLED=True                  # Activer les ventes en BULL
BULL_BUY_OFFSET=0                       # Offset d'achat (0$ = au prix spot)
BULL_SELL_OFFSET=1000                   # Offset de vente (+1000$ au-dessus)
BULL_PERCENT=3                          # % du capital à utiliser (3%)
BULL_TIME_PAUSE=10                      # Pause entre ordres (minutes)
BULL_AUTO_INTERVAL_NEW=360              # Intervalle d'auto-achat (minutes)
```

#### 🐻 BEAR MARKET (Marché Baissier)
```ini
BEAR_BUY_ENABLED=False                  # Désactiver les achats en BEAR
BEAR_SELL_ENABLED=False                 # Désactiver les ventes en BEAR
BEAR_BUY_OFFSET=-1000                   # Offset d'achat (-1000$)
BEAR_SELL_OFFSET=0                      # Offset de vente
BEAR_PERCENT=3                          # % du capital
BEAR_TIME_PAUSE=10                      # Pause (minutes)
BEAR_AUTO_INTERVAL_NEW=360              # Intervalle (minutes)
```

#### ↔️ RANGE MARKET (Marché en Consolidation)
```ini
RANGE_BUY_ENABLED=True                  # Activer les achats en RANGE
RANGE_SELL_ENABLED=True                 # Activer les ventes en RANGE
RANGE_BUY_OFFSET=-400                   # Offset par défaut (fallback)
RANGE_SELL_OFFSET=400                   # Offset par défaut (fallback)
RANGE_PERCENT=5                         # % du capital (5%)
RANGE_DYNAMIC_PERCENT=75                # % dynamique du range (75%)
RANGE_CALCULATION_PERIODS=20            # Périodes pour calcul du range
RANGE_TIME_PAUSE=10                     # Pause (minutes)
RANGE_AUTO_INTERVAL_NEW=180             # Intervalle (minutes)
```

#### 📊 MOYENNES MOBILES
```ini
MA4_PERIOD=4                            # Période MA rapide
MA8_PERIOD=8                            # Période MA moyenne
MA12_PERIOD=12                          # Période MA lente
MA12_FLAT_THRESHOLD=0.25                # Seuil de détection RANGE (0.25%)
MA12_PERIODS_CHECK=5                    # Nb de périodes à vérifier
```

#### 🔔 TELEGRAM (Optionnel)
```ini
TELEGRAM_ENABLED=True                   # Activer Telegram
TELEGRAM_BOT_TOKEN=123456:ABC...        # Token du bot (@BotFather)
TELEGRAM_CHAT_ID=123456789              # ID du chat (@userinfobot)
TELEGRAM_ON_ORDER_PLACED=True           # Notifier ordres placés
TELEGRAM_ON_ORDER_FILLED=True           # Notifier ordres exécutés
TELEGRAM_ON_PROFIT=True                 # Notifier profits
TELEGRAM_ON_ERROR=True                  # Notifier erreurs
```

---

## 🚀 Utilisation

### Démarrage

**Linux / macOS** :
```bash
./run.sh
```

**Windows** :
```cmd
run.bat
```

**Manuel** :
```bash
source venv/bin/activate  # Activer l'environnement
python main.py
```

### Arrêt

```bash
# Ctrl+C dans le terminal
# ou
pkill -f main.py
```

### Rechargement de la Configuration

```bash
python reload_config.py
```

Cette commande recharge le `.env` sans redémarrer le bot.

---

## 📊 Interface Web

Le dashboard web est accessible à l'adresse :

```
http://localhost:60000
```

### Fonctionnalités du Dashboard

- **📈 Vue d'ensemble** : Statistiques en temps réel
- **📋 Toutes les paires** : Liste complète des ordres
- **💰 Performance** : Graphiques de profit/perte
- **⚙️ Configuration** : Affichage des paramètres actuels
- **🔄 Contrôles** : Start/Stop/Reload du bot

### Pages Disponibles

- `/` - Dashboard principal
- `/orders` - Liste des ordres
- `/config` - Configuration
- `/api/status` - API JSON du statut

---

## 🔍 Modules

### 🎮 bot_controller.py
Contrôleur principal qui orchestre tous les modules :
- Initialisation des composants
- Gestion du cycle de vie
- Coordination des threads

### 💹 trading_engine.py
Interface avec l'API Hyperliquid :
- Placement d'ordres (buy/sell)
- Récupération des soldes
- Annulation d'ordres
- Gestion des erreurs API

### 📊 market_analyzer.py
Analyse de marché :
- Calcul des moyennes mobiles (MA4, MA8, MA12)
- Détection du type de marché (BULL/BEAR/RANGE)
- Calcul dynamique des limites de range
- Détermination de la tendance

### 🟢 buy_orders.py
Gestion des achats :
- Thread dédié pour les ordres d'achat
- Calcul des offsets selon le marché
- Vérification des soldes USDC
- Enregistrement en base de données

### 🔴 sell_orders.py
Gestion des ventes :
- Thread dédié pour les ordres de vente
- Vérification des soldes BTC
- Placement automatique après achat
- Cache des échecs pour retry

### 🔄 sync_hyperliquid_orders.py
Synchronisation :
- Vérification toutes les 5 minutes
- Mise à jour des statuts (Buy → Sell → Complete)
- Calcul des profits/pertes
- Notifications Telegram

### 🗄️ database.py
Base de données :
- ORM pour SQLite
- Gestion des paires d'ordres
- Statistiques et historique
- Migrations automatiques

### 📝 logger.py
Système de logs :
- Logs structurés avec niveaux
- Support UTF-8 et emojis
- Rotation automatique
- Fichier + console

---

## 📈 Stratégies de Trading

### 🐂 Stratégie BULL MARKET

**Conditions** : MA4 > MA8 > MA12

**Paramètres par défaut** :
- Buy Offset : 0$ (prix spot)
- Sell Offset : +1000$
- Capital : 3%

**Logique** :
1. Acheter au prix actuel
2. Vendre avec un gain de ~1000$
3. Capitaliser sur la tendance haussière

### 🐻 Stratégie BEAR MARKET

**Conditions** : MA4 < MA8 < MA12

**Paramètres par défaut** :
- Trading désactivé (BUY_ENABLED=False)

**Logique** :
- Pas de trading en marché baissier (préservation du capital)
- Peut être activé avec prudence

### ↔️ Stratégie RANGE MARKET

**Conditions** : MA12 plate (variation < 0.25%)

**Paramètres** :
- Calcul dynamique à 75% du range
- Capital : 5%

**Logique** :
1. Détection du range (high/low sur 20 périodes)
2. Achat à 75% vers le bas du range
3. Vente à 75% vers le haut du range
4. Profit sur les oscillations

**Exemple** :
```
Range détecté : 90,000$ - 92,000$ (delta = 2,000$)
75% du delta = 1,500$
Offset = 1,500$ / 2 = 750$

→ Buy : Prix spot - 750$
→ Sell : Prix spot + 750$
```

---

## 🛡️ Sécurité

### ⚠️ Gestion de la Clé Privée

```bash
# JAMAIS commiter le .env !
echo ".env" >> .gitignore

# Permissions restrictives
chmod 600 .env

# Vérifier qu'il n'est pas tracké
git status
```

### 🔐 Bonnes Pratiques

1. **Utilisez le Testnet d'abord** : `TESTNET=True`
2. **Limitez le capital** : Commencez avec de petites sommes
3. **Surveillez régulièrement** : Vérifiez le dashboard
4. **Sauvegardez la BDD** : `cp DB/trading_history.db DB/backup_$(date +%Y%m%d).db`
5. **Logs rotatifs** : Configurez la rotation des logs

### 🚨 Circuit Breakers

Le bot intègre plusieurs protections :
- **MIN_ORDER_VALUE_USDC** : Montant minimum par ordre
- **Vérification des soldes** : Avant chaque ordre
- **Retry logic** : En cas d'erreur temporaire
- **Cache des échecs** : Évite les boucles infinies

---

## ❓ FAQ

### ❓ Le bot place des ordres en double ?

**Réponse** : Vérifiez les paramètres `TIME_PAUSE` et `AUTO_INTERVAL_NEW`. Augmentez-les pour espacer les ordres.

### ❓ Les ordres ne se remplissent pas ?

**Réponse** : 
- Vérifiez les offsets (trop éloignés du prix spot)
- Consultez l'order book sur Hyperliquid
- Réduisez les offsets pour plus de liquidité

### ❓ Comment tester sans risque ?

**Réponse** : 
```ini
TESTNET=True
```

### ❓ Puis-je modifier la config sans redémarrer ?

**Réponse** : Oui !
```bash
python reload_config.py
```

### ❓ Le bot crash avec "Circuit breaker" ?

**Réponse** : L'API Hyperliquid limite les requêtes. Le bot patiente automatiquement. Attendez 1-2 minutes.

### ❓ Comment voir mes trades passés ?

**Réponse** :
```bash
python view_order_pairs.py
```

### ❓ Les notifications Telegram ne fonctionnent pas ?

**Réponse** :
1. Vérifiez le `BOT_TOKEN` avec [@BotFather](https://t.me/BotFather)
2. Vérifiez le `CHAT_ID` avec [@userinfobot](https://t.me/userinfobot)
3. Démarrez une conversation avec votre bot
4. Consultez les logs : `tail -f log/trading.log`

---

## ⚠️ Avertissement

### 🚨 RISQUES FINANCIERS

**CE BOT EST FOURNI "EN L'ÉTAT" SANS AUCUNE GARANTIE.**

- ⚠️ Le trading de crypto-monnaies comporte des **risques importants**
- ⚠️ Vous pouvez **perdre tout votre capital**
- ⚠️ Les performances passées ne garantissent pas les résultats futurs
- ⚠️ Testez toujours en **TESTNET** avant la production
- ⚠️ N'investissez que ce que vous pouvez **vous permettre de perdre**

### 📋 Responsabilités

- ✅ **Vous êtes seul responsable** de vos décisions de trading
- ✅ Les auteurs ne sont **pas responsables des pertes financières**
- ✅ Comprenez la stratégie avant de l'utiliser
- ✅ Surveillez régulièrement votre bot
- ✅ Respectez les lois de votre juridiction

### 🔒 Sécurité

- ✅ Ne partagez **JAMAIS** votre clé privée
- ✅ Utilisez un wallet dédié au bot
- ✅ Activez l'authentification 2FA sur Hyperliquid
- ✅ Hébergez le bot sur un serveur sécurisé

---

## 📄 Licence

Ce projet est sous licence MIT. Voir [LICENSE.txt](LICENSE.txt) pour plus de détails.

---

## 🤝 Contribution

Les contributions sont les bienvenues !

1. Fork le projet
2. Créez une branche (`git checkout -b feature/amelioration`)
3. Commit vos changements (`git commit -m 'Ajout fonctionnalité'`)
4. Push vers la branche (`git push origin feature/amelioration`)
5. Ouvrez une Pull Request

---

## 📞 Support

- 📧 Email : Olivier@cmails.eu
- 💬 Discord : [Lien vers Discord]
- 📚 Documentation : [Wiki du projet]
- 🐛 Issues : [GitHub Issues]

---

## 🙏 Remerciements

- **Hyperliquid** pour leur excellente API
- **La communauté Python** pour les bibliothèques
- **Tous les contributeurs** du projet

---

## 📊 Statistiques du Projet

- **Langage** : Python 3.8+
- **Architecture** : Modulaire avec threads séparés
- **Base de données** : SQLite
- **Interface** : Flask + HTML/CSS
- **Tests** : En cours d'ajout

---

## 🗓️ Roadmap

- [ ] **v4.0** : Support multi-symboles (BTC, ETH, SOL...)
- [ ] **v4.1** : Machine Learning pour prédiction
- [ ] **v4.2** : Backtesting sur données historiques
- [ ] **v4.3** : Support PostgreSQL
- [ ] **v4.4** : API REST complète
- [ ] **v4.5** : Interface web React

---

## 📝 Changelog

### Version 3.0 (Actuelle)
- ✅ Architecture modulaire complète
- ✅ Séparation buy_orders.py / sell_orders.py
- ✅ Calcul dynamique du range à 75%
- ✅ Toutes variables dans .env
- ✅ Contrôle granulaire par marché
- ✅ Synchronisation améliorée

### Version 2.0
- ✅ Support BULL/BEAR/RANGE
- ✅ Interface web Flask
- ✅ Notifications Telegram

### Version 1.0
- ✅ Bot de base fonctionnel
- ✅ Ordres buy/sell automatiques

---

## 🎓 Ressources d'Apprentissage

- [Documentation Hyperliquid](https://hyperliquid.gitbook.io/)
- [Tutoriel Python](https://docs.python.org/3/tutorial/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Trading 101](https://www.investopedia.com/)

---

**⭐ Si ce projet vous aide, n'hésitez pas à lui donner une étoile sur GitHub ! ⭐**

Made with ❤️ by the Trading Bot Community
