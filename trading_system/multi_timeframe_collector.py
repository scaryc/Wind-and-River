"""
Multi-Timeframe Data Collector for Wind Catcher & River Turn
Collects data for all symbols/timeframes in user_watchlists
"""

import sqlite3
from datetime import datetime
import time
from utils import DATABASE_FILE, load_config, get_current_timestamp
from hyperliquid_connector import HyperliquidConnector

def get_watchlist_requirements(conn):
    """
    Get unique symbols and timeframes from user_watchlists
    Returns: (set of symbols, set of timeframes)
    """
    cursor = conn.cursor()

    # Get all active entries from user_watchlists
    cursor.execute("""
        SELECT DISTINCT symbol, timeframe
        FROM user_watchlists
    """)

    entries = cursor.fetchall()

    symbols = set()
    timeframes = set()

    for symbol, timeframe in entries:
        symbols.add(symbol)
        timeframes.add(timeframe)

    cursor.close()

    return symbols, timeframes

def collect_multi_timeframe_data(symbols, timeframes, config, conn, limit=200):
    """
    Collect data for all symbol/timeframe combinations

    Args:
        symbols: Set of symbols to fetch
        timeframes: Set of timeframes to fetch
        config: Configuration dict
        conn: Database connection
        limit: Number of candles to fetch per symbol/timeframe

    Returns:
        dict with statistics
    """
    # Initialize connector
    use_testnet = config['exchange'].get('use_testnet', False)
    connector = HyperliquidConnector(use_testnet=use_testnet)

    stats = {
        'total_combinations': 0,
        'successful': 0,
        'failed': 0,
        'candles_stored': 0,
        'errors': []
    }

    # Calculate rate limit (Hyperliquid allows ~5 calls/sec)
    max_calls_per_second = config['system'].get('max_api_calls_per_second', 5)
    delay_between_calls = 1.0 / max_calls_per_second

    print(f"\n🔄 Multi-Timeframe Data Collection")
    print(f"="*60)
    print(f"Symbols: {len(symbols)}")
    print(f"Timeframes: {sorted(timeframes)}")
    print(f"Total combinations: {len(symbols) * len(timeframes)}")
    print(f"Rate limit: {max_calls_per_second} calls/second")
    print(f"="*60)

    cursor = conn.cursor()

    for symbol in sorted(symbols):
        for timeframe in sorted(timeframes):
            stats['total_combinations'] += 1

            try:
                print(f"\n📊 {symbol} ({timeframe})...", end=" ")

                # Fetch OHLCV data
                ohlcv = connector.fetch_ohlcv(symbol, timeframe, limit=limit)

                if not ohlcv or len(ohlcv) == 0:
                    print(f"⚠️  No data")
                    stats['failed'] += 1
                    stats['errors'].append(f"{symbol} {timeframe}: No data returned")
                    continue

                # Store in database
                stored_count = 0
                current_time = get_current_timestamp()

                for candle in ohlcv:
                    timestamp, open_price, high, low, close, volume = candle

                    # Convert timestamp from ms to seconds if needed
                    if timestamp > 10000000000:
                        timestamp = timestamp // 1000

                    try:
                        cursor.execute('''
                            INSERT OR REPLACE INTO price_data
                            (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (symbol, timeframe, timestamp, open_price, high, low, close, volume, current_time))
                        stored_count += 1
                    except Exception as e:
                        stats['errors'].append(f"{symbol} {timeframe} candle error: {e}")

                conn.commit()
                stats['successful'] += 1
                stats['candles_stored'] += stored_count

                print(f"✅ {stored_count} candles")

                # Rate limiting
                time.sleep(delay_between_calls)

            except Exception as e:
                print(f"❌ Error: {e}")
                stats['failed'] += 1
                stats['errors'].append(f"{symbol} {timeframe}: {str(e)}")
                continue

    cursor.close()

    return stats

def print_collection_summary(stats):
    """Print summary of data collection"""
    print(f"\n" + "="*60)
    print(f"📊 COLLECTION SUMMARY")
    print(f"="*60)
    print(f"Total combinations processed: {stats['total_combinations']}")
    print(f"✅ Successful: {stats['successful']}")
    print(f"❌ Failed: {stats['failed']}")
    print(f"📈 Total candles stored: {stats['candles_stored']}")

    if stats['errors']:
        print(f"\n⚠️  Errors ({len(stats['errors'])}):")
        for error in stats['errors'][:10]:  # Show first 10 errors
            print(f"  - {error}")
        if len(stats['errors']) > 10:
            print(f"  ... and {len(stats['errors']) - 10} more errors")

    print(f"="*60)

def main():
    """Main data collection function"""
    print("🚀 Wind Catcher & River Turn - Multi-Timeframe Data Collector")
    print("="*60)

    # Load config
    config = load_config()

    # Connect to database
    conn = sqlite3.connect(str(DATABASE_FILE))

    try:
        # Get watchlist requirements
        symbols, timeframes = get_watchlist_requirements(conn)

        if not symbols:
            print("\n⚠️  No symbols in user_watchlists table")
            print("   Add symbols using update_watchlist.py or manually insert into user_watchlists")
            return

        if not timeframes:
            print("\n⚠️  No timeframes found in user_watchlists")
            return

        # Collect data
        stats = collect_multi_timeframe_data(symbols, timeframes, config, conn, limit=200)

        # Print summary
        print_collection_summary(stats)

        # Show latest data
        cursor = conn.cursor()
        print(f"\n📋 Latest Data Per Symbol/Timeframe:")
        print("-"*60)

        for symbol in sorted(symbols):
            for timeframe in sorted(timeframes):
                cursor.execute("""
                    SELECT timestamp, close, volume
                    FROM price_data
                    WHERE symbol = ? AND timeframe = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (symbol, timeframe))

                row = cursor.fetchone()
                if row:
                    ts, close_price, volume = row
                    dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
                    print(f"  {symbol:12s} {timeframe:4s} - ${close_price:10.2f} @ {dt}")

        cursor.close()

        print("\n✅ Multi-timeframe data collection complete!")

    except Exception as e:
        print(f"\n❌ Error during collection: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
