"""
Generate Mock Trading Data - Set 2
Creates sample data when Hyperliquid API is not accessible
This demonstrates the structure and format of the reports
"""

import sys
import io

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

# Configuration for Set 2
SYMBOLS = ['SOL', 'AVAX', 'LINK', 'MATIC', 'UNI', 'AAVE']
TIMEFRAMES = ['4h', '30m', '5m']
LOOKBACK_DAYS = 21  # 3 weeks
OUTPUT_FILE = Path('../doc/TRADING_DATA_REPORT_SET2.xlsx')

# Mock price data (approximate current prices as of Nov 2025)
BASE_PRICES = {
    'SOL': 95.0,
    'AVAX': 32.0,
    'LINK': 14.5,
    'MATIC': 0.85,
    'UNI': 8.5,
    'AAVE': 170.0
}

def generate_mock_candles(symbol, timeframe, days):
    """Generate realistic mock candle data"""

    base_price = BASE_PRICES.get(symbol, 100.0)

    # Calculate candles needed
    if timeframe == '5m':
        num_candles = days * 288  # 288 candles per day
        interval_seconds = 5 * 60
    elif timeframe == '30m':
        num_candles = days * 48   # 48 candles per day
        interval_seconds = 30 * 60
    elif timeframe == '4h':
        num_candles = days * 6    # 6 candles per day
        interval_seconds = 4 * 60 * 60
    else:
        num_candles = 200
        interval_seconds = 3600

    # Generate timestamps (going backwards from now)
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    candles = []
    current_price = base_price

    for i in range(num_candles):
        timestamp = start_time + timedelta(seconds=i * interval_seconds)
        ts_unix = int(timestamp.timestamp())

        # Generate realistic price movement
        volatility = base_price * 0.02  # 2% volatility
        price_change = np.random.randn() * volatility
        current_price = max(current_price + price_change, base_price * 0.5)

        # OHLCV
        open_price = current_price
        high = open_price * (1 + abs(np.random.randn()) * 0.01)
        low = open_price * (1 - abs(np.random.randn()) * 0.01)
        close = low + (high - low) * np.random.random()
        volume = np.random.uniform(100000, 1000000) * (base_price / 100)

        candles.append({
            'timestamp': ts_unix,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

        current_price = close

    return candles

def store_mock_data_in_db():
    """Store mock data in database"""
    print("\n💾 Generating and storing mock data in database...")
    print("=" * 80)

    conn = sqlite3.connect('data/trading_system.db')
    cursor = conn.cursor()

    total_candles = 0

    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            print(f"\nGenerating {symbol} ({timeframe})...", end=' ')

            candles = generate_mock_candles(symbol, timeframe, LOOKBACK_DAYS)

            for candle in candles:
                cursor.execute("""
                    INSERT OR REPLACE INTO price_data
                    (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    symbol,
                    timeframe,
                    candle['timestamp'],
                    candle['open'],
                    candle['high'],
                    candle['low'],
                    candle['close'],
                    candle['volume']
                ))

                total_candles += 1

            print(f"✅ {len(candles)} candles")

    conn.commit()
    conn.close()

    print(f"\n✅ Stored {total_candles:,} candles in database")

def export_to_excel():
    """Export collected data to Excel"""
    print("\n📊 Exporting data to Excel...")

    conn = sqlite3.connect('data/trading_system.db')

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
                'Data Type',
                'Symbols',
                'Timeframes',
                'Lookback Period',
                'Generated On',
                'Total Candles',
                'Date Range',
                'Note'
            ],
            'Value': [
                'Set 2 - Alternative Trading Pairs',
                'Mock Data (for demonstration)',
                ', '.join(SYMBOLS),
                ', '.join(TIMEFRAMES),
                f'{LOOKBACK_DAYS} days (3 weeks)',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                f"{len(df):,}",
                f"{df['date'].min()} to {df['date'].max()}",
                'This is sample data generated for demonstration purposes'
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
    print("🚀 Mock Trading Data Report Generator - Set 2")
    print("=" * 80)
    print(f"📋 Configuration:")
    print(f"   Symbols: {', '.join(SYMBOLS)}")
    print(f"   Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"   Lookback: {LOOKBACK_DAYS} days (3 weeks)")
    print(f"   Output: {OUTPUT_FILE}")
    print(f"   Data Type: Mock/Sample Data")
    print("=" * 80)

    # Generate and store mock data
    store_mock_data_in_db()

    # Export to Excel
    export_to_excel()

    print("\n" + "=" * 80)
    print("✅ COMPLETE! Mock trading data report generated successfully!")
    print(f"📊 Open the file: {OUTPUT_FILE}")
    print("\nℹ️  Note: This is sample data for demonstration purposes.")
    print("   To use real data, run generate_trading_data_set2.py with API access.")
    print("=" * 80)

if __name__ == "__main__":
    main()
