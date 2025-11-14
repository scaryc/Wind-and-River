@echo off
REM Add coins to watchlist

cd trading_system

echo ============================================================
echo Wind Catcher ^& River Turn - Add Coins to Watchlist
echo ============================================================
echo.
echo IMPORTANT: Use coin names WITHOUT /USDT
echo Examples: BTC, ETH, SOL, DOGE, ARB
echo.
echo ============================================================

python update_watchlist.py

pause
