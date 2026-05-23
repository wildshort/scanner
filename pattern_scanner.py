"""
Advanced setup scanners for ASTA Scanner.
1. 52W High Breakout    2. Volume Surge         3. Gap Up / Gap Down
4. Supertrend           5. VCP (Minervini)       6. MA Crossovers
7. Candlestick Patterns 8. Classical Patterns
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


# ── Supertrend ─────────────────────────────────────────────────────────────────

def _supertrend_np(high, low, close, period: int = 10, multiplier: float = 3.0):
    """Returns (values, direction) as numpy arrays.  direction: 1=bull, -1=bear."""
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
    fu = hl2 + multiplier * atr   # upper band
    fl = hl2 - multiplier * atr   # lower band
    st = np.zeros(n); dr = np.ones(n, int)
    st[0] = fu[0]; dr[0] = -1

    for i in range(1, n):
        bu = hl2[i] + multiplier * atr[i]
        bl = hl2[i] - multiplier * atr[i]
        fu[i] = bu if (bu < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = bl if (bl > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if st[i - 1] == fu[i - 1]:
            if c[i] > fu[i]:  dr[i] =  1; st[i] = fl[i]
            else:              dr[i] = -1; st[i] = fu[i]
        else:
            if c[i] < fl[i]:  dr[i] = -1; st[i] = fu[i]
            else:              dr[i] =  1; st[i] = fl[i]
    return st, dr


# ── Candlestick Pattern Detector ───────────────────────────────────────────────

def detect_candlestick_patterns(df: pd.DataFrame) -> dict[str, bool]:
    """Detect patterns on the most recent 3 candles."""
    if len(df) < 3:
        return {}
    o = df['open'].values;  h = df['high'].values
    l = df['low'].values;   c = df['close'].values
    i = len(df) - 1
    pats: dict[str, bool] = {}

    body    = abs(c[i] - o[i])
    rng     = h[i] - l[i] + 1e-9
    upper_w = h[i] - max(c[i], o[i])
    lower_w = min(c[i], o[i]) - l[i]
    is_bull = c[i] > o[i]
    is_bear = c[i] < o[i]

    if body / rng < 0.05:
        pats['doji'] = True

    if lower_w >= 2 * body and upper_w <= 0.4 * body and body > 0:
        pats['hammer'] = True

    if upper_w >= 2 * body and lower_w <= 0.4 * body and body > 0:
        pats['shooting_star'] = True

    if lower_w >= 0.6 * rng and lower_w >= 2 * (upper_w + 1e-9):
        pats['pin_bar_bull'] = True

    if upper_w >= 0.6 * rng and upper_w >= 2 * (lower_w + 1e-9):
        pats['pin_bar_bear'] = True

    if i >= 1:
        if c[i-1] < o[i-1] and is_bull and c[i] > o[i-1] and o[i] < c[i-1]:
            pats['bullish_engulfing'] = True
        if c[i-1] > o[i-1] and is_bear and c[i] < o[i-1] and o[i] > c[i-1]:
            pats['bearish_engulfing'] = True

    if i >= 2:
        c1_body = abs(c[i-2] - o[i-2])
        c2_body = abs(c[i-1] - o[i-1])
        star    = c2_body < 0.3 * c1_body if c1_body > 0 else False
        mid_c1  = (c[i-2] + o[i-2]) / 2

        if c[i-2] < o[i-2] and star and is_bull and c[i] > mid_c1:
            pats['morning_star'] = True
        if c[i-2] > o[i-2] and star and is_bear and c[i] < mid_c1:
            pats['evening_star'] = True

    return pats


# ── Classical Chart Pattern Detector ──────────────────────────────────────────

def _swing_pts(arr, window=8):
    ph, pl = [], []
    for i in range(window, len(arr) - window):
        seg = arr[i - window: i + window + 1]
        if arr[i] == max(seg): ph.append(i)
        if arr[i] == min(seg): pl.append(i)
    return ph, pl


def detect_classical_patterns(df: pd.DataFrame, lookback: int = 150) -> dict:
    n = min(lookback, len(df))
    if n < 50:
        return {}
    sl  = df.tail(n)
    c   = sl['close'].values
    h_a = sl['high'].values
    l_a = sl['low'].values
    m   = len(c)
    cur = c[-1]
    pats = {}

    sh, sl_i = _swing_pts(c, window=8)

    # Double Top
    if len(sh) >= 2:
        i1, i2 = sh[-2], sh[-1]
        p1, p2 = c[i1], c[i2]
        if abs(p1 - p2) / (p1 + 1e-9) < 0.04 and i2 - i1 >= 10:
            neck = float(min(c[i1:i2 + 1]))
            if cur < neck * 0.998:
                pats['double_top'] = {'peak1': round(float(p1), 2), 'peak2': round(float(p2), 2), 'neckline': round(neck, 2)}

    # Double Bottom
    if len(sl_i) >= 2:
        i1, i2 = sl_i[-2], sl_i[-1]
        p1, p2 = l_a[i1], l_a[i2]
        if abs(p1 - p2) / (p1 + 1e-9) < 0.04 and i2 - i1 >= 10:
            neck = float(max(c[i1:i2 + 1]))
            if cur > neck * 1.002:
                pats['double_bottom'] = {'trough1': round(float(p1), 2), 'trough2': round(float(p2), 2), 'neckline': round(neck, 2)}

    # Head & Shoulders
    if len(sh) >= 3:
        li, hi, ri = sh[-3], sh[-2], sh[-1]
        ls, head, rs = c[li], c[hi], c[ri]
        if head > ls * 1.03 and head > rs * 1.03 and abs(ls - rs) / (ls + 1e-9) < 0.07:
            neck = float(np.mean([min(c[li:hi + 1]), min(c[hi:ri + 1])]))
            if cur < neck * 0.998:
                pats['head_shoulders'] = {'head': round(float(head), 2), 'neckline': round(neck, 2)}

    # Inverse Head & Shoulders
    if len(sl_i) >= 3:
        li, hi, ri = sl_i[-3], sl_i[-2], sl_i[-1]
        ls, head, rs = l_a[li], l_a[hi], l_a[ri]
        if head < ls * 0.97 and head < rs * 0.97 and abs(ls - rs) / (ls + 1e-9) < 0.07:
            neck = float(np.mean([max(c[li:hi + 1]), max(c[hi:ri + 1])]))
            if cur > neck * 1.002:
                pats['inv_head_shoulders'] = {'head': round(float(head), 2), 'neckline': round(neck, 2)}

    # Cup & Handle
    if m >= 60:
        q = m // 4
        left_high   = float(max(c[:q]))
        cup_low     = float(min(c[q:3 * q]))
        right_top   = float(max(c[3 * q:]))
        depth       = (left_high - cup_low) / (left_high + 1e-9)
        recovery    = (right_top - cup_low) / (left_high - cup_low + 1e-9)
        if 0.10 <= depth <= 0.50 and recovery >= 0.80:
            handle_seg = c[-15:]
            handle_rng = (max(handle_seg) - min(handle_seg)) / (max(handle_seg) + 1e-9)
            if handle_rng <= 0.15:
                pats['cup_handle'] = {
                    'cup_depth_pct': round(depth * 100, 1),
                    'recovery_pct':  round(recovery * 100, 1),
                }

    return pats


# ── VCP — Volatility Contraction Pattern ───────────────────────────────────────

def detect_vcp(df: pd.DataFrame) -> dict | None:
    """Minervini VCP: 3 tightening contractions, volume dry-up, near 52W high."""
    if len(df) < 60:
        return None
    c   = df['close'].values
    h   = df['high'].values
    v   = df['volume'].values
    cur = c[-1]
    h52 = max(h[-252:]) if len(h) >= 252 else max(h)

    if (h52 - cur) / (h52 + 1e-9) > 0.20:
        return None

    w = 20
    if len(c) < 3 * w:
        return None
    ranges = []
    for i in range(3):
        seg = c[-(3 - i) * w: -(2 - i) * w] if i < 2 else c[-w:]
        avg = float(np.mean(seg)) + 1e-9
        ranges.append((float(max(seg)) - float(min(seg))) / avg)

    tightening = all(ranges[j] > ranges[j + 1] * 1.05 for j in range(2))
    vol_dry    = float(np.mean(v[-10:])) < float(np.mean(v[-30:-10])) * 0.80
    ema150     = float(pd.Series(c).ewm(span=150, adjust=False).mean().iloc[-1])
    above_150  = cur > ema150

    return {
        'vcp':            bool(tightening and vol_dry and above_150),
        'contractions':   [round(r * 100, 1) for r in ranges],
        'vol_dry':        vol_dry,
        'above_150':      above_150,
        'from_52w_high_pct': round((h52 - cur) / (h52 + 1e-9) * 100, 1),
    }


# ── Per-Symbol Setup Analysis ─────────────────────────────────────────────────

def _analyze_setups(symbol: str) -> dict | None:
    try:
        import kite_data
        from universe import get_meta, is_fo

        df = kite_data.get_ohlcv(symbol, days=400)
        if df is None or len(df) < 60:
            return None
        df.columns = [c.lower() for c in df.columns]
        if not {'open', 'high', 'low', 'close', 'volume'}.issubset(df.columns):
            return None

        cls  = df['close'];  hgh = df['high'];  lw = df['low']
        opn  = df['open'];   vol = df['volume']
        cur  = float(cls.iloc[-1]);  prev_c = float(cls.iloc[-2])
        chg  = round((cur - prev_c) / prev_c * 100, 2)
        meta = get_meta(symbol)

        # 1. 52W High Breakout
        h52      = float(hgh.iloc[-252:].max()) if len(hgh) >= 252 else float(hgh.max())
        from_52w = round((h52 - cur) / (h52 + 1e-9) * 100, 1)
        near_52w = from_52w <= 2.0
        new_52w  = from_52w <= 0.3

        # 2. Volume Surge
        vol20     = float(vol.iloc[-21:-1].mean()) if len(vol) > 21 else float(vol.mean())
        vol_ratio = float(vol.iloc[-1]) / (vol20 + 1e-9)
        vol_surge = vol_ratio >= 2.5

        # 3. Gap
        gap_pct  = round((float(opn.iloc[-1]) - prev_c) / prev_c * 100, 2)
        gap_up   = gap_pct >= 1.0
        gap_down = gap_pct <= -1.0

        # 4. Supertrend
        st_v, st_d = _supertrend_np(hgh.values, lw.values, cls.values)
        st_bull    = bool(int(st_d[-1]) == 1)
        st_crossed = len(st_d) > 1 and int(st_d[-1]) != int(st_d[-2])
        st_val     = round(float(st_v[-1]), 2)

        # 5. VCP
        vcp    = detect_vcp(df)
        is_vcp = bool(vcp and vcp['vcp'])

        # 6. MA Crossovers (last 3 bars)
        ema5   = cls.ewm(span=5,   adjust=False).mean()
        ema20  = cls.ewm(span=20,  adjust=False).mean()
        ema50  = cls.ewm(span=50,  adjust=False).mean()
        ema200 = cls.ewm(span=200, adjust=False).mean()

        def _xup(a, b):
            for k in (-3, -2):
                if a.iloc[k - 1] <= b.iloc[k - 1] and a.iloc[k] > b.iloc[k]:
                    return True
            return False

        def _xdn(a, b):
            for k in (-3, -2):
                if a.iloc[k - 1] >= b.iloc[k - 1] and a.iloc[k] < b.iloc[k]:
                    return True
            return False

        golden_cross    = _xup(ema50, ema200)
        death_cross     = _xdn(ema50, ema200)
        ema_bull_cross  = _xup(ema5, ema20)
        ema_bear_cross  = _xdn(ema5, ema20)

        # 7. Candlestick Patterns
        candle_pats = detect_candlestick_patterns(df)

        # 8. Classical Patterns
        classical_pats = detect_classical_patterns(df)

        return {
            'symbol':      symbol,
            'name':        meta['name'],
            'sector':      meta['sector'],
            'sector_color': meta['sector_color'],
            'fo':          bool(is_fo(symbol)),
            'price':       round(cur, 2),
            'change_pct':  chg,
            'vol_ratio':   round(vol_ratio, 2),
            'high_52w':    round(h52, 2),
            'from_52w_high_pct': from_52w,
            'near_52w':    near_52w,
            'new_52w':     new_52w,
            'vol_surge':   vol_surge,
            'gap_pct':     gap_pct,
            'gap_up':      gap_up,
            'gap_down':    gap_down,
            'st_bull':     st_bull,
            'st_crossed':  st_crossed,
            'st_val':      st_val,
            'is_vcp':      is_vcp,
            'vcp':         vcp,
            'golden_cross':   golden_cross,
            'death_cross':    death_cross,
            'ema_bull_cross': ema_bull_cross,
            'ema_bear_cross': ema_bear_cross,
            'candle_patterns':   candle_pats,
            'classical_patterns': classical_pats,
        }
    except Exception as e:
        logger.warning(f"setup scan failed [{symbol}]: {e}")
        return None


def run_setups_scan(market: str = 'nifty50', max_workers: int = 8) -> dict:
    from universe import MARKETS
    symbols = MARKETS.get(market, MARKETS['nifty50'])['symbols']
    all_r: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_analyze_setups, s): s for s in symbols}
        for f in as_completed(futs):
            r = f.result()
            if r:
                all_r.append(r)

    bull_candle_keys = {'hammer', 'bullish_engulfing', 'pin_bar_bull', 'morning_star', 'doji'}
    bear_candle_keys = {'shooting_star', 'bearish_engulfing', 'pin_bar_bear', 'evening_star'}

    return {
        'breakouts_52w':  sorted([r for r in all_r if r['near_52w'] or r['new_52w']], key=lambda x: x['from_52w_high_pct']),
        'vol_surge':      sorted([r for r in all_r if r['vol_surge']], key=lambda x: x['vol_ratio'], reverse=True),
        'gap_up':         sorted([r for r in all_r if r['gap_up']],   key=lambda x: x['gap_pct'], reverse=True),
        'gap_down':       sorted([r for r in all_r if r['gap_down']], key=lambda x: x['gap_pct']),
        'st_bull_cross':  sorted([r for r in all_r if r['st_bull'] and r['st_crossed']], key=lambda x: x['change_pct'], reverse=True),
        'st_bear_cross':  sorted([r for r in all_r if not r['st_bull'] and r['st_crossed']], key=lambda x: x['change_pct']),
        'st_bull_all':    sorted([r for r in all_r if r['st_bull']], key=lambda x: x['change_pct'], reverse=True),
        'vcp':            sorted([r for r in all_r if r['is_vcp']], key=lambda x: x['from_52w_high_pct']),
        'golden_cross':   [r for r in all_r if r['golden_cross']],
        'death_cross':    [r for r in all_r if r['death_cross']],
        'ema_bull_cross': sorted([r for r in all_r if r['ema_bull_cross']], key=lambda x: x['change_pct'], reverse=True),
        'ema_bear_cross': [r for r in all_r if r['ema_bear_cross']],
        'candle_bull':    [r for r in all_r if any(p in r['candle_patterns'] for p in bull_candle_keys)],
        'candle_bear':    [r for r in all_r if any(p in r['candle_patterns'] for p in bear_candle_keys)],
        'classical':      [r for r in all_r if r['classical_patterns']],
    }
