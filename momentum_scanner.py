"""
ASTA Momentum Trader Setup scanner.
Tide = Daily timeframe, Wave = Weekly timeframe.

BB Buy/Sell: Bollinger Band Challenge + Trendline Breakout/Breakdown.
Mandatory (all 5 required) + Optional (up to 6 additional signals).
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Re-use helpers from scanner_engine
from scanner_engine import _rsi, _macd, _bb, _adx


def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


def _above_avg_vol(vol: pd.Series, n: int = 20, mult: float = 1.0) -> bool:
    if len(vol) < n + 1:
        return False
    avg = float(vol.iloc[-(n + 1):-1].mean())
    cur = float(vol.iloc[-1])
    return avg > 0 and cur >= avg * mult


def _has_higher_lows(lows: pd.Series, n: int = 7) -> bool:
    """At least 2 higher lows in last n bars."""
    vals = lows.iloc[-n:].values
    count = sum(1 for i in range(1, len(vals)) if vals[i] > vals[i - 1])
    return count >= 2


def _has_lower_highs(highs: pd.Series, n: int = 7) -> bool:
    """At least 2 lower highs in last n bars."""
    vals = highs.iloc[-n:].values
    count = sum(1 for i in range(1, len(vals)) if vals[i] < vals[i - 1])
    return count >= 2


def _ema_crossed_bull(fast: pd.Series, slow: pd.Series, lookback: int = 3) -> bool:
    """EMA fast crossed above slow within last `lookback` bars."""
    f, s = fast.values, slow.values
    for i in range(len(f) - lookback, len(f)):
        if i < 1:
            continue
        if f[i - 1] <= s[i - 1] and f[i] > s[i]:
            return True
    return False


def _ema_crossed_bear(fast: pd.Series, slow: pd.Series, lookback: int = 3) -> bool:
    """EMA fast crossed below slow within last `lookback` bars."""
    f, s = fast.values, slow.values
    for i in range(len(f) - lookback, len(f)):
        if i < 1:
            continue
        if f[i - 1] >= s[i - 1] and f[i] < s[i]:
            return True
    return False


def _di_pco(pdi: pd.Series, ndi: pd.Series, lookback: int = 3) -> bool:
    """+DI crossed above -DI within last `lookback` bars."""
    p, n = pdi.values, ndi.values
    for i in range(len(p) - lookback, len(p)):
        if i < 1:
            continue
        if p[i - 1] <= n[i - 1] and p[i] > n[i]:
            return True
    return False


def _di_nco(pdi: pd.Series, ndi: pd.Series, lookback: int = 3) -> bool:
    """+DI crossed below -DI within last `lookback` bars."""
    p, n = pdi.values, ndi.values
    for i in range(len(p) - lookback, len(p)):
        if i < 1:
            continue
        if p[i - 1] >= n[i - 1] and p[i] < n[i]:
            return True
    return False


def _adx_hook(adx: pd.Series, lookback: int = 4) -> bool:
    """ADX 'Ungli': was declining then turned up (V-shape hook)."""
    vals = adx.dropna().values
    if len(vals) < lookback + 1:
        return False
    seg = vals[-(lookback + 1):]
    min_i = int(np.argmin(seg[:-1]))
    # Hook: min somewhere in middle, last value above min and above the bar before min
    return min_i > 0 and float(seg[-1]) > float(seg[min_i]) and float(seg[min_i]) < float(seg[0])


def _sobbo(close: pd.Series, low: pd.Series, bb_lower: pd.Series, n: int = 5) -> bool:
    """Shake Out Before Breakout: candle wick below lower BB but closed above it."""
    for i in range(-n, 0):
        try:
            if float(low.iloc[i]) < float(bb_lower.iloc[i]) and float(close.iloc[i]) > float(bb_lower.iloc[i]):
                return True
        except Exception:
            pass
    return False


def _sobbd(close: pd.Series, high: pd.Series, bb_upper: pd.Series, n: int = 5) -> bool:
    """Shake Out Before Breakdown: candle wick above upper BB but closed below it."""
    for i in range(-n, 0):
        try:
            if float(high.iloc[i]) > float(bb_upper.iloc[i]) and float(close.iloc[i]) < float(bb_upper.iloc[i]):
                return True
        except Exception:
            pass
    return False


def analyze_momentum(symbol: str) -> dict | None:
    try:
        import kite_data
        from trendline_engine import classify_chart
        from universe import STOCK_META

        # ── Fetch data ──────────────────────────────────────────────────────────
        df_d = kite_data.get_ohlcv(symbol, days=400)          # Daily (Tide)
        df_w = kite_data.get_ohlcv_interval(symbol, '1w')     # Weekly (Wave)

        if df_d is None or len(df_d) < 50:
            return None
        if df_w is None or len(df_w) < 30:
            return None

        df_d.columns = [c.lower() for c in df_d.columns]
        df_w.columns = [c.lower() for c in df_w.columns]

        # ── Daily (Tide) indicators ─────────────────────────────────────────────
        dc = df_d['close']; dh = df_d['high']; dl = df_d['low']; dv = df_d['volume']
        d_bb_u, d_bb_m, d_bb_l = _bb(dc)
        _, __, d_hist = _macd(dc)
        d_rsi_s = _rsi(dc)
        d_adx_s, d_pdi_s, d_ndi_s = _adx(dh, dl, dc)

        d_price   = float(dc.iloc[-1])
        d_prev    = float(dc.iloc[-2]) if len(dc) > 1 else d_price
        d_rsi     = float(d_rsi_s.iloc[-1])
        d_hist_c  = float(d_hist.iloc[-1])
        d_hist_p  = float(d_hist.iloc[-2]) if len(d_hist) > 1 else 0.0
        d_bb_mid  = float(d_bb_m.iloc[-1])
        d_bb_top  = float(d_bb_u.iloc[-1])
        d_bb_bot  = float(d_bb_l.iloc[-1])
        d_change  = round((d_price - d_prev) / d_prev * 100, 2) if d_prev else 0.0

        # ── Weekly (Wave) indicators ────────────────────────────────────────────
        wc = df_w['close']; wh = df_w['high']; wl = df_w['low']; wv = df_w['volume']
        w_bb_u, w_bb_m, w_bb_l = _bb(wc)
        w_rsi_s = _rsi(wc)
        w_adx_s, w_pdi_s, w_ndi_s = _adx(wh, wl, wc)
        w_ema5  = _ema(wc, 5)
        w_ema13 = _ema(wc, 13)
        w_ema26 = _ema(wc, 26)
        w_ema50 = _ema(wc, 50)

        w_price    = float(wc.iloc[-1])
        w_rsi      = float(w_rsi_s.iloc[-1])
        w_adx      = float(w_adx_s.iloc[-1]) if not pd.isna(w_adx_s.iloc[-1]) else 0.0
        w_pdi      = float(w_pdi_s.iloc[-1]) if not pd.isna(w_pdi_s.iloc[-1]) else 0.0
        w_ndi      = float(w_ndi_s.iloc[-1]) if not pd.isna(w_ndi_s.iloc[-1]) else 0.0
        w_bb_mid   = float(w_bb_m.iloc[-1])
        w_ema50_v  = float(w_ema50.iloc[-1])

        # ── Weekly trendline ────────────────────────────────────────────────────
        w_tl = classify_chart(df_w[['open', 'high', 'low', 'close', 'volume']].copy())
        w_tl_cat = w_tl.get('category', 'no_structure')

        # ── BUY conditions ──────────────────────────────────────────────────────
        # Mandatory
        b_tide_bbuc     = d_price >= d_bb_mid                           # Tide: price in upper half
        b_tide_ti_up    = d_hist_c > d_hist_p                          # Tide: MACD hist rising (TI uptick)
        b_rsi_50        = d_rsi > 50 and w_rsi > 50                   # Both RSI > 50
        b_wave_bbuc_tl  = (w_price >= w_bb_mid) and (w_tl_cat in ('fresh_breakout',))  # Wave: upper half + TL breakout
        b_wave_vol      = _above_avg_vol(wv, n=20, mult=1.0)           # Wave: above avg volume

        buy_m_met = sum([b_tide_bbuc, b_tide_ti_up, b_rsi_50, b_wave_bbuc_tl, b_wave_vol])
        buy_qual  = buy_m_met == 5

        # Optional
        b_higher_lows   = _has_higher_lows(wl, n=7)
        b_ema_cross     = _ema_crossed_bull(w_ema5, w_ema13, 3) or _ema_crossed_bull(w_ema5, w_ema26, 3)
        b_di_pco        = _di_pco(w_pdi_s, w_ndi_s, 3)
        b_adx_ok        = _adx_hook(w_adx_s) or w_adx >= 15
        b_above_ema50   = w_price > w_ema50_v
        b_sobbo         = _sobbo(wc, wl, w_bb_l, n=5)

        buy_o_met = sum([b_higher_lows, b_ema_cross, b_di_pco, b_adx_ok, b_above_ema50, b_sobbo])

        # ── SELL conditions ─────────────────────────────────────────────────────
        # Mandatory
        s_tide_bbdc     = d_price <= d_bb_mid                           # Tide: price in lower half
        s_tide_ti_down  = d_hist_c < d_hist_p                          # Tide: MACD hist falling (TI downtick)
        s_rsi_50        = d_rsi < 50 and w_rsi < 50                   # Both RSI < 50
        s_wave_bbdc_tl  = (w_price <= w_bb_mid) and (w_tl_cat in ('fresh_breakdown',))  # Wave: lower half + TL breakdown
        s_wave_vol      = _above_avg_vol(wv, n=20, mult=1.0)           # Wave: above avg volume

        sell_m_met = sum([s_tide_bbdc, s_tide_ti_down, s_rsi_50, s_wave_bbdc_tl, s_wave_vol])
        sell_qual  = sell_m_met == 5

        # Optional
        s_lower_highs   = _has_lower_highs(wh, n=7)
        s_ema_cross     = _ema_crossed_bear(w_ema5, w_ema13, 3) or _ema_crossed_bear(w_ema5, w_ema26, 3)
        s_di_nco        = _di_nco(w_pdi_s, w_ndi_s, 3)
        s_adx_ok        = _adx_hook(w_adx_s) or w_adx >= 15
        s_below_ema50   = w_price < w_ema50_v
        s_sobbd         = _sobbd(wc, wh, w_bb_u, n=5)

        sell_o_met = sum([s_lower_highs, s_ema_cross, s_di_nco, s_adx_ok, s_below_ema50, s_sobbd])

        # ── Signal & Score ──────────────────────────────────────────────────────
        if buy_qual:
            signal = 'buy'
            score  = 50 + buy_o_met * 8
        elif sell_qual:
            signal = 'sell'
            score  = 50 + sell_o_met * 8
        else:
            signal = None
            score  = max(buy_m_met, sell_m_met) * 9  # partial

        meta = STOCK_META.get(symbol, ('Other', symbol))
        sector, name = meta[0], meta[1]
        from universe import KNOWN_FO
        fo = symbol in KNOWN_FO

        return {
            'symbol':     symbol,
            'name':       name,
            'sector':     sector,
            'fo':         fo,
            'signal':     signal,
            'score':      score,
            'price':      round(d_price, 2),
            'change_pct': d_change,
            'd_rsi':      round(d_rsi, 1),
            'w_rsi':      round(w_rsi, 1),
            'w_adx':      round(w_adx, 1),
            'w_pdi':      round(w_pdi, 1),
            'w_ndi':      round(w_ndi, 1),
            'w_tl_cat':   w_tl_cat,
            # Detailed conditions for display
            'buy': {
                'mandatory': {
                    'tide_bbuc':    b_tide_bbuc,
                    'tide_ti_up':   b_tide_ti_up,
                    'rsi_above_50': b_rsi_50,
                    'wave_bb_tl':   b_wave_bbuc_tl,
                    'wave_vol':     b_wave_vol,
                },
                'optional': {
                    'higher_lows':  b_higher_lows,
                    'ema_cross':    b_ema_cross,
                    'di_pco':       b_di_pco,
                    'adx_hook':     b_adx_ok,
                    'above_ema50':  b_above_ema50,
                    'sobbo':        b_sobbo,
                },
                'mandatory_met': buy_m_met,
                'optional_met':  buy_o_met,
                'qualified':     buy_qual,
            },
            'sell': {
                'mandatory': {
                    'tide_bbdc':     s_tide_bbdc,
                    'tide_ti_down':  s_tide_ti_down,
                    'rsi_below_50':  s_rsi_50,
                    'wave_bb_tl':    s_wave_bbdc_tl,
                    'wave_vol':      s_wave_vol,
                },
                'optional': {
                    'lower_highs':  s_lower_highs,
                    'ema_cross':    s_ema_cross,
                    'di_nco':       s_di_nco,
                    'adx_hook':     s_adx_ok,
                    'below_ema50':  s_below_ema50,
                    'sobbd':        s_sobbd,
                },
                'mandatory_met': sell_m_met,
                'optional_met':  sell_o_met,
                'qualified':     sell_qual,
            },
        }

    except Exception as e:
        logger.warning(f"momentum analyze failed [{symbol}]: {e}")
        return None


def run_momentum_scan(market: str = 'nifty50', max_workers: int = 6) -> dict:
    from universe import MARKETS
    symbols = MARKETS.get(market, MARKETS['nifty50'])['symbols']

    buys, sells, watch = [], [], []

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(analyze_momentum, sym): sym for sym in symbols}
        for fut in as_completed(futures):
            r = fut.result()
            if not r:
                continue
            if r['signal'] == 'buy':
                buys.append(r)
            elif r['signal'] == 'sell':
                sells.append(r)
            else:
                # Near-miss: 3 or 4 mandatory conditions met on either side
                if r['buy']['mandatory_met'] >= 3 or r['sell']['mandatory_met'] >= 3:
                    watch.append(r)

    buys.sort(key=lambda x: x['score'], reverse=True)
    sells.sort(key=lambda x: x['score'], reverse=True)
    watch.sort(key=lambda x: max(x['buy']['mandatory_met'], x['sell']['mandatory_met']), reverse=True)

    return {'buys': buys, 'sells': sells, 'watch': watch}
