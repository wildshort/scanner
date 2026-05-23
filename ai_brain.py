"""AI brain for ASTA Scanner — uses claude CLI subprocess."""
import subprocess, shutil, json

CLAUDE_BIN = shutil.which("claude") or "/Users/admin/.local/bin/claude"

SYSTEM = """You are an expert Indian stock market trading coach integrated into the ASTA Scanner dashboard.
You have access to real-time NSE/BSE data from Kite Connect.

Help traders with:
- Reading ASTA scan results (RSI, MACD, ADX, Volume, EMA alignment, Bollinger Bands)
- Multi-timeframe bias (Monthly/Weekly/Daily/4H)
- Price action: structure, HH/HL, BOS, CHoCH, supply/demand, FVG
- Options strategies (CE/PE) for F&O stocks
- Entry, stop-loss, targets with R:R ratios
- Risk management for Indian equity and derivatives

Style: concise bullets, actionable, use ₹ for prices. Reference specific numbers from the scan data when provided."""


def _run(prompt: str, timeout: int = 60) -> str:
    result = subprocess.run(
        [CLAUDE_BIN, "-p", prompt],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip() or "claude CLI error"
        if any(w in err.lower() for w in ("limit", "quota", "rate", "billing", "credits")):
            raise RuntimeError("Claude usage limit reached — wait a few minutes and try again")
        raise RuntimeError(err[:200])
    return result.stdout.strip()


def chat(message: str, symbol: str, scan_row: dict | None, history: list) -> str:
    parts = [SYSTEM, ""]

    if symbol and scan_row:
        parts.append(f"Current stock: NSE:{symbol}")
        parts.append(f"  Price: ₹{scan_row.get('price', '?')}  Change: {scan_row.get('change_pct', '?')}%")
        parts.append(f"  ASTA Score: {scan_row.get('score', '?')}  RSI: {scan_row.get('rsi', '?')}")
        parts.append(f"  Vol Ratio: {scan_row.get('vol_ratio', '?')}x  ADX: {scan_row.get('adx', '?')}")
        parts.append(f"  EMA aligned: {scan_row.get('ema_aligned', '?')}  Above EMA50: {scan_row.get('above_ema50', '?')}")
        parts.append(f"  MACD bullish: {scan_row.get('macd_bullish', '?')}  HA bullish: {scan_row.get('ha_bullish', '?')}")
        if scan_row.get('tl_category') and scan_row['tl_category'] != 'no_structure':
            parts.append(f"  Trendline: {scan_row.get('tl_category')} at ₹{scan_row.get('tl_level','?')}")
        parts.append(f"  Sector: {scan_row.get('sector', '?')}  F&O: {scan_row.get('fo', '?')}")

    if history:
        parts.append("\nRecent conversation:")
        for h in history[-4:]:
            role = "Trader" if h["role"] == "user" else "Coach"
            parts.append(f"{role}: {h['content']}")

    parts.append(f"\nTrader: {message}")
    parts.append("Coach:")

    return _run("\n".join(parts))
