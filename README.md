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

**Note:** Uses Yahoo Finance for market data (end-of-day). No login or API keys needed.
