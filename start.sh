#!/bin/bash
# Native macOS launch (supports Apple Calendar & Reminders)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Create venv if missing
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install / update deps
pip install -q -r requirements.txt

echo "Starting digest bot..."
python bot.py
