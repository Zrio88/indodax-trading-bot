"""
Pydantic Settings for Indodax Trading Bot
Central configuration manager with environment variable support
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Dict, List, Any
import json


class Settings(BaseSettings):
    """
    Central configuration for the trading bot.
    Supports both environment variables and config.json
    """
    
    # ===== Trading Parameters =====
    pairs: List[str] = Field(
        default_factory=lambda: ["BTC_IDR"],
        description="List of trading pairs to monitor"
    )
    timeframe: str = Field(
        default="1h",
        description="Timeframe for candle data (1m, 5m, 15m, 1h, 4h, 1d)"
    )
    initial_balance: float = Field(
        default=10_000_000,
        description="Initial balance in IDR"
    )
    mode: str = Field(
        default="paper",
        description="Trading mode: backtest, paper, live"
    )
    
    # ===== Risk Parameters =====
    stop_loss_pct: float = Field(
        default=0.05,
        description="Stop loss percentage (5% = 0.05)"
    )
    take_profit_r: float = Field(
        default=2.0,
        description="Take profit ratio (2x stop loss)"
    )
    
    # ===== Signal Weights (Dinamis) =====
    signal_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "rsi": 0.15,
            "macd": 0.20,
            "bollinger": 0.15,
            "ema_crossover": 0.20,
            "volume_spike": 0.10,
            "adx": 0.10,
            "stochastic": 0.10
        },
        description="Weights for each signal component (sum to 1.0)"
    )
    
    # ===== Phantom Detection Thresholds =====
    phantom_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "wash_trade_volume_multiplier": 6.0,
            "pump_dump_threshold": 0.15,
            "doji_manipulation_size": 0.001,
            "spread_anomaly_pct": 0.03,
            "consecutive_bullish": 8
        },
        description="Thresholds for detecting market manipulation"
    )
    
    # ===== Adaptive Engine Settings =====
    adaptive_settings: Dict[str, Any] = Field(
        default_factory=lambda: {
            "adx_choppy_threshold": 20,
            "adx_ranging_threshold": 25,
            "adx_trending_threshold": 50,
            "min_trades_for_adaptation": 20,
            "weight_adjustment_step": 0.05
        },
        description="Settings for adaptive weight adjustment"
    )
    
    # ===== Risk Management =====
    risk_parameters: Dict[str, Any] = Field(
        default_factory=lambda: {
            "daily_loss_limit_pct": 0.02,    # 2% daily loss limit
            "max_drawdown_pct": 0.05,         # 5% max drawdown
            "max_loss_streak": 3,              # Max 3 consecutive losses
            "max_positions": 3,                # Max 3 open positions
            "cooldown_minutes": 30,            # 30 min cooldown
            "kelly_fraction": 0.5,             # Half-Kelly sizing
            "regime_multipliers": {
                "choppy": 0.5,
                "ranging": 0.75,
                "trending": 1.25,
                "strong_trend": 1.5,
                "volatile": 0.25
            }
        },
        description="Risk management parameters"
    )
    
    # ===== Exchange Settings =====
    exchange: Dict[str, Any] = Field(
        default_factory=lambda: {
            "rate_limit": 100,        # 100 requests/minute
            "min_order_size": 0.0001, # 0.0001 BTC minimum
            "fee_pct": 0.002,         # 0.2% trading fee
            "slippage_pct": 0.001     # 0.1% slippage
        },
        description="Exchange-specific settings"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    @classmethod
    def from_config_file(cls, config_path: str = "config.json"):
        """Load configuration from JSON file"""
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
            valid_fields = cls.model_fields.keys()
            unknown_keys = set(config_data.keys()) - valid_fields
            if unknown_keys:
                print(f"Warning: Unknown config keys ignored: {', '.join(sorted(unknown_keys))}")
            return cls(**config_data)
        except FileNotFoundError:
            return cls()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
