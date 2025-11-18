"""Quick script to view current watchlist"""
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

# Get all watchlist entries
cursor.execute('''
    SELECT symbol, timeframe, direction, added_at, notes
    FROM user_watchlists
    ORDER BY direction, timeframe, symbol
''')

rows = cursor.fetchall()

if rows:
    print('Current Watchlist:')
    print('=' * 80)

    current_direction = None
    for symbol, timeframe, direction, added_at, notes in rows:
        # Print direction header
        if direction != current_direction:
            current_direction = direction
            emoji = '🌪️' if direction == 'wind_catcher' else '🌊'
            dir_name = 'Wind Catcher (Bullish)' if direction == 'wind_catcher' else 'River Turn (Bearish)'
            print(f'\n{emoji} {dir_name.upper()}')
            print('-' * 80)

        print(f'  {symbol:12} | {timeframe:6} | Added: {added_at if added_at else "N/A"}')

    print('\n' + '=' * 80)
    print(f'Total pairs: {len(rows)}')
else:
    print('❌ No trading pairs in watchlist yet!')
    print('Add pairs using: python update_watchlist.py')

conn.close()
