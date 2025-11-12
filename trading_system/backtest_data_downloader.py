"""
Historical Data Downloader for Backtesting
Downloads OHLCV data for specified date ranges
"""

import ccxt
import yaml
import sqlite3
import time
from datetime import datetime, timedelta
import pandas as pd


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


def download_historical_data(exchange, symbol, timeframe, start_date, end_date, limit=1000):
    """
    Download OHLCV data for specified period

    Parameters:
    - exchange: CCXT exchange object
    - symbol: Trading pair (e.g., 'BTC/USDT')
    - timeframe: Timeframe (e.g., '1h')
    - start_date: Start date string 'YYYY-MM-DD'
    - end_date: End date string 'YYYY-MM-DD'
    - limit: Max candles per API call (Gate.io limit: ~1000)

    Returns:
    - DataFrame with OHLCV data
    """
    print(f"\n📥 Downloading {symbol} [{timeframe}] from {start_date} to {end_date}")

    # Convert dates to timestamps
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')

    start_ts = int(start_dt.timestamp() * 1000)  # milliseconds
    end_ts = int(end_dt.timestamp() * 1000)

    print(f"  Start: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  End:   {end_dt.strftime('%Y-%m-%d %H:%M:%S')}")

    # Calculate timeframe in milliseconds
    timeframe_map = {
        '1m': 60 * 1000,
        '5m': 5 * 60 * 1000,
        '15m': 15 * 60 * 1000,
        '30m': 30 * 60 * 1000,
        '1h': 60 * 60 * 1000,
        '2h': 2 * 60 * 60 * 1000,
        '4h': 4 * 60 * 60 * 1000,
        '8h': 8 * 60 * 60 * 1000,
        '1d': 24 * 60 * 60 * 1000,
    }

    tf_ms = timeframe_map.get(timeframe, 60 * 60 * 1000)

    # Fetch data in chunks
    all_candles = []
    current_ts = start_ts
    chunk_count = 0

    while current_ts < end_ts:
        try:
            print(f"  Fetching chunk {chunk_count + 1}... ", end='', flush=True)

            # Fetch candles
            candles = exchange.fetch_ohlcv(
                symbol,
                timeframe,
                since=current_ts,
                limit=limit
            )

            if not candles:
                print("No data")
                break

            # Filter candles within date range
            filtered_candles = [c for c in candles if c[0] <= end_ts]
            all_candles.extend(filtered_candles)

            print(f"Got {len(filtered_candles)} candles")

            # Move to next chunk
            last_ts = candles[-1][0]

            # If we got the same timestamp, break to avoid infinite loop
            if last_ts <= current_ts:
                break

            current_ts = last_ts + tf_ms
            chunk_count += 1

            # Rate limiting
            time.sleep(0.6)

            # Stop if we've passed the end date
            if last_ts >= end_ts:
                break

        except Exception as e:
            print(f"\n  ⚠️  Error fetching chunk: {e}")
            break

    # Convert to DataFrame
    if all_candles:
        df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = df['timestamp'] // 1000  # Convert to seconds
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')

        # Remove duplicates
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)

        print(f"\n  ✅ Downloaded {len(df)} candles")
        print(f"  Date range: {df['datetime'].min()} to {df['datetime'].max()}")

        return df
    else:
        print(f"\n  ❌ No data downloaded")
        return None


def store_historical_data(conn, symbol, timeframe, df):
    """Store historical data in database"""
    if df is None or df.empty:
        return 0

    cursor = conn.cursor()
    stored_count = 0
    current_time = int(datetime.now().timestamp())

    print(f"  💾 Storing to database... ", end='', flush=True)

    for _, row in df.iterrows():
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO price_data
                (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, timeframe, int(row['timestamp']),
                  row['open'], row['high'], row['low'], row['close'],
                  row['volume'], current_time))

            stored_count += 1

        except Exception as e:
            print(f"\n    ⚠️  Error storing row: {e}")

    conn.commit()
    print(f"✅ Stored {stored_count} candles")

    return stored_count


def download_backtest_dataset(config, symbols, timeframe='1h', start_date='2024-10-03', end_date='2024-11-03'):
    """
    Download complete backtest dataset for multiple symbols

    Parameters:
    - config: Configuration dict
    - symbols: List of symbols to download
    - timeframe: Timeframe to download
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    """
    print("="*70)
    print("📊 Historical Data Download for Backtesting")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Symbols: {', '.join(symbols)}")
    print(f"  Timeframe: {timeframe}")
    print(f"  Period: {start_date} to {end_date}")

    # Connect to exchange
    print("\nConnecting to Gate.io...")
    exchange = connect_to_exchange(config)
    if not exchange:
        return False
    print("✅ Connected to exchange")

    # Connect to database
    print("Connecting to database...")
    conn = connect_to_database()
    if not conn:
        return False
    print("✅ Connected to database")

    # Download data for each symbol
    total_stored = 0
    successful = 0

    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] {symbol}")
        print("-"*70)

        try:
            # Download data
            df = download_historical_data(
                exchange,
                symbol,
                timeframe,
                start_date,
                end_date
            )

            if df is not None:
                # Store in database
                stored = store_historical_data(conn, symbol, timeframe, df)
                total_stored += stored
                successful += 1
                print(f"  ✅ Completed {symbol}")
            else:
                print(f"  ⚠️  No data for {symbol}")

        except Exception as e:
            print(f"  ❌ Error processing {symbol}: {e}")

    # Summary
    print("\n" + "="*70)
    print("📊 Download Summary")
    print("="*70)
    print(f"  Symbols processed: {len(symbols)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {len(symbols) - successful}")
    print(f"  Total candles stored: {total_stored}")
    print("="*70)

    conn.close()
    return True


def main():
    """Main execution"""
    print("🚀 Backtest Historical Data Downloader")
    print()

    # Load config
    config = load_config()
    if not config:
        return

    # Backtest configuration from development plan
    backtest_symbols = ['BTC/USDT', 'TAO/USDT', 'HYPE/USDT']
    backtest_timeframe = '1h'
    backtest_start = '2024-10-03'
    backtest_end = '2024-11-03'

    # Download data
    success = download_backtest_dataset(
        config,
        backtest_symbols,
        backtest_timeframe,
        backtest_start,
        backtest_end
    )

    if success:
        print("\n✅ Historical data download complete!")
        print("\n💡 Next steps:")
        print("   1. Run backtest_runner.py to generate signals")
        print("   2. Run backtest_reporter.py to create analysis report")
    else:
        print("\n❌ Download incomplete - check errors above")


if __name__ == "__main__":
    main()
