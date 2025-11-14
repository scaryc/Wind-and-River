@echo off
REM Start Auto-Updater for continuous monitoring

cd trading_system

echo ============================================================
echo Wind Catcher ^& River Turn - Auto Monitoring
echo ============================================================
echo.
echo Starting continuous monitoring system...
echo This will:
echo   - Update data every hour
echo   - Run dashboard analysis 3x daily ^(8am, 2pm, 8pm^)
echo   - Perform daily data collection at 6am
echo.
echo Press Ctrl+C to stop
echo.
echo ============================================================

python auto_updater.py

pause
