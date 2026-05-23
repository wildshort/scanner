"""
Price alert management with Telegram notifications.
Alerts are stored in alerts.json next to this file.
"""
from __future__ import annotations
import json, logging, os
from pathlib import Path

logger = logging.getLogger(__name__)
ALERTS_FILE = Path(__file__).parent / "alerts.json"


def _load() -> list[dict]:
    try:
        return json.loads(ALERTS_FILE.read_text()) if ALERTS_FILE.exists() else []
    except Exception:
        return []


def _save(alerts: list[dict]):
    ALERTS_FILE.write_text(json.dumps(alerts, indent=2))


def get_alerts() -> list[dict]:
    return _load()


def add_alert(symbol: str, price: float, condition: str, note: str = "") -> dict:
    alerts = _load()
    new_id = max((a["id"] for a in alerts), default=0) + 1
    alert = {
        "id": new_id, "symbol": symbol.upper(),
        "price": round(float(price), 2), "condition": condition,
        "note": note, "triggered": False,
    }
    alerts.append(alert)
    _save(alerts)
    return alert


def delete_alert(alert_id: int) -> bool:
    alerts = _load()
    updated = [a for a in alerts if a["id"] != alert_id]
    if len(updated) < len(alerts):
        _save(updated)
        return True
    return False


def check_alerts(scan_results: list[dict]) -> list[dict]:
    """Compare live prices against saved alerts; fire Telegram on hit."""
    alerts = _load()
    prices = {r["symbol"]: r["price"] for r in scan_results}
    triggered, changed = [], False

    for a in alerts:
        if a.get("triggered"):
            continue
        cur = prices.get(a["symbol"])
        if cur is None:
            continue
        hit = (a["condition"] == "above" and cur >= a["price"]) or \
              (a["condition"] == "below" and cur <= a["price"])
        if hit:
            a["triggered"] = True
            a["trigger_price"] = cur
            triggered.append(a)
            changed = True
            _send_telegram(a, cur)

    if changed:
        _save(alerts)
    return triggered


def _send_telegram(alert: dict, cur_price: float):
    try:
        import requests
        token = os.getenv("TELEGRAM_TOKEN")
        chat  = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat:
            return
        arrow = "🚀" if alert["condition"] == "above" else "🔻"
        text  = (f"{arrow} *Price Alert Triggered*\n"
                 f"*{alert['symbol']}* crossed {alert['condition']} ₹{alert['price']:.2f}\n"
                 f"Current price: ₹{cur_price:.2f}"
                 + (f"\n_{alert['note']}_" if alert.get("note") else ""))
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "parse_mode": "Markdown"},
            timeout=5,
        )
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")
