"""
Trendline detection and breakout classification.
Ported from ~/kite-trading-bot/trendline.py — standalone, no bot dependencies.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

# Config (mirrored from bot's config.py)
PIVOT_LEFT_BARS   = 5
PIVOT_RIGHT_BARS  = 3
MIN_PIVOTS        = 2
BREAKOUT_BUFFER   = 0.003   # 0.3%
ATR_PERIOD        = 14


@dataclass
class Trendline:
    kind: str
    slope: float
    intercept: float
    pivot_indices: list[int] = field(default_factory=list)
    pivot_prices: list[float] = field(default_factory=list)
    r_squared: float = 0.0

    def price_at(self, idx: int) -> float:
        return self.slope * idx + self.intercept


@dataclass
class BreakoutSignal:
    direction: str       # 'bullish' | 'bearish'
    trendline: Trendline
    entry_price: float
    trendline_level: float
    candle_idx: int
    score: float = 0.0
    category: str = ""   # fresh_breakout | fresh_breakdown | pullback | continuation


def _atr(df: pd.DataFrame, length: int = ATR_PERIOD) -> pd.Series:
    prev = df["close"].shift(1)
    tr = pd.concat([df["high"]-df["low"], (df["high"]-prev).abs(), (df["low"]-prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, min_periods=length).mean()


def find_pivots(df: pd.DataFrame) -> tuple[list[int], list[int]]:
    highs = df["high"].values
    lows  = df["low"].values
    n = len(df)
    ph, pl = [], []
    for i in range(PIVOT_LEFT_BARS, n - PIVOT_RIGHT_BARS):
        win_h = highs[i - PIVOT_LEFT_BARS: i + PIVOT_RIGHT_BARS + 1]
        win_l = lows[i  - PIVOT_LEFT_BARS: i + PIVOT_RIGHT_BARS + 1]
        if highs[i] == np.max(win_h): ph.append(i)
        if lows[i]  == np.min(win_l): pl.append(i)
    return ph, pl


def fit_trendline(indices: list[int], prices: list[float], kind: str) -> Optional[Trendline]:
    if len(indices) < MIN_PIVOTS:
        return None
    x = np.array(indices, dtype=float)
    y = np.array(prices, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return Trendline(kind=kind, slope=slope, intercept=intercept,
                     pivot_indices=list(indices), pivot_prices=list(prices), r_squared=r2)


def detect_trendlines(df: pd.DataFrame) -> tuple[Optional[Trendline], Optional[Trendline]]:
    ph_idx, pl_idx = find_pivots(df)
    resistance = None
    if len(ph_idx) >= MIN_PIVOTS:
        recent = ph_idx[-4:]
        resistance = fit_trendline(recent, [df["high"].iloc[i] for i in recent], "resistance")
    support = None
    if len(pl_idx) >= MIN_PIVOTS:
        recent = pl_idx[-4:]
        support = fit_trendline(recent, [df["low"].iloc[i] for i in recent], "support")
    return resistance, support


def _broke_recently(df: pd.DataFrame, tl: Trendline, direction: str, lookback: int = 3) -> bool:
    n = len(df)
    for i in range(max(1, n - lookback), n):
        curr_level = tl.price_at(i)
        prev_level = tl.price_at(i - 1)
        bar_close  = df["close"].iloc[i]
        prev_close = df["close"].iloc[i - 1]
        if direction == "up":
            if bar_close > curr_level * (1 + BREAKOUT_BUFFER) and prev_close <= prev_level * 1.002:
                return True
        else:
            if bar_close < curr_level * (1 - BREAKOUT_BUFFER) and prev_close >= prev_level * 0.998:
                return True
    return False


def _breakout_score(tl: Trendline, price: float, level: float) -> float:
    r2_score    = tl.r_squared * 40
    touch_score = min(len(tl.pivot_indices), 4) * 10
    magnitude   = abs(price - level) / (level + 1e-9)
    mag_score   = 20.0 if 0.003 <= magnitude <= 0.015 else (10.0 if magnitude < 0.003 else 5.0)
    return round(r2_score + touch_score + mag_score, 1)


def classify_chart(df: pd.DataFrame) -> dict:
    """
    Classify the latest bar vs trendlines.
    Returns: { category, direction, trendline_level, reason, score,
                resistance_points, support_points, resistance_slope, support_slope }
    """
    if len(df) < 30:
        return {"category": "no_structure", "direction": None, "reason": "Insufficient data"}

    resistance, support = detect_trendlines(df)
    atr_val = float(_atr(df).iloc[-1])
    current_idx   = len(df) - 1
    current_close = df["close"].iloc[-1]
    prev_close    = df["close"].iloc[-2] if len(df) > 1 else current_close

    result = {
        "category": "no_structure",
        "direction": None,
        "trendline_level": None,
        "reason": "No qualifying trendline",
        "score": 0.0,
        "resistance": _tl_to_dict(resistance, df) if resistance else None,
        "support":    _tl_to_dict(support,    df) if support    else None,
    }

    # ── Bullish breakout / pullback ─────────────────────────────────────────
    if resistance:
        res_level  = resistance.price_at(current_idx)
        threshold  = res_level * (1 + BREAKOUT_BUFFER)
        prev_level = resistance.price_at(current_idx - 1)

        if current_close > threshold and prev_close <= prev_level * 1.002:
            score = _breakout_score(resistance, current_close, res_level)
            result.update({"category": "fresh_breakout", "direction": "bullish",
                "trendline_level": round(res_level, 2),
                "reason": f"Broke resistance ₹{res_level:.1f} (R²={resistance.r_squared:.2f})",
                "score": score})
        elif _broke_recently(df, resistance, "up", lookback=4):
            score = _breakout_score(resistance, current_close, res_level)
            result.update({"category": "fresh_breakout", "direction": "bullish",
                "trendline_level": round(res_level, 2),
                "reason": f"Recent breakout above ₹{res_level:.1f}",
                "score": score})
        elif current_close < res_level and abs(current_close - res_level) <= 1.5 * atr_val:
            result.update({"category": "pullback", "direction": "bullish",
                "trendline_level": round(res_level, 2),
                "reason": f"Pulling back to resistance ₹{res_level:.1f}",
                "score": _breakout_score(resistance, current_close, res_level) * 0.6})

    # ── Bearish breakdown / pullback ────────────────────────────────────────
    if support:
        sup_level  = support.price_at(current_idx)
        threshold  = sup_level * (1 - BREAKOUT_BUFFER)
        prev_level = support.price_at(current_idx - 1)

        if current_close < threshold and prev_close >= prev_level * 0.998:
            score = _breakout_score(support, current_close, sup_level)
            result.update({"category": "fresh_breakdown", "direction": "bearish",
                "trendline_level": round(sup_level, 2),
                "reason": f"Broke support ₹{sup_level:.1f} (R²={support.r_squared:.2f})",
                "score": score})
        elif _broke_recently(df, support, "down", lookback=4):
            score = _breakout_score(support, current_close, sup_level)
            if result["category"] == "no_structure":
                result.update({"category": "fresh_breakdown", "direction": "bearish",
                    "trendline_level": round(sup_level, 2),
                    "reason": f"Recent breakdown below ₹{sup_level:.1f}",
                    "score": score})
        elif current_close > sup_level and abs(current_close - sup_level) <= 1.5 * atr_val:
            if result["category"] not in ("fresh_breakout", "fresh_breakdown"):
                result.update({"category": "pullback", "direction": "bearish",
                    "trendline_level": round(sup_level, 2),
                    "reason": f"Pulling back to support ₹{sup_level:.1f}",
                    "score": _breakout_score(support, current_close, sup_level) * 0.6})

    return result


def _tl_to_dict(tl: Trendline, df: pd.DataFrame) -> dict:
    """Serialize trendline for JSON + chart rendering."""
    n = len(df)
    points = []
    for idx in tl.pivot_indices:
        if 0 <= idx < n:
            points.append({
                "x": idx,
                "y": round(float(tl.pivot_prices[tl.pivot_indices.index(idx)]), 2),
                "date": str(df.index[idx].date()) if hasattr(df.index[idx], 'date') else str(df.index[idx])[:10],
            })

    # Pre-compute one price per bar using Unix timestamps (matches scanner_engine ohlc format)
    first_pivot = min(tl.pivot_indices) if tl.pivot_indices else 0
    line_data = []
    for i, ts in enumerate(df.index):
        if i < first_pivot:
            continue
        ts_int = int(pd.Timestamp(ts).timestamp())
        line_data.append({"time": ts_int, "value": round(float(tl.price_at(i)), 2)})

    return {
        "kind":          tl.kind,
        "slope":         round(float(tl.slope), 6),
        "intercept":     round(float(tl.intercept), 4),
        "r_squared":     round(float(tl.r_squared), 3),
        "touches":       len(tl.pivot_indices),
        "points":        points,
        "current_level": round(float(tl.price_at(n - 1)), 2),
        "line_data":     line_data,
    }
