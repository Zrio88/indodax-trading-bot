"""
Phantom Detection for Market Manipulation
Detects wash trades, pump & dump, and other anomalous market behavior
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class PhantomFlags:
    """Flags for detected market anomalies"""
    wash_trade: bool = False
    pump_dump: bool = False
    doji_manipulation: bool = False
    consecutive_bullish: bool = False
    consecutive_bearish: bool = False
    spread_anomaly: bool = False
    score: float = 0.0  # 0-100 (higher = more suspicious)


class PhantomDetector:
    """
    Detect market manipulation and anomalies using various patterns:
    - Wash Trade: Volume spike without price movement
    - Pump & Dump: Rapid price increase followed by crash
    - Doji Manipulation: Small body with high volume
    - Consecutive Candles: Unnatural sequence of bullish/bearish candles
    - Spread Anomaly: Unusually large spread compared to recent history
    
    The penalty factor (0-1) can be used to reduce position size or block trades.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize phantom detector with configuration
        
        Args:
            config: Configuration dictionary with phantom_thresholds
        """
        self.config = config
        self.thresholds = config.get("phantom_thresholds", {
            "wash_trade_volume_multiplier": 6.0,
            "pump_dump_threshold": 0.15,
            "doji_manipulation_size": 0.001,
            "spread_anomaly_pct": 0.03,
            "consecutive_bullish": 8
        })
        self.history: Dict[str, pd.DataFrame] = {}  # {pair: DataFrame}
    
    def update(self, pair: str, candle: Dict[str, Any]):
        """
        Update detector with new candle data
        
        Args:
            pair: Trading pair (e.g., BTC_IDR)
            candle: Dictionary with candle data (timestamp, open, high, low, close, volume)
        """
        # Convert timestamp if needed
        timestamp = candle.get("timestamp")
        if hasattr(timestamp, "isoformat"):
            timestamp = timestamp.isoformat()
        
        new_row = pd.DataFrame([{
            "timestamp": timestamp,
            "open": candle.get("open", 0),
            "high": candle.get("high", 0),
            "low": candle.get("low", 0),
            "close": candle.get("close", 0),
            "volume": candle.get("volume", 0)
        }])
        
        if pair not in self.history:
            self.history[pair] = new_row
        else:
            self.history[pair] = pd.concat([self.history[pair], new_row], ignore_index=True)
        
        # Keep only recent data (last 100 candles)
        if len(self.history[pair]) > 100:
            self.history[pair] = self.history[pair].tail(100)
    
    def detect(self, pair: str) -> PhantomFlags:
        """
        Detect anomalies for a given pair
        
        Args:
            pair: Trading pair to analyze
            
        Returns:
            PhantomFlags object with detected anomalies and score
        """
        if pair not in self.history or len(self.history[pair]) < 5:
            return PhantomFlags()
        
        df = self.history[pair]
        
        # Ensure we have the required columns
        required_cols = ["close", "volume", "high", "low", "open"]
        if not all(col in df.columns for col in required_cols):
            return PhantomFlags()
        
        closes = df["close"].values.astype(float)
        volumes = df["volume"].values.astype(float)
        highs = df["high"].values.astype(float)
        lows = df["low"].values.astype(float)
        opens = df["open"].values.astype(float)
        
        flags = PhantomFlags()
        
        # 1. Wash Trade Detection
        # Volume spike (6x previous) with minimal price movement (<0.5%)
        if len(volumes) >= 2 and len(closes) >= 2:
            volume_ratio = volumes[-1] / volumes[-2] if volumes[-2] > 0 else 1
            price_change = abs(closes[-1] - closes[-2]) / closes[-2] if closes[-2] > 0 else 0
            
            if (volume_ratio >= self.thresholds["wash_trade_volume_multiplier"] and
                price_change < 0.005):  # Less than 0.5% price movement
                flags.wash_trade = True
                flags.score += 30
        
        # 2. Pump & Dump Detection
        # Rapid price increase (>15%) over 5 candles
        if len(closes) >= 5:
            recent_closes = closes[-5:]
            price_change_pct = (recent_closes[-1] - recent_closes[0]) / recent_closes[0] if recent_closes[0] > 0 else 0
            
            if price_change_pct > self.thresholds["pump_dump_threshold"]:
                flags.pump_dump = True
                flags.score += 40
        
        # 3. Doji Manipulation Detection
        # Small body relative to range with high volume
        if len(df) >= 1:
            candle = df.iloc[-1]
            body_size = abs(candle["close"] - candle["open"])
            range_size = candle["high"] - candle["low"]
            
            if range_size > 0 and body_size / range_size < 0.1:
                # Compare to average volume
                if len(volumes) >= 5:
                    avg_volume = np.mean(volumes[-5:-1])
                    if avg_volume > 0 and candle["volume"] > avg_volume * 2:
                        flags.doji_manipulation = True
                        flags.score += 25
        
        # 4. Consecutive Bullish/Bearish Candles
        consecutive_bullish = 0
        consecutive_bearish = 0
        
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                consecutive_bullish += 1
                consecutive_bearish = 0
            else:
                consecutive_bearish += 1
                consecutive_bullish = 0
            
            if consecutive_bullish >= self.thresholds["consecutive_bullish"]:
                flags.consecutive_bullish = True
                flags.score += 20
            if consecutive_bearish >= self.thresholds["consecutive_bullish"]:
                flags.consecutive_bearish = True
                flags.score += 20
        
        # 5. Spread Anomaly Detection
        # Spread significantly larger than previous
        if len(df) >= 2:
            last_candle = df.iloc[-1]
            prev_candle = df.iloc[-2]
            
            spread = (last_candle["high"] - last_candle["low"]) / last_candle["low"] if last_candle["low"] > 0 else 0
            prev_spread = (prev_candle["high"] - prev_candle["low"]) / prev_candle["low"] if prev_candle["low"] > 0 else 0
            
            if spread > 0 and prev_spread > 0:
                spread_ratio = spread / prev_spread
                if spread_ratio > (1 + self.thresholds["spread_anomaly_pct"]):
                    flags.spread_anomaly = True
                    flags.score += 15
        
        # Cap score at 100
        flags.score = min(flags.score, 100)
        
        return flags
    
    def penalty_factor(self, flags: PhantomFlags) -> float:
        """
        Calculate penalty factor based on detected anomalies
        
        Args:
            flags: PhantomFlags object
            
        Returns:
            float: Penalty factor (0-1)
                - 0: No penalty
                - 0.25: 25% reduction in position size
                - 0.5: 50% reduction
                - 0.75: 75% reduction
                - 1.0: Block trade entirely
        """
        if flags.score < 20:
            return 0.0
        elif flags.score < 40:
            return 0.25
        elif flags.score < 60:
            return 0.5
        elif flags.score < 80:
            return 0.75
        else:
            return 1.0
    
    def get_history(self, pair: str) -> Optional[pd.DataFrame]:
        """Get stored history for a pair"""
        return self.history.get(pair)
    
    def clear_history(self, pair: str = None):
        """Clear history for a pair or all pairs"""
        if pair:
            self.history.pop(pair, None)
        else:
            self.history.clear()
