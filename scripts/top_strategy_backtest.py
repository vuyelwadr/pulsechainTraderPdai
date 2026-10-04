#!/usr/bin/env python3
"""Aggregate optimizer reports, pick top strategies, run full backtests, and
produce a multi-strategy HTML dashboard.

This script walks every optimizer pipeline report directory, concatenates all
`stage_aggregate.csv` files, ranks strategies primarily by profit while
penalizing excessive drawdowns, runs full backtests for the top candidates using
real PDAI OHLCV data, and emits both machine-readable summaries and a new
interactive HTML dashboard with multi-strategy overlays.
"""
import argparse
import json
import logging
import math
import multiprocessing as mp
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

# Ensure repository root on sys.path for dynamic strategy loading
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from optimization.runner import load_strategy_class  # type: ignore
from bot.backtest_engine import BacktestEngine  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("top_strategy_backtest")


_GLOBAL_BASE_DATA: Optional[pd.DataFrame] = None


@dataclass
class StageEntry:
    pipeline: str
    stage: str
    csv_path: Path
    json_dir: Path
    row: Dict[str, object]


@dataclass
class BacktestResult:
    strategy: str
    timeframe: str
    label: str
    params: Dict[str, object]
    row_meta: Dict[str, object]
    result: Dict[str, object]
    json_path: Path
    dataset_start: datetime
    dataset_end: datetime
    buy_hold_return_pct_full: float


TIMEFRAME_MINUTES = {
    "5min": 5,
    "15min": 15,
    "30min": 30,
    "1h": 60,
    "2h": 120,
    "4h": 240,
    "8h": 480,
    "12h": 720,
    "16h": 960,
    "1d": 1440,
    "2d": 2880,
}


COLOR_CYCLE = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
]


def load_base_dataframe(data_path: Path) -> pd.DataFrame:
    df = pd.read_csv(data_path, parse_dates=["timestamp"])
    if "price" not in df.columns:
        if "close" in df.columns:
            df["price"] = df["close"]
        elif "open" in df.columns:
            df["price"] = df["open"]
        else:
            raise ValueError("Data must contain either 'price', 'close', or 'open' column")
    for col in ["open", "high", "low", "close"]:
        if col not in df.columns:
            df[col] = df["price"]
    return df


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank optimizer strategies and run full backtests.")
    parser.add_argument("--reports-dir", default=REPO_ROOT / "reports", type=Path,
                        help="Directory containing optimizer pipeline reports.")
    parser.add_argument("--data-path", default=REPO_ROOT / "data" / "pdai_ohlcv_dai_730day_5m.csv", type=Path,
                        help="CSV with real PDAI OHLCV data (5m resolution).")
    parser.add_argument("--output-dir", default=None, type=Path,
                        help="Optional output directory. Defaults to reports/top_strategy_analysis_<timestamp>.")
    parser.add_argument("--top-n", default=20, type=int, help="Number of strategies to backtest in depth.")
    parser.add_argument("--min-return", default=100.0, type=float,
                        help="Minimum total return (percent) required to be considered.")
    parser.add_argument("--max-dd", default=70.0, type=float,
                        help="Maximum allowed drawdown (percent) for shortlisted strategies.")
    parser.add_argument("--max-dd-ratio", default=0.8, type=float,
                        help="Maximum drawdown to return ratio (drawdown/return).")
    parser.add_argument("--min-trades", default=2, type=int,
                        help="Require at least this many trades (set 0 to disable the filter).")
    parser.add_argument("--price-resample", default="none",
                        help="Resample interval for price chart (e.g. '1h'). Use 'none' to keep raw resolution.")
    parser.add_argument("--workers", default=0, type=int,
                        help="Number of parallel worker processes (0 uses CPU count).")
    parser.add_argument("--max-backtests", default=0, type=int,
                        help="Cap how many strategies get replayed (0 keeps all filtered rows).")
    return parser.parse_args()


def scan_stage_aggregates(reports_dir: Path) -> List[StageEntry]:
    entries: List[StageEntry] = []
    for csv_path in sorted(reports_dir.rglob("stage_aggregate.csv")):
        stage_dir = csv_path.parent
        pipeline_dir = stage_dir.parent
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            logger.warning("Failed reading %s: %s", csv_path, exc)
            continue
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            entries.append(
                StageEntry(
                    pipeline=pipeline_dir.name,
                    stage=stage_dir.name,
                    csv_path=csv_path,
                    json_dir=stage_dir,
                    row=row_dict,
                )
            )
    return entries


def entries_to_dataframe(entries: Iterable[StageEntry]) -> pd.DataFrame:
    records: List[Dict[str, object]] = []
    for e in entries:
        rec = dict(e.row)
        rec["pipeline"] = e.pipeline
        rec["stage"] = e.stage
        rec["csv_path"] = str(e.csv_path)
        rec["json_dir"] = str(e.json_dir)
        # Build absolute JSON path if possible
        filename = rec.get("file") or rec.get("json") or ""
        if isinstance(filename, str) and filename:
            json_path = e.json_dir / filename
            rec["json_path"] = str(json_path)
        else:
            rec["json_path"] = ""
        records.append(rec)
    df = pd.DataFrame(records)
    return df


def coerce_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def select_top_strategies(df: pd.DataFrame,
                          top_n: int,
                          min_return: float,
                          max_dd: float,
                          max_dd_ratio: float,
                          min_trades: int) -> pd.DataFrame:
    working = df.copy()
    for col in ["total_return_pct", "max_drawdown_pct", "total_trades", "score", "utility", "cps"]:
        if col in working.columns:
            working[col] = coerce_numeric(working[col])
    working = working.dropna(subset=["total_return_pct", "max_drawdown_pct"])
    working = working[working["total_return_pct"] > min_return]
    working = working[working["max_drawdown_pct"] < max_dd]
    if min_trades > 0 and "total_trades" in working.columns:
        working = working[working["total_trades"] >= min_trades]
    ratio = working["max_drawdown_pct"] / working["total_return_pct"].replace({0.0: np.nan})
    working = working[ratio.fillna(np.inf) <= max_dd_ratio]
    working = working.dropna(subset=["json_path"])  # require JSON to replay exact params
    working = working[working["json_path"].apply(lambda p: Path(p).exists())]
    if working.empty:
        return working
    # Composite ranking: profit first, then penalty for drawdown
    working = working.copy()
    working["drawdown_penalty"] = working["max_drawdown_pct"] * 0.6
    working["composite_score"] = working["total_return_pct"] - working["drawdown_penalty"]
    working.sort_values([
        "total_return_pct",
        "composite_score",
        "score" if "score" in working.columns else "total_return_pct"
    ], ascending=[False, False, False], inplace=True)
    working = working.drop_duplicates(subset=["json_path"], keep="first")
    return working.head(top_n)


def select_top_from_results(df: pd.DataFrame,
                            top_n: int,
                            min_return: float,
                            max_dd: float,
                            max_dd_ratio: float,
                            min_trades: int) -> pd.DataFrame:
    working = df.copy()
    for col in ["total_return_pct", "max_drawdown_pct", "total_trades"]:
        if col in working.columns:
            working[col] = coerce_numeric(working[col])
    working = working.dropna(subset=["total_return_pct", "max_drawdown_pct"])
    working = working[working["total_return_pct"] > min_return]
    working = working[working["max_drawdown_pct"] < max_dd]
    if min_trades > 0 and "total_trades" in working.columns:
        working = working[working["total_trades"] >= min_trades]
    ratio = working["max_drawdown_pct"] / working["total_return_pct"].replace({0.0: np.nan})
    working = working[ratio.fillna(np.inf) <= max_dd_ratio]
    working.sort_values(["total_return_pct", "max_drawdown_pct"], ascending=[False, True], inplace=True)
    return working.head(top_n)


def _pool_initializer(data_path: str):
    global _GLOBAL_BASE_DATA
    _GLOBAL_BASE_DATA = load_base_dataframe(Path(data_path))


def _run_backtest_job(args):
    idx, row_dict, output_dir_str, dataset_start, dataset_end, buy_hold_full_pct = args
    output_dir = Path(output_dir_str)
    try:
        return run_full_backtest(idx, row_dict, None, output_dir, dataset_start, dataset_end, buy_hold_full_pct)
    except Exception as exc:
        logger.warning("Worker failed %s: %s", row_dict.get("json_path"), exc)
        return None


def timeframe_to_minutes(tf: str) -> int:
    tf = tf.strip().lower()
    if tf in TIMEFRAME_MINUTES:
        return TIMEFRAME_MINUTES[tf]
    if tf.endswith("min"):
        return int(tf.replace("min", ""))
    if tf.endswith("h"):
        return int(float(tf.replace("h", "")) * 60)
    if tf.endswith("d"):
        return int(float(tf.replace("d", "")) * 1440)
    raise ValueError(f"Unsupported timeframe: {tf}")


def normalize_param_value(value: object) -> object:
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return value
        if v.lower() in {"true", "false"}:
            return v.lower() == "true"
        try:
            num = float(v)
            if math.isfinite(num):
                if abs(num - round(num)) < 1e-6:
                    return int(round(num))
                return num
        except ValueError:
            return value
    return value


def normalize_params(params: Dict[str, object], timeframe: str) -> Dict[str, object]:
    normalized = {k: normalize_param_value(v) for k, v in params.items()}
    normalized.setdefault("timeframe_minutes", timeframe_to_minutes(timeframe))
    return normalized


def load_json(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def ensure_datetime(series: Iterable) -> List[pd.Timestamp]:
    out: List[pd.Timestamp] = []
    for val in series:
        if isinstance(val, pd.Timestamp):
            out.append(val)
        else:
            out.append(pd.to_datetime(val))
    return out


def serialize_timestamp(value) -> str:
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is None:
            return value.isoformat() + "Z"
        return value.isoformat()
    return str(value)


def serialize_backtest_result(result: Dict[str, object]) -> Dict[str, object]:
    serializable = {}
    for key, value in result.items():
        if key in {"trades", "portfolio_history"} and isinstance(value, list):
            serializable[key] = []
            for entry in value:
                new_entry = {}
                for k, v in entry.items():
                    if isinstance(v, (pd.Timestamp, datetime)):
                        new_entry[k] = serialize_timestamp(v)
                    else:
                        new_entry[k] = v
                serializable[key].append(new_entry)
        elif isinstance(value, (pd.Timestamp, datetime)):
            serializable[key] = serialize_timestamp(value)
        else:
            serializable[key] = value
    return serializable


def sanitize_for_filename(value: str) -> str:
    return ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in value)


def run_full_backtest(rank: int,
                      row_data,
                      base_data: Optional[pd.DataFrame],
                      output_dir: Path,
                      dataset_start: datetime,
                      dataset_end: datetime,
                      buy_hold_full_pct: float) -> Optional[BacktestResult]:
    global _GLOBAL_BASE_DATA
    if isinstance(row_data, dict):
        row = pd.Series(row_data)
    else:
        row = row_data

    data = base_data if base_data is not None else _GLOBAL_BASE_DATA
    if data is None:
        raise RuntimeError("Base data is not loaded")

    json_path = Path(row["json_path"])
    meta = load_json(json_path)
    strategy_name = meta.get("strategy") or row.get("strategy")
    timeframe = meta.get("timeframe") or row.get("timeframe")
    if not strategy_name or not timeframe:
        logger.warning("Skipping %s because strategy or timeframe missing", json_path)
        return None
    params = meta.get("selected_params") or {}
    params = normalize_params(params, timeframe)
    strategy_class = load_strategy_class(strategy_name)
    if strategy_class is None:
        logger.warning("Strategy %s could not be loaded", strategy_name)
        return None
    try:
        strategy_instance = strategy_class(parameters=params)
    except Exception as exc:
        logger.warning("Failed to instantiate %s: %s", strategy_name, exc)
        return None
    engine = BacktestEngine()
    try:
        result = engine.run_backtest(strategy_instance, data.copy())
    except Exception as exc:
        logger.warning("Backtest failed for %s %s: %s", strategy_name, timeframe, exc)
        return None
    full_history = getattr(engine, "portfolio_history", [])
    serializable_result = serialize_backtest_result(result)
    if full_history and len(full_history) > len(serializable_result.get("portfolio_history", [])):
        serializable_result["portfolio_history_full"] = [
            {k: serialize_timestamp(v) if isinstance(v, (pd.Timestamp, datetime)) else v for k, v in entry.items()}
            for entry in full_history
        ]
    pipeline = str(row.get("pipeline") or "pipeline")
    stage = str(row.get("stage") or "stage")
    base_name = f"{rank:02d}_{sanitize_for_filename(strategy_name)}_{sanitize_for_filename(timeframe)}_{sanitize_for_filename(pipeline)}_{sanitize_for_filename(stage)}"
    output_json_name = f"{base_name}_full_backtest.json"
    output_path = output_dir / output_json_name
    label = f"{strategy_name} ({timeframe}, {pipeline}/{stage})"
    with output_path.open("w", encoding="utf-8") as fh:
        metrics_row = {k: row[k] for k in row.index if k not in {"csv_path", "json_dir", "json_path"}}
        metrics_row = json.loads(json.dumps(metrics_row, default=str))
        json.dump({
            "strategy": strategy_name,
            "timeframe": timeframe,
            "selected_params": params,
            "source_json": str(json_path),
            "source_pipeline": row.get("pipeline"),
            "source_stage": row.get("stage"),
            "label": label,
            "dataset_start": dataset_start.isoformat(),
            "dataset_end": dataset_end.isoformat(),
            "buy_hold_return_pct_full": buy_hold_full_pct,
            "metrics_row": metrics_row,
            "backtest": serializable_result,
        }, fh, indent=2)
    logger.info("Backtest for %s %s wrote %s", strategy_name, timeframe, output_path)
    return BacktestResult(
        strategy=strategy_name,
        timeframe=timeframe,
        label=label,
        params=params,
        row_meta=row.to_dict(),
        result=serializable_result,
        json_path=output_path,
        dataset_start=dataset_start,
        dataset_end=dataset_end,
        buy_hold_return_pct_full=buy_hold_full_pct,
    )


def build_dashboard_html(base_data: pd.DataFrame,
                         backtests: List[BacktestResult],
                         output_dir: Path,
                         price_resample: Optional[str] = None) -> Path:
    import html
    import json as jsonlib
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    if base_data.empty:
        raise ValueError("Base data is empty; cannot render dashboard")

    # Prepare buy & hold curve and price series
    base_df = base_data.copy()
    base_df.sort_values("timestamp", inplace=True)
    base_df["timestamp"] = pd.to_datetime(base_df["timestamp"])

    # Ensure OHLC columns exist (fallback to close/price if needed)
    for col in ["open", "high", "low", "close"]:
        if col not in base_df.columns:
            base_df[col] = base_df.get("price", base_df.get("close"))
    if "price" not in base_df.columns:
        base_df["price"] = base_df["close"]

    resample_rule = (price_resample or "").strip().lower()
    if resample_rule in {"", "none", "off", "no", "false"}:
        ohlc_df = base_df[["timestamp", "open", "high", "low", "close"]].dropna()
    else:
        price_df = base_df.set_index("timestamp")
        agg = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }
        ohlc_df = price_df.resample(resample_rule).agg(agg).dropna(subset=["close"]).reset_index()
        ohlc_df.rename(columns={"index": "timestamp"}, inplace=True)

    if ohlc_df.empty:
        raise ValueError("No OHLC data available for price chart")

    first_close = float(ohlc_df.iloc[0]["close"])
    base_df["buy_hold_value"] = (base_df["close"] / first_close) * 1000.0

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.04, row_heights=[0.7, 0.3])

    fig.add_trace(
        go.Candlestick(
            x=ohlc_df["timestamp"],
            open=ohlc_df["open"],
            high=ohlc_df["high"],
            low=ohlc_df["low"],
            close=ohlc_df["close"],
            name="PDAI Price",
            increasing_line_color="#2ecc71",
            decreasing_line_color="#e74c3c",
            increasing_fillcolor="#27ae60",
            decreasing_fillcolor="#c0392b",
            showlegend=True,
            legendgroup="Price",
        ),
        row=1,
        col=1,
    )

    trace_metadata: List[Dict[str, object]] = []

    for idx, bt in enumerate(backtests):
        color = COLOR_CYCLE[idx % len(COLOR_CYCLE)]
        strat_label = bt.label
        trades = pd.DataFrame(bt.result.get("trades", []))
        trades_ts = []
        if not trades.empty:
            trades["timestamp"] = pd.to_datetime(trades["timestamp"], utc=True)
            trades.sort_values("timestamp", inplace=True)
            buys = trades[trades["type"].str.lower() == "buy"]
            sells = trades[trades["type"].str.lower() == "sell"]
            if not buys.empty:
                fig.add_trace(
                    go.Scatter(
                        x=buys["timestamp"],
                        y=buys["price"],
                        mode="markers",
                        marker=dict(symbol="triangle-up", size=10, color=color, line=dict(width=0.5, color="#ffffff")),
                        name=f"{strat_label} Buys",
                        legendgroup=strat_label,
                        legendgrouptitle_text=strat_label,
                        hovertemplate="%{x|%Y-%m-%d %H:%M}<br>Buy @ %{y:.4f}",
                        showlegend=True,
                    ),
                    row=1,
                    col=1,
                )
                trace_metadata.append({"strategy": strat_label, "category": "buy", "trace_index": len(fig.data) - 1})
            if not sells.empty:
                fig.add_trace(
                    go.Scatter(
                        x=sells["timestamp"],
                        y=sells["price"],
                        mode="markers",
                        marker=dict(symbol="triangle-down", size=10, color=color, line=dict(width=0.5, color="#000000")),
                        name=f"{strat_label} Sells",
                        legendgroup=strat_label,
                        hovertemplate="%{x|%Y-%m-%d %H:%M}<br>Sell @ %{y:.4f}",
                        showlegend=True,
                    ),
                    row=1,
                    col=1,
                )
                trace_metadata.append({"strategy": strat_label, "category": "sell", "trace_index": len(fig.data) - 1})
        history_key = "portfolio_history_full" if "portfolio_history_full" in bt.result else "portfolio_history"
        portfolio = pd.DataFrame(bt.result.get(history_key, []))
        if not portfolio.empty and "total_value" in portfolio.columns:
            portfolio["timestamp"] = pd.to_datetime(portfolio["timestamp"], utc=True)
            portfolio.sort_values("timestamp", inplace=True)
            fig.add_trace(
                go.Scatter(
                    x=portfolio["timestamp"],
                    y=portfolio["total_value"],
                    mode="lines",
                    line=dict(color=color, width=2),
                    name=f"{strat_label} Equity",
                    legendgroup=strat_label,
                    showlegend=True,
                    hovertemplate="%{x|%Y-%m-%d %H:%M}<br>Equity %{y:.2f}",
                ),
                row=2,
                col=1,
            )
            trace_metadata.append({"strategy": strat_label, "category": "equity", "trace_index": len(fig.data) - 1})

    fig.add_trace(
        go.Scatter(
            x=base_df["timestamp"],
            y=base_df["buy_hold_value"],
            mode="lines",
            line=dict(color="#95a5a6", width=2, dash="dash"),
            name="Buy & Hold",
            legendgroup="BuyHold",
            hovertemplate="%{x|%Y-%m-%d %H:%M}<br>Value %{y:.2f}",
        ),
        row=2,
        col=1,
    )
    trace_metadata.append({"strategy": "Buy & Hold", "category": "equity", "trace_index": len(fig.data) - 1})

    fig.update_layout(
        template="plotly_dark",
        height=900,
        legend=dict(itemsizing="constant", orientation="h", yanchor="bottom", y=1.02, x=0, xanchor="left"),
        margin=dict(l=40, r=20, t=60, b=40),
        xaxis=dict(title="", rangeslider=dict(visible=False)),
        xaxis2=dict(title="Date", rangeslider=dict(visible=False)),
        yaxis=dict(title="Price (DAI)"),
        yaxis2=dict(title="Portfolio Value (DAI)"),
        hovermode="x unified",
    )

    config = {
        "responsive": True,
        "scrollZoom": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    }

    figure_json = fig.to_json()
    metadata_json = jsonlib.dumps(trace_metadata)

    # Build controls HTML
    strategy_controls: List[str] = []
    seen = set()
    for meta in trace_metadata:
        strat = meta["strategy"]
        if strat in seen or strat == "Buy & Hold":
            continue
        seen.add(strat)
        safe = html.escape(strat)
        strategy_controls.append(
            f"""
            <div class=\"strategy\">
              <div class=\"strategy-title\">{safe}</div>
              <label><input type=\"checkbox\" data-strategy=\"{safe}\" data-category=\"buy\" checked> Buys</label>
              <label><input type=\"checkbox\" data-strategy=\"{safe}\" data-category=\"sell\" checked> Sells</label>
              <label><input type=\"checkbox\" data-strategy=\"{safe}\" data-category=\"equity\" checked> Equity</label>
            </div>
            """
        )
    controls_html = "\n".join(strategy_controls)

    output_html = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>PDAI Top Strategy Dashboard</title>
  <script src=\"https://cdn.plot.ly/plotly-2.26.0.min.js\"></script>
  <style>
    body {{ margin: 0; padding: 0; background-color: #0b1320; color: #ecf0f1; font-family: 'Inter', 'Segoe UI', sans-serif; }}
    .wrapper {{ display: flex; flex-direction: column; height: 100vh; }}
    header {{ padding: 16px 24px; background: rgba(12, 20, 40, 0.95); box-shadow: 0 2px 12px rgba(0,0,0,0.4); z-index: 10; }}
    header h1 {{ margin: 0; font-size: 1.6rem; }}
    header p {{ margin: 4px 0 0; color: #95a5a6; font-size: 0.95rem; }}
    .content {{ flex: 1; display: grid; grid-template-columns: 260px 1fr; gap: 0; min-height: 0; }}
    .controls {{ padding: 18px; background: rgba(20, 32, 54, 0.95); overflow-y: auto; border-right: 1px solid rgba(236, 240, 241, 0.08); }}
    .controls h2 {{ font-size: 1.05rem; margin: 0 0 12px; color: #f1c40f; }}
    .controls p {{ font-size: 0.85rem; color: #bdc3c7; margin-bottom: 16px; line-height: 1.4; }}
    .strategy {{ margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid rgba(236, 240, 241, 0.05); }}
    .strategy-title {{ font-weight: 600; margin-bottom: 6px; color: #ffffff; }}
    label {{ display: block; font-size: 0.85rem; color: #ecf0f1; cursor: pointer; }}
    input[type='checkbox'] {{ margin-right: 6px; accent-color: #1abc9c; }}
    .plot-area {{ position: relative; }}
    #chart {{ width: 100%; height: 100%; }}
    footer {{ padding: 10px 24px; background: rgba(12, 20, 40, 0.95); font-size: 0.8rem; color: #7f8c8d; text-align: right; }}
    @media (max-width: 900px) {{
        .content {{ grid-template-columns: 1fr; }}
        .controls {{ border-right: none; border-bottom: 1px solid rgba(236, 240, 241, 0.08); display: flex; flex-wrap: wrap; gap: 16px; }}
        .strategy {{ width: calc(50% - 10px); border-bottom: none; border-right: 1px solid rgba(236,240,241,0.05); padding-right: 12px; }}
        .strategy:last-child {{ border-right: none; }}
    }}
  </style>
</head>
<body>
  <div class=\"wrapper\">
    <header>
      <h1>PDAI Optimizer – Multi-Strategy Deep Dive</h1>
      <p>Interactive exploration of the top-performing strategies ranked by profit with drawdown discipline. Use scroll to zoom, drag to pan, and the toggles to focus on specific signals.</p>
    </header>
    <div class=\"content\">
      <aside class=\"controls\">
        <h2>Strategy Layers</h2>
        <p>Disable buys, sells, or equity for any strategy to declutter the view. All price data is real PulseChain PDAI OHLCV.</p>
        {controls_html}
        <div class=\"strategy\">
          <div class=\"strategy-title\">Buy &amp; Hold Benchmark</div>
          <label><input type=\"checkbox\" data-strategy=\"Buy &amp; Hold\" data-category=\"equity\" checked> Equity</label>
        </div>
      </aside>
      <div class=\"plot-area\">
        <div id=\"chart\"></div>
      </div>
    </div>
    <footer>Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC · Scroll to zoom, drag to pan</footer>
  </div>
  <script>
    const figure = {figure_json};
    const metadata = {metadata_json};
    const config = {jsonlib.dumps(config)};
    const chart = document.getElementById('chart');
    Plotly.newPlot(chart, figure.data, figure.layout, config);

    function setVisibility(strategy, category, visible) {{
      metadata.forEach(meta => {{
        if (meta.strategy === strategy && meta.category === category) {{
          Plotly.restyle(chart, {{visible: visible}}, [meta.trace_index]);
        }}
      }});
    }}

    document.querySelectorAll("input[type='checkbox'][data-strategy]").forEach(cb => {{
      cb.addEventListener('change', evt => {{
        const target = evt.target;
        const strat = target.getAttribute('data-strategy');
        const category = target.getAttribute('data-category');
        const visible = target.checked;
        setVisibility(strat, category, visible);
      }});
    }});
  </script>
</body>
</html>
"""
    output_file = output_dir / "top_strategies_dashboard.html"
    with output_file.open("w", encoding="utf-8") as fh:
        fh.write(output_html)
    logger.info("Wrote dashboard: %s", output_file)
    return output_file


def main() -> None:
    args = parse_args()
    reports_dir = args.reports_dir.resolve()
    if not reports_dir.exists():
        raise SystemExit(f"Reports directory not found: {reports_dir}")
    entries = scan_stage_aggregates(reports_dir)
    if not entries:
        raise SystemExit("No stage_aggregate.csv files found")
    df = entries_to_dataframe(entries)
    df = df[df.get("json_path", "").astype(str).str.len() > 0]
    df = df[df["json_path"].apply(lambda p: Path(p).exists())]

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or (reports_dir / f"top_strategy_analysis_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    df.sort_values(["total_return_pct"], ascending=False, inplace=True, na_position="last")
    aggregate_csv_path = output_dir / "all_stage_aggregate.csv"
    df.to_csv(aggregate_csv_path, index=False)
    logger.info("Wrote aggregate results CSV: %s", aggregate_csv_path)

    agg_top_df = select_top_strategies(df, args.top_n, args.min_return, args.max_dd, args.max_dd_ratio, args.min_trades)
    agg_top_path = output_dir / "top_strategies_aggregate.csv"
    agg_top_df.to_csv(agg_top_path, index=False)
    logger.info("Wrote aggregate-derived top strategies CSV: %s", agg_top_path)

    # Load full OHLCV dataset
    data_path = args.data_path.resolve()
    if not data_path.exists():
        raise SystemExit(f"Data file not found: {data_path}")
    base_data = load_base_dataframe(data_path)

    dataset_start = pd.to_datetime(base_data["timestamp"].min()).to_pydatetime()
    dataset_end = pd.to_datetime(base_data["timestamp"].max()).to_pydatetime()
    first_close = float(base_data.iloc[0]["close"] if "close" in base_data.columns else base_data.iloc[0]["price"])
    last_close = float(base_data.iloc[-1]["close"] if "close" in base_data.columns else base_data.iloc[-1]["price"])
    buy_hold_full_pct = ((last_close / first_close) - 1.0) * 100.0 if first_close > 0 else 0.0

    backtest_df = df
    if args.max_backtests and args.max_backtests > 0:
        backtest_df = df.head(args.max_backtests).copy()
        logger.info("Limiting backtests to top %d rows after sorting", len(backtest_df))

    records = backtest_df.to_dict(orient="records")
    jobs = [
        (idx + 1, record, str(output_dir), dataset_start, dataset_end, buy_hold_full_pct)
        for idx, record in enumerate(records)
    ]

    backtest_results: List[BacktestResult] = []
    workers = args.workers if args.workers != 0 else mp.cpu_count()
    if workers <= 1:
        global _GLOBAL_BASE_DATA
        _GLOBAL_BASE_DATA = base_data
        for job in jobs:
            result = _run_backtest_job(job)
            if result:
                backtest_results.append(result)
    else:
        ctx = mp.get_context("spawn")
        with ctx.Pool(processes=workers, initializer=_pool_initializer, initargs=(str(data_path),)) as pool:
            for result in pool.imap_unordered(_run_backtest_job, jobs):
                if result:
                    backtest_results.append(result)

    if not backtest_results:
        raise SystemExit("All selected strategies failed during backtesting.")

    summary_path = output_dir / "backtest_summary.json"
    summary_payload = []
    for bt in backtest_results:
        summary_payload.append({
            "strategy": bt.strategy,
            "timeframe": bt.timeframe,
            "label": bt.label,
            "params": bt.params,
            "result_path": str(bt.json_path),
            "total_return_pct": float(bt.result.get("total_return_pct", 0.0)),
            "max_drawdown_pct": float(bt.result.get("max_drawdown_pct", 0.0)),
            "total_trades": int(bt.result.get("total_trades", 0) or 0),
            "final_balance": float(bt.result.get("final_balance", 0.0)),
            "buy_hold_return_pct_full": float(bt.buy_hold_return_pct_full),
            "dataset_start": bt.dataset_start.isoformat(),
            "dataset_end": bt.dataset_end.isoformat(),
        })
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary_payload, fh, indent=2)
    logger.info("Wrote summary JSON: %s", summary_path)

    fresh_rows = []
    for bt in backtest_results:
        res = bt.result
        fresh_rows.append({
            "strategy": bt.strategy,
            "timeframe": bt.timeframe,
            "label": bt.label,
            "total_return_pct": float(res.get("total_return_pct", 0.0)),
            "max_drawdown_pct": float(res.get("max_drawdown_pct", 0.0)),
            "sharpe_ratio": float(res.get("sharpe_ratio", 0.0) or 0.0),
            "win_rate_pct": float(res.get("win_rate_pct", 0.0)),
            "total_trades": int(res.get("total_trades", 0) or 0),
            "final_balance": float(res.get("final_balance", 0.0)),
            "buy_hold_return_pct_full": float(bt.buy_hold_return_pct_full),
            "dataset_start": bt.dataset_start.isoformat(),
            "dataset_end": bt.dataset_end.isoformat(),
            "source_pipeline": bt.row_meta.get("pipeline"),
            "source_stage": bt.row_meta.get("stage"),
            "source_json": bt.row_meta.get("json_path"),
            "backtest_json": str(bt.json_path),
        })

    results_df = pd.DataFrame(fresh_rows)
    results_df.sort_values(["total_return_pct", "max_drawdown_pct"], ascending=[False, True], inplace=True)
    all_results_csv = output_dir / "all_stage_results.csv"
    results_df.to_csv(all_results_csv, index=False)
    logger.info("Wrote full backtest results CSV: %s", all_results_csv)

    top_results_df = select_top_from_results(results_df, args.top_n, args.min_return, args.max_dd, args.max_dd_ratio, args.min_trades)
    top_csv = output_dir / "top_strategies.csv"
    top_results_df.to_csv(top_csv, index=False)
    logger.info("Wrote full backtest top strategies CSV: %s", top_csv)

    # Limit dashboard to the best performers for clarity
    top_backtests = sorted(backtest_results, key=lambda bt: bt.result.get("total_return_pct", float('-inf')), reverse=True)[:args.top_n]
    build_dashboard_html(base_data, top_backtests, output_dir, args.price_resample)


if __name__ == "__main__":
    main()
