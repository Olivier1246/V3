"""
Module d'interface web pour le bot de trading
CORRECTIONS APPLIQUÉES:
- Ajout des routes API manquantes (/api/status, /api/balance, /api/market, etc.)
- Correction des appels à trading_engine avec les bons paramètres
- Amélioration de la gestion d'erreurs
- Synchronisation avec bot_controller.py
- Ajout de toutes les routes de contrôle nécessaires
"""

from flask import Flask, render_template, redirect, url_for, flash, jsonify, request
from datetime import datetime, timezone
from config import TradingConfig
from DB.database import Database
import threading
import os
import json


class WebInterface:
    """Interface web complète et sécurisée pour le bot de trading
    
    🔧 CORRECTIONS APPLIQUÉES:
    - Routes API complètes pour intégration temps réel
    - Gestion d'erreurs robuste sur toutes les pages
    - Fallbacks sécurisés pour toutes les données
    - Désactivation cache pour données fraîches
    - Routes de contrôle avec validation
    """
    
    def __init__(self, config: TradingConfig, database: Database, bot_controller):
        self.config = config
        self.database = database
        self.bot_controller = bot_controller
        
        # Créer les dossiers templates et static - CHEMIN ABSOLU
        import sys
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        template_dir = os.path.join(base_dir, 'templates')
        static_dir = os.path.join(base_dir, 'static')
        os.makedirs(template_dir, exist_ok=True)
        os.makedirs(static_dir, exist_ok=True)

        self.app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
        print(f"🔍 Template dir: {template_dir}")
        print(f"🔍 Static dir: {static_dir}")

        # Configuration Flask sécurisée
        import secrets
        self.app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
        self.app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
        self.app.config['TEMPLATES_AUTO_RELOAD'] = True
        
        # Désactiver le cache pour données fraîches
        @self.app.after_request
        def add_headers(response):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '-1'
            return response
        
        self.setup_routes()
        print("✅ Interface web corrigée initialisée")
    
    def get_common_data(self):
        """🔧 CORRECTION: Récupère les données communes de manière sécurisée"""
        # Données par défaut sécurisées
        data = {
            'status': {
                'is_running': False, 
                'total_profit': 0, 
                'total_trades': 0, 
                'successful_trades': 0, 
                'failed_trades': 0
            },
            'balances': {'total': 0, 'usdc': 0, 'btc': 0, 'price': 0},
            'market': {'type': 'UNKNOWN', 'trend': 'UNKNOWN', 'ma12': 0},
            'active_pairs': 0,
            'win_rate': 0,
            'now': datetime.now().strftime('%H:%M:%S'),
            'error_count': 0
        }
        
        error_count = 0
        
        # 1. Statut du bot avec gestion d'erreur
        try:
            if hasattr(self.bot_controller, 'is_running'):
                data['status']['is_running'] = self.bot_controller.is_running
                
                # Calcul win rate sécurisé depuis la BDD
                stats = self.database.get_statistics()
                if stats:
                    data['status']['total_trades'] = stats.get('completed_pairs', 0)
                    data['status']['successful_trades'] = stats.get('profitable_pairs', 0)
                    data['status']['total_profit'] = stats.get('total_gain', 0)
                    
                    if data['status']['total_trades'] > 0:
                        data['win_rate'] = round((data['status']['successful_trades'] / data['status']['total_trades']) * 100, 1)
        except Exception as e:
            print(f"⚠️  Erreur récupération statut bot: {e}")
            error_count += 1
        
        # 2. Balances avec gestion d'erreur
        try:
            if self.bot_controller and hasattr(self.bot_controller, 'trading_engine') and self.bot_controller.trading_engine:
                usdc = self.bot_controller.trading_engine.get_balance("USDC")
                btc_pos = self.bot_controller.trading_engine.get_position(self.config.symbol)
                btc = btc_pos.get('size', 0) if btc_pos else 0
                price = self.bot_controller.trading_engine.get_current_price(self.config.symbol)
                
                data['balances'] = {
                    'total': usdc + (btc * price),
                    'usdc': usdc,
                    'btc': btc,
                    'price': price
                }
        except Exception as e:
            print(f"⚠️  Erreur récupération balances: {e}")
            error_count += 1
        
        # 3. Analyse de marché avec gestion d'erreur
        try:
            analyses = self.database.get_market_analysis_history(1)
            if analyses and len(analyses) > 0:
                latest = analyses[0]
                data['market'] = {
                    'type': getattr(latest, 'market_type', 'UNKNOWN'),
                    'trend': getattr(latest, 'trend', 'UNKNOWN'),
                    'ma12': getattr(latest, 'ma12', 0) or 0
                }
        except Exception as e:
            print(f"⚠️  Erreur récupération analyse marché: {e}")
            error_count += 1
        
        # 4. Paires actives avec gestion d'erreur
        try:
            pairs = self.database.get_active_order_pairs()
            data['active_pairs'] = len(pairs) if pairs else 0
        except Exception as e:
            print(f"⚠️  Erreur récupération paires actives: {e}")
            error_count += 1
        
        data['error_count'] = error_count
        return data
    
    def setup_routes(self):
        """Configure les routes de l'application avec gestion d'erreurs"""
        
        # ==================== PAGES PRINCIPALES ====================
                    
        @self.app.route('/')
        @self.app.route('/index.html')
        def all_pairs():
            """Page complète de toutes les paires d'ordres - Style tableau ASCII"""
            try:
                # Récupérer toutes les paires (limite: 200)
                pairs = self.database.get_all_pairs(limit=200)
        
                # Calculer les statistiques
                total_pairs = len(pairs)
                buy_count = sum(1 for p in pairs if p.status == 'Buy')
                sell_count = sum(1 for p in pairs if p.status == 'Sell')
                complete_count = sum(1 for p in pairs if p.status == 'Complete')
        
                # Calculer les gains
                completed_pairs = [p for p in pairs if p.status == 'Complete' and p.gain_usdc is not None]
                total_gain = sum(p.gain_usdc for p in completed_pairs)
                profitable = sum(1 for p in completed_pairs if p.gain_usdc > 0)
                win_rate = (profitable / complete_count * 100) if complete_count > 0 else 0
        
                # Heure actuelle
                now = datetime.now().strftime('%H:%M:%S')
                
                # 🆕 Récupérer l'analyse de marché et le prix BTC (CÔTÉ SERVEUR)
                market_type = 'UNKNOWN'
                market_trend = 'UNKNOWN'
                btc_price_raw = 0
                btc_price_formatted = '-'
                
                try:
                    if self.bot_controller and hasattr(self.bot_controller, 'market_analyzer'):
                        analysis = self.bot_controller.market_analyzer.analyze_market()
                        market_type = analysis.get('market_type', 'UNKNOWN')
                        market_trend = analysis.get('trend', 'UNKNOWN')
                        btc_price_raw = analysis.get('current_price', 0)
                        
                        # ✅ FORMATAGE CÔTÉ SERVEUR avec séparateurs de milliers
                        if btc_price_raw > 0:
                            btc_price_formatted = f"${btc_price_raw:,.0f}"
                except Exception as e:
                    print(f"⚠️ Erreur récupération analyse marché: {e}")
        
                return render_template('index.html',
                    pairs=pairs,
                    total_pairs=total_pairs,
                    buy_count=buy_count,
                    sell_count=sell_count,
                    complete_count=complete_count,
                    total_gain=total_gain,
                    win_rate=win_rate,
                    now=now,
                    market_type=market_type,
                    market_trend=market_trend,
                    btc_price_formatted=btc_price_formatted
                )
            except Exception as e:
                print(f"❌ Erreur page index: {e}")
                import traceback
                traceback.print_exc()
                return self.error_response(f"Erreur page paires: {e}")

        # ==================== API ROUTES ====================
        
        @self.app.route('/api/status')
        def api_status():
            """🆕 API: Statut complet du bot"""
            try:
                status = self.bot_controller.get_status() if self.bot_controller else {}
                
                return jsonify({
                    'success': True,
                    'data': status,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/balance')
        def api_balance():
            """🆕 API: Balances et portefeuille"""
            try:
                if not (self.bot_controller and hasattr(self.bot_controller, 'trading_engine') and self.bot_controller.trading_engine):
                    return jsonify({
                        'success': False,
                        'error': 'Trading engine non disponible'
                    }), 503
                
                usdc = self.bot_controller.trading_engine.get_balance("USDC")
                btc_pos = self.bot_controller.trading_engine.get_position(self.config.symbol)
                btc = btc_pos.get('size', 0) if btc_pos else 0
                price = self.bot_controller.trading_engine.get_current_price(self.config.symbol)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'usdc': usdc,
                        'btc': btc,
                        'price': price,
                        'total': usdc + (btc * price)
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/market')
        def api_market():
            """🆕 API: Analyse du marché"""
            try:
                if not (self.bot_controller and hasattr(self.bot_controller, 'market_analyzer')):
                    return jsonify({
                        'success': False,
                        'error': 'Market analyzer non disponible'
                    }), 503
                
                analysis = self.bot_controller.market_analyzer.analyze_market()
                
                return jsonify({
                    'success': True,
                    'data': {
                        'market_type': analysis.get('market_type'),
                        'trend': analysis.get('trend'),
                        'current_price': analysis.get('current_price'),
                        'ma4': analysis.get('ma4'),
                        'ma8': analysis.get('ma8'),
                        'ma12': analysis.get('ma12'),
                        'range_limits': analysis.get('range_limits', {})
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/pending_orders')
        def api_pending_orders():
            """🆕 API: Ordres en attente"""
            try:
                if not self.bot_controller:
                    return jsonify({
                        'success': False,
                        'error': 'Bot controller non disponible'
                    }), 503
                
                pending = self.bot_controller.get_pending_orders()
                
                return jsonify({
                    'success': True,
                    'data': pending,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/completed_pairs')
        def api_completed_pairs():
            """🆕 API: Paires complétées"""
            try:
                limit = request.args.get('limit', 50, type=int)
                
                if not self.bot_controller:
                    return jsonify({
                        'success': False,
                        'error': 'Bot controller non disponible'
                    }), 503
                
                completed = self.bot_controller.get_completed_pairs(limit=limit)
                
                return jsonify({
                    'success': True,
                    'data': completed,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/statistics')
        def api_statistics():
            """🆕 API: Statistiques globales"""
            try:
                stats = self.database.get_statistics()
                
                return jsonify({
                    'success': True,
                    'data': stats or {},
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/index')
        def api_order_pairs():
            """API JSON pour récupérer toutes les paires d'ordres"""
            try:
                # Récupérer toutes les paires
                limit = request.args.get('limit', 200, type=int)
                pairs = self.database.get_all_pairs(limit=limit)
        
                # Convertir en dictionnaires
                pairs_data = []
                for pair in pairs:
                    pairs_data.append({
                        'index': pair.index,
                        'status': pair.status,
                        'qty_btc': pair.quantity_btc,
                        'qty_usdc': pair.quantity_usdc,
                        'buy_price': pair.buy_price_btc,
                        'sell_price': pair.sell_price_btc,
                        'gain_percent': pair.gain_percent,
                        'gain_usdc': pair.gain_usdc,
                        'buy_id': pair.buy_order_id,
                        'sell_id': pair.sell_order_id,
                        'offset': pair.offset_display,
                        'market': pair.market_type,
                        'uuid': pair.uuid,
                        'created_at': pair.created_at.isoformat() if pair.created_at else None,
                        'completed_at': pair.completed_at.isoformat() if pair.completed_at else None
                    })
        
                # Statistiques
                total_pairs = len(pairs)
                buy_count = sum(1 for p in pairs if p.status == 'Buy')
                sell_count = sum(1 for p in pairs if p.status == 'Sell')
                complete_count = sum(1 for p in pairs if p.status == 'Complete')
        
                completed_pairs = [p for p in pairs if p.status == 'Complete' and p.gain_usdc is not None]
                total_gain = sum(p.gain_usdc for p in completed_pairs)
                profitable = sum(1 for p in completed_pairs if p.gain_usdc > 0)
                win_rate = (profitable / complete_count * 100) if complete_count > 0 else 0
        
                return jsonify({
                    'success': True,
                    'data': {
                        'pairs': pairs_data,
                        'statistics': {
                            'total_pairs': total_pairs,
                            'buy_count': buy_count,
                            'sell_count': sell_count,
                            'complete_count': complete_count,
                            'total_gain': total_gain,
                            'win_rate': win_rate
                        }
                    },
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # ==================== CONTRÔLES (POST) ====================
        
        @self.app.route('/control/start', methods=['POST'])
        def control_start():
            """Démarre le bot avec gestion d'erreur"""
            try:
                if self.bot_controller:
                    if self.bot_controller.is_running:
                        flash('⚠️  Le bot est déjà en cours d\'exécution', 'warning')
                    else:
                        self.bot_controller.start()
                        flash('✅ Bot démarré avec succès', 'success')
                else:
                    flash('❌ Controller non disponible', 'error')
            except Exception as e:
                flash(f'❌ Erreur démarrage: {str(e)}', 'error')
                print(f"❌ Erreur control_start: {e}")
                import traceback
                traceback.print_exc()
            
            return redirect(url_for('all_pairs'))
        
        @self.app.route('/control/stop', methods=['POST'])
        def control_stop():
            """Arrête le bot avec gestion d'erreur"""
            try:
                if self.bot_controller:
                    if not self.bot_controller.is_running:
                        flash('⚠️  Le bot n\'est pas en cours d\'exécution', 'warning')
                    else:
                        self.bot_controller.stop()
                        flash('✅ Bot arrêté avec succès', 'success')
                else:
                    flash('❌ Controller non disponible', 'error')
            except Exception as e:
                flash(f'❌ Erreur arrêt: {str(e)}', 'error')
                print(f"❌ Erreur control_stop: {e}")
                import traceback
                traceback.print_exc()
            
            return redirect(url_for('all_pairs'))
        
        @self.app.route('/control/reload_config', methods=['POST'])
        @self.app.route('/api/control/reload_config', methods=['POST'])
        def control_reload_config():
            """🆕 Recharge la configuration depuis le fichier .env et propage aux modules
            
            Utilise bot_controller.reload_config() pour:
            - Recharger le .env
            - Propager aux modules (market_analyzer, trading_engine, buy_manager, sell_manager, etc.)
            - Détecter et afficher les changements
            - Envoyer notification Telegram si configuré
            
            Endpoints:
            - POST /control/reload_config : Interface web (avec flash messages)
            - POST /api/control/reload_config : API REST (retour JSON)
            """
            try:
                # Vérifier que bot_controller existe et a la méthode reload_config
                if not self.bot_controller:
                    message = '❌ Bot controller non disponible'
                    if request.path.startswith('/api/'):
                        return jsonify({
                            'success': False,
                            'message': message
                        }), 500
                    else:
                        flash(message, 'error')
                        return redirect(url_for('all_pairs'))
                
                if not hasattr(self.bot_controller, 'reload_config'):
                    # Fallback sur l'ancienne méthode si reload_config n'existe pas
                    if hasattr(self.config, 'reload'):
                        success = self.config.reload()
                        
                        if success:
                            message = '✅ Configuration rechargée (mode basique - sans propagation)'
                            print(message)
                            
                            if request.path.startswith('/api/'):
                                return jsonify({
                                    'success': True,
                                    'message': message,
                                    'warning': 'Configuration rechargée mais non propagée aux modules. Mise à jour de bot_controller recommandée.',
                                    'config': {
                                        'bull_market': {
                                            'buy_offset': self.config.bull_buy_offset,
                                            'sell_offset': self.config.bull_sell_offset,
                                            'percent': self.config.bull_percent
                                        },
                                        'last_reload': datetime.now(timezone.utc).isoformat()
                                    }
                                })
                            else:
                                flash(message, 'warning')
                                return redirect(url_for('all_pairs'))
                        else:
                            message = '❌ Erreur lors du rechargement'
                            if request.path.startswith('/api/'):
                                return jsonify({'success': False, 'message': message}), 500
                            else:
                                flash(message, 'error')
                                return redirect(url_for('all_pairs'))
                    else:
                        message = '❌ Rechargement non supporté - Mise à jour requise'
                        if request.path.startswith('/api/'):
                            return jsonify({'success': False, 'message': message}), 501
                        else:
                            flash(message, 'error')
                            return redirect(url_for('all_pairs'))
                
                # Appeler la méthode reload_config du bot_controller
                # Cette méthode recharge la config ET propage aux modules
                result = self.bot_controller.reload_config()
                
                # Si requête API, retourner le résultat JSON complet
                if request.path.startswith('/api/'):
                    status_code = 200 if result.get('success') else 500
                    return jsonify(result), status_code
                
                # Si interface web, afficher un message flash et rediriger
                if result.get('success'):
                    changes = result.get('changes', {})
                    if changes:
                        flash(f"✅ Configuration rechargée - {len(changes)} changement(s) détecté(s)", 'success')
                    else:
                        flash('✅ Configuration rechargée - Aucun changement détecté', 'info')
                else:
                    flash(f"❌ Échec: {result.get('message', 'Erreur inconnue')}", 'error')
                
                return redirect(url_for('all_pairs'))
                
            except Exception as e:
                error_msg = f'❌ Erreur rechargement: {str(e)}'
                print(f"❌ Erreur control_reload_config: {e}")
                import traceback
                traceback.print_exc()
                
                if request.path.startswith('/api/'):
                    return jsonify({
                        'success': False,
                        'message': error_msg
                    }), 500
                else:
                    flash(error_msg, 'error')
                    return redirect(url_for('all_pairs'))
        
        @self.app.route('/control/cancel_order/<order_id>', methods=['POST'])
        def control_cancel_order(order_id):
            """🔧 CORRECTION: Annule un ordre spécifique avec gestion d'erreur"""
            try:
                if (self.bot_controller and 
                    hasattr(self.bot_controller, 'trading_engine') and 
                    self.bot_controller.trading_engine):
                    
                    # Appel corrigé - pas besoin de passer symbol car déjà dans le trading_engine
                    success = self.bot_controller.trading_engine.cancel_order(
                        order_id=str(order_id),
                        operator_action=True
                    )
                    
                    if success:
                        flash(f'✅ Ordre {order_id} annulé', 'success')
                        # Re-synchroniser après annulation
                        if hasattr(self.bot_controller, 'sync_with_hyperliquid'):
                            self.bot_controller.sync_with_hyperliquid()
                    else:
                        flash(f'❌ Échec annulation ordre {order_id}', 'error')
                else:
                    flash('❌ Trading engine non disponible', 'error')
            except Exception as e:
                flash(f'❌ Erreur annulation: {str(e)}', 'error')
                print(f"❌ Erreur control_cancel_order: {e}")
                import traceback
                traceback.print_exc()
            
            return redirect(url_for('all_pairs'))
        
        @self.app.route('/control/cancel_all_orders', methods=['POST'])
        def control_cancel_all_orders():
            """🔧 CORRECTION: Annule tous les ordres avec gestion d'erreur"""
            try:
                if (self.bot_controller and 
                    hasattr(self.bot_controller, 'trading_engine') and 
                    self.bot_controller.trading_engine):
                    
                    # Appel corrigé - pas besoin de passer symbol
                    success = self.bot_controller.trading_engine.cancel_all_orders(
                        operator_action=True
                    )
                    
                    if success:
                        flash('✅ Tous les ordres annulés', 'success')
                        # Re-synchroniser après annulation
                        if hasattr(self.bot_controller, 'sync_with_hyperliquid'):
                            self.bot_controller.sync_with_hyperliquid()
                    else:
                        flash('❌ Aucun ordre à annuler ou erreur', 'warning')
                else:
                    flash('❌ Trading engine non disponible', 'error')
            except Exception as e:
                flash(f'❌ Erreur annulation massive: {str(e)}', 'error')
                print(f"❌ Erreur control_cancel_all_orders: {e}")
                import traceback
                traceback.print_exc()
            
            return redirect(url_for('all_pairs'))
        
        @self.app.route('/control/sync', methods=['POST'])
        def control_sync():
            """🆕 Force une synchronisation manuelle"""
            try:
                if self.bot_controller and hasattr(self.bot_controller, 'sync_with_hyperliquid'):
                    self.bot_controller.sync_with_hyperliquid()
                    flash('✅ Synchronisation effectuée', 'success')
                else:
                    flash('❌ Bot controller non disponible', 'error')
            except Exception as e:
                flash(f'❌ Erreur synchronisation: {str(e)}', 'error')
                print(f"❌ Erreur control_sync: {e}")
                import traceback
                traceback.print_exc()
            
            return redirect(url_for('all_pairs'))
    
    def error_response(self, message, title="Erreur"):
        """🆕 Retourne une page d'erreur informative et stylée"""
        return f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title} - HL-Spot Bot</title>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 50px auto;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: #f44336;
                    color: white;
                    padding: 20px;
                    text-align: center;
                }}
                .content {{
                    padding: 30px;
                }}
                .error-icon {{
                    font-size: 48px;
                    margin-bottom: 20px;
                }}
                .back-btn {{
                    display: inline-block;
                    margin-top: 20px;
                    padding: 12px 24px;
                    background: #1976d2;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    transition: background 0.3s;
                }}
                .back-btn:hover {{
                    background: #1565c0;
                }}
                .timestamp {{
                    color: #666;
                    font-size: 0.9em;
                    margin-top: 15px;
                }}
                .tips {{
                    background: #e3f2fd;
                    border-left: 4px solid #2196f3;
                    padding: 15px;
                    margin-top: 20px;
                }}
                .tips h4 {{
                    margin-top: 0;
                    color: #1976d2;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="error-icon">⚠️</div>
                    <h2>{title}</h2>
                </div>
                <div class="content">
                    <p><strong>Message d'erreur :</strong></p>
                    <p style="background: #ffebee; padding: 15px; border-radius: 5px; border-left: 4px solid #f44336;">
                        {message}
                    </p>
                    
                    <div class="tips">
                        <h4>💡 Solutions possibles :</h4>
                        <ul>
                            <li>Vérifiez que le bot est démarré</li>
                            <li>Contrôlez votre connexion internet</li>
                            <li>Consultez les logs pour plus de détails</li>
                            <li>Essayez de recharger la page</li>
                            <li>Redémarrez le bot si nécessaire</li>
                        </ul>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="/" class="back-btn">← Retour au Dashboard</a>
                        <a href="/api/status" class="back-btn" style="background: #4caf50;">📊 API Status</a>
                    </div>
                    
                    <div class="timestamp">
                        Erreur survenue le {datetime.now().strftime('%Y-%m-%d à %H:%M:%S')}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def run(self, host='0.0.0.0', port=None):
        """Lance le serveur web avec gestion d'erreur"""
        if port is None:
            port = getattr(self.config, 'port', 60000)
        
        try:
            # Lance dans un thread séparé
            thread = threading.Thread(
                target=lambda: self.app.run(
                    host=host, 
                    port=port, 
                    debug=False, 
                    use_reloader=False,
                    threaded=True
                )
            )
            thread.daemon = True
            thread.start()
            
            print(f"\n{'='*60}")
            print(f"✅ Interface web lancée sur http://{host}:{port}")
            print(f"{'='*60}")
            print(f"   📊 Dashboard: http://localhost:{port}/")
            print(f"   🔌 API Status: http://localhost:{port}/api/status")
            print(f"   💰 Balance: http://localhost:{port}/api/balance")
            print(f"   📈 Market: http://localhost:{port}/api/market")
            print(f"   📋 Orders: http://localhost:{port}/api/pending_orders")
            print(f"   📊 Stats: http://localhost:{port}/api/statistics")
            print(f"   🔧 Version: Interface web corrigée v3.0")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"❌ Erreur lancement interface web: {e}")
            import traceback
            traceback.print_exc()
            raise
