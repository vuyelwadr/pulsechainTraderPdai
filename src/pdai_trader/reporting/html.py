"""HTML report generator for the pDAI trading toolkit."""
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import logging
import os
from bokeh.plotting import figure, save, output_file
from bokeh.models import HoverTool, CrosshairTool, ColumnDataSource
from bokeh.layouts import column, row
from bokeh.embed import file_html
from bokeh.resources import CDN

from pdai_trader.config import Settings

logger = logging.getLogger(__name__)

class HTMLGenerator:
    """Generates HTML reports for trading results"""
    
    def __init__(self):
        self.config = Settings
        os.makedirs(self.config.HTML_DIR, exist_ok=True)
        
    def generate_backtest_report(self, results: Dict, strategy_name: str = None) -> str:
        """Generate comprehensive HTML backtest report"""
        
        strategy_name = strategy_name or results.get('strategy_name', 'Unknown Strategy')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(self.config.HTML_DIR, f"backtest_{strategy_name}_{timestamp}.html")
        
        # Create the HTML content
        html_content = self._create_backtest_html(results, strategy_name)
        
        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Backtest report generated: {filename}")
        return filename
    
    def generate_live_report(self, portfolio_data: List[Dict], strategy_data: Dict) -> str:
        """Generate live trading HTML report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(self.config.HTML_DIR, f"live_trading_{timestamp}.html")
        
        html_content = self._create_live_html(portfolio_data, strategy_data)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Live trading report generated: {filename}")
        return filename
    
    def _create_backtest_html(self, results: Dict, strategy_name: str) -> str:
        """Create HTML content for backtest results"""
        
        # Extract key metrics
        total_return = results.get('total_return_pct', 0)
        win_rate = results.get('win_rate_pct', 0)
        max_drawdown = results.get('max_drawdown_pct', 0)
        sharpe_ratio = results.get('sharpe_ratio', 0)
        total_trades = results.get('total_trades', 0)
        
        # Generate charts if we have portfolio history
        charts_html = ""
        if results.get('portfolio_history'):
            charts_html = self._create_portfolio_charts(results['portfolio_history'])
        
        # Generate trade table
        trades_html = self._create_trades_table(results.get('trades', []))
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>pDAI Trading Bot - Backtest Results</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 12px;
                    margin-bottom: 30px;
                    text-align: center;
                }}
                
                .header h1 {{ margin: 0; font-size: 2.5em; }}
                .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
                
                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                
                .metric-card {{
                    background: white;
                    padding: 25px;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    text-align: center;
                    transition: transform 0.2s;
                }}
                
                .metric-card:hover {{ transform: translateY(-2px); }}
                
                .metric-value {{
                    font-size: 2.5em;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                
                .metric-label {{
                    color: #666;
                    font-size: 0.9em;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                
                .positive {{ color: #28a745; }}
                .negative {{ color: #dc3545; }}
                .neutral {{ color: #6c757d; }}
                
                .section {{
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    margin-bottom: 30px;
                }}
                
                .section h2 {{
                    margin-top: 0;
                    color: #495057;
                    border-bottom: 2px solid #e9ecef;
                    padding-bottom: 10px;
                }}
                
                .trades-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                
                .trades-table th, .trades-table td {{
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #dee2e6;
                }}
                
                .trades-table th {{
                    background-color: #f8f9fa;
                    font-weight: 600;
                    color: #495057;
                }}
                
                .trades-table tr:hover {{
                    background-color: #f8f9fa;
                }}
                
                .timestamp {{
                    color: #6c757d;
                    font-size: 0.9em;
                }}
                
                .chart-container {{
                    margin: 20px 0;
                    text-align: center;
                }}
                
                .footer {{
                    text-align: center;
                    color: #6c757d;
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #dee2e6;
                }}
                
                .refresh-notice {{
                    background: #e7f3ff;
                    border: 1px solid #b6e0ff;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 20px;
                    text-align: center;
                }}
            </style>
            <meta http-equiv="refresh" content="30">
        </head>
        <body>
            <div class="header">
                <h1>🚀 pDAI Trading Bot</h1>
                <p>Backtest Results - {strategy_name}</p>
                <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="refresh-notice">
                📊 This report auto-refreshes every 30 seconds
            </div>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Total Return</div>
                    <div class="metric-value {'positive' if total_return > 0 else 'negative' if total_return < 0 else 'neutral'}">
                        {total_return:+.2f}%
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value {'positive' if win_rate > 50 else 'negative' if win_rate < 50 else 'neutral'}">
                        {win_rate:.1f}%
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Max Drawdown</div>
                    <div class="metric-value negative">
                        -{max_drawdown:.2f}%
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Sharpe Ratio</div>
                    <div class="metric-value {'positive' if sharpe_ratio > 1 else 'neutral' if sharpe_ratio > 0 else 'negative'}">
                        {sharpe_ratio:.2f}
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Total Trades</div>
                    <div class="metric-value neutral">
                        {total_trades}
                    </div>
                </div>
                
                <div class="metric-card">
                    <div class="metric-label">Final Balance</div>
                    <div class="metric-value {'positive' if results.get('final_balance', 0) > results.get('initial_balance', 0) else 'negative'}">
                        {results.get('final_balance', 0):.4f} DAI
                    </div>
                </div>
            </div>
            
            {charts_html}
            
            <div class="section">
                <h2>📊 Detailed Results</h2>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
                    <div>
                        <h3>Performance Metrics</h3>
                        <p><strong>Initial Balance:</strong> {results.get('initial_balance', 0):.4f} DAI</p>
                        <p><strong>Final Balance:</strong> {results.get('final_balance', 0):.4f} DAI</p>
                        <p><strong>Total Fees:</strong> {results.get('total_fees', 0):.6f} DAI</p>
                        <p><strong>Volatility:</strong> {results.get('volatility_pct', 0):.2f}%</p>
                        <p><strong>Profit Factor:</strong> {results.get('profit_factor', 0):.2f}</p>
                    </div>
                    
                    <div>
                        <h3>Trading Statistics</h3>
                        <p><strong>Buy Trades:</strong> {results.get('buy_trades', 0)}</p>
                        <p><strong>Sell Trades:</strong> {results.get('sell_trades', 0)}</p>
                        <p><strong>Profitable Trades:</strong> {results.get('profitable_trades', 0)}</p>
                        <p><strong>Losing Trades:</strong> {results.get('losing_trades', 0)}</p>
                        <p><strong>Average Win:</strong> {results.get('avg_win_pct', 0):.2f}%</p>
                        <p><strong>Average Loss:</strong> {results.get('avg_loss_pct', 0):.2f}%</p>
                    </div>
                </div>
            </div>
            
            {trades_html}
            
            <div class="footer">
                <p>📈 pDAI Trading Bot | PulseChain Automated Trading</p>
                <p>⚠️ This is for educational purposes only. Past performance does not guarantee future results.</p>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def _create_portfolio_charts(self, portfolio_history: List[Dict]) -> str:
        """Create portfolio value charts using simple HTML/CSS (fallback)"""
        if not portfolio_history:
            return ""
        
        # For now, return a simple placeholder
        # In a full implementation, we would generate Bokeh charts here
        return """
        <div class="section">
            <h2>📈 Portfolio Performance</h2>
            <div class="chart-container">
                <p style="color: #6c757d; font-style: italic;">
                    Interactive charts will be displayed here in the full version.
                    Portfolio data contains {len(portfolio_history)} data points.
                </p>
            </div>
        </div>
        """
    
    def _create_trades_table(self, trades: List[Dict]) -> str:
        """Create HTML table for trades"""
        if not trades:
            return """
            <div class="section">
                <h2>📝 Trade History</h2>
                <p>No trades executed during this backtest.</p>
            </div>
            """
        
        # Limit to last 20 trades for display
        recent_trades = trades[-20:] if len(trades) > 20 else trades
        
        rows_html = ""
        for trade in recent_trades:
            trade_type = trade.get('type', 'unknown')
            row_class = 'positive' if trade_type == 'buy' else 'negative' if trade_type == 'sell' else 'neutral'
            
            timestamp_str = trade.get('timestamp', '')
            if isinstance(timestamp_str, str):
                timestamp_display = timestamp_str
            else:
                timestamp_display = str(timestamp_str)
            
            pnl_display = ""
            if trade_type == 'sell' and 'pnl_pct' in trade:
                pnl = trade['pnl_pct']
                pnl_class = 'positive' if pnl > 0 else 'negative'
                pnl_display = f"<span class='{pnl_class}'>{pnl:+.2f}%</span>"
            
            rows_html += f"""
            <tr>
                <td class="timestamp">{timestamp_display}</td>
                <td><span class="{row_class}">{trade_type.upper()}</span></td>
                <td>{trade.get('price', 0):.8f}</td>
                <td>{trade.get('pdai_amount', 0):.4f}</td>
                <td>{trade.get('quote_amount', 0):.4f}</td>
                <td>{trade.get('fee', 0):.6f}</td>
                <td>{pnl_display}</td>
                <td>{trade.get('signal_strength', 0):.2f}</td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2>📝 Trade History</h2>
            <p>Showing {'last 20' if len(trades) > 20 else 'all'} trades (Total: {len(trades)})</p>
            
            <table class="trades-table">
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Type</th>
                        <th>Price (DAI)</th>
                        <th>pDAI Amount</th>
                        <th>Quote Amount (DAI)</th>
                        <th>Fee (DAI)</th>
                        <th>P&L %</th>
                        <th>Signal Strength</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """
    
    def _create_live_html(self, portfolio_data: List[Dict], strategy_data: Dict) -> str:
        """Create HTML content for live trading"""
        
        current_balance = portfolio_data[-1].get('total_value', 0) if portfolio_data else 0
        current_price = portfolio_data[-1].get('price', 0) if portfolio_data else 0
        position = portfolio_data[-1].get('position', 'none') if portfolio_data else 'none'
        
        recommendation = strategy_data.get('recommendation', 'hold')
        signal_strength = strategy_data.get('signal_strength', 0)
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>pDAI Trading Bot - Live Trading</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }}
                
                .header {{
                    background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 12px;
                    margin-bottom: 30px;
                    text-align: center;
                }}
                
                .header h1 {{ margin: 0; font-size: 2.5em; }}
                .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
                
                .status-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                
                .status-card {{
                    background: white;
                    padding: 25px;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                
                .status-value {{
                    font-size: 2em;
                    font-weight: bold;
                    margin: 10px 0;
                }}
                
                .status-label {{
                    color: #666;
                    font-size: 0.9em;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                
                .live-indicator {{
                    display: inline-block;
                    width: 12px;
                    height: 12px;
                    background-color: #28a745;
                    border-radius: 50%;
                    animation: pulse 2s infinite;
                    margin-right: 8px;
                }}
                
                @keyframes pulse {{
                    0% {{ opacity: 1; }}
                    50% {{ opacity: 0.5; }}
                    100% {{ opacity: 1; }}
                }}
                
                .positive {{ color: #28a745; }}
                .negative {{ color: #dc3545; }}
                .neutral {{ color: #6c757d; }}
                
                .refresh-notice {{
                    background: #e7f3ff;
                    border: 1px solid #b6e0ff;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 20px;
                    text-align: center;
                }}
            </style>
            <meta http-equiv="refresh" content="10">
        </head>
        <body>
            <div class="header">
                <h1>🔥 pDAI Trading Bot</h1>
                <p><span class="live-indicator"></span>Live Trading Mode</p>
                <p class="timestamp">Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="refresh-notice">
                🔄 This page auto-refreshes every 10 seconds | ⚠️ Demo Mode Active
            </div>
            
            <div class="status-grid">
                <div class="status-card">
                    <div class="status-label">Current Price</div>
                    <div class="status-value neutral">
                        {current_price:.8f} DAI
                    </div>
                </div>
                
                <div class="status-card">
                    <div class="status-label">Portfolio Value</div>
                    <div class="status-value positive">
                        {current_balance:.4f} DAI
                    </div>
                </div>
                
                <div class="status-card">
                    <div class="status-label">Current Position</div>
                    <div class="status-value {'positive' if position == 'long' else 'neutral'}">
                        {position.upper() if position else 'NONE'}
                    </div>
                </div>
                
                <div class="status-card">
                    <div class="status-label">Strategy Signal</div>
                    <div class="status-value {'positive' if recommendation == 'buy' else 'negative' if recommendation == 'sell' else 'neutral'}">
                        {recommendation.upper()}
                    </div>
                </div>
                
                <div class="status-card">
                    <div class="status-label">Signal Strength</div>
                    <div class="status-value neutral">
                        {signal_strength:.2f}
                    </div>
                </div>
            </div>
            
            <div style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center;">
                <h2>🎯 Strategy Status</h2>
                <p style="font-size: 1.2em; margin: 20px 0;">
                    <strong>Recommendation:</strong> 
                    <span class="{'positive' if recommendation == 'buy' else 'negative' if recommendation == 'sell' else 'neutral'}">
                        {recommendation.upper()}
                    </span>
                </p>
                <p style="color: #666;">
                    {strategy_data.get('reason', 'No specific reason provided')}
                </p>
            </div>
            
            <div style="text-align: center; color: #6c757d; margin-top: 40px; padding-top: 20px; border-top: 1px solid #dee2e6;">
                <p>📈 pDAI Trading Bot | PulseChain Automated Trading</p>
                <p>⚠️ Demo Mode - No Real Trading</p>
            </div>
        </body>
        </html>
        """
        
        return html_template
