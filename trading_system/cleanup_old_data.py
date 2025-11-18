"""Clean up old ADA and BNB data from database"""
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import sqlite3
from pathlib import Path

db_path = Path('data/trading_system.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("🧹 Cleaning up old data...")
print("=" * 80)

# Count before deletion
cursor.execute("SELECT COUNT(*) FROM price_data WHERE symbol LIKE '%ADA%' OR symbol LIKE '%BNB%'")
before_count = cursor.fetchone()[0]
print(f"\n📊 Found {before_count} ADA/BNB candles to delete")

# Delete ADA data
cursor.execute("DELETE FROM price_data WHERE symbol LIKE '%ADA%'")
ada_deleted = cursor.rowcount
print(f"   ✅ Deleted {ada_deleted} ADA candles")

# Delete BNB data
cursor.execute("DELETE FROM price_data WHERE symbol LIKE '%BNB%'")
bnb_deleted = cursor.rowcount
print(f"   ✅ Deleted {bnb_deleted} BNB candles")

# Commit changes
conn.commit()

# Verify deletion
cursor.execute("SELECT COUNT(*) FROM price_data")
remaining = cursor.fetchone()[0]
print(f"\n📈 Total candles remaining: {remaining}")

# Show remaining symbols
cursor.execute("SELECT DISTINCT symbol FROM price_data ORDER BY symbol")
symbols = [row[0] for row in cursor.fetchall()]
print(f"\n📋 Remaining symbols: {', '.join(symbols)}")

print("\n" + "=" * 80)
print("✅ Cleanup complete!")

conn.close()
