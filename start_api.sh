#!/usr/bin/env bash
# Start the FastAPI backend
cd "$(dirname "$0")"

if ! command -v uvicorn &>/dev/null; then
  echo "Installing Python dependencies..."
  pip install -r requirements.txt
fi

echo "Starting TUTOR AI API on http://localhost:8000"
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
