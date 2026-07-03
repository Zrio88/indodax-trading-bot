from config.settings import Settings


def test_settings_defaults():
    s = Settings()
    assert s.pairs == ["BTC_IDR"]
    assert s.timeframe == "1h"
    assert s.initial_balance == 10_000_000
    assert s.mode == "paper"
    assert s.stop_loss_pct == 0.05
    assert s.take_profit_r == 2.0


def test_settings_signal_weights():
    s = Settings()
    weights = s.signal_weights
    assert abs(sum(weights.values()) - 1.0) < 0.01
    assert "rsi" in weights
    assert "macd" in weights


def test_settings_risk_params():
    s = Settings()
    rp = s.risk_parameters
    assert rp["max_drawdown_pct"] == 0.05
    assert rp["daily_loss_limit_pct"] == 0.02
    assert rp["max_positions"] == 3
    assert rp["kelly_fraction"] == 0.5
