import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import datetime, timedelta
from storage.database import TradeRecord, TradeStore
from core.risk_manager import RiskManager


@pytest.fixture
def sample_config():
    return {
        "pairs": ["BTC_IDR", "ETH_IDR"],
        "timeframe": "1h",
        "mode": "paper",
        "initial_balance": 10_000_000,
        "stop_loss_pct": 0.05,
        "take_profit_r": 2.0,
        "signal_weights": {
            "rsi": 0.15, "macd": 0.20, "bollinger": 0.15,
            "ema_crossover": 0.20, "volume_spike": 0.10,
            "adx": 0.10, "stochastic": 0.10
        },
        "phantom_thresholds": {
            "wash_trade_volume_multiplier": 6.0,
            "pump_dump_threshold": 0.15,
            "doji_manipulation_size": 0.001,
            "spread_anomaly_pct": 0.03,
            "consecutive_bullish": 8
        },
        "adaptive_settings": {
            "adx_choppy_threshold": 20,
            "adx_ranging_threshold": 25,
            "adx_trending_threshold": 50,
            "min_trades_for_adaptation": 20,
            "weight_adjustment_step": 0.05
        },
        "risk_parameters": {
            "daily_loss_limit_pct": 0.02,
            "max_drawdown_pct": 0.05,
            "max_loss_streak": 3,
            "max_positions": 3,
            "cooldown_minutes": 30,
            "kelly_fraction": 0.5,
            "regime_multipliers": {
                "choppy": 0.5, "ranging": 0.75,
                "trending": 1.25, "strong_trend": 1.5, "volatile": 0.25
            }
        },
        "exchange": {
            "rate_limit": 100, "min_order_size": 0.0001,
            "fee_pct": 0.002, "slippage_pct": 0.001
        }
    }


@pytest.fixture
def sample_candle():
    return {
        "timestamp": datetime.utcnow(),
        "open": 100.0, "high": 105.0, "low": 99.0,
        "close": 103.0, "volume": 1000.0
    }


@pytest.fixture
def sample_candles():
    base_time = datetime.utcnow()
    candles = []
    for i in range(100):
        t = base_time - timedelta(hours=99 - i)
        candles.append({
            "timestamp": t,
            "open": 100 + i * 0.5,
            "high": 100 + i * 0.5 + 5,
            "low": 100 + i * 0.5 - 5,
            "close": 100 + i * 0.5 + 2,
            "volume": 1000 + i
        })
    return candles


@pytest.fixture
def trade_store(tmp_path):
    db_path = str(tmp_path / "test_trades.db")
    store = TradeStore(db_path)
    yield store
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def open_trade():
    return TradeRecord(
        id=1, pair="BTC_IDR", signal="BUY",
        entry_price=100.0, exit_price=0.0, size=1.0,
        entry_time=datetime.utcnow() - timedelta(hours=2),
        exit_time=None, stop_loss=95.0, take_profit=110.0,
        pnl=0.0, pnl_pct=0.0, fee=0.001,
        status="OPEN", regime="trending",
        phantom_flags={}, notes="test trade"
    )


@pytest.fixture
def closed_trade():
    return TradeRecord(
        id=1, pair="BTC_IDR", signal="BUY",
        entry_price=100.0, exit_price=110.0, size=1.0,
        entry_time=datetime.utcnow() - timedelta(hours=24),
        exit_time=datetime.utcnow(),
        stop_loss=95.0, take_profit=110.0,
        pnl=10.0, pnl_pct=10.0, fee=0.001,
        status="CLOSED", regime="trending",
        phantom_flags={}, notes="test trade"
    )


@pytest.fixture
def open_trade_store(tmp_path):
    """TradeStore with an open trade pre-populated"""
    db_path = str(tmp_path / "open_trades.db")
    store = TradeStore(db_path)
    trade = TradeRecord(
        id=0, pair="BTC_IDR", signal="BUY",
        entry_price=100.0, exit_price=0.0, size=1.0,
        entry_time=datetime.utcnow() - timedelta(hours=2),
        exit_time=None, stop_loss=95.0, take_profit=110.0,
        pnl=0.0, pnl_pct=0.0, fee=0.001,
        status="OPEN", regime="trending",
        phantom_flags={}, notes=""
    )
    store.add_trade(trade)
    return store


@pytest.fixture
def exit_manager(tmp_path):
    """Empty TradeStore for exit manager tests"""
    return TradeStore(str(tmp_path / "exit_test.db"))
