# Stage 2 Hierarchical Analysis System
CRITICAL thing. we ONLY USE REAL price data for pdai no synthetic data.  

## 🧠 Architecture Overview

This system prevents context overflow while ensuring deep analysis through a 4-level hierarchy:

```
Level 1: Individual Strategy Analysis (60 agents)
├── 1 strategy per agent (~40k tokens input)
├── Deep individual analysis (~5k tokens output)
├── Deploy in 2 batches of 30 agents
└── Output: 60 focused strategy documents

Level 2: Thematic Pattern Analysis (20 agents)  
├── 3 strategies per agent (via Level 1 docs)
├── Pattern recognition across strategy types
├── Deploy all 20 agents simultaneously  
└── Output: 20 thematic analysis documents

Level 3: Comprehensive Synthesis (5 agents)
├── 4 thematic analyses per agent
├── Systems-level integration design
├── Deploy all 5 agents simultaneously
└── Output: 5 comprehensive synthesis documents

Level 4: Master Integration (Manual)
├── Read 5 synthesis documents + continuous documentation
├── Analyze all 85 documents systematically  
├── Memory management through continuous writing
└── Output: Final Stage 2 comprehensive report
```

## 📊 Strategy Distribution

**Total Strategies**: 60 (selected from Stage 1 top performers)

**By Type**:
- Momentum: 19 strategies
- Trend: 16 strategies  
- Volatility: 7 strategies
- Oscillator: 13 strategies
- Volume: 5 strategies

## 📁 File Structure

```
task/stage2_subagent_instructions/
├── level1_individual/          # 60 individual strategy analysis instructions
│   ├── stage2_agent_01_instructions.md
│   ├── stage2_agent_02_instructions.md  
│   └── ... (60 files total)
├── level2_thematic/            # 20 thematic pattern analysis instructions
│   ├── stage2_thematic_agent_01_instructions.md
│   ├── stage2_thematic_agent_02_instructions.md
│   └── ... (20 files total)
├── level3_synthesis/           # 5 comprehensive synthesis instructions
│   ├── stage2_synthesis_agent_01_instructions.md
│   ├── stage2_synthesis_agent_02_instructions.md
│   └── ... (5 files total)
└── master_instructions.md      # This file
```

## 🚀 Deployment Strategy

### Phase 1: Individual Analysis (Level 1)
```bash
# Batch 1: Deploy agents 1-30
deploy_subagents(agents=1-30, type="individual_analysis")
wait_for_completion()

# Batch 2: Deploy agents 31-60  
deploy_subagents(agents=31-60, type="individual_analysis")
wait_for_completion()
```

### Phase 2: Thematic Analysis (Level 2) 
```bash
# Deploy all 20 thematic agents simultaneously
deploy_subagents(agents=1-20, type="thematic_analysis")
wait_for_completion()
```

### Phase 3: Synthesis (Level 3)
```bash
# Deploy all 5 synthesis agents simultaneously
deploy_subagents(agents=1-5, type="comprehensive_synthesis") 
wait_for_completion()
```

### Phase 4: Master Integration (Manual)
```bash
# Manual analysis with continuous documentation
analyze_synthesis_documents()
write_continuous_findings()
generate_final_report()
```

## ⚠️ Critical Success Factors

1. **Context Management**: Each level designed to stay well under 160k token limit
2. **Memory Preservation**: Continuous documentation at Level 4 to prevent information loss
3. **Systematic Coverage**: Every strategy analyzed at multiple levels
4. **Quality Assurance**: Each level validates and builds upon previous level
5. **Actionable Outputs**: Every analysis must produce implementable recommendations

## 📊 Expected Outcomes

**Level 1**: 60 detailed individual strategy analyses (300+ pages total)
**Level 2**: 20 thematic pattern analyses (160+ pages total) 
**Level 3**: 5 comprehensive integration designs (50+ pages total)
**Level 4**: 1 master Stage 2 report with final recommendations (25+ pages)

**Total Analysis**: 535+ pages of systematic, hierarchical analysis ensuring no strategy or pattern is missed.

## 🎯 Quality Metrics

Each level must achieve:
- ✅ 100% strategy coverage (no gaps)
- ✅ Data-driven conclusions (backed by optimization results)
- ✅ Actionable recommendations (implementable insights)
- ✅ Cross-validation (findings verified across levels)
- ✅ Context preservation (no critical information lost)

This hierarchical system ensures comprehensive analysis while managing context limitations and memory constraints.
