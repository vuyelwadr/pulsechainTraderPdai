import pandas as pd

from pdai_trader.config import Settings
from pdai_trader.optimization import StrategyOptimizer
from pdai_trader.strategies.ma_crossover import MovingAverageCrossover
from pdai_trader.trading.backtest import BacktestEngine


SAMPLE_DATA = Settings.DATA_DIR / "sample" / "pdai_ohlcv_sample.csv"


def load_sample_frame():
    df = pd.read_csv(SAMPLE_DATA)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    if "price" not in df:
        df["price"] = df["close"]
    return df


def test_backtest_runs_repeatedly_on_sample_dataset():
    data = load_sample_frame()
    strategy = MovingAverageCrossover({
        "short_period": 2,
        "long_period": 3,
        "min_strength": 0.0,
    })
    engine = BacktestEngine(initial_balance=1_000)

    results = []
    for _ in range(5):
        outcome = engine.run_backtest(strategy, data)
        assert "error" not in outcome
        assert outcome["data_points"] == len(data)
        results.append(outcome)

    final_balances = {round(r["final_balance"], 8) for r in results}
    assert len(final_balances) == 1


def test_sample_dataset_resamples_to_eight_hours_cleanly():
    data = load_sample_frame()
    assert len(data) == 4

    resampled = (
        data.set_index("timestamp")
        .resample("8h")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume_pdai": "sum"})
        .dropna()
    )
    assert len(resampled) == 4


def test_optimizer_generates_report(tmp_path):
    data = load_sample_frame()
    optimizer = StrategyOptimizer(data, output_root=tmp_path)
    results = optimizer.optimise(strategies=["MovingAverageCrossover"], timeframes=["8h"], trials=3)
    assert len(results) == 1
    report = tmp_path / "MovingAverageCrossover_8h.json"
    assert report.exists()
