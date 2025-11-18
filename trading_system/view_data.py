"""Quick script to view collected price data"""
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import sqlite3
from pathlib import Path
from datetime import datetime

db_path = Path('data/trading_system.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("📊 Trading System Database - Data Overview")
print("=" * 80)

# Count total candles
cursor.execute("SELECT COUNT(*) FROM price_data")
total_candles = cursor.fetchone()[0]
print(f"\n📈 Total candles stored: {total_candles:,}")

# Count by symbol
print("\n📊 Candles per symbol:")
print("-" * 80)
cursor.execute("""
    SELECT symbol, COUNT(*) as count
    FROM price_data
    GROUP BY symbol
    ORDER BY symbol
""")
for symbol, count in cursor.fetchall():
    print(f"  {symbol:12} - {count:4} candles")

# Count by timeframe
print("\n⏰ Candles per timeframe:")
print("-" * 80)
cursor.execute("""
    SELECT timeframe, COUNT(*) as count
    FROM price_data
    GROUP BY timeframe
    ORDER BY timeframe
""")
for timeframe, count in cursor.fetchall():
    print(f"  {timeframe:12} - {count:4} candles")

# Show latest candles for each symbol/timeframe
print("\n📋 Latest candle per symbol/timeframe:")
print("-" * 80)
cursor.execute("""
    SELECT
        symbol,
        timeframe,
        timestamp,
        open,
        high,
        low,
        close,
        volume
    FROM price_data
    WHERE (symbol, timeframe, timestamp) IN (
        SELECT symbol, timeframe, MAX(timestamp)
        FROM price_data
        GROUP BY symbol, timeframe
    )
    ORDER BY symbol, timeframe
""")

for row in cursor.fetchall():
    symbol, timeframe, timestamp, open_p, high, low, close, volume = row
    dt = datetime.fromtimestamp(timestamp)
    print(f"  {symbol:6} {timeframe:6} - ${close:10.2f} @ {dt.strftime('%Y-%m-%d %H:%M')} | Vol: {volume:,.0f}")

# Date range
print("\n📅 Data date range:")
print("-" * 80)
cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM price_data")
min_ts, max_ts = cursor.fetchone()
if min_ts and max_ts:
    print(f"  Oldest: {datetime.fromtimestamp(min_ts).strftime('%Y-%m-%d %H:%M')}")
    print(f"  Newest: {datetime.fromtimestamp(max_ts).strftime('%Y-%m-%d %H:%M')}")
    days = (max_ts - min_ts) / (24 * 3600)
    print(f"  Span:   {days:.1f} days")

# Database file size
db_size = db_path.stat().st_size / (1024 * 1024)
print(f"\n💾 Database size: {db_size:.2f} MB")

print("\n" + "=" * 80)
print("✅ Data overview complete!")

conn.close()
