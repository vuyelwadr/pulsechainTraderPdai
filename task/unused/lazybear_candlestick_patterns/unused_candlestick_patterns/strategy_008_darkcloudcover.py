#!/usr/bin/env python3
"""
Strategy 008: Dark Cloud Cover Candlestick Pattern

A bearish reversal candlestick pattern that occurs after an uptrend.
The pattern consists of a bullish candle followed by a bearish candle that:
1. Opens above the previous candle's high
2. Closes below the midpoint of the previous candle's body

This implementation uses TA-Lib's CDLDARKCLOUDCOVER function for pattern detection.

Strategy Number: 003
LazyBear Name: Dark Cloud Cover
Type: candlestick/reversal
TradingView URL: https://www.tradingview.com/v/h7CaKwlf/

Description:
Simple Dark Cloud Cover pattern detection using TA-Lib with no additional filters.
Generates sell signals when the bearish pattern is detected.
"""

import pandas as pd
import numpy as np
import talib
from typing import Dict
import sys
import os

# Add repository root to path for imports
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, repo_root)
from strategies.base_strategy import BaseStrategy


class Strategy008Darkcloudcover(BaseStrategy):
    """
    Strategy 008: Dark Cloud Cover Candlestick Pattern
    
    Simple implementation that detects Dark Cloud Cover pattern using TA-Lib.
    No additional filters or parameters - pure pattern recognition.
    """
    
    def __init__(self, parameters: Dict = None):
        """
        Initialize strategy with empty parameters (no optimization parameters)
        
        Args:
            parameters: Dictionary of strategy parameters (should be empty for candlestick patterns)
        """
        # Empty parameters - no optimizable parameters for simple candlestick patterns
        default_params = {}
        
        # Merge with provided parameters (should be empty)
        if parameters:
            default_params.update(parameters)
        
        # Initialize parent class
        super().__init__(
            name="Strategy_008_Darkcloudcover",
            parameters=default_params
        )
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the Dark Cloud Cover pattern using TA-Lib
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            DataFrame with Dark Cloud Cover indicator column
        """
        # Ensure we have required columns
        if 'close' not in data.columns and 'price' in data.columns:
            data['close'] = data['price']
        
        # Ensure we have OHLC data
        if 'open' not in data.columns:
            data['open'] = data['close'].shift(1).fillna(data['close'])
        if 'high' not in data.columns:
            data['high'] = data['close']
        if 'low' not in data.columns:
            data['low'] = data['close']
        
        # Calculate Dark Cloud Cover pattern using TA-Lib
        # Returns: -100 for bearish pattern, 0 for no pattern, 100 for bullish (rare)
        # Using default penetration of 0.5 (50% into previous candle body)
        data['CDL_DARKCLOUDCOVER'] = talib.CDLDARKCLOUDCOVER(
            data['open'].astype(np.float64).values,
            data['high'].astype(np.float64).values,
            data['low'].astype(np.float64).values,
            data['close'].astype(np.float64).values,
            penetration=0.5
        )
        
        return data
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate sell signals based on Dark Cloud Cover pattern detection
        
        Args:
            data: DataFrame with price and indicator data
            
        Returns:
            DataFrame with buy_signal, sell_signal, and signal_strength columns
        """
        # Initialize signal columns
        data['buy_signal'] = False
        data['sell_signal'] = False
        data['signal_strength'] = 0.0
        
        # Identify Dark Cloud Cover patterns (-100 indicates bearish pattern)
        dark_cloud_cover_signal = (data['CDL_DARKCLOUDCOVER'] < 0)
        
        # --- State Management (simplified from Turn 85 blueprint) ---
        # Create a unified raw signal series: +1 for potential buy, -1 for potential sell
        # For Dark Cloud Cover, we're only interested in sell signals
        raw_signal = np.select(
            [dark_cloud_cover_signal],
            [-1],  # -1 for sell signal
            default=0
        )

        # Calculate the position state column based on raw signals.
        # A non-zero signal flips the position. ffill() holds it until the next signal.
        # Use .shift(1) to ensure the position is based on *previous* bar's state.
        position = pd.Series(raw_signal).replace(0, np.nan).ffill().fillna(0)
        is_flat = (position.shift(1) == 0)

        # Refine signals based on state to prevent opening multiple positions
        # Only allow a sell if currently flat (no open position)
        data['sell_signal'] = dark_cloud_cover_signal & is_flat
        
        # Set fixed signal strength for bearish pattern
        data.loc[data['sell_signal'], 'signal_strength'] = -1.0

        return data
    
    def validate_signals(self, data: pd.DataFrame) -> bool:
        """
        Validate that signals are properly formed
        
        Returns:
            True if signals are valid, False otherwise
        """
        # Check for required columns
        required = ['buy_signal', 'sell_signal', 'signal_strength']
        if not all(col in data.columns for col in required):
            return False
        
        # Check for NaN values
        if data[required].isna().any().any():
            return False
        
        # Check for simultaneous buy and sell signals
        simultaneous = (data['buy_signal'] & data['sell_signal']).any()
        if simultaneous:
            return False
        
        # Check signal strength is in valid range (allowing negative for bearish)
        if (data['signal_strength'] < -1).any() or (data['signal_strength'] > 1).any():
            return False
        
        # For Dark Cloud Cover, we should only have sell signals
        if data['buy_signal'].any():
            print("Warning: Dark Cloud Cover generated buy signals (unexpected)")
        
        return True


if __name__ == "__main__":
    # Test the strategy with sample data
    
    # Create realistic OHLC data that includes some Dark Cloud Cover patterns
    np.random.seed(42)  # For reproducible results
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='1h')
    n = len(dates)
    
    # Generate trending data with some reversals
    base_price = 100
    trend = np.linspace(0, 10, n)  # Upward trend
    noise = np.random.randn(n).cumsum() * 0.2
    closes = base_price + trend + noise
    
    # Create OHLC data with realistic relationships
    opens = np.roll(closes, 1)
    opens[0] = base_price
    
    # Manually create some Dark Cloud Cover patterns
    dcc_indices = [100, 200, 300, 400]  # Indices where we'll force patterns
    for idx in dcc_indices:
        if idx < n - 1:
            # Day 1: Strong bullish candle
            opens[idx] = closes[idx-1] if idx > 0 else base_price
            closes[idx] = opens[idx] + 2.0  # Strong up move
            
            # Day 2: Dark Cloud Cover - opens above high, closes below midpoint
            midpoint = (opens[idx] + closes[idx]) / 2
            opens[idx+1] = closes[idx] + 0.5  # Gap up opening
            closes[idx+1] = midpoint - 0.3   # Close below midpoint
    
    # Calculate highs and lows ensuring OHLC consistency
    highs = np.maximum(opens, closes)
    lows = np.minimum(opens, closes)
    
    # Add some wicks
    highs += np.random.exponential(0.2, n)
    lows -= np.random.exponential(0.2, n)
    
    # Ensure Dark Cloud Cover patterns have correct high/low relationships
    for idx in dcc_indices:
        if idx < n - 1:
            # Ensure the opening gap is reflected in the high
            highs[idx+1] = max(highs[idx+1], opens[idx+1])
    
    # Generate volume
    volumes = np.random.exponential(10000, n)
    
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'price': closes,  # For compatibility
        'volume': volumes
    })
    
    # Test strategy
    print("Testing Strategy 008: Dark Cloud Cover (Simplified)")
    print("=" * 60)
    
    try:
        strategy = Strategy003DarkCloudCover()
        print(f"✅ Strategy initialized: {strategy.name}")
        print(f"Parameters: {strategy.parameters}")
        
        # Calculate indicators
        data_with_indicators = strategy.calculate_indicators(sample_data.copy())
        print(f"✅ Indicators calculated. Shape: {data_with_indicators.shape}")
        
        # Show pattern detection stats
        dcc_patterns = (data_with_indicators['CDL_DARKCLOUDCOVER'] < 0).sum()
        print(f"Dark Cloud Cover patterns detected: {dcc_patterns}")
        
        # Generate signals
        data_with_signals = strategy.generate_signals(data_with_indicators)
        print(f"✅ Signals generated. Shape: {data_with_signals.shape}")
        
        # Validate signals
        if strategy.validate_signals(data_with_signals):
            print("✅ Signal validation passed")
            
            buy_signals = data_with_signals['buy_signal'].sum()
            sell_signals = data_with_signals['sell_signal'].sum()
            avg_strength = data_with_signals['signal_strength'].abs().mean()
            
            print(f"Buy signals: {buy_signals}")
            print(f"Sell signals: {sell_signals}")
            print(f"Average signal strength: {avg_strength:.3f}")
            
            # Show actual signals generated
            if sell_signals > 0:
                signal_rows = data_with_signals[data_with_signals['sell_signal']]
                print(f"\nActual sell signals generated:")
                cols = ['timestamp', 'open', 'high', 'low', 'close', 'CDL_DARKCLOUDCOVER', 'sell_signal', 'signal_strength']
                print(signal_rows[cols])
            
            print("\n✅ Strategy 003 simplified implementation completed successfully")
            
        else:
            print("❌ Signal validation failed")
            
    except Exception as e:
        print(f"❌ Strategy test failed: {e}")
        import traceback
        traceback.print_exc()