@echo off
REM ASTA Stock Scanner — run.bat (Windows)
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════╗
echo  ║   ASTA Stock Scanner v1.0   ║
echo  ╚══════════════════════════════╝
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found. Install from https://python.org
    pause
    exit /b 1
)

if not exist venv (
    echo  Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo  Installing dependencies...
    pip install -r requirements.txt -q
)

echo  Starting scanner on http://localhost:8888
echo  Open your browser and go to http://localhost:8888
echo  Press Ctrl+C to stop
echo.

python -m uvicorn app:app --host 0.0.0.0 --port 8888
pause
