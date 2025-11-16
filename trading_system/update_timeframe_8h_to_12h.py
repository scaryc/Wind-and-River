#!/usr/bin/env python3
"""
Update 8h timeframe to 12h in database
"""

import sqlite3
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import DATABASE_FILE

def update_timeframes():
    """Update 8h to 12h in user_watchlists and price_data tables"""
    conn = sqlite3.connect(str(DATABASE_FILE))
    cursor = conn.cursor()

    try:
        # Check current 8h entries in user_watchlists
        cursor.execute("SELECT symbol, timeframe, direction FROM user_watchlists WHERE timeframe = '8h'")
        watchlist_entries = cursor.fetchall()

        print(f"Found {len(watchlist_entries)} watchlist entries with 8h timeframe:")
        for entry in watchlist_entries:
            print(f"  {entry}")

        # Update user_watchlists
        cursor.execute("UPDATE user_watchlists SET timeframe = '12h' WHERE timeframe = '8h'")
        watchlist_updated = cursor.rowcount

        # Check current 8h entries in price_data
        cursor.execute("SELECT COUNT(*) FROM price_data WHERE timeframe = '8h'")
        price_data_count = cursor.fetchone()[0]

        print(f"\nFound {price_data_count} price_data entries with 8h timeframe")

        # Update price_data
        cursor.execute("UPDATE price_data SET timeframe = '12h' WHERE timeframe = '8h'")
        price_data_updated = cursor.rowcount

        conn.commit()

        print(f"\n✅ Update complete:")
        print(f"   - Updated {watchlist_updated} watchlist entries")
        print(f"   - Updated {price_data_updated} price_data entries")

        # Verify
        cursor.execute("SELECT symbol, timeframe, direction FROM user_watchlists WHERE timeframe = '12h'")
        new_entries = cursor.fetchall()
        print(f"\nVerification - 12h watchlist entries:")
        for entry in new_entries:
            print(f"  {entry}")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    update_timeframes()
