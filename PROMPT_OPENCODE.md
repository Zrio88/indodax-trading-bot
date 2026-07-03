# PROMPT OPENCODE - INDODAX AUTONOMOUS TRADING BOT
## Expert-Level Execution Prompt (Zero Error Tolerance)

---

## 🎯 MISSION STATEMENT

> **KAMU ADALAH ARSITEK & ENGINEER TRADING BOT LEVEL EXPERT**
> 
> Buat **SISTEM TRADING AUTONOMOUS COMPREHENSIVE** untuk **Indodax Market** dengan **Zero Error Tolerance**. Setiap komponen harus **production-ready**, **well-tested**, **optimized**, dan **self-healing**.

---

## 📋 REQUIREMENTS MATRIX

### ✅ **CORE ARCHITECTURE (MANDATORY)**

| Component | Class | Methods | Responsibilities |
|-----------|-------|---------|------------------|
| **CONFIG** | `ConfigManager` | `load()`, `validate()`, `get()` | Centralized configuration (pairs, timeframes, weights, thresholds) |
| **TradeStore** | `SQLiteTradeStore` | `add_trade()`, `close_trade()`, `open_trades()`, `rolling_metrics()`, `loss_streak()`, `total_pnl()` | SQLite database for trades, PnL, candles |
| **Exchange** | `IndodaxExchange` | `fetch_ohlcv()`, `fetch_balance()`, `idr_balance()`, `limit_buy()`, `limit_sell()`, `_adjust_precision()` | CCXT wrapper for Indodax API |
| **Sentiment** | `SentimentAnalyzer` | `score()`, `_fetch_fear_greed()` | Fear & Greed Index (0.0-1.0 scale, 1hr cache) |

### ✅ **TECHNICAL INDICATORS (MANDATORY)**

| Indicator | Parameters | Output | Weight |
|-----------|------------|--------|--------|
| EMA | 9, 20, 50 periods | Trend direction | Dynamic |
| SMA | 20, 50 periods | Trend confirmation | Dynamic |
| RSI | 14 periods | Overbought/Oversold | Dynamic |
| Bollinger Bands | 20 periods, 2 std | Volatility & reversal | Dynamic |
| MACD | 12, 26, 9 | Momentum | Dynamic |
| ATR | 14 periods | Volatility | Dynamic |
| ADX + DMP/DMN | 14 periods | Trend strength | Dynamic |
| Stochastic | 14, 3, 3 | Momentum reversal | Dynamic |
| Volume SMA | 20 periods | Volume trend | Dynamic |
| Volume Ratio | Current vs SMA | Volume spike | Dynamic |
| OBV | - | Volume accumulation | Dynamic |

**Method:** `Indicators.signal_score()` → 6 components + phantom penalty

### ✅ **PHANTOM DETECTION SYSTEM (MANDATORY)**

| Anomaly Type | Detection Logic | Impact |
|--------------|------------------|--------|
| `wash_trade` | Volume spike 6× without price movement | +Penalty score |
| `pump_dump` | Rapid price movement + volume spike | +Penalty score |
| `doji_manipulation` | Doji pattern with abnormal volume | +Penalty score |
| `consecutive_bullish` | N consecutive green candles | +Penalty score |
| `spread_anomaly` | Abnormal bid-ask spread | +Penalty score |

**Method:** `PhantomDetector.detect(candles)` → List of anomalies

### ✅ **ADAPTIVE ENGINE (MANDATORY)**

```python
# Regime Detection (ADX-based)
regimes = {
    'choppy': ADX < 20,
    'ranging': 20 <= ADX < 25,
    'trending': 25 <= ADX < 40,
    'strong_trend': 40 <= ADX < 60,
    'volatile': ADX >= 60
}

# Weight Adjustment
- Track win rate per signal
- Increase weights for winning signals
- Decrease weights for losing signals
- Multipliers based on regime

# Methods:
- detect_regime(candles) → regime_type
- feed_trade(trade_result) → update weights
- update_weights() → adjust signal weights
- get_multipliers(regime) → sizing/threshold multipliers
```

### ✅ **RISK MANAGEMENT SYSTEM (MANDATORY)**

#### **7 Guard Rails (`can_trade()`)**

1. **Daily Loss Limit** → Stop if daily loss > X% of capital
2. **Drawdown Circuit** → Stop if drawdown > Y% from peak
3. **Loss Streak Pause** → Pause if N consecutive losses
4. **Max Positions** → Limit open positions (default: 3)
5. **Cooldown Period** → Wait Z minutes after loss
6. **Balance Check** → Minimum IDR balance required
7. **Market Hours** → Only trade during active hours

#### **Position Sizing (`position_size()`)**

```python
position_size = (
    (account_balance * risk_per_trade) / stop_loss_distance
) * half_kelly_multiplier
  * drawdown_multiplier
  * regime_multiplier
```

- **Half-Kelly**: 0.5 × (win_rate - loss_rate)
- **Drawdown Multiplier**: 1.0 - (current_drawdown / max_drawdown)
- **Regime Multiplier**: Based on market regime

**Default Values:**
- `risk_per_trade`: 1-2% of capital
- `stop_loss_pct`: 5%
- `max_drawdown`: 20%
- `max_daily_loss`: 10%
- `max_loss_streak`: 5
- `cooldown_minutes`: 30

### ✅ **EXIT MANAGEMENT (MANDATORY)**

| Exit Type | Condition | Priority |
|-----------|-----------|----------|
| **Take Profit (TP)** | Price reaches 2R (2× risk) | High |
| **Stop Loss (SL)** | Price drops 5% from entry | Critical |
| **Trailing Stop** | 2× ATR from highest price | Medium |
| **Breakeven** | Move SL to entry +1.5% after 1R | Medium |
| **Time Stop** | Auto-exit after 24 hours | Low |

**Method:** `ExitManager.check(trade, current_price)` → exit_signal

### ✅ **LOGGING SYSTEM (MANDATORY)**

```python
# Log Levels
- INFO: Pair status, market updates
- SUCCESS: Entry/exit execution
- WARNING: Risk guards triggered
- ERROR: API failures, critical errors
- DEBUG: Indicator values, calculations

# Methods:
- print_banner() → ASCII art header
- print_header() → Timestamp + market info
- print_pair_status() → Current state of each pair
- print_entry() → Trade entry confirmation
- print_exit() → Trade exit confirmation
- print_summary() → Daily PnL + win rate + regime
```

### ✅ **MAIN BOT ENGINE (MANDATORY)**

```python
class Bot:
    def __init__(self, config: ConfigManager):
        self.config = config
        self.exchange = IndodaxExchange(config)
        self.store = SQLiteTradeStore(config)
        self.indicators = Indicators(config)
        self.phantom = PhantomDetector(config)
        self.adaptive = AdaptiveEngine(config)
        self.risk = RiskManager(config)
        self.exit = ExitManager(config)
        self.sentiment = SentimentAnalyzer(config)
        self.logger = Logger(config)
    
    def cycle(self):
        # Phase 1: Exit Check
        for pair in self.config.pairs:
            open_trades = self.store.open_trades(pair)
            for trade in open_trades:
                exit_signal = self.exit.check(trade)
                if exit_signal:
                    self._execute_exit(trade, exit_signal)
        
        # Phase 2: Risk Guard
        if not self.risk.can_trade():
            return
        
        # Phase 3: Entry Scan
        for pair in self.config.pairs:
            if self._should_enter(pair):
                self._execute_entry(pair)
    
    def run(self):
        while True:
            try:
                self.cycle()
                time.sleep(self.config.interval * 60)
            except Exception as e:
                self.logger.error(f"Cycle error: {e}")
                time.sleep(60)
```

---

## 📁 PROJECT STRUCTURE (MANDATORY)

```
indodax-trading-bot/
├── config/
│   ├── __init__.py
│   ├── config.py          # ConfigManager
│   └── constants.py       # All constants
├── core/
│   ├── __init__.py
│   ├── bot.py             # Main Bot class
│   ├── engine.py          # AdaptiveEngine
│   └── cycle.py           # Trading cycle logic
├── storage/
│   ├── __init__.py
│   ├── trades.py          # SQLiteTradeStore
│   └── database.py        # DB setup & migrations
├── services/
│   ├── __init__.py
│   ├── exchange.py        # IndodaxExchange
│   ├── sentiment.py       # SentimentAnalyzer
│   ├── indicators.py      # All technical indicators
│   ├── phantom.py         # PhantomDetector
│   ├── risk.py            # RiskManager
│   └── exit.py            # ExitManager
├── utils/
│   ├── __init__.py
│   ├── logger.py          # Logger
│   ├── helpers.py         # Utility functions
│   └── precision.py       # Price/volume precision
├── tests/
│   ├── __init__.py
│   ├── test_indicators.py
│   ├── test_phantom.py
│   ├── test_risk.py
│   └── test_strategy.py
├── data/
│   └── trades.db          # SQLite database
├── .env.example
├── .env
├── requirements.txt
├── main.py               # Entry point
└── README.md
```

---

## 🔧 CONFIGURATION SPECIFICATION

### **config.py**

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

@dataclass
class Config:
    # API Keys
    indodax_api_key: str
    indodax_secret_key: str
    
    # Trading Parameters
    pairs: List[str] = field(default_factory=lambda: [
        "BTCIDR", "ETHIDR", "SOLIDR", "BNBIDR", "XRPIDR"
    ])
    timeframes: List[str] = field(default_factory=lambda: ["1h", "4h", "1d"])
    
    # Risk Parameters
    risk_per_trade: float = 0.01  # 1%
    max_positions: int = 3
    max_daily_loss_pct: float = 0.10  # 10%
    max_drawdown_pct: float = 0.20  # 20%
    stop_loss_pct: float = 0.05  # 5%
    take_profit_r: float = 2.0  # 2R
    
    # Adaptive Parameters
    initial_weights: Dict[str, float] = field(default_factory=lambda: {
        "ema": 0.15, "sma": 0.10, "rsi": 0.15, 
        "bb": 0.10, "macd": 0.15, "atr": 0.05,
        "adx": 0.10, "stochastic": 0.10, "volume": 0.10
    })
    
    # Phantom Detection
    volume_spike_threshold: float = 6.0
    adx_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "choppy": 20, "ranging": 25, "trending": 40, 
        "strong_trend": 60, "volatile": 80
    })
    
    # Timing
    interval_minutes: int = 5
    lookback_candles: int = 100
    
    # Database
    db_path: str = "data/trades.db"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/bot.log"
    
    # Paper Trading
    paper_trading: bool = True
    initial_balance: float = 10000000  # IDR 10M

class ConfigManager:
    def __init__(self):
        load_dotenv()
        self.config = Config(
            indodax_api_key=os.getenv("INDODAX_API_KEY", ""),
            indodax_secret_key=os.getenv("INDODAX_SECRET_KEY", "")
        )
    
    def load(self) -> Config:
        return self.config
    
    def validate(self) -> bool:
        required = [
            self.config.indodax_api_key,
            self.config.indodax_secret_key
        ]
        return all(required)
    
    def get(self, key: str):
        return getattr(self.config, key)
```

### **requirements.txt**

```
ccxt>=4.0.0
pandas>=2.0.0
numpy>=1.24.0
sqlite3>=3.0.0
python-dotenv>=1.0.0
aiohttp>=3.8.0
requests>=2.31.0
cachetools>=5.3.0
rich>=13.0.0
```

---

## 💡 EXECUTION INSTRUCTIONS FOR OPENCODE

### **PROMPT FORMAT FOR OPENCODE:**

```
YOU ARE AN EXPERT PYTHON DEVELOPER AND QUANTITATIVE TRADER.

CREATE A COMPLETE, PRODUCTION-READY AUTONOMOUS TRADING BOT FOR INDODAX MARKET.

REQUIREMENTS:
1. Use the architecture and specifications defined in this file
2. Zero error tolerance - all code must be syntactically correct and well-tested
3. Use type hints (Python 3.11+)
4. Use async/await for API calls where appropriate
5. Implement comprehensive error handling
6. Include unit tests for all components
7. Use SQLAlchemy or raw SQLite for database operations
8. Optimize for low latency and high reliability
9. Include proper logging throughout
10. Support both paper trading and live trading

IMPLEMENTATION ORDER:
1. config/ - Configuration management
2. storage/ - Database layer
3. services/ - Exchange, Indicators, Phantom, Sentiment
4. utils/ - Logger, helpers
5. core/ - AdaptiveEngine, RiskManager, ExitManager, Bot
6. tests/ - Comprehensive test suite
7. main.py - Entry point

START WITH THE FIRST COMPONENT AND WAIT FOR FEEDBACK BEFORE PROCEEDING TO THE NEXT.

FIRST TASK: Create config/config.py with Config dataclass and ConfigManager as specified above.
```

---

## 🎯 SIGNAL SCORING ALGORITHM

```python
class Indicators:
    def signal_score(self, candles: DataFrame) -> float:
        """
        Calculate weighted signal score from all indicators
        Returns: float between -1.0 (strong sell) and +1.0 (strong buy)
        """
        scores = {}
        
        # 1. EMA Score (Trend)
        ema_9 = self.ema(candles['close'], 9)
        ema_20 = self.ema(candles['close'], 20)
        ema_50 = self.ema(candles['close'], 50)
        ema_score = self._calculate_ema_score(ema_9, ema_20, ema_50)
        scores['ema'] = ema_score
        
        # 2. RSI Score (Momentum)
        rsi = self.rsi(candles['close'], 14)
        rsi_score = self._normalized_score(rsi, 30, 70)  # -1 to +1
        scores['rsi'] = rsi_score
        
        # 3. MACD Score
        macd, signal, histogram = self.macd(candles['close'])
        macd_score = self._normalized_score(histogram.iloc[-1], -0.1, 0.1)
        scores['macd'] = macd_score
        
        # 4. Bollinger Bands Score
        bb_upper, bb_middle, bb_lower = self.bollinger_bands(candles['close'])
        bb_position = (candles['close'].iloc[-1] - bb_lower) / (bb_upper - bb_lower)
        bb_score = bb_position * 2 - 1  # 0-1 -> -1 to +1
        scores['bb'] = bb_score
        
        # 5. ADX + DMP/DMN Score
        adx, plus_dm, minus_dm = self.adx(candles)
        dmp_score = plus_dm.iloc[-1] - minus_dm.iloc[-1]
        dmp_score = self._normalized_score(dmp_score, -50, 50)
        adx_weight = min(adx.iloc[-1] / 50, 1.0)  # Stronger trend = more weight
        scores['adx'] = dmp_score * adx_weight
        
        # 6. Stochastic Score
        k, d = self.stochastic(candles)
        stoch_score = self._normalized_score(k.iloc[-1], 20, 80)
        scores['stochastic'] = stoch_score
        
        # 7. Volume Score
        volume_sma = self.sma(candles['volume'], 20)
        volume_ratio = candles['volume'].iloc[-1] / volume_sma.iloc[-1]
        volume_score = min(volume_ratio / 5, 1.0)  # Cap at 5x
        scores['volume'] = volume_score if candles['close'].iloc[-1] > candles['close'].iloc[-2] else -volume_score
        
        # Apply weights
        weighted_sum = 0
        total_weight = 0
        for indicator, score in scores.items():
            weight = self.config.get(f"initial_weights.{indicator}")
            weighted_sum += score * weight
            total_weight += weight
        
        composite_score = weighted_sum / total_weight
        
        # Apply phantom penalty
        anomalies = self.phantom.detect(candles)
        phantom_penalty = len(anomalies) * 0.1  # -0.1 per anomaly
        
        final_score = composite_score - phantom_penalty
        
        # Apply regime multiplier
        regime = self.adaptive.detect_regime(candles)
        regime_multiplier = self.adaptive.get_multipliers(regime)
        final_score *= regime_multiplier['signal']
        
        return max(-1.0, min(1.0, final_score))
```

---

## 🛡️ ERROR HANDLING & VALIDATION

### **Mandatory Validations:**

```python
# Exchange Validation
- API key presence
- API connectivity
- Rate limit handling (max 1200 requests/minute for Indodax)
- Precision adjustment for each pair

# Data Validation
- OHLCV data completeness
- Candle count minimum (config.lookback_candles)
- Price > 0
- Volume >= 0

# Trade Validation
- Position size > 0
- Price within bid-ask spread
- Balance sufficient
- Not exceeding max positions

# Risk Validation
- Drawdown calculation accuracy
- Daily PnL tracking
- Loss streak counting
```

---

## 🚀 DEPLOYMENT CHECKLIST

### **Before Production:**

- [ ] All unit tests pass (pytest tests/ -v)
- [ ] Paper trading shows consistent results
- [ ] Backtest on historical data (minimum 3 months)
- [ ] Stress test with concurrent operations
- [ ] Database integrity verified
- [ ] Logging captures all critical events
- [ ] Error recovery tested
- [ ] API rate limits respected
- [ ] Memory usage stable (no leaks)
- [ ] CPU usage within acceptable range

### **Production Monitoring:**

```python
# Health Metrics to Track:
- Win rate (%) per day/week/month
- Profit factor (gross_profit / gross_loss)
- Max drawdown (%) from peak
- Sharpe ratio
- Sortino ratio
- Average win/loss ratio
- Number of trades per day
- Execution latency (ms)
- API error rate (%)
- Database query time (ms)
```

---

## 📊 BACKTESTING SPECIFICATION

```python
class Backtester:
    def __init__(self, config: Config, start_date: str, end_date: str):
        self.config = config
        self.start = pd.to_datetime(start_date)
        self.end = pd.to_datetime(end_date)
        self.results = []
    
    def run(self) -> Dict:
        for pair in self.config.pairs:
            candles = self.exchange.fetch_ohlcv(
                pair, 
                self.config.timeframes[0],
                self.start, 
                self.end
            )
            
            for i in range(self.config.lookback_candles, len(candles)):
                current_candles = candles.iloc[i-self.config.lookback_candles:i]
                
                # Check if should enter
                if self._should_enter(pair, current_candles):
                    entry_price = candles['close'].iloc[i]
                    trade = Trade(
                        pair=pair,
                        entry_price=entry_price,
                        entry_time=candles['timestamp'].iloc[i],
                        direction='buy',
                        size=self.risk.position_size(pair, entry_price)
                    )
                    
                    # Simulate exit
                    for j in range(i+1, min(i+24*24, len(candles))):  # Max 24h
                        exit_price = candles['close'].iloc[j]
                        exit_signal = self.exit.check(trade, exit_price)
                        
                        if exit_signal:
                            pnl = self._calculate_pnl(trade, exit_price)
                            trade.close(exit_price, j, pnl, exit_signal)
                            self.results.append(trade)
                            break
        
        return self._calculate_metrics()
    
    def _calculate_metrics(self) -> Dict:
        if not self.results:
            return {}
        
        wins = [t for t in self.results if t.pnl > 0]
        losses = [t for t in self.results if t.pnl < 0]
        
        return {
            'total_trades': len(self.results),
            'win_rate': len(wins) / len(self.results),
            'profit_factor': sum(t.pnl for t in wins) / abs(sum(t.pnl for t in losses)),
            'avg_win': sum(t.pnl for t in wins) / len(wins) if wins else 0,
            'avg_loss': sum(t.pnl for t in losses) / len(losses) if losses else 0,
            'win_loss_ratio': (sum(t.pnl for t in wins) / len(wins)) / (abs(sum(t.pnl for t in losses)) / len(losses)) if losses else float('inf'),
            'total_pnl': sum(t.pnl for t in self.results),
            'max_drawdown': self._calculate_max_drawdown(),
            'sharpe_ratio': self._calculate_sharpe_ratio(),
            'sortino_ratio': self._calculate_sortino_ratio()
        }
```

---

## 🔐 SECURITY CONSIDERATIONS

```python
# API Key Security
- Never log API keys
- Use environment variables (not hardcoded)
- Encrypt sensitive data at rest
- Implement rate limiting on our side
- Use HTTPS for all API calls

# Database Security
- SQLite file permissions (600)
- Regular backups
- Integrity checks
- No SQL injection vulnerabilities

# Trading Security
- Validate all order parameters
- Prevent duplicate orders
- Handle API timeouts gracefully
- Verify order execution before updating state
- Implement circuit breakers
```

---

## 📝 IMPLEMENTATION NOTES

### **Performance Optimizations:**

1. **Caching:**
   - Cache OHLCV data (5 minute TTL)
   - Cache Fear & Greed Index (1 hour TTL)
   - Cache indicator calculations per timeframe

2. **Parallel Processing:**
   - Use asyncio for concurrent pair processing
   - Process different timeframes in parallel
   - Batch API requests where possible

3. **Memory Management:**
   - Limit candle history in memory
   - Use generators for large datasets
   - Clean up old trades periodically

### **Error Recovery:**

```python
class Exchange:
    async def _retry_api_call(self, func, *args, max_retries=3, **kwargs):
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except (ccxt.NetworkError, ccxt.ExchangeError) as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = (attempt + 1) * 5  # Exponential backoff
                self.logger.warning(f"API call failed, retry {attempt + 1}/{max_retries} in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
        
    async def fetch_ohlcv(self, pair, timeframe, limit=100):
        return await self._retry_api_call(
            self.exchange.fetch_ohlcv,
            pair, timeframe, limit=limit
        )
```

---

## 🎓 BEST PRACTICES

### **Code Quality:**
- Type hints for all functions and variables
- Comprehensive docstrings
- Follow PEP 8 style guide
- Use dataclasses for data structures
- Immutable configuration where possible
- Dependency injection pattern

### **Testing:**
- Unit tests for each component
- Integration tests for component interactions
- End-to-end tests for trading cycle
- Mock external dependencies (CCXT, APIs)
- Test edge cases and error conditions

### **Monitoring:**
- Real-time dashboards
- Alerting for critical errors
- Performance metrics collection
- Trade history visualization
- Risk metrics tracking

---

## 🚨 CRITICAL WARNINGS

1. **NEVER** trade with real money without extensive paper trading first
2. **NEVER** run without proper risk management
3. **NEVER** ignore circuit breakers
4. **NEVER** hardcode API keys
5. **ALWAYS** validate all inputs
6. **ALWAYS** handle exceptions gracefully
7. **ALWAYS** log critical actions
8. **ALWAYS** test with small amounts first

---

## ✅ ACCEPTANCE CRITERIA

- [ ] All components implemented as specified
- [ ] Zero syntax errors
- [ ] Zero runtime errors in normal operation
- [ ] All unit tests pass
- [ ] Paper trading works without errors
- [ ] Backtesting produces reasonable results
- [ ] Logging captures all important events
- [ ] Risk management prevents catastrophic losses
- [ ] Phantom detection identifies market manipulation
- [ ] Adaptive engine improves over time
- [ ] Exit management closes trades appropriately
- [ ] Configuration is flexible and validated

---

## 📞 SUPPORT & MAINTENANCE

### **Troubleshooting Guide:**

| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| API Connection Error | Network issue or invalid keys | Check internet, verify API keys |
| Rate Limit Exceeded | Too many API calls | Implement rate limiting, increase interval |
| Database Locked | Concurrent access | Use WAL mode, implement queue |
| Invalid Precision | Order rejected | Use `_adjust_precision()` method |
| Insufficient Balance | Not enough IDR | Reduce position size, add funds |
| No Trades Executed | Market conditions or config | Adjust weights, check signals |

### **Performance Tuning:**

```python
# Adjust these parameters based on backtest results:
config = {
    'risk_per_trade': 0.01,      # Start conservative
    'max_positions': 3,           # Don't overload
    'lookback_candles': 100,     # Balance accuracy vs performance
    'interval_minutes': 5,       # Adjust based on strategy
    'volume_spike_threshold': 6.0,  # Tune for Indodax market
    'adx_thresholds': {
        'choppy': 20,
        'ranging': 25,
        'trending': 40
    }
}
```

---

## 🏁 FINAL NOTES

> **INI ADALAH PROMPT KOMPREHENSIF UNTUK OPENCODE**
> 
> Prompt ini dirancang untuk menghasilkan **TRADING BOT AUTONOMOUS SUPER** untuk **Indodax Market** dengan **Zero Error Tolerance**. Setiap detail telah diperhitungkan, setiap komponen terdefinisi dengan jelas, dan setiap skenario diantisipasi.
> 
> **EKSEKUSI DENGAN HATI-HATI. KESELAMATAN DANA ANDA ADALAH TANGGUNG JAWAB ANDA.**

---

**File Location:** `/home/get/Desktop/indodax-trading-bot/PROMPT_OPENCODE.md`
**Created:** 2026-07-02
**Version:** 1.0.0
**Author:** Mistral Vibe (Expert Level)
