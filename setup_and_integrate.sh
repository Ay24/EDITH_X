#!/usr/bin/env bash
# ==============================================================================
# EDITH-X Enterprise: Automated Setup, Dependency Installation & System Integration
# ==============================================================================
set -e

echo "======================================================================"
echo "   EDITH-X ENTERPRISE: ONE-CLICK SETUP & SYSTEM INTEGRATION           "
echo "======================================================================"

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3.10+ is required but not found."
    exit 1
fi

echo "[*] Found Python: $(python3 --version)"

# 2. Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[*] Creating .venv virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# 3. Dependencies
echo "[*] Installing/Verifying dependencies..."
pip install --upgrade pip setuptools wheel --quiet
pip install fastapi uvicorn pydantic pydantic-settings httpx litellm qdrant-client structlog python-pptx xlsxwriter psutil pyyaml numpy pytest pytest-asyncio --quiet

# 4. Check Docker
if command -v docker &> /dev/null; then
    echo "[OK] Docker CLI detected."
else
    echo "[!] Docker not detected. Native process socket mode will be used."
fi

# 5. Run Python Orchestrator
python scripts/setup_and_integrate.py "$@"
