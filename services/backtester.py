import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from collections import OrderedDict

from storage.database import TradeStore, TradeRecord
from core.sentiment import Sentiment
from core.phantom_detector import PhantomDetector, PhantomFlags
from core.adaptive_engine import AdaptiveEngine
from core.risk_manager import RiskManager, RiskCheckResult, PositionSizeResult
from core.exit_manager import ExitManager, ExitSignal
TIMEFRAME_SECONDS = {
    "1m": 60, "5m": 300, "15m": 900, "30m": 1800,
    "1h": 3600, "2h": 7200, "4h": 14400,
    "1d": 86400
}


class BacktestTrade:
    __slots__ = (
        "id", "pair", "signal", "entry_price", "exit_price",
        "size", "entry_time", "exit_time",
        "stop_loss", "take_profit", "pnl", "pnl_pct",
        "fee", "regime", "composite_score", "exit_reason",
        "entry_candle_idx"
    )

    def __init__(self, pair: str, signal: str, entry_price: float, size: float,
                 entry_time: datetime, stop_loss: float, take_profit: float,
                 fee: float, regime: str, composite_score: float,
                 entry_candle_idx: int = 0):
        self.id = 0
        self.pair = pair
        self.signal = signal
        self.entry_price = entry_price
        self.exit_price = 0.0
        self.size = size
        self.entry_time = entry_time
        self.exit_time = None
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.pnl = 0.0
        self.pnl_pct = 0.0
        self.fee = fee
        self.regime = regime
        self.composite_score = composite_score
        self.exit_reason = ""
        self.entry_candle_idx = entry_candle_idx


class Backtester:
    TIMEFRAME_ORDER = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"]
    WARMUP_CANDLES = 60

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pairs = config.get("pairs", [])
        self.timeframe = config.get("timeframe", "1h")
        self.initial_balance = float(config.get("initial_balance", 10_000_000))
        self.start_date = config.get("start_date")
        self.end_date = config.get("end_date")
        self.fee_pct = config.get("exchange", {}).get("fee_pct", 0.002)

        self._init_exchange()
        self._init_components()
        self._init_portfolio()

    def _init_exchange(self):
        import ccxt
        self._exchange = ccxt.indodax({
            "enableRateLimit": True,
            "rateLimit": 100,
        })

    def _init_components(self):
        self.phantom_detector = PhantomDetector(self.config)
        self.adaptive_engine = AdaptiveEngine(self.config)
        self.exit_manager = ExitManager(self.config, TradeStore(":memory:"))

    def _init_portfolio(self):
        self.balance = self.initial_balance
        self.peak_balance = self.initial_balance
        self.positions: Dict[str, "BacktestTrade"] = OrderedDict()
        self.trades: List["BacktestTrade"] = []
        self.trade_counter = 0
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.cycle_count = 0
        self.last_trade_time: Dict[str, datetime] = {}
        self.consecutive_losses: int = 0
        self.daily_pnl: Dict[str, float] = {}
        self.current_drawdown: float = 0.0
        self.balance_history: List[Tuple[datetime, float]] = []

    def _to_market_symbol(self, pair: str) -> str:
        return pair.replace("_", "/") if "_" in pair else pair

    def fetch_historical(self, pair: str) -> List[Dict[str, Any]]:
        import ccxt
        symbol = self._to_market_symbol(pair)
        start_dt = datetime.strptime(self.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(self.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        warmup_start = start_dt - timedelta(seconds=self.WARMUP_CANDLES * TIMEFRAME_SECONDS[self.timeframe])

        since = int(warmup_start.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)
        timeframe_sec = TIMEFRAME_SECONDS[self.timeframe]
        batch_limit = 1000
        all_candles = []

        print(f"  Fetching {pair} from {warmup_start.date()} to {end_dt.date()}...")
        while since < end_ms:
            try:
                raw = self._exchange.fetch_ohlcv(symbol, self.timeframe, since, batch_limit)
                if not raw:
                    break
                all_candles.extend(raw)
                since = raw[-1][0] + timeframe_sec * 1000
                time.sleep(0.3)
            except ccxt.NetworkError:
                print("  Network error, retrying in 3s...")
                time.sleep(3)
            except ccxt.RateLimitExceeded:
                print("  Rate limit hit, waiting 10s...")
                time.sleep(10)

        result = []
        for c in all_candles:
            ts = datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc)
            result.append({
                "timestamp": ts,
                "open": c[1], "high": c[2], "low": c[3],
                "close": c[4], "volume": c[5]
            })

        result.sort(key=lambda x: x["timestamp"])
        deduped = list(OrderedDict((c["timestamp"], c) for c in result).values())
        print(f"    Got {len(deduped)} candles ({len(deduped) - len(result) + len(result)} unique)")
        return deduped

    def _candles_to_df(self, candles):
        import pandas as pd
        df = pd.DataFrame(candles)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)
        return df

    def _check_exit(self, position: BacktestTrade, candle: Dict[str, Any],
                    atr_14: float, candle_idx: int, entry_candle_idx: int) -> Optional[ExitSignal]:
        o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]
        ts = candle["timestamp"]

        if position.signal in ("BUY", "STRONG_BUY"):
            if l <= position.stop_loss:
                return ExitSignal(position.pair, position.id, "CLOSE", position.stop_loss, "Stop Loss")
            if h >= position.take_profit:
                return ExitSignal(position.pair, position.id, "CLOSE", position.take_profit, "Take Profit")
        else:
            if h >= position.stop_loss:
                return ExitSignal(position.pair, position.id, "CLOSE", position.stop_loss, "Stop Loss")
            if l <= position.take_profit:
                return ExitSignal(position.pair, position.id, "CLOSE", position.take_profit, "Take Profit")

        # Breakeven — only after at least 6 candles and price moved > 1.5x SL distance
        candles_since_entry = candle_idx - entry_candle_idx
        if candles_since_entry >= 6:
            stop_loss_pct = self.config.get("stop_loss_pct", 0.05)
            min_profit_move = stop_loss_pct * 1.5
            if position.signal in ("BUY", "STRONG_BUY"):
                be = position.entry_price * (1 + position.fee / (position.entry_price * position.size))
                if c >= position.entry_price * (1 + min_profit_move) and position.stop_loss < be:
                    position.stop_loss = be
            else:
                be = position.entry_price * (1 - position.fee / (position.entry_price * position.size))
                if c <= position.entry_price * (1 - min_profit_move) and position.stop_loss > be:
                    position.stop_loss = be

        # Time stop (48h for backtest)
        if (ts - position.entry_time) > timedelta(hours=48):
            return ExitSignal(position.pair, position.id, "CLOSE", c, "Time Stop")

        return None

    def _close_position(self, position: BacktestTrade, exit_price: float,
                        reason: str, candle_time: datetime):
        if position.signal in ("BUY", "STRONG_BUY"):
            pnl = (exit_price - position.entry_price) * position.size - position.fee
        else:
            pnl = (position.entry_price - exit_price) * position.size - position.fee

        cost = position.entry_price * position.size
        pnl_pct = (pnl / cost) * 100 if cost > 0 else 0

        position.exit_price = exit_price
        position.exit_time = candle_time
        position.pnl = pnl
        position.pnl_pct = pnl_pct
        position.exit_reason = reason
        self.trades.append(position)

        self.balance += (position.size * exit_price) - position.fee
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        self.peak_balance = max(self.peak_balance, self.balance)
        self.current_drawdown = (self.peak_balance - self.balance) / self.peak_balance if self.peak_balance > 0 else 0

        date_key = candle_time.date().isoformat()
        self.daily_pnl[date_key] = self.daily_pnl.get(date_key, 0.0) + pnl

        direction = "LONG" if position.signal in ("BUY", "STRONG_BUY") else "SHORT"
        print(f"  {'✅' if pnl > 0 else '❌'} {position.pair} {direction} | "
              f"Entry: {position.entry_price:.0f} Exit: {exit_price:.0f} | "
              f"PnL: {pnl:+,.0f} ({pnl_pct:+.2f}%) | {reason}")

        del self.positions[position.pair]

    def _check_entry(self, pair: str, indicators, signal_data: Dict[str, Any],
                     current_price: float, phantom_flags: PhantomFlags,
                     phantom_penalty: float, regime: str, candle_time: datetime,
                     candle_idx: int = 0):

        if pair in self.positions:
            return

        signal = signal_data["signal"]
        if signal not in ("BUY", "STRONG_BUY", "SELL", "STRONG_SELL"):
            return

        # Max positions check
        if len(self.positions) >= self.config.get("risk_parameters", {}).get("max_positions", 3):
            return

        # Min balance check
        min_balance = 100_000
        if self.balance < min_balance:
            return

        # Max loss streak check (cooldown is not candle-aware, skip for backtest)
        max_loss_streak = self.config.get("risk_parameters", {}).get("max_loss_streak", 3)
        if self.consecutive_losses >= max_loss_streak:
            return

        stop_loss_pct = self.config.get("stop_loss_pct", 0.05)
        take_profit_r = self.config.get("take_profit_r", 2.0)

        if signal in ("BUY", "STRONG_BUY"):
            stop_loss = current_price * (1 - stop_loss_pct)
            take_profit = current_price * (1 + stop_loss_pct * take_profit_r)
        else:
            stop_loss = current_price * (1 + stop_loss_pct)
            take_profit = current_price * (1 - stop_loss_pct * take_profit_r)

        if stop_loss <= 0 or current_price <= 0:
            return

        # Position sizing (simplified for backtest)
        regime_multipliers = self.config.get("risk_parameters", {}).get("regime_multipliers", {})
        position_multiplier = regime_multipliers.get(regime, 1.0)
        signal_multiplier = 0.5 + (signal_data["composite_score"] / 100.0)
        phantom_multiplier = 1.0 - phantom_penalty
        dd_multiplier = 1.0 - (self.current_drawdown * 2)

        kelly = self.config.get("risk_parameters", {}).get("kelly_fraction", 0.5)
        win_prob, win_loss = 0.6, 2.0
        base_size_idr = self.balance * kelly * (win_prob - (1 - win_prob) / win_loss)
        adjusted_idr = base_size_idr * position_multiplier * signal_multiplier * phantom_multiplier * dd_multiplier

        stop_loss_pct_actual = abs((current_price - stop_loss) / current_price)
        max_risk = self.balance * 0.02
        max_size_idr = max_risk / stop_loss_pct_actual if stop_loss_pct_actual > 0 else 0
        final_idr = min(adjusted_idr, max_size_idr)
        size = final_idr / current_price

        min_order = self.config.get("exchange", {}).get("min_order_size", 0.0001)
        if size < min_order or final_idr > self.balance * 0.9:
            return

        fee = final_idr * self.fee_pct

        trade = BacktestTrade(
            pair=pair, signal=signal, entry_price=current_price,
            size=size, entry_time=candle_time, stop_loss=stop_loss,
            take_profit=take_profit, fee=fee, regime=regime,
            composite_score=signal_data["composite_score"],
            entry_candle_idx=candle_idx
        )
        self.trade_counter += 1
        trade.id = self.trade_counter

        self.balance -= final_idr
        self.positions[pair] = trade
        self.last_trade_time[pair] = candle_time

        direction = "LONG" if signal in ("BUY", "STRONG_BUY") else "SHORT"
        print(f"  📝 {pair} {direction} @ {current_price:,.0f} | "
              f"Size: {size:.4f} | Score: {signal_data['composite_score']:.1f} | Regime: {regime}")

    def run(self):
        from main import Indicators

        print(f"\n{'='*70}")
        print(f"📊 BACKTEST: {', '.join(self.pairs)} | {self.timeframe}")
        print(f"   Period: {self.start_date} → {self.end_date}")
        print(f"   Balance: IDR {self.initial_balance:,.0f}")
        print(f"{'='*70}\n")

        all_results = {}

        for pair in self.pairs:
            print(f"\n{'─'*50}")
            print(f"Pair: {pair}")
            print(f"{'─'*50}")

            candles = self.fetch_historical(pair)
            if len(candles) < self.WARMUP_CANDLES + 10:
                print(f"  ⚠️  Insufficient data ({len(candles)} candles), skipping")
                all_results[pair] = {"trades": 0, "error": "insufficient_data"}
                continue

            indicators = Indicators(self.config)
            market_pair_config = {**self.config, "pairs": [pair]}
            phantom = PhantomDetector(market_pair_config)
            adaptive = AdaptiveEngine(market_pair_config)
            sentiment = Sentiment()

            self._init_portfolio()
            self.phantom_detector = phantom
            self.adaptive_engine = adaptive

            warmup_end = self.WARMUP_CANDLES

            for i in range(warmup_end, len(candles)):
                self.cycle_count += 1
                candle = candles[i]
                window = candles[i - self.WARMUP_CANDLES + 1:i + 1]

                # Exit checks
                for pos_pair in list(self.positions.keys()):
                    pos = self.positions[pos_pair]
                    atr = 0.0
                    try:
                        df = self._candles_to_df(window)
                        import talib
                        highs = df["high"].values
                        lows = df["low"].values
                        closes = df["close"].values
                        atr = talib.ATR(highs, lows, closes, timeperiod=14)[-1]
                    except Exception:
                        pass

                    exit_signal = self._check_exit(pos, candle, atr, i, pos.entry_candle_idx)
                    if exit_signal:
                        self._close_position(pos, exit_signal.price, exit_signal.reason, candle["timestamp"])

                # Entry scan
                if pair in self.positions:
                    continue

                try:
                    df = self._candles_to_df(window)
                    ind = indicators.calculate(df)
                    if not ind:
                        continue

                    sent_score = sentiment.score()

                    regime = adaptive.detect_regime(ind.adx, ind.dmp_plus, ind.dmp_minus)
                    adaptive.update_regime(regime)

                    for cv in window[-5:]:
                        phantom.update(pair, cv)
                    flags = phantom.detect(pair)
                    penalty = phantom.penalty_factor(flags)

                    signal_data = indicators.signal_score(ind, sent_score, regime)

                    self._check_entry(
                        pair=pair, indicators=ind, signal_data=signal_data,
                        current_price=candle["close"], phantom_flags=flags,
                        phantom_penalty=penalty, regime=regime,
                        candle_time=candle["timestamp"],
                        candle_idx=i
                    )
                except Exception as e:
                    pass

            # Close any remaining open positions at last price
            for pos_pair in list(self.positions.keys()):
                pos = self.positions[pos_pair]
                last_candle = candles[-1]
                self._close_position(pos, last_candle["close"], "End of Backtest", last_candle["timestamp"])

            all_results[pair] = self._pair_summary(pair)
            self._print_pair_summary(pair, all_results[pair])

        self._print_combined_summary(all_results)
        return all_results

    def _pair_summary(self, pair: str) -> Dict[str, Any]:
        pair_trades = [t for t in self.trades if t.pair == pair]
        if not pair_trades:
            return {"trades": 0}

        wins = [t for t in pair_trades if t.pnl > 0]
        losses = [t for t in pair_trades if t.pnl <= 0]
        total_pnl = sum(t.pnl for t in pair_trades)
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = sum(t.pnl for t in losses)
        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else float("inf")
        win_rate = len(wins) / len(pair_trades) if pair_trades else 0
        avg_win = gross_profit / len(wins) if wins else 0
        avg_loss = gross_loss / len(losses) if losses else 0

        # Max consecutive wins/losses
        max_cw = max_cl = cw = cl = 0
        for t in pair_trades:
            if t.pnl > 0:
                cw += 1; cl = 0; max_cw = max(max_cw, cw)
            else:
                cl += 1; cw = 0; max_cl = max(max_cl, cl)

        # Sharpe ratio (daily returns)
        daily_returns = []
        current_date = None
        daily_sum = 0.0
        for t in pair_trades:
            d = t.exit_time.date().isoformat()
            if current_date is None:
                current_date = d
            if d != current_date:
                daily_returns.append(daily_sum / self.initial_balance)
                current_date = d
                daily_sum = 0.0
            daily_sum += t.pnl
        if daily_sum != 0:
            daily_returns.append(daily_sum / self.initial_balance)

        sharpe = 0.0
        if daily_returns:
            import statistics
            mean_r = statistics.mean(daily_returns) if daily_returns else 0
            std_r = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0.001
            sharpe = (mean_r / std_r) * math.sqrt(365) if std_r > 0 else 0

        return {
            "trades": len(pair_trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "total_pnl_pct": (total_pnl / self.initial_balance) * 100,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "largest_win": max((t.pnl for t in wins), default=0),
            "largest_loss": min((t.pnl for t in losses), default=0),
            "max_consecutive_wins": max_cw,
            "max_consecutive_losses": max_cl,
            "sharpe_ratio": sharpe,
            "max_drawdown": self.current_drawdown * 100,
            "final_balance": self.balance,
        }

    def _print_pair_summary(self, pair: str, s: Dict[str, Any]):
        if s["trades"] == 0:
            return
        profit_factor_str = "∞" if s["profit_factor"] == float("inf") else f"{s['profit_factor']:.2f}"
        print(f"\n  📊 {pair} Results:")
        print(f"     Trades: {s['trades']} ({s['wins']}W / {s['losses']}L) | Win Rate: {s['win_rate']:.1%}")
        print(f"     Net PnL: IDR {s['total_pnl']:+,.0f} ({s['total_pnl_pct']:+.2f}%)")
        print(f"     Profit Factor: {profit_factor_str}")
        print(f"     Avg Win: IDR {s['avg_win']:+,.0f} | Avg Loss: IDR {s['avg_loss']:+,.0f}")
        print(f"     Largest Win: IDR {s['largest_win']:+,.0f} | Largest Loss: IDR {s['largest_loss']:+,.0f}")
        print(f"     Max DD: {s['max_drawdown']:.2f}% | Sharpe: {s['sharpe_ratio']:.2f}")
        print(f"     Final Balance: IDR {s['final_balance']:,.0f}")

    def _print_combined_summary(self, results: Dict[str, Any]):
        print(f"\n{'='*70}")
        print(f"📈 BACKTEST SUMMARY")
        print(f"{'='*70}")

        total_trades = sum(r.get("trades", 0) for r in results.values())
        if total_trades == 0:
            print("\n  No trades were executed during the backtest period.")
            print("  Possible reasons:")
            print("  - Insufficient data for indicator calculations")
            print("  - Signal scores didn't meet entry thresholds")
            print("  - Risk guards blocked all entries\n")
            return

        all_trades = sorted(self.trades, key=lambda t: t.entry_time)
        total_pnl = sum(t.pnl for t in all_trades)
        start = all_trades[0].entry_time if all_trades else ""
        end = all_trades[-1].exit_time if all_trades else ""

        wins = [t for t in all_trades if t.pnl > 0]
        losses = [t for t in all_trades if t.pnl <= 0]
        win_rate = len(wins) / len(all_trades) if all_trades else 0

        total_pnl_pct = (total_pnl / self.initial_balance) * 100

        # Trade list
        print(f"\n  {'ID':<4} {'Pair':<10} {'Direction':<8} {'Entry':<14} {'Exit':<14} {'PnL':<14} {'Reason':<20}")
        print(f"  {'─'*84}")
        for t in all_trades:
            direction = "LONG" if t.signal in ("BUY", "STRONG_BUY") else "SHORT"
            entry_str = f"{t.entry_price:,.0f}"
            exit_str = f"{t.exit_price:,.0f}" if t.exit_price else "—"
            pnl_str = f"{t.pnl:+,.0f}"
            print(f"  {t.id:<4} {t.pair:<10} {direction:<8} {entry_str:<14} {exit_str:<14} {pnl_str:<14} {t.exit_reason:<20}")

        print(f"\n  {'─'*84}")
        print(f"  {'TOTAL':<38} {total_pnl:+,.0f} IDR ({total_pnl_pct:+.2f}%)")

        # Summary table
        avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0
        gross_profit = sum(t.pnl for t in wins)
        gross_loss = sum(t.pnl for t in losses)
        pf = abs(gross_profit / gross_loss) if gross_loss != 0 else float("inf")

        print(f"\n  {'Metric':<35} {'Value':<15}")
        print(f"  {'─'*50}")
        print(f"  {'Total Trades':<35} {total_trades:<15}")
        print(f"  {'Winning / Losing':<35} {len(wins)} / {len(losses)}")
        print(f"  {'Win Rate':<35} {win_rate:.1%}")
        print(f"  {'Total Return':<35} IDR {total_pnl:+,.0f} ({total_pnl_pct:+.2f}%)")
        print(f"  {'Profit Factor':<35} {'∞' if pf == float('inf') else f'{pf:.2f}'}")
        print(f"  {'Average Win':<35} IDR {avg_win:+,.0f}")
        print(f"  {'Average Loss':<35} IDR {avg_loss:+,.0f}")
        print(f"  {'Largest Win':<35} IDR {max((t.pnl for t in wins), default=0):+,.0f}")
        print(f"  {'Largest Loss':<35} IDR {min((t.pnl for t in losses), default=0):+,.0f}")

        # Max drawdown calculation
        running_peak = self.initial_balance
        max_dd = 0.0
        running_balance = self.initial_balance
        for t in all_trades:
            running_balance += t.pnl
            running_peak = max(running_peak, running_balance)
            dd = (running_peak - running_balance) / running_peak
            max_dd = max(max_dd, dd)

        print(f"  {'Max Drawdown':<35} {max_dd:.2%}")

        # Sharpe
        daily_returns = {}
        for t in all_trades:
            d = t.exit_time.date().isoformat()
            daily_returns[d] = daily_returns.get(d, 0.0) + t.pnl
        dr_list = [v / self.initial_balance for v in daily_returns.values()]
        if dr_list:
            import statistics
            mean_r = statistics.mean(dr_list)
            std_r = statistics.stdev(dr_list) if len(dr_list) > 1 else 0.001
            sharpe = (mean_r / std_r) * math.sqrt(365) if std_r > 0 else 0
            print(f"  {'Sharpe Ratio':<35} {sharpe:.2f}")

        # Calmar ratio
        if max_dd > 0:
            calmar = (total_pnl / self.initial_balance) / max_dd if max_dd > 0 else 0
            print(f"  {'Calmar Ratio':<35} {calmar:.2f}")

        best_trade = max(all_trades, key=lambda t: t.pnl_pct)
        worst_trade = min(all_trades, key=lambda t: t.pnl_pct)
        print(f"  {'Best Trade':<35} {best_trade.pnl_pct:+.2f}% ({best_trade.pair})")
        print(f"  {'Worst Trade':<35} {worst_trade.pnl_pct:+.2f}% ({worst_trade.pair})")

        print(f"{'='*70}\n")

        # Save output if requested
        output_path = self.config.get("output")
        if output_path:
            self._save_results(all_trades, results, output_path)

    def _save_results(self, all_trades: List["BacktestTrade"], results: Dict[str, Any],
                      output_path: str):
        ext = os.path.splitext(output_path)[1].lower()
        if ext == ".html":
            self._save_html_report(all_trades, results, output_path)
        elif ext == ".csv":
            import csv
            with open(output_path, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["id", "pair", "direction", "entry_price", "exit_price",
                           "size", "entry_time", "exit_time", "pnl", "pnl_pct",
                           "reason", "regime", "score"])
                for t in all_trades:
                    direction = "LONG" if t.signal in ("BUY", "STRONG_BUY") else "SHORT"
                    w.writerow([
                        t.id, t.pair, direction, t.entry_price, t.exit_price,
                        t.size, t.entry_time.isoformat(), t.exit_time.isoformat() if t.exit_time else "",
                        t.pnl, t.pnl_pct, t.exit_reason, t.regime, t.composite_score
                    ])
            print(f"\n  💾 Results saved to {output_path}")
        elif ext == ".json":
            data = {
                "summary": {
                    "total_trades": len(all_trades),
                    "total_pnl": sum(t.pnl for t in all_trades),
                    "win_rate": len([t for t in all_trades if t.pnl > 0]) / len(all_trades) if all_trades else 0,
                },
                "trades": [
                    {
                        "id": t.id, "pair": t.pair,
                        "direction": "LONG" if t.signal in ("BUY", "STRONG_BUY") else "SHORT",
                        "entry_price": t.entry_price, "exit_price": t.exit_price,
                        "size": t.size, "entry_time": t.entry_time.isoformat(),
                        "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                        "pnl": t.pnl, "pnl_pct": t.pnl_pct,
                        "reason": t.exit_reason, "regime": t.regime, "score": t.composite_score
                    }
                    for t in all_trades
                ],
                "pair_results": results
            }
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            print(f"\n  💾 Results saved to {output_path}")

    def _save_html_report(self, all_trades, results, output_path):
        total_pnl = sum(t.pnl for t in all_trades)
        wins = [t for t in all_trades if t.pnl > 0]
        losses = [t for t in all_trades if t.pnl <= 0]
        win_rate = len(wins) / len(all_trades) if all_trades else 0
        initial = self.initial_balance
        final = self.balance

        equity_points = [initial]
        timestamps = ["Start"]
        running = initial
        for t in sorted(all_trades, key=lambda x: x.entry_time):
            running += t.pnl
            equity_points.append(round(running, 2))
            ts = t.entry_time.strftime("%m-%d %H:%M") if hasattr(t.entry_time, 'strftime') else str(t.entry_time)
            timestamps.append(ts)

        rows = ""
        for i, t in enumerate(all_trades):
            direction = "LONG" if t.signal in ("BUY", "STRONG_BUY") else "SHORT"
            cls = "win" if t.pnl > 0 else "loss"
            pnl_str = f"+{t.pnl:,.0f}" if t.pnl > 0 else f"{t.pnl:,.0f}"
            rows += f"""<tr class="{cls}">
                <td>{i+1}</td><td>{t.pair}</td><td>{direction}</td>
                <td>{t.entry_price:,.0f}</td><td>{t.exit_price:,.0f}</td>
                <td>{pnl_str}</td><td>{t.pnl_pct:+.2f}%</td>
                <td>{t.exit_reason}</td>
            </tr>\n"""

        avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0

        html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Backtest Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,system-ui,sans-serif; background:#0f172a; color:#e2e8f0; padding:2rem; }}
h1 {{ color:#38bdf8; margin-bottom:0.5rem; }}
.metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:1rem; margin:1.5rem 0; }}
.card {{ background:#1e293b; padding:1.25rem; border-radius:12px; text-align:center; }}
.card .label {{ font-size:0.75rem; text-transform:uppercase; color:#94a3b8; }}
.card .value {{ font-size:1.5rem; font-weight:700; color:#f1f5f9; }}
.card .value.green {{ color:#4ade80; }}
.card .value.red {{ color:#f87171; }}
.chart-container {{ background:#1e293b; padding:1.5rem; border-radius:12px; margin:1.5rem 0; }}
table {{ width:100%; border-collapse:collapse; font-size:0.875rem; }}
th {{ background:#1e293b; color:#94a3b8; text-align:left; padding:0.75rem; position:sticky; top:0; }}
td {{ padding:0.5rem 0.75rem; border-bottom:1px solid #334155; }}
tr.win td:nth-child(6) {{ color:#4ade80; }}
tr.loss td:nth-child(6) {{ color:#f87171; }}
tr:hover {{ background:#1e293b; }}
</style></head>
<body>
<h1>Backtest Report</h1>
<p style="color:#94a3b8;">{self.start_date} \u2192 {self.end_date} \u00b7 {', '.join(self.pairs)} \u00b7 {self.timeframe}</p>

<div class="metrics">
    <div class="card"><div class="label">Total Trades</div><div class="value">{len(all_trades)}</div></div>
    <div class="card"><div class="label">Win Rate</div><div class="value{' green' if win_rate>=0.5 else ' red'}">{win_rate:.1%}</div></div>
    <div class="card"><div class="label">Total Return</div><div class="value{' green' if total_pnl>=0 else ' red'}">{total_pnl:+,.0f} ({((final-initial)/initial*100):+.2f}%)</div></div>
    <div class="card"><div class="label">Final Balance</div><div class="value">{final:,.0f}</div></div>
    <div class="card"><div class="label">Avg Win</div><div class="value green">{avg_win:+,.0f}</div></div>
    <div class="card"><div class="label">Avg Loss</div><div class="value red">{avg_loss:+,.0f}</div></div>
</div>

<div class="chart-container">
    <canvas id="equityChart" height="80"></canvas>
</div>

<div style="overflow-x:auto;">
    <table><thead><tr><th>#</th><th>Pair</th><th>Dir</th><th>Entry</th><th>Exit</th><th>PnL</th><th>%</th><th>Reason</th></tr></thead>
    <tbody>{rows}</tbody></table>
</div>

<script>
new Chart(document.getElementById('equityChart'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(timestamps)},
        datasets: [{{
            label: 'Equity',
            data: {json.dumps(equity_points)},
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56,189,248,0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 0
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ ticks: {{ maxTicksLimit: 10, color: '#94a3b8' }}, grid: {{ color: '#1e293b' }} }},
            y: {{ ticks: {{ color: '#94a3b8' }}, grid: {{ color: '#1e293b' }} }}
        }}
    }}
}});
</script>
</body></html>"""
        with open(output_path, "w") as f:
            f.write(html)
        print(f"\n  HTML report saved to {output_path}")
