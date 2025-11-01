# 📦 PACKAGE DE MIGRATION - BOT TRADING SIMPLIFIÉ

## 📁 Fichiers fournis

### 1. Fichiers Python principaux

| Fichier | Description | Action |
|---------|-------------|--------|
| **database.py** | Nouvelle structure BDD simplifiée | ⚠️ REMPLACER |
| **buy_orders.py** | Gestion des achats (1 thread) | ⚠️ REMPLACER |
| **sell_orders.py** | Gestion des ventes (1 thread) | ⚠️ REMPLACER |
| **bot_controller.py** | Contrôleur principal | ⚠️ REMPLACER |

### 2. Documentation

| Fichier | Description |
|---------|-------------|
| **README_MODIFICATIONS.md** | Documentation complète des changements |
| **env_template_simplified.txt** | Template du fichier .env |

### 3. Outils

| Fichier | Description |
|---------|-------------|
| **migrate_database.py** | Script de migration de la BDD |

---

## 🚀 INSTALLATION RAPIDE

### Étape 1: Sauvegarde

```bash
# Sauvegarder les fichiers actuels
cp database.py database.py.backup
cp buy_orders.py buy_orders.py.backup
cp sell_orders.py sell_orders.py.backup
cp bot_controller.py bot_controller.py.backup

# Sauvegarder la base de données
cp trading_history.db trading_history.db.backup
```

### Étape 2: Installation des nouveaux fichiers

```bash
# Copier les nouveaux fichiers
cp /path/to/downloads/database.py .
cp /path/to/downloads/buy_orders.py .
cp /path/to/downloads/sell_orders.py .
cp /path/to/downloads/bot_controller.py .
```

### Étape 3: Migration de la base de données

```bash
# Option A: Recommencer avec une nouvelle base (RECOMMANDÉ)
mv trading_history.db trading_history.db.old
# Le bot créera une nouvelle base au démarrage

# Option B: Utiliser le script de migration
python migrate_database.py
```

### Étape 4: Vérification du .env

```bash
# Comparer votre .env avec le template
diff .env env_template_simplified.txt

# Ajouter les variables manquantes si nécessaire
```

### Étape 5: Test

```bash
# Vérifier la configuration
python diagnostic.py

# Démarrer le bot
python main.py
```

---

## 🔑 CHANGEMENTS MAJEURS

### Architecture

**AVANT:**
- Logique complexe avec plusieurs modes
- Annulations automatiques d'ordres
- Gestion distribuée dans plusieurs fichiers

**APRÈS:**
- 1 thread d'achat unique
- 1 thread de vente unique
- Aucune annulation automatique
- Logique simplifiée et linéaire

### Base de données

**AVANT:**
```
order_pairs:
  - index
  - exchange
  - status
  - quantity_btc
  - prix_achat
  - prix_vente
  - gain_percent
  - gain_usdc
  - id_exchange_achat
  - id_exchange_vente
  - uuid
  - created_at
  - buy_filled_at
  - sell_filled_at
  - completed_at
```

**APRÈS:**
```
order_pairs:
  - index (auto-incrémente)
  - status (Buy/Sell/Complete)
  - quantity_usdc (calculé)
  - quantity_btc (de Hyperliquid)
  - buy_price_btc (spot + offset)
  - sell_price_btc (spot + offset)
  - gain_percent (calculé avec frais)
  - gain_usdc (calculé avec frais)
  - buy_order_id (de Hyperliquid)
  - sell_order_id (de Hyperliquid)
  - offset_display (format: -400/400)
  - market_type
  - symbol
  - uuid
  - created_at
  - buy_filled_at
  - sell_placed_at
  - completed_at
```

### Logique de trading

**ACHAT (buy_orders.py):**
```
BOUCLE INFINIE:
  1. Attendre AUTO_INTERVAL_NEW
  2. Analyser marché
  3. Calculer paramètres
  4. Placer ordre d'achat
  5. Enregistrer dans BDD (status='Buy')
```

**VENTE (sell_orders.py):**
```
BOUCLE INFINIE:
  1. Attendre TIME_PAUSE
  2. Vérifier ordres d'achat (status='Buy')
  3. Si rempli:
     - Marquer buy_filled
     - Placer ordre de vente
     - Update BDD (status='Sell')
  4. Vérifier ordres de vente (status='Sell')
  5. Si rempli:
     - Calculer gains
     - Update BDD (status='Complete')
```

---

## ⚙️ CONFIGURATION (.env)

### Variables essentielles

```env
# Global
BUY_ENABLED=true
SELL_ENABLED=true
MIN_ORDER_VALUE_USDC=10.0

# Par marché (BULL/BEAR/RANGE)
<MARKET>_BUY_ENABLED=true
<MARKET>_SELL_ENABLED=true
<MARKET>_BUY_OFFSET=0
<MARKET>_SELL_OFFSET=1000
<MARKET>_PERCENT=3
<MARKET>_TIME_PAUSE=10
<MARKET>_AUTO_INTERVAL_NEW=360

# Frais
TAKER_FEE=0.07
MAKER_FEE=0.04

# Timing
SELL_CHECK_INTERVAL_SECONDS=120
```

### Exemple complet

Voir le fichier `env_template_simplified.txt`

---

## 📊 FONCTIONNEMENT

### Cycle complet d'une paire

```
[Temps 0] ACHAT
  ↓ Thread Buy place ordre
  ↓ Status = 'Buy'
  ↓
[Temps +X] ACHAT REMPLI
  ↓ Thread Sell détecte
  ↓ Status = 'Sell'
  ↓ Place ordre de vente
  ↓
[Temps +Y] VENTE REMPLIE
  ↓ Thread Sell détecte
  ↓ Calcule gains
  ↓ Status = 'Complete'
  └─ Paire terminée
```

### Calculs automatiques

**Prix:**
```
Buy Price = Prix Spot + BUY_OFFSET
Sell Price = Prix Spot + SELL_OFFSET
```

**Quantité:**
```
Quantity USDC = Balance USDC disponible × (PERCENT / 100)
Quantity BTC = Quantity USDC / Buy Price
```

**Gains:**
```
Gain brut = (Sell Price - Buy Price) × Quantity BTC
Frais buy = Buy Price × Quantity × (TAKER_FEE / 100)
Frais sell = Sell Price × Quantity × (TAKER_FEE / 100)
Gain net = Gain brut - Frais buy - Frais sell
Gain % = (Gain net / Coût achat) × 100
```

---

## 🔍 VÉRIFICATION

### Après installation

```bash
# 1. Configuration
python diagnostic.py

# 2. Base de données
ls -lh trading_history.db*

# 3. Logs
tail -f trading.log

# 4. Interface web (si activée)
# Ouvrir dans un navigateur:
http://localhost:60000
```

### Vérifier les threads

Les logs doivent montrer :
```
✅ Thread d'achat démarré
✅ Thread de vente démarré
🔄 Thread de synchronisation démarré
```

### Vérifier les ordres

```bash
# Visualiser les paires
python view_order_pairs.py
```

---

## ⚠️ POINTS D'ATTENTION

### 1. Threads uniques
- 1 SEUL thread d'achat
- 1 SEUL thread de vente
- Ne pas lancer plusieurs instances du bot

### 2. Synchronisation
- Automatique au démarrage
- Automatique toutes les 5 minutes
- Manuelle après annulation

### 3. Minimum d'ordre
- 10 USDC minimum par ordre
- Vérifié avant placement
- Ajuster PERCENT si nécessaire

### 4. Balance disponible
- Calcul: Total - Hold
- Hold = somme des ordres ouverts
- Vérifier régulièrement

---

## 🆘 DÉPANNAGE

### Le bot ne place pas d'ordres

1. Vérifier les logs
2. Vérifier BUY_ENABLED / SELL_ENABLED
3. Vérifier <MARKET>_BUY_ENABLED
4. Vérifier la balance USDC disponible
5. Vérifier MIN_ORDER_VALUE_USDC

### Les ordres ne sont pas détectés

1. Vérifier SELL_CHECK_INTERVAL_SECONDS
2. Vérifier les logs du thread de vente
3. Lancer sync manuellement: `bot.sync_with_hyperliquid()`
4. Vérifier sur Hyperliquid directement

### Erreurs de base de données

1. Sauvegarder: `cp trading_history.db trading_history.db.backup`
2. Relancer: `python migrate_database.py`
3. En dernier recours: supprimer et recommencer

---

## 📞 SUPPORT

Pour toute question :

1. Consultez `README_MODIFICATIONS.md`
2. Vérifiez les logs: `tail -f trading.log`
3. Lancez le diagnostic: `python diagnostic.py`
4. Vérifiez votre .env vs `env_template_simplified.txt`

---

## ✅ CHECKLIST FINALE

Avant de démarrer le bot :

- [ ] Fichiers sauvegardés
- [ ] Nouveaux fichiers installés
- [ ] Base de données migrée ou réinitialisée
- [ ] .env vérifié et complet
- [ ] diagnostic.py réussi
- [ ] Logs accessibles
- [ ] Interface web fonctionnelle (optionnel)

---

**Version**: 2.0 Simplifiée  
**Date**: Janvier 2025  
**Compatibilité**: Python 3.8+  
**Plateforme**: Hyperliquid (Mainnet/Testnet)
