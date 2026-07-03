from core.phantom_detector import PhantomDetector


def make_candle(open_p, high, low, close, volume=1000):
    return {"open": open_p, "high": high, "low": low, "close": close, "volume": volume}


def pd():
    """Create PhantomDetector with default thresholds (no phantom_thresholds key)"""
    return PhantomDetector({})


def test_default_thresholds():
    d = PhantomDetector({})
    t = d.thresholds
    assert t["wash_trade_volume_multiplier"] == 6.0
    assert t["pump_dump_threshold"] == 0.15
    assert t["doji_manipulation_size"] == 0.001
    assert t["consecutive_bullish"] == 8
    assert t["spread_anomaly_pct"] == 0.03


def test_no_candles_no_flags():
    d = pd()
    flags = d.detect("BTC_IDR")
    assert flags.score == 0.0
    assert not flags.wash_trade


def test_wash_trade():
    d = pd()
    for _ in range(10):
        d.update("BTC_IDR", make_candle(100, 101, 99, 100))
    d.update("BTC_IDR", make_candle(100, 101, 99, 100, volume=7000))
    flags = d.detect("BTC_IDR")
    assert flags.wash_trade
    assert flags.score >= 30


def test_no_wash_trade_with_price_move():
    d = pd()
    for _ in range(10):
        d.update("BTC_IDR", make_candle(100, 101, 99, 100))
    d.update("BTC_IDR", make_candle(105, 106, 104, 105, volume=7000))
    flags = d.detect("BTC_IDR")
    assert not flags.wash_trade


def test_pump_dump():
    d = pd()
    for i in range(5):
        d.update("BTC_IDR", make_candle(100, 101, 99, 100 + i * 4))
    flags = d.detect("BTC_IDR")
    assert flags.pump_dump
    assert flags.score >= 40


def test_no_pump_dump_small_move():
    d = pd()
    for i in range(5):
        d.update("BTC_IDR", make_candle(100, 101, 99, 100 + i))
    flags = d.detect("BTC_IDR")
    assert not flags.pump_dump


def test_doji_manipulation():
    d = pd()
    for _ in range(6):
        d.update("BTC_IDR", make_candle(100, 102, 98, 101, volume=1000))
    d.update("BTC_IDR", make_candle(100.0005, 110, 90, 100.001, volume=3000))
    flags = d.detect("BTC_IDR")
    assert flags.doji_manipulation
    assert flags.score >= 25


def test_no_doji_without_volume():
    d = pd()
    for _ in range(6):
        d.update("BTC_IDR", make_candle(100, 102, 98, 101, volume=1000))
    d.update("BTC_IDR", make_candle(100.0005, 110, 90, 100.001, volume=1000))
    flags = d.detect("BTC_IDR")
    assert not flags.doji_manipulation


def test_consecutive_bullish():
    d = PhantomDetector({"phantom_thresholds": {
        "wash_trade_volume_multiplier": 6.0,
        "pump_dump_threshold": 0.15,
        "doji_manipulation_size": 0.001,
        "spread_anomaly_pct": 0.03,
        "consecutive_bullish": 5
    }})
    for i in range(10):
        d.update("BTC_IDR", make_candle(100, 102, 98, 100 + i))
    flags = d.detect("BTC_IDR")
    assert flags.consecutive_bullish
    assert flags.score >= 20


def test_consecutive_bearish():
    d = PhantomDetector({"phantom_thresholds": {
        "wash_trade_volume_multiplier": 6.0,
        "pump_dump_threshold": 0.15,
        "doji_manipulation_size": 0.001,
        "spread_anomaly_pct": 0.03,
        "consecutive_bullish": 5
    }})
    for i in range(10):
        d.update("BTC_IDR", make_candle(100, 102, 98, 100 - i))
    flags = d.detect("BTC_IDR")
    assert flags.consecutive_bearish
    assert flags.score >= 20


def test_spread_anomaly():
    d = pd()
    for _ in range(4):
        d.update("BTC_IDR", make_candle(100, 102, 98, 101))
    d.update("BTC_IDR", make_candle(100, 120, 90, 105))
    flags = d.detect("BTC_IDR")
    assert flags.spread_anomaly


def test_spread_ratio_exact():
    d = pd()
    d.update("BTC_IDR", make_candle(100, 102, 98, 101))
    d.update("BTC_IDR", make_candle(100, 101, 99, 100))
    flags = d.detect("BTC_IDR")
    # spread went from 4/98=4.08% to 2/99=2.02%, ratio < 1.03
    assert not flags.spread_anomaly


def test_penalty_factor():
    d = pd()
    flags = d.detect("BTC_IDR")
    assert d.penalty_factor(flags) == 0.0

    flags.score = 50
    assert d.penalty_factor(flags) == 0.5

    flags.score = 85
    assert d.penalty_factor(flags) == 1.0


def test_clear_history():
    d = pd()
    d.update("BTC_IDR", make_candle(100, 101, 99, 100))
    assert d.get_history("BTC_IDR") is not None
    d.clear_history("BTC_IDR")
    assert d.get_history("BTC_IDR") is None


def test_clear_all_history():
    d = pd()
    d.update("BTC_IDR", make_candle(100, 101, 99, 100))
    d.update("ETH_IDR", make_candle(100, 101, 99, 100))
    d.clear_history()
    assert d.get_history("BTC_IDR") is None
    assert d.get_history("ETH_IDR") is None


def test_insufficient_data():
    d = pd()
    d.update("BTC_IDR", make_candle(100, 101, 99, 100))
    flags = d.detect("BTC_IDR")
    assert flags.score == 0.0


def test_missing_columns():
    d = pd()
    d.update("BTC_IDR", {"open": 100, "high": 101, "low": 99, "close": 100})
    flags = d.detect("BTC_IDR")
    assert flags.score == 0.0


def test_all_detection_types_count():
    d = PhantomDetector({"phantom_thresholds": {
        "wash_trade_volume_multiplier": 6.0,
        "pump_dump_threshold": 0.15,
        "doji_manipulation_size": 0.001,
        "spread_anomaly_pct": 0.03,
        "consecutive_bullish": 3
    }})
    for _ in range(10):
        d.update("BTC_IDR", make_candle(100, 101, 99, 100))
    d.update("BTC_IDR", make_candle(100, 101, 99, 100, volume=7000))
    for i in range(10):
        d.update("BTC_IDR", make_candle(100, 102, 98, 100 + i))
    flags = d.detect("BTC_IDR")
    assert flags.score > 0
