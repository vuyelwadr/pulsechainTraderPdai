"""
PDAI Trading Bot - Main Bot Class
Orchestrates all components for automated PDAI trading on PulseChain
"""
import argparse
import os, sys
# Ensure repo root on sys.path so sibling packages import correctly when running this file directly
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional
import json
import os

from bot.config import Config
from bot.data_handler import DataHandler
from strategies.base_strategy import StrategyManager
from strategies.ma_crossover import MovingAverageCrossover
from bot.backtest_engine import BacktestEngine
from bot.html_generator import HTMLGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class PDAITradingBot:
    """Main PDAI Trading Bot class"""
    
    def __init__(self, demo_mode: bool = True):
        self.config = Config()
        self.demo_mode = demo_mode or self.config.DEMO_MODE
        
        # Initialize components
        self.data_handler = DataHandler()
        self.strategy_manager = StrategyManager()
        self.backtest_engine = BacktestEngine()
        self.html_generator = HTMLGenerator()
        
        # Trading state
        self.is_running = False
        self.portfolio_history = []
        self.current_position = None
        self.balance = float(self.config.INITIAL_BALANCE)
        self.pdai_balance = 0.0
        
        # Setup strategies
        self._initialize_strategies()
        
        logger.info(f"PDAI Trading Bot initialized - Demo Mode: {self.demo_mode}")
    
    def _initialize_strategies(self):
        """Initialize available trading strategies"""
        
        # Add Moving Average Crossover strategy
        ma_strategy = MovingAverageCrossover({
            'short_period': self.config.MA_SHORT_PERIOD,
            'long_period': self.config.MA_LONG_PERIOD,
            'ma_type': 'ema',
            'min_strength': 0.6
        })
        self.strategy_manager.add_strategy(ma_strategy)
        
        logger.info(f"Initialized {len(self.strategy_manager.list_strategies())} strategies")
    
    def run_backtest(self, days: int = None, strategy_name: str = None) -> Dict:
        """Run backtest on historical data"""
        
        days = days or self.config.BACKTEST_DAYS
        logger.info(f"Starting backtest for {days} days")
        
        # Fetch historical data
        historical_data = self.data_handler.fetch_historical_data(days)
        if historical_data.empty:
            return {'error': 'No historical data available'}
        
        # Select strategy
        if strategy_name:
            if strategy_name not in self.strategy_manager.strategies:
                return {'error': f'Strategy {strategy_name} not found'}
            strategy = self.strategy_manager.strategies[strategy_name]
        else:
            strategy = self.strategy_manager.get_active_strategy()
            if not strategy:
                return {'error': 'No active strategy selected'}
        
        # Run backtest
        results = self.backtest_engine.run_backtest(
            strategy,
            historical_data,
        )
        
        # Generate HTML report
        if not results.get('error'):
            html_file = self.html_generator.generate_backtest_report(results, strategy.name)
            results['html_report'] = html_file
        
        return results
    
    def start_live_trading(self):
        """Start live trading mode"""
        if not self.demo_mode:
            logger.error("Live trading with real money not implemented yet - use demo mode")
            return
        
        logger.info("Starting live trading in DEMO MODE")
        self.is_running = True
        
        # Start trading loop in separate thread
        trading_thread = threading.Thread(target=self._trading_loop, daemon=True)
        trading_thread.start()
        
        return trading_thread
    
    def stop_trading(self):
        """Stop live trading"""
        logger.info("Stopping trading bot")
        self.is_running = False
    
    def _trading_loop(self):
        """Main trading loop for live trading"""
        last_update = datetime.now()
        
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Update data every minute
                if (current_time - last_update).total_seconds() >= 60:
                    
                    # Get current price
                    current_price = self.data_handler.get_current_price()
                    if current_price is None:
                        logger.warning("Could not fetch current price")
                        time.sleep(10)
                        continue
                    
                    # Add to historical data
                    self.data_handler.add_price_point(current_price)
                    
                    # Get recent data for analysis
                    recent_data = self.data_handler.get_latest_data(100)
                    if recent_data.empty:
                        logger.warning("No data available for analysis")
                        time.sleep(10)
                        continue
                    
                    # Get trading signal
                    signal, strength = self.strategy_manager.get_signal(recent_data)
                    
                    # Execute trade if in demo mode
                    if self.demo_mode:
                        self._execute_demo_trade(signal, strength, current_price)
                    
                    # Update portfolio history
                    self._update_portfolio_state(current_price, signal, strength)
                    
                    # Generate HTML report
                    self._generate_live_report()
                    
                    last_update = current_time
                    
                    logger.info(f"Price: {current_price:.8f} DAI, Signal: {signal}, Strength: {strength:.2f}")
                
                time.sleep(5)  # Check every 5 seconds
                
            except KeyboardInterrupt:
                logger.info("Trading interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                time.sleep(10)
        
        self.is_running = False
        logger.info("Trading loop stopped")
    
    def _execute_demo_trade(self, signal: str, strength: float, price: float):
        """Execute trades in demo mode"""
        if strength < 0.6:  # Minimum signal strength
            return
        
        if signal == 'buy' and self.current_position != 'long':
            # Buy PDAI with DAI (routed through WPLS on-chain)
            trade_amount = self.balance  # Deploy full balance by default
            if trade_amount > 1.0:  # Minimum trade
                fee = trade_amount * 0.0025  # 0.25% fee
                net_amount = trade_amount - fee
                pdai_received = net_amount / price
                
                self.balance -= trade_amount
                self.pdai_balance += pdai_received
                self.current_position = 'long'
                
                logger.info(f"DEMO BUY: {pdai_received:.4f} PDAI at {price:.8f} DAI")
        
        elif signal == 'sell' and self.current_position == 'long':
            # Sell PDAI for DAI
            if self.pdai_balance > 0:
                quote_gross = self.pdai_balance * price
                fee = quote_gross * 0.0025
                quote_net = quote_gross - fee
                
                self.balance += quote_net
                pdai_sold = self.pdai_balance
                self.pdai_balance = 0.0
                self.current_position = None
                
                logger.info(f"DEMO SELL: {pdai_sold:.4f} PDAI at {price:.8f} DAI")
    
    def _update_portfolio_state(self, price: float, signal: str, strength: float):
        """Update portfolio state tracking"""
        pdai_value = self.pdai_balance * price
        total_value = self.balance + pdai_value
        
        state = {
            'timestamp': datetime.now(),
            'price': price,
            'quote_balance': self.balance,
            'pdai_balance': self.pdai_balance,
            'pdai_value_quote': pdai_value,
            'total_value': total_value,
            'position': self.current_position,
            'signal': signal,
            'signal_strength': strength
        }
        
        self.portfolio_history.append(state)
        
        # Keep only last 1000 points
        if len(self.portfolio_history) > 1000:
            self.portfolio_history = self.portfolio_history[-500:]
    
    def _generate_live_report(self):
        """Generate live trading HTML report"""
        if not self.portfolio_history:
            return
        
        # Get strategy recommendation
        recent_data = self.data_handler.get_latest_data(50)
        if not recent_data.empty:
            strategy = self.strategy_manager.get_active_strategy()
            if strategy and hasattr(strategy, 'get_current_position_recommendation'):
                strategy_data = strategy.get_current_position_recommendation(recent_data)
            else:
                signal, strength = self.strategy_manager.get_signal(recent_data)
                strategy_data = {
                    'recommendation': signal,
                    'signal_strength': strength,
                    'reason': f'Signal from {strategy.name if strategy else "unknown strategy"}'
                }
        else:
            strategy_data = {'recommendation': 'hold', 'signal_strength': 0, 'reason': 'No data available'}
        
        # Generate HTML report
        html_file = self.html_generator.generate_live_report(
            self.portfolio_history[-100:],  # Last 100 points
            strategy_data
        )
        
        # Also save to a fixed filename for easy access
        fixed_filename = os.path.join(self.config.HTML_DIR, "live_trading.html")
        try:
            with open(html_file, 'r') as source:
                content = source.read()
            with open(fixed_filename, 'w') as target:
                target.write(content)
        except Exception as e:
            logger.warning(f"Could not create fixed filename report: {e}")
    
    def get_status(self) -> Dict:
        """Get current bot status"""
        current_price = self.data_handler.get_current_price() or 0
        pdai_value = self.pdai_balance * current_price
        total_value = self.balance + pdai_value
        
        status = {
            'is_running': self.is_running,
            'demo_mode': self.demo_mode,
            'current_price': current_price,
            'quote_balance': self.balance,
            'pdai_balance': self.pdai_balance,
            'pdai_value_quote': pdai_value,
            'total_value': total_value,
            'position': self.current_position,
            'active_strategy': self.strategy_manager.active_strategy,
            'available_strategies': self.strategy_manager.list_strategies(),
            'data_points': len(self.data_handler.price_history)
        }
        
        return status
    
    def get_portfolio_summary(self) -> str:
        """Get formatted portfolio summary"""
        status = self.get_status()
        
        summary = f"""
PDAI Trading Bot Status
====================
Mode: {'DEMO' if self.demo_mode else 'LIVE'}
Running: {'Yes' if self.is_running else 'No'}

Portfolio:
  DAI Balance: {status['quote_balance']:.4f}
  PDAI Balance: {status['pdai_balance']:.4f}
  PDAI Value (DAI): {status['pdai_value_quote']:.4f}
  Total Value: {status['total_value']:.4f}
  
Current Position: {status['position'] or 'None'}
Current Price: {status['current_price']:.8f} DAI
Active Strategy: {status['active_strategy']}
Data Points: {status['data_points']}
        """
        
        return summary.strip()

def main():
    """Main function for CLI interface"""
    parser = argparse.ArgumentParser(description='PDAI Trading Bot for PulseChain')
    parser.add_argument('--backtest', action='store_true', help='Run backtest mode')
    parser.add_argument('--live', action='store_true', help='Run live trading mode')
    parser.add_argument('--days', type=int, default=30, help='Days of data for backtesting')
    parser.add_argument('--strategy', type=str, help='Strategy to use')
    parser.add_argument('--demo', action='store_true', default=True, help='Force demo mode')
    
    args = parser.parse_args()
    
    # Create bot instance
    bot = PDAITradingBot(demo_mode=args.demo)
    
    try:
        if args.backtest:
            print("🚀 Running PDAI Trading Bot Backtest...")
            print(f"📊 Testing {args.days} days of data")
            
            results = bot.run_backtest(days=args.days, strategy_name=args.strategy)
            
            if 'error' in results:
                print(f"❌ Error: {results['error']}")
                return
            
            # Print results
            print("\n" + "="*50)
            print("BACKTEST RESULTS")
            print("="*50)
            print(f"Strategy: {results.get('strategy_name', 'Unknown')}")
            print(f"Initial Balance: {results.get('initial_balance', 0):.4f} DAI")
            print(f"Final Balance: {results.get('final_balance', 0):.4f} DAI")
            print(f"Total Return: {results.get('total_return_pct', 0):+.2f}%")
            print(f"Total Trades: {results.get('total_trades', 0)}")
            print(f"Win Rate: {results.get('win_rate_pct', 0):.1f}%")
            print(f"Max Drawdown: {results.get('max_drawdown_pct', 0):.2f}%")
            print(f"Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
            
            if 'html_report' in results:
                print(f"\n📊 HTML Report: {results['html_report']}")
            
        elif args.live:
            print("🔥 Starting PDAI Trading Bot Live Mode...")
            print("⚠️  DEMO MODE ACTIVE - No real trading")
            print("Press Ctrl+C to stop\n")
            
            # Start live trading
            bot.start_live_trading()
            
            # Print status updates
            try:
                while bot.is_running:
                    time.sleep(30)  # Update every 30 seconds
                    print("\n" + "="*40)
                    print(bot.get_portfolio_summary())
                    print("="*40)
                    
            except KeyboardInterrupt:
                print("\n\n🛑 Stopping bot...")
                bot.stop_trading()
                time.sleep(2)
                print("✅ Bot stopped")
        
        else:
            # Show status
            print("🤖 PDAI Trading Bot")
            print(bot.get_portfolio_summary())
            print("\nUse --backtest to run backtesting or --live for live trading")
            print("Use --help for more options")
    
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
