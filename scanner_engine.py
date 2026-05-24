"""
Core analysis: indicators, scoring, per-symbol deep dive.
"""
from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

import kite_data
from universe import MARKETS, get_meta, is_fo, NIFTY_200
from trendline_engine import classify_chart, detect_trendlines, _tl_to_dict

logger = logging.getLogger(__name__)


# ── Indicator helpers ──────────────────────────────────────────────────────────

def _rsi(s: pd.Series, n=14) -> pd.Series:
    d = s.diff(); g = d.clip(lower=0); l = -d.clip(upper=0)
    ag = g.ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    al = l.ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    return 100 - 100 / (1 + ag / al)

def _macd(s: pd.Series):
    e12 = s.ewm(span=12, adjust=False).mean()
    e26 = s.ewm(span=26, adjust=False).mean()
    m = e12 - e26; sig = m.ewm(span=9, adjust=False).mean()
    return m, sig, m - sig

def _bb(s: pd.Series, n=20, k=2.0):
    m = s.rolling(n).mean(); sd = s.rolling(n).std()
    return m + k*sd, m, m - k*sd

def _adx(h, l, c, n=14):
    pdm = h.diff().clip(lower=0); ndm = (-l.diff()).clip(lower=0)
    mask = pdm > ndm; ndm[mask] = 0
    mask2 = ndm >= pdm; pdm[mask2] = 0
    tr = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/n, min_periods=n, adjust=False).mean()
    pdi = 100 * pdm.ewm(alpha=1/n, min_periods=n, adjust=False).mean() / atr
    ndi = 100 * ndm.ewm(alpha=1/n, min_periods=n, adjust=False).mean() / atr
    dx  = 100 * (pdi-ndi).abs() / (pdi+ndi+1e-9)
    return dx.ewm(alpha=1/n, min_periods=n, adjust=False).mean(), pdi, ndi

def _stoch(h: pd.Series, l: pd.Series, c: pd.Series, k=14, d=3):
    lo = l.rolling(k).min(); hi = h.rolling(k).max()
    kp = 100 * (c - lo) / (hi - lo + 1e-9)
    return kp, kp.rolling(d).mean()

def _vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df['high'] + df['low'] + df['close']) / 3
    return (tp * df['volume']).cumsum() / (df['volume'].cumsum() + 1e-9)


def _pivot_points(ph: float, pl: float, pc: float) -> dict:
    pp = (ph + pl + pc) / 3
    return {
        'pp': round(pp, 2),
        'r1': round(2*pp - pl, 2), 'r2': round(pp + ph - pl, 2), 'r3': round(2*pp + ph - 2*pl, 2),
        's1': round(2*pp - ph, 2), 's2': round(pp - ph + pl, 2), 's3': round(2*pp - 2*ph + pl, 2),
    }


def _nifty_returns() -> dict:
    try:
        import yfinance as yf
        df = yf.download('^NSEI', period='2mo', auto_adjust=True, progress=False)
        c  = df['Close'].squeeze().dropna()
        if len(c) < 6:
            return {}
        v = lambda i: float(c.iloc[i])
        return {
            '1d':  round((v(-1) - v(-2)) / v(-2) * 100, 2),
            '5d':  round((v(-1) - v(-6)) / v(-6) * 100, 2) if len(c) >= 6  else 0,
            '20d': round((v(-1) - v(-21))/ v(-21)* 100, 2) if len(c) >= 21 else 0,
        }
    except Exception:
        return {}


def _supertrend(high, low, close, period: int = 10, multiplier: float = 3.0):
    """Returns (values, direction) as numpy arrays. direction: 1=bull, -1=bear."""
    n = len(close)
    h = np.asarray(high, float); l = np.asarray(low, float); c = np.asarray(close, float)
    prev_c = np.empty_like(c); prev_c[0] = c[0]; prev_c[1:] = c[:-1]
    tr = np.maximum.reduce([h - l, np.abs(h - prev_c), np.abs(l - prev_c)])
    atr = np.zeros(n)
    if n >= period:
        atr[period - 1] = tr[:period].mean()
        for i in range(period, n):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        atr[:period - 1] = atr[period - 1]
    hl2 = (h + l) / 2.0
    fu = hl2 + multiplier * atr; fl = hl2 - multiplier * atr
    st = np.zeros(n); dr = np.ones(n, int)
    st[0] = fu[0]; dr[0] = -1
    for i in range(1, n):
        bu = hl2[i] + multiplier * atr[i]; bl = hl2[i] - multiplier * atr[i]
        fu[i] = bu if (bu < fu[i-1] or c[i-1] > fu[i-1]) else fu[i-1]
        fl[i] = bl if (bl > fl[i-1] or c[i-1] < fl[i-1]) else fl[i-1]
        if st[i-1] == fu[i-1]:
            dr[i] =  1 if c[i] > fu[i] else -1
            st[i] = fl[i] if dr[i] == 1 else fu[i]
        else:
            dr[i] = -1 if c[i] < fl[i] else 1
            st[i] = fu[i] if dr[i] == -1 else fl[i]
    return st, dr


def _ha(df: pd.DataFrame) -> pd.DataFrame:
    ha = pd.DataFrame(index=df.index)
    ha['close'] = (df['open']+df['high']+df['low']+df['close'])/4
    ho = [(df['open'].iloc[0]+df['close'].iloc[0])/2]
    for i in range(1, len(df)): ho.append((ho[-1]+ha['close'].iloc[i-1])/2)
    ha['open'] = ho
    ha['high'] = pd.concat([df['high'],ha['open'],ha['close']],axis=1).max(axis=1)
    ha['low']  = pd.concat([df['low'], ha['open'],ha['close']],axis=1).min(axis=1)
    return ha


def _score(r: dict) -> float:
    s = 0.0
    if r.get('above_ema20'): s += 8
    if r.get('above_ema50'): s += 10
    if r.get('ema_aligned'): s += 12
    rsi = r.get('rsi', 50)
    if 45<=rsi<=65: s += 15
    elif 65<rsi<=75: s += 8
    elif 30<=rsi<45: s += 5
    if r.get('macd_bullish'):    s += 10
    if r.get('macd_crossover'):  s += 5
    v = r.get('vol_ratio', 1)
    if v >= 2: s += 20
    elif v >= 1.5: s += 12
    elif v >= 1.2: s += 6
    if r.get('in_bb_upper'): s += 6
    adx = r.get('adx', 0)
    if adx >= 25: s += 8
    elif adx >= 20: s += 4
    if r.get('ha_bullish'): s += 6
    return round(s, 1)


def _f(v):
    if v is None: return None
    try:
        fv = float(v)
        return None if fv != fv else round(fv, 4)
    except: return None


def analyze_symbol(symbol: str, include_chart: bool = True) -> dict | None:
    try:
        df_raw = kite_data.get_ohlcv(symbol, "day", 400)
        if df_raw is None or len(df_raw) < 60:
            return None

        df = df_raw.copy()
        df.columns = [c.lower() for c in df.columns]
        if not {'open','high','low','close','volume'}.issubset(df.columns):
            return None

        close = df['close']; high = df['high']; low = df['low']; vol = df['volume']

        rsi_s               = _rsi(close)
        macd_s, sig_s, hist = _macd(close)
        bb_up, bb_mid, bb_lo = _bb(close)
        adx_s, pdi, ndi     = _adx(high, low, close)
        ema5  = close.ewm(span=5,  adjust=False).mean()
        ema13 = close.ewm(span=13, adjust=False).mean()
        ema20 = close.ewm(span=20, adjust=False).mean()
        ema50 = close.ewm(span=50, adjust=False).mean()
        ha    = _ha(df)
        vol20 = vol.rolling(20).mean()
        st_vals, st_dirs = _supertrend(high.values, low.values, close.values)

        price     = float(close.iloc[-1])
        prev_close= float(close.iloc[-2])
        rsi_v     = float(rsi_s.iloc[-1])
        macd_v    = float(macd_s.iloc[-1])
        sig_v     = float(sig_s.iloc[-1])
        adx_v     = float(adx_s.iloc[-1]) if not pd.isna(adx_s.iloc[-1]) else 0
        vol_ratio = float(vol.iloc[-1] / vol20.iloc[-1]) if vol20.iloc[-1] > 0 else 1.0

        e5, e13, e50 = float(ema5.iloc[-1]), float(ema13.iloc[-1]), float(ema50.iloc[-1])
        macd_bullish   = bool(macd_v > sig_v)
        macd_crossover = bool(macd_s.iloc[-2] <= sig_s.iloc[-2] and macd_s.iloc[-1] > sig_s.iloc[-1])
        above_ema20    = bool(price > float(ema20.iloc[-1]))
        above_ema50    = bool(price > e50)
        ema_aligned    = bool(e5 > e13 > e50)
        in_bb_upper    = bool(price > float(bb_mid.iloc[-1]))
        ha_bullish     = bool(float(ha['close'].iloc[-1]) > float(ha['open'].iloc[-1]))

        change_pct  = round((price - prev_close) / prev_close * 100, 2)
        change_5d   = round((price - float(close.iloc[-6]))  / float(close.iloc[-6])  * 100, 2) if len(close) >= 6  else 0.0
        change_20d  = round((price - float(close.iloc[-21])) / float(close.iloc[-21]) * 100, 2) if len(close) >= 21 else 0.0
        st_bull    = bool(int(st_dirs[-1]) == 1)
        st_crossed = len(st_dirs) > 1 and int(st_dirs[-1]) != int(st_dirs[-2])
        st_val     = round(float(st_vals[-1]), 2)

        # Pivot points from previous session
        prev_bar = df.iloc[-2]
        pivots   = _pivot_points(float(prev_bar['high']), float(prev_bar['low']), float(prev_bar['close']))

        # Fundamentals
        pe = mktcap = None
        try:
            import yfinance as yf
            info = yf.Ticker(symbol + ".NS").info
            raw_pe = info.get('trailingPE') or info.get('forwardPE')
            pe     = round(float(raw_pe), 1) if raw_pe else None
            mc     = info.get('marketCap')
            mktcap = int(mc) if mc else None
        except: pass

        meta = get_meta(symbol)

        row = {
            "symbol":        symbol,
            "name":          meta["name"],
            "sector":        meta["sector"],
            "sector_color":  meta["sector_color"],
            "fo":            bool(is_fo(symbol)),
            "price":         round(price, 2),
            "change_pct":    change_pct,
            "rsi":           round(rsi_v, 1),
            "macd_v":        _f(macd_v),
            "sig_v":         _f(sig_v),
            "macd_hist":     _f(float(hist.iloc[-1])),
            "adx":           round(adx_v, 1),
            "plus_di":       round(float(pdi.iloc[-1]), 1),
            "minus_di":      round(float(ndi.iloc[-1]), 1),
            "vol_ratio":     round(vol_ratio, 2),
            "volume":        int(vol.iloc[-1]),
            "ema5":          round(e5, 2),
            "ema13":         round(e13, 2),
            "ema20":         round(float(ema20.iloc[-1]), 2),
            "ema50":         round(e50, 2),
            "bb_upper":      round(float(bb_up.iloc[-1]), 2),
            "bb_mid":        round(float(bb_mid.iloc[-1]), 2),
            "bb_lower":      round(float(bb_lo.iloc[-1]), 2),
            "bb_pct":        round((price-float(bb_lo.iloc[-1]))/(float(bb_up.iloc[-1])-float(bb_lo.iloc[-1])+1e-9)*100, 1),
            "high_52w":      round(float(high.max()), 2),
            "low_52w":       round(float(low.min()), 2),
            "from_52w_high": round((price - float(high.max())) / float(high.max()) * 100, 1),
            "pe":            pe,
            "mktcap":        mktcap,
            "above_ema20":   above_ema20,
            "above_ema50":   above_ema50,
            "ema_aligned":   ema_aligned,
            "macd_bullish":  macd_bullish,
            "macd_crossover": macd_crossover,
            "in_bb_upper":   in_bb_upper,
            "ha_bullish":    ha_bullish,
            "st_bull":       st_bull,
            "st_crossed":    st_crossed,
            "st_val":        st_val,
            "change_5d":     change_5d,
            "change_20d":    change_20d,
            "pivots":        pivots,
        }
        row["score"] = _score(row)

        # Trendline classification
        try:
            tl_df = df[['open','high','low','close','volume']].copy()
            tl_result = classify_chart(tl_df)

            # Context validation: suppress signals that contradict the EMA20 trend
            cat = tl_result.get("category", "no_structure")
            if cat == "fresh_breakout" and not above_ema20:
                tl_result["category"] = "no_structure"
                tl_result["direction"] = None
                tl_result["reason"] = ""
            elif cat == "fresh_breakdown" and above_ema20:
                tl_result["category"] = "no_structure"
                tl_result["direction"] = None
                tl_result["reason"] = ""

            row["tl_category"] = tl_result.get("category", "no_structure")
            row["tl_direction"] = tl_result.get("direction")
            row["tl_level"]    = tl_result.get("trendline_level")
            row["tl_reason"]   = tl_result.get("reason", "")
            row["tl_score"]    = tl_result.get("score", 0.0)
            row["tl_resistance"] = tl_result.get("resistance")
            row["tl_support"]    = tl_result.get("support")
        except Exception as e:
            logger.debug(f"TL classify failed for {symbol}: {e}")
            row["tl_category"] = "no_structure"

        if include_chart:
            # Per-candle data for chart (1Y window) — computed on full df for warm indicators
            n1y = 252
            rsi_all    = _rsi(close)
            macd_all, sig_all, hist_all = _macd(close)
            bb_u_all, bb_m_all, bb_l_all = _bb(close)
            adx_all, pdi_all, ndi_all = _adx(high, low, close)
            ema5_all   = close.ewm(span=5,  adjust=False).mean()
            ema50_all  = close.ewm(span=50, adjust=False).mean()
            sk_all, sd_all = _stoch(high, low, close)
            st_all, stdir_all = _supertrend(high.values, low.values, close.values)

            df_1y = df.tail(n1y)
            slice_idx = range(len(df) - min(n1y, len(df)), len(df))

            ohlc = []
            for pos, (idx, r) in zip(slice_idx, df_1y.iterrows()):
                date_str = str(idx.date()) if hasattr(idx, 'date') else str(idx)[:10]
                ohlc.append({
                    "time":      int(pd.Timestamp(idx).timestamp()),
                    "date":      date_str,
                    "open":      _f(r['open']),
                    "high":      _f(r['high']),
                    "low":       _f(r['low']),
                    "close":     _f(r['close']),
                    "volume":    int(r['volume']),
                    "rsi":       _f(rsi_all.iloc[pos]),
                    "ema5":      _f(ema5_all.iloc[pos]),
                    "ema50":     _f(ema50_all.iloc[pos]),
                    "bb_upper":  _f(bb_u_all.iloc[pos]),
                    "bb_mid":    _f(bb_m_all.iloc[pos]),
                    "bb_lower":  _f(bb_l_all.iloc[pos]),
                    "macd":      _f(macd_all.iloc[pos]),
                    "macd_sig":  _f(sig_all.iloc[pos]),
                    "macd_hist": _f(hist_all.iloc[pos]),
                    "plus_di":   _f(pdi_all.iloc[pos]),
                    "minus_di":  _f(ndi_all.iloc[pos]),
                    "adx_bar":   _f(adx_all.iloc[pos]),
                    "stoch_k":   _f(sk_all.iloc[pos]),
                    "stoch_d":   _f(sd_all.iloc[pos]),
                    "st":        _f(st_all[pos]),
                    "st_dir":    int(stdir_all[pos]),
                })
            row["ohlc"] = ohlc

            # 4H data
            try:
                df4h_raw = kite_data.get_ohlcv(symbol, "60m", 60)
                if df4h_raw is not None and len(df4h_raw) >= 16:
                    df4h_raw.columns = [c.lower() for c in df4h_raw.columns]
                    df4h = df4h_raw.resample('4h').agg(
                        {'open':'first','high':'max','low':'min','close':'last','volume':'sum'}
                    ).dropna()
                    rsi4h = _rsi(df4h['close'])
                    row["ohlc_4h"] = [
                        {"time": int(pd.Timestamp(idx).timestamp()), "date": str(idx)[:16],
                         "open":_f(r['open']),"high":_f(r['high']),"low":_f(r['low']),
                         "close":_f(r['close']),"volume":int(r['volume']),"rsi":_f(rsi4h.iloc[j])}
                        for j,(idx,r) in enumerate(df4h.iterrows())
                    ]
            except: row["ohlc_4h"] = []

        return row
    except Exception as e:
        logger.warning(f"analyze_symbol failed [{symbol}]: {e}")
        return None


def fetch_chart_data(symbol: str, interval: str) -> dict | None:
    """Fetch OHLCV + all indicators for a specific chart interval."""
    try:
        df = kite_data.get_ohlcv_interval(symbol, interval)
        if df is None or len(df) < 5:
            return None
        df.columns = [c.lower() for c in df.columns]

        close = df['close']; high = df['high']; low = df['low']; vol = df['volume']
        rsi_s              = _rsi(close)
        macd_s, sig_s, hs  = _macd(close)
        bb_u, bb_m, bb_l   = _bb(close)
        adx_s, pdi, ndi    = _adx(high, low, close)
        ema5               = close.ewm(span=5,  adjust=False).mean()
        ema50              = close.ewm(span=50, adjust=False).mean()
        sk, sd             = _stoch(high, low, close)
        st_v, st_d         = _supertrend(high.values, low.values, close.values)

        intraday_intervals = {"5m","10m","15m","30m","1h"}
        vwap_s = _vwap(df) if interval in intraday_intervals else None

        ohlc = []
        for i, (idx, r) in enumerate(df.iterrows()):
            candle = {
                "time":      int(pd.Timestamp(idx).timestamp()),
                "open":      _f(r['open']),
                "high":      _f(r['high']),
                "low":       _f(r['low']),
                "close":     _f(r['close']),
                "volume":    int(r['volume']) if not pd.isna(r['volume']) else 0,
                "rsi":       _f(rsi_s.iloc[i]),
                "ema5":      _f(ema5.iloc[i]),
                "ema50":     _f(ema50.iloc[i]),
                "bb_upper":  _f(bb_u.iloc[i]),
                "bb_mid":    _f(bb_m.iloc[i]),
                "bb_lower":  _f(bb_l.iloc[i]),
                "macd":      _f(macd_s.iloc[i]),
                "macd_sig":  _f(sig_s.iloc[i]),
                "macd_hist": _f(hs.iloc[i]),
                "plus_di":   _f(pdi.iloc[i]),
                "minus_di":  _f(ndi.iloc[i]),
                "adx_bar":   _f(adx_s.iloc[i]),
                "stoch_k":   _f(sk.iloc[i]),
                "stoch_d":   _f(sd.iloc[i]),
                "st":        _f(st_v[i]),
                "st_dir":    int(st_d[i]),
            }
            if vwap_s is not None:
                candle["vwap"] = _f(vwap_s.iloc[i])
            ohlc.append(candle)
        return {"symbol": symbol, "interval": interval, "ohlc": ohlc}
    except Exception as e:
        logger.warning(f"fetch_chart_data failed [{symbol}/{interval}]: {e}")
        return None


def run_scan(market: str = "nifty50", max_workers: int = 16) -> dict:
    symbols = MARKETS.get(market, MARKETS["nifty50"])["symbols"]

    # Fetch Nifty returns once for RS calculation
    nifty_ret = _nifty_returns()

    # Batch live quotes first (fast single call)
    live_quotes = kite_data.get_live_quotes(symbols) if kite_data.is_live() else {}

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(analyze_symbol, sym, False): sym for sym in symbols}
        for fut in as_completed(futures):
            r = fut.result()
            if r:
                # Overlay live price if available
                q = live_quotes.get(r["symbol"])
                if q and q.get("last_price"):
                    r["price"]  = q["last_price"]
                    # Only use live change_pct when market is actually open;
                    # Kite resets it to 0 at market open before first tick
                    if kite_data._is_market_open():
                        r["change_pct"] = q["change_pct"]
                    r["volume"] = q["volume"]
                    r["oi"]     = q.get("oi", 0)

                # RS vs Nifty
                if nifty_ret:
                    r["rs_1d"]  = round(r.get("change_pct", 0) - nifty_ret.get("1d",  0), 2)
                    r["rs_5d"]  = round(r.get("change_5d",  0) - nifty_ret.get("5d",  0), 2)
                    r["rs_20d"] = round(r.get("change_20d", 0) - nifty_ret.get("20d", 0), 2)

                results.append(r)

    results.sort(key=lambda x: x["score"], reverse=True)

    # Sector aggregation
    sectors = _aggregate_sectors(results)

    # Market breadth
    above_ema50 = sum(1 for r in results if r.get("above_ema50"))
    adv = sum(1 for r in results if r.get("change_pct", 0) > 0)
    dec = sum(1 for r in results if r.get("change_pct", 0) < 0)
    highs_52w = sum(1 for r in results if r.get("from_52w_high", -99) >= -2)
    breadth = {
        "pct_above_ema50": round(above_ema50 / len(results) * 100, 1) if results else 0,
        "adv_dec_ratio":   round(adv / (dec + 1), 2),
        "advances":        adv,
        "declines":        dec,
        "new_52w_highs":   highs_52w,
    }

    return {
        "results":  results,
        "sectors":  sectors,
        "breadth":  breadth,
        "source":   kite_data.get_status(),
        "total":    len(results),
    }


def run_trendline_scan(market: str = "nifty50", max_workers: int = 6) -> dict:
    """Scan for trendline breakouts/breakdowns using the same analyze_symbol
    logic (including EMA20 context validation and ASTA scoring).

    Qualification rules:
      fresh_breakout  — price > EMA20  AND  ASTA score >= 40
      fresh_breakdown — price < EMA20  (any score; bearish setups score low by design)
      pullback        — included as-is for awareness
    """
    symbols = MARKETS.get(market, MARKETS["nifty50"])["symbols"]
    breakouts, breakdowns, pullbacks = [], [], []

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(analyze_symbol, sym, False): sym for sym in symbols}
        for fut in as_completed(futures):
            r = fut.result()
            if not r: continue
            cat   = r.get("tl_category", "no_structure")
            score = r.get("score", 0)

            entry = {
                "symbol":     r["symbol"],
                "name":       r["name"],
                "sector":     r["sector"],
                "fo":         r["fo"],
                "price":      r["price"],
                "change_pct": r["change_pct"],
                "score":      score,
                "rsi":        r.get("rsi"),
                "above_ema20": r.get("above_ema20"),
                "category":   cat,
                "direction":  r.get("tl_direction"),
                "trendline_level": r.get("tl_level"),
                "reason":     r.get("tl_reason", ""),
                "tl_score":   r.get("tl_score", 0),
                "resistance": r.get("tl_resistance"),
                "support":    r.get("tl_support"),
            }

            if cat == "fresh_breakout" and score >= 40:
                breakouts.append(entry)
            elif cat == "fresh_breakdown":
                breakdowns.append(entry)
            elif cat == "pullback":
                pullbacks.append(entry)

    breakouts.sort(key=lambda x: x["score"], reverse=True)
    breakdowns.sort(key=lambda x: x["tl_score"], reverse=True)

    return {
        "breakouts":  breakouts,
        "breakdowns": breakdowns,
        "pullbacks":  pullbacks,
    }


def _aggregate_sectors(results: list[dict]) -> list[dict]:
    sectors: dict[str, list] = {}
    for r in results:
        sec = r.get("sector", "Other")
        sectors.setdefault(sec, []).append(r)

    agg = []
    for sec, stocks in sectors.items():
        changes = [s["change_pct"] for s in stocks if s.get("change_pct") is not None]
        avg_chg = round(sum(changes) / len(changes), 2) if changes else 0
        top = sorted(stocks, key=lambda x: x.get("change_pct", 0), reverse=True)
        bot = sorted(stocks, key=lambda x: x.get("change_pct", 0))
        agg.append({
            "sector":    sec,
            "count":     len(stocks),
            "avg_chg":   avg_chg,
            "top_gainer": top[0]["symbol"] if top else "",
            "top_loser":  bot[0]["symbol"] if bot else "",
            "color":     stocks[0].get("sector_color", "#6b7280") if stocks else "#6b7280",
            "stocks":    [s["symbol"] for s in stocks],
        })
    agg.sort(key=lambda x: x["avg_chg"], reverse=True)
    return agg
