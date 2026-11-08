#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "         PEGPOWER - SMART ELECTRICITY CONTROLLER          "
echo "=========================================================="

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# 1. Activate Virtual Environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "[!] .venv not found. Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r backend/requirements.txt
fi

# 2. Seed Baseline Data
echo "[*] Initializing database and demo seeds..."
PYTHONPATH=backend python3 scripts/seed_demo.py

# 3. Start Backend & UI Server
echo "[+] Starting PegPower Unified Server on http://localhost:8000..."
echo "    - UI Dashboard: http://localhost:8000"
echo "    - API Docs:     http://localhost:8000/docs"
echo "    - WebSocket:    ws://localhost:8000/api/ws"
echo ""
echo "[i] To run AZ3166 DevKit Emulator in a separate terminal:"
echo "    python3 scripts/mock_az3166.py http://localhost:8000"
echo "=========================================================="

PYTHONPATH=backend uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
