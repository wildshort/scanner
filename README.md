# ASTA Scanner

NSE stock scanner — scores, trendlines, charts, sector heatmap. Runs on your own PC.

## Setup (one time)

**1.** Install Python: **https://www.python.org/downloads/**
  → On the first installer screen, **tick "Add python.exe to PATH"**.

**2.** Double-click **`run.bat`**

That's it. The first run installs everything (2–3 min), then opens
**http://localhost:8888** in your browser by itself.

## Every day after that

Double-click **`run.bat`** → opens in a few seconds.
To stop: close the black window.

---

<details>
<summary>If something goes wrong</summary>

**"Python was not found"** — Python isn't installed, or "Add python.exe to PATH"
wasn't ticked. Re-run the Python installer, tick that box, restart the PC.

**Windows SmartScreen warning** — click *More info* → *Run anyway*. It appears
because the file arrived from a chat app, not because anything is wrong.

**Page doesn't load** — wait for the black window to say `Ready`, then refresh.

**Port already in use** — another copy is running. Close all black windows, retry.

</details>

<details>
<summary>What's inside</summary>

- Nifty 50/100/200/500 + Midcap scans — ASTA score, RSI, ADX, volume ratio
- TradingView-style charts, 5m → monthly, with EMA/BB/Supertrend/MACD/Stochastic/DMI
- RSI divergence detection (daily + 4H), trendlines, momentum, setups, MTF
  confluence, sector heatmap, FII/DII

Data: Yahoo Finance (end-of-day). **No login, no API keys.** Needs internet.

</details>
