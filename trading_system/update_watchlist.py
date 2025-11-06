"""
Update Watchlist Script
Updates the watchlist with new trading pairs
"""

import sqlite3
from datetime import datetime

def update_watchlist():
    """Update watchlist with new pairs"""
    conn = sqlite3.connect('data/trading_system.db')
    cursor = conn.cursor()
    
    # Clear current watchlist
    cursor.execute("DELETE FROM watchlist")
    print("Cleared existing watchlist")
    
    # Add new pairs
    new_pairs = ['BTC/USDT', 'ENA/USDT', 'HYPE/USDT']
    current_time = int(datetime.now().timestamp())
    
    for symbol in new_pairs:
        cursor.execute('''
            INSERT INTO watchlist (symbol, added_at, active, notes)
            VALUES (?, ?, 1, 'Updated pairs')
        ''', (symbol, current_time))
        print(f"Added {symbol}")
    
    conn.commit()
    
    # Show updated watchlist
    cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
    active_pairs = cursor.fetchall()
    
    print(f"\nUpdated watchlist ({len(active_pairs)} pairs):")
    for pair in active_pairs:
        print(f"  - {pair[0]}")
    
    conn.close()
    print("\nWatchlist update complete!")

if __name__ == "__main__":
    update_watchlist()