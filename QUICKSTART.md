# 🚀 GUIDE DE DÉMARRAGE RAPIDE

## ⚡ Installation en 30 secondes

### Linux / macOS

```bash
# 1. Télécharger le projet
cd trading-bot

# 2. Installer (UNE SEULE COMMANDE)
chmod +x install_auto.sh && ./install_auto.sh

# 3. Configurer votre clé privée
nano .env
# Modifier: PRIVATE_KEY=0xVOTRE_CLE

# 4. Tester en testnet
chmod +x deploy.sh
./deploy.sh start testnet fg
```

### Windows

```
1. Double-clic sur install_auto.bat
2. Éditer .env avec notepad
   - PRIVATE_KEY=0xVOTRE_CLE
3. Double-clic sur deploy.bat
```

---

## 📚 Fichiers créés

### 🔧 Installation

| Fichier | Description | Usage |
|---------|-------------|-------|
| `install_auto.sh` | Installation Linux/Mac | `./install_auto.sh` |
| `install_auto.bat` | Installation Windows | Double-clic |

**Ce qu'ils font :**
- ✅ Vérifient Python 3.8+
- ✅ Créent l'environnement virtuel
- ✅ Installent toutes les dépendances
- ✅ Créent la structure des dossiers
- ✅ Configurent le fichier .env
- ✅ Lancent le diagnostic

---

### 🚀 Déploiement

| Fichier | Description | Usage |
|---------|-------------|-------|
| `deploy.sh` | Déploiement Linux/Mac | `./deploy.sh start` |
| `deploy.bat` | Déploiement Windows | `deploy.bat start` |
| `Makefile` | Raccourcis Linux/Mac | `make start` |

**Commandes principales :**

```bash
# Linux/Mac
./deploy.sh start              # Démarrer (mainnet, background)
./deploy.sh start testnet fg   # Testnet en temps réel
./deploy.sh stop               # Arrêter
./deploy.sh status             # Statut
./deploy.sh logs               # Logs

# Ou avec Make (plus court)
make start                     # Démarrer
make start-test                # Testnet
make stop                      # Arrêter
make status                    # Statut
make logs                      # Logs

# Windows
deploy.bat start              # Démarrer
deploy.bat start testnet fg   # Testnet
deploy.bat stop               # Arrêter
deploy.bat status             # Statut
deploy.bat logs               # Logs
```

---

### 🐛 Correction du bug

| Fichier | Description |
|---------|-------------|
| `sync_hyperliquid_orders.py` | Module de synchronisation corrigé |

**Nouvelle logique :**
- Analyse par Order ID + Time (le plus récent)
- Résout le problème de la paire #85
- Trie l'historique par timestamp
- Prend le statut le plus récent

---

### 📖 Documentation

| Fichier | Description |
|---------|-------------|
| `INSTALLATION.md` | Guide complet d'installation |
| `README_DEPLOY.md` | Documentation des scripts |

---

## 🎯 Scénarios d'utilisation

### Scénario 1 : Test rapide (Testnet)

```bash
# Linux/Mac
./install_auto.sh              # Installer
nano .env                      # Configurer PRIVATE_KEY
./deploy.sh start testnet fg   # Tester

# Windows
install_auto.bat               # Installer
notepad .env                   # Configurer PRIVATE_KEY
deploy.bat start testnet fg    # Tester
```

**Durée : 5 minutes**

---

### Scénario 2 : Production (Mainnet)

```bash
# Linux/Mac
./install_auto.sh              # Installer
nano .env                      # Configurer
# Changer: TESTNET=false
./deploy.sh start mainnet bg   # Démarrer en production
./deploy.sh status             # Vérifier

# Windows
install_auto.bat               # Installer
notepad .env                   # Configurer
# Changer: TESTNET=false
deploy.bat start mainnet bg    # Démarrer
deploy.bat status              # Vérifier
```

**Durée : 10 minutes**

---

### Scénario 3 : Développement

```bash
# Linux/Mac avec Make
make install                   # Installer
make config                    # Configurer
make dev                       # Mode développement
# (équivalent à: deploy.sh start testnet fg)

# Linux/Mac sans Make
./install_auto.sh
nano .env
./deploy.sh start testnet fg
```

**Durée : 5 minutes**

---

## 💡 Commandes utiles

### Surveillance

```bash
# Voir le statut
./deploy.sh status        # Linux/Mac
deploy.bat status         # Windows
make status               # Linux/Mac (avec Make)

# Suivre les logs
./deploy.sh logs          # Linux/Mac
deploy.bat logs           # Windows
make logs                 # Linux/Mac (avec Make)

# Logs manuellement
tail -f log/trading.log   # Linux/Mac
type log\trading.log      # Windows
```

### Gestion

```bash
# Arrêter
./deploy.sh stop          # Linux/Mac
deploy.bat stop           # Windows
make stop                 # Linux/Mac (avec Make)

# Redémarrer
./deploy.sh restart       # Linux/Mac
deploy.bat restart        # Windows
make restart              # Linux/Mac (avec Make)
```

### Diagnostic

```bash
# Diagnostic complet
python utils/diagnostic.py         # Tous systèmes
make diagnostic                    # Linux/Mac (avec Make)

# Vérifier l'environnement
make info                          # Linux/Mac (avec Make)
```

---

## 🔧 Configuration rapide (.env)

### Paramètres essentiels

```bash
# CLÉ PRIVÉE (OBLIGATOIRE)
PRIVATE_KEY=0xVOTRE_CLE_PRIVEE_66_CARACTERES

# MODE
TESTNET=false              # false = mainnet, true = testnet

# SYMBOLE
SYMBOL=BTC

# PORT WEB
PORT=60000

# TRADING
BULL_BUY_OFFSET=0
BULL_SELL_OFFSET=1000
BULL_PERCENT=10

# TELEGRAM (optionnel)
TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

---

## 📊 Interface Web

Une fois démarré, accédez au dashboard :

```
http://localhost:60000
```

**Fonctionnalités :**
- 📈 Visualisation des trades
- 📊 Statistiques en temps réel
- 💰 Solde et positions
- 📋 Historique des ordres
- ⚙️ Configuration

---

## 🆘 Aide rapide

### Le bot ne démarre pas ?

```bash
# 1. Vérifier l'installation
python utils/diagnostic.py

# 2. Vérifier les logs
tail -50 log/trading.log        # Linux/Mac
type log\trading.log            # Windows

# 3. Vérifier le fichier .env
cat .env                        # Linux/Mac
type .env                       # Windows
```

### Réinstaller complètement ?

```bash
# Linux/Mac
./deploy.sh stop               # Arrêter
rm -rf venv log/*              # Supprimer
./install_auto.sh              # Réinstaller

# Windows
deploy.bat stop                # Arrêter
rmdir /s /q venv               # Supprimer venv
del /q log\*                   # Supprimer logs
install_auto.bat               # Réinstaller
```

---

## 🎓 Workflow recommandé

```
1. Installation
   └─> ./install_auto.sh (ou install_auto.bat)

2. Configuration
   └─> Éditer .env (PRIVATE_KEY minimum)

3. Test en Testnet
   └─> ./deploy.sh start testnet fg
   └─> Vérifier que tout fonctionne
   └─> Tester quelques cycles

4. Production en Mainnet
   └─> Modifier .env (TESTNET=false)
   └─> ./deploy.sh start mainnet bg
   └─> Surveiller: ./deploy.sh status

5. Surveillance quotidienne
   └─> ./deploy.sh status
   └─> ./deploy.sh logs
   └─> Interface web: http://localhost:60000
```

---

## ⚡ Commandes ultra-rapides (avec Make)

```bash
# Linux/Mac uniquement

make install       # Installer
make config        # Configurer
make start-test    # Tester (testnet)
make start-prod    # Production (mainnet)
make status        # Statut
make logs          # Logs
make stop          # Arrêter
make help          # Aide
```

---

## 🎯 En résumé

### 3 fichiers pour tout gérer

1. **`install_auto.sh`** (ou `.bat`) → Installation en 1 commande
2. **`deploy.sh`** (ou `.bat`) → Gestion complète du bot
3. **`Makefile`** (optionnel) → Raccourcis ultra-rapides

### 3 commandes pour démarrer

```bash
# Linux/Mac
./install_auto.sh
./deploy.sh start testnet fg
./deploy.sh status

# Ou avec Make
make install
make start-test
make status
```

### 3 modes disponibles

- **Testnet + Foreground** : Pour tester et voir les logs
- **Testnet + Background** : Pour tester en arrière-plan
- **Mainnet + Background** : Pour la production

---

## 🚀 Prêt à démarrer !

```bash
# Linux/Mac - Installation + Test en 3 lignes
chmod +x install_auto.sh && ./install_auto.sh
nano .env  # Configurer PRIVATE_KEY
./deploy.sh start testnet fg

# Ou avec Make (encore plus court)
make install
make config
make start-test
```

**Bon trading ! 💰📈**
