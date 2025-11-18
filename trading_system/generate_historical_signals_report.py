"""
Generate Historical Signals Report
Collects 2 weeks of data and generates ALL signals (including WEAK) for analysis
Exports to Excel for easy filtering and review
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
from datetime import datetime, timedelta
import time
from pathlib import Path
from utils import connect_to_database, load_config
from hyperliquid_connector import connect_to_hyperliquid
from master_confluence import analyze_master_confluence

# Configuration
SYMBOLS = ['BTC', 'ETH', 'DOT', 'FET', 'HYPE', 'ICP']
TIMEFRAMES = ['12h', '1h', '15m']
LOOKBACK_DAYS = 14  # 2 weeks
OUTPUT_FILE = Path('../doc/SIGNALS_REPORT_2_WEEKS.xlsx')

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
            if timeframe == '15m':
                limit = days * 96  # 96 candles per day
            elif timeframe == '1h':
                limit = days * 24  # 24 candles per day
            elif timeframe == '12h':
                limit = days * 2   # 2 candles per day
            else:
                limit = 200

            # Fetch candles
            candles = connector.fetch_ohlcv(symbol, timeframe, limit=limit)

            if candles:
                print(f"✅ {len(candles)} candles")
                data_collected[(symbol, timeframe)] = candles
            else:
                print("❌ Failed")

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

def generate_signals_for_all_data():
    """
    Generate signals for all symbol/timeframe combinations
    Includes ALL signals (even WEAK ones)

    Returns:
        list: List of signal dictionaries
    """
    print("\n🔍 Generating signals for all data...")
    print("=" * 80)

    conn = connect_to_database()
    cursor = conn.cursor()

    # Get all symbol/timeframe combinations with data
    cursor.execute("""
        SELECT DISTINCT symbol, timeframe
        FROM price_data
        WHERE symbol IN ('BTC', 'ETH', 'DOT', 'FET', 'HYPE', 'ICP')
        ORDER BY symbol, timeframe
    """)

    combinations = cursor.fetchall()
    all_signals = []

    for idx, (symbol, timeframe) in enumerate(combinations, 1):
        print(f"\n[{idx}/{len(combinations)}] Analyzing {symbol} ({timeframe})...")

        # Analyze this symbol/timeframe
        result = analyze_master_confluence(symbol, timeframe)

        if result and result.get('confluence'):
            confluence = result['confluence']
            score = confluence.get('score', 0)

            # Include ALL signals (no minimum score filter)
            if score > 0:
                signal_data = {
                    'Symbol': symbol,
                    'Timeframe': timeframe,
                    'Timestamp': result.get('timestamp', 0),
                    'Date': datetime.fromtimestamp(result.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                    'Price': result.get('current_price', 0),
                    'Direction': '🌪️ Bullish' if confluence.get('direction') == 'bullish' else '🌊 Bearish',
                    'Score': score,
                    'Classification': confluence.get('classification', 'UNKNOWN'),
                    'Hull_Signals': confluence.get('breakdown', {}).get('hull', 0),
                    'AO_Signals': confluence.get('breakdown', {}).get('ao', 0),
                    'Alligator_Signals': confluence.get('breakdown', {}).get('alligator', 0),
                    'Ichimoku_Signals': confluence.get('breakdown', {}).get('ichimoku', 0),
                    'Volume_Level': result.get('volume_analysis', {}).get('level', 'NORMAL'),
                    'Volume_Ratio': result.get('volume_analysis', {}).get('ratio', 0),
                    'Total_Indicators': len(confluence.get('signals', [])),
                    'Signal_Details': ' | '.join([s.get('message', '') for s in confluence.get('signals', [])][:5])
                }

                all_signals.append(signal_data)

                emoji = confluence.get('emoji', '💫')
                print(f"  {emoji} {confluence.get('classification')} - Score: {score:.1f}")

    conn.close()

    print("\n" + "=" * 80)
    print(f"✅ Generated {len(all_signals)} signals")
    return all_signals

def export_to_excel(signals):
    """Export signals to Excel file"""
    print(f"\n📊 Exporting {len(signals)} signals to Excel...")

    if not signals:
        print("⚠️  No signals to export!")
        return

    # Create DataFrame
    df = pd.DataFrame(signals)

    # Sort by symbol, then timeframe, then date
    df = df.sort_values(['Symbol', 'Timeframe', 'Timestamp'])

    # Create Excel writer
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        # Main sheet with all signals
        df.to_excel(writer, sheet_name='All Signals', index=False)

        # Summary sheet
        summary_data = {
            'Metric': [
                'Total Signals',
                'PERFECT Signals (≥3.0)',
                'EXCELLENT Signals (≥2.5)',
                'VERY GOOD Signals (≥1.8)',
                'GOOD Signals (≥1.2)',
                'WEAK Signals (<1.2)',
                '',
                'Symbols Analyzed',
                'Timeframes',
                'Date Range',
                'Generated On'
            ],
            'Value': [
                len(df),
                len(df[df['Score'] >= 3.0]),
                len(df[df['Score'] >= 2.5]),
                len(df[df['Score'] >= 1.8]),
                len(df[df['Score'] >= 1.2]),
                len(df[df['Score'] < 1.2]),
                '',
                ', '.join(sorted(df['Symbol'].unique())),
                ', '.join(sorted(df['Timeframe'].unique())),
                f"{df['Date'].min()} to {df['Date'].max()}",
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

        # Per-symbol sheets
        for symbol in sorted(df['Symbol'].unique()):
            symbol_df = df[df['Symbol'] == symbol]
            symbol_df.to_excel(writer, sheet_name=symbol, index=False)

    print(f"✅ Excel report saved to: {OUTPUT_FILE}")
    print(f"   📄 Sheets: All Signals, Summary, + per-symbol sheets")

def main():
    """Main execution"""
    print("🚀 Historical Signals Report Generator")
    print("=" * 80)
    print(f"📋 Configuration:")
    print(f"   Symbols: {', '.join(SYMBOLS)}")
    print(f"   Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"   Lookback: {LOOKBACK_DAYS} days")
    print(f"   Output: {OUTPUT_FILE}")
    print("=" * 80)

    # Step 1: Collect data
    print("\n🔄 STEP 1: Data Collection")
    connector = connect_to_hyperliquid(use_testnet=False)
    if not connector:
        print("❌ Failed to connect to Hyperliquid")
        return

    data_collected = collect_historical_data(
        connector,
        SYMBOLS,
        TIMEFRAMES,
        LOOKBACK_DAYS
    )

    if not data_collected:
        print("❌ No data collected")
        return

    # Step 2: Store in database
    print("\n🔄 STEP 2: Database Storage")
    store_data_in_db(data_collected)

    # Step 3: Generate signals
    print("\n🔄 STEP 3: Signal Generation")
    signals = generate_signals_for_all_data()

    # Step 4: Export to Excel
    print("\n🔄 STEP 4: Export to Excel")
    export_to_excel(signals)

    print("\n" + "=" * 80)
    print("✅ COMPLETE! Report generated successfully!")
    print(f"📊 Open the file: {OUTPUT_FILE}")
    print("=" * 80)

if __name__ == "__main__":
    main()
