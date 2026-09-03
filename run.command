#!/bin/bash
# ============================================================
#  ASTA Stock Scanner - macOS launcher
#  Double-click this file in Finder. That is the whole install.
#
#  .command (not .sh) on purpose: Finder double-click opens .sh
#  in a text editor, but runs .command in Terminal.
# ============================================================

# Finder launches scripts from an arbitrary directory, so anchor to this file.
cd "$(dirname "$0")" || exit 1

# Override with:  ASTA_PORT=8899 ./run.command   (useful if 8888 is taken)
PORT="${ASTA_PORT:-8888}"

echo ""
echo "  =================================="
echo "    ASTA Stock Scanner"
echo "  =================================="
echo ""

# ---- Find Python 3 ------------------------------------------------------
# macOS no longer ships python3; the stub prompts to install Xcode Command
# Line Tools. Detect a *working* interpreter rather than just the name.
PY=""
for c in python3 python3.12 python3.11 /usr/local/bin/python3 /opt/homebrew/bin/python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; sys.exit(0 if sys.version_info>=(3,9) else 1)" >/dev/null 2>&1; then
        PY="$c"; break
    fi
done

if [ -z "$PY" ]; then
    echo "  ERROR: Python 3.9+ was not found."
    echo ""
    echo "  Install it either way:"
    echo "    - Run:  xcode-select --install    (then double-click this again)"
    echo "    - Or download from https://www.python.org/downloads/"
    echo ""
    read -n 1 -s -r -p "  Press any key to close..."
    exit 1
fi

# ---- Create the virtual environment on first run ------------------------
if [ ! -x "venv/bin/python" ]; then
    echo "  First run: creating environment. This takes a minute..."
    "$PY" -m venv venv || {
        echo "  ERROR: Could not create the environment."
        read -n 1 -s -r -p "  Press any key to close..."
        exit 1
    }
fi

VPY="venv/bin/python"

# ---- Install dependencies if missing ------------------------------------
if ! "$VPY" -c "import fastapi, uvicorn, pandas, numpy, yfinance" >/dev/null 2>&1; then
    echo "  Installing dependencies. First time only, 2-3 minutes..."
    "$VPY" -m pip install --upgrade pip -q
    if ! "$VPY" -m pip install -r requirements.txt -q; then
        echo ""
        echo "  ERROR: Dependency install failed. Check your internet connection."
        read -n 1 -s -r -p "  Press any key to close..."
        exit 1
    fi
fi

# ---- Start the server, then open the browser once it answers ------------
# The browser must open AFTER the server is listening, otherwise the first
# run shows a connection error while dependencies are still installing.
echo ""
echo "  Starting scanner..."
"$VPY" -m uvicorn app:app --host 127.0.0.1 --port "$PORT" &
SERVER_PID=$!

# Closing the Terminal window or pressing Ctrl+C stops the server too.
cleanup() {
    echo ""
    echo "  Stopping scanner..."
    kill "$SERVER_PID" 2>/dev/null
    exit 0
}
trap cleanup INT TERM

echo "  Waiting for it to come up..."
for _ in $(seq 1 60); do
    if "$VPY" -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1',$PORT))==0 else 1)" >/dev/null 2>&1; then
        break
    fi
    # If the server died (bad port, crash), stop waiting and show why.
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        echo "  ERROR: The scanner stopped unexpectedly (is port $PORT already in use?)."
        read -n 1 -s -r -p "  Press any key to close..."
        exit 1
    fi
    sleep 1
done

echo ""
echo "  =================================="
echo "    Ready:  http://localhost:$PORT"
echo "  =================================="
echo ""
open "http://localhost:$PORT"
echo "  Keep this window open while you use the scanner."
echo "  Press Ctrl+C (or close this window) to stop."
echo ""

wait "$SERVER_PID"
