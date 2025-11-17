@echo off
echo ========================================
echo Recreating Virtual Environment
echo ========================================
echo.

cd "c:\Users\peter\wind and river\trading_system"

echo Step 1: Removing old venv...
if exist venv (
    rmdir /s /q venv
    echo   Old venv removed
) else (
    echo   No old venv found
)
echo.

echo Step 2: Creating new virtual environment...
python -m venv venv
if errorlevel 1 (
    echo   ERROR: Failed to create venv
    echo   Make sure Python is installed and in PATH
    pause
    exit /b 1
)
echo   Virtual environment created successfully
echo.

echo Step 3: Upgrading pip...
venv\Scripts\python.exe -m pip install --upgrade pip
echo.

echo Step 4: Installing dependencies...
venv\Scripts\pip.exe install -r ..\requirements.txt
echo.

echo ========================================
echo Virtual environment ready!
echo ========================================
echo.
echo You can now:
echo   - Run dashboard: ..\run_dashboard.bat
echo   - Start web interface: ..\start_web_interface.bat
echo.

pause
