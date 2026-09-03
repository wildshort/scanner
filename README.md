# ASTA Scanner

NSE stock scanner — scores, trendlines, charts, sector heatmap. Runs on your own machine.

## Mac

**1.** Double-click **`run.command`**

That's it. First run installs everything (2–3 min), then opens
**http://localhost:8888** by itself. After that it starts in ~1 second.

> If macOS says *"cannot be opened because it is from an unidentified developer"* —
> **right-click `run.command` → Open → Open**. Only needed the first time.
>
> If it says Python is missing, run `xcode-select --install` in Terminal, then
> double-click again.

## Windows

**1.** Install Python: **https://www.python.org/downloads/**
  → On the first installer screen, **tick "Add python.exe to PATH"**.

**2.** Double-click **`run.bat`**

First run installs everything (2–3 min), then opens **http://localhost:8888** by itself.

---

**To stop (either platform):** close the black/Terminal window.

---

<details>
<summary>Getting updates</summary>

Download the latest ZIP again from the repo (**Code → Download ZIP**) and replace
your folder — or, if you have git:

```
git pull
```

Your `venv` folder is reused, so updates start instantly.

</details>

<details>
<summary>If something goes wrong</summary>

**Port already in use** — another copy is running. Close all Terminal/black windows
and retry. Or run it on a different port:
`ASTA_PORT=8899 ./run.command` (Mac).

**Page doesn't load** — wait for the window to say `Ready`, then refresh.

**Windows: "Python was not found"** — Python isn't installed, or "Add python.exe to
PATH" wasn't ticked. Re-run the installer, tick that box, restart the PC.

**Windows SmartScreen warning** — *More info* → *Run anyway*.

</details>

<details>
<summary>What's inside</summary>

- Nifty 50/100/200/500 + Midcap scans — ASTA score, RSI, ADX, volume ratio
- TradingView-style charts, 5m → monthly, with EMA/BB/Supertrend/MACD/Stochastic/DMI
- RSI divergence detection (daily + 4H), trendlines, momentum, setups, MTF
  confluence, sector heatmap, FII/DII

Data: Yahoo Finance (end-of-day). **No login, no API keys.** Needs internet.

Run the tests with `venv/bin/python -m pytest tests/ -q` (Mac) or
`venv\Scripts\python -m pytest tests\ -q` (Windows).

</details>
