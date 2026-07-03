"""
Adaptive Engine for Dynamic Weight Adjustment
Adjusts signal weights based on performance in different market regimes
"""
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class AdaptiveState:
    """State for adaptive engine"""
    weights: Dict[str, float]  # Current signal weights
    win_rates: Dict[str, float]  # Win rate per signal component
    total_trades: Dict[str, int]  # Total trades per signal component
    current_regime: str  # Current market regime


class AdaptiveEngine:
    """
    Adaptively adjust signal weights based on performance.
    
    Features:
    - Market regime detection (choppy, ranging, trending, strong_trend, volatile)
    - Dynamic weight adjustment based on win rates
    - Regime-based position size multipliers
    - Performance tracking per signal component
    
    The engine automatically:
    1. Detects current market regime using ADX
    2. Tracks win rates for each signal component
    3. Adjusts weights to favor better-performing components
    4. Applies regime-based multipliers to position sizing
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adaptive engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.adaptive_settings = config.get("adaptive_settings", {
            "adx_choppy_threshold": 20,
            "adx_ranging_threshold": 25,
            "adx_trending_threshold": 50,
            "min_trades_for_adaptation": 20,
            "weight_adjustment_step": 0.05
        })
        
        # Initialize state
        signal_components = config.get("signal_weights", {}).keys()
        self.state = AdaptiveState(
            weights=config.get("signal_weights", {}).copy(),
            win_rates={comp: 0.5 for comp in signal_components},
            total_trades={comp: 0 for comp in signal_components},
            current_regime="ranging"
        )
    
    def detect_regime(self, adx: float, dmp_plus: float, dmp_minus: float) -> str:
        """
        Detect current market regime using ADX and Directional Movement
        
        Args:
            adx: Average Directional Index value
            dmp_plus: Plus Directional Movement
            dmp_minus: Minus Directional Movement
            
        Returns:
            str: Market regime
                - "choppy": ADX < 20 (no clear trend)
                - "ranging": 20 <= ADX < 25 (sideways movement)
                - "trending": 25 <= ADX < 50 (developing trend)
                - "strong_trend": ADX >= 50 (strong trend)
        """
        if adx < self.adaptive_settings["adx_choppy_threshold"]:
            return "choppy"
        elif adx < self.adaptive_settings["adx_ranging_threshold"]:
            return "ranging"
        elif adx < self.adaptive_settings["adx_trending_threshold"]:
            return "trending"
        else:
            return "strong_trend"
    
    def feed_trade(self, signal_scores: Dict[str, float], pnl: float):
        """
        Update performance metrics after a trade
        
        Args:
            signal_scores: Dictionary of component scores (0-100)
            pnl: Profit/Loss from the trade
        """
        for component in signal_scores:
            if component not in self.state.total_trades:
                continue
            
            # Update trade count
            self.state.total_trades[component] += 1
            
            # Update win rate
            if self.state.total_trades[component] > 0:
                if pnl > 0:
                    # Win
                    self.state.win_rates[component] = (
                        self.state.win_rates[component] * (self.state.total_trades[component] - 1) + 1
                    ) / self.state.total_trades[component]
                else:
                    # Loss
                    self.state.win_rates[component] = (
                        self.state.win_rates[component] * (self.state.total_trades[component] - 1) + 0
                    ) / self.state.total_trades[component]
    
    def update_weights(self):
        """
        Update signal weights based on performance
        
        Adjusts weights using:
        - Win rate of each component
        - Smoothing factor to prevent rapid changes
        - Minimum trade threshold to ensure statistical significance
        """
        min_trades = self.adaptive_settings["min_trades_for_adaptation"]
        adjustment_step = self.adaptive_settings["weight_adjustment_step"]
        
        for component in self.state.weights:
            if self.state.total_trades[component] < min_trades:
                continue  # Not enough data
            
            # Calculate target weight based on win rate
            # Scale: 0.1 (for 0% win rate) to 0.9 (for 100% win rate)
            target_weight = 0.1 + (self.state.win_rates[component] * 0.8)
            
            # Smooth adjustment
            adjustment = (target_weight - self.state.weights[component]) * adjustment_step
            new_weight = self.state.weights[component] + adjustment
            
            # Ensure weights stay within bounds
            new_weight = max(0.05, min(0.35, new_weight))
            self.state.weights[component] = new_weight
        
        # Normalize weights to sum to 1
        total = sum(self.state.weights.values())
        if total > 0:
            for component in self.state.weights:
                self.state.weights[component] /= total
        
        # Update config weights
        if "signal_weights" in self.config:
            self.config["signal_weights"].update(self.state.weights)
    
    def get_multipliers(self, regime: str) -> Dict[str, float]:
        """
        Get position size and threshold multipliers based on market regime
        
        Args:
            regime: Market regime
            
        Returns:
            Dictionary with multipliers
                - position_size_multiplier: Factor to apply to position size
                - entry_threshold_multiplier: Factor to apply to entry thresholds
        """
        regime_multipliers = self.config.get("risk_parameters", {}).get("regime_multipliers", {
            "choppy": 0.5,
            "ranging": 0.75,
            "trending": 1.25,
            "strong_trend": 1.5,
            "volatile": 0.25
        })
        
        if regime not in regime_multipliers:
            regime = "ranging"  # Default
        
        return {
            "position_size_multiplier": regime_multipliers[regime],
            "entry_threshold_multiplier": regime_multipliers[regime] * 0.8
        }
    
    def update_regime(self, regime: str):
        """
        Update current market regime
        
        Args:
            regime: New market regime
        """
        self.state.current_regime = regime
    
    def get_current_regime(self) -> str:
        """Get current market regime"""
        return self.state.current_regime
    
    def get_weights(self) -> Dict[str, float]:
        """Get current signal weights"""
        return self.state.weights.copy()
    
    def get_performance(self) -> Dict[str, Dict[str, float]]:
        """Get performance metrics for all components"""
        return {
            comp: {
                "win_rate": self.state.win_rates[comp],
                "total_trades": self.state.total_trades[comp],
                "weight": self.state.weights[comp]
            }
            for comp in self.state.weights
        }
