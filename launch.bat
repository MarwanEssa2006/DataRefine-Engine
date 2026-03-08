@echo off
title Data Intelligence Engine

echo.
echo  ╔══════════════════════════════════════╗
echo  ║    Data Intelligence Engine          ║
echo  ║    Starting...                       ║
echo  ╚══════════════════════════════════════╝
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.9+ from python.org
    pause
    exit /b 1
)

:: Install dependencies silently if missing
echo  [1/2] Checking dependencies...
pip install streamlit plotly rapidfuzz scipy openpyxl --quiet --disable-pip-version-check

echo  [2/2] Launching app...
echo.
echo  Opening in your browser at http://localhost:8501
echo  Press Ctrl+C in this window to stop the server.
echo.

:: Launch Streamlit — opens browser automatically
streamlit run app.py --server.headless false --browser.gatherUsageStats false

pause
