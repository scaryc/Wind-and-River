"""
Database Migration Script
Migrates existing database to new multi-timeframe schema
"""

import sqlite3
import os
from datetime import datetime


def get_table_columns(conn, table_name):
    """Get list of columns in a table"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return [col[1] for col in columns]


def migrate_signals_table(conn):
    """Migrate signals table to new schema"""
    cursor = conn.cursor()

    # Check if signals table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signals'")
    if not cursor.fetchone():
        print("ℹ️  Signals table doesn't exist yet - will be created fresh")
        return False

    # Get existing columns
    existing_columns = get_table_columns(conn, 'signals')
    print(f"📋 Existing signals columns: {existing_columns}")

    # Check if we need to migrate
    required_new_columns = ['timeframe', 'confluence_score', 'confluence_class',
                            'indicators_firing', 'volume_level', 'volume_ratio',
                            'details', 'notified']

    needs_migration = any(col not in existing_columns for col in required_new_columns)

    if not needs_migration:
        print("✅ Signals table already has new schema")
        return False

    print("🔄 Migrating signals table to new schema...")

    # Backup old table
    cursor.execute("DROP TABLE IF EXISTS signals_old")
    cursor.execute("ALTER TABLE signals RENAME TO signals_old")
    print("✅ Backed up old signals table")

    # Create new table with updated schema
    cursor.execute('''
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL DEFAULT '1h',
            system TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            confluence_score REAL NOT NULL DEFAULT 0.0,
            confluence_class TEXT NOT NULL DEFAULT 'UNKNOWN',
            price REAL NOT NULL,
            indicators_firing TEXT,
            volume_level TEXT,
            volume_ratio REAL,
            details TEXT,
            notified BOOLEAN DEFAULT 0,
            created_at INTEGER NOT NULL
        )
    ''')
    print("✅ Created new signals table")

    # Migrate old data
    try:
        cursor.execute('''
            INSERT INTO signals (
                id, timestamp, symbol, timeframe, system, signal_type,
                price, details, created_at
            )
            SELECT
                id, timestamp, symbol, '1h', system, signal_type,
                price, notes, created_at
            FROM signals_old
        ''')
        migrated_count = cursor.rowcount
        print(f"✅ Migrated {migrated_count} signals from old table")
    except Exception as e:
        print(f"⚠️  Could not migrate old data: {e}")

    conn.commit()
    return True


def add_indexes(conn):
    """Add performance indexes"""
    cursor = conn.cursor()

    print("🔧 Adding performance indexes...")

    # Price data indexes
    try:
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol_timeframe_timestamp
            ON price_data(symbol, timeframe, timestamp)
        ''')
        print("✅ Added price_data index")
    except Exception as e:
        print(f"⚠️  Price data index: {e}")

    # Signals indexes
    try:
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_signals_timestamp
            ON signals(timestamp DESC)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_signals_symbol_timeframe
            ON signals(symbol, timeframe)
        ''')
        print("✅ Added signals indexes")
    except Exception as e:
        print(f"⚠️  Signals indexes: {e}")

    conn.commit()


def main():
    """Main migration function"""
    print("🔄 Database Migration Tool")
    print("="*50)

    db_path = 'data/trading_system.db'

    if not os.path.exists(db_path):
        print(f"ℹ️  Database doesn't exist at {db_path}")
        print("💡 Run database_setup.py to create a fresh database")
        return

    try:
        conn = sqlite3.connect(db_path)
        print(f"✅ Connected to {db_path}")

        # Migrate signals table
        migrate_signals_table(conn)

        # Add indexes
        add_indexes(conn)

        conn.close()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
