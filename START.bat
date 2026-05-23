@echo off
echo Starting ASTA Scanner...
docker compose up --build -d
echo.
echo Done! Open your browser and go to:
echo http://localhost:8888
echo.
start http://localhost:8888
pause
