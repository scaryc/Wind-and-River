@echo off
REM Wind Catcher & River Turn - Complete Setup and Run Script
REM This script automates the entire setup process

echo ============================================================
echo Wind Catcher ^& River Turn Trading System - Setup
echo ============================================================
echo.

REM Step 1: Install dependencies
echo Step 1/5: Installing dependencies...
echo ------------------------------------------------------------
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo ✓ Dependencies installed successfully
echo.

REM Step 2: Test Hyperliquid connection
echo Step 2/5: Testing Hyperliquid connection...
echo ------------------------------------------------------------
cd trading_system
python hyperliquid_connector.py
if errorlevel 1 (
    echo ERROR: Hyperliquid connection test failed
    pause
    exit /b 1
)
echo ✓ Hyperliquid connection verified
echo.

REM Step 3: Setup database (if needed)
echo Step 3/5: Setting up database...
echo ------------------------------------------------------------
if not exist "data\trading_system.db" (
    python database_setup.py
    if errorlevel 1 (
        echo ERROR: Database setup failed
        pause
        exit /b 1
    )
    echo ✓ Database created successfully
) else (
    echo ✓ Database already exists, skipping
)
echo.

REM Step 4: Check watchlist
echo Step 4/5: Checking watchlist...
echo ------------------------------------------------------------
python -c "import sqlite3; conn = sqlite3.connect('data/trading_system.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM watchlist WHERE active = 1'); count = cursor.fetchone()[0]; print(f'Watchlist has {count} active coins'); exit(0 if count > 0 else 1)"
if errorlevel 1 (
    echo.
    echo ⚠ WARNING: Watchlist is empty!
    echo.
    echo You need to add coins to your watchlist.
    echo After this script finishes, run:
    echo    cd trading_system
    echo    python update_watchlist.py
    echo.
    echo Add coins like: BTC, ETH, SOL ^(without /USDT^)
    echo.
    pause
) else (
    echo ✓ Watchlist configured
)
echo.

REM Step 5: Collect initial data (only if watchlist has coins)
echo Step 5/5: Collecting initial data...
echo ------------------------------------------------------------
python -c "import sqlite3; conn = sqlite3.connect('data/trading_system.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM watchlist WHERE active = 1'); count = cursor.fetchone()[0]; exit(0 if count > 0 else 1)"
if errorlevel 1 (
    echo ⚠ Skipping data collection - watchlist is empty
    echo Please add coins first using: python update_watchlist.py
) else (
    python data_collector.py
    if errorlevel 1 (
        echo ERROR: Data collection failed
        pause
        exit /b 1
    )
    echo ✓ Data collected successfully
)
echo.

REM All done!
echo ============================================================
echo ✓ Setup Complete!
echo ============================================================
echo.
echo Your trading system is ready to use!
echo.
echo Available commands:
echo   python trading_dashboard.py      - View signals and analysis
echo   python data_collector.py         - Update price data
echo   python update_watchlist.py       - Manage your coins
echo   python auto_updater.py           - Start continuous monitoring
echo.
echo To add coins to watchlist:
echo   python update_watchlist.py
echo   Add: BTC, ETH, SOL, etc. ^(without /USDT^)
echo.

cd ..
pause
