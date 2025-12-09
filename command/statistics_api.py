"""
Module d'API pour les statistiques du bot de trading
À intégrer dans web_interface.py
"""

from flask import jsonify, request
from datetime import datetime, timedelta, timezone
from typing import Dict, List
import sqlite3


class StatisticsAPI:
    """Gestionnaire des statistiques pour l'API web"""
    
    def __init__(self, database):
        self.database = database
    
    def get_statistics(self, period: str = "7") -> Dict:
        """Récupère les statistiques pour une période donnée
        
        Args:
            period: Période en jours ("7", "30", "90", "all")
            
        Returns:
            Dict avec toutes les statistiques
        """
        
        # Calculer la date de début selon la période
        if period == "all":
            start_date = None
        else:
            try:
                days = int(period)
                start_date = datetime.now(timezone.utc) - timedelta(days=days)
            except ValueError:
                days = 7
                start_date = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Récupérer les trades complétés
        completed_trades = self._get_completed_trades(start_date)
        
        if not completed_trades:
            return self._empty_statistics()
        
        # Calculer les statistiques principales
        main_stats = self._calculate_main_stats(completed_trades)
        
        # Statistiques par marché
        market_breakdown = self._calculate_market_breakdown(completed_trades)
        
        # Profit cumulé dans le temps
        cumulative_profit = self._calculate_cumulative_profit(completed_trades)
        
        # Distribution des profits
        distribution = self._calculate_distribution(completed_trades)
        
        # Trades récents
        recent_trades = self._format_recent_trades(completed_trades[:20])
        
        # Indicateurs de performance
        performance = self._calculate_performance_indicators(completed_trades)
        
        return {
            'success': True,
            'stats': main_stats,
            'market_breakdown': market_breakdown,
            'cumulative_profit': cumulative_profit,
            'distribution': distribution,
            'recent_trades': recent_trades,
            'performance': performance,
            'period': period
        }
    
    def _get_completed_trades(self, start_date=None) -> List[Dict]:
        """Récupère les trades complétés depuis la BDD"""
        try:
            conn = sqlite3.connect(self.database.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    *,
                    (sell_price_btc * quantity_btc) - (buy_price_btc * quantity_btc) as profit_usdc,
                    ((sell_price_btc - buy_price_btc) / buy_price_btc * 100) as profit_percent
                FROM order_pairs
                WHERE status = 'Complete'
            """
            
            if start_date:
                query += " AND completed_at >= ?"
                cursor.execute(query + " ORDER BY completed_at DESC", (start_date.isoformat(),))
            else:
                cursor.execute(query + " ORDER BY completed_at DESC")
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convertir en liste de dictionnaires
            trades = []
            for row in rows:
                trade = dict(row)
                trades.append(trade)
            
            return trades
            
        except Exception as e:
            print(f"Erreur récupération trades: {e}")
            return []
    
    def _calculate_main_stats(self, trades: List[Dict]) -> Dict:
        """Calcule les statistiques principales"""
        if not trades:
            return {
                'total_profit': 0,
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'best_trade': 0,
                'worst_trade': 0
            }
        
        profits = [t['profit_usdc'] for t in trades]
        winning_trades = [p for p in profits if p > 0]
        
        total_profit = sum(profits)
        total_trades = len(trades)
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        best_trade = max(profits) if profits else 0
        worst_trade = min(profits) if profits else 0
        
        return {
            'total_profit': round(total_profit, 2),
            'total_trades': total_trades,
            'win_rate': round(win_rate, 2),
            'avg_profit': round(avg_profit, 2),
            'best_trade': round(best_trade, 2),
            'worst_trade': round(worst_trade, 2)
        }
    
    def _calculate_market_breakdown(self, trades: List[Dict]) -> Dict:
        """Calcule les statistiques par type de marché"""
        breakdown = {
            'bull': {'trades': 0, 'profit': 0, 'wins': 0},
            'bear': {'trades': 0, 'profit': 0, 'wins': 0},
            'range': {'trades': 0, 'profit': 0, 'wins': 0}
        }
        
        for trade in trades:
            market = trade.get('market_type', 'RANGE').lower()
            if market not in breakdown:
                market = 'range'
            
            breakdown[market]['trades'] += 1
            breakdown[market]['profit'] += trade['profit_usdc']
            if trade['profit_usdc'] > 0:
                breakdown[market]['wins'] += 1
        
        # Calculer les taux de réussite et profits moyens
        for market in breakdown:
            data = breakdown[market]
            trades_count = data['trades']
            
            if trades_count > 0:
                data['win_rate'] = round((data['wins'] / trades_count) * 100, 2)
                data['avg_profit'] = round(data['profit'] / trades_count, 2)
            else:
                data['win_rate'] = 0
                data['avg_profit'] = 0
            
            data['profit'] = round(data['profit'], 2)
            del data['wins']  # Retirer le compteur intermédiaire
        
        return breakdown
    
    def _calculate_cumulative_profit(self, trades: List[Dict]) -> Dict:
        """Calcule le profit cumulé dans le temps"""
        if not trades:
            return {'dates': [], 'values': []}
        
        # Trier par date
        sorted_trades = sorted(trades, key=lambda t: t['completed_at'])
        
        dates = []
        values = []
        cumulative = 0
        
        for trade in sorted_trades:
            completed_at = trade['completed_at']
            if isinstance(completed_at, str):
                date_obj = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
            else:
                date_obj = completed_at
            
            dates.append(date_obj.strftime('%d/%m'))
            cumulative += trade['profit_usdc']
            values.append(round(cumulative, 2))
        
        # Limiter à 50 points maximum pour la lisibilité
        if len(dates) > 50:
            step = len(dates) // 50
            dates = dates[::step]
            values = values[::step]
        
        return {
            'dates': dates,
            'values': values
        }
    
    def _calculate_distribution(self, trades: List[Dict]) -> Dict:
        """Calcule la distribution des profits/pertes"""
        if not trades:
            return {'labels': [], 'values': []}
        
        # Prendre les 30 derniers trades
        recent = trades[:30]
        
        labels = [f"T{i+1}" for i in range(len(recent))]
        values = [round(t['profit_usdc'], 2) for t in recent]
        
        return {
            'labels': labels,
            'values': values
        }
    
    def _format_recent_trades(self, trades: List[Dict]) -> List[Dict]:
        """Formate les trades récents pour l'affichage"""
        formatted = []
        
        for trade in trades:
            formatted.append({
                'index': trade['index'],
                'completed_at': trade['completed_at'],
                'market_type': trade.get('market_type', 'UNKNOWN'),
                'buy_price': round(trade['buy_price_btc'], 2),
                'sell_price': round(trade['sell_price_btc'], 2),
                'quantity_btc': round(trade['quantity_btc'], 8),
                'profit': round(trade['profit_usdc'], 2),
                'profit_percent': round(trade['profit_percent'], 2)
            })
        
        return formatted
    
    def _calculate_performance_indicators(self, trades: List[Dict]) -> Dict:
        """Calcule les indicateurs de performance avancés"""
        if not trades:
            return {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'profit_factor': 0,
                'avg_holding_time': 0
            }
        
        profits = [t['profit_usdc'] for t in trades]
        
        # Sharpe Ratio (simplifié)
        avg_profit = sum(profits) / len(profits)
        std_dev = (sum((p - avg_profit) ** 2 for p in profits) / len(profits)) ** 0.5
        sharpe_ratio = (avg_profit / std_dev) if std_dev > 0 else 0
        
        # Max Drawdown
        cumulative = 0
        peak = 0
        max_dd = 0
        for profit in profits:
            cumulative += profit
            if cumulative > peak:
                peak = cumulative
            dd = ((peak - cumulative) / peak * 100) if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        
        # Profit Factor
        gross_profit = sum(p for p in profits if p > 0)
        gross_loss = abs(sum(p for p in profits if p < 0))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
        
        # Temps de détention moyen (en heures)
        holding_times = []
        for trade in trades:
            if trade.get('created_at') and trade.get('completed_at'):
                try:
                    created = datetime.fromisoformat(trade['created_at'].replace('Z', '+00:00'))
                    completed = datetime.fromisoformat(trade['completed_at'].replace('Z', '+00:00'))
                    holding_time = (completed - created).total_seconds() / 3600
                    holding_times.append(holding_time)
                except:
                    pass
        
        avg_holding_time = sum(holding_times) / len(holding_times) if holding_times else 0
        
        return {
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_dd, 2),
            'profit_factor': round(profit_factor, 2),
            'avg_holding_time': round(avg_holding_time, 1)
        }
    
    def _empty_statistics(self) -> Dict:
        """Retourne des statistiques vides"""
        return {
            'success': True,
            'stats': {
                'total_profit': 0,
                'total_trades': 0,
                'win_rate': 0,
                'avg_profit': 0,
                'best_trade': 0,
                'worst_trade': 0
            },
            'market_breakdown': {
                'bull': {'trades': 0, 'profit': 0, 'win_rate': 0, 'avg_profit': 0},
                'bear': {'trades': 0, 'profit': 0, 'win_rate': 0, 'avg_profit': 0},
                'range': {'trades': 0, 'profit': 0, 'win_rate': 0, 'avg_profit': 0}
            },
            'cumulative_profit': {'dates': [], 'values': []},
            'distribution': {'labels': [], 'values': []},
            'recent_trades': [],
            'performance': {
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'profit_factor': 0,
                'avg_holding_time': 0
            }
        }


# ========================================
# Code à ajouter dans web_interface.py
# ========================================

"""
Ajouter cette route dans la classe WebInterface ou dans les routes Flask:

from command.statistics_api import StatisticsAPI

# Dans __init__ ou setup
self.stats_api = StatisticsAPI(self.database)

# Route API
@app.route('/api/statistics', methods=['GET'])
def api_statistics():
    '''Endpoint API pour les statistiques'''
    period = request.args.get('period', '7')
    
    try:
        stats = self.stats_api.get_statistics(period)
        return jsonify(stats)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
"""
