#!/usr/bin/env python3
"""
Indodax Autonomous Trading Bot - Main Entry Point

Usage:
    python main.py backtest --pairs BTC_IDR --timeframe 1h --start 2023-01-01 --end 2023-12-31
    python main.py paper --pairs BTC_IDR,ETH_IDR --timeframe 1h
    python main.py live --pairs BTC_IDR --timeframe 1h

Components:
    - TradeStore: SQLite database for trades
    - Exchange: CCXT Indodax wrapper
    - Sentiment: Fear & Greed Index
    - Indicators: Technical Analysis
    - PhantomDetector: Market manipulation detection
    - AdaptiveEngine: Dynamic weight adjustment
    - RiskManager: Position sizing & risk guards
    - ExitManager: TP/SL/Trailing/Breakeven logic
    - Logger: Structured logging
    - Bot: Main trading engine (3-phase cycle)
"""

import argparse
import sys
import os
import json
import time
import signal
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import configuration
from config.settings import Settings
from config.secrets import SecretManager

# Import storage
from storage.database import TradeStore, TradeRecord

# Import core components
from core.sentiment import Sentiment
from core.phantom_detector import PhantomDetector, PhantomFlags
from core.adaptive_engine import AdaptiveEngine
from core.risk_manager import RiskManager, RiskCheckResult, PositionSizeResult
from core.exit_manager import ExitManager, ExitSignal
from core.logger import Logger

# Import models
from dataclasses import dataclass


@dataclass
class IndicatorValues:
    """Data class for indicator values"""
    # Moving Averages
    ema_9: float = 0.0
    ema_20: float = 0.0
    ema_50: float = 0.0
    sma_20: float = 0.0
    sma_50: float = 0.0
    
    # Momentum
    rsi_14: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_hist: float = 0.0
    stochastic_k: float = 0.0
    stochastic_d: float = 0.0
    
    # Volatility
    atr_14: float = 0.0
    bollinger_upper: float = 0.0
    bollinger_middle: float = 0.0
    bollinger_lower: float = 0.0
    
    # Trend Strength
    adx: float = 0.0
    dmp_plus: float = 0.0
    dmp_minus: float = 0.0
    
    # Volume
    volume_sma: float = 0.0
    volume_ratio: float = 0.0
    obv: float = 0.0
    
    # Trend Conditions
    price_above_ema20: bool = False
    price_above_ema50: bool = False
    ema9_above_ema20: bool = False
    ema20_above_ema50: bool = False


class Indicators:
    """Technical Analysis Indicators Calculator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.signal_weights = config["signal_weights"]
    
    def calculate(self, df) -> Optional[IndicatorValues]:
        """Calculate indicators from DataFrame"""
        if df is None or len(df) < 50:
            return None
        
        try:
            import pandas as pd
            import talib
            import numpy as np
            
            if not isinstance(df, pd.DataFrame):
                df = pd.DataFrame(df)
            
            if 'timestamp' in df.columns:
                df.set_index('timestamp', inplace=True)
            
            closes = df['close'].values
            highs = df['high'].values
            lows = df['low'].values
            opens = df['open'].values
            volumes = df['volume'].values
            
            # Moving Averages
            ema_9 = talib.EMA(closes, timeperiod=9)[-1] if len(closes) >= 9 else 0
            ema_20 = talib.EMA(closes, timeperiod=20)[-1] if len(closes) >= 20 else 0
            ema_50 = talib.EMA(closes, timeperiod=50)[-1] if len(closes) >= 50 else 0
            sma_20 = talib.SMA(closes, timeperiod=20)[-1] if len(closes) >= 20 else 0
            sma_50 = talib.SMA(closes, timeperiod=50)[-1] if len(closes) >= 50 else 0
            
            # Momentum
            rsi_14 = talib.RSI(closes, timeperiod=14)[-1] if len(closes) >= 14 else 50
            macd, macd_signal, macd_hist = talib.MACD(closes, fastperiod=12, slowperiod=26, signalperiod=9)
            macd = macd[-1] if len(macd) > 0 else 0
            macd_signal = macd_signal[-1] if len(macd_signal) > 0 else 0
            macd_hist = macd_hist[-1] if len(macd_hist) > 0 else 0
            
            stochastic = talib.STOCH(highs, lows, closes, fastk_period=14, slowk_period=3, slowd_period=3)
            stochastic_k = stochastic[0][-1] if len(stochastic[0]) > 0 else 50
            stochastic_d = stochastic[1][-1] if len(stochastic[1]) > 0 else 50
            
            # Volatility
            atr_14 = talib.ATR(highs, lows, closes, timeperiod=14)[-1] if len(highs) >= 14 else 0
            bollinger = talib.BBANDS(closes, timeperiod=20, nbdevup=2, nbdevdn=2)
            bollinger_upper = bollinger[0][-1] if len(bollinger[0]) > 0 else 0
            bollinger_middle = bollinger[1][-1] if len(bollinger[1]) > 0 else 0
            bollinger_lower = bollinger[2][-1] if len(bollinger[2]) > 0 else 0
            
            # Trend Strength
            adx = talib.ADX(highs, lows, closes, timeperiod=14)[-1] if len(highs) >= 14 else 0
            dmp_plus = talib.PLUS_DI(highs, lows, closes, timeperiod=14)
            dmp_minus = talib.MINUS_DI(highs, lows, closes, timeperiod=14)
            dmp_plus = dmp_plus[-1] if len(dmp_plus) > 0 else 0
            dmp_minus = dmp_minus[-1] if len(dmp_minus) > 0 else 0
            
            # Volume
            volume_sma = talib.SMA(volumes, timeperiod=20)[-1] if len(volumes) >= 20 else 0
            volume_ratio = volumes[-1] / volume_sma if volume_sma > 0 else 1.0
            obv = talib.OBV(closes, volumes)[-1] if len(closes) > 0 else 0
            
            current_price = closes[-1]
            
            return IndicatorValues(
                ema_9=ema_9, ema_20=ema_20, ema_50=ema_50,
                sma_20=sma_20, sma_50=sma_50,
                rsi_14=rsi_14,
                macd=macd, macd_signal=macd_signal, macd_hist=macd_hist,
                stochastic_k=stochastic_k, stochastic_d=stochastic_d,
                atr_14=atr_14,
                bollinger_upper=bollinger_upper, bollinger_middle=bollinger_middle, bollinger_lower=bollinger_lower,
                adx=adx, dmp_plus=dmp_plus, dmp_minus=dmp_minus,
                volume_sma=volume_sma, volume_ratio=volume_ratio, obv=obv,
                price_above_ema20=current_price > ema_20,
                price_above_ema50=current_price > ema_50,
                ema9_above_ema20=ema_9 > ema_20,
                ema20_above_ema50=ema_20 > ema_50
            )
        except Exception as e:
            print(f"Error calculating indicators: {e}")
            return None
    
    def signal_score(self, indicators: IndicatorValues, sentiment_score: float, regime: str) -> Dict[str, Any]:
        """Calculate composite signal score (0-100)"""
        scores = {}
        
        # RSI Score
        if indicators.rsi_14 < 30:
            scores["rsi"] = 100
        elif indicators.rsi_14 < 70:
            scores["rsi"] = 50
        else:
            scores["rsi"] = 0
        
        # MACD Score
        if indicators.macd > indicators.macd_signal:
            scores["macd"] = 100
        elif indicators.macd < indicators.macd_signal:
            scores["macd"] = 0
        else:
            scores["macd"] = 50
        
        # Bollinger Score
        current_price = indicators.ema_20
        if current_price < indicators.bollinger_lower:
            scores["bollinger"] = 100
        elif current_price > indicators.bollinger_upper:
            scores["bollinger"] = 0
        else:
            scores["bollinger"] = 50
        
        # EMA Crossover
        if indicators.ema9_above_ema20 and indicators.ema20_above_ema50:
            scores["ema_crossover"] = 100
        elif indicators.ema9_above_ema20:
            scores["ema_crossover"] = 75
        elif indicators.ema20_above_ema50:
            scores["ema_crossover"] = 25
        elif not indicators.ema9_above_ema20 and not indicators.ema20_above_ema50:
            scores["ema_crossover"] = 0
        else:
            scores["ema_crossover"] = 50
        
        # Volume Score
        if indicators.volume_ratio > 2.0:
            scores["volume_spike"] = 100
        elif indicators.volume_ratio > 1.0:
            scores["volume_spike"] = 75
        else:
            scores["volume_spike"] = 25
        
        # ADX Score
        if indicators.adx > 25:
            scores["adx"] = 100 if indicators.dmp_plus > indicators.dmp_minus else 0
        else:
            scores["adx"] = 50
        
        # Stochastic Score (oversold = bullish, overbought = bearish)
        if indicators.stochastic_k < 20 and indicators.stochastic_d < 20:
            scores["stochastic"] = 100
        elif indicators.stochastic_k > 80 and indicators.stochastic_d > 80:
            scores["stochastic"] = 0
        else:
            scores["stochastic"] = 50
        
        # Sentiment Score (higher fear = better buying opportunity)
        scores["sentiment"] = (1 - sentiment_score) * 100
        
        # Apply regime-based weight adjustments
        weighted_scores = self._apply_regime_weights(scores, regime)
        
        # Calculate composite score
        total_weight = sum(self.signal_weights.values())
        composite_score = sum(
            weighted_scores.get(k, 0) * self.signal_weights.get(k, 0) 
            for k in self.signal_weights
        ) / total_weight if total_weight > 0 else 0
        
        # Determine signal
        if composite_score >= 80:
            signal = "STRONG_BUY"
        elif composite_score >= 60:
            signal = "BUY"
        elif composite_score >= 40:
            signal = "NEUTRAL"
        elif composite_score >= 20:
            signal = "SELL"
        else:
            signal = "STRONG_SELL"
        
        return {
            "composite_score": composite_score,
            "signal": signal,
            "scores": weighted_scores,
            "weights": self.signal_weights,
            "regime": regime
        }
    
    def _apply_regime_weights(self, scores: Dict[str, float], regime: str) -> Dict[str, float]:
        """Adjust weights based on market regime"""
        weights = self.signal_weights.copy()
        
        # In trending markets, give more weight to trend-following indicators
        if regime in ["trending", "strong_trend"]:
            weights["ema_crossover"] = weights.get("ema_crossover", 0) + 0.10
            weights["adx"] = weights.get("adx", 0) + 0.10
            weights["macd"] = weights.get("macd", 0) + 0.05
            weights["rsi"] = max(0, weights.get("rsi", 0) - 0.05)
            weights["bollinger"] = max(0, weights.get("bollinger", 0) - 0.10)
        
        # In ranging markets, give more weight to mean-reversion indicators
        elif regime in ["ranging", "choppy"]:
            weights["bollinger"] = weights.get("bollinger", 0) + 0.15
            weights["rsi"] = weights.get("rsi", 0) + 0.10
            weights["stochastic"] = weights.get("stochastic", 0) + 0.10
            weights["ema_crossover"] = max(0, weights.get("ema_crossover", 0) - 0.10)
            weights["adx"] = max(0, weights.get("adx", 0) - 0.05)
        
        # Normalize weights to sum to 1
        total = sum(weights.values())
        if total > 0:
            for key in weights:
                weights[key] = weights[key] / total
        
        return scores


class Exchange:
    """CCXT Indodax Exchange Wrapper"""
    
    def __init__(self, api_key: str = None, secret: str = None):
        self.api_key = api_key
        self.secret = secret
        self._init_ccxt()
    
    def _init_ccxt(self):
        """Initialize CCXT Indodax exchange"""
        try:
            import ccxt
            self.exchange = ccxt.indodax({
                'apiKey': self.api_key,
                'secret': self.secret,
                'enableRateLimit': True,
                'rateLimit': 100,
            })
            self.exchange.set_sandbox_mode(False)
        except ImportError:
            raise ImportError("CCXT library not installed. Run: pip install ccxt")
    
    def _to_market_symbol(self, pair: str) -> str:
        """Convert internal pair format (BTC_IDR) to exchange format (BTC/IDR)"""
        return pair.replace("_", "/") if "_" in pair else pair
    
    def fetch_ohlcv(self, pair: str, timeframe: str = "1h", limit: int = 100):
        """Fetch OHLCV data from Indodax"""
        symbol = self._to_market_symbol(pair)
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, None, limit)
            return [{
                "timestamp": datetime.fromtimestamp(c[0] / 1000),
                "open": c[1], "high": c[2], "low": c[3],
                "close": c[4], "volume": c[5]
            } for c in ohlcv]
        except Exception as e:
            print(f"Error fetching OHLCV for {pair}: {e}")
            return []
    
    def fetch_balance(self):
        """Fetch account balance"""
        try:
            balance = self.exchange.fetch_balance()
            return balance["free"]
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return {}
    
    def idr_balance(self):
        """Get IDR balance"""
        balance = self.fetch_balance()
        return balance.get("IDR", 0.0)
    
    def limit_buy(self, pair: str, price: float, amount: float):
        """Place limit buy order"""
        symbol = self._to_market_symbol(pair)
        try:
            # Adjust precision
            market = self.exchange.markets[symbol]
            price_precision = market["precision"]["price"]
            amount_precision = market["precision"]["amount"]
            price = round(price, price_precision)
            amount = round(amount, amount_precision)
            
            order = self.exchange.create_limit_buy_order(symbol, amount, price)
            return {"success": True, "order_id": order["id"]}
        except Exception as e:
            print(f"Error placing buy order: {e}")
            return {"success": False, "error": str(e)}
    
    def limit_sell(self, pair: str, price: float, amount: float):
        """Place limit sell order"""
        symbol = self._to_market_symbol(pair)
        try:
            market = self.exchange.markets[symbol]
            price_precision = market["precision"]["price"]
            amount_precision = market["precision"]["amount"]
            price = round(price, price_precision)
            amount = round(amount, amount_precision)
            
            order = self.exchange.create_limit_sell_order(symbol, amount, price)
            return {"success": True, "order_id": order["id"]}
        except Exception as e:
            print(f"Error placing sell order: {e}")
            return {"success": False, "error": str(e)}
    
    def limit_sell(self, pair: str, price: float, amount: float):
        """Place limit sell order"""
        try:
            market = self.exchange.markets[pair]
            price_precision = market["precision"]["price"]
            amount_precision = market["precision"]["amount"]
            price = round(price, price_precision)
            amount = round(amount, amount_precision)
            
            order = self.exchange.create_limit_sell_order(pair, amount, price)
            return {"success": True, "order_id": order["id"]}
        except Exception as e:
            print(f"Error placing sell order: {e}")
            return {"success": False, "error": str(e)}


class Bot:
    """
    Main trading bot class
    
    Implements 3-phase trading cycle:
    1. EXIT CHECK: Check all pairs for exit conditions (TP/SL/Trailing/Breakeven)
    2. RISK GUARD: Check if trading is allowed (7 guards)
    3. ENTRY SCAN: Scan for entry opportunities with phantom + regime + adaptive weights
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.settings = Settings(**config)
        
        # Initialize components
        self.trade_store = TradeStore()
        self.exchange = Exchange(config.get("INDODAX_API_KEY"), config.get("INDODAX_SECRET_KEY"))
        self.sentiment = Sentiment()
        self.indicators = Indicators(config)
        self.phantom_detector = PhantomDetector(config)
        self.adaptive_engine = AdaptiveEngine(config)
        self.risk_manager = RiskManager(config, self.trade_store)
        self.exit_manager = ExitManager(config, self.trade_store)
        self.logger = Logger(config)
        
        # Update config
        self.config.update({
            "paper_balance": config.get("initial_balance", 10_000_000),
            "mode": config.get("mode", "paper")
        })
        
        # State
        self.cycle_count = 0
        self.running = False
    
    def _candles_to_dataframe(self, candles):
        """Convert candles to pandas DataFrame"""
        if not candles:
            return None
        try:
            import pandas as pd
            df = pd.DataFrame(candles)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                df.sort_index(inplace=True)
            return df
        except:
            return None
    
    def initialize(self):
        """Initialize the bot"""
        self.logger.print_banner()
        print(f"Configuration loaded: {len(self.config.get('pairs', []))} pairs, {self.config.get('timeframe')} timeframe")
        
        # Initialize adaptive engine with current regime
        for pair in self.config.get("pairs", []):
            candles = self.trade_store.get_candles(pair, self.config.get("timeframe", "1h"), limit=50)
            if candles:
                df = self._candles_to_dataframe(candles)
                indicators = self.indicators.calculate(df)
                if indicators:
                    regime = self.adaptive_engine.detect_regime(
                        indicators.adx, indicators.dmp_plus, indicators.dmp_minus
                    )
                    self.adaptive_engine.update_regime(regime)
    
    def cycle(self):
        """
        Main trading cycle with 3 phases:
        1. EXIT CHECK: Check all pairs for exit conditions
        2. RISK GUARD: Check if trading is allowed
        3. ENTRY SCAN: Scan for entry opportunities
        """
        self.cycle_count += 1
        self.logger.print_header(self.cycle_count)
        
        # ===== PHASE 1: EXIT CHECK =====
        print(f"\n🔍 PHASE 1: Checking exits for all pairs...")
        for pair in self.config.get("pairs", []):
            try:
                candles = self.exchange.fetch_ohlcv(
                    pair=pair,
                    timeframe=self.config.get("timeframe", "1h"),
                    limit=1
                )
                if not candles:
                    print(f"  ⚠️  No data for {pair}")
                    continue
                
                current_price = candles[0]["close"]
                exit_signals = self.exit_manager.check(pair, current_price, datetime.utcnow())
                
                for signal in exit_signals:
                    if self.config.get("mode") in ["paper", "live"]:
                        exit_result = self.exit_manager.execute_exit(
                            signal, self.exchange, self.risk_manager
                        )
                        self.logger.print_exit(exit_result)
                        self.logger.log_to_file(
                            f"EXIT: {pair} | {signal.action} | {signal.reason}",
                            level="INFO"
                        )
            except Exception as e:
                print(f"  ❌ Exit check error for {pair}: {e}")
        
        # ===== PHASE 2: RISK GUARD =====
        print(f"\n🛡️  PHASE 2: Checking risk guards...")
        risk_check = self.risk_manager.can_trade()
        if not risk_check.can_trade:
            print(f"  ⚠️  Trading blocked: {risk_check.reason}")
            self.logger.log_to_file(f"Trading blocked: {risk_check.reason}", level="WARNING")
            return
        else:
            print(f"  ✅ All risk guards passed")
        
        # ===== PHASE 3: ENTRY SCAN =====
        print(f"\n🎯 PHASE 3: Scanning for entry opportunities...")
        for pair in self.config.get("pairs", []):
            try:
                # Risk check per pair
                pair_risk = self.risk_manager.can_trade(pair)
                if not pair_risk.can_trade:
                    print(f"  ⚠️  {pair} blocked: {pair_risk.reason}")
                    continue
                
                # Get market data
                candles = self.exchange.fetch_ohlcv(
                    pair=pair,
                    timeframe=self.config.get("timeframe", "1h"),
                    limit=50
                )
                if not candles or len(candles) < 50:
                    print(f"  ⚠️  Insufficient data for {pair} ({len(candles)} candles)")
                    continue
                
                # Update phantom detector
                for candle in candles[-5:]:
                    self.phantom_detector.update(pair, candle)
                
                # Calculate indicators
                df = self._candles_to_dataframe(candles)
                if df is None or len(df) < 50:
                    print(f"  ⚠️  Invalid DataFrame for {pair}")
                    continue
                
                indicators = self.indicators.calculate(df)
                if not indicators:
                    print(f"  ⚠️  Could not calculate indicators for {pair}")
                    continue
                
                # Get sentiment
                sentiment_score = self.sentiment.score()
                
                # Detect regime
                regime = self.adaptive_engine.detect_regime(
                    indicators.adx, indicators.dmp_plus, indicators.dmp_minus
                )
                self.adaptive_engine.update_regime(regime)
                
                # Detect phantom
                phantom_flags = self.phantom_detector.detect(pair)
                phantom_penalty = self.phantom_detector.penalty_factor(phantom_flags)
                
                # Calculate signal
                signal_data = self.indicators.signal_score(
                    indicators=indicators,
                    sentiment_score=sentiment_score,
                    regime=regime
                )
                
                # Log pair status
                self.logger.print_pair_status(pair, {
                    **signal_data,
                    "close": candles[0]["close"],
                    "volume": candles[0]["volume"],
                    "adx": indicators.adx,
                    "rsi": indicators.rsi_14,
                    "macd": indicators.macd,
                    "phantom_score": phantom_flags.score
                })
                
                # Check for entry (only BUY/SELL, not NEUTRAL)
                if signal_data["signal"] in ["BUY", "STRONG_BUY", "SELL", "STRONG_SELL"]:
                    self._check_entry(
                        pair=pair,
                        indicators=indicators,
                        signal_data=signal_data,
                        current_price=candles[0]["close"],
                        phantom_flags=phantom_flags,
                        phantom_penalty=phantom_penalty,
                        regime=regime
                    )
                    
            except Exception as e:
                print(f"  ❌ Entry scan error for {pair}: {e}")
                import traceback
                traceback.print_exc()
        
        # Update adaptive weights periodically
        if self.cycle_count % 10 == 0:
            self.adaptive_engine.update_weights()
            print(f"\n🔄 Updated adaptive weights")
    
    def _check_entry(self, pair: str, indicators: IndicatorValues, signal_data: Dict[str, Any],
                   current_price: float, phantom_flags: PhantomFlags,
                   phantom_penalty: float, regime: str):
        """Check and execute entry"""
        signal = signal_data["signal"]
        is_sell = signal in ["SELL", "STRONG_SELL"]
        
        # Calculate SL/TP
        stop_loss_pct = self.config["stop_loss_pct"]
        take_profit_r = self.config["take_profit_r"]
        
        if signal in ["BUY", "STRONG_BUY"]:
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + (stop_loss_pct * take_profit_r))
        else:  # SELL
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - (stop_loss_pct * take_profit_r))
        
        # Calculate position size
        size_result = self.risk_manager.position_size(
            pair=pair,
            entry_price=current_price,
            stop_loss=stop_loss,
            signal_score=signal_data["composite_score"],
            phantom_penalty=phantom_penalty,
            regime=regime
        )
        
        if size_result.size <= 0:
            print(f"  ❌ Position size too small for {pair} {signal}")
            return
        
        # Check affordability (max 90% of balance)
        if size_result.size_idr > self.config["paper_balance"] * 0.9:
            print(f"  ❌ Position size too large for {pair} {signal}")
            return
        
        # Calculate fee
        fee = size_result.size_idr * self.config["exchange"]["fee_pct"]
        
        # Create trade record
        trade_record = TradeRecord(
            id=0,
            pair=pair,
            signal=signal,
            entry_price=current_price,
            exit_price=0,
            size=size_result.size,
            entry_time=datetime.utcnow(),
            exit_time=None,
            stop_loss=stop_loss,
            take_profit=take_profit,
            pnl=0,
            pnl_pct=0,
            fee=fee,
            status="OPEN",
            regime=regime,
            phantom_flags=phantom_flags.__dict__,
            notes=f"Signal: {signal} | Score: {signal_data['composite_score']:.2f}"
        )
        
        # Add to store
        trade_id = self.trade_store.add_trade(trade_record)
        self.risk_manager.update_last_trade(pair)
        
        # Log entry
        self.logger.print_entry({
            "pair": pair,
            "signal": signal,
            "entry_price": current_price,
            "size": size_result.size,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk": size_result.risk_per_trade,
            "risk_pct": size_result.risk_pct,
            "regime": regime,
            "phantom_penalty": phantom_penalty * 100,
            "id": trade_id
        })
        
        # Execute trade (in paper or live mode)
        if self.config.get("mode") in ["paper", "live"]:
            if signal in ["BUY", "STRONG_BUY"]:
                result = self.exchange.limit_buy(pair, current_price, size_result.size)
            else:
                result = self.exchange.limit_sell(pair, current_price, size_result.size)
            
            if not result.get("success"):
                print(f"  ❌ Order failed for {pair} {signal}: {result.get('error')}")
                self.trade_store.update_trade(
                    trade_id=trade_id,
                    exit_price=current_price,
                    exit_time=datetime.utcnow(),
                    pnl=-fee,
                    pnl_pct=(-fee / size_result.size_idr) * 100,
                    status="FAILED"
                )
            else:
                print(f"  📝 Order placed for {pair} {signal}: ID {result['order_id']}")
    
    def run(self, interval_minutes: int = 5):
        """Run the bot in a loop"""
        self.running = True
        
        try:
            self.initialize()
            
            while self.running:
                start_time = time.time()
                
                try:
                    self.cycle()
                except Exception as e:
                    print(f"\n❌ Cycle error: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Calculate sleep time
                elapsed = time.time() - start_time
                sleep_time = max(0, (interval_minutes * 60) - elapsed)
                print(f"\n⏳ Next cycle in {sleep_time:.1f}s...")
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            self.logger.print_summary()
            self.running = False
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            self.logger.log_to_file(f"Fatal error: {e}", level="CRITICAL")
            self.running = False
    
    def stop(self):
        """Stop the bot"""
        self.running = False
        self.logger.print_summary()


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Indodax Autonomous Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py backtest --pairs BTC_IDR --timeframe 1h --start 2023-01-01 --end 2023-12-31
  python main.py paper --pairs BTC_IDR,ETH_IDR --timeframe 1h --interval 5
  python main.py live --pairs BTC_IDR --timeframe 1h
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Backtest command
    backtest_parser = subparsers.add_parser("backtest", help="Run backtesting on historical data")
    backtest_parser.add_argument("--pairs", type=str, default="BTC_IDR",
                                help="Comma-separated trading pairs (e.g., BTC_IDR,ETH_IDR)")
    backtest_parser.add_argument("--timeframe", type=str, default="1h",
                                help="Timeframe: 1m, 5m, 15m, 1h, 4h, 1d")
    backtest_parser.add_argument("--start", type=str, required=True,
                                help="Start date (YYYY-MM-DD)")
    backtest_parser.add_argument("--end", type=str, required=True,
                                help="End date (YYYY-MM-DD)")
    backtest_parser.add_argument("--balance", type=float, default=10_000_000,
                                help="Initial balance in IDR")
    
    # Paper trading command
    paper_parser = subparsers.add_parser("paper", help="Run paper trading (simulation)")
    paper_parser.add_argument("--pairs", type=str, default="BTC_IDR",
                             help="Comma-separated trading pairs")
    paper_parser.add_argument("--timeframe", type=str, default="1h",
                             help="Timeframe")
    paper_parser.add_argument("--interval", type=int, default=5,
                             help="Cycle interval in minutes")
    
    # Live trading command
    live_parser = subparsers.add_parser("live", help="Run live trading (REAL MONEY - BE CAREFUL!)")
    live_parser.add_argument("--pairs", type=str, default="BTC_IDR",
                            help="Comma-separated trading pairs")
    live_parser.add_argument("--timeframe", type=str, default="1h",
                            help="Timeframe")
    live_parser.add_argument("--interval", type=int, default=5,
                            help="Cycle interval in minutes")
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    # Load default config
    config = {
        "pairs": [p.strip() for p in args.pairs.split(",")],
        "timeframe": args.timeframe,
        "mode": args.command,
        "initial_balance": args.balance if hasattr(args, "balance") else 10_000_000,
    }
    
    # Load from config.json if exists
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r") as f:
                file_config = json.load(f)
            config.update(file_config)
        except Exception as e:
            print(f"Warning: Could not load config.json: {e}")
    
    # Load environment variables
    if os.path.exists(".env"):
        from dotenv import load_dotenv
        load_dotenv()
        
        # Decrypt API keys if encrypted
        if os.getenv("INDODAX_API_KEY_ENC"):
            try:
                manager = SecretManager()
                config["INDODAX_API_KEY"] = manager.decrypt(os.getenv("INDODAX_API_KEY_ENC"))
                config["INDODAX_SECRET_KEY"] = manager.decrypt(os.getenv("INDODAX_SECRET_KEY_ENC"))
            except Exception as e:
                print(f"Warning: Could not decrypt API keys: {e}")
    
    # Initialize bot
    bot = Bot(config)
    
    if args.command == "live":
        print("\n" + "=" * 60)
        print("⚠️  WARNING: LIVE TRADING MODE - REAL MONEY WILL BE USED!")
        print("=" * 60)
        print("\nPlease confirm:")
        print("- You have tested in paper trading for at least 1 week")
        print("- You understand all risks involved")
        print("- You have set proper stop losses")
        print("- Your API keys are correct and encrypted")
        print()
        
        confirm = input("Type 'I UNDERSTAND THE RISK' to continue: ")
        if confirm != "I UNDERSTAND THE RISK":
            print("\nLive trading cancelled. Use paper trading mode first.")
            sys.exit(0)
    
    # Run bot
    interval = getattr(args, "interval", 5)
    bot.run(interval_minutes=interval)


def _signal_handler(signum, frame):
    """Handle SIGTERM/SIGINT gracefully"""
    raise KeyboardInterrupt()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
