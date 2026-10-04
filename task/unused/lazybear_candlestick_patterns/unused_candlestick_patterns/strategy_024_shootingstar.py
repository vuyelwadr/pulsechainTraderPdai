#!/usr/bin/env python3
"""
Strategy 024: Shooting Star Candlestick Pattern

A bearish reversal candlestick pattern that occurs after an uptrend.
The pattern consists of a single candle with:
1. A small real body near the low of the day
2. A long upper shadow (at least twice the size of the real body)
3. Little or no lower shadow

This implementation uses TA-Lib's CDLSHOOTINGSTAR function for pattern detection.

Strategy Number: 009
LazyBear Name: Shooting Star
Type: candlestick/reversal
TradingView URL: https://www.tradingview.com/script/[shooting_star_url]/

Description:
Simple Shooting Star pattern detection using TA-Lib with no additional filters.
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


class Strategy024Shootingstar(BaseStrategy):
    """
    Strategy 024: Shooting Star Candlestick Pattern
    
    Simple implementation that detects Shooting Star pattern using TA-Lib.
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
            name="Strategy_024_Shootingstar",
            parameters=default_params
        )
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the Shooting Star pattern using TA-Lib
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            DataFrame with Shooting Star indicator column
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
        
        # Calculate Shooting Star pattern using TA-Lib
        # Returns: -100 for bearish pattern, 0 for no pattern, 100 for bullish (rare)
        data['CDL_SHOOTINGSTAR'] = talib.CDLSHOOTINGSTAR(
            data['open'].to_numpy(),
            data['high'].to_numpy(),
            data['low'].to_numpy(),
            data['close'].to_numpy()
        )
        
        return data
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate sell signals based on Shooting Star pattern detection
        
        Args:
            data: DataFrame with price and indicator data
            
        Returns:
            DataFrame with buy_signal, sell_signal, and signal_strength columns
        """
        # Initialize signal columns
        data['buy_signal'] = False
        data['sell_signal'] = False
        data['signal_strength'] = 0.0
        
        # Identify Shooting Star patterns (-100 indicates bearish pattern)
        shooting_star_signal = (data['CDL_SHOOTINGSTAR'] < 0)
        
        # --- State Management (simplified blueprint) ---
        # Create a unified raw signal series: +1 for potential buy, -1 for potential sell
        # For Shooting Star, we're only interested in sell signals
        raw_signal = np.select(
            [shooting_star_signal],
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
        data['sell_signal'] = shooting_star_signal & is_flat
        
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
        
        # For Shooting Star, we should only have sell signals
        if data['buy_signal'].any():
            print("Warning: Shooting Star generated buy signals (unexpected)")
        
        return True


if __name__ == "__main__":
    # Test the strategy with sample data
    
    # Create realistic OHLC data that includes some Shooting Star patterns
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
    
    # Manually create some Shooting Star patterns
    ss_indices = [100, 200, 300, 400]  # Indices where we'll force patterns
    for idx in ss_indices:
        if idx < n:
            # Shooting Star: small body near low, long upper shadow
            body_size = 0.3
            upper_shadow = 2.0  # Long upper shadow
            
            # Set open and close to create small body near low
            opens[idx] = closes[idx-1] if idx > 0 else base_price
            closes[idx] = opens[idx] + body_size  # Small bullish body
            
            # Set high to create long upper shadow
            # Set low close to open/close (small lower shadow)
    
    # Calculate highs and lows ensuring OHLC consistency
    highs = np.maximum(opens, closes)
    lows = np.minimum(opens, closes)
    
    # Add some wicks and adjust for Shooting Star patterns
    highs += np.random.exponential(0.2, n)
    lows -= np.random.exponential(0.1, n)
    
    # Ensure Shooting Star patterns have correct relationships
    for idx in ss_indices:
        if idx < n:
            # Long upper shadow (high well above body)
            body_top = max(opens[idx], closes[idx])
            highs[idx] = body_top + 2.0  # Long upper shadow
            
            # Small or no lower shadow
            body_bottom = min(opens[idx], closes[idx])
            lows[idx] = body_bottom - 0.1  # Small lower shadow
    
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
    print("Testing Strategy 024: Shooting Star (Simplified)")
    print("=" * 60)
    
    try:
        strategy = Strategy009ShootingStar()
        print(f"✅ Strategy initialized: {strategy.name}")
        print(f"Parameters: {strategy.parameters}")
        
        # Calculate indicators
        data_with_indicators = strategy.calculate_indicators(sample_data.copy())
        print(f"✅ Indicators calculated. Shape: {data_with_indicators.shape}")
        
        # Show pattern detection stats
        ss_patterns = (data_with_indicators['CDL_SHOOTINGSTAR'] < 0).sum()
        print(f"Shooting Star patterns detected: {ss_patterns}")
        
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
                cols = ['timestamp', 'open', 'high', 'low', 'close', 'CDL_SHOOTINGSTAR', 'sell_signal', 'signal_strength']
                print(signal_rows[cols])
            
            print("\n✅ Strategy 009 simplified implementation completed successfully")
            
        else:
            print("❌ Signal validation failed")
            
    except Exception as e:
        print(f"❌ Strategy test failed: {e}")
        import traceback
        traceback.print_exc()