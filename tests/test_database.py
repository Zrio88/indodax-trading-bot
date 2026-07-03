from datetime import datetime, timedelta
from storage.database import TradeRecord


def test_add_and_get_trade(trade_store, open_trade):
    trade_id = trade_store.add_trade(open_trade)
    assert trade_id > 0

    fetched = trade_store.get_trade(trade_id)
    assert fetched is not None
    assert fetched.pair == "BTC_IDR"
    assert fetched.signal == "BUY"
    assert fetched.entry_price == 100.0
    assert fetched.status == "OPEN"


def test_open_trades(trade_store, open_trade):
    trade_store.add_trade(open_trade)
    open_list = trade_store.open_trades()
    assert len(open_list) == 1
    assert open_list[0].pair == "BTC_IDR"

    pair_filtered = trade_store.open_trades("ETH_IDR")
    assert len(pair_filtered) == 0


def test_close_trade(trade_store, open_trade):
    trade_id = trade_store.add_trade(open_trade)
    exit_time = datetime.utcnow()
    result = trade_store.close_trade(trade_id, 110.0, exit_time)
    assert result is True

    closed = trade_store.get_trade(trade_id)
    assert closed.status == "CLOSED"
    assert closed.exit_price == 110.0
    assert closed.exit_time is not None

    # BUY at 100, sell at 110, size=1, fee=0.001 => pnl = (110-100)*1 - 0.001 = 9.999
    assert abs(closed.pnl - 9.999) < 0.001


def test_close_trade_already_closed(trade_store, open_trade):
    trade_id = trade_store.add_trade(open_trade)
    trade_store.close_trade(trade_id, 110.0, datetime.utcnow())
    result = trade_store.close_trade(trade_id, 115.0, datetime.utcnow())
    assert result is False


def test_update_trade(trade_store, open_trade):
    trade_id = trade_store.add_trade(open_trade)
    exit_time = datetime.utcnow()
    result = trade_store.update_trade(trade_id, 105.0, exit_time, 5.0, 5.0, "BREAKEVEN")
    assert result is True

    updated = trade_store.get_trade(trade_id)
    assert updated.status == "BREAKEVEN"
    assert updated.exit_price == 105.0


def test_breakeven_trade(trade_store, open_trade):
    trade_id = trade_store.add_trade(open_trade)
    result = trade_store.breakeven_trade(trade_id, 100.0)
    assert result is True

    updated = trade_store.get_trade(trade_id)
    assert updated.stop_loss == 100.0


def test_get_nonexistent_trade(trade_store):
    assert trade_store.get_trade(999) is None


def test_rolling_metrics_empty(trade_store):
    metrics = trade_store.rolling_metrics(30)
    assert metrics["total_trades"] == 0
    assert metrics["win_rate"] == 0.0


def test_rolling_metrics_with_trades(trade_store):
    t1 = TradeRecord(
        id=0, pair="BTC_IDR", signal="BUY",
        entry_price=100.0, exit_price=0.0, size=1.0,
        entry_time=datetime.utcnow() - timedelta(hours=48),
        exit_time=None,
        stop_loss=95.0, take_profit=110.0,
        pnl=0.0, pnl_pct=0.0, fee=0.001,
        status="OPEN", regime="trending",
        phantom_flags={}, notes=""
    )
    trade_id = trade_store.add_trade(t1)
    trade_store.close_trade(trade_id, 110.0, datetime.utcnow() - timedelta(hours=24))

    t2 = TradeRecord(
        id=0, pair="BTC_IDR", signal="BUY",
        entry_price=100.0, exit_price=0.0, size=1.0,
        entry_time=datetime.utcnow() - timedelta(hours=24),
        exit_time=None,
        stop_loss=95.0, take_profit=110.0,
        pnl=0.0, pnl_pct=0.0, fee=0.001,
        status="OPEN", regime="trending",
        phantom_flags={}, notes=""
    )
    trade_id2 = trade_store.add_trade(t2)
    trade_store.close_trade(trade_id2, 90.0, datetime.utcnow())

    metrics = trade_store.rolling_metrics(30)
    assert metrics["total_trades"] == 2
    assert metrics["win_rate"] == 0.5
    assert abs(metrics["total_pnl"] - (-0.002)) < 0.05  # ~0 with 1 win + 1 loss canceling


def test_loss_streak(trade_store):
    # Create trades using close_trade to ensure pnl is set in DB
    t = TradeRecord(
        id=0, pair="BTC_IDR", signal="BUY",
        entry_price=100.0, exit_price=0.0, size=1.0,
        entry_time=datetime.utcnow() - timedelta(hours=100),
        exit_time=None,
        stop_loss=95.0, take_profit=110.0,
        pnl=0.0, pnl_pct=0.0, fee=0.001,
        status="OPEN", regime="trending",
        phantom_flags={}, notes=""
    )
    trade_id1 = trade_store.add_trade(t)
    trade_store.close_trade(trade_id1, 90.0, datetime.utcnow() - timedelta(hours=96))

    t2 = TradeRecord(
        id=0, pair="BTC_IDR", signal="BUY",
        entry_price=100.0, exit_price=0.0, size=1.0,
        entry_time=datetime.utcnow() - timedelta(hours=50),
        exit_time=None,
        stop_loss=95.0, take_profit=110.0,
        pnl=0.0, pnl_pct=0.0, fee=0.001,
        status="OPEN", regime="trending",
        phantom_flags={}, notes=""
    )
    trade_id2 = trade_store.add_trade(t2)
    trade_store.close_trade(trade_id2, 92.0, datetime.utcnow() - timedelta(hours=48))

    t3 = TradeRecord(
        id=0, pair="BTC_IDR", signal="BUY",
        entry_price=100.0, exit_price=0.0, size=1.0,
        entry_time=datetime.utcnow() - timedelta(hours=2),
        exit_time=None,
        stop_loss=95.0, take_profit=110.0,
        pnl=0.0, pnl_pct=0.0, fee=0.001,
        status="OPEN", regime="trending",
        phantom_flags={}, notes=""
    )
    trade_id3 = trade_store.add_trade(t3)
    trade_store.close_trade(trade_id3, 93.0, datetime.utcnow())

    assert trade_store.loss_streak() == 3


def test_loss_streak_break(trade_store):
    # Add win first, then loss — streak should be 1
    t1 = TradeRecord(
        id=0, pair="BTC_IDR", signal="BUY",
        entry_price=100.0, exit_price=0.0, size=1.0,
        entry_time=datetime.utcnow() - timedelta(hours=48),
        exit_time=None,
        stop_loss=95.0, take_profit=110.0,
        pnl=0.0, pnl_pct=0.0, fee=0.001,
        status="OPEN", regime="trending",
        phantom_flags={}, notes=""
    )
    trade_id1 = trade_store.add_trade(t1)
    trade_store.close_trade(trade_id1, 110.0, datetime.utcnow() - timedelta(hours=24))

    t2 = TradeRecord(
        id=0, pair="BTC_IDR", signal="BUY",
        entry_price=100.0, exit_price=0.0, size=1.0,
        entry_time=datetime.utcnow() - timedelta(hours=2),
        exit_time=None,
        stop_loss=95.0, take_profit=110.0,
        pnl=0.0, pnl_pct=0.0, fee=0.001,
        status="OPEN", regime="trending",
        phantom_flags={}, notes=""
    )
    trade_id2 = trade_store.add_trade(t2)
    trade_store.close_trade(trade_id2, 90.0, datetime.utcnow())

    assert trade_store.loss_streak() == 1


def test_total_pnl(trade_store):
    for exit_price in [110.0, 95.0, 103.0]:
        t = TradeRecord(
            id=0, pair="BTC_IDR", signal="BUY",
            entry_price=100.0, exit_price=0.0, size=1.0,
            entry_time=datetime.utcnow(), exit_time=None,
            stop_loss=95.0, take_profit=110.0,
            pnl=0.0, pnl_pct=0.0, fee=0.001,
            status="OPEN", regime="trending",
            phantom_flags={}, notes=""
        )
        tid = trade_store.add_trade(t)
        trade_store.close_trade(tid, exit_price, datetime.utcnow())

    total = trade_store.total_pnl()
    assert total > 0  # (10 - 5 + 3 - 3*0.001) = 7.997


def test_candle_cache(trade_store):
    candle = {
        "timestamp": datetime.utcnow(),
        "open": 100.0, "high": 105.0, "low": 99.0,
        "close": 103.0, "volume": 1000.0
    }
    assert trade_store.add_candle("BTC_IDR", "1h", candle) is True

    candles = trade_store.get_candles("BTC_IDR", "1h", limit=10)
    assert len(candles) == 1
    assert candles[0]["close"] == 103.0
