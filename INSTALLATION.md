# 🤖 BOT TRADING HYPERLIQUID - GUIDE D'INSTALLATION ET DE DÉPLOIEMENT

## 📋 Table des matières

1. [Prérequis](#prérequis)
2. [Installation automatique](#installation-automatique)
3. [Configuration](#configuration)
4. [Déploiement](#déploiement)
5. [Commandes disponibles](#commandes-disponibles)
6. [Dépannage](#dépannage)
7. [Structure du projet](#structure-du-projet)

---

## 🔧 Prérequis

### Système d'exploitation
- **Linux** (Ubuntu 20.04+, Debian 10+)
- **macOS** (10.14+)
- **Windows** (10/11)

### Logiciels requis
- **Python 3.8+** ([Télécharger](https://www.python.org/downloads/))
- **pip** (gestionnaire de paquets Python)
- **Git** (optionnel, pour cloner le projet)

### Compte Hyperliquid
- Compte Hyperliquid actif
- Clé privée (wallet Ethereum compatible)
- Fonds sur mainnet ou testnet

---

## 🚀 Installation automatique

### Linux / macOS

```bash
# 1. Rendre le script exécutable
chmod +x install_auto.sh

# 2. Lancer l'installation (UNE SEULE COMMANDE)
./install_auto.sh
```

**Ce script effectue automatiquement :**
- ✅ Vérification de Python 3.8+
- ✅ Création de l'environnement virtuel
- ✅ Installation des dépendances
- ✅ Création de la structure des dossiers
- ✅ Configuration du fichier .env
- ✅ Diagnostic complet

### Windows

```cmd
REM 1. Clic droit sur install_auto.bat
REM 2. Sélectionner "Exécuter en tant qu'administrateur"
```

**Ou en ligne de commande :**
```cmd
install_auto.bat
```

---

## ⚙️ Configuration

### Fichier .env

Après l'installation, éditez le fichier `.env` :

#### Linux / macOS
```bash
nano .env
# ou
vim .env
```

#### Windows
```cmd
notepad .env
```

### Paramètres essentiels

```bash
# ========================================
# HYPERLIQUID - CONFIGURATION
# ========================================

# 🔑 CLÉ PRIVÉE (OBLIGATOIRE)
PRIVATE_KEY=0xVOTRE_CLE_PRIVEE_ICI_66_CARACTERES

# 🌐 MODE (true = testnet, false = mainnet)
TESTNET=false

# 📊 SYMBOLE
SYMBOL=BTC

# ⏰ INTERVALLE DES CHANDELIERS
INTERVAL=1h

# 🔢 PORT DE L'INTERFACE WEB
PORT=60000

# ========================================
# TRADING - PARAMÈTRES PAR MARCHÉ
# ========================================

# 🐂 MARCHÉ HAUSSIER (BULL)
BULL_BUY_OFFSET=0
BULL_SELL_OFFSET=1000
BULL_PERCENT=10
BULL_TIME_PAUSE=30
BULL_AUTO_INTERVAL_NEW=60
BULL_BUY_ENABLED=true

# 🐻 MARCHÉ BAISSIER (BEAR)
BEAR_BUY_OFFSET=-500
BEAR_SELL_OFFSET=500
BEAR_PERCENT=5
BEAR_TIME_PAUSE=60
BEAR_AUTO_INTERVAL_NEW=120
BEAR_BUY_ENABLED=false

# 📐 MARCHÉ EN RANGE
RANGE_BUY_OFFSET=-200
RANGE_SELL_OFFSET=200
RANGE_PERCENT=15
RANGE_TIME_PAUSE=45
RANGE_AUTO_INTERVAL_NEW=90
RANGE_DYNAMIC_PERCENT=75
RANGE_BUY_ENABLED=true

# ========================================
# TELEGRAM (OPTIONNEL)
# ========================================

TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Notifications
TELEGRAM_ON_BOT_START=true
TELEGRAM_ON_ORDER_PLACED=true
TELEGRAM_ON_ORDER_FILLED=true
TELEGRAM_ON_ERROR=true
```

---

## 🎯 Déploiement

### Commandes de base

#### Linux / macOS

```bash
# Rendre le script exécutable (une seule fois)
chmod +x deploy.sh

# Démarrer le bot
./deploy.sh start                    # Mainnet, arrière-plan
./deploy.sh start mainnet bg         # Mainnet, arrière-plan (explicite)
./deploy.sh start testnet fg         # Testnet, temps réel
./deploy.sh start mainnet fg         # Mainnet, temps réel

# Arrêter le bot
./deploy.sh stop

# Redémarrer le bot
./deploy.sh restart
./deploy.sh restart testnet bg

# Voir le statut
./deploy.sh status

# Suivre les logs en temps réel
./deploy.sh logs

# Afficher l'aide
./deploy.sh help
```

#### Windows

```cmd
REM Démarrer le bot
deploy.bat start                    REM Mainnet, arrière-plan
deploy.bat start mainnet bg         REM Mainnet, arrière-plan (explicite)
deploy.bat start testnet fg         REM Testnet, temps réel
deploy.bat start mainnet fg         REM Mainnet, temps réel

REM Arrêter le bot
deploy.bat stop

REM Redémarrer le bot
deploy.bat restart
deploy.bat restart testnet bg

REM Voir le statut
deploy.bat status

REM Voir les logs
deploy.bat logs

REM Afficher l'aide
deploy.bat help
```

---

## 📚 Commandes disponibles

### deploy.sh / deploy.bat

| Commande | Description | Exemple |
|----------|-------------|---------|
| `start` | Démarre le bot | `./deploy.sh start mainnet bg` |
| `stop` | Arrête le bot | `./deploy.sh stop` |
| `restart` | Redémarre le bot | `./deploy.sh restart testnet fg` |
| `status` | Affiche le statut | `./deploy.sh status` |
| `logs` | Suit les logs | `./deploy.sh logs` |
| `help` | Affiche l'aide | `./deploy.sh help` |

### Modes disponibles

| Mode | Description | Valeur .env |
|------|-------------|-------------|
| `mainnet` | Production avec vrais fonds | `TESTNET=false` |
| `testnet` | Test sans vrais fonds | `TESTNET=true` |

### Types d'exécution

| Type | Description | Comportement |
|------|-------------|--------------|
| `fg` | Foreground | Affichage temps réel dans le terminal |
| `bg` | Background | Tâche de fond, logs dans fichier |

---

## 🔍 Dépannage

### Le bot ne démarre pas

**Vérifications :**
```bash
# Linux/Mac
python utils/diagnostic.py

# Windows
python utils\diagnostic.py
```

**Problèmes courants :**

1. **Clé privée invalide**
   - Vérifiez que `PRIVATE_KEY` commence par `0x`
   - Longueur : 66 caractères exactement

2. **Dépendances manquantes**
   ```bash
   # Linux/Mac
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Windows
   venv\Scripts\activate.bat
   pip install -r requirements.txt
   ```

3. **Port déjà utilisé**
   - Modifiez `PORT` dans le fichier `.env`
   - Par défaut : `60000`

4. **Solde insuffisant**
   - Vérifiez votre solde USDC/BTC sur Hyperliquid
   - Minimum recommandé : 100 USDC

### Le bot s'arrête tout seul

**Consultez les logs :**
```bash
# Linux/Mac
tail -100 log/trading.log

# Windows
powershell -Command "Get-Content log\trading.log -Tail 100"
```

**Causes fréquentes :**
- Erreur de connexion à l'API Hyperliquid
- Ordre refusé (valeur trop faible)
- Circuit breaker activé (trop d'échecs)

### Réinitialiser complètement

#### Linux / macOS
```bash
# Arrêter le bot
./deploy.sh stop

# Supprimer l'environnement virtuel
rm -rf venv

# Supprimer les logs
rm -rf log/*

# Réinstaller
./install_auto.sh
```

#### Windows
```cmd
REM Arrêter le bot
deploy.bat stop

REM Supprimer l'environnement virtuel
rmdir /s /q venv

REM Supprimer les logs
del /q log\*

REM Réinstaller
install_auto.bat
```

---

## 📁 Structure du projet

```
trading-bot/
│
├── 📄 install_auto.sh          # Installation automatique (Linux/Mac)
├── 📄 install_auto.bat         # Installation automatique (Windows)
├── 📄 deploy.sh                # Déploiement (Linux/Mac)
├── 📄 deploy.bat               # Déploiement (Windows)
│
├── 📄 main.py                  # Point d'entrée principal
├── 📄 config.py                # Configuration centralisée
├── 📄 .env                     # Variables d'environnement
├── 📄 requirements.txt         # Dépendances Python
│
├── 📂 command/                 # Modules de trading
│   ├── bot_controller.py       # Contrôleur principal
│   ├── buy_orders.py           # Gestion ordres d'achat
│   ├── sell_orders.py          # Gestion ordres de vente
│   ├── sync_hyperliquid_orders.py  # Synchronisation
│   ├── trading_engine.py       # Moteur de trading
│   ├── market_analyzer.py      # Analyse du marché
│   ├── logger.py               # Système de logs
│   └── web_interface.py        # Interface web
│
├── 📂 DB/                      # Base de données
│   ├── database.py             # Gestion BDD
│   └── trading_history.db      # Historique des trades
│
├── 📂 telegram/                # Notifications
│   └── telegram_notifier.py    # Bot Telegram
│
├── 📂 utils/                   # Utilitaires
│   └── diagnostic.py           # Script de diagnostic
│
├── 📂 templates/               # Interface web
│   └── index.html              # Dashboard
│
├── 📂 static/                  # Fichiers statiques
│   └── style.css               # Styles CSS
│
├── 📂 log/                     # Logs
│   └── trading.log             # Log principal
│
└── 📂 venv/                    # Environnement virtuel Python
```

---

## 🎓 Guide de démarrage rapide

### 1. Installation (30 secondes)

```bash
# Linux/Mac
./install_auto.sh

# Windows
install_auto.bat
```

### 2. Configuration (2 minutes)

```bash
# Éditer le fichier .env
nano .env  # ou notepad .env sur Windows

# Configurer au minimum :
# - PRIVATE_KEY=0xVOTRE_CLE
# - TESTNET=true (pour tester)
```

### 3. Test en mode TESTNET (conseillé)

```bash
# Linux/Mac
./deploy.sh start testnet fg

# Windows
deploy.bat start testnet fg
```

### 4. Production en mode MAINNET

```bash
# 1. Modifier .env
TESTNET=false

# 2. Démarrer en arrière-plan
# Linux/Mac
./deploy.sh start mainnet bg

# Windows
deploy.bat start mainnet bg
```

### 5. Surveillance

```bash
# Voir le statut
./deploy.sh status        # Linux/Mac
deploy.bat status         # Windows

# Suivre les logs
./deploy.sh logs          # Linux/Mac
deploy.bat logs           # Windows
```

---

## 📞 Support

### Logs et diagnostics

```bash
# Diagnostic complet
python utils/diagnostic.py

# Logs du bot
cat log/trading.log           # Linux/Mac
type log\trading.log          # Windows
```

### Interface web

Une fois le bot démarré, accédez au dashboard :
```
http://localhost:60000
```

---

## 📝 Notes importantes

### Sécurité

⚠️ **JAMAIS** partager votre clé privée
⚠️ **TOUJOURS** tester en mode TESTNET avant mainnet
⚠️ **SURVEILLER** régulièrement les logs et les positions

### Bonnes pratiques

✅ Commencer avec de petits montants
✅ Utiliser TESTNET pour les tests
✅ Surveiller le bot quotidiennement
✅ Sauvegarder régulièrement la base de données
✅ Activer les notifications Telegram

### Responsabilité

Ce bot est fourni "tel quel" sans garantie. Le trading comporte des risques. N'investissez que ce que vous pouvez vous permettre de perdre.

---

## 🚀 Prêt à trader !

Vous avez tout installé ? Parfait ! 🎉

```bash
# Linux/Mac - Démarrer en testnet
./deploy.sh start testnet fg

# Windows - Démarrer en testnet
deploy.bat start testnet fg
```

Bon trading ! 💰📈
