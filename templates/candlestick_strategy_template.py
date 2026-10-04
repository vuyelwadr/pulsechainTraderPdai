#!/usr/bin/env python3
"""
Candlestick Strategy Template

A specialized template for TA-Lib candlestick pattern strategies.
This template provides standardized state management, signal generation,
and validation logic specifically optimized for binary candlestick patterns.

Features:
- Enhanced state management with prev_position logic for look-ahead bias prevention
- Fixed signal_strength = 1.0 for all detected patterns (appropriate for binary detection)
- Bidirectional signal handling for patterns that can be both bullish and bearish
- Consistent validation logic across all candlestick strategies
- Empty parameters dictionary standard (candlestick patterns have no optimizable parameters)
"""

import pandas as pd
import numpy as np
import sys
import os
from abc import abstractmethod

# Add parent directories to path for imports
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, repo_root)
from strategies.base_strategy import BaseStrategy


class CandlestickStrategyTemplate(BaseStrategy):
    """
    Base template for all TA-Lib candlestick pattern strategies
    
    This template handles the common logic for:
    - State management with look-ahead bias prevention
    - Signal generation based on pattern detection
    - Fixed signal strength for binary patterns
    - Validation of signals
    
    Derived classes only need to implement calculate_indicators() to:
    1. Calculate the candlestick pattern using appropriate talib.CDL* function
    2. Set bullish_pattern_detected and bearish_pattern_detected boolean columns
    """

    def __init__(self, name: str, parameters=None):
        """
        Initialize candlestick strategy with standardized parameters
        
        Args:
            name: Strategy name (e.g., "Strategy_001_3_Line_Strike")
            parameters: Should be empty dict for candlestick patterns
        """
        if parameters is None:
            parameters = {}
        
        # Initialize parent class
        super().__init__(name=name, parameters=parameters)

    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate candlestick pattern indicators using TA-Lib
        
        Derived classes must implement this method to:
        1. Ensure OHLC data is available (with fallback logic)
        2. Call appropriate talib.CDL* function
        3. Set boolean columns: 'bullish_pattern_detected' and 'bearish_pattern_detected'
        
        Args:
            data: DataFrame with OHLC data
            
        Returns:
            DataFrame with pattern detection columns added
        """
        pass

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate buy/sell signals based on detected candlestick patterns.
        Uses standardized bidirectional signal logic with enhanced state management.

        CRITICAL: Applies look-ahead bias prevention using prev_position logic.
        """
        # Initialize signal columns
        data['buy_signal'] = False
        data['sell_signal'] = False
        data['signal_strength'] = 0.0

        # Ensure pattern detection columns exist
        if 'bullish_pattern_detected' not in data.columns:
            data['bullish_pattern_detected'] = False
        if 'bearish_pattern_detected' not in data.columns:
            data['bearish_pattern_detected'] = False

        # --- Enhanced State Management ---
        # This is crucial for preventing look-ahead bias.
        # It ensures we only take a new position if we are changing states.

        # Create a unified raw signal series: +1 for buy, -1 for sell
        raw_signal = np.select(
            [data['bullish_pattern_detected'], data['bearish_pattern_detected']],
            [1, -1],  # +1 for buy signal, -1 for sell signal
            default=0
        )

        # Calculate the position state column based on raw signals.
        # A non-zero signal flips the position. ffill() holds it until the next signal.
        position = pd.Series(raw_signal, index=data.index).replace(0, np.nan).ffill().fillna(0)
        
        # Determine the previous bar's state to identify changes. This is key for preventing look-ahead bias.
        prev_position = position.shift(1).fillna(0)

        # A buy signal occurs when our state changes TO long (1) FROM not-long (0 or -1).
        # A sell signal occurs when our state changes TO short (-1) FROM not-short (0 or 1).
        data.loc[(position == 1) & (prev_position != 1), 'buy_signal'] = True
        data.loc[(position == -1) & (prev_position != -1), 'sell_signal'] = True

        # Set signal strength for the active signals
        # For binary candlestick patterns, strength is always 1.0 when pattern is detected
        data.loc[data['buy_signal'], 'signal_strength'] = 1.0
        data.loc[data['sell_signal'], 'signal_strength'] = 1.0

        return data

    def validate_signals(self, data: pd.DataFrame) -> bool:
        """
        Validate that signals are properly formed according to candlestick strategy standards
        
        Returns:
            True if signals are valid, False otherwise
        """
        # Check for required columns
        required = ['buy_signal', 'sell_signal', 'signal_strength']
        if not all(col in data.columns for col in required):
            return False
        
        # Check for NaN values in signal columns
        if data[required].isna().any().any():
            return False
        
        # Check for simultaneous buy and sell signals
        simultaneous = (data['buy_signal'] & data['sell_signal']).any()
        if simultaneous:
            return False
        
        # Check signal strength is in valid range (positive only for candlestick patterns)
        if (data['signal_strength'] < 0).any() or (data['signal_strength'] > 1).any():
            return False
        
        return True

    def ensure_ohlc_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Utility method to ensure OHLC data is available with fallback logic
        
        Args:
            data: Input DataFrame
            
        Returns:
            DataFrame with guaranteed OHLC columns
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
            
        return data


# Example implementation showing how to use the template
class ExampleCandlestickStrategy(CandlestickStrategyTemplate):
    """
    Example implementation of the candlestick template
    This shows the pattern for implementing any TA-Lib candlestick strategy
    """
    
    def __init__(self, parameters=None):
        super().__init__(
            name="Example_Candlestick_Strategy",
            parameters=parameters
        )
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Example implementation - replace with specific TA-Lib function
        """
        import talib
        
        # Ensure OHLC data is available
        data = self.ensure_ohlc_data(data)
        
        # Example: Calculate Hammer pattern using TA-Lib
        # Replace talib.CDLHAMMER with appropriate function for your pattern
        pattern_values = talib.CDLHAMMER(
            data['open'].to_numpy(),
            data['high'].to_numpy(),
            data['low'].to_numpy(),
            data['close'].to_numpy()
        )
        
        # Set pattern detection columns based on TA-Lib return values
        # Most TA-Lib candlestick functions return: +100 for bullish, -100 for bearish, 0 for no pattern
        data['bullish_pattern_detected'] = (pattern_values > 0)
        data['bearish_pattern_detected'] = (pattern_values < 0)
        
        return data


if __name__ == "__main__":
    """Test the candlestick template with example implementation"""
    
    # Create sample OHLC data
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='5min')
    n_points = len(dates)
    
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
    
    # Ensure OHLC consistency
    sample_data['high'] = sample_data[['open', 'close', 'high']].max(axis=1)
    sample_data['low'] = sample_data[['open', 'close', 'low']].min(axis=1)
    sample_data['price'] = sample_data['close']
    
    print("🔍 Testing Candlestick Strategy Template")
    print(f"Sample data shape: {sample_data.shape}")
    
    try:
        # Test example strategy
        strategy = ExampleCandlestickStrategy()
        print("✅ Template initialization successful")
        
        # Test indicator calculation
        data_with_indicators = strategy.calculate_indicators(sample_data.copy())
        print(f"✅ Indicator calculation successful")
        
        # Test signal generation
        data_with_signals = strategy.generate_signals(data_with_indicators)
        print("✅ Signal generation successful")
        
        # Validate signals
        if strategy.validate_signals(data_with_signals):
            print("✅ Signal validation passed")
            
            # Print summary statistics
            buy_signals = data_with_signals['buy_signal'].sum()
            sell_signals = data_with_signals['sell_signal'].sum()
            total_patterns = (data_with_signals['bullish_pattern_detected'] | 
                            data_with_signals['bearish_pattern_detected']).sum()
            
            print(f"📊 Template Test Results:")
            print(f"   Total patterns detected: {total_patterns}")
            print(f"   Buy signals generated: {buy_signals}")
            print(f"   Sell signals generated: {sell_signals}")
            print(f"✅ Candlestick template working correctly!")
            
        else:
            print("❌ Signal validation failed")
            
    except Exception as e:
        print(f"❌ Template test failed: {e}")
        import traceback
        traceback.print_exc()