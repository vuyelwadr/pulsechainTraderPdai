#!/usr/bin/env python3
"""
Strategy 022: Piercing Line Candlestick Pattern

LazyBear Strategy Number: 004 (Original)
Strategy ID: 022 (Canonical)
LazyBear Name: Piercing Line
Type: candlestick/reversal
TradingView URL: https://www.tradingview.com/v/cqDroCxc/ (referenced)

Description:
Identifies the Piercing Line candlestick pattern using TA-Lib.
This is a two-candle bullish reversal pattern:
1. A long bearish candle.
2. A bullish candle that opens below the low of the first candle and closes
   more than halfway up the body of the first candle, but not above its open.
It signals a potential reversal to the upside.
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


class Strategy022Piercing(BaseStrategy):
    """
    Strategy 022: Piercing Line Candlestick Pattern

    Identifies the Piercing Line candlestick pattern using TA-Lib.
    This is a two-candle bullish reversal pattern that signals a potential reversal to the upside.
    """

    def __init__(self, parameters: dict = None):
        """
        Initializes the strategy with data and parameters.
        For this pattern, there are no optimizable parameters.
        """
        if parameters is None:
            parameters = {}
        super().__init__(
            name="Strategy_022_Piercing",
            parameters=parameters
        )

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the Piercing Line pattern using TA-Lib.
        The 'CDL_PIERCING' column will contain 100 for the pattern.
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

        # Calculate Piercing Line candlestick pattern using TA-Lib directly
        # Returns +100 for piercing line pattern, 0 for no pattern
        data['CDL_PIERCING'] = talib.CDLPIERCING(
            data['open'].astype(float).to_numpy(),
            data['high'].astype(float).to_numpy(),
            data['low'].astype(float).to_numpy(),
            data['close'].astype(float).to_numpy()
        )
        
        # Identify piercing line pattern (positive values indicate bullish piercing)
        data['piercing_line_detected'] = data['CDL_PIERCING'] > 0
        
        # Store indicators for debugging
        self.indicators = data[['CDL_PIERCING', 'piercing_line_detected']].copy()
        
        return data

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate buy/sell signals based on Piercing Line pattern with state management

        Args:
            data: DataFrame with price and indicator data
            
        Returns:
            DataFrame with buy_signal, sell_signal, and signal_strength columns
        """
        # Initialize signal columns
        data['buy_signal'] = False
        data['sell_signal'] = False
        data['signal_strength'] = 0.0
        
        # Primary condition: Piercing Line pattern detected
        piercing_line_signal = data['piercing_line_detected']
        
        # Create a unified raw signal series: +1 for potential buy
        # For a Piercing Line, we're primarily interested in buy signals
        raw_signal = np.where(piercing_line_signal, 1, 0)
        
        # Calculate the position state column based on raw signals
        # A non-zero signal flips the position. ffill() holds it until the next signal
        # Use .shift(1) to ensure the position is based on *previous* bar's state
        position = pd.Series(raw_signal, index=data.index).replace(0, np.nan).ffill().fillna(0)
        is_flat = (position.shift(1) == 0)
        
        # Only allow a buy signal if currently flat (no open position)
        # Apply look-ahead bias prevention using shift(1)
        combined_signal = (piercing_line_signal & is_flat).shift(1)
        data['buy_signal'] = combined_signal.fillna(False).infer_objects(copy=False).astype(bool)
        
        # Set signal strength to 1.0 for detected patterns
        data.loc[data['buy_signal'], 'signal_strength'] = 1.0

        # Store signals for debugging
        self.signals = data[['buy_signal', 'sell_signal', 'signal_strength']].copy()

        return data


# Test the strategy with sample data when run directly
if __name__ == "__main__":
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    
    # Create sample data with some realistic OHLC patterns for Piercing Line
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='5min')
    n_periods = len(dates)
    
    # Generate sample OHLC data
    np.random.seed(42)
    base_price = 100
    price_changes = np.random.normal(-0.001, 0.02, n_periods)  # Slight downward bias
    prices = [base_price]
    
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 50))  # Prevent negative prices
    
    # Create OHLC from the price series
    sample_data = pd.DataFrame({
        'timestamp': dates,
        'close': prices
    })
    
    # Generate OHLC data
    sample_data['open'] = sample_data['close'].shift(1).fillna(sample_data['close'].iloc[0])
    sample_data['high'] = sample_data[['open', 'close']].max(axis=1) * (1 + np.random.uniform(0, 0.01, n_periods))
    sample_data['low'] = sample_data[['open', 'close']].min(axis=1) * (1 - np.random.uniform(0, 0.01, n_periods))
    sample_data['volume'] = np.random.randint(1000, 10000, n_periods)
    sample_data['price'] = sample_data['close']
    
    # Manually insert a few potential Piercing Line patterns
    idx1 = n_periods // 3
    sample_data.loc[idx1, 'open'] = sample_data.loc[idx1, 'close'] * 1.02
    sample_data.loc[idx1, 'close'] = sample_data.loc[idx1, 'close'] * 0.98
    sample_data.loc[idx1, 'low'] = sample_data.loc[idx1, 'close'] * 0.99
    
    sample_data.loc[idx1+1, 'open'] = sample_data.loc[idx1, 'low'] * 0.99
    sample_data.loc[idx1+1, 'close'] = sample_data.loc[idx1, 'open'] * 0.999  # Close above midpoint
    sample_data.loc[idx1+1, 'high'] = sample_data.loc[idx1+1, 'close'] * 1.001
    
    # Update price and high/low consistency
    sample_data['price'] = sample_data['close']
    sample_data['high'] = np.maximum(sample_data['high'], sample_data[['open', 'close']].max(axis=1))
    sample_data['low'] = np.minimum(sample_data['low'], sample_data[['open', 'close']].min(axis=1))
    
    # Test strategy
    print("Testing Strategy 022: Piercing Line Candlestick Pattern")
    print("=" * 60)
    
    try:
        strategy = Strategy004PiercingLine()
        data_with_indicators = strategy.calculate_indicators(sample_data.copy())
        data_with_signals = strategy.generate_signals(data_with_indicators)
        
        # Simple validation
        required = ['buy_signal', 'sell_signal', 'signal_strength']
        validation_result = all(col in data_with_signals.columns for col in required)
        
        if validation_result:
            print("✅ Strategy validation passed")
            
            # Display results
            buy_signals = data_with_signals['buy_signal'].sum()
            sell_signals = data_with_signals['sell_signal'].sum()
            avg_strength = data_with_signals['signal_strength'].mean()
            piercing_patterns = data_with_indicators['CDL_PIERCING'].gt(0).sum() if 'CDL_PIERCING' in data_with_indicators else 0
            
            print(f"📊 Results:")
            print(f"   • Piercing Line patterns detected: {piercing_patterns}")
            print(f"   • Buy signals generated: {buy_signals}")
            print(f"   • Sell signals generated: {sell_signals}")
            print(f"   • Average signal strength: {avg_strength:.3f}")
            
            # Show pattern details
            if piercing_patterns > 0:
                pattern_rows = data_with_indicators[data_with_indicators['CDL_PIERCING'] > 0]
                print(f"\n📈 Piercing Line Pattern Details:")
                for idx, row in pattern_rows.head(3).iterrows():  # Show first 3 patterns
                    print(f"   • {row['timestamp']}: CDL_PIERCING = {row['CDL_PIERCING']}")
            
            # Show signal details
            if buy_signals > 0:
                signal_rows = data_with_signals[data_with_signals['buy_signal']]
                print(f"\n🔥 Buy Signal Details:")
                for idx, row in signal_rows.head(3).iterrows():  # Show first 3 signals
                    print(f"   • {row['timestamp']}: Strength = {row['signal_strength']:.3f}")
        else:
            print("❌ Strategy validation failed")
            
    except Exception as e:
        print(f"❌ Error testing strategy: {e}")
        import traceback
        traceback.print_exc()