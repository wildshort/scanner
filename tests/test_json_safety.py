"""
Tests for the JSON response layer (app._clean / app._j) and the global
exception handler.

Regression covered
------------------
Every API route once returned HTTP 500 with the plain-text body "Internal
Server Error", which the frontend surfaced as:

    Scan failed: Unexpected token 'I', "Internal S"... is not valid JSON

Cause: indicator NaNs (RSI/MACD/ATR warm-up bars, missing P/E, short history)
reached Starlette's JSONResponse, which serializes with allow_nan=False and
raises "Out of range float values are not JSON compliant: nan".

The decisive assertion in these tests is therefore not "NaN became None" but
`json.dumps(cleaned, allow_nan=False)` succeeding — that is exactly what
Starlette does internally, so it is what actually has to hold.

Importing app is network-free: scanner_engine and yfinance are imported lazily
inside the route handlers, and TestClient without a context manager does not
run the startup cache-warm event.
"""
import json
import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import _clean, _j, app


def strict(obj) -> str:
    """Serialize the way Starlette's JSONResponse does (allow_nan=False)."""
    return json.dumps(obj, allow_nan=False)


# ── _clean: non-finite floats ────────────────────────────────────────────────

@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_floats_become_none(value):
    assert _clean(value) is None


@pytest.mark.parametrize("value", [
    np.float64("nan"), np.float32("nan"),
    np.float64("inf"), np.float64("-inf"),
])
def test_non_finite_numpy_floats_become_none(value):
    assert _clean(value) is None


def test_finite_values_pass_through_unchanged():
    assert _clean(61.2) == 61.2
    assert _clean(0.0) == 0.0
    assert _clean(-17.5) == -17.5
    assert _clean("RELIANCE") == "RELIANCE"
    assert _clean(None) is None
    assert _clean(True) is True


# ── _clean: numpy scalar/array conversion ────────────────────────────────────

def test_numpy_scalars_convert_to_python_types():
    score = _clean(np.int64(80))
    assert score == 80 and isinstance(score, int)

    rsi = _clean(np.float64(61.25))
    assert rsi == 61.25 and isinstance(rsi, float)

    flag = _clean(np.bool_(True))
    assert flag is True and isinstance(flag, bool)


def test_ndarray_becomes_list_with_nan_replaced():
    assert _clean(np.array([1.0, float("nan"), 3.0])) == [1.0, None, 3.0]


# ── _clean: recursion through containers ─────────────────────────────────────

def test_nested_structures_are_cleaned_at_every_depth():
    payload = {
        "results": [
            {"symbol": "TCS", "rsi": float("nan"), "pe": np.float64("nan")},
            {"symbol": "INFY", "rsi": 55.0},
        ],
        "nested": {"deep": [{"v": float("nan")}, (float("nan"), 2.5)]},
    }
    out = _clean(payload)

    assert out["results"][0]["rsi"] is None
    assert out["results"][0]["pe"] is None
    assert out["results"][1]["rsi"] == 55.0
    assert out["nested"]["deep"][0]["v"] is None
    assert out["nested"]["deep"][1] == [None, 2.5]   # tuples become lists


def test_tuples_become_lists():
    assert _clean((1.0, 2.0)) == [1.0, 2.0]


def test_dict_keys_are_preserved():
    assert set(_clean({"a": 1.0, "b": float("nan")})) == {"a", "b"}


# ── The real contract: survives strict serialization ─────────────────────────

def test_cleaned_payload_survives_starlette_strict_serialization():
    """The actual regression: this raised ValueError before the fix."""
    payload = {
        "results": [{"symbol": "TRENT", "rsi": float("nan"),
                     "adx": np.float64("nan"), "score": np.int64(91)}],
        "breadth": {"advancing": np.int64(21), "ratio": float("inf")},
        "total": 50,
    }
    assert strict(_clean(payload))          # must not raise


def test_raw_payload_would_have_failed_without_clean():
    """Guards the premise: without _clean the same payload is unserializable."""
    with pytest.raises(ValueError, match="not JSON compliant"):
        strict({"rsi": float("nan")})


def test_j_returns_valid_json_response_for_nan_payload():
    resp = _j({"results": [{"symbol": "TCS", "rsi": float("nan")}], "total": 1})
    body = json.loads(resp.body)
    assert resp.status_code == 200
    assert body["results"][0]["rsi"] is None
    assert body["total"] == 1


def test_realistic_scan_payload_round_trips():
    """Payload shaped like /api/scan output, with the NaN mix seen live."""
    payload = {
        "results": [
            {"symbol": "TRENT", "name": "Trent", "sector": "Consumer",
             "price": 3107.1, "change_pct": -0.7, "rsi": np.float64(62.0),
             "pe": float("nan"), "adx": np.float64(22.1),
             "vol_ratio": np.float64("nan"), "fo": np.bool_(True),
             "score": np.int64(91), "spark": np.array([1.0, float("nan"), 3.0])},
        ],
        "sectors": [{"name": "Consumer", "avg_score": float("nan")}],
        "breadth": {"advancing": np.int64(21), "declining": np.int64(29)},
        "total": 50,
        "cached": False,
    }
    body = json.loads(strict(_clean(payload)))

    row = body["results"][0]
    assert row["pe"] is None and row["vol_ratio"] is None      # NaN → null
    assert row["rsi"] == 62.0 and row["score"] == 91           # good data kept
    assert row["fo"] is True
    assert row["spark"] == [1.0, None, 3.0]
    assert body["sectors"][0]["avg_score"] is None
    assert body["total"] == 50


# ── Global exception handler ─────────────────────────────────────────────────

@app.get("/_test/boom")
async def _boom():                                   # pragma: no cover - test route
    raise RuntimeError("kaboom")


client = TestClient(app, raise_server_exceptions=False)


def test_unhandled_error_returns_json_not_plain_text():
    """The frontend must never again receive plain 'Internal Server Error'."""
    resp = client.get("/_test/boom")

    assert resp.status_code == 500
    body = resp.json()                               # would raise before the fix
    assert body["error"] == "RuntimeError: kaboom"
    assert body["path"] == "/_test/boom"


def test_unhandled_error_body_is_parseable_json():
    resp = client.get("/_test/boom")
    assert json.loads(resp.text)                     # no 'Unexpected token I'


def test_http_exception_still_returns_json():
    """404s keep FastAPI's normal JSON shape — handler doesn't swallow them."""
    resp = client.get("/api/scan/not_a_real_market")
    assert resp.status_code == 404
    assert "detail" in resp.json()
