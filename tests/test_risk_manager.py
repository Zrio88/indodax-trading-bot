from datetime import datetime, timedelta
from storage.database import TradeStore, TradeRecord
from core.risk_manager import RiskManager


def make_store(tmp_path):
    return TradeStore(str(tmp_path / "risk.db"))


def test_initial_state(tmp_path):
    rm = RiskManager({"initial_balance": 10_000_000, "risk_parameters": {}, "pairs": ["BTC_IDR"]},
                     make_store(tmp_path))
    assert rm.get_balance() == 10_000_000
    assert rm.get_current_drawdown() == 0.0
    assert rm.get_daily_pnl() == 0.0


def test_daily_loss_guard(tmp_path):
    store = make_store(tmp_path)
    rm = RiskManager({"initial_balance": 10_000_000, "risk_parameters": {"daily_loss_limit_pct": 0.02},
                      "pairs": ["BTC_IDR"]}, store)
    rm.daily_pnl[datetime.utcnow().date().isoformat()] = -250_000
    result = rm.can_trade()
    assert not result.can_trade
    assert "Daily loss" in result.reason


def test_daily_loss_within_limit(tmp_path):
    store = make_store(tmp_path)
    rm = RiskManager({"initial_balance": 10_000_000, "risk_parameters": {"daily_loss_limit_pct": 0.02},
                      "pairs": ["BTC_IDR"]}, store)
    rm.daily_pnl[datetime.utcnow().date().isoformat()] = -100_000
    result = rm.can_trade()
    assert result.can_trade


def test_max_drawdown_guard(tmp_path):
    store = make_store(tmp_path)
    rm = RiskManager({"initial_balance": 10_000_000, "risk_parameters": {"max_drawdown_pct": 0.05},
                      "pairs": ["BTC_IDR"]}, store)
    rm.peak_balance = 10_000_000
    rm.paper_balance = 9_400_000
    rm.current_drawdown = (10_000_000 - 9_400_000) / 10_000_000
    result = rm.can_trade()
    assert not result.can_trade
    assert "Max drawdown" in result.reason


def test_max_positions_guard(tmp_path):
    store = make_store(tmp_path)
    for _ in range(2):
        t = TradeRecord(id=0, pair="BTC_IDR", signal="BUY",
                        entry_price=100.0, exit_price=0.0, size=1.0,
                        entry_time=datetime.utcnow(), exit_time=None,
                        stop_loss=95.0, take_profit=110.0,
                        pnl=0.0, pnl_pct=0.0, fee=0.001,
                        status="OPEN", regime="trending",
                        phantom_flags={}, notes="")
        store.add_trade(t)
    rm = RiskManager({"initial_balance": 10_000_000, "risk_parameters": {"max_positions": 2},
                      "pairs": ["BTC_IDR"]}, store)
    result = rm.can_trade()
    assert not result.can_trade
    assert "Max positions" in result.reason


def test_balance_guard(tmp_path):
    store = make_store(tmp_path)
    rm = RiskManager({"initial_balance": 50_000, "risk_parameters": {},
                      "pairs": ["BTC_IDR"]}, store)
    rm.paper_balance = 50_000
    result = rm.can_trade()
    assert not result.can_trade
    assert "Insufficient balance" in result.reason


def test_allowed_pairs_guard(tmp_path):
    store = make_store(tmp_path)
    rm = RiskManager({"initial_balance": 10_000_000, "risk_parameters": {},
                      "pairs": ["BTC_IDR"]}, store)
    result = rm.can_trade("ETH_IDR")
    assert not result.can_trade
    assert "not allowed" in result.reason
    assert result.allowed_pairs == ["BTC_IDR"]


def test_can_trade_passes(tmp_path):
    store = make_store(tmp_path)
    rm = RiskManager({"initial_balance": 10_000_000, "risk_parameters": {},
                      "pairs": ["BTC_IDR"]}, store)
    result = rm.can_trade("BTC_IDR")
    assert result.can_trade


def test_position_size_basic(tmp_path):
    store = make_store(tmp_path)
    rm = RiskManager({"initial_balance": 10_000_000, "risk_parameters": {
        "kelly_fraction": 0.5, "regime_multipliers": {"trending": 1.0}
    }, "exchange": {"min_order_size": 0.0001}}, store)
    result = rm.position_size(pair="BTC_IDR", entry_price=100.0,
                               stop_loss=95.0, signal_score=50.0,
                               phantom_penalty=0.0, regime="trending")
    assert result.size > 0
    assert result.size_idr > 0
    assert result.risk_pct > 0


def test_position_size_with_phantom_penalty(tmp_path):
    store = make_store(tmp_path)
    rm = RiskManager({"initial_balance": 10_000_000, "risk_parameters": {
        "kelly_fraction": 0.5, "regime_multipliers": {"trending": 1.0}
    }, "exchange": {"min_order_size": 0.0001}}, store)
    r1 = rm.position_size("BTC_IDR", 100.0, 95.0, 50.0, 0.0, "trending")
    r2 = rm.position_size("BTC_IDR", 100.0, 95.0, 50.0, 0.5, "trending")
    assert r2.size < r1.size


def test_position_size_zero_on_invalid(tmp_path):
    store = make_store(tmp_path)
    rm = RiskManager({"initial_balance": 10_000_000, "risk_parameters": {},
                      "exchange": {"min_order_size": 0.0001}}, store)
    result = rm.position_size("BTC_IDR", 0, 0, 50.0, 0.0, "trending")
    assert result.size == 0
    assert result.size_idr == 0


def test_update_balance(tmp_path):
    store = make_store(tmp_path)
    rm = RiskManager({"initial_balance": 10_000_000, "risk_parameters": {},
                      "pairs": ["BTC_IDR"]}, store)
    rm.update_balance(500_000, "BTC_IDR")
    assert rm.get_balance() == 10_500_000
    assert rm.get_daily_pnl() == 500_000


def test_update_balance_drawdown(tmp_path):
    store = make_store(tmp_path)
    rm = RiskManager({"initial_balance": 10_000_000, "risk_parameters": {},
                      "pairs": ["BTC_IDR"]}, store)
    rm.update_balance(-1_000_000, "BTC_IDR")
    assert rm.get_balance() == 9_000_000
    assert rm.get_current_drawdown() > 0


def test_update_last_trade(tmp_path):
    store = make_store(tmp_path)
    rm = RiskManager({"initial_balance": 10_000_000, "risk_parameters": {},
                      "pairs": ["BTC_IDR"]}, store)
    rm.update_last_trade("BTC_IDR")
    assert "BTC_IDR" in rm.last_trade_time


def test_loss_streak_guard(tmp_path):
    store = make_store(tmp_path)
    # Create losing trades via close_trade (sets pnl in DB)
    for i in range(4):
        t = TradeRecord(id=0, pair="BTC_IDR", signal="BUY",
                        entry_price=100.0, exit_price=0.0, size=1.0,
                        entry_time=datetime.utcnow() - timedelta(hours=(10 - i)),
                        exit_time=None,
                        stop_loss=95.0, take_profit=110.0,
                        pnl=0.0, pnl_pct=0.0, fee=0.001,
                        status="OPEN", regime="trending",
                        phantom_flags={}, notes="")
        tid = store.add_trade(t)
        store.close_trade(tid, 90.0, datetime.utcnow())
    rm = RiskManager({"initial_balance": 10_000_000, "risk_parameters": {
        "max_loss_streak": 3, "cooldown_minutes": 60
    }, "pairs": ["BTC_IDR"]}, store)
    rm.last_trade_time["BTC_IDR"] = datetime.utcnow()
    result = rm.can_trade("BTC_IDR")
    assert not result.can_trade
    assert "Loss streak" in result.reason
