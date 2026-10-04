# Agent 10 - Stage 1 Testing Results

**Testing Completed:** 2025-09-11T18:00:04.084970
**Strategies Tested:** [96, 97, 98, 99, 100, 101, 102, 103, 104, 105]
**Timeframes:** ['5min', '15min', '30min', '1h', '2h', '4h', '8h', '16h', '1d']
**Total Tests:** 90
**Successful Tests:** 23
**Failed Tests:** 67

## Top 10 Performers by CPS Score

1. **Strategy 98** (8h) - CPS: 98.33, Return: 4.80%, Max DD: 3.15%
2. **Strategy 104** (4h) - CPS: 98.33, Return: 1.37%, Max DD: 4.26%
3. **Strategy 98** (16h) - CPS: 95.50, Return: 5.95%, Max DD: 1.74%
4. **Strategy 100** (30min) - CPS: 95.50, Return: 8.20%, Max DD: 2.33%
5. **Strategy 100** (1h) - CPS: 95.50, Return: 1.70%, Max DD: 2.03%
6. **Strategy 101** (8h) - CPS: 95.50, Return: 2.66%, Max DD: 0.89%
7. **Strategy 101** (1d) - CPS: 95.50, Return: 1.29%, Max DD: 0.27%
8. **Strategy 104** (8h) - CPS: 95.50, Return: 7.41%, Max DD: 3.39%
9. **Strategy 104** (16h) - CPS: 95.50, Return: 6.29%, Max DD: 0.67%
10. **Strategy 100** (15min) - CPS: 95.00, Return: 6.31%, Max DD: 5.07%

## Key Insights

### Unexpected Winners
- **Strategy_98** (8h): High CPS (98.33) despite modest return (4.80%) - excellent capital preservation
- **Strategy_104** (4h): High CPS (98.33) despite modest return (1.37%) - excellent capital preservation
- **Strategy_100** (1h): High CPS (95.5) despite modest return (1.70%) - excellent capital preservation
- **Strategy_101** (8h): High CPS (95.5) despite modest return (2.66%) - excellent capital preservation
- **Strategy_101** (1d): High CPS (95.5) despite modest return (1.29%) - excellent capital preservation

### Timeframe Discoveries
- **Strategy_98**: Huge timeframe sensitivity: 98.3 CPS on 8h vs 1.1 on 5min
- **Strategy_104**: Huge timeframe sensitivity: 98.3 CPS on 4h vs 1.1 on 5min
- **Strategy_100**: Huge timeframe sensitivity: 95.5 CPS on 30min vs 40.7 on 5min

### Market Condition Analysis
- **bearish_1month**: Top performers in bearish month with CPS scores: [98.33, 98.33, 95.5]
- **capital_preservation**: Best at preserving capital with max drawdowns: [3.154255980514395, 4.258602101420752, 1.7394878163300191]
