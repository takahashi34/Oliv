#!/bin/bash
# Activate the virtual environment
# Usage: source activate_env.sh

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please create it first by running: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    return 1 2>/dev/null || exit 1
fi

source venv/bin/activate
echo "Virtual environment activated!"
echo "Python: $(which python)"
echo "To deactivate, run: deactivate"

