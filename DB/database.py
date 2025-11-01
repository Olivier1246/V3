"""
Module de gestion de la base de données
Structure simplifiée selon les nouvelles spécifications
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timezone
from config import TradingConfig
import threading
import os
import uuid as uuid_lib

Base = declarative_base()


class OrderPair(Base):
    """Modèle pour les paires d'ordres achat/vente - NOUVELLE STRUCTURE"""
    __tablename__ = 'order_pairs'
    
    # Index auto-incrémenté à chaque ordre d'achat
    index = Column(Integer, primary_key=True, autoincrement=True)
    
    # Status: Buy / Sell / Complete
    status = Column(String, default='Buy', nullable=False)
    
    # Quantité USDC = solde USDC * (*_PERCENT)
    quantity_usdc = Column(Float, nullable=False)
    
    # Quantité BTC = "size" sur hyperliquid
    quantity_btc = Column(Float, nullable=False)
    
    # Buy price BTC = prix BTC spot + (*_BUY_OFFSET)
    buy_price_btc = Column(Float, nullable=False)
    
    # Sell price BTC = prix BTC spot + (*_SELL_OFFSET)
    sell_price_btc = Column(Float, nullable=False)
    
    # Gain % = calculer le gain en %
    gain_percent = Column(Float, nullable=True)
    
    # Gain $ = calculer le gain en $ moins les frais taker
    gain_usdc = Column(Float, nullable=True)
    
    # Buy Order ID = récupéré sur Hyperliquid
    buy_order_id = Column(String, nullable=True)
    
    # Sell Order ID = récupéré sur Hyperliquid
    sell_order_id = Column(String, nullable=True)
    
    # Offset = afficher sous la forme *_BUY_OFFSET/*_SELL_OFFSET
    offset_display = Column(String, nullable=True)
    
    # Informations complémentaires
    market_type = Column(String, nullable=True)  # BULL, BEAR, RANGE
    symbol = Column(String, default='BTC')
    uuid = Column(String, unique=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    buy_filled_at = Column(DateTime, nullable=True)
    sell_placed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)


class Database:
    """Gestionnaire de base de données simplifié"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        
        # Construire le chemin de la base de données
        # S'assurer qu'il est toujours dans le dossier DB
        db_file = getattr(config, 'db_file', 'DB/trading_history.db')
        
        # Si le chemin ne commence pas par DB/, le forcer
        if not db_file.startswith('DB/') and not db_file.startswith('DB\\'):
            # Extraire juste le nom du fichier
            db_filename = os.path.basename(db_file)
            db_file = os.path.join('DB', db_filename)
        
        # Convertir en chemin absolu pour éviter toute ambiguïté
        self.db_file = os.path.abspath(db_file)
        
        self._engine = None
        self._session_factory = None
        self._lock = threading.RLock()
        self._initialized = False
        
        print(f"🗄️  Initialisation base de données: {self.db_file}")
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialise la base avec configuration SQLite optimisée"""
        try:
            # Extraire et créer le répertoire de la base de données
            db_dir = os.path.dirname(self.db_file)
            
            if db_dir:
                print(f"📁 Répertoire base de données: {db_dir}")
                
                if not os.path.exists(db_dir):
                    print(f"📁 Création du répertoire: {db_dir}")
                    os.makedirs(db_dir, exist_ok=True)
                else:
                    print(f"✅ Répertoire existant: {db_dir}")
            
            # Vérifier que le fichier sera bien dans le dossier DB
            if 'DB' not in self.db_file:
                print(f"⚠️  ATTENTION: Le chemin de la base ne contient pas 'DB': {self.db_file}")
            
            connection_string = f"sqlite:///{self.db_file}"
            print(f"🔗 Connexion SQLite: {connection_string}")
            
            self._engine = create_engine(
                connection_string,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args={
                    'check_same_thread': False,
                    'timeout': 30,
                    'isolation_level': None
                },
                poolclass=StaticPool
            )
            
            self._session_factory = sessionmaker(
                bind=self._engine,
                autoflush=True,
                autocommit=False,
                expire_on_commit=False
            )
            
            Base.metadata.create_all(self._engine)
            self._optimize_sqlite()
            
            self._initialized = True
            print("✅ Base de données initialisée avec succès")
            
            # Vérifier que le fichier existe bien là où on l'attend
            if os.path.exists(self.db_file):
                print(f"✅ Fichier base de données créé: {self.db_file}")
            else:
                print(f"⚠️  Fichier base de données non trouvé: {self.db_file}")
            
        except Exception as e:
            print(f"❌ Erreur initialisation base de données: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _optimize_sqlite(self):
        """Configure SQLite pour des performances optimales"""
        try:
            with self._engine.connect() as conn:
                optimizations = [
                    "PRAGMA journal_mode=WAL",
                    "PRAGMA synchronous=NORMAL",
                    "PRAGMA cache_size=10000",
                    "PRAGMA temp_store=MEMORY",
                    "PRAGMA busy_timeout=30000",
                ]
                
                for pragma in optimizations:
                    try:
                        conn.execute(text(pragma))
                        conn.commit()
                    except Exception as e:
                        print(f"⚠️  Warning pragma {pragma}: {e}")
                
                print("✅ Optimisations SQLite appliquées")
                
        except Exception as e:
            print(f"⚠️  Erreur optimisation SQLite: {e}")
    
    def get_session(self):
        """Obtient une session de base de données"""
        if not self._initialized:
            self._initialize_database()
        return self._session_factory()
    
    def safe_execute(self, func, *args, **kwargs):
        """Exécute une fonction avec gestion d'erreur et retry"""
        max_retries = 3
        for attempt in range(max_retries):
            session = None
            try:
                with self._lock:
                    session = self.get_session()
                    result = func(session, *args, **kwargs)
                    session.commit()
                    return result
            except Exception as e:
                if session:
                    session.rollback()
                if attempt < max_retries - 1:
                    print(f"⚠️  Retry DB (tentative {attempt + 1}): {e}")
                else:
                    print(f"❌ Erreur DB après {max_retries} tentatives: {e}")
                    raise
            finally:
                if session:
                    session.close()
    
    def create_buy_order_pair(self, data: dict) -> int:
        """Crée une nouvelle paire d'ordres avec un ordre d'achat
        
        Args:
            data: Dictionnaire contenant:
                - quantity_usdc: Montant en USDC
                - quantity_btc: Quantité en BTC
                - buy_price_btc: Prix d'achat
                - sell_price_btc: Prix de vente cible
                - buy_order_id: ID de l'ordre sur Hyperliquid
                - market_type: Type de marché (BULL, BEAR, RANGE)
                - offset_display: Affichage des offsets
        
        Returns:
            Index de la paire créée
        """
        def _create(session, order_data):
            # Générer UUID
            order_uuid = str(uuid_lib.uuid4())
            
            # Créer la paire
            pair = OrderPair(
                status='Buy',
                quantity_usdc=order_data['quantity_usdc'],
                quantity_btc=order_data['quantity_btc'],
                buy_price_btc=order_data['buy_price_btc'],
                sell_price_btc=order_data['sell_price_btc'],
                buy_order_id=order_data.get('buy_order_id'),
                market_type=order_data.get('market_type'),
                offset_display=order_data.get('offset_display'),
                uuid=order_uuid,
                symbol=order_data.get('symbol', 'BTC')
            )
            
            session.add(pair)
            session.flush()
            
            print(f"✅ Nouvelle paire créée - Index: {pair.index}, UUID: {order_uuid[:8]}")
            return pair.index
        
        try:
            return self.safe_execute(_create, data)
        except Exception as e:
            print(f"❌ Erreur création paire: {e}")
            raise
    
    def update_buy_filled(self, index: int) -> bool:
        """Marque un ordre d'achat comme rempli"""
        def _update(session, pair_index):
            pair = session.query(OrderPair).filter_by(index=pair_index).first()
            if pair:
                pair.buy_filled_at = datetime.now(timezone.utc)
                pair.status = 'Sell'  # Prêt pour la vente
                session.flush()
                print(f"✅ Paire {pair_index} - Achat rempli, status -> Sell")
                return True
            return False
        
        try:
            return self.safe_execute(_update, index)
        except Exception as e:
            print(f"❌ Erreur update buy_filled: {e}")
            return False
    
    def update_sell_order(self, index: int, sell_order_id: str) -> bool:
        """Met à jour une paire avec l'ID de l'ordre de vente"""
        def _update(session, pair_index, order_id):
            pair = session.query(OrderPair).filter_by(index=pair_index).first()
            if pair:
                pair.sell_order_id = order_id
                pair.sell_placed_at = datetime.now(timezone.utc)
                session.flush()
                print(f"✅ Paire {pair_index} - Ordre de vente placé: {order_id}")
                return True
            return False
        
        try:
            return self.safe_execute(_update, index, sell_order_id)
        except Exception as e:
            print(f"❌ Erreur update sell_order: {e}")
            return False

    def update_sell_order_id(self, pair_index: int, sell_order_id: str):
        """
        Met à jour l'ID de l'ordre de vente pour une paire d'ordres
        
        Args:
            pair_index: Index de la paire dans la base de données
            sell_order_id: ID de l'ordre de vente sur Hyperliquid
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE order_pairs 
                    SET sell_order_id = ?
                    WHERE id = ?
                """, (sell_order_id, pair_index))
                
                conn.commit()
                
                if cursor.rowcount == 0:
                    raise ValueError(f"Aucune paire trouvée avec l'index {pair_index}")
                    
                return True
                
        except Exception as e:
            raise Exception(f"Erreur lors de la mise à jour du sell_order_id: {e}")

    def complete_order_pair(self, index: int, sell_price_actual: float = None) -> bool:
        """Marque une paire comme complétée et calcule les gains
        
        Args:
            index: Index de la paire
            sell_price_actual: Prix de vente réel (optionnel, sinon utilise sell_price_btc)
        """
        def _complete(session, pair_index, actual_price):
            pair = session.query(OrderPair).filter_by(index=pair_index).first()
            if not pair:
                return False
            
            # Prix de vente effectif
            sell_price = actual_price if actual_price else pair.sell_price_btc
            
            # Calcul du gain brut
            buy_cost = pair.buy_price_btc * pair.quantity_btc
            sell_revenue = sell_price * pair.quantity_btc
            gross_profit = sell_revenue - buy_cost
            
            # Frais taker (récupérés depuis config)
            taker_fee_percent = self.config.taker_fee / 100
            buy_fee = buy_cost * taker_fee_percent
            sell_fee = sell_revenue * taker_fee_percent
            total_fees = buy_fee + sell_fee
            
            # Profit net
            net_profit = gross_profit - total_fees
            profit_percent = (net_profit / buy_cost) * 100 if buy_cost > 0 else 0
            
            # Mettre à jour la paire
            pair.gain_usdc = net_profit
            pair.gain_percent = profit_percent
            pair.status = 'Complete'
            pair.completed_at = datetime.now(timezone.utc)
            
            session.flush()
            
            print(f"✅ Paire {pair_index} complétée")
            print(f"   Gain: {net_profit:.2f}$ ({profit_percent:.2f}%)")
            print(f"   Frais: {total_fees:.4f}$")
            
            return True
        
        try:
            return self.safe_execute(_complete, index, sell_price_actual)
        except Exception as e:
            print(f"❌ Erreur completion paire: {e}")
            return False
    
    def get_pending_buy_orders(self):
        """Récupère les paires en attente de remplissage d'achat (status='Buy')"""
        def _get(session):
            return session.query(OrderPair).filter_by(status='Buy').all()
        
        try:
            return self.safe_execute(_get)
        except Exception as e:
            print(f"❌ Erreur récupération pending buy: {e}")
            return []
    
    def get_pending_sell_orders(self):
        """Récupère les paires prêtes pour la vente (status='Sell')"""
        def _get(session):
            return session.query(OrderPair).filter_by(status='Sell').all()
        
        try:
            return self.safe_execute(_get)
        except Exception as e:
            print(f"❌ Erreur récupération pending sell: {e}")
            return []
    
    def get_all_pairs(self, limit: int = 100):
        """Récupère toutes les paires"""
        def _get(session, pair_limit):
            return session.query(OrderPair).order_by(OrderPair.index.desc()).limit(pair_limit).all()
        
        try:
            return self.safe_execute(_get, limit)
        except Exception as e:
            print(f"❌ Erreur récupération paires: {e}")
            return []
    
    def get_pair_by_index(self, index: int):
        """Récupère une paire par son index"""
        def _get(session, pair_index):
            return session.query(OrderPair).filter_by(index=pair_index).first()
        
        try:
            return self.safe_execute(_get, index)
        except Exception as e:
            print(f"❌ Erreur récupération paire {index}: {e}")
            return None
    
    def get_pair_by_buy_order_id(self, buy_order_id: str):
        """Récupère une paire par l'ID de l'ordre d'achat"""
        def _get(session, order_id):
            return session.query(OrderPair).filter_by(buy_order_id=order_id).first()
        
        try:
            return self.safe_execute(_get, buy_order_id)
        except Exception as e:
            print(f"❌ Erreur récupération paire by buy_order_id: {e}")
            return None
    
    def get_statistics(self):
        """Retourne des statistiques sur les paires"""
        def _get_stats(session):
            stats = {}
            
            # Total paires
            stats['total_pairs'] = session.query(OrderPair).count()
            
            # Paires par status
            stats['buy_pending'] = session.query(OrderPair).filter_by(status='Buy').count()
            stats['sell_pending'] = session.query(OrderPair).filter_by(status='Sell').count()
            stats['completed'] = session.query(OrderPair).filter_by(status='Complete').count()
            
            # Gains totaux
            completed_pairs = session.query(OrderPair).filter_by(status='Complete').all()
            total_gain = sum(p.gain_usdc for p in completed_pairs if p.gain_usdc)
            profitable = len([p for p in completed_pairs if p.gain_usdc and p.gain_usdc > 0])
            
            stats['total_gain_usdc'] = total_gain
            stats['profitable_trades'] = profitable
            stats['losing_trades'] = stats['completed'] - profitable
            
            if stats['completed'] > 0:
                stats['win_rate'] = (profitable / stats['completed']) * 100
                stats['average_gain'] = total_gain / stats['completed']
            else:
                stats['win_rate'] = 0
                stats['average_gain'] = 0
            
            return stats
        
        try:
            return self.safe_execute(_get_stats)
        except Exception as e:
            print(f"❌ Erreur récupération statistiques: {e}")
            return {}
    
    def get_active_order_pairs(self):
        """Récupère toutes les paires actives (Buy et Sell)
        Alias pour la compatibilité avec web_interface.py
        """
        def _get(session):
            return session.query(OrderPair).filter(
                OrderPair.status.in_(['Buy', 'Sell'])
            ).all()
        
        try:
            return self.safe_execute(_get)
        except Exception as e:
            print(f"❌ Erreur récupération paires actives: {e}")
            return []
    
    def get_market_analysis_history(self, limit: int = 100):
        """Récupère l'historique des analyses de marché
        
        Note: Cette méthode retourne une liste vide car l'architecture actuelle
        ne stocke pas l'historique des analyses de marché dans la base de données.
        Les analyses sont effectuées en temps réel par MarketAnalyzer.
        
        Pour l'interface web, utilisez plutôt:
        - market_analyzer.analyze_market() pour les données temps réel
        - Ou ajoutez une table MarketAnalysis si vous souhaitez persister l'historique
        """
        # Retourne une liste vide pour éviter les erreurs
        # L'interface web doit utiliser le MarketAnalyzer directement
        return []
    
    def get_recent_trades(self, limit: int = 20):
        """Récupère les trades récents (paires complétées)
        Alias pour get_all_pairs avec filtre sur status='Complete'
        """
        def _get(session, trade_limit):
            return session.query(OrderPair).filter_by(
                status='Complete'
            ).order_by(
                OrderPair.completed_at.desc()
            ).limit(trade_limit).all()
        
        try:
            return self.safe_execute(_get, limit)
        except Exception as e:
            print(f"❌ Erreur récupération trades récents: {e}")
            return []
    
    def __del__(self):
        """Nettoyage propre lors de la destruction"""
        try:
            if hasattr(self, '_engine') and self._engine:
                self._engine.dispose()
                print("🔌 Connexions base de données fermées proprement")
        except:
            pass
