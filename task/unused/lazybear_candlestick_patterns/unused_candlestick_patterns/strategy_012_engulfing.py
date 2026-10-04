#!/usr/bin/env python3
"""
Strategy 012: Bullish Engulfing Candlestick Pattern

LazyBear Strategy Number: 006 (Original)
Strategy ID: 012 (Canonical)
LazyBear Name: Bullish Engulfing
Type: candlestick/reversal
TradingView URL: https://www.tradingview.com/v/qoQoqU4Q/ (referenced)

Description:
Identifies the Bullish Engulfing candlestick pattern using TA-Lib.
A Bullish Engulfing is a two-candle bullish reversal pattern:
1. A smaller bearish (red) candle.
2. Followed by a larger bullish (green) candle whose body completely
   engulfs the body of the previous bearish candle.
It often signals a potential reversal to the upside.
"""

import pandas as pd
import numpy as np
import talib
import sys
import os

# Add parent directories to path for imports
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, repo_root)
from strategies.base_strategy import BaseStrategy


class Strategy012Engulfing(BaseStrategy):
    """
    Strategy 012: Bullish Engulfing Candlestick Pattern

    Simple candlestick pattern detection strategy focusing purely on
    the Bullish Engulfing pattern with state management for look-ahead bias prevention.
    """

    def __init__(self, parameters: dict = None):
        """
        Initialize strategy with parameters
        
        No optimizable parameters for simple candlestick patterns
        """
        # Empty parameters for simple candlestick patterns
        default_params = {}
        
        # Merge with provided parameters (though none expected for simple patterns)
        if parameters:
            default_params.update(parameters)
        
        # Initialize parent class
        super().__init__(
            name="Strategy_012_Engulfing",
            parameters=default_params
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all indicators needed for the Bullish Engulfing strategy
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            DataFrame with additional indicator columns
        """
        # Ensure we have required columns
        if 'close' not in data.columns and 'price' in data.columns:
            data['close'] = data['price']
        
        # Ensure we have OHLC data for candlestick patterns
        if 'open' not in data.columns:
            data['open'] = data['close'].shift(1).fillna(data['close'])
        if 'high' not in data.columns:
            data['high'] = data['close']
        if 'low' not in data.columns:
            data['low'] = data['close']
        
        # Calculate Engulfing candlestick pattern using TA-Lib directly
        # Returns +100 for bullish engulfing, -100 for bearish engulfing, 0 for no pattern
        data['cdl_engulfing'] = talib.CDLENGULFING(
            data['open'].to_numpy(),
            data['high'].to_numpy(),
            data['low'].to_numpy(),
            data['close'].to_numpy()
        )
        
        # Identify bullish engulfing pattern (positive values indicate bullish)
        data['bullish_engulfing_detected'] = data['cdl_engulfing'] > 0
        
        return data

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate buy/sell signals based on Bullish Engulfing pattern
        
        Args:
            data: DataFrame with price and indicator data
            
        Returns:
            DataFrame with buy_signal, sell_signal, and signal_strength columns
        """
        # Initialize signal columns
        data['buy_signal'] = False
        data['sell_signal'] = False
        data['signal_strength'] = 0.0
        
        # Primary condition: Bullish Engulfing pattern detected
        bullish_engulfing_signal = data['bullish_engulfing_detected']
        
        # --- State Management for look-ahead bias prevention ---
        # Create raw signal: +1 for buy, 0 for no signal
        raw_signal = np.where(bullish_engulfing_signal, 1, 0)
        
        # Calculate position state with forward fill
        position = pd.Series(raw_signal).replace(0, np.nan).ffill().fillna(0)
        
        # Determine state based on previous bar to avoid look-ahead bias
        is_flat = (position.shift(1) == 0)
        
        # Generate buy signals: only when pattern detected and currently flat
        combined_signal = bullish_engulfing_signal & is_flat
        
        # Apply look-ahead bias prevention using shift(1)
        data['buy_signal'] = combined_signal.shift(1).fillna(False).astype(bool)
        
        # Set fixed signal strength for active signals
        data.loc[data['buy_signal'], 'signal_strength'] = 1.0
        
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
    
    print("🔍 Testing Strategy 012: Bullish Engulfing")
    print(f"Sample data shape: {sample_data.shape}")
    
    try:
        # Test strategy initialization
        strategy = Strategy006BullishEngulfing()
        print("✅ Strategy initialization successful")
        
        # Test indicator calculation
        data_with_indicators = strategy.calculate_indicators(sample_data.copy())
        print(f"✅ Indicator calculation successful - Added columns: {[col for col in data_with_indicators.columns if col not in sample_data.columns]}")
        
        # Test signal generation
        data_with_signals = strategy.generate_signals(data_with_indicators)
        print("✅ Signal generation successful")
        
        # Print summary statistics
        buy_signals = data_with_signals['buy_signal'].sum()
        sell_signals = data_with_signals['sell_signal'].sum()
        avg_strength = data_with_signals['signal_strength'].mean()
        max_strength = data_with_signals['signal_strength'].max()
        
        print(f"📊 Signal Summary:")
        print(f"   Buy signals: {buy_signals}")
        print(f"   Sell signals: {sell_signals}")
        print(f"   Average signal strength: {avg_strength:.3f}")
        print(f"   Maximum signal strength: {max_strength:.3f}")
        
        # Check for pattern detections
        if 'bullish_engulfing_detected' in data_with_indicators.columns:
            engulfing_patterns = data_with_indicators['bullish_engulfing_detected'].sum()
            print(f"   Bullish Engulfing patterns detected: {engulfing_patterns}")
            cdl_positive = (data_with_indicators['cdl_engulfing'] > 0).sum()
            print(f"   CDL_ENGULFING positive values: {cdl_positive}")
        
        if buy_signals > 0:
            print(f"✅ Strategy generated {buy_signals} buy signals - Ready for deployment")
        else:
            print("ℹ️  No buy signals in test data - This is normal for pattern-based strategies")
            
    except Exception as e:
        print(f"❌ Strategy test failed with error: {e}")
        import traceback
        traceback.print_exc()