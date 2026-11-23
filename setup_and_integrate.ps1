# ==============================================================================
# EDITH-X Enterprise: Automated Setup, Dependency Installation & System Integration
# ==============================================================================

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   EDITH-X ENTERPRISE: ONE-CLICK SETUP & SYSTEM INTEGRATION           " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Check Python Installation
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python 3.10+ is not found in PATH." -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/ and check 'Add Python to PATH'." -ForegroundColor Yellow
    Exit 1
}

$pyVersion = python --version
Write-Host "[*] Found Python: $pyVersion" -ForegroundColor Green

# 2. Check / Create Virtual Environment
$venvPath = Join-Path $PSScriptRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "[*] Virtual environment not found. Creating .venv..." -ForegroundColor Yellow
    python -m venv $venvPath
    if (-not (Test-Path $venvPython)) {
        Write-Host "[ERROR] Failed to create virtual environment." -ForegroundColor Red
        Exit 1
    }
    Write-Host "[OK] Created virtual environment at .venv" -ForegroundColor Green
} else {
    Write-Host "[OK] Detected existing virtual environment at .venv" -ForegroundColor Green
}

# 3. Upgrade pip and install wheel
Write-Host "[*] Upgrading pip, setuptools, and wheel..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip setuptools wheel --quiet

# 4. Install Project Dependencies
Write-Host "[*] Installing EDITH-X Enterprise dependencies..." -ForegroundColor Cyan
& $venvPython -m pip install fastapi uvicorn pydantic pydantic-settings httpx litellm qdrant-client structlog python-pptx xlsxwriter psutil pyyaml numpy pytest pytest-asyncio --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Dependency installation encountered issues." -ForegroundColor Red
} else {
    Write-Host "[OK] All required packages installed successfully." -ForegroundColor Green
}

# 5. Check Docker & Containerization State
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    Write-Host "[OK] Docker CLI detected." -ForegroundColor Green
} else {
    Write-Host "[!] Docker not detected on host." -ForegroundColor Yellow
    Write-Host "    Note: EDITH-X includes a native loopback HTTP test harness capable of" -ForegroundColor DarkGray
    Write-Host "    testing 1,000 users without Docker." -ForegroundColor DarkGray
    Write-Host "    If you wish to run the full Docker Compose cluster (Qdrant + Redis + Gunicorn):" -ForegroundColor DarkGray
    Write-Host "      1. Run PowerShell as Administrator:  wsl --install" -ForegroundColor DarkGray
    Write-Host "      2. Download & install Docker Desktop: https://www.docker.com/products/docker-desktop/" -ForegroundColor DarkGray
}

# 6. Execute Python Setup & Brain Seeding Orchestrator
Write-Host "`n[*] Executing Brain Initialization & Seeding..." -ForegroundColor Cyan
& $venvPython scripts/setup_and_integrate.py

# 7. Interactive Control Menu
while ($true) {
    Write-Host "`n======================================================================" -ForegroundColor Cyan
    Write-Host " EDITH-X ENTERPRISE INTERACTIVE CONTROL CENTER" -ForegroundColor Cyan
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host " [1] Run 1,000 Users Brain Seeder & Verification Suite"
    Write-Host " [2] Run Full HTTP Production Stress & Reliability Sim (T0 to T8)"
    Write-Host " [3] Start Live API Server (Port 8000)"
    Write-Host " [4] Start Mock-LLM Microservice (Port 8001)"
    Write-Host " [5] Run All 125 Pytest Regression Tests"
    Write-Host " [6] Exit"
    Write-Host "----------------------------------------------------------------------"
    $choice = Read-Host "Select an option [1-6]"

    switch ($choice) {
        "1" {
            Write-Host "`n[*] Running 1,000 Users Brain Seeder..." -ForegroundColor Green
            & $venvPython scripts/seed_and_test_1000_users.py
        }
        "2" {
            Write-Host "`n[*] Running Full Production Simulation (T0 to T8)..." -ForegroundColor Green
            & $venvPython tests/prod_sim/run_prod_sim.py
        }
        "3" {
            Write-Host "`n[*] Launching EDITH-X REST API on port 8000..." -ForegroundColor Green
            $env:LOCAL_LLM_HOST = "http://127.0.0.1:8001/v1"
            & $venvPython -m uvicorn edith_x.interfaces.rest.app:app --host 127.0.0.1 --port 8000 --reload
        }
        "4" {
            Write-Host "`n[*] Launching Mock-LLM Microservice on port 8001..." -ForegroundColor Green
            & $venvPython -m uvicorn tests.prod_sim.mock_llm.main:app --host 127.0.0.1 --port 8001 --reload
        }
        "5" {
            Write-Host "`n[*] Running Pytest Suite..." -ForegroundColor Green
            & $venvPython -m pytest -v
        }
        "6" {
            Write-Host "`nExiting EDITH-X Control Center. Goodbye!" -ForegroundColor Cyan
            Exit 0
        }
        default {
            Write-Host "`nInvalid selection. Please choose 1 to 6." -ForegroundColor Yellow
        }
    }
}
