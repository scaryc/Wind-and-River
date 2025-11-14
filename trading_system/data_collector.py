"""
Data Collector for Wind Catcher & River Turn Trading System
This script fetches price data from Hyperliquid DEX and saves it to the database
"""

import time
from datetime import datetime
from utils import (
    load_config, connect_to_database, validate_ohlcv_data,
    normalize_timestamp, get_current_timestamp, log_message
)
from hyperliquid_connector import connect_to_hyperliquid

def connect_to_exchange(config):
    """Connect to Hyperliquid DEX with proper error handling"""
    try:
        exchange_name = config['exchange']['name'].lower()

        if exchange_name == 'hyperliquid':
            use_testnet = config['exchange'].get('use_testnet', False)
            connector = connect_to_hyperliquid(use_testnet=use_testnet)
            return connector
        else:
            print(f"❌ Unsupported exchange: {exchange_name}")
            print("   Currently only 'hyperliquid' is supported")
            return None

    except KeyError as e:
        print(f"❌ Missing configuration: {e}")
        print("   Check your config/config.yaml file")
        return None
    except Exception as e:
        print(f"❌ Failed to connect to exchange: {e}")
        return None

def get_watchlist(conn):
    """Get active coins from watchlist"""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
        symbols = [row[0] for row in cursor.fetchall()]
        return symbols
    finally:
        cursor.close()

def fetch_and_store_ohlcv(connector, conn, symbol, timeframe='1h', limit=24):
    """Fetch OHLCV data from Hyperliquid and store in database with validation"""
    cursor = None
    try:
        # Fetch data from Hyperliquid
        ohlcv_data = connector.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

        if not ohlcv_data:
            print(f"⚠️ No data received for {symbol}")
            return 0

        cursor = conn.cursor()
        stored_count = 0
        skipped_count = 0
        current_time = get_current_timestamp()

        for candle in ohlcv_data:
            try:
                # Validate candle data
                validate_ohlcv_data(candle)

                # Normalize timestamp to seconds
                timestamp = normalize_timestamp(candle[0])
                open_price = candle[1]
                high_price = candle[2]
                low_price = candle[3]
                close_price = candle[4]
                volume = candle[5]

                cursor.execute('''
                    INSERT OR REPLACE INTO price_data
                    (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (symbol, timeframe, timestamp, open_price, high_price,
                      low_price, close_price, volume, current_time))

                stored_count += 1

            except ValueError as e:
                skipped_count += 1
                print(f"⚠️ Skipped invalid candle for {symbol}: {e}")
            except Exception as e:
                print(f"⚠️ Error storing candle for {symbol}: {e}")

        conn.commit()

        if skipped_count > 0:
            print(f"⚠️ Skipped {skipped_count} invalid candles for {symbol}")

        return stored_count

    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")
        return 0
    finally:
        if cursor:
            cursor.close()

def show_latest_prices(conn):
    """Show the latest prices we've stored"""
    cursor = conn.cursor()
    try:
        print("\n📊 Latest Stored Prices:")
        print("-" * 60)

        cursor.execute('''
            SELECT symbol, close, timestamp, timeframe
            FROM price_data
            WHERE (symbol, timestamp) IN (
                SELECT symbol, MAX(timestamp)
                FROM price_data
                GROUP BY symbol
            )
            ORDER BY symbol
        ''')

        results = cursor.fetchall()

        for symbol, price, timestamp, timeframe in results:
            # Convert timestamp to readable date
            dt = datetime.fromtimestamp(timestamp)
            date_str = dt.strftime('%Y-%m-%d %H:%M')

            print(f"{symbol:12s} ${price:>10.2f} ({timeframe}) at {date_str}")
    finally:
        cursor.close()

def show_database_stats(conn):
    """Show database statistics"""
    cursor = conn.cursor()
    try:
        print("\n📈 Database Statistics:")
        print("-" * 40)

        # Total records
        cursor.execute("SELECT COUNT(*) FROM price_data")
        total_records = cursor.fetchone()[0]
        print(f"Total price records: {total_records}")

        # Records per symbol
        cursor.execute('''
            SELECT symbol, COUNT(*) as count
            FROM price_data
            GROUP BY symbol
            ORDER BY symbol
        ''')

        symbol_counts = cursor.fetchall()
        for symbol, count in symbol_counts:
            print(f"  {symbol}: {count} candles")

        # Date range
        cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM price_data")
        min_ts, max_ts = cursor.fetchone()

        if min_ts and max_ts:
            min_date = datetime.fromtimestamp(min_ts).strftime('%Y-%m-%d %H:%M')
            max_date = datetime.fromtimestamp(max_ts).strftime('%Y-%m-%d %H:%M')
            print(f"Data range: {min_date} to {max_date}")
    finally:
        cursor.close()

def main():
    """Main data collection function"""
    print("🚀 Wind Catcher & River Turn - Data Collector")
    print("="*50)

    # Load configuration
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ Configuration error: {e}")
        return
    
    # Connect to exchange
    exchange_name = config['exchange']['name']
    print(f"Connecting to {exchange_name}...")
    connector = connect_to_exchange(config)
    if not connector:
        return
    print(f"✅ Connected to {exchange_name}")
    
    # Connect to database
    print("Connecting to database...")
    try:
        conn = connect_to_database()
        print("✅ Connected to database")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("   Run database_setup.py first to create the database")
        return
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Get watchlist
    watchlist = get_watchlist(conn)
    print(f"📋 Found {len(watchlist)} coins in watchlist: {', '.join(watchlist)}")
    
    # Collect data for each symbol
    print("\n📥 Collecting price data...")
    total_stored = 0

    for symbol in watchlist:
        print(f"Fetching {symbol}...", end=' ')
        stored = fetch_and_store_ohlcv(connector, conn, symbol, timeframe='1h', limit=24)
        total_stored += stored
        print(f"✅ Stored {stored} candles")
        time.sleep(0.5)  # Be nice to the API (Hyperliquid is generous but still be respectful)
    
    print(f"\n✅ Collection complete! Stored {total_stored} total candles")
    
    # Show results
    show_latest_prices(conn)
    show_database_stats(conn)
    
    # Close connection
    conn.close()
    print("\n🎯 Data collection finished!")

if __name__ == "__main__":
    main()