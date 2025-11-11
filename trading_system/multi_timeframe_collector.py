"""
Multi-Timeframe Data Collector for Wind Catcher & River Turn
Fetches OHLCV data for 8h, 1h, and 15m timeframes
"""

import ccxt
import yaml
import sqlite3
import time
from datetime import datetime


def load_config():
    """Load configuration from config.yaml"""
    try:
        with open('config/config.yaml', 'r') as file:
            config = yaml.safe_load(file)
            return config
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None


def connect_to_exchange(config):
    """Connect to Gate.io exchange"""
    try:
        exchange = ccxt.gateio({
            'apiKey': config['exchange']['api_key'],
            'secret': config['exchange']['api_secret'],
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        exchange.load_markets()
        return exchange
    except Exception as e:
        print(f"❌ Failed to connect to exchange: {e}")
        return None


def connect_to_database():
    """Connect to SQLite database"""
    try:
        conn = sqlite3.connect('data/trading_system.db')
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return None


def get_active_watchlist_pairs(conn):
    """Get unique symbols from all user watchlists"""
    cursor = conn.cursor()

    # Get unique symbols from user_watchlists
    cursor.execute("SELECT DISTINCT symbol FROM user_watchlists")
    symbols = [row[0] for row in cursor.fetchall()]

    # If no user watchlists, fall back to legacy watchlist
    if not symbols:
        cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
        symbols = [row[0] for row in cursor.fetchall()]
        if symbols:
            print("ℹ️  Using legacy watchlist (user_watchlists is empty)")

    return symbols


def fetch_ohlcv_multi_timeframe(exchange, symbol, timeframes, limit=200):
    """
    Fetch multiple timeframes for one symbol

    Parameters:
    - exchange: CCXT exchange object
    - symbol: Trading pair (e.g., 'BTC/USDT')
    - timeframes: List of timeframes (e.g., ['8h', '1h', '15m'])
    - limit: Number of candles per timeframe

    Returns:
    - dict: {timeframe: ohlcv_data}
    """
    result = {}

    for timeframe in timeframes:
        try:
            ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            result[timeframe] = ohlcv_data

            # Rate limiting - Gate.io allows ~2 calls/sec
            time.sleep(0.6)

        except Exception as e:
            print(f"    ⚠️  Error fetching {timeframe}: {e}")
            result[timeframe] = []

    return result


def store_ohlcv_data(conn, symbol, timeframe, ohlcv_data):
    """Store OHLCV data in database"""
    if not ohlcv_data:
        return 0

    cursor = conn.cursor()
    stored_count = 0
    current_time = int(datetime.now().timestamp())

    for candle in ohlcv_data:
        timestamp = candle[0] // 1000  # Convert ms to seconds
        open_price = candle[1]
        high_price = candle[2]
        low_price = candle[3]
        close_price = candle[4]
        volume = candle[5]

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO price_data
                (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, timeframe, timestamp, open_price, high_price,
                  low_price, close_price, volume, current_time))

            stored_count += 1

        except Exception as e:
            print(f"      ⚠️  Error storing candle: {e}")

    conn.commit()
    return stored_count


def collect_all_watchlist_data(conn, config, timeframes=['8h', '1h', '15m'], limit=200):
    """
    Main collection loop - fetches data for all pairs in watchlists

    Parameters:
    - conn: Database connection
    - config: Configuration dict
    - timeframes: List of timeframes to fetch
    - limit: Number of candles per timeframe
    """
    print("🔄 Multi-Timeframe Data Collection")
    print("="*60)

    # Connect to exchange
    print("Connecting to Gate.io...")
    exchange = connect_to_exchange(config)
    if not exchange:
        return False
    print("✅ Connected to Gate.io")

    # Get watchlist pairs
    symbols = get_active_watchlist_pairs(conn)

    if not symbols:
        print("⚠️  No symbols in watchlist. Add symbols to user_watchlists table.")
        return False

    print(f"📋 Collecting data for {len(symbols)} symbols: {', '.join(symbols)}")
    print(f"⏱️  Timeframes: {', '.join(timeframes)}")
    print(f"📊 Candles per timeframe: {limit}")
    print()

    # Collect data for each symbol
    total_stored = 0
    start_time = time.time()

    for i, symbol in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {symbol}")

        try:
            # Fetch all timeframes for this symbol
            multi_tf_data = fetch_ohlcv_multi_timeframe(exchange, symbol, timeframes, limit)

            # Store each timeframe
            for tf in timeframes:
                if multi_tf_data.get(tf):
                    stored = store_ohlcv_data(conn, symbol, tf, multi_tf_data[tf])
                    total_stored += stored
                    print(f"  ✅ {tf:4s}: {stored:3d} candles")
                else:
                    print(f"  ⚠️  {tf:4s}: No data")

        except Exception as e:
            print(f"  ❌ Error: {e}")

        print()

    # Summary
    elapsed = time.time() - start_time
    print("="*60)
    print(f"✅ Collection Complete!")
    print(f"   Total candles stored: {total_stored}")
    print(f"   Time elapsed: {elapsed:.1f} seconds")
    print("="*60)

    return True


def show_collection_stats(conn):
    """Show statistics about collected data"""
    cursor = conn.cursor()

    print("\n📊 Collection Statistics:")
    print("-"*60)

    # Count by timeframe
    cursor.execute('''
        SELECT timeframe, COUNT(*) as count
        FROM price_data
        GROUP BY timeframe
        ORDER BY
            CASE timeframe
                WHEN '8h' THEN 1
                WHEN '1h' THEN 2
                WHEN '15m' THEN 3
                ELSE 4
            END
    ''')

    tf_stats = cursor.fetchall()
    print("\nCandles by Timeframe:")
    for tf, count in tf_stats:
        print(f"  {tf:4s}: {count:>6d} candles")

    # Count by symbol
    cursor.execute('''
        SELECT symbol, timeframe, COUNT(*) as count
        FROM price_data
        GROUP BY symbol, timeframe
        ORDER BY symbol, timeframe
    ''')

    symbol_stats = cursor.fetchall()
    print("\nCandles by Symbol & Timeframe:")
    current_symbol = None
    for symbol, tf, count in symbol_stats:
        if symbol != current_symbol:
            current_symbol = symbol
            print(f"\n  {symbol}:")
        print(f"    {tf:4s}: {count:>4d} candles")

    # Latest data timestamps
    cursor.execute('''
        SELECT symbol, timeframe, MAX(timestamp) as latest
        FROM price_data
        GROUP BY symbol, timeframe
        ORDER BY symbol, timeframe
    ''')

    latest_data = cursor.fetchall()
    print("\nLatest Data Timestamps:")
    current_symbol = None
    for symbol, tf, timestamp in latest_data:
        if symbol != current_symbol:
            current_symbol = symbol
            print(f"\n  {symbol}:")
        dt = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
        print(f"    {tf:4s}: {dt}")


def add_test_watchlist(conn):
    """Add test symbols to user_watchlists for testing"""
    cursor = conn.cursor()
    current_time = int(datetime.now().timestamp())

    # Test watchlists from development plan
    test_watchlists = [
        ('BTC/USDT', '8h', 'wind_catcher'),
        ('BTC/USDT', '1h', 'wind_catcher'),
        ('TAO/USDT', '1h', 'wind_catcher'),
        ('HYPE/USDT', '15m', 'river_turn'),
    ]

    print("📝 Adding test watchlists...")
    for symbol, tf, direction in test_watchlists:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO user_watchlists
                (symbol, timeframe, direction, added_at, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (symbol, tf, direction, current_time, 'Test setup'))
            print(f"  ✅ Added: {symbol} [{tf}] - {direction}")
        except Exception as e:
            print(f"  ⚠️  Error adding {symbol}: {e}")

    conn.commit()
    print("✅ Test watchlists added\n")


def main():
    """Main execution function"""
    print("🚀 Wind Catcher & River Turn - Multi-Timeframe Collector")
    print("="*60)

    # Load configuration
    config = load_config()
    if not config:
        return

    # Connect to database
    print("Connecting to database...")
    conn = connect_to_database()
    if not conn:
        return
    print("✅ Connected to database\n")

    # Check if user_watchlists is empty, if so add test data
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_watchlists")
    count = cursor.fetchone()[0]

    if count == 0:
        print("ℹ️  User watchlists empty. Adding test data...")
        add_test_watchlist(conn)

    # Collect data
    success = collect_all_watchlist_data(
        conn,
        config,
        timeframes=['8h', '1h', '15m'],
        limit=200
    )

    if success:
        # Show statistics
        show_collection_stats(conn)

    # Close connection
    conn.close()
    print("\n🎯 Multi-timeframe collection finished!")


if __name__ == "__main__":
    main()
