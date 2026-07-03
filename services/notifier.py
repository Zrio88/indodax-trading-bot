import urllib.request
import urllib.parse
import json


class TelegramNotifier:
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)

    def send(self, message: str) -> bool:
        if not self.enabled:
            return False
        try:
            data = urllib.parse.urlencode({
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }).encode()
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            req = urllib.request.Request(url, data=data, method="POST")
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.status == 200
        except Exception as e:
            print(f"Telegram send error: {e}")
            return False

    def send_trade(self, pair: str, action: str, price: float, size: float,
                   pnl: float = None, reason: str = None) -> bool:
        if action in ("BUY", "STRONG_BUY", "SELL", "STRONG_SELL"):
            emoji = "\U0001f4e1" if "BUY" in action else "\U0001f4e2"
            msg = (
                f"{emoji} <b>TRADE ENTRY</b>\n"
                f"Pair: {pair}\n"
                f"Signal: {action}\n"
                f"Price: {price:,.0f}\n"
                f"Size: {size:.4f}"
            )
        else:
            emoji = "\U00002705" if pnl and pnl > 0 else "\U0000274c"
            direction = reason or "EXIT"
            msg = (
                f"{emoji} <b>TRADE EXIT</b>\n"
                f"Pair: {pair}\n"
                f"Exit Price: {price:,.0f}\n"
                f"PnL: {pnl:+,.0f} ({((pnl or 0)/(price*size or 1)*100):+.2f}%)\n"
                f"Reason: {direction}"
            )
        return self.send(msg)

    def send_alert(self, message: str) -> bool:
        return self.send(f"\u26a0\ufe0f <b>ALERT</b>\n{message}")

    def send_startup(self, mode: str, pairs: list, balance: float) -> bool:
        return self.send(
            f"\U0001f680 <b>BOT STARTED</b>\n"
            f"Mode: {mode}\n"
            f"Pairs: {', '.join(pairs)}\n"
            f"Balance: IDR {balance:,.0f}"
        )

    def send_shutdown(self, trades: int, pnl: float, uptime: str) -> bool:
        return self.send(
            f"\U0001f534 <b>BOT SHUTDOWN</b>\n"
            f"Trades: {trades}\n"
            f"PnL: {pnl:+,.0f}\n"
            f"Uptime: {uptime}"
        )
