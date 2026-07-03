# Indodax Autonomous Trading Bot

[![Tests](https://img.shields.io/badge/tests-92%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

Autonomous trading bot for the [Indodax](https://indodax.com) cryptocurrency exchange (IDR pairs) with multi-indicator signal generation, adaptive weight adjustment, market manipulation detection, and comprehensive risk management.

## Features

- **3-Phase Trading Cycle** — exit check → risk guard → entry scan
- **Multi-Indicator Signals** — RSI, MACD, Bollinger Bands, EMA crossover, volume spike, ADX, Stochastic
- **Adaptive Engine** — Regime detection (choppy/ranging/trending/strong_trend) with dynamic weight adjustment
- **Phantom Detection** — Wash trade, pump & dump, doji manipulation, spread anomaly, consecutive candle patterns
- **Risk Management** — Daily loss limit, max drawdown, loss streak protection, Half-Kelly position sizing, cooldown
- **Exit Manager** — Stop loss, take profit, trailing stop, breakeven, time stop
- **Sentiment Analysis** — Fear & Greed Index integration
- **Backtest, Paper, Live Modes** — Validate before deploying real funds
- **Encrypted Secrets** — AES-256 Fernet encryption for API keys

## Architecture

```
indodax-trading-bot/
├── main.py                  # Entry point — Exchange, Indicators, Bot classes + CLI
├── config/
│   ├── settings.py          # Pydantic Settings — all config defaults
│   └── secrets.py           # SecretManager — Fernet encrypt/decrypt for API keys
├── core/
│   ├── sentiment.py         # Fear & Greed Index fetcher (sync, with cache)
│   ├── phantom_detector.py  # 5 anomaly detection algorithms with penalty scoring
│   ├── adaptive_engine.py   # ADX-based regime detection + weight tuning
│   ├── risk_manager.py      # 7 risk guards + Half-Kelly position sizing
│   ├── exit_manager.py      # SL/TP/trailing/breakeven/time exit conditions
│   └── logger.py            # Structured logging with banner + summary
├── storage/
│   └── database.py          # SQLite TradeStore — trades, rolling metrics, candle cache
├── tests/                   # 92 test cases across all components
├── utils/
│   └── encrypt_keys.py      # CLI utility to encrypt API keys
├── .env.example             # Required environment variables template
├── config.json              # Trading parameters (pairs, thresholds, weights)
└── Dockerfile               # Containerized deployment
```

### 3-Phase Trading Cycle

```
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: EXIT CHECK                                        │
│  For each pair → check all open trades for exit conditions  │
│  (SL hit? TP hit? Trailing triggered? Breakeven? Time stop?)│
├─────────────────────────────────────────────────────────────┤
│  PHASE 2: RISK GUARD                                        │
│  Daily loss OK? Drawdown OK? Positions count OK?            │
│  Balance OK? Cooldown elapsed? Loss streak OK?              │
├─────────────────────────────────────────────────────────────┤
│  PHASE 3: ENTRY SCAN                                        │
│  For each pair → fetch candles → indicators → phantom scan  │
│  → regime detection → composite signal → position sizing    │
│  → place order                                              │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- [TA-Lib system library](https://github.com/ta-lib/ta-lib) (`apt install libta-lib-dev` on Debian/Kali)

### Setup

```bash
git clone https://github.com/Zrio88/indodax-trading-bot.git
cd indodax-trading-bot

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your Indodax API credentials
```

### API Key Encryption (Optional)

```bash
python utils/encrypt_keys.py
# Follow prompts to encrypt your API keys
```

### Configure

Edit `config.json` to set your trading pairs, risk parameters, signal weights, and phantom detection thresholds.

### Run

```bash
# Backtest (historical data)
python main.py backtest --pairs BTC_IDR --timeframe 1h --start 2024-01-01 --end 2024-12-31

# Paper trading (simulation)
python main.py paper --pairs BTC_IDR,ETH_IDR --timeframe 1h

# Live trading (real money)
python main.py live --pairs BTC_IDR --timeframe 1h
```

## Configuration

### config.json

| Section | Key | Default | Description |
|---------|-----|---------|-------------|
| Trading | `pairs` | `["BTC_IDR"]` | Trading pairs to monitor |
| Trading | `timeframe` | `"1h"` | Candle timeframe (1m/5m/15m/1h/4h/1d) |
| Trading | `initial_balance` | `10_000_000` | Starting balance in IDR |
| Risk | `stop_loss_pct` | `0.05` | Stop loss (5%) |
| Risk | `take_profit_r` | `2.0` | Take profit (2× risk) |
| Weights | `signal_weights` | See below | Signal component weights (must sum to 1.0) |
| Phantom | `phantom_thresholds` | See below | Anomaly detection thresholds |
| Adaptive | `adaptive_settings` | See below | Regime detection and adaptation params |
| Exchange | `exchange` | See below | Rate limit, fees, slippage, min order |

#### Signal Weights

| Signal | Default Weight | Description |
|--------|---------------|-------------|
| `rsi` | 0.15 | RSI oversold/overbought |
| `macd` | 0.20 | MACD crossover |
| `bollinger` | 0.15 | Bollinger Band position |
| `ema_crossover` | 0.20 | EMA crossover signals |
| `volume_spike` | 0.10 | Volume anomaly |
| `adx` | 0.10 | Trend strength |
| `stochastic` | 0.10 | Stochastic oscillator |

#### Risk Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `daily_loss_limit_pct` | 0.02 | 2% daily max loss |
| `max_drawdown_pct` | 0.05 | 5% max drawdown |
| `max_loss_streak` | 3 | Stop after 3 consecutive losses |
| `max_positions` | 3 | Maximum 3 open positions |
| `cooldown_minutes` | 30 | Cooldown between trades |
| `kelly_fraction` | 0.5 | Half-Kelly sizing |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `INDODAX_API_KEY` | For live | Indodax API key |
| `INDODAX_SECRET_KEY` | For live | Indodax secret key |
| `INDODAX_API_KEY_ENC` | Alternative | Encrypted API key |
| `INDODAX_SECRET_KEY_ENC` | Alternative | Encrypted secret key |
| `SECRET_KEY` | For encryption | Fernet key for decrypting API keys |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=term-missing

# Run specific component
pytest tests/test_risk_manager.py -v
pytest tests/test_exit_manager.py -v
```

92 test cases covering all components.

## Component Details

### Exchange (`main.py:Exchange`)
- CCXT wrapper for Indodax with automatic symbol format conversion (`BTC_IDR` ↔ `BTC/IDR`)
- Rate-limited requests, precision-adjusted order placement
- Graceful error handling with descriptive messages

### Settings (`config/settings.py`)
- Pydantic Settings v2 with `SettingsConfigDict`
- All parameters have sensible defaults
- Loads from `config.json` or environment variables
- Validates types at load time

### RiskManager (`core/risk_manager.py`)
7 risk guards evaluated before every trade:
1. **Daily Loss** — stops trading after daily loss exceeds limit
2. **Max Drawdown** — stops if peak-to-current drawdown exceeds threshold
3. **Max Positions** — limits concurrent open positions
4. **Min Balance** — prevents trading below a minimum balance
5. **Allowed Pairs** — restricts trading to configured pairs
6. **Loss Streak** — stops after N consecutive losses
7. **Cooldown** — enforces minimum time between trades

Position sizing uses Half-Kelly criterion with optional phantom penalty multiplier.

### PhantomDetector (`core/phantom_detector.py`)
5 detection algorithms:
- **Wash Trade** — volume spike without price movement
- **Pump & Dump** — rapid rise followed by crash
- **Doji Manipulation** — tiny body with high volume
- **Consecutive Candles** — unnatural sequences (8+ bullish/bearish)
- **Spread Anomaly** — abnormal bid-ask spread

Returns a composite penalty score (0-100) used to reduce position size.

### AdaptiveEngine (`core/adaptive_engine.py`)
- **Regime Detection** — ADX-based: choppy (<20), ranging (20-25), trending (25-50), strong_trend (>50)
- **Dynamic Weights** — trend-following indicators weighted up in trending regimes, mean-reversion in ranging
- **Trade Feedback** — wins/losses feed back into weight adjustment
- **Regime Multipliers** — position size scaled per regime (trending=1.25×, choppy=0.5×)

### ExitManager (`core/exit_manager.py`)
5 exit conditions checked every cycle:
1. **Stop Loss** — fixed percentage below/above entry
2. **Take Profit** — risk-reward ratio target
3. **Trailing Stop** — 2× ATR trailing, only moves up for BUY or down for SELL
4. **Breakeven** — moves SL to breakeven when price reaches 1R
5. **Time Stop** — forces exit after 72 hours

### TradeStore (`storage/database.py`)
- SQLite database via raw sqlite3 (no ORM)
- Tables: `trades`, `candle_cache`, `rolling_metrics`
- Tracks individual trades with entry/exit prices, fees, PnL
- Rolling metrics: win rate, total PnL, loss streak (Python-loop calculation)
- Candle cache for offline analysis

### Sentiment (`core/sentiment.py`)
- Fetches Fear & Greed Index from alternative.me API
- Synchronous via urllib (no aiohttp dependency)
- 5-minute cache to avoid redundant fetches
- Classifies: extreme_fear (<25), fear (25-45), neutral (45-55), greed (55-75), extreme_greed (>75)
- Validates responses: refuses stale data (>30 min) and value range (0-100)

## Docker

```bash
docker compose build
docker compose up -d
# View logs
docker compose logs -f
```

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| `TA-Lib not found` | System lib not installed | `apt install libta-lib-dev` |
| `indodax does not have market symbol` | Symbol format wrong | Use `BTC/IDR` or the bot converts `BTC_IDR` automatically |
| `from is less than 2000-01-01` | Exchange API rate limit | Wait and retry |
| No data in backtest | `storage/trades.db` missing | Run `main.py paper` once to create it |
| API key errors | Key not set or encrypted | Check `.env` or run `utils/encrypt_keys.py` |

## License

MIT License — see [LICENSE](LICENSE) file.
