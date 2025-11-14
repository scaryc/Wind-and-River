@echo off
REM Quick Start - Run trading dashboard after collecting latest data

cd trading_system

echo ============================================================
echo Wind Catcher ^& River Turn - Quick Start
echo ============================================================
echo.

echo Collecting latest data...
python data_collector.py
echo.

echo Running trading dashboard...
echo ============================================================
python trading_dashboard.py

echo.
echo ============================================================
pause
