@echo off
REM ============================================================
REM  ASTA Stock Scanner - Windows launcher (no Docker needed)
REM  Double-click this file. That is the whole install.
REM
REM  ASCII only + CRLF line endings on purpose: cmd.exe garbles
REM  UTF-8 box characters and mis-parses LF-only batch files.
REM ============================================================
setlocal
cd /d "%~dp0"

echo.
echo  ==================================
echo    ASTA Stock Scanner
echo  ==================================
echo.

REM ---- Find a real Python -------------------------------------------------
REM  Prefer the py launcher: on Windows 10/11 a bare "python" is often the
REM  Microsoft Store stub, which exits silently and installs nothing.
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
    python --version >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo  ERROR: Python was not found.
    echo.
    echo  1. Install Python from https://www.python.org/downloads/
    echo  2. On the first installer screen, TICK "Add python.exe to PATH"
    echo  3. Then double-click this file again.
    echo.
    pause
    exit /b 1
)

REM ---- Create the virtual environment on first run ------------------------
if not exist "venv\Scripts\python.exe" (
    echo  First run: creating environment. This takes a minute...
    %PY% -m venv venv
    if errorlevel 1 (
        echo  ERROR: Could not create the environment.
        pause
        exit /b 1
    )
)

set "VPY=venv\Scripts\python.exe"

REM ---- Install dependencies if missing ------------------------------------
"%VPY%" -c "import fastapi, uvicorn, pandas, numpy, yfinance" >nul 2>&1
if errorlevel 1 (
    echo  Installing dependencies. First time only, 2-3 minutes...
    "%VPY%" -m pip install --upgrade pip -q
    "%VPY%" -m pip install -r requirements.txt -q
    if errorlevel 1 (
        echo.
        echo  ERROR: Dependency install failed. Check your internet connection
        echo  and try again.
        pause
        exit /b 1
    )
)

REM ---- Start the server, then open the browser once it answers ------------
REM  The browser must open AFTER the server is listening, otherwise the first
REM  run shows a connection error while dependencies are still installing.
echo.
echo  Starting scanner...
start "" /b "%VPY%" -m uvicorn app:app --host 127.0.0.1 --port 8888

echo  Waiting for it to come up...
set /a TRIES=0
:WAITLOOP
set /a TRIES+=1
"%VPY%" -c "import socket,sys; s=socket.socket(); s.settimeout(1); sys.exit(0 if s.connect_ex(('127.0.0.1',8888))==0 else 1)" >nul 2>&1
if not errorlevel 1 goto READY
if %TRIES% GEQ 60 (
    echo  ERROR: The scanner did not start in time.
    echo  Close this window and try again.
    pause
    exit /b 1
)
"%VPY%" -c "import time; time.sleep(1)" >nul 2>&1
goto WAITLOOP

:READY
echo.
echo  ==================================
echo    Ready:  http://localhost:8888
echo  ==================================
echo.
start "" http://localhost:8888
echo  Keep this window open while you use the scanner.
echo  Closing this window stops the scanner.
echo.
pause >nul
