
# Subagent Task Instructions

## Agent ID: 3
## Stage: 1

### Assigned Strategies
You are responsible for testing the following 11 strategies:
- Strategy_23 (ID: 23, Type: trend)
- Strategy_24 (ID: 24, Type: oscillator)
- Strategy_25 (ID: 25, Type: volume)
- Strategy_26 (ID: 26, Type: volatility)
- Strategy_27 (ID: 27, Type: hybrid)
- Strategy_28 (ID: 28, Type: momentum)
- Strategy_29 (ID: 29, Type: trend)
- Strategy_30 (ID: 30, Type: oscillator)
- Strategy_31 (ID: 31, Type: volume)
- Strategy_32 (ID: 32, Type: volatility)
- Strategy_33 (ID: 33, Type: hybrid)


### Testing Parameters
- Timeframes: 5min, 15min, 30min, 1h, 2h, 4h, 8h, 16h, 1d
- Data file: data/pdai_price_3months.csv
- CPU allocation: 0.60 cores
- Memory limit: 1.5GB

### Output Requirements
1. Save results to: task/subagent_results/stage1_agent_03.json
2. Save checkpoints to: task/subagent_results/checkpoint_agent_03.pkl
3. Report format must include:
   - CPS score for each strategy/timeframe combination
   - Detailed metrics (return, drawdown, Sharpe, etc.)
   - Insights and pairing suggestions
   - Any unexpected discoveries

### Scoring Criteria
Use the Composite Performance Score (CPS) with:
- 30% Profit Score
- 25% Capital Preservation Score
- 20% Risk-Adjusted Score
- 15% Trade Activity Score (profit-aware)
- 10% Trend Detection Score

### Special Instructions
- If strategies show promise when combined, note this in insights
- Pay attention to strategies that work well in downtrends
- Note any timeframe-specific behaviors
- Report strategies that might work as ensemble components

Remember: We're looking for strategies that can beat Buy & Hold (100.88% annual return)
while also preserving capital in downtrends and catching trend reversals.

### Stage 1 Specific Context
- Market condition: BEARISH (1.05% Buy & Hold over 1 month)
- Priority: Capital preservation and trend reversal detection
- Note strategies that limit losses in downtrend
- Highlight any that caught the recent reversal
