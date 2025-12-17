#!/bin/bash

# Ensure we're in the script directory
cd "$(dirname "$0")"

# Activate venv if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run the app
echo "🚀 Starting application..."
python3 app.py
