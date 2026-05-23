"""
Data client: Yahoo Finance (EOD) only.
No Kite Connect dependency — safe to run without any API credentials.
"""
import datetime
import logging
import pandas as pd

logger = logging.getLogger(__name__)

_INTERVAL_CFG = {
    "5m":  ("5m",   "5d",   None),
    "10m": ("5m",   "5d",   "10min"),
    "15m": ("15m",  "5d",   None),
    "30m": ("30m",  "5d",   None),
    "1h":  ("60m",  "60d",  None),
    "4h":  ("60m",  "60d",  "4h"),
    "1d":  ("1d",   "2y",   None),
    "1w":  ("1wk",  "10y",  None),
    "1mo": ("1mo",  "max",  "ME"),
}


def is_live() -> bool:
    return False


def get_status() -> dict:
    return {
        "live": False,
        "source": "Yahoo Finance (EOD)",
        "market_open": _is_market_open(),
    }


def _is_market_open() -> bool:
    now = datetime.datetime.now()
    if now.weekday() >= 5:
        return False
    t = now.time()
    return datetime.time(9, 15) <= t <= datetime.time(15, 30)


def _yf_ohlcv(symbol: str, days: int = 365) -> pd.DataFrame:
    import yfinance as yf
    sym = symbol + ".NS" if "." not in symbol else symbol
    try:
        period = "1y" if days >= 365 else ("6mo" if days >= 180 else "3mo")
        df = yf.Ticker(sym).history(period=period, interval="1d")
        if df is None or df.empty:
            return pd.DataFrame()
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index).tz_convert(None)
        return df[["open", "high", "low", "close", "volume"]]
    except Exception as e:
        logger.debug(f"yfinance failed for {symbol}: {e}")
        return pd.DataFrame()


def _yf_ohlcv_interval(symbol: str, yf_interval: str, period: str) -> pd.DataFrame:
    import yfinance as yf
    sym = symbol + ".NS" if "." not in symbol else symbol
    try:
        df = yf.Ticker(sym).history(period=period, interval=yf_interval)
        if df is None or df.empty:
            return pd.DataFrame()
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index).tz_convert(None)
        return df[["open", "high", "low", "close", "volume"]]
    except Exception as e:
        logger.debug(f"yfinance interval {yf_interval} failed for {symbol}: {e}")
        return pd.DataFrame()


def get_ohlcv(symbol: str, interval: str = "day", days: int = 365) -> pd.DataFrame:
    return _yf_ohlcv(symbol, days)


def get_ohlcv_interval(symbol: str, interval: str) -> pd.DataFrame:
    cfg = _INTERVAL_CFG.get(interval)
    if not cfg:
        return get_ohlcv(symbol)
    yf_int, yf_period, resample = cfg
    df = _yf_ohlcv_interval(symbol, yf_int, yf_period)
    if not df.empty and resample:
        agg = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
        df = df.resample(resample).agg(agg).dropna()
    return df


def get_live_quotes(symbols: list) -> dict:
    return {}


_NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/market-data/fii-dii-activity",
}

def get_fii_dii() -> dict:
    """Fetch FII/DII activity from NSE India (public API, no login needed)."""
    empty = {"today": {}, "week_fii": 0, "week_dii": 0, "records": [], "sentiment": "Neutral"}
    try:
        import httpx
        with httpx.Client(headers=_NSE_HEADERS, follow_redirects=True, timeout=15) as client:
            # NSE requires a cookie from the homepage before the API works
            client.get("https://www.nseindia.com")
            r = client.get("https://www.nseindia.com/api/fiidiiTradeReact")
            r.raise_for_status()
            raw = r.json()

        rows = raw if isinstance(raw, list) else raw.get("data", [])
        if not rows:
            return empty

        # NSE returns [{date, category, buyValue, sellValue, netValue}, ...]
        # Multiple rows per date (one for FII/FPI, one for DII)
        from collections import defaultdict
        by_date: dict = defaultdict(dict)
        for item in rows:
            date = item.get("date", "")
            cat  = (item.get("category") or item.get("type") or "").upper()
            try:
                net = float(str(item.get("netValue") or item.get("net_value") or 0).replace(",", ""))
            except ValueError:
                net = 0.0
            if "FII" in cat or "FPI" in cat:
                by_date[date]["fii_net"] = net
            elif "DII" in cat:
                by_date[date]["dii_net"] = net

        records = []
        for date, vals in sorted(by_date.items(), reverse=True):
            records.append({
                "date":    date,
                "fii_net": round(vals.get("fii_net", 0), 2),
                "dii_net": round(vals.get("dii_net", 0), 2),
            })

        recent   = records[:5]
        today    = records[0] if records else {}
        week_fii = sum(r.get("fii_net", 0) for r in recent)
        week_dii = sum(r.get("dii_net", 0) for r in recent)

        return {
            "today":    today,
            "week_fii": round(week_fii, 2),
            "week_dii": round(week_dii, 2),
            "records":  recent,
            "sentiment": _fii_sentiment(week_fii, week_dii),
        }
    except Exception as e:
        logger.warning(f"FII/DII fetch failed: {e}")
        return empty


def _fii_sentiment(fii_5d: float, dii_5d: float) -> str:
    if fii_5d > 2000:  return "Strongly Bullish"
    if fii_5d > 500:   return "Bullish"
    if fii_5d < -2000: return "Strongly Bearish"
    if fii_5d < -500:  return "Bearish"
    if dii_5d > 1000:  return "DII Supported"
    return "Neutral"
