@echo off
echo ========================================
echo Wind Catcher ^& River Turn - Web Interface
echo ========================================
echo.

cd "c:\Users\peter\wind and river\trading_system\web"

echo Starting Flask web server...
echo Open browser to: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

..\venv\Scripts\python.exe app.py

pause
