"""
Generate Historical Signals Report - Set 2
Analyzes the Set 2 trading data and generates signals report
Based on batch_historical_analyzer.py but for Set 2 symbols
"""

import sys
import io

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
from datetime import datetime
import sqlite3
from pathlib import Path
import time
import json

# Configuration for Set 2
SYMBOLS = ['SOL', 'AVAX', 'LINK', 'MATIC', 'UNI', 'AAVE']  # Same as data collection
TIMEFRAMES = ['4h', '30m', '5m']  # Same as data collection
MIN_CANDLES_REQUIRED = 100  # Minimum candles needed for analysis
OUTPUT_FILE = Path('../doc/SIGNALS_FROM_HISTORICAL_DATA_SET2.xlsx')

# Import master confluence
from master_confluence import analyze_master_confluence


def get_all_timestamps(symbol, timeframe):
    """Get all timestamps for a symbol/timeframe from database"""
    conn = sqlite3.connect('data/trading_system.db')

    query = """
        SELECT DISTINCT timestamp, close as price
        FROM price_data
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp ASC
    """

    df = pd.read_sql_query(query, conn, params=(symbol, timeframe))
    conn.close()

    return df


def analyze_at_timestamp(symbol, timeframe, target_timestamp):
    """
    Analyze confluence at a specific point in time

    This creates a temporary view of data up to target_timestamp
    and runs the analysis
    """
    conn = sqlite3.connect('data/trading_system.db')
    cursor = conn.cursor()

    try:
        # Create temporary table with data up to target_timestamp
        cursor.execute("""
            CREATE TEMP TABLE IF NOT EXISTS temp_price_data AS
            SELECT * FROM price_data
            WHERE symbol = ? AND timeframe = ? AND timestamp <= ?
            ORDER BY timestamp DESC
            LIMIT 200
        """, (symbol, timeframe, target_timestamp))

        # Check if we have enough data
        cursor.execute("SELECT COUNT(*) FROM temp_price_data")
        count = cursor.fetchone()[0]

        if count < MIN_CANDLES_REQUIRED:
            cursor.execute("DROP TABLE IF EXISTS temp_price_data")
            conn.close()
            return None

        # Now analyze using the master confluence
        # We need to temporarily swap the table
        cursor.execute("ALTER TABLE price_data RENAME TO price_data_backup")
        cursor.execute("ALTER TABLE temp_price_data RENAME TO price_data")

        # Run analysis
        result = analyze_master_confluence(symbol, timeframe)

        # Restore original table
        cursor.execute("ALTER TABLE price_data RENAME TO temp_price_data")
        cursor.execute("ALTER TABLE price_data_backup RENAME TO price_data")
        cursor.execute("DROP TABLE IF EXISTS temp_price_data")

        conn.close()
        return result

    except Exception as e:
        print(f"      Error analyzing {symbol} {timeframe} at {target_timestamp}: {e}")
        # Restore tables if error
        try:
            cursor.execute("ALTER TABLE price_data RENAME TO temp_price_data")
            cursor.execute("ALTER TABLE price_data_backup RENAME TO price_data")
            cursor.execute("DROP TABLE IF EXISTS temp_price_data")
        except:
            pass
        conn.close()
        return None


def analyze_symbol_timeframe_sampled(symbol, timeframe):
    """
    Simplified approach: Sample every Nth candle instead of all candles
    This makes it feasible to complete in reasonable time
    """
    print(f"\n{'='*80}")
    print(f"Analyzing {symbol} ({timeframe})")
    print(f"{'='*80}")

    # Get all timestamps
    timestamps_df = get_all_timestamps(symbol, timeframe)

    if len(timestamps_df) < MIN_CANDLES_REQUIRED:
        print(f"  ⚠️  Insufficient data: {len(timestamps_df)} candles (need {MIN_CANDLES_REQUIRED})")
        return []

    print(f"  📊 Total candles: {len(timestamps_df)}")
    print(f"  📅 Date range: {datetime.fromtimestamp(timestamps_df['timestamp'].min())} to {datetime.fromtimestamp(timestamps_df['timestamp'].max())}")

    # Sampling strategy based on timeframe
    if timeframe == '5m':
        sample_rate = 24  # Every 24th candle = every 2 hours
    elif timeframe == '30m':
        sample_rate = 16  # Every 16th candle = every 8 hours
    elif timeframe == '4h':
        sample_rate = 3   # Every 3rd candle = every 12 hours
    else:
        sample_rate = 10

    sampled_indices = range(MIN_CANDLES_REQUIRED, len(timestamps_df), sample_rate)
    total_to_analyze = len(list(sampled_indices))

    print(f"  🔄 Analyzing {total_to_analyze} sampled candles (every {sample_rate}th candle)")

    signals_found = []

    for idx, i in enumerate(sampled_indices):
        if idx % 10 == 0:
            progress_pct = (idx / total_to_analyze) * 100
            print(f"    Progress: {idx}/{total_to_analyze} ({progress_pct:.1f}%) - {len(signals_found)} signals", end='\r')

        timestamp = timestamps_df.iloc[i]['timestamp']
        price = timestamps_df.iloc[i]['price']

        # Analyze at this timestamp
        result = analyze_at_timestamp(symbol, timeframe, timestamp)

        if result and result.get('confluence'):
            confluence = result['confluence']
            score = confluence.get('score', 0)

            # Include ALL signals (even WEAK)
            if score > 0:
                signal_data = {
                    'Symbol': symbol,
                    'Timeframe': timeframe,
                    'Timestamp': int(timestamp),
                    'Date': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                    'Price': float(price),
                    'Direction': '🌪️ Bullish' if confluence.get('direction') == 'bullish' else '🌊 Bearish',
                    'Score': score,
                    'Classification': confluence.get('classification', 'UNKNOWN'),
                    'Emoji': confluence.get('emoji', '💫'),
                    'Hull_Signals': confluence.get('breakdown', {}).get('hull', 0),
                    'AO_Signals': confluence.get('breakdown', {}).get('ao', 0),
                    'Alligator_Signals': confluence.get('breakdown', {}).get('alligator', 0),
                    'Ichimoku_Signals': confluence.get('breakdown', {}).get('ichimoku', 0),
                    'Volume_Level': result.get('volume_analysis', {}).get('level', 'NORMAL'),
                    'Volume_Ratio': result.get('volume_analysis', {}).get('ratio', 0),
                    'Total_Indicators': len(confluence.get('signals', [])),
                    'Signal_Details': ' | '.join([s.get('message', '')[:50] for s in confluence.get('signals', [])][:3])
                }

                signals_found.append(signal_data)

        # Small delay to avoid database locks
        time.sleep(0.01)

    print(f"\n  ✅ Complete: Found {len(signals_found)} signals")
    return signals_found


def export_to_excel(all_signals):
    """Export all signals to Excel"""
    print(f"\n{'='*80}")
    print(f"📊 Exporting {len(all_signals)} signals to Excel")
    print(f"{'='*80}")

    if not all_signals:
        print("⚠️  No signals to export!")
        return

    df = pd.DataFrame(all_signals)
    df = df.sort_values(['Symbol', 'Timeframe', 'Timestamp'])

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        # All signals
        df.to_excel(writer, sheet_name='All Signals', index=False)

        # Summary
        summary_data = {
            'Metric': [
                'Dataset',
                'Total Signals',
                'PERFECT (≥3.0)',
                'EXCELLENT (≥2.5)',
                'VERY GOOD (≥1.8)',
                'GOOD (≥1.2)',
                'WEAK (<1.2)',
                '',
                'Bullish Signals',
                'Bearish Signals',
                '',
                'Symbols',
                'Timeframes',
                'Date Range',
                'Generated'
            ],
            'Value': [
                'Set 2 - Alternative Trading Pairs',
                len(df),
                len(df[df['Score'] >= 3.0]),
                len(df[df['Score'] >= 2.5]),
                len(df[df['Score'] >= 1.8]),
                len(df[df['Score'] >= 1.2]),
                len(df[df['Score'] < 1.2]),
                '',
                len(df[df['Direction'] == '🌪️ Bullish']),
                len(df[df['Direction'] == '🌊 Bearish']),
                '',
                ', '.join(sorted(df['Symbol'].unique())),
                ', '.join(sorted(df['Timeframe'].unique())),
                f"{df['Date'].min()} to {df['Date'].max()}",
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

        # Classification breakdown
        classification_counts = df['Classification'].value_counts().reset_index()
        classification_counts.columns = ['Classification', 'Count']
        classification_counts.to_excel(writer, sheet_name='By Classification', index=False)

        # Per-symbol sheets
        for symbol in sorted(df['Symbol'].unique()):
            symbol_df = df[df['Symbol'] == symbol].copy()
            symbol_df.to_excel(writer, sheet_name=symbol, index=False)

        # Per-timeframe sheets
        for tf in sorted(df['Timeframe'].unique()):
            tf_df = df[df['Timeframe'] == tf].copy()
            # Excel sheet names can't contain : so replace with h/m
            sheet_name = f"TF_{tf.replace(':', 'h' if 'h' in tf else 'm')}"
            tf_df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"✅ Report saved: {OUTPUT_FILE}")
    print(f"\n📊 Signal Distribution:")
    print(df['Classification'].value_counts().to_string())


def main():
    """Main execution"""
    print("🚀 Historical Signals Report Generator - Set 2")
    print("="*80)
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"Strategy: Sampled analysis (manageable runtime)")
    print("="*80)

    start_time = time.time()

    all_signals = []
    total_combinations = len(SYMBOLS) * len(TIMEFRAMES)
    current = 0

    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            current += 1
            print(f"\n[{current}/{total_combinations}] Processing {symbol} ({timeframe})")

            signals = analyze_symbol_timeframe_sampled(symbol, timeframe)
            all_signals.extend(signals)

            elapsed = time.time() - start_time
            avg_time = elapsed / current
            remaining = (total_combinations - current) * avg_time

            print(f"  ⏱️  Elapsed: {elapsed/60:.1f}min | Est. remaining: {remaining/60:.1f}min")

    # Export to Excel
    export_to_excel(all_signals)

    total_time = time.time() - start_time
    print(f"\n{'='*80}")
    print(f"✅ ANALYSIS COMPLETE!")
    print(f"  Total time: {total_time/60:.1f} minutes")
    print(f"  Total signals: {len(all_signals)}")
    print(f"  Output file: {OUTPUT_FILE}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
