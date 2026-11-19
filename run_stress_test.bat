@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo       EDITH-X ENTERPRISE 1,000-USER PRODUCTION STRESS TEST
echo ======================================================================
echo.

cd /d "%~dp0"

set PYTHON_CMD=python
if exist ".\.venv\Scripts\python.exe" (
    set PYTHON_CMD=.\.venv\Scripts\python.exe
)

:: 1. Verify Dataset
if not exist "tests\benchmarks\datasets\enterprise_1000_users.json" (
    echo [*] Generating 1,000 enterprise user profiles and workload dataset...
    %PYTHON_CMD% tests/benchmarks/datasets/build_enterprise_1000_dataset.py
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to generate dataset!
        pause
        exit /b 1
    )
)

:: 2. Choose Concurrency Level
set CONCURRENCY=50
echo Select concurrency level for the 1,000-user stress test:
echo   [1] 25 Concurrent Workers  (Standard Workstation)
echo   [2] 50 Concurrent Workers  (Recommended Enterprise Baseline)
echo   [3] 100 Concurrent Workers (High-Throughput Burst)
echo.
set /p CHOICE="Enter choice [1-3, default 2]: "
if "%CHOICE%"=="1" set CONCURRENCY=25
if "%CHOICE%"=="2" set CONCURRENCY=50
if "%CHOICE%"=="3" set CONCURRENCY=100

echo.
echo [*] Launching EDITH-X Production Stress Test with %CONCURRENCY% concurrent workers...
echo [*] Executing 1,000 enterprise user journeys across 50 multi-tenant organizations...
echo.

%PYTHON_CMD% tests/benchmarks/runners/enterprise_stress_test_1000.py --concurrency %CONCURRENCY%

echo.
echo ======================================================================
echo                     STRESS TEST COMPLETED
echo ======================================================================
echo.
echo Detailed report generated at:
echo   tests\benchmarks\reports\ENTERPRISE_1000_USER_STRESS_TEST_REPORT.md
echo.
pause
