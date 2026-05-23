import json, time, os, numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import asyncio

app = FastAPI(title="ASTA Scanner")

_cache: dict = {}
_cache_ts: dict = {}
CACHE_TTL = 300


@app.on_event("startup")
async def startup_event():
    """Pre-warm nifty50 cache on start so dashboard loads instantly."""
    async def _warm():
        try:
            from scanner_engine import run_scan
            loop = asyncio.get_running_loop()
            data = await loop.run_in_executor(None, lambda: run_scan("nifty50"))
            _cache["nifty50"] = data
            _cache_ts["nifty50"] = time.time()
            import logging
            logging.getLogger(__name__).info("nifty50 cache warmed")
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Cache warm failed: {e}")
    asyncio.create_task(_warm())


# ── JSON encoder ───────────────────────────────────────────────────────────────
class _Enc(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (np.integer,)): return int(o)
        if isinstance(o, (np.floating,)): return float(o)
        if isinstance(o, (np.bool_,)):   return bool(o)
        if isinstance(o, np.ndarray):    return o.tolist()
        return super().default(o)

def _j(data) -> JSONResponse:
    return JSONResponse(content=json.loads(json.dumps(data, cls=_Enc)))


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    from fastapi.responses import Response
    path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(path) as f:
        html = f.read()

    # Embed cached scan data so the page renders instantly with zero JS fetch
    initial_data = _cache.get("nifty50", {})
    data_script = f'<script>window.__INITIAL_SCAN__={json.dumps(initial_data, default=str)};</script>'
    html = html.replace('</head>', data_script + '\n</head>')

    return Response(content=html, media_type="text/html",
                    headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


@app.get("/api/status")
async def status():
    from kite_data import get_status
    return _j(get_status())


@app.get("/api/markets")
async def markets():
    from universe import MARKETS
    return _j({k: {"name": v["name"], "count": len(v["symbols"])} for k, v in MARKETS.items()})


@app.get("/api/scan/{market}")
async def scan(market: str, force: bool = False):
    import logging as _log
    from universe import MARKETS
    if market not in MARKETS:
        raise HTTPException(404, f"Unknown market: {market}")
    now = time.time()
    if not force and market in _cache and now - _cache_ts.get(market, 0) < CACHE_TTL:
        return _j({**_cache[market], "cached": True, "scanned_at": _cache_ts[market]})
    loop = asyncio.get_running_loop()
    from scanner_engine import run_scan
    try:
        data = await loop.run_in_executor(None, lambda: run_scan(market))
    except Exception as e:
        _log.getLogger(__name__).error(f"run_scan({market}) failed: {e}", exc_info=True)
        return _j({"error": str(e), "results": [], "sectors": [], "total": 0})
    _cache[market] = data
    _cache_ts[market] = now
    return _j({**data, "cached": False, "scanned_at": now, "market": market})


@app.get("/api/trendlines/{market}")
async def trendlines(market: str, force: bool = False):
    import logging as _log
    from universe import MARKETS
    if market not in MARKETS:
        raise HTTPException(404, f"Unknown market: {market}")
    key = f"tl_{market}"
    now = time.time()
    if not force and key in _cache and now - _cache_ts.get(key, 0) < CACHE_TTL:
        return _j({**_cache[key], "cached": True})
    loop = asyncio.get_running_loop()
    from scanner_engine import run_trendline_scan
    try:
        data = await loop.run_in_executor(None, lambda: run_trendline_scan(market))
    except Exception as e:
        _log.getLogger(__name__).error(f"run_trendline_scan({market}) failed: {e}", exc_info=True)
        return _j({"error": str(e), "breakouts": [], "breakdowns": [], "pullbacks": []})
    _cache[key] = data
    _cache_ts[key] = now
    return _j({**data, "cached": False, "scanned_at": now})


@app.get("/api/stock/{symbol}")
async def stock(symbol: str):
    loop = asyncio.get_running_loop()
    from scanner_engine import analyze_symbol
    result = await loop.run_in_executor(None, lambda: analyze_symbol(symbol, include_chart=True))
    if not result:
        raise HTTPException(404, f"No data for {symbol}")
    return _j(result)


@app.get("/api/chart/{symbol}/{interval}")
async def chart(symbol: str, interval: str):
    valid = {"5m","10m","15m","30m","1h","4h","1d","1w","1mo"}
    if interval not in valid:
        raise HTTPException(400, f"Invalid interval: {interval}")
    key = f"chart_{symbol}_{interval}"
    now = time.time()
    ttl = 60 if interval in ("5m","10m","15m","30m") else 300
    if key in _cache and now - _cache_ts.get(key, 0) < ttl:
        return _j({**_cache[key], "cached": True})
    loop = asyncio.get_running_loop()
    from scanner_engine import fetch_chart_data
    data = await loop.run_in_executor(None, lambda: fetch_chart_data(symbol, interval))
    if not data:
        raise HTTPException(404, f"No chart data for {symbol}/{interval}")
    _cache[key] = data
    _cache_ts[key] = now
    return _j({**data, "cached": False})


@app.get("/api/sectors/{market}")
async def sectors(market: str):
    key = f"sec_{market}"
    now = time.time()
    if key in _cache and now - _cache_ts.get(key, 0) < CACHE_TTL:
        return _j(_cache[key])
    if market in _cache:
        data = {"sectors": _cache[market].get("sectors", [])}
        return _j(data)
    raise HTTPException(400, "Run a scan first")


@app.get("/api/momentum/{market}")
async def momentum(market: str, force: bool = False):
    from universe import MARKETS
    if market not in MARKETS:
        raise HTTPException(404, f"Unknown market: {market}")
    key = f"mom_{market}"
    now = time.time()
    if not force and key in _cache and now - _cache_ts.get(key, 0) < CACHE_TTL:
        return _j({**_cache[key], "cached": True})
    loop = asyncio.get_running_loop()
    from momentum_scanner import run_momentum_scan
    data = await loop.run_in_executor(None, lambda: run_momentum_scan(market))
    _cache[key] = data
    _cache_ts[key] = now
    return _j({**data, "cached": False, "scanned_at": now})


@app.get("/api/fiidii")
async def fiidii():
    loop = asyncio.get_running_loop()
    from kite_data import get_fii_dii
    data = await loop.run_in_executor(None, get_fii_dii)
    return _j(data)


@app.get("/api/cache/clear")
async def clear():
    _cache.clear(); _cache_ts.clear()
    return _j({"ok": True})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8888, reload=False)
