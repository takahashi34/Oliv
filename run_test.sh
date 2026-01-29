#!/bin/bash
# Test run script for OPREL Laser Measurement Suite (with mock instruments)
# Use this script to test the application without real hardware

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found!"
    echo "Creating virtual environment..."
    
    # Try to use Python 3.14 if available (has tkinter support), otherwise fall back to python3
    if command -v python3.14 &> /dev/null; then
        python3.14 -m venv venv
    else
        python3 -m venv venv
    fi
    
    echo "Installing requirements..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "Virtual environment created and requirements installed!"
fi

# Activate virtual environment
source venv/bin/activate

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "Error: Python is not available in virtual environment"
    exit 1
fi

# Verify tkinter is available
if ! python -c "import tkinter" 2>/dev/null; then
    echo "Warning: tkinter is not available in this Python installation."
    echo "On macOS, install it with: brew install python-tk"
    echo "Attempting to run anyway..."
fi

echo "============================================"
echo "  RUNNING IN TEST MODE (Mock Instruments)"
echo "============================================"
echo ""

# Enable mock instruments and run the main application
export MOCK_INSTRUMENTS=1
python "OPREL Laser Measurement Suite.py"


