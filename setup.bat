@echo off
REM ============================================
REM  FIFA 16 Revival Server - Setup Script
REM ============================================

echo.
echo ========================================
echo   FIFA 16 Revival Server - Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.11+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Checking Python...
python --version

echo.
echo [2/4] Creating virtual environment...
if not exist ".venv" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo.
echo [3/4] Installing dependencies...
pip install -r requirements.txt

echo.
echo [4/4] Creating data directories...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo To start the server:
echo   1. Activate venv:  .venv\Scripts\activate
echo   2. Run:            python run_server.py
echo.
echo To setup DNS redirect (run as Admin):
echo   python recon\setup_dns_redirect.py install
echo.
pause
