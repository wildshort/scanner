import json, math, time, os, numpy as np
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse
import asyncio

app = FastAPI(title="ASTA Scanner")

_cache: dict = {}
_cache_ts: dict = {}
CACHE_TTL = 300
CACHE_TTL_LARGE = 900  # 15 min for 200+ stock scans


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


def _clean(o):
    """Recursively convert numpy scalars to Python types and replace
    non-finite floats (NaN, ±Inf) with None.

    Indicators legitimately produce NaN — warm-up bars of RSI/MACD/ATR, a
    missing P/E, a symbol yfinance returned short. Those must not abort the
    whole response. A JSONEncoder subclass cannot fix this: the json module
    serializes floats in C and never calls default() for them, so NaN survives
    into the payload and Starlette's JSONResponse (which uses allow_nan=False)
    raises "Out of range float values are not JSON compliant". The values have
    to be replaced *before* serialization. null is the right wire value — JSON
    has no NaN, and the UI already renders missing fields as "—".
    """
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, np.floating):
        v = float(o)
        return v if math.isfinite(v) else None
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return [_clean(x) for x in o.tolist()]
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(x) for x in o]
    return o


def _j(data) -> JSONResponse:
    return JSONResponse(content=json.loads(json.dumps(_clean(data), cls=_Enc)))


@app.exception_handler(Exception)
async def _unhandled_exception(request, exc):
    """Return JSON for ANY unhandled error.

    Without this, Starlette answers with the plain-text body "Internal Server
    Error", and the frontend's response.json() then fails with the misleading
    "Unexpected token 'I' ... is not valid JSON" — hiding the real cause. A
    JSON body means the UI can surface the actual error text instead.
    """
    import logging as _log
    _log.getLogger(__name__).error(
        f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": f"{type(exc).__name__}: {exc}",
                 "path": request.url.path},
    )


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


@app.get("/api/symbols")
async def symbols():
    """Return all known symbols with name/sector for autocomplete — no scan needed."""
    from universe import STOCK_META, SECTOR_COLORS
    data = [
        {"symbol": sym, "name": meta[1], "sector": meta[0],
         "sector_color": SECTOR_COLORS.get(meta[0], "#8b949e")}
        for sym, meta in STOCK_META.items()
    ]
    return _j({"symbols": data, "total": len(data)})


@app.get("/api/scan/{market}")
async def scan(market: str, force: bool = False):
    import logging as _log
    from universe import MARKETS
    if market not in MARKETS:
        raise HTTPException(404, f"Unknown market: {market}")
    from universe import MARKETS
    now = time.time()
    ttl = CACHE_TTL_LARGE if len(MARKETS.get(market, {}).get("symbols", [])) > 200 else CACHE_TTL
    if not force and market in _cache and now - _cache_ts.get(market, 0) < ttl:
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
    # Check price alerts against fresh prices
    try:
        from alerts import check_alerts
        check_alerts(data.get("results", []))
    except Exception:
        pass
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


@app.get("/api/setups/{market}")
async def setups(market: str, force: bool = False):
    import logging as _log
    from universe import MARKETS
    if market not in MARKETS:
        raise HTTPException(404, f"Unknown market: {market}")
    key = f"setups_{market}"
    now = time.time()
    if not force and key in _cache and now - _cache_ts.get(key, 0) < CACHE_TTL:
        return _j({**_cache[key], "cached": True})
    loop = asyncio.get_running_loop()
    from pattern_scanner import run_setups_scan
    try:
        data = await loop.run_in_executor(None, lambda: run_setups_scan(market))
    except Exception as e:
        _log.getLogger(__name__).error(f"run_setups_scan({market}) failed: {e}", exc_info=True)
        return _j({"error": str(e)})
    _cache[key] = data
    _cache_ts[key] = now
    return _j({**data, "cached": False, "scanned_at": now})


@app.get("/api/fiidii")
async def fiidii():
    loop = asyncio.get_running_loop()
    from kite_data import get_fii_dii
    data = await loop.run_in_executor(None, get_fii_dii)
    return _j(data)


@app.get("/api/alerts")
async def get_alerts():
    from alerts import get_alerts as _get
    return _j(_get())


@app.post("/api/alerts")
async def add_alert(body: dict = Body(...)):
    from alerts import add_alert as _add
    symbol    = body.get("symbol", "")
    price     = body.get("price", 0)
    condition = body.get("condition", "above")
    note      = body.get("note", "")
    if not symbol or not price:
        raise HTTPException(400, "symbol and price required")
    if condition not in ("above", "below"):
        raise HTTPException(400, "condition must be 'above' or 'below'")
    alert = _add(symbol, float(price), condition, note)
    return _j(alert)


@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int):
    from alerts import delete_alert as _del
    ok = _del(alert_id)
    if not ok:
        raise HTTPException(404, f"Alert {alert_id} not found")
    return _j({"ok": True})


@app.get("/api/confluence/{market}")
async def confluence(market: str, force: bool = False):
    import logging as _log
    from universe import MARKETS
    if market not in MARKETS:
        raise HTTPException(404, f"Unknown market: {market}")
    key = f"conf_{market}"
    now = time.time()
    if not force and key in _cache and now - _cache_ts.get(key, 0) < CACHE_TTL:
        return _j({**_cache[key], "cached": True})
    loop = asyncio.get_running_loop()
    from pattern_scanner import run_confluence_scan
    try:
        data = await loop.run_in_executor(None, lambda: run_confluence_scan(market))
    except Exception as e:
        _log.getLogger(__name__).error(f"run_confluence_scan({market}) failed: {e}", exc_info=True)
        return _j({"error": str(e)})
    _cache[key] = data
    _cache_ts[key] = now
    return _j({**data, "cached": False, "scanned_at": now})


@app.get("/api/intraday/{market}/{interval}")
async def intraday(market: str, interval: str, force: bool = False):
    import logging as _log
    from universe import MARKETS
    valid_intervals = {"5m", "10m", "15m", "30m", "1h"}
    if market not in MARKETS:
        raise HTTPException(404, f"Unknown market: {market}")
    if interval not in valid_intervals:
        raise HTTPException(400, f"Invalid interval: {interval}")
    key = f"intra_{market}_{interval}"
    now = time.time()
    if not force and key in _cache and now - _cache_ts.get(key, 0) < 60:
        return _j({**_cache[key], "cached": True})
    loop = asyncio.get_running_loop()
    from pattern_scanner import run_intraday_scan
    try:
        data = await loop.run_in_executor(None, lambda: run_intraday_scan(market, interval))
    except Exception as e:
        _log.getLogger(__name__).error(f"run_intraday_scan({market}/{interval}) failed: {e}", exc_info=True)
        return _j({"error": str(e)})
    _cache[key] = data
    _cache_ts[key] = now
    return _j({**data, "cached": False, "scanned_at": now})


@app.get("/api/cache/clear")
async def clear():
    _cache.clear(); _cache_ts.clear()
    return _j({"ok": True})


_js_errors: list = []

@app.post("/api/js-error")
async def js_error(body: dict = Body(...)):
    import logging
    _js_errors.append(body)
    logging.getLogger(__name__).error(f"JS ERROR: {body}")
    return _j({"ok": True})

@app.get("/api/js-errors")
async def get_js_errors():
    return _j({"errors": _js_errors})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8888, reload=False)
