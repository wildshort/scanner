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

def _pivot_highs(arr, window: int = 12) -> list[int]:
    out = []
    for i in range(window, len(arr) - window):
        if arr[i] == max(arr[i - window: i + window + 1]):
            out.append(i)
    return out

def _pivot_lows(arr, window: int = 12) -> list[int]:
    out = []
    for i in range(window, len(arr) - window):
        if arr[i] == min(arr[i - window: i + window + 1]):
            out.append(i)
    return out


def detect_classical_patterns(df: pd.DataFrame, lookback: int = 200) -> dict:
    """
    Strict classical pattern detection.
    Uses actual high/low arrays and tighter thresholds to eliminate false positives.
    """
    n = min(lookback, len(df))
    if n < 80:
        return {}
    sl  = df.tail(n)
    c   = sl['close'].values
    h   = sl['high'].values
    l   = sl['low'].values
    m   = len(c)
    cur = c[-1]
    pats = {}

    # Use actual highs/lows with larger window — fewer, cleaner pivots
    ph = _pivot_highs(h, window=12)
    pl = _pivot_lows(l, window=12)

    # ── Double Top ────────────────────────────────────────────────────────────
    # Two peaks within 3% of each other, 15–80 bars apart,
    # valley ≥4% below peaks, current price broken below valley
    if len(ph) >= 2:
        i1, i2 = ph[-2], ph[-1]
        p1, p2 = h[i1], h[i2]
        sep = i2 - i1
        if 15 <= sep <= 80:
            similarity = abs(p1 - p2) / ((p1 + p2) / 2 + 1e-9)
            valley     = float(min(l[i1:i2 + 1]))
            peak_avg   = (p1 + p2) / 2
            v_depth    = (peak_avg - valley) / (peak_avg + 1e-9)
            if similarity <= 0.03 and v_depth >= 0.04 and cur < valley * 0.997:
                pats['double_top'] = {
                    'peak1':    round(float(p1), 2),
                    'peak2':    round(float(p2), 2),
                    'neckline': round(valley, 2),
                }

    # ── Double Bottom ─────────────────────────────────────────────────────────
    if len(pl) >= 2:
        i1, i2 = pl[-2], pl[-1]
        p1, p2 = l[i1], l[i2]
        sep = i2 - i1
        if 15 <= sep <= 80:
            similarity = abs(p1 - p2) / ((p1 + p2) / 2 + 1e-9)
            peak       = float(max(h[i1:i2 + 1]))
            trough_avg = (p1 + p2) / 2
            p_height   = (peak - trough_avg) / (trough_avg + 1e-9)
            if similarity <= 0.03 and p_height >= 0.04 and cur > peak * 1.003:
                pats['double_bottom'] = {
                    'trough1':  round(float(p1), 2),
                    'trough2':  round(float(p2), 2),
                    'neckline': round(peak, 2),
                }

    # ── Head & Shoulders ──────────────────────────────────────────────────────
    # Head ≥5% above both shoulders; shoulders within 8% of each other;
    # min 10 bars between each point; price broken below neckline
    if len(ph) >= 3:
        li, hi_i, ri = ph[-3], ph[-2], ph[-1]
        ls, head, rs = h[li], h[hi_i], h[ri]
        shld_sim = abs(ls - rs) / ((ls + rs) / 2 + 1e-9)
        if (head >= ls * 1.05 and head >= rs * 1.05 and
                shld_sim <= 0.08 and
                hi_i - li >= 10 and ri - hi_i >= 10):
            neck_l = float(max(min(l[li:hi_i + 1]), min(l[hi_i:ri + 1])))
            if cur < neck_l * 0.998:
                pats['head_shoulders'] = {
                    'head':     round(float(head), 2),
                    'neckline': round(neck_l, 2),
                }

    # ── Inverse Head & Shoulders ──────────────────────────────────────────────
    if len(pl) >= 3:
        li, hi_i, ri = pl[-3], pl[-2], pl[-1]
        ls, head, rs = l[li], l[hi_i], l[ri]
        shld_sim = abs(ls - rs) / ((ls + rs) / 2 + 1e-9)
        if (head <= ls * 0.95 and head <= rs * 0.95 and
                shld_sim <= 0.08 and
                hi_i - li >= 10 and ri - hi_i >= 10):
            neck_h = float(min(max(h[li:hi_i + 1]), max(h[hi_i:ri + 1])))
            if cur > neck_h * 1.002:
                pats['inv_head_shoulders'] = {
                    'head':     round(float(head), 2),
                    'neckline': round(neck_h, 2),
                }

    # ── Cup & Handle ──────────────────────────────────────────────────────────
    # Proper criteria (Minervini / O'Neil):
    # 1. Left rim: prior high in first 40% of lookback
    # 2. Cup depth: 15–45% from left rim
    # 3. Right rim recovered to within 8% of left rim
    # 4. Cup formed over ≥30 bars (smooth U, not V)
    # 5. Handle: 10–30 bar pullback of 3–15% from right rim
    # 6. Handle low above cup midpoint
    if m >= 100:
        rim_end      = m * 40 // 100
        left_rim_idx = int(np.argmax(h[:rim_end]))
        left_rim     = h[left_rim_idx]

        cup_start = left_rim_idx + 5
        cup_end   = m - 15
        if cup_end > cup_start + 25:
            cup_bot_idx = cup_start + int(np.argmin(l[cup_start:cup_end]))
            cup_bot     = l[cup_bot_idx]
            cup_depth   = (left_rim - cup_bot) / (left_rim + 1e-9)

            if 0.15 <= cup_depth <= 0.45:
                right_end     = m - 10
                right_rim_idx = cup_bot_idx + int(np.argmax(h[cup_bot_idx:right_end]))
                right_rim     = h[right_rim_idx]
                recovery      = (right_rim - cup_bot) / (left_rim - cup_bot + 1e-9)
                rim_gap       = abs(left_rim - right_rim) / (left_rim + 1e-9)
                cup_bars      = right_rim_idx - left_rim_idx

                if recovery >= 0.85 and rim_gap <= 0.08 and cup_bars >= 30:
                    handle_h   = h[right_rim_idx:]
                    handle_l   = l[right_rim_idx:]
                    hbars      = len(handle_l)
                    if 5 <= hbars <= 30:
                        h_high  = float(max(handle_h))
                        h_low   = float(min(handle_l))
                        h_depth = (h_high - h_low) / (h_high + 1e-9)
                        cup_mid = cup_bot + (left_rim - cup_bot) * 0.5
                        if 0.03 <= h_depth <= 0.15 and h_low > cup_mid:
                            pats['cup_handle'] = {
                                'cup_depth_pct': round(cup_depth * 100, 1),
                                'recovery_pct':  round(recovery * 100, 1),
                                'left_rim':      round(float(left_rim), 2),
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
