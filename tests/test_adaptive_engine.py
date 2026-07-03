from core.adaptive_engine import AdaptiveEngine


def make_engine(config=None):
    if config is None:
        config = {"signal_weights": {
            "rsi": 0.2, "macd": 0.2, "bollinger": 0.2,
            "ema_crossover": 0.2, "volume_spike": 0.1, "adx": 0.1
        }}
    return AdaptiveEngine(config)


def test_default_regime():
    ae = make_engine()
    assert ae.get_current_regime() == "ranging"


def test_detect_regime_choppy():
    ae = make_engine()
    assert ae.detect_regime(adx=15, dmp_plus=20, dmp_minus=18) == "choppy"


def test_detect_regime_ranging():
    ae = make_engine()
    assert ae.detect_regime(adx=22, dmp_plus=20, dmp_minus=18) == "ranging"


def test_detect_regime_trending():
    ae = make_engine()
    assert ae.detect_regime(adx=35, dmp_plus=30, dmp_minus=15) == "trending"


def test_detect_regime_strong_trend():
    ae = make_engine()
    assert ae.detect_regime(adx=60, dmp_plus=45, dmp_minus=10) == "strong_trend"


def test_feed_trade_win():
    ae = make_engine()
    ae.feed_trade({"rsi": 80, "macd": 70}, pnl=100.0)
    perf = ae.get_performance()
    assert perf["rsi"]["total_trades"] == 1
    assert perf["rsi"]["win_rate"] == 1.0


def test_feed_trade_loss():
    ae = make_engine()
    ae.feed_trade({"rsi": 80, "macd": 70}, pnl=-50.0)
    perf = ae.get_performance()
    assert perf["rsi"]["total_trades"] == 1
    assert perf["rsi"]["win_rate"] == 0.0


def test_feed_trade_unknown_component():
    ae = make_engine()
    ae.feed_trade({"unknown_signal": 80}, pnl=100.0)
    # Should not crash, just skip
    assert "unknown_signal" not in ae.get_performance()


def test_update_weights_no_data():
    ae = make_engine()
    weights = ae.get_weights()
    # Without any trades, update_weights does nothing
    ae.update_weights()
    assert ae.get_weights() == weights


def test_update_weights_with_trades():
    ae = make_engine()
    # Must exceed min_trades_for_adaptation (default 20)
    for i in range(25):
        ae.feed_trade({"rsi": 80, "macd": 70, "bollinger": 60,
                       "ema_crossover": 90, "volume_spike": 50, "adx": 40},
                      pnl=100.0 if i < 20 else -50.0)
    ae.update_weights()
    weights = ae.get_weights()
    assert abs(sum(weights.values()) - 1.0) < 0.01


def test_update_regime():
    ae = make_engine()
    ae.update_regime("trending")
    assert ae.get_current_regime() == "trending"


def test_get_multipliers():
    ae = make_engine()
    multipliers = ae.get_multipliers("trending")
    assert "position_size_multiplier" in multipliers
    assert "entry_threshold_multiplier" in multipliers
    assert multipliers["position_size_multiplier"] > 0


def test_get_multipliers_unknown_regime():
    ae = make_engine({"signal_weights": {
        "rsi": 0.2}})
    multipliers = ae.get_multipliers("unknown_regime")
    assert multipliers["position_size_multiplier"] == 0.75  # default ranging


def test_get_weights():
    ae = make_engine()
    weights = ae.get_weights()
    assert abs(sum(weights.values()) - 1.0) < 0.01
