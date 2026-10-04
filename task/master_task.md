# Master Task: Ultimate PDAI Trading Strategy Optimization

## Core Objective
Create the BEST performing PDAI trading strategy through systematic research, implementation, and iterative optimization.
CRITICAL thing. we ONLY USE REAL price data for pdai no synthetic data.  
## Original User Instructions
```
amazing now delete all previous historical data and give me command to start collecting all historical data within 1 year please. actually you run the command but not as a subcommand as a main command you have to wait till it finishes executing or crashes. i want you to do this because when it finished executing on your todo must be generating optimal strategy. youll use the internet after you have 1 year historical data to search for best trading strategies. youll take a few at least 10 or so. then code them and try hyper param searches for all 10 make sure the hyperparams are for most common time intervals. i.e 5 min, 15, 30, 1h 2h 4h, etc all the way until 1 day. learn how the strategies perform please. so to do this if you need to have the strategy hyperparam search output certain e.g visualizations alongside raw data that can be analyzed later. then see which strategy performed the best. if performance is really good then please write down the strategy params that output best results to a best strat .md doc. then run git add . to stage all your changes. afterwards youll then analyze all strategy data. idk how youll do this but it must be accurate and comprehensive so think of this when you design the hyperparam search data output. learn from all strategies and continuously iterate, keep iterating and creating a single strategy with findings from all strategies, e.g you can combine all 5 into 1 strat, take the best aspects of all 5 and create completely new strat. you have to try out all these different combinations its an iterative approach. trying to get the BEST strategy performance. remember slippage is usually around 1% but can be as high as 5% so please take that into account. with each improved version you should create a new branch so after your 1st git add commit the changes then from there onwards while iterating when youre happy with improvement create branch. the branch name must indicate improvement percentage in terms of performance and profit percent. i dont care if at the end you have 100 different branches. the branching is just so you can always go back to a certain branch when you make a mistake, realize that oh wait im in branch 23 but ive discovered something amazing that could actually be applied to branch 5 that could get performance up even more than branch 23 that im in so ill switch and test and you can keep testing and if you fail to get it higher than branch 26 then its no problem just switch back to branch 26 and continue. everything must be meticulously documented in /docs so you can read docs and all youve learnt about strategy, about pdai about trading. feel free to use the internet as much as you want even look it at tradingview for inspiration. i dont care how many strategies you try out i just want the best. just dont create new branch if your approach was shit just keep trying findings to /docs and iterating only branch when performance is better than current branch. ultrathink the entire time please. also create a /task doc where youll copy this exact prompt and use that every time you get slightly lost. youll read this file and read all /docs every time you only see a summary in your chat meaning youve lost your memory and should recover whats happened. amazing now do that.
```

## Phase 1: Data Collection
- [x] Delete all previous historical data
- [x] Collect 3 MONTHS of historical PDAI price data (UPDATED: Using last 3 months for more relevant backtesting)
- [x] Verify data quality and completeness

## Phase 2: Strategy Research
- [ ] Research best trading strategies from internet (minimum 10)
- [ ] Research TradingView for inspiration
- [ ] Document findings in /docs/strategy_research.md

## Phase 3: Strategy Implementation
- [ ] Code all 10+ strategies
- [ ] Implement hyperparameter search framework
- [ ] Support timeframes: 5min, 15min, 30min, 1h, 2h, 4h, 8h, 12h, 1day
- [ ] Account for slippage (1-5%)
- [ ] Generate visualizations and raw data output

## Phase 4: Strategy Analysis
- [ ] Run comprehensive hyperparameter searches
- [ ] Analyze performance metrics
- [ ] Identify best performing strategies
- [ ] Document results in best_strat.md

## Phase 5: Iterative Optimization
- [ ] Combine best aspects of top strategies
- [ ] Create hybrid strategies
- [ ] Test combinations and variations
- [ ] Create branches for improvements only
- [ ] Document all findings in /docs

## Branching Strategy
- Initial commit: git add . && git commit -m "Initial strategy optimization project"
- Branch naming: improvement_X%_profit_Y% (only when better performance)
- Always return to best performing branch
- No branches for failed experiments

## Documentation Requirements
- /docs/strategy_research.md - All research findings
- /docs/trading_insights.md - PDAI-specific trading knowledge  
- /docs/performance_analysis.md - Analysis methodology and results
- /docs/branch_history.md - Track of all successful branches
- best_strat.md - Final best strategy parameters

## Memory Recovery Protocol
When seeing only summary in chat:
1. Read this file (/task/master_task.md)
2. Read all /docs files
3. Check current branch and progress
4. Continue from last completed task
## CRITICAL PERFORMANCE UPDATE (Sept 11, 2025)

### MANDATORY REQUIREMENTS - URGENT
- **USE 90% OF SYSTEM RESOURCES** - Performance is critical
- **IMPLEMENT PARALLEL PROCESSING** - Use all CPU cores simultaneously  
- **35 HOURS IS UNACCEPTABLE** - Must complete in hours not days
- **INCLUDE BUY & HOLD BENCHMARK** - Compare all strategies to baseline
- **DO NOT STOP FOR UPDATES** - Continuous execution required

### Speed Optimization Implementation
- Use multiprocessing.Pool for parallel backtests
- Process multiple strategies simultaneously  
- Run multiple parameter combinations in parallel
- Cache data aggressively to reduce I/O
- Use vectorized operations wherever possible

## ZEN CONVERSATION ID
**CRITICAL FOR RECOVERY**: `6767f96e-5e0d-48d3-baac-c890350c53e8`
- Use this ID with zen chat/thinkdeep for context recovery after memory loss

## Optimization Strategy (from zen thinkdeep analysis)
### Archipelago Approach
1. **Coarse Search**: Test 3 values per parameter for ALL strategies (~500 tests)
2. **Identify Islands**: Select top 3-5 performing parameter regions
3. **Fine-tune**: Do detailed search around each island
4. **Time Target**: Complete in under 10 minutes with 12 cores

### Key Optimizations
- Pre-calculate static indicators once
- Use ProcessPoolExecutor with chunked workloads
- Vectorized numpy operations
- Cache intermediate results for crash recovery
