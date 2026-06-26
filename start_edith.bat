@echo off
echo ===================================================
echo       EDITH-X ENTERPRISE AI RUNTIME STARTUP
echo ===================================================
echo.

cd /d "%~dp0"

echo [1/2] Starting EDITH-X API Server (Port 8000)...
start "EDITH-X API" cmd /k "py -3.12 -m uvicorn edith_x.interfaces.rest.app:app --host 0.0.0.0 --port 8000 --log-level info"

echo Waiting for API to initialize...
timeout /t 5 /nobreak > nul

echo [2/2] Starting EDITH-X Dashboard (Port 8501)...
start "EDITH-X Dashboard" cmd /k "py -3.12 -m streamlit run edith_x/demo/ui.py --server.port 8501 --server.headless false --browser.gatherUsageStats false"

echo.
echo ===================================================
echo                SYSTEM ONLINE
echo ===================================================
echo.
echo Dashboard: http://localhost:8501
echo API Docs:  http://localhost:8000/docs
echo.
echo Note: Ensure LM Studio is running on Port 1234.
echo Close the two newly opened terminal windows to stop the servers.
echo.
pause
