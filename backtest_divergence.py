"""
Backtest RSI divergence signals (as implemented in scanner_engine.detect_rsi_divergence).

Walk-forward safe: a signal is only "tradeable" at its confirmation bar
(2nd pivot + right-window), which is exactly what detect_rsi_divergence reports
in `confirmed_t`. Entry = close of the confirmation bar. Forward returns are
measured 5/10/20 bars later and compared against the buy-anytime baseline.

Usage:
    python3 backtest_divergence.py            # daily, Nifty 50
    python3 backtest_divergence.py 4h         # 4-hour bars (last ~60 days)
"""
import sys
import time
import numpy as np
import pandas as pd

import kite_data
from universe import MARKETS
from scanner_engine import _rsi, detect_rsi_divergence

HORIZONS = (5, 10, 20)


def collect_signals(df: pd.DataFrame, rsi_s: pd.Series) -> list[dict]:
    divs = detect_rsi_divergence(df, rsi_s, lookback=len(df), max_out=10_000)
    times = [int(pd.Timestamp(i).timestamp()) for i in df.index]
    pos = {t: i for i, t in enumerate(times)}
    out = []
    for dv in divs:
        i = pos.get(dv["confirmed_t"])
        if i is None:
            continue
        row = {"type": dv["type"], "entry_i": i}
        for h in HORIZONS:
            if i + h < len(df):
                row[h] = float(df["close"].iloc[i + h] / df["close"].iloc[i] - 1)
        out.append(row)
    return out


def main(interval: str = "1d"):
    symbols = MARKETS["nifty50"]["symbols"]
    signals, baseline = [], {h: [] for h in HORIZONS}
    for n, sym in enumerate(symbols, 1):
        try:
            df = kite_data.get_ohlcv_interval(sym, interval)
            if df is None or len(df) < 60:
                continue
            df.columns = [c.lower() for c in df.columns]
            signals += collect_signals(df, _rsi(df["close"]))
            c = df["close"]
            for h in HORIZONS:
                baseline[h] += list((c.shift(-h) / c - 1).dropna())
        except Exception as e:
            print(f"  ! {sym}: {e}")
        if n % 10 == 0:
            print(f"  …{n}/{len(symbols)} symbols")
        time.sleep(0.2)  # be gentle with yahoo

    print(f"\n═══ RSI divergence backtest — Nifty 50, {interval} bars ═══")
    print(f"symbols: {len(symbols)}   signals: {len(signals)} "
          f"(bull {sum(s['type']=='bullish' for s in signals)}, "
          f"bear {sum(s['type']=='bearish' for s in signals)})\n")
    hdr = f"{'signal':8} {'N':>4} " + "".join(f"{f'+{h} win%':>9}{f'+{h} avg%':>9}" for h in HORIZONS)
    print(hdr); print("─" * len(hdr))
    for typ, sign in (("bullish", 1), ("bearish", -1)):
        rows = [s for s in signals if s["type"] == typ]
        line = f"{typ:8} {len(rows):>4} "
        for h in HORIZONS:
            r = np.array([s[h] for s in rows if h in s])
            if len(r):
                win = (sign * r > 0).mean() * 100
                line += f"{win:>8.1f}%{r.mean()*100:>8.2f}%"
            else:
                line += f"{'—':>9}{'—':>9}"
        print(line)
    line = f"{'baseline':8} {'':>4} "
    for h in HORIZONS:
        b = np.array(baseline[h])
        line += f"{(b > 0).mean()*100:>8.1f}%{b.mean()*100:>8.2f}%"
    print(line)
    print("\nbaseline = every bar, long. bullish win = price up after N bars; "
          "bearish win = price down after N bars.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "1d")
