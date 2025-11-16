"""
Database Migration Script - Version 2
Migrates from simple watchlist to multi-timeframe user_watchlists
Enhances signals table with full confluence data
"""

import sqlite3
import json
from datetime import datetime
from utils import DATABASE_FILE, get_current_timestamp

def backup_database():
    """Remind user to backup (already done manually)"""
    print("⚠️  IMPORTANT: Ensure you have backed up your database before proceeding!")
    print(f"   Database location: {DATABASE_FILE}")
    response = input("   Have you backed up the database? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Migration cancelled. Please backup your database first.")
        return False
    return True

def check_current_schema(conn):
    """Check what tables and columns currently exist"""
    cursor = conn.cursor()

    print("\n📊 Current Database Schema:")
    print("="*60)

    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"\nExisting tables: {[t[0] for t in tables]}")

    # Check if user_watchlists already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_watchlists';")
    has_user_watchlists = cursor.fetchone() is not None

    # Check signals table columns
    cursor.execute("PRAGMA table_info(signals)")
    signals_columns = cursor.fetchall()
    signals_col_names = [col[1] for col in signals_columns]
    print(f"\nSignals table columns: {signals_col_names}")

    # Check watchlist table
    cursor.execute("SELECT COUNT(*) FROM watchlist WHERE active = 1")
    active_watchlist_count = cursor.fetchone()[0]
    print(f"\nActive watchlist entries: {active_watchlist_count}")

    return {
        'has_user_watchlists': has_user_watchlists,
        'signals_columns': signals_col_names,
        'active_watchlist_count': active_watchlist_count
    }

def create_user_watchlists_table(conn):
    """Create the new user_watchlists table"""
    cursor = conn.cursor()

    print("\n🔧 Creating user_watchlists table...")

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

    conn.commit()
    print("✅ user_watchlists table created")

def migrate_old_watchlist(conn):
    """Migrate data from old watchlist to new user_watchlists"""
    cursor = conn.cursor()

    print("\n🔄 Migrating old watchlist data...")

    # Get all active symbols from old watchlist
    cursor.execute("SELECT symbol, added_at, notes FROM watchlist WHERE active = 1")
    old_watchlist = cursor.fetchall()

    if not old_watchlist:
        print("   No active watchlist entries to migrate")
        return

    # Default migration strategy: add to Wind Catcher 1h
    # (User can reorganize later via web interface)
    migrated_count = 0

    for symbol, added_at, notes in old_watchlist:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO user_watchlists
                (symbol, timeframe, direction, added_at, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (symbol, '1h', 'wind_catcher', added_at, notes or 'Migrated from old watchlist'))

            migrated_count += 1
        except Exception as e:
            print(f"   ⚠️ Could not migrate {symbol}: {e}")

    conn.commit()
    print(f"✅ Migrated {migrated_count} symbols to user_watchlists (Wind Catcher 1h)")
    print("   Note: You can reorganize symbols across timeframes/directions later")

def enhance_signals_table(conn):
    """Add new columns to signals table for confluence data"""
    cursor = conn.cursor()

    print("\n🔧 Enhancing signals table...")

    # Check which columns need to be added
    cursor.execute("PRAGMA table_info(signals)")
    existing_columns = [col[1] for col in cursor.fetchall()]

    new_columns = [
        ('timeframe', 'TEXT'),
        ('confluence_score', 'REAL'),
        ('confluence_class', 'TEXT'),
        ('indicators_firing', 'TEXT'),  # JSON field
        ('volume_level', 'TEXT'),
        ('volume_ratio', 'REAL'),
        ('details', 'TEXT'),  # JSON field
        ('notified', 'BOOLEAN DEFAULT 0')
    ]

    added_count = 0
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f'ALTER TABLE signals ADD COLUMN {col_name} {col_type}')
                print(f"   ✅ Added column: {col_name}")
                added_count += 1
            except Exception as e:
                print(f"   ⚠️ Could not add {col_name}: {e}")
        else:
            print(f"   ⏭️  Column already exists: {col_name}")

    conn.commit()
    print(f"✅ Enhanced signals table ({added_count} new columns)")

def add_database_indexes(conn):
    """Add performance indexes"""
    cursor = conn.cursor()

    print("\n🔧 Adding database indexes...")

    indexes = [
        ('idx_price_data_symbol_timeframe_timestamp',
         'price_data', '(symbol, timeframe, timestamp)'),

        ('idx_signals_timestamp',
         'signals', '(timestamp DESC)'),

        ('idx_signals_symbol_timeframe',
         'signals', '(symbol, timeframe)'),

        ('idx_signals_confluence_score',
         'signals', '(confluence_score DESC)'),

        ('idx_user_watchlists_timeframe_direction',
         'user_watchlists', '(timeframe, direction)')
    ]

    added_count = 0
    for index_name, table_name, columns in indexes:
        try:
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} {columns}')
            print(f"   ✅ Created index: {index_name}")
            added_count += 1
        except Exception as e:
            print(f"   ⚠️ Could not create {index_name}: {e}")

    conn.commit()
    print(f"✅ Added {added_count} database indexes")

def verify_migration(conn):
    """Verify the migration was successful"""
    cursor = conn.cursor()

    print("\n✅ Migration Verification:")
    print("="*60)

    # Check user_watchlists
    cursor.execute("SELECT COUNT(*) FROM user_watchlists")
    uwl_count = cursor.fetchone()[0]
    print(f"user_watchlists entries: {uwl_count}")

    if uwl_count > 0:
        cursor.execute("""
            SELECT symbol, timeframe, direction
            FROM user_watchlists
            LIMIT 5
        """)
        samples = cursor.fetchall()
        print("\nSample entries:")
        for symbol, tf, direction in samples:
            print(f"  - {symbol} ({tf}, {direction})")

    # Check signals table columns
    cursor.execute("PRAGMA table_info(signals)")
    signals_columns = [col[1] for col in cursor.fetchall()]
    print(f"\nSignals table now has {len(signals_columns)} columns:")
    print(f"  {', '.join(signals_columns)}")

    # Check indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
    indexes = cursor.fetchall()
    print(f"\nIndexes created: {len(indexes)}")
    for idx in indexes:
        print(f"  - {idx[0]}")

    print("="*60)

def main():
    """Run the database migration"""
    print("🚀 Wind Catcher & River Turn - Database Migration to V2")
    print("="*60)
    print("\nThis migration will:")
    print("  1. Create user_watchlists table (multi-timeframe support)")
    print("  2. Migrate existing watchlist data")
    print("  3. Enhance signals table with confluence fields")
    print("  4. Add performance indexes")
    print("\n⚠️  This is a NON-DESTRUCTIVE migration.")
    print("   Old tables remain intact for rollback if needed.")
    print("="*60)

    # Backup reminder
    if not backup_database():
        return False

    try:
        # Connect to database
        conn = sqlite3.connect(str(DATABASE_FILE))
        print(f"\n✅ Connected to database: {DATABASE_FILE}")

        # Check current schema
        schema_info = check_current_schema(conn)

        # Step 1: Create user_watchlists table
        if not schema_info['has_user_watchlists']:
            create_user_watchlists_table(conn)

            # Step 2: Migrate old watchlist
            if schema_info['active_watchlist_count'] > 0:
                migrate_old_watchlist(conn)
        else:
            print("\n⏭️  user_watchlists table already exists, skipping creation")

        # Step 3: Enhance signals table
        enhance_signals_table(conn)

        # Step 4: Add indexes
        add_database_indexes(conn)

        # Step 5: Verify
        verify_migration(conn)

        # Close connection
        conn.close()

        print("\n" + "="*60)
        print("✅ DATABASE MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nNext steps:")
        print("  1. Test the new schema with: python test_connection.py")
        print("  2. Review user_watchlists entries")
        print("  3. Update code to use new multi-timeframe features")
        print("\nOld tables (watchlist, etc.) are preserved for safety.")
        print("You can remove them after confirming everything works.")

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
