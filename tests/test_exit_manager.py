from datetime import datetime, timedelta
from core.exit_manager import ExitManager, ExitSignal
from storage.database import TradeRecord, TradeStore


def make_buy_trade(entry=100.0, sl=95.0, tp=110.0, size=1.0,
                   entry_age_hours=2, fee=0.001):
    return TradeRecord(
        id=0, pair="BTC_IDR", signal="BUY",
        entry_price=entry, exit_price=0.0, size=size,
        entry_time=datetime.utcnow() - timedelta(hours=entry_age_hours),
        exit_time=None, stop_loss=sl, take_profit=tp,
        pnl=0.0, pnl_pct=0.0, fee=fee,
        status="OPEN", regime="trending",
        phantom_flags={}, notes=""
    )


def test_stop_loss_hit(tmp_path):
    store = TradeStore(str(tmp_path / "sl_test.db"))
    tid = store.add_trade(make_buy_trade())
    em = ExitManager({"stop_loss_pct": 0.05, "take_profit_r": 2.0}, store)
    signals = em.check("BTC_IDR", 94.0, datetime.utcnow())
    assert len(signals) == 1
    assert signals[0].trade_id == tid
    assert signals[0].action == "CLOSE"
    assert "Stop Loss" in signals[0].reason


def test_take_profit_hit(tmp_path):
    store = TradeStore(str(tmp_path / "tp_test.db"))
    tid = store.add_trade(make_buy_trade())
    em = ExitManager({"stop_loss_pct": 0.05, "take_profit_r": 2.0}, store)
    signals = em.check("BTC_IDR", 110.0, datetime.utcnow())
    assert len(signals) == 1
    assert signals[0].trade_id == tid
    assert signals[0].action == "CLOSE"
    assert "Take Profit" in signals[0].reason


def test_no_exit_when_price_between_sl_tp(tmp_path):
    store = TradeStore(str(tmp_path / "mid_test.db"))
    store.add_trade(make_buy_trade())
    em = ExitManager({"stop_loss_pct": 0.05, "take_profit_r": 2.0}, store)
    signals = em.check("BTC_IDR", 98.0, datetime.utcnow())
    assert len(signals) == 0


def test_breakeven(tmp_path):
    store = TradeStore(str(tmp_path / "be_test.db"))
    store.add_trade(make_buy_trade())
    em = ExitManager({"stop_loss_pct": 0.05, "take_profit_r": 2.0}, store)
    signals = em.check("BTC_IDR", 101.0, datetime.utcnow())
    assert len(signals) == 1
    assert signals[0].action == "BREAKEVEN"
    assert "Breakeven" in signals[0].reason


def test_time_stop(tmp_path):
    store = TradeStore(str(tmp_path / "ts_test.db"))
    store.add_trade(make_buy_trade(entry_age_hours=25))
    em = ExitManager({"stop_loss_pct": 0.05, "take_profit_r": 2.0}, store)
    signals = em.check("BTC_IDR", 99.0, datetime.utcnow())
    assert len(signals) == 1
    assert signals[0].action == "CLOSE"
    assert "Time Stop" in signals[0].reason


def test_no_time_stop_before_24h(tmp_path):
    store = TradeStore(str(tmp_path / "nts_test.db"))
    store.add_trade(make_buy_trade(entry_age_hours=23))
    em = ExitManager({"stop_loss_pct": 0.05, "take_profit_r": 2.0}, store)
    signals = em.check("BTC_IDR", 99.0, datetime.utcnow())
    assert len(signals) == 0


def test_multiple_trades_independent(tmp_path):
    store = TradeStore(str(tmp_path / "multi_test.db"))
    tid1 = store.add_trade(make_buy_trade(entry=100.0, sl=97.0, tp=110.0))
    t2 = TradeRecord(id=0, pair="BTC_IDR", signal="SELL",
                     entry_price=200.0, exit_price=0.0, size=1.0,
                     entry_time=datetime.utcnow() - timedelta(hours=2),
                     exit_time=None, stop_loss=199.0, take_profit=50.0,
                     pnl=0.0, pnl_pct=0.0, fee=0.001,
                     status="OPEN", regime="trending", phantom_flags={}, notes="")
    tid2 = store.add_trade(t2)
    em = ExitManager({"stop_loss_pct": 0.05, "take_profit_r": 2.0}, store)
    signals = em.check("BTC_IDR", 96.0, datetime.utcnow())
    assert len(signals) == 1
    assert signals[0].trade_id == tid1  # Only BUY SL at 97 hit (96 <= 97); SELL TP at 50 not hit (96 > 50)


def test_sell_stop_loss(tmp_path):
    store = TradeStore(str(tmp_path / "sell_sl.db"))
    trade = TradeRecord(
        id=0, pair="BTC_IDR", signal="SELL",
        entry_price=100.0, exit_price=0.0, size=1.0,
        entry_time=datetime.utcnow() - timedelta(hours=2),
        exit_time=None, stop_loss=105.0, take_profit=90.0,
        pnl=0.0, pnl_pct=0.0, fee=0.001,
        status="OPEN", regime="trending", phantom_flags={}, notes=""
    )
    tid = store.add_trade(trade)
    em = ExitManager({"stop_loss_pct": 0.05, "take_profit_r": 2.0}, store)
    signals = em.check("BTC_IDR", 106.0, datetime.utcnow())
    assert len(signals) == 1
    assert signals[0].action == "CLOSE"
    assert "Stop Loss" in signals[0].reason


def test_sell_take_profit(tmp_path):
    store = TradeStore(str(tmp_path / "sell_tp.db"))
    trade = TradeRecord(
        id=0, pair="BTC_IDR", signal="SELL",
        entry_price=100.0, exit_price=0.0, size=1.0,
        entry_time=datetime.utcnow() - timedelta(hours=2),
        exit_time=None, stop_loss=105.0, take_profit=90.0,
        pnl=0.0, pnl_pct=0.0, fee=0.001,
        status="OPEN", regime="trending", phantom_flags={}, notes=""
    )
    tid = store.add_trade(trade)
    em = ExitManager({"stop_loss_pct": 0.05, "take_profit_r": 2.0}, store)
    signals = em.check("BTC_IDR", 89.0, datetime.utcnow())
    assert len(signals) == 1
    assert signals[0].action == "CLOSE"
    assert "Take Profit" in signals[0].reason


def test_no_signals_for_other_pair(tmp_path):
    store = TradeStore(str(tmp_path / "pair_test.db"))
    tid = store.add_trade(make_buy_trade())
    em = ExitManager({"stop_loss_pct": 0.05, "take_profit_r": 2.0}, store)
    signals = em.check("ETH_IDR", 94.0, datetime.utcnow())
    assert len(signals) == 0


def test_execute_close(tmp_path):
    store = TradeStore(str(tmp_path / "exec_test.db"))
    tid = store.add_trade(make_buy_trade())
    em = ExitManager({"stop_loss_pct": 0.05, "take_profit_r": 2.0}, store)
    signal = ExitSignal(pair="BTC_IDR", trade_id=tid, action="CLOSE",
                        price=110.0, reason="Test")
    result = em.execute_exit(signal, exchange=None, risk_manager=DummyRM())
    assert result["success"] is True
    assert result["action"] == "CLOSE"
    assert result["pnl"] > 0

    updated = store.get_trade(tid)
    assert updated.status == "CLOSED"


def test_execute_breakeven(tmp_path):
    store = TradeStore(str(tmp_path / "exec_be.db"))
    tid = store.add_trade(make_buy_trade())
    em = ExitManager({"stop_loss_pct": 0.05, "take_profit_r": 2.0}, store)
    signal = ExitSignal(pair="BTC_IDR", trade_id=tid, action="BREAKEVEN",
                        price=100.0, reason="BE")
    result = em.execute_exit(signal, exchange=None, risk_manager=DummyRM())
    assert result["success"] is True
    assert result["action"] == "BREAKEVEN"
    assert result["new_stop_loss"] == 100.0

    updated = store.get_trade(tid)
    assert updated.stop_loss == 100.0


def test_execute_trade_not_found(tmp_path):
    store = TradeStore(str(tmp_path / "nf_test.db"))
    em = ExitManager({"stop_loss_pct": 0.05, "take_profit_r": 2.0}, store)
    signal = ExitSignal(pair="BTC_IDR", trade_id=999, action="CLOSE",
                        price=100.0, reason="No trade")
    result = em.execute_exit(signal, exchange=None, risk_manager=DummyRM())
    assert result["success"] is False
    assert "not found" in result["error"]


def test_execute_unknown_action(tmp_path):
    store = TradeStore(str(tmp_path / "ua_test.db"))
    tid = store.add_trade(make_buy_trade())
    em = ExitManager({"stop_loss_pct": 0.05, "take_profit_r": 2.0}, store)
    signal = ExitSignal(pair="BTC_IDR", trade_id=tid, action="INVALID",
                        price=100.0, reason="Test")
    result = em.execute_exit(signal, exchange=None, risk_manager=DummyRM())
    assert result["success"] is False
    assert "Unknown action" in result["error"]


class DummyRM:
    def record_trade(self, trade_id, pnl, pair):
        pass
