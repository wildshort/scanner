#!/bin/bash
# ASTA Stock Scanner — run.sh
# Usage: bash run.sh

cd "$(dirname "$0")"

echo ""
echo "╔══════════════════════════════╗"
echo "║   ASTA Stock Scanner v1.0   ║"
echo "╚══════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "❌ Python 3 not found. Install from https://python.org"
  exit 1
fi

# Create venv if needed
if [ ! -d "venv" ]; then
  echo "⚙️  Creating virtual environment..."
  python3 -m venv venv
fi

source venv/bin/activate

# Install deps if needed
if ! python3 -c "import fastapi" &>/dev/null; then
  echo "📦 Installing dependencies..."
  pip install -r requirements.txt -q
fi

echo "✅ Starting scanner on http://localhost:8888"
echo "   Open your browser and go to http://localhost:8888"
echo "   Press Ctrl+C to stop"
echo ""

python3 -m uvicorn app:app --host 0.0.0.0 --port 8888
