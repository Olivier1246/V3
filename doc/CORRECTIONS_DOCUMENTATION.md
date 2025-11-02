# 🔧 CORRECTIONS DES ORDRES DE VENTE - DOCUMENTATION COMPLÈTE

## 📋 Problèmes identifiés

### 1️⃣ Les ordres de vente ne correspondent pas aux montants de la BDD

**CAUSE** : La quantité BTC **calculée** était stockée dans la BDD, mais la quantité **réelle** (après frais maker d'achat) n'était jamais mise à jour.

**Exemple concret** :
```
Calcul initial : acheter pour 100 USDC à 100000$ → 0.001 BTC
Ordre placé    : 0.001 BTC
Frais maker    : 0.04% = 0.00000004 BTC
Réel reçu      : 0.00099996 BTC
BDD stockée    : 0.001 BTC ❌ (quantité calculée, pas réelle)

→ Lors de la vente, on essaie de vendre 0.001 BTC
→ Solde insuffisant car on n'a que 0.00099996 BTC
→ ÉCHEC
```

### 2️⃣ La BDD n'est pas mise à jour quand l'ordre est filled

**CAUSE** : Dans `sync_hyperliquid_orders.py`, la quantité réelle était récupérée mais **jamais enregistrée** :

```python
# ANCIEN CODE (ligne 209-220)
elif status == 'filled':
    total_filled = order_status['size']  # ✅ Quantité RÉELLE récupérée
    
    # ❌ PROBLÈME : On ne met PAS À JOUR la BDD !
    self.database.update_pair_status(pair.index, 'Sell')
    # Manque : self.database.update_quantity_btc(pair.index, total_filled)
```

### 3️⃣ Frais maker non pris en compte

**MODE SPOT LIMIT** = Toujours des ordres MAKER, jamais TAKER

Les frais maker (0.04%) sont appliqués :
- À l'achat : déduits de la quantité BTC reçue
- À la vente : déduits du montant USDC reçu (pas de la quantité BTC)

---

## ✅ SOLUTIONS APPLIQUÉES

### 🔹 Fichier 1 : `database.py`

**3 nouvelles méthodes ajoutées** :

#### 1. `update_quantity_btc(pair_index, new_quantity_btc)`
```python
# Met à jour la quantité BTC RÉELLE après fill de l'ordre d'achat
# Appelée par sync_hyperliquid_orders.py
def update_quantity_btc(self, pair_index: int, new_quantity_btc: float) -> bool:
    """
    Args:
        pair_index: Index de la paire
        new_quantity_btc: Quantité BTC réelle reçue après frais
    """
```

**Exemple d'utilisation** :
```python
# Après que l'ordre d'achat soit rempli
total_filled = 0.00099996  # Quantité réelle depuis Hyperliquid
database.update_quantity_btc(pair_index=42, new_quantity_btc=total_filled)
```

#### 2. `update_pair_status(pair_index, new_status)`
```python
# Change le statut d'une paire : 'Buy' → 'Sell' → 'Complete'
# Met à jour automatiquement les timestamps
def update_pair_status(self, pair_index: int, new_status: str) -> bool:
```

#### 3. `get_pairs_by_status(status)`
```python
# Récupère toutes les paires ayant un statut donné
def get_pairs_by_status(self, status: str):
    """
    Args:
        status: 'Buy', 'Sell', ou 'Complete'
    Returns:
        list: Liste des paires
    """
```

**Correction du calcul des gains** :
```python
# ANCIEN : utilisait taker_fee (0.07%)
taker_fee_percent = self.config.taker_fee / 100

# NOUVEAU : utilise maker_fee (0.04%)
maker_fee_percent = self.config.maker_fee / 100
```

---

### 🔹 Fichier 2 : `sync_hyperliquid_orders.py`

**Modification de `_check_buy_orders()`** :

```python
elif status == 'filled':
    total_filled = order_status['size']  # Quantité RÉELLE depuis Hyperliquid
    
    self.logger.info(f"✅ Ordre d'achat {buy_order_id} REMPLI")
    self.logger.info(f"   Quantité calculée: {pair.quantity_btc:.8f} BTC")
    self.logger.info(f"   Quantité réelle: {total_filled:.8f} BTC")
    self.logger.info(f"   Différence (frais maker): {pair.quantity_btc - total_filled:.8f} BTC")
    
    # 1️⃣ NOUVEAU : Mettre à jour la quantité BTC réelle
    self.database.update_quantity_btc(pair.index, total_filled)
    
    # 2️⃣ Mettre à jour le statut
    self.database.update_pair_status(pair.index, 'Sell')
```

**Avant** :
- Récupérait la quantité réelle ✅
- Ne la stockait PAS dans la BDD ❌

**Après** :
- Récupère la quantité réelle ✅
- La stocke dans la BDD ✅
- Met à jour le statut ✅

---

### 🔹 Fichier 3 : `sell_orders.py`

**Modification de `_place_sell_order_for_pair()`** :

```python
def _place_sell_order_for_pair(self, pair) -> bool:
    """
    NOUVELLE LOGIQUE (mode spot limit):
    1. Prendre la quantité BTC de la BDD (déjà ajustée après frais d'achat)
    2. Vérifier que le solde BTC disponible est >= quantité BTC
    3. Placer l'ordre de vente avec cette quantité exacte
    
    Note: Pas besoin d'ajuster pour les frais maker de vente car :
    - On vend la quantité BTC qu'on possède réellement
    - Les frais maker seront déduits du montant USDC reçu, pas de la quantité BTC
    """
    
    quantity_btc = pair.quantity_btc  # ✅ Quantité RÉELLE (mise à jour par sync)
    available_btc = self.trading_engine.get_balance("BTC", available_only=True)
    
    # Vérifier avec tolérance de 0.1% pour les arrondis
    if available_btc < quantity_btc * 0.999:
        self.logger.warning(f"⚠️  Solde BTC insuffisant")
        return False
    
    # Placer l'ordre avec la quantité réelle
    order_result = self.trading_engine.execute_sell_order(sell_price, quantity_btc)
```

**Avant** :
- Utilisait `pair.quantity_btc` (quantité calculée) ❌
- Pas de vérification approfondie du solde ❌

**Après** :
- Utilise `pair.quantity_btc` (quantité RÉELLE mise à jour) ✅
- Vérifie le solde avec tolérance ✅
- Logs détaillés pour debug ✅

---

## 🔄 FLUX COMPLET CORRIGÉ

### Étape 1 : Placement ordre d'ACHAT (buy_orders.py)
```
1. Calculer quantité théorique : 0.001 BTC
2. Placer ordre d'achat sur Hyperliquid
3. Enregistrer dans BDD :
   - quantity_btc = 0.001 BTC (calculé)
   - status = 'Buy'
   - buy_order_id = "123456"
```

### Étape 2 : Synchronisation (sync_hyperliquid_orders.py)
```
5 minutes plus tard...

1. Vérifier statut ordre "123456" sur Hyperliquid
2. Statut = 'filled', quantité réelle = 0.00099996 BTC
3. ✅ NOUVEAU : Mettre à jour la BDD :
   - quantity_btc = 0.00099996 BTC (RÉEL)
   - status = 'Sell'
   - buy_filled_at = timestamp
```

### Étape 3 : Placement ordre de VENTE (sell_orders.py)
```
30 secondes plus tard...

1. Détecter paire avec status='Sell' et sans sell_order_id
2. Récupérer quantity_btc de la BDD = 0.00099996 BTC (RÉEL)
3. Vérifier solde BTC disponible >= 0.00099996 BTC
4. Si OK : placer ordre de vente pour 0.00099996 BTC
5. Enregistrer sell_order_id dans BDD
```

### Étape 4 : Synchronisation finale (sync_hyperliquid_orders.py)
```
5 minutes plus tard...

1. Vérifier statut ordre de vente
2. Statut = 'filled'
3. Mettre à jour BDD :
   - status = 'Complete'
   - completed_at = timestamp
4. Calculer profit (avec frais maker)
```

---

## 📦 INSTALLATION DES CORRECTIONS

### Option 1 : Remplacement complet (recommandé)

```bash
# 1. Sauvegarder les fichiers actuels
cp DB/database.py DB/database.py.backup
cp command/sync_hyperliquid_orders.py command/sync_hyperliquid_orders.py.backup
cp command/sell_orders.py command/sell_orders.py.backup

# 2. Remplacer par les versions corrigées
cp database_FIXED.py DB/database.py
cp sync_hyperliquid_orders_FIXED.py command/sync_hyperliquid_orders.py
cp sell_orders_FIXED.py command/sell_orders.py

# 3. Redémarrer le bot
python main.py
```

### Option 2 : Migration de la BDD existante

Si vous avez déjà des paires dans la BDD avec des quantités calculées, vous devez les mettre à jour :

```python
# Script de migration (à exécuter une fois)
from DB.database import Database
from config import load_config

config = load_config()
database = Database(config)

# Récupérer toutes les paires 'Sell' (achat rempli, vente pas placée)
sell_pairs = database.get_pairs_by_status('Sell')

print(f"🔄 Migration de {len(sell_pairs)} paires...")

for pair in sell_pairs:
    # Vous devez récupérer la quantité RÉELLE depuis Hyperliquid
    # ou utiliser une approximation (quantité - 0.04% de frais)
    
    estimated_real = pair.quantity_btc * 0.9996  # Approximation
    
    database.update_quantity_btc(pair.index, estimated_real)
    print(f"✅ Paire {pair.index} : {pair.quantity_btc:.8f} → {estimated_real:.8f} BTC")

print("✅ Migration terminée")
```

---

## 🧪 TESTS DE VALIDATION

### Test 1 : Vérifier la mise à jour de la quantité

```python
# Dans sync_hyperliquid_orders.py, ajouter des logs
self.logger.info(f"Avant mise à jour : {pair.quantity_btc:.8f} BTC")
self.database.update_quantity_btc(pair.index, total_filled)

# Recharger la paire depuis la BDD
pair_updated = self.database.get_pair_by_index(pair.index)
self.logger.info(f"Après mise à jour : {pair_updated.quantity_btc:.8f} BTC")
```

### Test 2 : Vérifier le placement de vente

```python
# Logs dans sell_orders.py
self.logger.info(f"Quantité BTC dans BDD : {pair.quantity_btc:.8f}")
self.logger.info(f"Solde BTC disponible : {available_btc:.8f}")
self.logger.info(f"Différence : {available_btc - pair.quantity_btc:.8f} BTC")
```

### Test 3 : Vérifier les frais maker

```python
# Calculer manuellement
buy_value = buy_price * quantity_btc
buy_fee = buy_value * 0.0004  # 0.04%
sell_value = sell_price * quantity_btc
sell_fee = sell_value * 0.0004  # 0.04%
total_fees = buy_fee + sell_fee

print(f"Frais maker total : {total_fees:.4f} USDC")
```

---

## 📊 VÉRIFICATION DANS LES LOGS

Après corrections, vous devriez voir dans les logs :

### Lors de l'achat rempli :
```
✅ Ordre d'achat 123456 REMPLI
   Quantité calculée: 0.00100000 BTC
   Quantité réelle: 0.00099996 BTC
   Différence (frais maker): 0.00000004 BTC
✅ Quantité BTC mise à jour pour paire 42
   Ancienne: 0.00100000 BTC
   Nouvelle: 0.00099996 BTC
   Différence: -0.00000004 BTC (frais maker)
✅ Paire 42 - Status mis à jour: Buy -> Sell
```

### Lors du placement de vente :
```
🔵 VÉRIFICATION PAIRE 42
   Quantité BTC requise: 0.00099996 BTC
   Solde BTC disponible: 0.00100123 BTC
✅ Solde suffisant (0.00100123 >= 0.00099996)

🔵 PLACEMENT ORDRE DE VENTE
   Paire: 42
   Prix vente: 101000.00$
   Quantité: 0.00099996 BTC (quantité RÉELLE)
   Valeur estimée: 100.99 USDC
   Note: Frais maker seront déduits du montant USDC reçu
✅ Ordre de vente placé sur Hyperliquid - ID: 789012
```

### Lors de la vente remplie :
```
✅ Ordre de vente 789012 REMPLI
   Quantité: 0.00099996 BTC
✅ Paire 42 - Status mis à jour: Sell -> Complete
💰 Profit brut: 1.00$
💰 Frais maker: 0.0808$ (0.04% × 2)
💰 Profit net: 0.92$ (+0.91%)
```

---

## ⚠️ POINTS D'ATTENTION

### 1. Ordres partiellement remplis
Si un ordre n'est pas complètement rempli, le code actuel attend qu'il le soit à 99% minimum :
```python
if total_filled >= pair.quantity_btc * 0.99:  # Tolérance 1%
```

### 2. Arrondis et précision
Les montants BTC ont 8 décimales. La vérification du solde utilise une tolérance de 0.1% :
```python
if available_btc < quantity_btc * 0.999:  # Marge de 0.1%
```

### 3. Délais de synchronisation
- Synchronisation : toutes les 5 minutes
- Vérification ventes : toutes les 30 secondes
- Délai entre paires : 2 secondes

### 4. Cache des échecs
Les paires en échec sont réessayées après 5 minutes :
```python
self.retry_delay = 300  # 5 minutes
```

---

## 🎯 RÉSUMÉ DES BÉNÉFICES

✅ **Quantités exactes** : Plus de différence entre BDD et réalité
✅ **Pas d'échecs** : Solde vérifié avant chaque vente
✅ **Frais corrects** : Maker fees uniquement (0.04% au lieu de 0.07%)
✅ **Traçabilité** : Logs détaillés à chaque étape
✅ **Fiabilité** : Vérifications avec tolérances pour les arrondis

---

## 📞 SUPPORT

Si vous rencontrez des problèmes :

1. Vérifier les logs dans `log/trading.log`
2. Vérifier les statuts dans la BDD : `python view_order_pairs.py`
3. Forcer une synchronisation via l'API web : `POST /api/control/force_sync`
4. Nettoyer le cache d'échecs : `POST /api/control/clear_failed_pairs`

---

## 📝 CHANGELOG

### Version FIXED (2025-01-XX)

**Ajouts** :
- `database.py` : Méthodes `update_quantity_btc()`, `update_pair_status()`, `get_pairs_by_status()`
- `sync_hyperliquid_orders.py` : Mise à jour automatique de la quantité réelle
- `sell_orders.py` : Vérification approfondie du solde avant placement

**Corrections** :
- Frais maker (0.04%) au lieu de taker (0.07%)
- Quantité BTC mise à jour après fill
- Vérification du solde avec tolérance

**Améliorations** :
- Logs détaillés pour debug
- Messages d'erreur plus explicites
- Documentation inline complète

---

**FIN DU DOCUMENT - VERSION 1.0**
