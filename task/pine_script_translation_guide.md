# Pine Script to Vectorized Python Translation Guide

## Executive Summary

This guide provides comprehensive patterns for translating TradingView Pine Script indicators to vectorized Python using pandas, numpy, and TA-Lib. All implementations must work with our BacktestEngine which expects vectorized signals.

**ZEN CONTINUATION ID**: `7e4154c6-0b08-4399-a4b1-ed986fff0244`

---

## Core Translation Principles

### 1. Data Indexing Differences

| Pine Script | Python Vectorized | Notes |
|------------|------------------|-------|
| `close[0]` | `data['close'].iloc[-1]` | Current value |
| `close[1]` | `data['close'].shift(1)` | Previous value |
| `close[n]` | `data['close'].shift(n)` | n bars ago |
| `close[-n]` | Not available | No future data |

### 2. Avoid Look-Ahead Bias

**CRITICAL**: Always use `.shift(1)` when comparing current to previous values

```python
# WRONG - Look-ahead bias!
crossover = (fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma)

# CORRECT - Proper time alignment
crossover = (fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma.shift(1))
```

---

## Common Pine Script Functions → Python

### Moving Averages

```python
# Pine: ta.sma(source, length)
sma = data['close'].rolling(window=length).mean()

# Pine: ta.ema(source, length)
ema = data['close'].ewm(span=length, adjust=False).mean()
# OR using TA-Lib (more accurate to Pine)
ema = talib.EMA(data['close'].values, timeperiod=length)

# Pine: ta.rma(source, length)  [Running Moving Average]
rma = data['close'].ewm(alpha=1/length, adjust=False).mean()

# Pine: ta.wma(source, length)  [Weighted Moving Average]
wma = talib.WMA(data['close'].values, timeperiod=length)
```

### Oscillators

```python
# Pine: ta.rsi(source, length)
rsi = talib.RSI(data['close'].values, timeperiod=length)

# Pine: ta.stoch(source, high, low, length)
stoch_k, stoch_d = talib.STOCH(
    data['high'].values,
    data['low'].values,
    data['close'].values,
    fastk_period=length,
    slowk_period=3,
    slowd_period=3
)

# Pine: ta.macd(source, fast, slow, signal)
macd, signal, hist = talib.MACD(
    data['close'].values,
    fastperiod=fast,
    slowperiod=slow,
    signalperiod=signal
)
```

### Bands & Channels

```python
# Pine: ta.bb(source, length, mult)
upper, middle, lower = talib.BBANDS(
    data['close'].values,
    timeperiod=length,
    nbdevup=mult,
    nbdevdn=mult
)

# Pine: ta.kc(source, length, mult, use_true_range)
# Keltner Channels
middle = talib.EMA(data['close'].values, timeperiod=length)
atr = talib.ATR(data['high'].values, data['low'].values, data['close'].values, timeperiod=length)
upper = middle + (mult * atr)
lower = middle - (mult * atr)
```

### Volatility

```python
# Pine: ta.atr(length)
atr = talib.ATR(
    data['high'].values,
    data['low'].values,
    data['close'].values,
    timeperiod=length
)

# Pine: ta.stdev(source, length)
stdev = data['close'].rolling(window=length).std()
```

---

## Crossover/Crossunder Patterns

### Use Our Helper Functions

```python
from utils.vectorized_helpers import crossover, crossunder

# Pine: ta.crossover(series1, series2)
buy_signal = crossover(fast_ma, slow_ma)

# Pine: ta.crossunder(series1, series2)
sell_signal = crossunder(fast_ma, slow_ma)
```

---

## Complex Indicators

### 1. Bollinger Band Squeeze

```python
# Pine Script version
bb_upper, bb_middle, bb_lower = talib.BBANDS(close, 20, 2)
kc_upper = ema + 1.5 * atr
kc_lower = ema - 1.5 * atr
squeeze = (bb_lower > kc_lower) & (bb_upper < kc_upper)

# Python vectorized
def calculate_squeeze(data):
    bb_upper, bb_middle, bb_lower = talib.BBANDS(
        data['close'].values, timeperiod=20, nbdevup=2, nbdevdn=2
    )
    
    ema = talib.EMA(data['close'].values, timeperiod=20)
    atr = talib.ATR(data['high'].values, data['low'].values, 
                   data['close'].values, timeperiod=20)
    
    kc_upper = ema + (1.5 * atr)
    kc_lower = ema - (1.5 * atr)
    
    squeeze = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    return pd.Series(squeeze, index=data.index)
```

### 2. Divergence Detection

```python
def detect_divergence(price, indicator, lookback=14):
    """Detect bullish and bearish divergences"""
    
    # Find local peaks and troughs
    price_highs = price.rolling(window=lookback).max() == price
    price_lows = price.rolling(window=lookback).min() == price
    
    ind_highs = indicator.rolling(window=lookback).max() == indicator
    ind_lows = indicator.rolling(window=lookback).min() == indicator
    
    # Bullish divergence: price makes lower low, indicator makes higher low
    bullish = price_lows & (price < price.shift(lookback)) & \
              ind_lows & (indicator > indicator.shift(lookback))
    
    # Bearish divergence: price makes higher high, indicator makes lower high
    bearish = price_highs & (price > price.shift(lookback)) & \
              ind_highs & (indicator < indicator.shift(lookback))
    
    return bullish, bearish
```

---

## Signal Generation Pattern

### Standard Template

```python
def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
    # Initialize
    data['buy_signal'] = False
    data['sell_signal'] = False
    data['signal_strength'] = 0.0
    
    # Calculate conditions
    condition1 = data['rsi'] < 30
    condition2 = crossover(data['macd'], data['macd_signal'])
    condition3 = data['volume'] > data['volume_ma']
    
    # Combine conditions (AND logic)
    data['buy_signal'] = condition1 & condition2 & condition3
    
    # Calculate signal strength (0-1 scale)
    strength_factors = []
    
    # RSI contribution
    rsi_strength = (70 - data['rsi']) / 70  # Stronger when more oversold
    strength_factors.append(rsi_strength.clip(0, 1))
    
    # MACD contribution
    macd_strength = np.abs(data['macd_hist']) / data['close'] * 100
    strength_factors.append(macd_strength.clip(0, 1))
    
    # Average strength
    data['signal_strength'] = pd.concat(strength_factors, axis=1).mean(axis=1)
    
    # Apply minimum threshold
    weak_signals = data['signal_strength'] < 0.6
    data.loc[weak_signals, 'buy_signal'] = False
    
    return data
```

---

## Research Process for Missing Strategies

### When TradingView URL Has No Code

1. **Search for Pine Script Implementation**
   ```
   Search: "LazyBear [Strategy Name] Pine Script code"
   Search: "[Strategy Name] indicator TradingView source"
   Search: "[Strategy Name] formula calculation"
   ```

2. **Check GitHub**
   ```
   GitHub: "[Strategy Name] Pine Script"
   GitHub: "LazyBear indicators"
   GitHub: "TradingView strategies Python"
   ```

3. **Consult Trading Forums**
   - TradingView Ideas section
   - Pine Coders community
   - Stack Overflow trading tags

4. **Use Standard Implementation**
   If no exact implementation found, use the standard version:
   - RSI: Standard 14-period
   - MACD: 12, 26, 9 periods
   - Bollinger Bands: 20-period, 2 standard deviations
   - Stochastic: 14, 3, 3 periods

---

## Testing & Validation

### 1. Signal Validation

```python
from utils.vectorized_helpers import validate_signals

# After generating signals
validation = validate_signals(buy_signals, sell_signals)
if not validation['valid']:
    print(f"Signal issues: {validation['issues']}")
```

### 2. Backtest Verification

```python
# Quick test with sample data
engine = BacktestEngine()
results = engine.run_backtest(
    strategy,
    test_data,
    trade_amount_pct=0.5
)

# Check for reasonable metrics
assert results['total_trades'] > 0
assert results['total_return_pct'] != 0
assert results['max_drawdown_pct'] < 100
```

---

## Common Pitfalls to Avoid

### ❌ DON'T DO THIS

```python
# Direct array access (causes index errors)
if close[i] > close[i-1]:  # WRONG

# Using future data
signal = close > close.shift(-1)  # WRONG - looks ahead!

# Not handling NaN values
data['signal'] = condition1 & condition2  # May have NaN

# Iterating through rows
for i in range(len(data)):  # SLOW - avoid loops
    if data.iloc[i]['rsi'] < 30:
        signals[i] = True
```

### ✅ DO THIS INSTEAD

```python
# Vectorized comparison
condition = data['close'] > data['close'].shift(1)

# Proper time alignment
signal = data['close'] > data['close'].shift(1)

# Handle NaN values
data['signal'] = condition1 & condition2
data['signal'] = data['signal'].fillna(False)

# Vectorized operations
signals = data['rsi'] < 30  # FAST - entire column at once
```

---

## Implementation Checklist

For each LazyBear strategy implementation:

- [ ] Research actual implementation (not just TradingView URL)
- [ ] Identify core indicator calculations
- [ ] Map Pine functions to Python equivalents
- [ ] Implement using vectorized operations
- [ ] Add proper signal generation logic
- [ ] Calculate signal strength (0-1 scale)
- [ ] Test for look-ahead bias
- [ ] Validate signals have no NaN values
- [ ] Verify no simultaneous buy/sell signals
- [ ] Test with sample data
- [ ] Document any deviations from original

---

## Example: Converting a Complete Pine Script Strategy

### Pine Script Original
```pinescript
//@version=5
strategy("RSI MACD Strategy")
rsi = ta.rsi(close, 14)
[macd, signal, hist] = ta.macd(close, 12, 26, 9)

longCondition = ta.crossover(macd, signal) and rsi < 30
shortCondition = ta.crossunder(macd, signal) and rsi > 70

if (longCondition)
    strategy.entry("Long", strategy.long)
if (shortCondition)
    strategy.close("Long")
```

### Python Vectorized Translation
```python
class RSIMACDStrategy(BaseStrategy):
    def calculate_indicators(self, data):
        data['rsi'] = talib.RSI(data['close'].values, timeperiod=14)
        data['macd'], data['signal'], data['hist'] = talib.MACD(
            data['close'].values,
            fastperiod=12,
            slowperiod=26,
            signalperiod=9
        )
        return data
    
    def generate_signals(self, data):
        data['buy_signal'] = crossover(data['macd'], data['signal']) & \
                             (data['rsi'] < 30)
        
        data['sell_signal'] = crossunder(data['macd'], data['signal']) & \
                             (data['rsi'] > 70)
        
        # Signal strength based on RSI extremes
        data['signal_strength'] = 0.5
        data.loc[data['rsi'] < 20, 'signal_strength'] = 1.0
        data.loc[data['rsi'] > 80, 'signal_strength'] = 1.0
        
        return data
```

---

This guide ensures consistent, efficient translation of Pine Script strategies to our vectorized Python framework.