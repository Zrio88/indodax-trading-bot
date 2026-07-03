"""
Risk Manager for Position Sizing and Trading Guards
Implements comprehensive risk management with 7 guards
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

from storage.database import TradeStore


@dataclass
class RiskCheckResult:
    """Result of risk check"""
    can_trade: bool
    reason: Optional[str] = None
    allowed_pairs: Optional[List[str]] = None


@dataclass
class PositionSizeResult:
    """Result of position size calculation"""
    size: float  # Size in base currency (e.g., BTC)
    size_idr: float  # Size in IDR
    risk_per_trade: float  # Risk amount in IDR
    risk_pct: float  # Risk percentage


class RiskManager:
    """
    Comprehensive risk management system with 7 guards:
    
    1. Daily Loss Limit: Maximum daily loss percentage (default: 2%)
    2. Max Drawdown: Maximum drawdown from peak balance (default: 5%)
    3. Loss Streak: Maximum consecutive losses (default: 3)
    4. Max Positions: Maximum number of open positions (default: 3)
    5. Cooldown: Minimum time between trades after max loss (default: 30 min)
    6. Balance Check: Minimum balance required (default: IDR 100,000)
    7. Allowed Pairs: Only trade configured pairs
    
    Position sizing uses:
    - Half-Kelly Criterion
    - Drawdown multiplier
    - Regime multiplier
    - Phantom penalty
    - Signal score multiplier
    """
    
    def __init__(self, config: Dict[str, Any], trade_store: TradeStore):
        """
        Initialize risk manager
        
        Args:
            config: Configuration dictionary
            trade_store: TradeStore instance for accessing trade history
        """
        self.config = config
        self.trade_store = trade_store
        self.risk_params = config.get("risk_parameters", {
            "daily_loss_limit_pct": 0.02,
            "max_drawdown_pct": 0.05,
            "max_loss_streak": 3,
            "max_positions": 3,
            "cooldown_minutes": 30,
            "kelly_fraction": 0.5
        })
        self.paper_balance = config.get("initial_balance", 10_000_000)
        self.last_trade_time: Dict[str, datetime] = {}
        self.daily_pnl: Dict[str, float] = {}
        self.current_drawdown: float = 0.0
        self.peak_balance: float = self.paper_balance
    
    def update_balance(self, pnl: float, pair: str):
        """
        Update paper balance after a trade
        
        Args:
            pnl: Profit/Loss from the trade
            pair: Trading pair
        """
        self.paper_balance += pnl
        
        # Update peak balance and drawdown
        if self.paper_balance > self.peak_balance:
            self.peak_balance = self.paper_balance
        
        self.current_drawdown = (self.peak_balance - self.paper_balance) / self.peak_balance if self.peak_balance > 0 else 0
        
        # Update daily PnL
        today = datetime.utcnow().date().isoformat()
        if today not in self.daily_pnl:
            self.daily_pnl[today] = 0.0
        self.daily_pnl[today] += pnl
    
    def record_trade(self, trade_id: int, pnl: float, pair: str):
        """
        Record a completed trade
        
        Args:
            trade_id: ID of the trade
            pnl: Profit/Loss from the trade
            pair: Trading pair
        """
        self.update_balance(pnl, pair)
        
        # Update trade store
        trade = self.trade_store.get_trade(trade_id)
        if trade:
            if trade.size == 0:
                exit_price = trade.entry_price
            elif trade.signal == "BUY":
                exit_price = trade.entry_price + (pnl / trade.size)
            else:
                exit_price = trade.entry_price - (pnl / trade.size)
            self.trade_store.close_trade(trade_id, exit_price, datetime.utcnow())
    
    def can_trade(self, pair: str = None) -> RiskCheckResult:
        """
        Check if trading is allowed (all 7 guards)
        
        Args:
            pair: Optional pair to check (checks all pairs if None)
            
        Returns:
            RiskCheckResult with can_trade flag and reason if blocked
        """
        # 1. Daily Loss Limit Check
        today = datetime.utcnow().date().isoformat()
        daily_pnl = self.daily_pnl.get(today, 0.0)
        daily_loss_limit = self.paper_balance * self.risk_params.get("daily_loss_limit_pct", 0.02)
        
        if daily_pnl < -daily_loss_limit:
            return RiskCheckResult(
                can_trade=False,
                reason=f"Daily loss limit reached (IDR {daily_pnl:,.2f})"
            )
        
        # 2. Max Drawdown Check
        if self.current_drawdown > self.risk_params.get("max_drawdown_pct", 0.05):
            return RiskCheckResult(
                can_trade=False,
                reason=f"Max drawdown reached ({self.current_drawdown:.2%})"
            )
        
        # 3. Loss Streak Check
        if pair:
            loss_streak = self.trade_store.loss_streak(pair)
            max_loss_streak = self.risk_params.get("max_loss_streak", 3)
            
            if loss_streak >= max_loss_streak:
                cooldown_minutes = self.risk_params.get("cooldown_minutes", 30)
                last_trade = self.last_trade_time.get(pair)
                
                if last_trade and (datetime.utcnow() - last_trade) < timedelta(minutes=cooldown_minutes):
                    remaining = cooldown_minutes - (datetime.utcnow() - last_trade).total_seconds() / 60
                    return RiskCheckResult(
                        can_trade=False,
                        reason=f"Loss streak pause ({loss_streak} losses). Cooldown: {remaining:.1f}min"
                    )
        
        # 4. Max Positions Check
        open_trades = len(self.trade_store.open_trades())
        max_positions = self.risk_params.get("max_positions", 3)
        
        if open_trades >= max_positions:
            return RiskCheckResult(
                can_trade=False,
                reason=f"Max positions reached ({open_trades}/{max_positions})"
            )
        
        # 5. Cooldown Check (per pair)
        if pair:
            last_trade = self.last_trade_time.get(pair)
            if last_trade and (datetime.utcnow() - last_trade) < timedelta(minutes=5):
                remaining = 5 - (datetime.utcnow() - last_trade).total_seconds() / 60
                return RiskCheckResult(
                    can_trade=False,
                    reason=f"Pair cooldown: {remaining:.1f}min"
                )
        
        # 6. Balance Check
        min_balance = 100_000  # Minimum IDR 100K
        if self.paper_balance < min_balance:
            return RiskCheckResult(
                can_trade=False,
                reason=f"Insufficient balance (IDR {self.paper_balance:,.2f})"
            )
        
        # 7. Allowed Pairs Check
        allowed_pairs = self.config.get("pairs", [])
        if pair and pair not in allowed_pairs:
            return RiskCheckResult(
                can_trade=False,
                reason=f"Pair not allowed: {pair}",
                allowed_pairs=allowed_pairs
            )
        
        return RiskCheckResult(can_trade=True)
    
    def position_size(
        self,
        pair: str,
        entry_price: float,
        stop_loss: float,
        signal_score: float,
        phantom_penalty: float,
        regime: str,
        atr_14: float = 0.0
    ) -> PositionSizeResult:
        """
        Calculate position size using multiple factors
        
        Uses:
        - Half-Kelly Criterion for base position size
        - Regime multiplier to adjust for market conditions
        - Signal score multiplier (better signals = larger positions)
        - Phantom penalty to reduce size in suspicious conditions
        - Drawdown multiplier to reduce size when in drawdown
        - Maximum risk per trade limit
        
        Args:
            pair: Trading pair
            entry_price: Entry price
            stop_loss: Stop loss price
            signal_score: Signal score (0-100)
            phantom_penalty: Phantom penalty factor (0-1)
            regime: Market regime
            
        Returns:
            PositionSizeResult with calculated size
        """
        # 1. Validate stop loss
        if stop_loss <= 0 or entry_price <= 0:
            return PositionSizeResult(size=0, size_idr=0, risk_per_trade=0, risk_pct=0)
        
        # 2. Calculate stop loss percentage
        stop_loss_pct = abs((entry_price - stop_loss) / entry_price)
        
        if stop_loss_pct <= 0:
            return PositionSizeResult(size=0, size_idr=0, risk_per_trade=0, risk_pct=0)
        
        # 3. Volatility-adjusted stop loss (widen in high volatility)
        if atr_14 > 0 and entry_price > 0:
            atr_pct = atr_14 / entry_price
            vol_regime = "high" if atr_pct > 0.03 else "normal" if atr_pct > 0.01 else "low"
            vol_mult = {"high": 1.3, "normal": 1.0, "low": 0.7}.get(vol_regime, 1.0)
        else:
            vol_mult = 1.0
        actual_sl_pct = stop_loss_pct * vol_mult
        actual_stop_loss = entry_price * (1 - actual_sl_pct) if stop_loss < entry_price else entry_price * (1 + actual_sl_pct)
        adjusted_stop_loss_pct = abs((entry_price - actual_stop_loss) / entry_price)

        # 4. Dynamic win probability from trade history
        recent_trades = self.trade_store.recent_trades(self.paper_balance)
        if recent_trades:
            wins = [t for t in recent_trades if getattr(t, 'pnl', 0) > 0]
            win_prob = len(wins) / len(recent_trades) if recent_trades else 0.5
            # Clamp between 0.3-0.8 to avoid extreme values
            win_prob = max(0.3, min(0.8, win_prob))
        else:
            win_prob = 0.6

        # 5. Base position size (Half-Kelly)
        win_loss_ratio = 2.0
        kelly_fraction = self.risk_params.get("kelly_fraction", 0.5)
        
        base_size_idr = self.paper_balance * kelly_fraction * (
            win_prob - ((1 - win_prob) / win_loss_ratio)
        )
        
        # 4. Apply multipliers
        regime_multipliers = self.risk_params.get("regime_multipliers", {})
        position_multiplier = regime_multipliers.get(regime, 1.0)
        
        # Signal score multiplier (0-2x)
        signal_multiplier = 0.5 + (signal_score / 100.0)
        
        # Phantom penalty multiplier (0-1x)
        phantom_multiplier = 1.0 - phantom_penalty
        
        # Drawdown multiplier (reduce size when in drawdown)
        drawdown_multiplier = 1.0 - (self.current_drawdown * 2)
        
        # Apply all multipliers
        adjusted_size_idr = base_size_idr * \
                            position_multiplier * \
                            signal_multiplier * \
                            phantom_multiplier * \
                            drawdown_multiplier
        
        # 5. Calculate size in base currency
        size = adjusted_size_idr / entry_price
        
        # 8. Portfolio risk check: sum risk of all open positions
        open_trades = self.trade_store.open_trades()
        total_risk = 0.0
        for t in open_trades:
            if t.entry_price and t.stop_loss:
                t_risk_pct = abs((t.entry_price - t.stop_loss) / t.entry_price)
                total_risk += t.size * t.entry_price * t_risk_pct
        remaining_risk_capacity = max(0, self.paper_balance * 0.06 - total_risk)

        # 9. Apply maximum risk per trade limit
        max_risk_per_trade = self.paper_balance * 0.02  # 2% max risk
        max_risk_per_trade = min(max_risk_per_trade, remaining_risk_capacity)
        max_size_idr = max_risk_per_trade / adjusted_stop_loss_pct if adjusted_stop_loss_pct > 0 else 0
        max_size = max_size_idr / entry_price
        
        # Take the smaller of the two
        final_size = min(size, max_size)
        
        # 10. Ensure minimum order size
        min_order_size = self.config.get("exchange", {}).get("min_order_size", 0.0001)
        if final_size < min_order_size:
            return PositionSizeResult(size=0, size_idr=0, risk_per_trade=0, risk_pct=0)
        
        # 11. Calculate actual risk
        risk_per_trade = final_size * entry_price * adjusted_stop_loss_pct
        risk_pct = (risk_per_trade / self.paper_balance) * 100 if self.paper_balance > 0 else 0
        
        return PositionSizeResult(
            size=round(final_size, 8),
            size_idr=final_size * entry_price,
            risk_per_trade=risk_per_trade,
            risk_pct=risk_pct
        )
    
    def update_last_trade(self, pair: str):
        """Update last trade time for a pair"""
        self.last_trade_time[pair] = datetime.utcnow()
    
    def get_balance(self) -> float:
        """Get current paper balance"""
        return self.paper_balance
    
    def get_current_drawdown(self) -> float:
        """Get current drawdown percentage"""
        return self.current_drawdown
    
    def get_daily_pnl(self, date: str = None) -> float:
        """Get daily PnL for a specific date or today"""
        if date is None:
            date = datetime.utcnow().date().isoformat()
        return self.daily_pnl.get(date, 0.0)
