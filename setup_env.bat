@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo              EDITH-X ENTERPRISE ENVIRONMENT SETUP
echo ======================================================================
echo.

cd /d "%~dp0"

:: 1. Detect Python
where uv >nul 2>nul
if %errorlevel% equ 0 (
    echo [*] Found uv package manager (Ultra-fast setup enabled).
    set USE_UV=1
) else (
    set USE_UV=0
    where python >nul 2>nul
    if %errorlevel% neq 0 (
        echo [ERROR] Python was not found in PATH!
        echo Please install Python 3.10+ and add it to your PATH: https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

:: 2. Setup Virtual Environment
if not exist ".venv\Scripts\python.exe" (
    echo [*] Creating virtual environment (.venv)...
    if %USE_UV% equ 1 (
        uv venv .venv
    ) else (
        python -m venv .venv
    )
    if not exist ".venv\Scripts\python.exe" (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Existing virtual environment found in .venv.
)

:: 3. Install Dependencies
echo [*] Installing dependencies and project in editable mode...
if %USE_UV% equ 1 (
    uv pip install -e ".[dev]" --python .\.venv\Scripts\python.exe
) else (
    .\.venv\Scripts\python -m pip install --upgrade pip
    .\.venv\Scripts\python -m pip install -e ".[dev]"
)

:: 4. Setup Environment File
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Initializing .env configuration from .env.example...
        copy .env.example .env >nul
        echo [OK] Created .env configuration file.
    )
) else (
    echo [OK] .env configuration file present.
)

:: 5. Verification Check
echo.
echo [*] Verifying EDITH-X module imports...
.\.venv\Scripts\python -c "import edith_x; print('[OK] EDITH-X core package import successful.')"
if %errorlevel% neq 0 (
    echo [ERROR] Verification failed. Please check logs.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo            ENVIRONMENT SETUP COMPLETE AND READY!
echo ======================================================================
echo.
echo Next steps:
echo   1. To start the Gateway and Web Dashboard:  run start_edith.bat
echo   2. To run real-time interactive tests:       .\.venv\Scripts\python test_realtime.py
echo   3. To run the full automated test suite:    .\.venv\Scripts\pytest -q
echo.
pause
