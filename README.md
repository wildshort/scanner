# ASTA Scanner

NSE stock scanner with trendline detection, multi-timeframe charts, and sector heatmap.

## How to Run on Windows

### Step 1 — Install Docker Desktop
1. Go to **https://www.docker.com/products/docker-desktop**
2. Click **Download for Windows**
3. Run the installer — keep all default settings
4. Restart your PC when prompted
5. Launch Docker Desktop from the Start menu and wait for it to finish starting (whale icon in taskbar)

> Requires Windows 10/11 (64-bit). If asked about WSL2, click Install.

### Step 2 — Start the scanner
Double-click **`START.bat`**

First launch downloads ~500MB (Python + libraries). Takes 3-5 minutes.
After that, starts in seconds.

### Step 3 — Open your browser
Go to **http://localhost:8888**

The browser should open automatically. If not, type the address above manually.

---

### To stop the scanner
Double-click **`STOP.bat`**

---

## Alternative — run without Docker

If you can't install Docker, install **Python 3.11+** from https://python.org
(tick **"Add python.exe to PATH"** during install), then double-click **`run.bat`**.
First run installs dependencies (1-2 minutes); the browser opens automatically.
Stop with **Ctrl+C** in the black window.

---

## Features

- Nifty 50/100/200/500 + Midcap scans with ASTA score, RSI, ADX, volume ratio
- TradingView-style charts: 5m → monthly, EMA/BB/Supertrend/MACD/Stochastic/DMI
- **RSI divergence detection** (daily + 4H) — drawn on the chart with Bull/Bear markers
- RSI overlay band inside the price chart, always aligned with candles
- Trendline detection, momentum scan, setups, MTF confluence, sector heatmap, FII/DII

**Note:** Uses Yahoo Finance for market data (end-of-day). No login or API keys
needed. Internet connection required.
