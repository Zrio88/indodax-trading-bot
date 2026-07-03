"""
Logger for Structured Logging and Monitoring
Provides console output and file logging with JSON format
"""
from typing import Dict, Any, Optional
from datetime import datetime
import sys
import json
import os


class Logger:
    """
    Structured logging for the trading bot.
    
    Features:
    - Console output with colored formatting
    - JSON file logging for analysis
    - Trade entry/exit notifications
    - Pair status updates
    - Summary statistics
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize logger
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.start_time = datetime.utcnow()
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
    
    def print_banner(self):
        """Print startup banner"""
        print("""
   _____ _____  _____ _____ _____ _____ _____ _____
  |   __| __  |     |  |  | __  |     |     |  |  |
  |  |  |    -|  |  |  |  | __ -|  |  |  |  |  |  |
  |_____|__|__|_____|_____|_____|_____|_____|_____|

        INDODAX AUTONOMOUS TRADING BOT
        ===============================
        """)
        print(f"Started at: {self.start_time}")
        print(f"Mode: {self.config.get('mode', 'paper')}")
        print(f"Pairs: {', '.join(self.config.get('pairs', []))}")
        print(f"Timeframe: {self.config.get('timeframe', '1h')}")
        print("=" * 60)
    
    def print_header(self, cycle: int):
        """Print cycle header"""
        uptime = datetime.utcnow() - self.start_time
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{uptime.days}d {hours}h {minutes}m {seconds}s"
        
        balance = self.config.get('paper_balance', 0)
        win_rate = self.win_rate()
        
        print(f"\n{'=' * 70}")
        print(f"📊 CYCLE {cycle:04d} | Uptime: {uptime_str}")
        print(f"   Balance: IDR {balance:,.2f} | Trades: {self.trade_count} | Win Rate: {win_rate:.2%}")
        print(f"{'=' * 70}")
    
    def print_pair_status(self, pair: str, data: Dict[str, Any]):
        """Print status for a trading pair"""
        signal = data.get('signal', 'N/A')
        score = data.get('composite_score', 0)
        regime = data.get('regime', 'N/A')
        phantom = data.get('phantom_score', 0)
        adx = data.get('adx', 0)
        rsi = data.get('rsi', 0)
        macd = data.get('macd', 0)
        close = data.get('close', 0)
        
        print(f"\n📈 {pair}:")
        print(f"   Price: IDR {close:,.2f}")
        print(f"   Signal: {signal}")
        print(f"   Score: {score:.2f}/100")
        print(f"   Regime: {regime}")
        print(f"   Phantom: {phantom:.1f}%")
        print(f"   Indicators: ADX={adx:.2f} | RSI={rsi:.2f} | MACD={macd:.4f}")
    
    def print_entry(self, trade: Dict[str, Any]):
        """Print trade entry confirmation"""
        self.trade_count += 1
        pair = trade.get('pair', 'N/A')
        signal = trade.get('signal', 'N/A')
        price = trade.get('entry_price', 0)
        size = trade.get('size', 0)
        stop_loss = trade.get('stop_loss', 0)
        take_profit = trade.get('take_profit', 0)
        risk = trade.get('risk', 0)
        risk_pct = trade.get('risk_pct', 0)
        regime = trade.get('regime', 'N/A')
        phantom = trade.get('phantom_penalty', 0)
        trade_id = trade.get('id', 0)
        
        print(f"\n✅ ENTRY CONFIRMED [ID: {trade_id}]:")
        print(f"   Pair: {pair}")
        print(f"   Signal: {signal}")
        print(f"   Price: IDR {price:,.2f}")
        print(f"   Size: {size:.8f} {pair.split('_')[0]}")
        print(f"   Stop Loss: IDR {stop_loss:,.2f}")
        print(f"   Take Profit: IDR {take_profit:,.2f}")
        print(f"   Risk: IDR {risk:,.2f} ({risk_pct:.2f}%)")
        print(f"   Regime: {regime}")
        print(f"   Phantom Penalty: {phantom:.1f}%")
    
    def print_exit(self, exit_data: Dict[str, Any]):
        """Print trade exit confirmation"""
        pair = exit_data.get('pair', 'N/A')
        trade_id = exit_data.get('trade_id', 0)
        action = exit_data.get('action', 'N/A')
        price = exit_data.get('exit_price', 0)
        pnl = exit_data.get('pnl', 0)
        pnl_pct = exit_data.get('pnl_pct', 0)
        reason = exit_data.get('reason', 'N/A')
        
        if pnl >= 0:
            self.winning_trades += 1
            print(f"\n🟢 EXIT PROFITABLE [ID: {trade_id}]:")
        else:
            self.losing_trades += 1
            print(f"\n🔴 EXIT WITH LOSS [ID: {trade_id}]:")
        
        print(f"   Pair: {pair}")
        print(f"   Action: {action}")
        print(f"   Exit Price: IDR {price:,.2f}")
        print(f"   PnL: IDR {pnl:,.2f} ({pnl_pct:.2f}%)")
        print(f"   Reason: {reason}")
    
    def print_summary(self):
        """Print trading summary"""
        uptime = datetime.utcnow() - self.start_time
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{uptime.days}d {hours}h {minutes}m {seconds}s"
        
        balance = self.config.get('paper_balance', 0)
        initial = self.config.get('initial_balance', 10_000_000)
        total_pnl = balance - initial
        total_pnl_pct = (total_pnl / initial) * 100 if initial > 0 else 0
        
        win_rate = self.win_rate()
        
        print(f"\n{'=' * 70}")
        print("                   TRADING SUMMARY")
        print(f"{'=' * 70}")
        print(f"Total Trades:     {self.trade_count:>10}")
        print(f"Winning Trades:  {self.winning_trades:>10}")
        print(f"Losing Trades:   {self.losing_trades:>10}")
        print(f"Win Rate:        {win_rate:>10.2%}")
        print(f"Initial Balance:  IDR {initial:>15,.2f}")
        print(f"Current Balance:  IDR {balance:>15,.2f}")
        print(f"Total PnL:       IDR {total_pnl:>15,.2f} ({total_pnl_pct:>+7.2f}%)")
        print(f"Uptime:          {uptime_str}")
        print(f"{'=' * 70}\n")
    
    def win_rate(self) -> float:
        """Calculate current win rate"""
        if self.trade_count == 0:
            return 0.0
        return self.winning_trades / self.trade_count
    
    def log_to_file(self, message: str, level: str = "INFO"):
        """Log message to file in JSON format"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "cycle": self.trade_count,
            "balance": self.config.get("paper_balance", 0),
            "win_rate": self.win_rate(),
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades
        }
        
        try:
            with open("logs/bot.log", "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except OSError as e:
            print(f"Warning: Could not write to log file: {e}")
    
    def log_trade(self, trade_data: Dict[str, Any], action: str = "ENTRY"):
        """Log a trade to file"""
        trade_data["timestamp"] = datetime.utcnow().isoformat()
        trade_data["action"] = action
        
        try:
            with open("logs/trades.log", "a") as f:
                f.write(json.dumps(trade_data) + "\n")
        except OSError as e:
            print(f"Warning: Could not write trade log: {e}")
