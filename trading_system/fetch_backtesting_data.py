"""
Fetch Historical Data for Backtesting from Hyperliquid
Creates Excel file with historical OHLCV data for multiple symbols and timeframes
"""

import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from hyperliquid_connector import connect_to_hyperliquid
import time

# Configuration
SYMBOLS = ['ETH', 'NEAR', 'UNI', 'BTC', 'APT', 'AERO', 'DEEP', 'POPCAT', 'SUI', 'AAVE']
TIMEFRAMES = ['30m', '1h', '2h', '4h', '8h', '12h', '1d']
START_DATE = '2025-09-20'  # September 20, 2025
END_DATE = '2025-11-19'    # November 19, 2025
OUTPUT_FILE = Path('../doc/backtestingwatchlist.xlsx')

def calculate_candles_needed(start_date_str, end_date_str, timeframe):
    """
    Calculate how many candles are needed to cover the date range

    Args:
        start_date_str: Start date in 'YYYY-MM-DD' format
        end_date_str: End date in 'YYYY-MM-DD' format
        timeframe: Timeframe string (e.g., '1h', '4h', '1d')

    Returns:
        tuple: (start_timestamp_ms, end_timestamp_ms, num_candles)
    """
    # Parse dates as UTC
    start_dt = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)

    # Convert to milliseconds
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    # Calculate timeframe in milliseconds
    if timeframe.endswith('m'):
        minutes = int(timeframe[:-1])
        tf_ms = minutes * 60 * 1000
    elif timeframe.endswith('h'):
        hours = int(timeframe[:-1])
        tf_ms = hours * 60 * 60 * 1000
    elif timeframe.endswith('d'):
        days = int(timeframe[:-1])
        tf_ms = days * 24 * 60 * 60 * 1000
    else:
        tf_ms = 60 * 60 * 1000  # Default 1h

    # Calculate number of candles (add buffer for safety)
    time_diff = end_ms - start_ms
    num_candles = int(time_diff / tf_ms) + 10

    # Hyperliquid max is 5000
    num_candles = min(num_candles, 5000)

    return start_ms, end_ms, num_candles

def fetch_symbol_timeframe_data(connector, symbol, timeframe, start_ms, end_ms, num_candles):
    """
    Fetch historical data for a specific symbol and timeframe

    Args:
        connector: HyperliquidConnector instance
        symbol: Symbol to fetch (e.g., 'BTC')
        timeframe: Timeframe string
        start_ms: Start timestamp in milliseconds
        end_ms: End timestamp in milliseconds
        num_candles: Number of candles to fetch

    Returns:
        pandas.DataFrame: OHLCV data with columns [symbol, timeframe, timestamp, date, open, high, low, close, volume]
    """
    print(f"  📊 Fetching {symbol} {timeframe}...", end=' ')

    try:
        # Fetch candles using the connector's built-in method
        # The connector already handles start/end time calculation
        candles = connector.fetch_ohlcv(symbol, timeframe=timeframe, limit=num_candles)

        if not candles:
            print(f"❌ No data returned")
            return None

        # Filter candles to exact date range
        filtered_candles = []
        for candle in candles:
            timestamp_ms = candle[0]
            if start_ms <= timestamp_ms <= end_ms:
                filtered_candles.append(candle)

        if not filtered_candles:
            print(f"⚠️  No candles in date range")
            return None

        # Convert to DataFrame
        df = pd.DataFrame(filtered_candles, columns=['timestamp_ms', 'open', 'high', 'low', 'close', 'volume'])

        # Add metadata columns
        df['symbol'] = symbol
        df['timeframe'] = timeframe

        # Convert timestamp to seconds (from milliseconds)
        df['timestamp'] = df['timestamp_ms'] / 1000

        # Add readable date column
        df['date'] = pd.to_datetime(df['timestamp_ms'], unit='ms')

        # Reorder columns to match expected format
        df = df[['symbol', 'timeframe', 'timestamp', 'date', 'open', 'high', 'low', 'close', 'volume']]

        print(f"✅ {len(df)} candles ({df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')})")

        return df

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def fetch_all_data():
    """
    Fetch all data for all symbols and timeframes

    Returns:
        dict: {symbol: DataFrame with all timeframes combined}
    """
    print("\n" + "=" * 80)
    print("📥 FETCHING BACKTESTING DATA FROM HYPERLIQUID")
    print("=" * 80)
    print(f"\n📅 Date Range: {START_DATE} to {END_DATE}")
    print(f"📊 Symbols: {', '.join(SYMBOLS)}")
    print(f"⏱️  Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"📦 Total combinations: {len(SYMBOLS)} × {len(TIMEFRAMES)} = {len(SYMBOLS) * len(TIMEFRAMES)}")

    # Connect to Hyperliquid
    print("\n🔗 Connecting to Hyperliquid...")
    connector = connect_to_hyperliquid(use_testnet=False)

    if not connector:
        print("❌ Failed to connect to Hyperliquid")
        return None

    print("✅ Connected successfully!")

    # Fetch data for each symbol
    data_by_symbol = {}
    total_fetched = 0
    total_failed = 0

    for symbol in SYMBOLS:
        print(f"\n{'─' * 80}")
        print(f"📈 Fetching {symbol}...")
        print(f"{'─' * 80}")

        symbol_dfs = []

        for timeframe in TIMEFRAMES:
            # Calculate date range and candles needed
            start_ms, end_ms, num_candles = calculate_candles_needed(START_DATE, END_DATE, timeframe)

            # Fetch data
            df = fetch_symbol_timeframe_data(connector, symbol, timeframe, start_ms, end_ms, num_candles)

            if df is not None:
                symbol_dfs.append(df)
                total_fetched += 1
            else:
                total_failed += 1

            # Small delay to avoid rate limiting
            time.sleep(0.5)

        # Combine all timeframes for this symbol
        if symbol_dfs:
            combined_df = pd.concat(symbol_dfs, ignore_index=True)
            data_by_symbol[symbol] = combined_df
            print(f"\n  ✅ {symbol}: {len(combined_df)} total candles across {len(symbol_dfs)} timeframes")

    print("\n" + "=" * 80)
    print(f"✅ FETCH COMPLETE: {total_fetched} successful, {total_failed} failed")
    print("=" * 80)

    return data_by_symbol

def save_to_excel(data_by_symbol):
    """
    Save data to Excel file with each symbol as a separate sheet

    Args:
        data_by_symbol: Dictionary of {symbol: DataFrame}
    """
    print(f"\n💾 Saving data to {OUTPUT_FILE}...")
    print("=" * 80)

    # Create parent directory if it doesn't exist
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Create Excel writer
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:

        # Create summary sheet
        summary_data = []
        total_candles = 0

        for symbol in SYMBOLS:
            if symbol in data_by_symbol:
                df = data_by_symbol[symbol]

                # Count candles per timeframe
                for timeframe in TIMEFRAMES:
                    tf_df = df[df['timeframe'] == timeframe]
                    candle_count = len(tf_df)
                    total_candles += candle_count

                    if candle_count > 0:
                        date_range = f"{tf_df['date'].min().strftime('%Y-%m-%d')} to {tf_df['date'].max().strftime('%Y-%m-%d')}"
                    else:
                        date_range = "No data"

                    summary_data.append({
                        'Symbol': symbol,
                        'Timeframe': timeframe,
                        'Candles': candle_count,
                        'Date Range': date_range
                    })

        # Write summary sheet
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        print(f"  ✅ Summary sheet: {len(summary_data)} entries")

        # Write each symbol as a separate sheet
        for symbol, df in data_by_symbol.items():
            # Sort by timeframe and timestamp
            df = df.sort_values(['timeframe', 'timestamp'])

            df.to_excel(writer, sheet_name=symbol, index=False)
            print(f"  ✅ {symbol} sheet: {len(df)} rows")

    print("\n" + "=" * 80)
    print(f"✅ SAVED: {OUTPUT_FILE}")
    print(f"   Total symbols: {len(data_by_symbol)}")
    print(f"   Total candles: {total_candles:,}")
    print("=" * 80)

def main():
    """
    Main execution function
    """
    print("\n" + "=" * 80)
    print("🚀 BACKTESTING DATA FETCHER")
    print("=" * 80)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = time.time()

    # Fetch data
    data_by_symbol = fetch_all_data()

    if not data_by_symbol:
        print("\n❌ No data fetched. Exiting.")
        return

    # Save to Excel
    save_to_excel(data_by_symbol)

    # Print completion
    elapsed = time.time() - start_time
    print(f"\n⏱️  Total time: {elapsed:.1f} seconds")
    print(f"✅ Complete! File ready at: {OUTPUT_FILE.resolve()}")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
