"""
Generate Trading Data Report - Set 2
Collects data from different trading pairs and time period
Based on create_signals_report.py but with different parameters
"""

import sys
import io

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time
from utils import connect_to_database
from hyperliquid_connector import connect_to_hyperliquid

# DIFFERENT Configuration for Set 2
SYMBOLS = ['SOL', 'AVAX', 'LINK', 'MATIC', 'UNI', 'AAVE']  # Different trading pairs
TIMEFRAMES = ['4h', '30m', '5m']  # Different timeframes
LOOKBACK_DAYS = 21  # 3 weeks instead of 2
OUTPUT_FILE = Path('../doc/TRADING_DATA_REPORT_SET2.xlsx')

def collect_historical_data(connector, symbols, timeframes, days):
    """
    Collect historical data for specified symbols and timeframes

    Returns:
        dict: {(symbol, timeframe): candles_data}
    """
    print(f"\n📥 Collecting {days} days of historical data...")
    print("=" * 80)

    data_collected = {}
    total_combinations = len(symbols) * len(timeframes)
    current = 0

    for symbol in symbols:
        for timeframe in timeframes:
            current += 1
            print(f"\n[{current}/{total_combinations}] {symbol} ({timeframe})...", end=' ')

            # Calculate number of candles needed
            if timeframe == '5m':
                limit = days * 288  # 288 candles per day (5-min intervals)
            elif timeframe == '30m':
                limit = days * 48   # 48 candles per day
            elif timeframe == '4h':
                limit = days * 6    # 6 candles per day
            else:
                limit = 200

            # Fetch candles
            try:
                candles = connector.fetch_ohlcv(symbol, timeframe, limit=limit)

                if candles:
                    print(f"✅ {len(candles)} candles")
                    data_collected[(symbol, timeframe)] = candles
                else:
                    print("❌ Failed")
            except Exception as e:
                print(f"❌ Error: {e}")

            # Rate limiting
            time.sleep(0.2)

    print("\n" + "=" * 80)
    print(f"✅ Data collection complete: {len(data_collected)}/{total_combinations} successful")
    return data_collected

def store_data_in_db(data_collected):
    """Store collected data in database"""
    print("\n💾 Storing data in database...")

    conn = connect_to_database()
    cursor = conn.cursor()

    total_candles = 0

    for (symbol, timeframe), candles in data_collected.items():
        for candle in candles:
            timestamp, open_p, high, low, close, volume = candle

            cursor.execute("""
                INSERT OR REPLACE INTO price_data
                (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (symbol, timeframe, timestamp/1000, open_p, high, low, close, volume))

            total_candles += 1

    conn.commit()
    conn.close()

    print(f"✅ Stored {total_candles:,} candles in database")

def export_to_excel():
    """Export collected data to Excel"""
    print("\n📊 Exporting data to Excel...")

    conn = connect_to_database()

    # Get all price data for our symbols
    symbols_str = "'" + "', '".join(SYMBOLS) + "'"
    query = f"""
        SELECT
            symbol,
            timeframe,
            timestamp,
            open, high, low, close, volume
        FROM price_data
        WHERE symbol IN ({symbols_str})
        ORDER BY symbol, timeframe, timestamp DESC
    """

    df = pd.read_sql_query(query, conn)
    df['date'] = pd.to_datetime(df['timestamp'], unit='s')

    # Create summary
    summary = df.groupby(['symbol', 'timeframe']).agg({
        'timestamp': ['count', 'min', 'max'],
        'close': ['first', 'min', 'max', 'mean']
    }).reset_index()

    summary.columns = ['Symbol', 'Timeframe', 'Candles', 'First_Timestamp', 'Last_Timestamp',
                       'Latest_Price', 'Min_Price', 'Max_Price', 'Avg_Price']

    summary['First_Date'] = pd.to_datetime(summary['First_Timestamp'], unit='s')
    summary['Last_Date'] = pd.to_datetime(summary['Last_Timestamp'], unit='s')
    summary['Period_Days'] = (summary['Last_Date'] - summary['First_Date']).dt.days

    # Reorder columns
    summary = summary[['Symbol', 'Timeframe', 'Candles', 'First_Date', 'Last_Date',
                       'Period_Days', 'Latest_Price', 'Min_Price', 'Max_Price', 'Avg_Price']]

    # Export to Excel
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        # Summary sheet
        summary.to_excel(writer, sheet_name='Summary', index=False)

        # Metadata sheet
        metadata = pd.DataFrame({
            'Property': [
                'Dataset',
                'Symbols',
                'Timeframes',
                'Lookback Period',
                'Generated On',
                'Total Candles',
                'Date Range'
            ],
            'Value': [
                'Set 2 - Alternative Trading Pairs',
                ', '.join(SYMBOLS),
                ', '.join(TIMEFRAMES),
                f'{LOOKBACK_DAYS} days (3 weeks)',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                f"{len(df):,}",
                f"{df['date'].min()} to {df['date'].max()}"
            ]
        })
        metadata.to_excel(writer, sheet_name='Metadata', index=False)

        # Per-symbol sheets with recent data
        for symbol in SYMBOLS:
            symbol_df = df[df['symbol'] == symbol].head(2000)  # Last 2000 candles
            if not symbol_df.empty:
                symbol_df.to_excel(writer, sheet_name=symbol, index=False)

    conn.close()

    print(f"✅ Excel report saved to: {OUTPUT_FILE}")
    print(f"\nSummary:")
    print(summary.to_string(index=False))

def main():
    """Main execution"""
    print("🚀 Trading Data Report Generator - Set 2")
    print("=" * 80)
    print(f"📋 Configuration:")
    print(f"   Symbols: {', '.join(SYMBOLS)}")
    print(f"   Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"   Lookback: {LOOKBACK_DAYS} days (3 weeks)")
    print(f"   Output: {OUTPUT_FILE}")
    print("=" * 80)

    # Step 1: Connect to exchange
    print("\n🔄 STEP 1: Connecting to Hyperliquid")
    connector = connect_to_hyperliquid(use_testnet=False)
    if not connector:
        print("❌ Failed to connect to Hyperliquid")
        return

    # Step 2: Collect data
    print("\n🔄 STEP 2: Data Collection")
    data_collected = collect_historical_data(
        connector,
        SYMBOLS,
        TIMEFRAMES,
        LOOKBACK_DAYS
    )

    if not data_collected:
        print("❌ No data collected")
        return

    # Step 3: Store in database
    print("\n🔄 STEP 3: Database Storage")
    store_data_in_db(data_collected)

    # Step 4: Export to Excel
    print("\n🔄 STEP 4: Export to Excel")
    export_to_excel()

    print("\n" + "=" * 80)
    print("✅ COMPLETE! Trading data report generated successfully!")
    print(f"📊 Open the file: {OUTPUT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
