#!/usr/bin/env python3
"""
Strategy 025: Spinning Top Candlestick Pattern

LazyBear Strategy Number: 020 (Original)
Strategy ID: 025 (Canonical)
LazyBear Name: Spinning Top
Type: candlestick/reversal
TradingView URL: https://www.tradingview.com/v/1GeJzXyY/ (referenced)

Description:
Identifies the Spinning Top candlestick pattern using TA-Lib.
This is a single-candle reversal pattern characterized by:
- Small real body (open and close are close but not identical)
- Long upper and lower shadows
- Body positioned anywhere within the high-low range
- Indicates market indecision and potential reversal

The Spinning Top pattern suggests that neither bulls nor bears were able
to gain decisive control during the trading session. The small body
indicates minimal price movement between open and close, while the long
shadows show that both sides tested their strength but neither prevailed.

This implementation uses the CandlestickStrategyTemplate for standardized signal generation.
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


class Strategy025Spinningtop(CandlestickStrategyTemplate):
    """
    Strategy 025: Spinning Top Candlestick Pattern

    Identifies the Spinning Top candlestick pattern using TA-Lib.
    This is a single-candle reversal pattern that signals market indecision.
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
            name="Strategy_025_Spinningtop",
            parameters=parameters
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the Spinning Top pattern using TA-Lib.
        Populates 'bullish_pattern_detected' and 'bearish_pattern_detected' boolean columns.
        """
        # Ensure we have OHLC data using the template helper method
        data = self.ensure_ohlc_data(data)
        
        # Calculate Spinning Top pattern using TA-Lib
        # Returns +100 for bullish, -100 for bearish, 0 for no pattern
        cdl_spinning_top = talib.CDLSPINNINGTOP(
            data['open'].to_numpy(),
            data['high'].to_numpy(),
            data['low'].to_numpy(),
            data['close'].to_numpy()
        )
        
        # Convert TA-Lib output to boolean pattern detection columns expected by template
        data['bullish_pattern_detected'] = (cdl_spinning_top > 0)
        data['bearish_pattern_detected'] = (cdl_spinning_top < 0)
        
        # Keep original column for reference/debugging
        data['cdl_spinning_top'] = cdl_spinning_top
        
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
    
    print("🔍 Testing Strategy 025: Spinning Top (Template-based)")
    print(f"Sample data shape: {sample_data.shape}")
    
    try:
        # Test strategy initialization
        strategy = Strategy020SpinningTop()
        print("✅ Strategy initialization successful")
        
        # Test indicator calculation
        data_with_indicators = strategy.calculate_indicators(sample_data.copy())
        print(f"✅ Indicator calculation successful - Added columns: {[col for col in data_with_indicators.columns if col not in sample_data.columns]}")
        
        # Test signal generation (now inherited from template)
        data_with_signals = strategy.generate_signals(data_with_indicators)
        print("✅ Signal generation successful (from template)")
        
        # Validate signals (now inherited from template)
        if strategy.validate_signals(data_with_signals):
            print("✅ Signal validation passed (from template)")
            
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
            if 'cdl_spinning_top' in data_with_indicators.columns:
                bullish_patterns = (data_with_indicators['cdl_spinning_top'] > 0).sum()
                bearish_patterns = (data_with_indicators['cdl_spinning_top'] < 0).sum()
                print(f"   Bullish Spinning Top patterns detected: {bullish_patterns}")
                print(f"   Bearish Spinning Top patterns detected: {bearish_patterns}")
            
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