"""
Database Setup for Wind Catcher & River Turn Trading System
This creates the SQLite database and tables for storing price data
"""

import sqlite3
import os
from datetime import datetime

def create_database():
    """Create the main database file"""
    # Create the database directory if it doesn't exist
    if not os.path.exists('data'):
        os.makedirs('data')
        print("✅ Created data directory")
    
    # Database file path
    db_path = 'data/trading_system.db'
    
    # Connect to database (creates file if it doesn't exist)
    conn = sqlite3.connect(db_path)
    print(f"✅ Connected to database: {db_path}")
    
    return conn

def create_tables(conn):
    """Create all the tables we need"""

    cursor = conn.cursor()

    # Table 1: Price data (OHLCV - Open, High, Low, Close, Volume)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            created_at INTEGER NOT NULL,
            UNIQUE(symbol, timeframe, timestamp)
        )
    ''')
    print("✅ Created price_data table")

    # Add index for performance
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_symbol_timeframe_timestamp
        ON price_data(symbol, timeframe, timestamp)
    ''')
    print("✅ Created price_data index")

    # Table 2: Legacy Watchlist (kept for backward compatibility)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL UNIQUE,
            added_at INTEGER NOT NULL,
            active BOOLEAN DEFAULT 1,
            notes TEXT
        )
    ''')
    print("✅ Created watchlist table")

    # Table 2B: User Watchlists (new multi-timeframe watchlists)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_watchlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            direction TEXT NOT NULL,
            added_at INTEGER NOT NULL,
            notes TEXT,
            UNIQUE(symbol, timeframe, direction)
        )
    ''')
    print("✅ Created user_watchlists table")

    # Table 3: Enhanced Signals (Wind Catcher/River Turn alerts)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            system TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            confluence_score REAL NOT NULL,
            confluence_class TEXT NOT NULL,
            price REAL NOT NULL,
            indicators_firing TEXT,
            volume_level TEXT,
            volume_ratio REAL,
            details TEXT,
            notified BOOLEAN DEFAULT 0,
            created_at INTEGER NOT NULL
        )
    ''')
    print("✅ Created signals table")

    # Add indexes for signals table
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_signals_timestamp
        ON signals(timestamp DESC)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_signals_symbol_timeframe
        ON signals(symbol, timeframe)
    ''')
    print("✅ Created signals indexes")

    # Save changes
    conn.commit()
    print("✅ All tables created successfully!")

def add_initial_watchlist(conn):
    """Add initial coins to watchlist"""
    cursor = conn.cursor()
    
    initial_coins = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'ADA/USDT']
    current_time = int(datetime.now().timestamp())
    
    for symbol in initial_coins:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO watchlist (symbol, added_at, notes)
                VALUES (?, ?, ?)
            ''', (symbol, current_time, 'Initial setup'))
        except Exception as e:
            print(f"⚠️ Could not add {symbol}: {e}")
    
    conn.commit()
    print(f"✅ Added {len(initial_coins)} coins to watchlist")

def show_database_info(conn):
    """Show some basic info about the database"""
    cursor = conn.cursor()

    print("\n" + "="*50)
    print("📊 DATABASE INFORMATION")
    print("="*50)

    # Show tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"\nTables created: {len(tables)}")
    for table in tables:
        print(f"  - {table[0]}")

    # Show legacy watchlist
    cursor.execute("SELECT symbol, active FROM watchlist ORDER BY symbol")
    watchlist = cursor.fetchall()
    print(f"\nLegacy Watchlist ({len(watchlist)} coins):")
    for symbol, active in watchlist:
        status = "✅" if active else "❌"
        print(f"  {status} {symbol}")

    # Show user watchlists
    cursor.execute("SELECT COUNT(*) FROM user_watchlists")
    user_watchlist_count = cursor.fetchone()[0]
    print(f"\nUser Watchlists: {user_watchlist_count} entries")

    if user_watchlist_count > 0:
        cursor.execute("""
            SELECT symbol, timeframe, direction
            FROM user_watchlists
            ORDER BY direction, timeframe, symbol
        """)
        user_watchlists = cursor.fetchall()
        current_direction = None
        for symbol, timeframe, direction in user_watchlists:
            if direction != current_direction:
                current_direction = direction
                emoji = "🌪️" if direction == "wind_catcher" else "🌊"
                print(f"\n  {emoji} {direction.replace('_', ' ').title()}:")
            print(f"    [{timeframe}] {symbol}")

    # Show price data count
    cursor.execute("SELECT COUNT(*) FROM price_data")
    price_count = cursor.fetchone()[0]
    print(f"\nPrice records stored: {price_count}")

    # Show signals count
    cursor.execute("SELECT COUNT(*) FROM signals")
    signals_count = cursor.fetchone()[0]
    print(f"Signals recorded: {signals_count}")

    print("="*50)

def main():
    """Main setup function"""
    print("🚀 Setting up Wind Catcher & River Turn Database")
    print("="*50)
    
    try:
        # Create database connection
        conn = create_database()
        
        # Create all tables
        create_tables(conn)
        
        # Add initial watchlist
        add_initial_watchlist(conn)
        
        # Show database information
        show_database_info(conn)
        
        # Close connection
        conn.close()
        print("\n✅ Database setup completed successfully!")
        print("\nYour trading system database is ready to use!")
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()