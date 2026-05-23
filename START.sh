#!/bin/bash
echo "Starting ASTA Scanner..."
docker compose up --build -d
echo ""
echo "Done! Opening browser..."
sleep 2
open http://localhost:8888 2>/dev/null || xdg-open http://localhost:8888 2>/dev/null
echo "If browser didn't open, go to: http://localhost:8888"
