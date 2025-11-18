"""
Practical Signals Report Generator
Analyzes current state of all coins and creates Excel report
"""

import sys
import io

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

import pandas as pd
from datetime import datetime
from pathlib import Path

print("🚀 Creating Signals Report from Database")
print("="*80)

# First, run master confluence to generate latest signals
print("\nStep 1: Analyzing latest data...")
import subprocess
result = subprocess.run(
    ['./venv/Scripts/python.exe', 'master_confluence.py'],
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace'
)

print(result.stdout[:500])  # Show first 500 chars

# Now export database data to Excel
print("\nStep 2: Exporting to Excel...")

import sqlite3
conn = sqlite3.connect('data/trading_system.db')

# Get all price data
query = """
    SELECT
        symbol,
        timeframe,
        timestamp,
        open, high, low, close, volume
    FROM price_data
    WHERE symbol IN ('BTC', 'ETH', 'DOT', 'FET', 'HYPE', 'ICP')
    ORDER BY symbol, timeframe, timestamp DESC
"""

df = pd.read_sql_query(query, conn)
df['date'] = pd.to_datetime(df['timestamp'], unit='s')

# Create summary
summary = df.groupby(['symbol', 'timeframe']).agg({
    'timestamp': ['count', 'min', 'max'],
    'close': ['first', 'min', 'max', 'mean']
}).reset_index()

summary.columns = ['Symbol', 'Timeframe', 'Candles', 'First_Date', 'Last_Date',
                   'Latest_Price', 'Min_Price', 'Max_Price', 'Avg_Price']

summary['First_Date'] = pd.to_datetime(summary['First_Date'], unit='s')
summary['Last_Date'] = pd.to_datetime(summary['Last_Date'], unit='s')

# Export to Excel
output_file = Path('../doc/TRADING_DATA_REPORT.xlsx')
output_file.parent.mkdir(parents=True, exist_ok=True)

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # Summary sheet
    summary.to_excel(writer, sheet_name='Summary', index=False)

    # Per-symbol sheets with recent data
    for symbol in ['BTC', 'ETH', 'DOT', 'FET', 'HYPE', 'ICP']:
        symbol_df = df[df['symbol'] == symbol].head(1000)  # Last 1000 candles
        symbol_df.to_excel(writer, sheet_name=symbol, index=False)

conn.close()

print(f"✅ Report created: {output_file}")
print(f"\nSummary:")
print(summary.to_string(index=False))
print("\n" + "="*80)
print("✅ Complete! Open the Excel file to review data.")
