# Launch Instructions

## Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

## Quick Start (Mac/Linux)

We have provided helper scripts to make this easy.

1. **Setup** (runs once):
   ```bash
   bash setup.sh
   ```

2. **Run**:
   ```bash
   bash run.sh
   ```

## Manual Setup

If you prefer to run commands manually:

1. **Create a Virtual Environment** (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   - Ensure `.env` exists and contains your `OPENROUTER_API_KEY`.
   - The verified `.env` file should look like:
     ```env
     OPENROUTER_API_KEY=your_key_here
     SECRET_KEY=your_secret_key
     DEBUG=True
     PORT=5001
     ```

4. **Run the Application**:
   ```bash
   python app.py
   ```
   The server will start at `http://localhost:5001`.

## Verification

To verify that the backend is working correctly, you can run the included verification script while the server is running:

```bash
python verify_workflow.py
```
