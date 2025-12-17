#!/bin/bash

# Ensure we're in the script directory
cd "$(dirname "$0")"

echo "🚀 Setting up environment..."

# 1. Create venv if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

# 2. Activate venv
source .venv/bin/activate

# 3. Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo "✅ Setup complete! You can now run the app with: ./run.sh"
