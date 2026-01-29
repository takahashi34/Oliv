@echo off
REM Test run script for OPREL Laser Measurement Suite (Windows)
REM Use this script to test the application without real hardware

REM Get the directory where this script is located
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv" (
    echo Error: Virtual environment not found!
    echo Creating virtual environment...
    python -m venv venv
    echo Installing requirements...
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    echo Virtual environment created and requirements installed!
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not available in virtual environment
    pause
    exit /b 1
)

REM Verify tkinter is available
python -c "import tkinter" >nul 2>&1
if errorlevel 1 (
    echo Warning: tkinter is not available in this Python installation.
    echo Make sure Python was installed with tkinter support.
    echo Attempting to run anyway...
)

echo ============================================
echo   RUNNING IN TEST MODE (Mock Instruments)
echo ============================================
echo.

REM Enable mock instruments and run the main application
set MOCK_INSTRUMENTS=1
python "OPREL Laser Measurement Suite.py"

pause


