"""
Generate Signals from Backtesting Watchlist Data
Loads data from backtestingwatchlist.xlsx and generates all signals for comparison with TradingView
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
from datetime import datetime
from pathlib import Path
from utils import connect_to_database
from master_confluence import analyze_master_confluence

# Configuration
INPUT_FILE = Path('../doc/backtestingwatchlist.xlsx')
OUTPUT_FILE = Path('../doc/BACKTESTING_SIGNALS_REPORT.xlsx')

# Symbols from the backtesting watchlist
SYMBOLS = ['ETH', 'NEAR', 'UNI', 'BTC', 'APT', 'AERO', 'POPCAT', 'SUI', 'AAVE']
TIMEFRAMES = ['30m', '1h', '2h', '4h', '8h', '12h', '1d']

def load_backtesting_data_from_excel():
    """
    Load backtesting data from Excel file

    Returns:
        dict: {symbol: DataFrame with all candle data}
    """
    print(f"\n📂 Loading backtesting data from {INPUT_FILE}...")
    print("=" * 80)

    if not INPUT_FILE.exists():
        print(f"❌ File not found: {INPUT_FILE}")
        return None

    try:
        # Read Excel file - get all sheets
        excel_file = pd.ExcelFile(INPUT_FILE)

        print(f"📋 Available sheets: {excel_file.sheet_names}")

        data_by_symbol = {}

        # Read each symbol's data
        for symbol in SYMBOLS:
            if symbol in excel_file.sheet_names:
                df = pd.read_excel(INPUT_FILE, sheet_name=symbol)
                data_by_symbol[symbol] = df
                print(f"  ✅ {symbol}: {len(df)} rows loaded")
            else:
                print(f"  ⚠️  {symbol}: Sheet not found in Excel file")

        print(f"\n✅ Loaded {len(data_by_symbol)} symbols from Excel")
        return data_by_symbol

    except Exception as e:
        print(f"❌ Error loading Excel file: {e}")
        return None

def store_data_in_database(data_by_symbol):
    """
    Store backtesting data in database for analysis

    Args:
        data_by_symbol: Dictionary of {symbol: DataFrame}
    """
    print("\n💾 Storing backtesting data in database...")
    print("=" * 80)

    conn = connect_to_database()
    cursor = conn.cursor()

    # Clear existing data for these symbols
    print("  🗑️  Clearing old data...")
    cursor.execute("""
        DELETE FROM price_data
        WHERE symbol IN ({})
    """.format(','.join(['?' for _ in SYMBOLS])), SYMBOLS)

    total_candles = 0

    for symbol, df in data_by_symbol.items():
        symbol_candles = 0

        # Expected columns: symbol, timeframe, timestamp, date, open, high, low, close, volume
        for _, row in df.iterrows():
            try:
                # Convert timestamp to seconds if it's in milliseconds
                timestamp = row['timestamp']
                if timestamp > 1e10:  # Likely milliseconds
                    timestamp = timestamp / 1000

                cursor.execute("""
                    INSERT OR REPLACE INTO price_data
                    (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    symbol,
                    row['timeframe'],
                    timestamp,
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume']
                ))
                symbol_candles += 1
                total_candles += 1

            except Exception as e:
                print(f"    ⚠️  Error storing row for {symbol}: {e}")
                continue

        print(f"  ✅ {symbol}: {symbol_candles:,} candles stored")

    conn.commit()
    conn.close()

    print(f"\n✅ Stored {total_candles:,} total candles in database")
    return total_candles

def generate_signals_for_all_combinations():
    """
    Generate signals for all symbol/timeframe combinations from backtesting data

    Returns:
        list: List of signal dictionaries
    """
    print("\n🔍 Generating signals for all symbol/timeframe combinations...")
    print("=" * 80)

    conn = connect_to_database()
    cursor = conn.cursor()

    # Get all symbol/timeframe combinations that have data
    cursor.execute("""
        SELECT DISTINCT symbol, timeframe
        FROM price_data
        WHERE symbol IN ({})
        ORDER BY symbol, timeframe
    """.format(','.join(['?' for _ in SYMBOLS])), SYMBOLS)

    combinations = cursor.fetchall()
    all_signals = []

    print(f"\n📊 Found {len(combinations)} symbol/timeframe combinations to analyze\n")

    for idx, (symbol, timeframe) in enumerate(combinations, 1):
        print(f"[{idx}/{len(combinations)}] Analyzing {symbol} ({timeframe})...", end=' ')

        try:
            # Analyze this symbol/timeframe using master confluence
            result = analyze_master_confluence(conn, symbol, timeframe)

            if result and result.get('confluence'):
                confluence = result['confluence']
                score = confluence.get('score', 0)

                # Include ALL signals (even weak ones) for comparison with TradingView
                if score > 0:
                    # Determine direction based on primary system and signals
                    direction = 'NEUTRAL'
                    if confluence.get('primary_system') == 'wind_catcher':
                        direction = 'BULLISH'
                    elif confluence.get('primary_system') == 'river_turn':
                        direction = 'BEARISH'

                    # Count signals by type
                    hull_count = len(result.get('hull_signals', []))
                    ao_count = len(result.get('ao_signals', []))
                    alligator_count = len(result.get('alligator_signals', []))
                    ichimoku_count = len(result.get('ichimoku_signals', []))

                    signal_data = {
                        'Symbol': symbol,
                        'Timeframe': timeframe,
                        'Timestamp': result.get('timestamp', 0),
                        'Date': datetime.fromtimestamp(result.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                        'Price': result.get('price', 0),
                        'Direction': direction,
                        'Score': score,
                        'Classification': confluence.get('classification', 'UNKNOWN'),
                        'Hull_Signals': hull_count,
                        'AO_Signals': ao_count,
                        'Alligator_Signals': alligator_count,
                        'Ichimoku_Signals': ichimoku_count,
                        'Total_Signals': confluence.get('signal_count', 0),
                        'Volume_Level': result.get('volume_signals', [{}])[-1].get('level', 'NORMAL') if result.get('volume_signals') else 'NORMAL',
                        'Volume_Ratio': result.get('volume_signals', [{}])[-1].get('ratio', 0) if result.get('volume_signals') else 0,
                        'Signal_Details': ' | '.join(confluence.get('factors', [])[:5])
                    }

                    all_signals.append(signal_data)

                    emoji = confluence.get('emoji', '💫')
                    print(f"{emoji} {confluence.get('classification')} - Score: {score:.1f} - {direction}")
                else:
                    print("No signals")
            else:
                print("Insufficient data")

        except Exception as e:
            print(f"❌ Error: {e}")

    conn.close()

    print("\n" + "=" * 80)
    print(f"✅ Generated {len(all_signals)} signals from backtesting data")
    return all_signals

def export_signals_to_excel(signals):
    """
    Export signals to Excel file with multiple sheets for easy analysis

    Args:
        signals: List of signal dictionaries
    """
    print(f"\n📊 Exporting {len(signals)} signals to Excel...")
    print("=" * 80)

    if not signals:
        print("⚠️  No signals to export!")
        return

    # Create DataFrame
    df = pd.DataFrame(signals)

    # Sort by symbol, timeframe, then timestamp
    df = df.sort_values(['Symbol', 'Timeframe', 'Timestamp'])

    # Create Excel writer
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        # Main sheet with all signals
        df.to_excel(writer, sheet_name='All Signals', index=False)
        print(f"  ✅ 'All Signals' sheet: {len(df)} rows")

        # Summary sheet
        summary_data = []

        summary_data.append({
            'Metric': 'Total Signals',
            'Value': len(df)
        })
        summary_data.append({
            'Metric': 'PERFECT Signals (≥3.0)',
            'Value': len(df[df['Score'] >= 3.0])
        })
        summary_data.append({
            'Metric': 'EXCELLENT Signals (≥2.5)',
            'Value': len(df[df['Score'] >= 2.5])
        })
        summary_data.append({
            'Metric': 'VERY GOOD Signals (≥1.8)',
            'Value': len(df[df['Score'] >= 1.8])
        })
        summary_data.append({
            'Metric': 'GOOD Signals (≥1.2)',
            'Value': len(df[df['Score'] >= 1.2])
        })
        summary_data.append({
            'Metric': 'INTERESTING Signals (≥0.8)',
            'Value': len(df[df['Score'] >= 0.8])
        })
        summary_data.append({
            'Metric': 'WEAK Signals (<0.8)',
            'Value': len(df[df['Score'] < 0.8])
        })
        summary_data.append({
            'Metric': '',
            'Value': ''
        })
        summary_data.append({
            'Metric': 'Bullish Signals',
            'Value': len(df[df['Direction'] == 'BULLISH'])
        })
        summary_data.append({
            'Metric': 'Bearish Signals',
            'Value': len(df[df['Direction'] == 'BEARISH'])
        })
        summary_data.append({
            'Metric': '',
            'Value': ''
        })
        summary_data.append({
            'Metric': 'Symbols Analyzed',
            'Value': ', '.join(sorted(df['Symbol'].unique()))
        })
        summary_data.append({
            'Metric': 'Timeframes',
            'Value': ', '.join(sorted(df['Timeframe'].unique()))
        })
        summary_data.append({
            'Metric': 'Date Range',
            'Value': f"{df['Date'].min()} to {df['Date'].max()}"
        })
        summary_data.append({
            'Metric': 'Generated On',
            'Value': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        print(f"  ✅ 'Summary' sheet created")

        # Per-symbol sheets
        for symbol in sorted(df['Symbol'].unique()):
            symbol_df = df[df['Symbol'] == symbol].copy()
            symbol_df = symbol_df.sort_values(['Timeframe', 'Timestamp'])
            symbol_df.to_excel(writer, sheet_name=symbol, index=False)
            print(f"  ✅ '{symbol}' sheet: {len(symbol_df)} signals")

        # High quality signals sheet (score >= 1.8)
        high_quality = df[df['Score'] >= 1.8].copy()
        if len(high_quality) > 0:
            high_quality = high_quality.sort_values('Score', ascending=False)
            high_quality.to_excel(writer, sheet_name='High Quality', index=False)
            print(f"  ✅ 'High Quality' sheet: {len(high_quality)} signals (≥1.8)")

    print("\n" + "=" * 80)
    print(f"✅ Excel report saved to: {OUTPUT_FILE}")
    print(f"   File location: {OUTPUT_FILE.resolve()}")
    print("=" * 80)

def main():
    """Main execution"""
    print("\n" + "=" * 80)
    print("🚀 BACKTESTING SIGNALS GENERATOR")
    print("=" * 80)
    print(f"📋 Input: {INPUT_FILE}")
    print(f"📋 Output: {OUTPUT_FILE}")
    print(f"📊 Symbols: {', '.join(SYMBOLS)}")
    print(f"⏱️  Timeframes: {', '.join(TIMEFRAMES)}")
    print("=" * 80)

    start_time = datetime.now()

    # Step 1: Load backtesting data from Excel
    print("\n🔄 STEP 1: Load Backtesting Data")
    data_by_symbol = load_backtesting_data_from_excel()

    if not data_by_symbol:
        print("❌ Failed to load backtesting data")
        return

    # Step 2: Store in database
    print("\n🔄 STEP 2: Store Data in Database")
    total_candles = store_data_in_database(data_by_symbol)

    if total_candles == 0:
        print("❌ No data stored in database")
        return

    # Step 3: Generate signals
    print("\n🔄 STEP 3: Generate Signals from All Data")
    signals = generate_signals_for_all_combinations()

    if not signals:
        print("⚠️  No signals generated")

    # Step 4: Export to Excel
    print("\n🔄 STEP 4: Export Signals to Excel")
    export_signals_to_excel(signals)

    # Print completion summary
    elapsed = datetime.now() - start_time
    print("\n" + "=" * 80)
    print("✅ COMPLETE! Backtesting signals generated successfully!")
    print("=" * 80)
    print(f"⏱️  Total time: {elapsed.total_seconds():.1f} seconds")
    print(f"📊 Total signals: {len(signals)}")
    print(f"📂 Output file: {OUTPUT_FILE}")
    print("\n💡 You can now compare these signals with TradingView charts!")
    print("=" * 80)

if __name__ == "__main__":
    main()
