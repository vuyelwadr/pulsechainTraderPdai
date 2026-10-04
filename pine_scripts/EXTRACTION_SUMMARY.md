# Pine Script Extraction Summary

## Overview
Extracted Pine Scripts from 205 TradingView URLs by LazyBear. Successfully obtained 135 complete scripts with actual Pine Script code.

## Results
- **Total URLs**: 205
- **Successfully Extracted**: 135 scripts with actual Pine code
- **Incomplete/Missing**: 70 scripts

## Issue Analysis

### Why Some Scripts Are Missing:
1. **No Source Code on Page**: Many TradingView pages don't expose the Pine Script source in the HTML
2. **Pastebin Links**: ~30 scripts are hosted on pastebin.com, not TradingView
3. **404 Errors**: Some URLs no longer exist (e.g., ASI scripts)
4. **Truncated Response**: WebFetch tool has length limits that truncate longer scripts

### Scripts That Need Manual Extraction:
The following scripts exist on TradingView but the source code isn't accessible via web scraping:
- 024_frama.pine (links to pastebin)
- 029_vidya.pine, 030_adaptive_rsi.pine (URL shows different script)
- 050_projection_osc.pine, 051_projection_bandwidth.pine (not visible on page)
- 053_hurst_osc.pine (truncated)
- 054_inverse_fisher_cci.pine, 055_z_score.pine, 056_r_squared.pine (no source visible)
- 058_guppy_osc.pine, 059_linda_raschke.pine, 060_ian_osc.pine (not on page)
- 061_constance_brown_composite.pine, 062_rsi_plus_avgs.pine (no source visible)
- 063_asi.pine, 064_asi_osc.pine (404 error)
- 195_ehlers_simple_cycle.pine, 197_ehlers_stoch_cg.pine (no source visible)

## Recommendation
To get the missing scripts:
1. **Visit TradingView directly** and use the Pine Editor to view source
2. **Check pastebin links** from the tradingViewStrats.md file
3. **Contact LazyBear** for scripts that are no longer publicly available

## Successfully Extracted Categories:
- ✅ Moving Averages and Bands
- ✅ Oscillators (RSI, MACD variations)
- ✅ Volume Indicators
- ✅ Momentum Indicators
- ✅ Trend Indicators
- ✅ Volatility Indicators
- ✅ Market Breadth Indicators
- ✅ Ehlers Indicators (most)
- ✅ Custom Channels and Bands