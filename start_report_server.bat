@echo off
REM AWS Service Screener - Windows Report Server Launcher
REM =====================================================
REM
REM This batch file starts the report server on Windows systems.
REM Make sure Python 3.x is installed and available in your PATH.

echo.
echo ============================================================
echo  AWS Service Screener - Report Server (Windows)
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.x from https://python.org
    echo.
    pause
    exit /b 1
)

REM Check if the server script exists
if not exist "start_report_server.py" (
    echo Error: start_report_server.py not found
    echo Make sure you've extracted the output.zip file completely
    echo and are running this from the extracted directory.
    echo.
    pause
    exit /b 1
)

echo Starting report server...
echo Press Ctrl+C to stop the server when done.
echo.

REM Start the Python server
python start_report_server.py

echo.
echo Server stopped. Press any key to exit.
pause >nul