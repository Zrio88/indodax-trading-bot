"""
Exit Manager for Trade Exit Conditions
Handles stop loss, take profit, trailing stops, and breakeven
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

from storage.database import TradeStore, TradeRecord
from .risk_manager import RiskManager


@dataclass
class ExitSignal:
    """Signal to exit a trade"""
    pair: str
    trade_id: int
    action: str  # CLOSE, BREAKEVEN, TRAILING
    price: float
    reason: str


class ExitManager:
    """
    Manage exit conditions for open trades.
    
    Implements 5 exit conditions:
    1. Stop Loss: Fixed percentage stop loss
    2. Take Profit: Fixed risk-reward ratio (e.g., 2:1)
    3. Trailing Stop: 2x ATR trailing stop
    4. Breakeven: Move stop loss to breakeven when price moves favorably
    5. Time Stop: Close trade after 24 hours
    """
    
    def __init__(self, config: Dict[str, Any], trade_store: TradeStore):
        """
        Initialize exit manager
        
        Args:
            config: Configuration dictionary
            trade_store: TradeStore instance
        """
        self.config = config
        self.trade_store = trade_store
        self.stop_loss_pct = config.get("stop_loss_pct", 0.05)
        self.take_profit_r = config.get("take_profit_r", 2.0)
        self.peak_prices: Dict[int, float] = {}  # trade_id -> highest price seen
        self.lowest_prices: Dict[int, float] = {}  # trade_id -> lowest price seen
    
    def check(self, pair: str, current_price: float, current_time: datetime) -> List[ExitSignal]:
        """
        Check all open trades for a pair for exit conditions
        
        Args:
            pair: Trading pair
            current_price: Current market price
            current_time: Current time
            
        Returns:
            List of ExitSignal objects for trades that should be exited
        """
        exit_signals = []
        open_trades = self.trade_store.open_trades(pair)
        
        for trade in open_trades:
            exit_signal = self._check_trade(trade, current_price, current_time)
            if exit_signal:
                exit_signals.append(exit_signal)
        
        return exit_signals
    
    def _check_trade(
        self,
        trade: TradeRecord,
        current_price: float,
        current_time: datetime
    ) -> Optional[ExitSignal]:
        """
        Check a single trade for exit conditions
        
        Args:
            trade: TradeRecord to check
            current_price: Current market price
            current_time: Current time
            
        Returns:
            ExitSignal if trade should be exited, None otherwise
        """
        # 1. Stop Loss Check
        if (trade.signal == "BUY" and current_price <= trade.stop_loss) or \
           (trade.signal == "SELL" and current_price >= trade.stop_loss):
            return ExitSignal(
                pair=trade.pair,
                trade_id=trade.id,
                action="CLOSE",
                price=current_price,
                reason=f"Stop Loss Hit (IDR {trade.stop_loss:,.2f})"
            )
        
        # 2. Take Profit Check
        if (trade.signal == "BUY" and current_price >= trade.take_profit) or \
           (trade.signal == "SELL" and current_price <= trade.take_profit):
            return ExitSignal(
                pair=trade.pair,
                trade_id=trade.id,
                action="CLOSE",
                price=current_price,
                reason=f"Take Profit Hit (IDR {trade.take_profit:,.2f})"
            )
        
        # 3. Trailing Stop Check
        # For profitable trades, track peak/low and trail stop behind
        atr = getattr(trade, 'atr_14', None)
        if atr is not None and atr > 0:
            if trade.signal == "BUY" and current_price > trade.entry_price:
                old_peak = self.peak_prices.get(trade.id, current_price)
                new_peak = max(old_peak, current_price)
                self.peak_prices[trade.id] = new_peak
                trailing_stop = new_peak - (atr * 2)
                if current_price <= trailing_stop and trailing_stop > trade.entry_price:
                    return ExitSignal(
                        pair=trade.pair,
                        trade_id=trade.id,
                        action="CLOSE",
                        price=current_price,
                        reason=f"Trailing Stop Hit (IDR {trailing_stop:,.2f})"
                    )
            elif trade.signal == "SELL" and current_price < trade.entry_price:
                old_low = self.lowest_prices.get(trade.id, current_price)
                new_low = min(old_low, current_price)
                self.lowest_prices[trade.id] = new_low
                trailing_stop = new_low + (atr * 2)
                if current_price >= trailing_stop and trailing_stop < trade.entry_price:
                    return ExitSignal(
                        pair=trade.pair,
                        trade_id=trade.id,
                        action="CLOSE",
                        price=current_price,
                        reason=f"Trailing Stop Hit (IDR {trailing_stop:,.2f})"
                    )
        
        # 4. Breakeven Check
        # Move stop loss to breakeven when price moves favorably
        if trade.signal == "BUY":
            breakeven_price = trade.entry_price * (1 + (trade.fee / (trade.entry_price * trade.size)))
            if current_price >= breakeven_price and trade.stop_loss < breakeven_price:
                return ExitSignal(
                    pair=trade.pair,
                    trade_id=trade.id,
                    action="BREAKEVEN",
                    price=breakeven_price,
                    reason="Breakeven Stop Loss"
                )
        else:  # SELL
            breakeven_price = trade.entry_price * (1 - (trade.fee / (trade.entry_price * trade.size)))
            if current_price <= breakeven_price and trade.stop_loss > breakeven_price:
                return ExitSignal(
                    pair=trade.pair,
                    trade_id=trade.id,
                    action="BREAKEVEN",
                    price=breakeven_price,
                    reason="Breakeven Stop Loss"
                )
        
        # 5. Time Stop Check (24 hours)
        if (current_time - trade.entry_time) > timedelta(hours=24):
            return ExitSignal(
                pair=trade.pair,
                trade_id=trade.id,
                action="CLOSE",
                price=current_price,
                reason="24h Time Stop"
            )
        
        return None
    
    def execute_exit(
        self,
        exit_signal: ExitSignal,
        exchange: Any,
        risk_manager: RiskManager
    ) -> Dict[str, Any]:
        """
        Execute exit for a trade
        
        Args:
            exit_signal: ExitSignal to execute
            exchange: Exchange instance (for live trading)
            risk_manager: RiskManager instance
            
        Returns:
            Dictionary with exit result
        """
        trade = self.trade_store.get_trade(exit_signal.trade_id)
        if not trade:
            return {"success": False, "error": "Trade not found"}
        
        if exit_signal.action == "CLOSE":
            # Calculate PnL
            if trade.signal == "BUY":
                pnl = (exit_signal.price - trade.entry_price) * trade.size - trade.fee
            else:  # SELL
                pnl = (trade.entry_price - exit_signal.price) * trade.size - trade.fee
            
            # Close the trade in the store
            self.trade_store.close_trade(
                exit_signal.trade_id,
                exit_signal.price,
                datetime.utcnow()
            )
            
            # Update risk manager
            risk_manager.record_trade(exit_signal.trade_id, pnl, trade.pair)
            
            # Feed trade to adaptive engine
            # (Would need access to adaptive engine and signal scores)
            
            return {
                "success": True,
                "action": exit_signal.action,
                "pair": exit_signal.pair,
                "trade_id": exit_signal.trade_id,
                "exit_price": exit_signal.price,
                "pnl": pnl,
                "pnl_pct": (pnl / (trade.entry_price * trade.size)) * 100,
                "reason": exit_signal.reason
            }
        
        elif exit_signal.action == "BREAKEVEN":
            # Update stop loss to breakeven
            self.trade_store.breakeven_trade(exit_signal.trade_id, exit_signal.price)
            return {
                "success": True,
                "action": exit_signal.action,
                "pair": exit_signal.pair,
                "trade_id": exit_signal.trade_id,
                "new_stop_loss": exit_signal.price,
                "reason": exit_signal.reason
            }
        
        return {"success": False, "error": "Unknown action"}
