#!/usr/bin/env python3
"""
Strategy 002: Bearish Abandoned Baby Candlestick Pattern

LazyBear Strategy Number: 008 (Original)
Strategy ID: 002 (Canonical)
LazyBear Name: Bearish Abandoned Baby
Type: candlestick/reversal
TradingView URL: https://www.tradingview.com/v/ixvySF6T/ (referenced)

Description:
Identifies the Bearish Abandoned Baby candlestick pattern using TA-Lib.
This is a three-candle bearish reversal pattern:
1. A large bullish candle.
2. A doji that gaps above the close of the first candle.
3. A large bearish candle that gaps below the second candle and closes
   within the body of the first candle.
It signals a potential reversal to the downside.
"""

import pandas as pd
import numpy as np
import talib
import sys
import os

# Add parent directories to path for imports
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, repo_root)
sys.path.insert(0, os.path.join(repo_root, 'src'))
from templates.candlestick_strategy_template import CandlestickStrategyTemplate


class Strategy002Abandonedbaby(CandlestickStrategyTemplate):
    """
    Strategy 002: Bearish Abandoned Baby Candlestick Pattern

    Identifies the Bearish Abandoned Baby candlestick pattern using TA-Lib.
    This is a three-candle bearish reversal pattern that signals a potential reversal to the downside.
    """

    def __init__(self, parameters=None):
        """
        Initialize strategy with parameters
        For this pattern, there are no optimizable parameters.
        """
        if parameters is None:
            parameters = {}
        
        # Initialize parent class
        super().__init__(
            name="Strategy_002_Abandonedbaby",
            parameters=parameters
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the Bearish Abandoned Baby pattern using TA-Lib.
        Populates 'bullish_pattern_detected' and 'bearish_pattern_detected' boolean columns.
        """
        # Ensure we have OHLC data using the template helper method
        data = self.ensure_ohlc_data(data)
        
        # Calculate Abandoned Baby pattern using TA-Lib
        # Returns -100 for bearish abandoned baby, +100 for bullish abandoned baby, 0 for no pattern
        pattern_values = talib.CDLABANDONEDBABY(
            data['open'].to_numpy(),
            data['high'].to_numpy(),
            data['low'].to_numpy(),
            data['close'].to_numpy()
        )
        
        # Convert TA-Lib output to boolean pattern detection columns expected by template
        data['bullish_pattern_detected'] = (pattern_values > 0)
        data['bearish_pattern_detected'] = (pattern_values < 0)
        
        return data


# Test function for smoke testing
if __name__ == "__main__":
    # Create sample data with realistic OHLCV structure
    import datetime
    
    # Generate sample data with pattern-like structures
    np.random.seed(42)  # For reproducible results
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='5min')
    n_points = len(dates)
    
    # Create realistic price movement with some volatility
    base_price = 100
    price_changes = np.random.randn(n_points).cumsum() * 0.5
    
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'open': base_price + price_changes + np.random.randn(n_points) * 0.1,
        'high': base_price + price_changes + np.random.randn(n_points) * 0.1 + 0.5,
        'low': base_price + price_changes + np.random.randn(n_points) * 0.1 - 0.5,
        'close': base_price + price_changes,
        'volume': np.random.randint(1000, 10000, n_points)
    })
    
    # Ensure OHLC consistency (High >= Open,Close >= Low)
    sample_data['high'] = sample_data[['open', 'close', 'high']].max(axis=1)
    sample_data['low'] = sample_data[['open', 'close', 'low']].min(axis=1)
    sample_data['price'] = sample_data['close']
    
    print("🔍 Testing Strategy 002: Bearish Abandoned Baby")
    print(f"Sample data shape: {sample_data.shape}")
    
    try:
        # Test strategy initialization
        strategy = Strategy008BearishAbandonedBaby()
        print("✅ Strategy initialization successful")
        
        # Test indicator calculation
        data_with_indicators = strategy.calculate_indicators(sample_data.copy())
        print(f"✅ Indicator calculation successful - Added columns: {[col for col in data_with_indicators.columns if col not in sample_data.columns]}")
        
        # Test signal generation
        data_with_signals = strategy.generate_signals(data_with_indicators)
        print("✅ Signal generation successful")
        
        # Validate signals
        if strategy.validate_signals(data_with_signals):
            print("✅ Signal validation passed")
            
            # Print summary statistics
            buy_signals = data_with_signals['buy_signal'].sum()
            sell_signals = data_with_signals['sell_signal'].sum()
            avg_strength = data_with_signals['signal_strength'].mean()
            min_strength = data_with_signals['signal_strength'].min()
            max_strength = data_with_signals['signal_strength'].max()
            
            print(f"📊 Signal Summary:")
            print(f"   Buy signals: {buy_signals}")
            print(f"   Sell signals: {sell_signals}")
            print(f"   Average signal strength: {avg_strength:.3f}")
            print(f"   Min signal strength: {min_strength:.3f}")
            print(f"   Max signal strength: {max_strength:.3f}")
            
            # Check for pattern detections
            if 'bullish_pattern_detected' in data_with_indicators.columns:
                bullish_patterns = data_with_indicators['bullish_pattern_detected'].sum()
                bearish_patterns = data_with_indicators['bearish_pattern_detected'].sum()
                print(f"   Bullish Abandoned Baby patterns detected: {bullish_patterns}")
                print(f"   Bearish Abandoned Baby patterns detected: {bearish_patterns}")
            
            total_signals = buy_signals + sell_signals
            if total_signals > 0:
                print(f"✅ Strategy generated {total_signals} total signals ({buy_signals} buy, {sell_signals} sell) - Ready for deployment")
            else:
                print("ℹ️  No signals in test data - This is normal for pattern-based strategies")
                
        else:
            print("❌ Signal validation failed")
            
    except Exception as e:
        print(f"❌ Strategy test failed with error: {e}")
        import traceback
        traceback.print_exc()