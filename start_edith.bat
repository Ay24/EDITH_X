@echo off
echo ===================================================
echo       EDITH-X ENTERPRISE AI RUNTIME STARTUP
echo ===================================================
echo.

cd /d "%~dp0"

set PYTHON_CMD=python
if exist ".\.venv\Scripts\python.exe" (
    set PYTHON_CMD=.\.venv\Scripts\python.exe
)

echo [1/2] Starting EDITH-X API Server (Port 8000)...
start "EDITH-X API" cmd /k "%PYTHON_CMD% -m uvicorn edith_x.interfaces.rest.app:app --host 0.0.0.0 --port 8000 --log-level info"

echo Waiting for API to initialize...
timeout /t 4 /nobreak > nul

echo [2/2] Launching Web Control Center...
start http://localhost:8000/dashboard

echo.
echo ===================================================
echo                SYSTEM ONLINE
echo ===================================================
echo.
echo Control Center: http://localhost:8000/dashboard
echo API Docs:       http://localhost:8000/docs
echo Metrics:        http://localhost:8000/edith/v1/metrics
echo.
echo Press any key to run real-time diagnostic test...
pause > nul
%PYTHON_CMD% test_realtime.py
pause
