#!/usr/bin/env python3
"""
Strategy 004: Belt-hold Candlestick Pattern

LazyBear Strategy Number: 004 (Original)
Strategy ID: 004 (Canonical)
LazyBear Name: Belt-hold
Type: candlestick/reversal
TradingView URL: https://www.tradingview.com/v/ixvySF6T/ (referenced)

Description:
Identifies the Belt-hold candlestick pattern using TA-Lib.
This is a single-candle reversal pattern that comes in both bullish and bearish forms:

Bullish Belt-hold (White Opening Shaved Bottom):
- A long white (bullish) candle that opens at or near its low
- Little to no lower shadow
- Signals potential reversal to the upside after a downtrend

Bearish Belt-hold (Black Opening Shaved Head):
- A long black (bearish) candle that opens at or near its high
- Little to no upper shadow
- Signals potential reversal to the downside after an uptrend

This implementation uses bidirectional signals based on both pattern types.
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


class Strategy004Belthold(CandlestickStrategyTemplate):
    """
    Strategy 004: Belt-hold Candlestick Pattern

    Identifies the Belt-hold candlestick pattern using TA-Lib.
    This is a single-candle reversal pattern that provides bidirectional signals.
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
            name="Strategy_004_Belthold",
            parameters=parameters
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the Belt-hold pattern using TA-Lib.
        Populates 'bullish_pattern_detected' and 'bearish_pattern_detected' boolean columns.
        """
        # Ensure we have OHLC data using the template helper method
        data = self.ensure_ohlc_data(data)
        
        # Calculate Belt-hold pattern using TA-Lib
        # Returns +100 for bullish belt-hold, -100 for bearish belt-hold, 0 for no pattern
        cdl_belthold = talib.CDLBELTHOLD(
            data['open'].to_numpy(),
            data['high'].to_numpy(),
            data['low'].to_numpy(),
            data['close'].to_numpy()
        )
        
        # Convert TA-Lib output to boolean pattern detection columns expected by template
        data['bullish_pattern_detected'] = (cdl_belthold > 0)
        data['bearish_pattern_detected'] = (cdl_belthold < 0)
        
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
    
    print("🔍 Testing Strategy 004: Belt-hold")
    print(f"Sample data shape: {sample_data.shape}")
    
    try:
        # Test strategy initialization
        strategy = Strategy004BeltHold()
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
                print(f"   Bullish Belt-hold patterns detected: {bullish_patterns}")
                print(f"   Bearish Belt-hold patterns detected: {bearish_patterns}")
            
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