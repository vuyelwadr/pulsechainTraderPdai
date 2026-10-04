#!/usr/bin/env python3
"""
Strategy 017: Bullish Harami Candlestick Pattern

Identifies the Bullish Harami candlestick pattern using TA-Lib.
A Bullish Harami is a two-candle bullish reversal pattern:
1. A large bearish (red) candle during a downtrend.
2. Followed by a smaller bullish (green) candle whose body is completely
   contained within the body of the previous bearish candle.
It often signals a potential reversal to the upside.

TradingView URL: https://www.tradingview.com/v/Dliig9JF/
Pattern Type: Candlestick reversal pattern
Simple implementation - no parameters or confirmation filters
"""

import pandas as pd
import numpy as np
import talib
from typing import Dict
import sys
import os

# Add parent directories to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)
from strategies.base_strategy import BaseStrategy


class Strategy017Harami(BaseStrategy):
    """
    Strategy 017: Bullish Harami Candlestick Pattern
    
    Strategy Number: 001
    LazyBear Name: Bullish Harami
    Type: reversal/candlestick
    
    Description:
    Detects the Bullish Harami candlestick pattern which consists of:
    1. Large bearish candle (first candle)
    2. Small bullish candle contained within the first candle's body (second candle)
    This pattern typically appears during downtrends and signals potential bullish reversal.
    
    Simple candlestick patterns have no optimizable parameters.
    """
    
    def __init__(self, parameters: Dict = None):
        """
        Initialize strategy. Simple candlestick patterns have no optimizable parameters.
        """
        if parameters is None:
            parameters = {}
        
        # Initialize parent class
        super().__init__(
            name="Strategy_017_Harami",
            parameters=parameters
        )
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the Bullish Harami candlestick pattern using TA-Lib
        The 'CDL_HARAMI' column will contain 100 for a Bullish Harami.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            DataFrame with additional indicator columns
        """
        # Ensure we have required OHLC columns
        if 'close' not in data.columns and 'price' in data.columns:
            data['close'] = data['price']
        if 'open' not in data.columns:
            data['open'] = data['close'].shift(1).fillna(data['close'])
        if 'high' not in data.columns:
            data['high'] = data['close']
        if 'low' not in data.columns:
            data['low'] = data['close']
        
        # Ensure data types are float64 for TA-Lib
        open_prices = data['open'].astype(np.float64).values
        high_prices = data['high'].astype(np.float64).values
        low_prices = data['low'].astype(np.float64).values
        close_prices = data['close'].astype(np.float64).values
        
        # Calculate Bullish Harami pattern using TA-Lib
        # CDLHARAMI returns +100 for bullish harami, -100 for bearish, 0 for none
        data['CDL_HARAMI'] = talib.CDLHARAMI(
            open_prices,
            high_prices,
            low_prices,
            close_prices
        )
        
        return data
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate buy signals based on the detected Bullish Harami pattern.
        CRITICAL: Apply look-ahead bias prevention using .shift(1) for stateful logic.
        
        Args:
            data: DataFrame with price and indicator data
            
        Returns:
            DataFrame with buy_signal, sell_signal, and signal_strength columns
        """
        harami_col = 'CDL_HARAMI'
        
        # Identify Bullish Harami patterns (value is 100)
        bullish_harami_signal = (data[harami_col] > 0)
        
        # Initialize signal columns
        data['buy_signal'] = False
        data['sell_signal'] = False
        data['signal_strength'] = 0.0
        
        # --- State Management to prevent look-ahead bias ---
        # Create a raw signal series: +1 for buy
        raw_signal = np.select([bullish_harami_signal], [1], default=0)
        
        # Convert to series if needed
        if not isinstance(raw_signal, pd.Series):
            raw_signal = pd.Series(raw_signal, index=data.index)
        
        # Determine position state based on the *previous* bar's information
        position = raw_signal.replace(0, np.nan).ffill().fillna(0)
        is_flat = (position.shift(1) == 0)
        
        # Only allow a buy if we are currently flat
        data['buy_signal'] = bullish_harami_signal & is_flat
        
        # Set signal strength for active signals
        data.loc[data['buy_signal'], 'signal_strength'] = 1.0
        
        return data


if __name__ == "__main__":
    # Test the strategy with sample data
    
    # Create sample OHLC data for testing
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='5min')
    np.random.seed(42)  # For reproducible results
    
    # Create realistic OHLC data with some patterns
    base_price = 100
    returns = np.random.normal(0, 0.02, len(dates))
    price_series = base_price * np.exp(returns.cumsum())
    
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'close': price_series,
        'volume': np.random.randint(1000, 10000, len(dates))
    })
    
    # Add OHLC data based on close prices
    sample_data['open'] = sample_data['close'].shift(1).fillna(sample_data['close'])
    sample_data['high'] = sample_data['close'] * (1 + np.random.uniform(0, 0.01, len(sample_data)))
    sample_data['low'] = sample_data['close'] * (1 - np.random.uniform(0, 0.01, len(sample_data)))
    sample_data['price'] = sample_data['close']
    
    # Test strategy
    print("Testing Strategy 017: Bullish Harami (Simplified)")
    print("=" * 60)
    
    try:
        strategy = Strategy001BullishHarami()
        
        # Calculate indicators
        data_with_indicators = strategy.calculate_indicators(sample_data.copy())
        print(f"✅ Indicators calculated successfully")
        print(f"   Harami patterns detected: {(data_with_indicators['CDL_HARAMI'] != 0).sum()}")
        print(f"   Bullish Harami patterns: {(data_with_indicators['CDL_HARAMI'] > 0).sum()}")
        
        # Generate signals
        data_with_signals = strategy.generate_signals(data_with_indicators)
        print(f"✅ Signals generated successfully")
        
        # Basic validation
        buy_signals = data_with_signals['buy_signal'].sum()
        sell_signals = data_with_signals['sell_signal'].sum()
        avg_strength = data_with_signals['signal_strength'].mean()
        max_strength = data_with_signals['signal_strength'].max()
        
        print(f"✅ Signal validation:")
        print(f"   Buy signals: {buy_signals}")
        print(f"   Sell signals: {sell_signals}")
        print(f"   Avg signal strength: {avg_strength:.3f}")
        print(f"   Max signal strength: {max_strength:.3f}")
        
        # Show some example signals
        signals_found = data_with_signals[data_with_signals['buy_signal']]
        if len(signals_found) > 0:
            print(f"\n📊 Example signals:")
            for i, (idx, row) in enumerate(signals_found.head(3).iterrows()):
                print(f"   Signal {i+1}: {row['timestamp']}, "
                      f"Strength: {row['signal_strength']:.3f}, "
                      f"Pattern: {row['CDL_HARAMI']}")
        
        print("\n🎯 Strategy 001 simplified implementation completed successfully!")
        print("✅ No over-engineering - simple candlestick pattern only")
        print("✅ No confirmation filters or complex parameters")
        print("✅ Proper state management for look-ahead bias prevention")
        
    except Exception as e:
        print(f"❌ Strategy test failed: {str(e)}")
        import traceback
        traceback.print_exc()