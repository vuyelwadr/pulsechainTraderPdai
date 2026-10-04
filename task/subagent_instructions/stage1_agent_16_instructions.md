
# Subagent Task Instructions

## Agent ID: 16
## Stage: 1

### Assigned Strategies
You are responsible for testing the following 10 strategies:
- Strategy_156 (ID: 156, Type: oscillator)
- Strategy_157 (ID: 157, Type: volume)
- Strategy_158 (ID: 158, Type: volatility)
- Strategy_159 (ID: 159, Type: hybrid)
- Strategy_160 (ID: 160, Type: momentum)
- Strategy_161 (ID: 161, Type: trend)
- Strategy_162 (ID: 162, Type: oscillator)
- Strategy_163 (ID: 163, Type: volume)
- Strategy_164 (ID: 164, Type: volatility)
- Strategy_165 (ID: 165, Type: hybrid)


### Testing Parameters
- Timeframes: 5min, 15min, 30min, 1h, 2h, 4h, 8h, 16h, 1d
- Data file: data/pdai_price_3months.csv
- CPU allocation: 0.60 cores
- Memory limit: 1.5GB

### Output Requirements
1. Save results to: task/subagent_results/stage1_agent_16.json
2. Save checkpoints to: task/subagent_results/checkpoint_agent_16.pkl
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
