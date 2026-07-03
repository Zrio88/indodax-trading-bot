"""
SQLite Database Storage for Trade History
Stores trades, daily PnL, and market data for analysis
"""
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
import json
import os


@dataclass
class TradeRecord:
    """Data class for trade records"""
    id: int
    pair: str
    signal: str  # BUY/SELL
    entry_price: float
    exit_price: float
    size: float
    entry_time: datetime
    exit_time: Optional[datetime]
    stop_loss: float
    take_profit: float
    pnl: float
    pnl_pct: float
    fee: float
    status: str  # OPEN/CLOSED/BREAKEVEN/FAILED
    regime: str
    phantom_flags: Dict[str, Any]
    notes: str


class TradeStore:
    """
    SQLite-based storage for trades, daily PnL, and market data.
    
    Provides methods for:
    - Adding and updating trades
    - Querying open/closed trades
    - Calculating performance metrics
    - Caching market data
    """
    
    def __init__(self, db_path: str = "storage/trades.db"):
        """
        Initialize TradeStore
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pair TEXT NOT NULL,
                    signal TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    size REAL NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    stop_loss REAL NOT NULL,
                    take_profit REAL NOT NULL,
                    pnl REAL,
                    pnl_pct REAL,
                    fee REAL NOT NULL,
                    status TEXT NOT NULL,
                    regime TEXT,
                    phantom_flags TEXT,
                    notes TEXT
                )
            """)
            
            # Daily PnL table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_pnl (
                    date TEXT PRIMARY KEY,
                    pair TEXT NOT NULL,
                    daily_pnl REAL NOT NULL,
                    daily_pnl_pct REAL NOT NULL,
                    trades_count INTEGER NOT NULL,
                    win_rate REAL NOT NULL,
                    max_drawdown REAL NOT NULL,
                    regime TEXT
                )
            """)
            
            # Candles cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS candles (
                    pair TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    PRIMARY KEY (pair, timeframe, timestamp)
                )
            """)
            
            # Indexes for faster queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_pair ON trades(pair)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(entry_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_candles_pair ON candles(pair, timeframe, timestamp)")
            
            conn.commit()
    
    def add_trade(self, trade: TradeRecord) -> int:
        """
        Add a new trade to the database
        
        Args:
            trade: TradeRecord object
            
        Returns:
            ID of the newly created trade
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (
                    pair, signal, entry_price, size, entry_time,
                    stop_loss, take_profit, fee, status, regime, phantom_flags, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.pair, trade.signal, trade.entry_price, trade.size,
                trade.entry_time.isoformat(), trade.stop_loss, trade.take_profit,
                trade.fee, trade.status, trade.regime,
                json.dumps(trade.phantom_flags) if isinstance(trade.phantom_flags, dict) else trade.phantom_flags,
                trade.notes
            ))
            trade_id = cursor.lastrowid
            conn.commit()
            return trade_id
    
    def update_trade(self, trade_id: int, exit_price: float, exit_time: datetime,
                    pnl: float, pnl_pct: float, status: str) -> bool:
        """
        Update trade with exit details
        
        Args:
            trade_id: ID of the trade to update
            exit_price: Price at which trade was exited
            exit_time: Time when trade was exited
            pnl: Profit/Loss from the trade
            pnl_pct: Profit/Loss percentage
            status: New status (CLOSED, BREAKEVEN, FAILED)
            
        Returns:
            True if update was successful
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trades SET
                    exit_price = ?,
                    exit_time = ?,
                    pnl = ?,
                    pnl_pct = ?,
                    status = ?
                WHERE id = ?
            """, (exit_price, exit_time.isoformat(), pnl, pnl_pct, status, trade_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def close_trade(self, trade_id: int, exit_price: float, exit_time: datetime) -> bool:
        """
        Close a trade and calculate PnL
        
        Args:
            trade_id: ID of the trade to close
            exit_price: Price at which trade was exited
            exit_time: Time when trade was exited
            
        Returns:
            True if successful
        """
        trade = self.get_trade(trade_id)
        if not trade or trade.status != "OPEN":
            return False
        
        if trade.signal == "BUY":
            pnl = (exit_price - trade.entry_price) * trade.size - trade.fee
        else:  # SELL
            pnl = (trade.entry_price - exit_price) * trade.size - trade.fee
        
        pnl_pct = (pnl / (trade.entry_price * trade.size)) * 100 if trade.entry_price * trade.size > 0 else 0
        
        return self.update_trade(
            trade_id=trade_id,
            exit_price=exit_price,
            exit_time=exit_time,
            pnl=pnl,
            pnl_pct=pnl_pct,
            status="CLOSED"
        )
    
    def breakeven_trade(self, trade_id: int, breakeven_price: float) -> bool:
        """
        Move stop loss to breakeven
        
        Args:
            trade_id: ID of the trade
            breakeven_price: Price to set as new stop loss
            
        Returns:
            True if successful
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trades SET stop_loss = ? WHERE id = ?
            """, (breakeven_price, trade_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_trade(self, trade_id: int) -> Optional[TradeRecord]:
        """
        Get a trade by ID
        
        Args:
            trade_id: ID of the trade
            
        Returns:
            TradeRecord object or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
            row = cursor.fetchone()
            if row:
                return TradeRecord(
                    id=row["id"],
                    pair=row["pair"],
                    signal=row["signal"],
                    entry_price=row["entry_price"],
                    exit_price=row["exit_price"],
                    size=row["size"],
                    entry_time=datetime.fromisoformat(row["entry_time"]),
                    exit_time=datetime.fromisoformat(row["exit_time"]) if row["exit_time"] else None,
                    stop_loss=row["stop_loss"],
                    take_profit=row["take_profit"],
                    pnl=row["pnl"],
                    pnl_pct=row["pnl_pct"],
                    fee=row["fee"],
                    status=row["status"],
                    regime=row["regime"],
                    phantom_flags=json.loads(row["phantom_flags"]) if row["phantom_flags"] else {},
                    notes=row["notes"]
                )
            return None
    
    def open_trades(self, pair: Optional[str] = None) -> List[TradeRecord]:
        """
        Get all open trades
        
        Args:
            pair: Optional pair filter
            
        Returns:
            List of TradeRecord objects
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = "SELECT * FROM trades WHERE status = 'OPEN'"
            params = []
            if pair:
                query += " AND pair = ?"
                params.append(pair)
            cursor.execute(query, params)
            return [
                TradeRecord(
                    id=row["id"], pair=row["pair"], signal=row["signal"],
                    entry_price=row["entry_price"], exit_price=row["exit_price"],
                    size=row["size"],
                    entry_time=datetime.fromisoformat(row["entry_time"]),
                    exit_time=datetime.fromisoformat(row["exit_time"]) if row["exit_time"] else None,
                    stop_loss=row["stop_loss"], take_profit=row["take_profit"],
                    pnl=row["pnl"], pnl_pct=row["pnl_pct"],
                    fee=row["fee"], status=row["status"],
                    regime=row["regime"],
                    phantom_flags=json.loads(row["phantom_flags"]) if row["phantom_flags"] else {},
                    notes=row["notes"]
                )
                for row in cursor.fetchall()
            ]
    
    def rolling_metrics(self, days: int = 30, pair: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculate rolling metrics (win rate, avg PnL, etc.)
        
        Args:
            days: Number of days to look back
            pair: Optional pair filter
            
        Returns:
            Dictionary with trading metrics
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) as total_winning_pnl,
                    SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END) as total_losing_pnl,
                    MIN(pnl) as worst_trade,
                    MAX(pnl) as best_trade
                FROM trades
                WHERE status = 'CLOSED'
                AND exit_time >= datetime('now', ?)
            """
            params = [f"-{days} days"]
            
            if pair:
                query += " AND pair = ?"
                params.append(pair)
            
            cursor.execute(query, params)
            row = cursor.fetchone()
            
            if not row or row["total_trades"] == 0:
                return {
                    "total_trades": 0, "win_rate": 0.0, "profit_factor": 0.0,
                    "avg_pnl": 0.0, "total_pnl": 0.0, "max_drawdown": 0.0,
                    "worst_trade": 0.0, "best_trade": 0.0
                }
            
            win_rate = row["winning_trades"] / row["total_trades"]
            profit_factor = abs(row["total_winning_pnl"] / row["total_losing_pnl"]) if row["total_losing_pnl"] < 0 else 0
            
            return {
                "total_trades": row["total_trades"],
                "winning_trades": row["winning_trades"],
                "losing_trades": row["losing_trades"],
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "avg_pnl": row["avg_pnl"],
                "total_pnl": row["total_pnl"],
                "worst_trade": row["worst_trade"],
                "best_trade": row["best_trade"]
            }
    
    def loss_streak(self, pair: Optional[str] = None) -> int:
        """
        Get current loss streak count
        
        Args:
            pair: Optional pair filter
            
        Returns:
            Number of consecutive losing trades
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = """
                SELECT pnl FROM trades
                WHERE status = 'CLOSED'
            """
            params = []
            if pair:
                query += " AND pair = ?"
                params.append(pair)
            query += " ORDER BY exit_time DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            streak = 0
            for row in rows:
                if row["pnl"] < 0:
                    streak += 1
                else:
                    break
            return streak
    
    def recent_trades(self, limit: int = 50) -> List[TradeRecord]:
        """
        Get most recent closed trades
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of recent trade records
        """
        trades = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades
                WHERE status = 'CLOSED'
                ORDER BY exit_time DESC
                LIMIT ?
            """, (limit,))
            for row in cursor.fetchall():
                try:
                    trades.append(TradeRecord(
                        id=row["id"], pair=row["pair"],
                        signal=row["signal"], entry_price=row["entry_price"],
                        exit_price=row["exit_price"], size=row["size"],
                        entry_time=datetime.fromisoformat(row["entry_time"]),
                        exit_time=datetime.fromisoformat(row["exit_time"]) if row["exit_time"] else None,
                        stop_loss=row["stop_loss"], take_profit=row["take_profit"],
                        fee=row["fee"], status=row["status"],
                        regime=row["regime"], phantom_flags=row["phantom_flags"],
                        notes=row["notes"], pnl=row["pnl"],
                        pnl_pct=row["pnl_pct"]
                    ))
                except Exception:
                    continue
        return trades
    
    def total_pnl(self, pair: Optional[str] = None) -> float:
        """
        Get total PnL for all closed trades
        
        Args:
            pair: Optional pair filter
            
        Returns:
            Total PnL in IDR
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = "SELECT SUM(pnl) as total FROM trades WHERE status = 'CLOSED'"
            params = []
            if pair:
                query += " AND pair = ?"
                params.append(pair)
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0.0
    
    def add_candle(self, pair: str, timeframe: str, candle: Dict[str, Any]) -> bool:
        """
        Add candle data to cache
        
        Args:
            pair: Trading pair (e.g., BTC_IDR)
            timeframe: Timeframe (e.g., 1h)
            candle: Dictionary with candle data
            
        Returns:
            True if successful
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO candles (
                        pair, timeframe, timestamp, open, high, low, close, volume
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pair, timeframe,
                    candle["timestamp"].isoformat() if hasattr(candle["timestamp"], "isoformat") else candle["timestamp"],
                    candle["open"], candle["high"], candle["low"],
                    candle["close"], candle["volume"]
                ))
                conn.commit()
                return True
            except Exception as e:
                print(f"Error adding candle: {e}")
                return False
    
    def get_candles(self, pair: str, timeframe: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get historical candles
        
        Args:
            pair: Trading pair
            timeframe: Timeframe
            limit: Maximum number of candles to return
            
        Returns:
            List of candle dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM candles
                WHERE pair = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (pair, timeframe, limit))
            return [
                {
                    "pair": row["pair"],
                    "timeframe": row["timeframe"],
                    "timestamp": datetime.fromisoformat(row["timestamp"]),
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row["volume"]
                }
                for row in cursor.fetchall()
            ]
