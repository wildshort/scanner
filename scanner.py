import yfinance as yf
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

NIFTY_50 = [
    "RELIANCE.NS","HDFCBANK.NS","BHARTIARTL.NS","TCS.NS","ICICIBANK.NS",
    "SBIN.NS","INFY.NS","BAJFINANCE.NS","HINDUNILVR.NS","ITC.NS",
    "LT.NS","HCLTECH.NS","KOTAKBANK.NS","SUNPHARMA.NS","M&M.NS",
    "MARUTI.NS","ULTRACEMCO.NS","AXISBANK.NS","NTPC.NS","BAJAJFINSV.NS",
    "ADANIPORTS.NS","ONGC.NS","BEL.NS","TITAN.NS","ADANIENT.NS",
    "WIPRO.NS","POWERGRID.NS","TATAMOTORS.NS","JSWSTEEL.NS","ASIANPAINT.NS",
    "COALINDIA.NS","NESTLEIND.NS","BAJAJ-AUTO.NS","TATASTEEL.NS","TRENT.NS",
    "GRASIM.NS","SBILIFE.NS","HDFCLIFE.NS","TECHM.NS","EICHERMOT.NS",
    "HINDALCO.NS","SHRIRAMFIN.NS","CIPLA.NS","TATACONSUM.NS","APOLLOHOSP.NS",
    "DRREDDY.NS","HEROMOTOCO.NS","INDUSINDBK.NS","DMART.NS","JIOFIN.NS"
]

NIFTY_100 = NIFTY_50 + [
    "PIDILITIND.NS","AMBUJACEM.NS","GODREJCP.NS","DABUR.NS","ICICIGI.NS",
    "HINDZINC.NS","SIEMENS.NS","LTIM.NS","CONCOR.NS","ASTRAL.NS",
    "ALKEM.NS","ABB.NS","BHARATFORG.NS","BOSCHLTD.NS","CUMMINSIND.NS",
    "BERGEPAINT.NS","DLF.NS","VEDL.NS","IRCTC.NS","MUTHOOTFIN.NS",
    "COLPAL.NS","OFSS.NS","JUBLFOOD.NS","MARICO.NS","GODREJPROP.NS",
    "LTTS.NS","DIXON.NS","SBICARD.NS","CHOLAFIN.NS","TVSMOTOR.NS",
    "ICICIPRULI.NS","NMDC.NS","BHEL.NS","SUPREMEIND.NS","MRF.NS",
    "TATAPOWER.NS","COFORGE.NS","HDFCAMC.NS","POLYCAB.NS","BSE.NS",
    "SRF.NS","PERSISTENT.NS","LUPIN.NS","ASHOKLEY.NS","TORNTPOWER.NS",
    "AUBANK.NS","IDFCFIRSTB.NS","SAIL.NS","MPHASIS.NS","PAGEIND.NS"
]

NIFTY_ALL = NIFTY_100 + [
    "BANDHANBNK.NS","PIIND.NS","M&MFIN.NS","APLLTD.NS","MAXHEALTH.NS",
    "INDUSTOWER.NS","HINDPETRO.NS","NHPC.NS","IDEA.NS","PRESTIGE.NS",
    "OIL.NS","OBEROIRLTY.NS","AUROPHARMA.NS","YESBANK.NS","PAYTM.NS",
    "TIINDIA.NS","PHOENIXLTD.NS","FEDERALBNK.NS","PETRONET.NS","VOLTAS.NS",
    "POWERINDIA.NS","PGHH.NS","PEL.NS"
]

SP500_SAMPLE = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","BRK-B","LLY","AVGO","TSLA",
    "WMT","JPM","V","UNH","XOM","ORCL","MA","HD","PG","COST",
    "JNJ","ABBV","BAC","MRK","CVX","NFLX","KO","AMD","ADBE","CRM",
    "CSCO","ACN","PEP","MCD","TMO","LIN","ABT","CAT","TXN","NOW",
    "ISRG","GE","QCOM","PM","INTU","IBM","RTX","GS","DHR","AMGN",
    "SPGI","BLK","SYK","UNP","LOW","AXP","C","VRTX","REGN","BKNG",
    "SCHW","CME","CB","ETN","PLD","MMC","DE","MDLZ","TJX","ADI",
    "ZTS","GILD","BMY","CI","SO","DUK","CL","EOG","SLB","ITW"
]

MARKETS = {
    "nifty50":  {"name": "Nifty 50",        "symbols": NIFTY_50},
    "nifty100": {"name": "Nifty 100",        "symbols": NIFTY_100},
    "niftyall": {"name": "NSE All (124)",    "symbols": NIFTY_ALL},
    "sp500":    {"name": "S&P 500 (Top 80)", "symbols": SP500_SAMPLE},
}


# ─── Indicator helpers ────────────────────────────────────────────────────────

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_macd(series: pd.Series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal, macd - signal


def compute_bollinger(series: pd.Series, period: int = 20, std: float = 2.0):
    mid = series.rolling(period).mean()
    sd = series.rolling(period).std()
    return mid + std * sd, mid, mid - std * sd


def compute_adx(high, low, close, period: int = 14):
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    mask = plus_dm > minus_dm; minus_dm[mask] = 0
    mask2 = minus_dm >= plus_dm; plus_dm[mask2] = 0
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
    adx = dx.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    return adx, plus_di, minus_di


def heikin_ashi(df: pd.DataFrame) -> pd.DataFrame:
    ha = pd.DataFrame(index=df.index)
    ha['close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ho = [(df['Open'].iloc[0] + df['Close'].iloc[0]) / 2]
    for i in range(1, len(df)):
        ho.append((ho[i-1] + ha['close'].iloc[i-1]) / 2)
    ha['open'] = ho
    ha['high'] = pd.concat([df['High'], ha['open'], ha['close']], axis=1).max(axis=1)
    ha['low']  = pd.concat([df['Low'],  ha['open'], ha['close']], axis=1).min(axis=1)
    return ha


# ─── Divergence & trendline ───────────────────────────────────────────────────

def find_swings(data: list, lookback: int = 3, typ: str = 'high') -> list:
    swings = []
    n = len(data)
    for i in range(lookback, n - lookback):
        window = data[max(0, i-lookback): i+lookback+1]
        target = max(window) if typ == 'high' else min(window)
        if data[i] == target:
            swings.append(i)
    return swings


def detect_divergence(prices: list, rsis: list, lookback: int = 3, recent_n: int = 50) -> list:
    n = min(recent_n, len(prices))
    if n < 12:
        return []
    p = prices[-n:]
    r = rsis[-n:]

    sh = find_swings(p, lookback=lookback, typ='high')
    sl = find_swings(p, lookback=lookback, typ='low')
    result = []

    if len(sh) >= 2:
        i1, i2 = sh[-2], sh[-1]
        p1, p2, r1, r2 = p[i1], p[i2], r[i1], r[i2]
        global_i1 = len(prices) - n + i1
        global_i2 = len(prices) - n + i2
        if p2 > p1 * 1.002 and r2 < r1 - 2:
            result.append({"type": "bearish", "sub": "regular",
                "label": "Bearish Divergence — Price HH, RSI LH → reversal risk",
                "i1": global_i1, "i2": global_i2,
                "p1": round(float(p1),2), "p2": round(float(p2),2),
                "r1": round(float(r1),1), "r2": round(float(r2),1)})
        elif p2 < p1 * 0.998 and r2 > r1 + 2:
            result.append({"type": "bearish", "sub": "hidden",
                "label": "Hidden Bear Div — Price LH, RSI HH → bearish continuation",
                "i1": global_i1, "i2": global_i2,
                "p1": round(float(p1),2), "p2": round(float(p2),2),
                "r1": round(float(r1),1), "r2": round(float(r2),1)})

    if len(sl) >= 2:
        i1, i2 = sl[-2], sl[-1]
        p1, p2, r1, r2 = p[i1], p[i2], r[i1], r[i2]
        global_i1 = len(prices) - n + i1
        global_i2 = len(prices) - n + i2
        if p2 < p1 * 0.998 and r2 > r1 + 2:
            result.append({"type": "bullish", "sub": "regular",
                "label": "Bullish Divergence — Price LL, RSI HL → reversal up",
                "i1": global_i1, "i2": global_i2,
                "p1": round(float(p1),2), "p2": round(float(p2),2),
                "r1": round(float(r1),1), "r2": round(float(r2),1)})
        elif p2 > p1 * 1.002 and r2 < r1 - 2:
            result.append({"type": "bullish", "sub": "hidden",
                "label": "Hidden Bull Div — Price HL, RSI LL → bullish continuation",
                "i1": global_i1, "i2": global_i2,
                "p1": round(float(p1),2), "p2": round(float(p2),2),
                "r1": round(float(r1),1), "r2": round(float(r2),1)})

    return result


def detect_trendlines(close_list: list, high_list: list, low_list: list, lookback: int = 90) -> dict:
    n = min(lookback, len(close_list))
    h = high_list[-n:]
    l = low_list[-n:]
    c = close_list[-n:]
    offset = len(close_list) - n  # index offset into full data
    result = {}

    sh = find_swings(h, lookback=5, typ='high')
    if len(sh) >= 2:
        i1, i2 = sh[-2], sh[-1]
        slope = (h[i2] - h[i1]) / max(i2 - i1, 1)
        end_x = n - 1
        y_at_end = h[i1] + slope * (end_x - i1)
        y_at_prev = h[i1] + slope * (end_x - 1 - i1)
        broke = bool(len(c) >= 2 and c[-2] <= y_at_prev * 1.002 and c[-1] > y_at_end * 0.998)
        result['resistance'] = {
            "sx": int(i1 + offset), "sy": round(float(h[i1]), 2),
            "ex": int(i2 + offset), "ey": round(float(h[i2]), 2),
            "slope": round(float(slope), 6),
            "y_at_end": round(float(y_at_end), 2),
            "end_x": int(end_x + offset),
            "broke": broke
        }

    sl = find_swings(l, lookback=5, typ='low')
    if len(sl) >= 2:
        i1, i2 = sl[-2], sl[-1]
        slope = (l[i2] - l[i1]) / max(i2 - i1, 1)
        end_x = n - 1
        y_at_end = l[i1] + slope * (end_x - i1)
        y_at_prev = l[i1] + slope * (end_x - 1 - i1)
        broke = bool(len(c) >= 2 and c[-2] >= y_at_prev * 0.998 and c[-1] < y_at_end * 1.002)
        result['support'] = {
            "sx": int(i1 + offset), "sy": round(float(l[i1]), 2),
            "ex": int(i2 + offset), "ey": round(float(l[i2]), 2),
            "slope": round(float(slope), 6),
            "y_at_end": round(float(y_at_end), 2),
            "end_x": int(end_x + offset),
            "broke": broke
        }

    return result


# ─── Scoring ──────────────────────────────────────────────────────────────────

def score_stock(row: dict) -> float:
    score = 0.0
    if row.get('above_ema20'):  score += 8
    if row.get('above_ema50'):  score += 10
    if row.get('ema_aligned'):  score += 12
    rsi = row.get('rsi', 50)
    if 45 <= rsi <= 65:   score += 15
    elif 65 < rsi <= 75:  score += 8
    elif 30 <= rsi < 45:  score += 5
    if row.get('macd_bullish'):    score += 10
    if row.get('macd_crossover'):  score += 5
    vol = row.get('vol_ratio', 1.0)
    if vol >= 2.0:   score += 20
    elif vol >= 1.5: score += 12
    elif vol >= 1.2: score += 6
    if row.get('in_bb_upper_half'): score += 6
    adx = row.get('adx', 0)
    if adx >= 25:   score += 8
    elif adx >= 20: score += 4
    if row.get('ha_bullish'): score += 6
    return round(score, 1)


# ─── Main analysis ────────────────────────────────────────────────────────────

def analyze_symbol(symbol: str) -> dict | None:
    try:
        ticker = yf.Ticker(symbol)

        # 1Y daily data
        df = ticker.history(period="1y", interval="1d")
        if df is None or len(df) < 60:
            return None

        close  = df['Close']
        high   = df['High']
        low    = df['Low']
        volume = df['Volume']

        rsi_s                    = compute_rsi(close)
        macd, signal, hist       = compute_macd(close)
        bb_upper, bb_mid, bb_low = compute_bollinger(close)
        adx_s, plus_di, minus_di = compute_adx(high, low, close)
        ema5   = close.ewm(span=5,  adjust=False).mean()
        ema13  = close.ewm(span=13, adjust=False).mean()
        ema20  = close.ewm(span=20, adjust=False).mean()
        ema50  = close.ewm(span=50, adjust=False).mean()
        ha     = heikin_ashi(df)
        vol20  = volume.rolling(20).mean()

        price      = float(close.iloc[-1])
        rsi_val    = float(rsi_s.iloc[-1])
        macd_val   = float(macd.iloc[-1])
        signal_val = float(signal.iloc[-1])
        adx_now    = float(adx_s.iloc[-1]) if not pd.isna(adx_s.iloc[-1]) else 0
        vol_ratio  = float(volume.iloc[-1] / vol20.iloc[-1]) if vol20.iloc[-1] > 0 else 1.0

        e5  = float(ema5.iloc[-1])
        e13 = float(ema13.iloc[-1])
        e50 = float(ema50.iloc[-1])

        macd_bullish   = bool(macd_val > signal_val)
        macd_crossover = bool((macd.iloc[-2] <= signal.iloc[-2]) and (macd.iloc[-1] > signal.iloc[-1]))
        above_ema20    = bool(price > float(ema20.iloc[-1]))
        above_ema50    = bool(price > e50)
        ema_aligned    = bool(e5 > e13 > e50)
        in_bb_upper    = bool(price > float(bb_mid.iloc[-1]))
        ha_bullish     = bool(float(ha['close'].iloc[-1]) > float(ha['open'].iloc[-1]))
        bb_pct         = (price - float(bb_low.iloc[-1])) / (float(bb_upper.iloc[-1]) - float(bb_low.iloc[-1]) + 1e-9)

        high_52w      = float(high.max())
        low_52w       = float(low.min())
        from_52w_high = ((price - high_52w) / high_52w) * 100

        # Fundamentals
        pe = mktcap = None
        try:
            info  = ticker.info
            raw   = info.get('trailingPE') or info.get('forwardPE')
            if raw and not (isinstance(raw, float) and raw != raw):
                pe = float(raw)
            mktcap = info.get('marketCap')
        except Exception:
            pass

        # Build per-candle OHLC array (1Y daily, with indicators)
        def _f(v): return round(float(v), 4) if v is not None and not (isinstance(v, float) and v != v) else None
        ohlc = []
        for i, (idx, row_d) in enumerate(df.iterrows()):
            ohlc.append({
                "date":     str(idx.date()),
                "open":     _f(row_d['Open']),
                "high":     _f(row_d['High']),
                "low":      _f(row_d['Low']),
                "close":    _f(row_d['Close']),
                "volume":   int(row_d['Volume']),
                "rsi":      _f(rsi_s.iloc[i]),
                "ema5":     _f(ema5.iloc[i]),
                "ema50":    _f(ema50.iloc[i]),
                "bb_upper": _f(bb_upper.iloc[i]),
                "bb_mid":   _f(bb_mid.iloc[i]),
                "bb_lower": _f(bb_low.iloc[i]),
            })

        # Trendlines (last 90 trading days ≈ 3 months)
        close_l = [c['close'] for c in ohlc if c['close']]
        high_l  = [c['high']  for c in ohlc if c['high']]
        low_l   = [c['low']   for c in ohlc if c['low']]
        trendlines = detect_trendlines(close_l, high_l, low_l, lookback=90)

        # Daily divergence
        rsi_l = [c['rsi'] or 50 for c in ohlc]
        divs_daily = detect_divergence(close_l, rsi_l, lookback=4, recent_n=60)

        # 4H data for divergence (60 days of 1H → resample to 4H)
        ohlc_4h = []
        divs_4h = []
        try:
            df1h = ticker.history(period="60d", interval="1h")
            if df1h is not None and len(df1h) >= 16:
                df4h = df1h.resample('4h').agg(
                    {'Open': 'first', 'High': 'max', 'Low': 'min',
                     'Close': 'last', 'Volume': 'sum'}
                ).dropna()
                rsi_4h = compute_rsi(df4h['Close'], 14)
                for j, (idx4, row4) in enumerate(df4h.iterrows()):
                    ohlc_4h.append({
                        "date":  str(idx4)[:16],
                        "open":  _f(row4['Open']),  "high": _f(row4['High']),
                        "low":   _f(row4['Low']),   "close": _f(row4['Close']),
                        "volume": int(row4['Volume']),
                        "rsi":   _f(rsi_4h.iloc[j]),
                    })
                c4 = [c['close'] for c in ohlc_4h if c['close']]
                r4 = [c['rsi'] or 50 for c in ohlc_4h]
                divs_4h = detect_divergence(c4, r4, lookback=3, recent_n=40)
        except Exception as e:
            logger.debug(f"4H fetch failed for {symbol}: {e}")

        row = {
            "symbol":       symbol.replace(".NS", ""),
            "full_symbol":  symbol,
            "price":        round(price, 2),
            "change_pct":   round(((price - float(close.iloc[-2])) / float(close.iloc[-2])) * 100, 2),
            "rsi":          round(rsi_val, 1),
            "macd_val":     round(macd_val, 4),
            "signal_val":   round(signal_val, 4),
            "macd_hist":    round(float(hist.iloc[-1]), 4),
            "adx":          round(adx_now, 1),
            "plus_di":      round(float(plus_di.iloc[-1]), 1),
            "minus_di":     round(float(minus_di.iloc[-1]), 1),
            "vol_ratio":    round(vol_ratio, 2),
            "volume":       int(volume.iloc[-1]),
            "avg_volume":   int(vol20.iloc[-1]),
            "ema5":         round(e5, 2),
            "ema13":        round(e13, 2),
            "ema20":        round(float(ema20.iloc[-1]), 2),
            "ema50":        round(e50, 2),
            "bb_upper":     round(float(bb_upper.iloc[-1]), 2),
            "bb_mid":       round(float(bb_mid.iloc[-1]), 2),
            "bb_lower":     round(float(bb_low.iloc[-1]), 2),
            "bb_pct":       round(bb_pct * 100, 1),
            "high_52w":     round(high_52w, 2),
            "low_52w":      round(low_52w, 2),
            "from_52w_high":round(from_52w_high, 1),
            "pe":           round(pe, 1) if pe else None,
            "mktcap":       mktcap,
            "above_ema20":  above_ema20,
            "above_ema50":  above_ema50,
            "ema_aligned":  ema_aligned,
            "macd_bullish": macd_bullish,
            "macd_crossover": macd_crossover,
            "in_bb_upper_half": in_bb_upper,
            "ha_bullish":   ha_bullish,
            "ohlc":         ohlc,
            "ohlc_4h":      ohlc_4h,
            "trendlines":   trendlines,
            "divergences":  divs_daily,
            "divergences_4h": divs_4h,
        }
        row["score"] = score_stock(row)
        return row

    except Exception as e:
        logger.warning(f"Failed {symbol}: {e}")
        return None


def run_scan(market: str = "nifty50", max_workers: int = 8) -> list:
    symbols = MARKETS.get(market, MARKETS["nifty50"])["symbols"]
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(analyze_symbol, sym): sym for sym in symbols}
        for future in as_completed(futures):
            r = future.result()
            if r:
                results.append(r)
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
