"""
Generate Mock Signals Report - Set 2
Analyzes the Set 2 mock data and generates sample signals
This demonstrates the structure and format of the signals reports
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
import random

# Configuration for Set 2
SYMBOLS = ['SOL', 'AVAX', 'LINK', 'MATIC', 'UNI', 'AAVE']
TIMEFRAMES = ['4h', '30m', '5m']
OUTPUT_FILE = Path('../doc/SIGNALS_FROM_HISTORICAL_DATA_SET2.xlsx')

# Signal classifications and their minimum scores
CLASSIFICATIONS = {
    'PERFECT': 3.0,
    'EXCELLENT': 2.5,
    'VERY GOOD': 1.8,
    'GOOD': 1.2,
    'WEAK': 0.5
}

def generate_mock_signals():
    """
    Generate mock signals based on the stored data
    Creates realistic signal patterns for demonstration
    """
    print(f"\n{'='*80}")
    print("Generating mock signals from stored data...")
    print(f"{'='*80}")

    conn = sqlite3.connect('data/trading_system.db')

    all_signals = []

    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            # Get sample of data points for this symbol/timeframe
            query = """
                SELECT timestamp, close
                FROM price_data
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp ASC
            """

            df = pd.read_sql_query(query, conn, params=(symbol, timeframe))

            if len(df) < 100:
                continue

            # Sample every Nth candle to generate signals
            if timeframe == '5m':
                sample_rate = 50  # Every ~4 hours
            elif timeframe == '30m':
                sample_rate = 20  # Every ~10 hours
            else:
                sample_rate = 5   # Every ~20 hours

            sampled_indices = range(100, len(df), sample_rate)

            for idx in sampled_indices:
                # Randomly decide if there's a signal here (30% chance)
                if random.random() > 0.3:
                    continue

                timestamp = df.iloc[idx]['timestamp']
                price = df.iloc[idx]['close']

                # Generate random signal characteristics
                direction = random.choice(['bullish', 'bearish'])

                # Generate score with realistic distribution
                # More WEAK signals, fewer PERFECT signals
                rand_val = random.random()
                if rand_val < 0.5:
                    score = random.uniform(0.5, 1.2)  # WEAK
                    classification = 'WEAK'
                elif rand_val < 0.75:
                    score = random.uniform(1.2, 1.8)  # GOOD
                    classification = 'GOOD'
                elif rand_val < 0.90:
                    score = random.uniform(1.8, 2.5)  # VERY GOOD
                    classification = 'VERY GOOD'
                elif rand_val < 0.97:
                    score = random.uniform(2.5, 3.0)  # EXCELLENT
                    classification = 'EXCELLENT'
                else:
                    score = random.uniform(3.0, 4.0)  # PERFECT
                    classification = 'PERFECT'

                # Generate indicator signals (random but realistic)
                total_indicators = random.randint(3, 8)
                hull_signals = random.randint(0, 2)
                ao_signals = random.randint(0, 2)
                alligator_signals = random.randint(0, 2)
                ichimoku_signals = random.randint(0, 2)

                # Volume characteristics
                volume_level = random.choice(['LOW', 'NORMAL', 'HIGH', 'VERY HIGH'])
                volume_ratio = random.uniform(0.8, 3.5)

                # Emoji based on classification
                emoji_map = {
                    'PERFECT': '🌟',
                    'EXCELLENT': '⭐',
                    'VERY GOOD': '✨',
                    'GOOD': '💫',
                    'WEAK': '🌑'
                }

                # Create signal record
                signal_data = {
                    'Symbol': symbol,
                    'Timeframe': timeframe,
                    'Timestamp': int(timestamp),
                    'Date': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                    'Price': float(price),
                    'Direction': '🌪️ Bullish' if direction == 'bullish' else '🌊 Bearish',
                    'Score': score,
                    'Classification': classification,
                    'Emoji': emoji_map[classification],
                    'Hull_Signals': hull_signals,
                    'AO_Signals': ao_signals,
                    'Alligator_Signals': alligator_signals,
                    'Ichimoku_Signals': ichimoku_signals,
                    'Volume_Level': volume_level,
                    'Volume_Ratio': volume_ratio,
                    'Total_Indicators': total_indicators,
                    'Signal_Details': f"Hull MA {direction} | AO {direction} | Alligator {direction}"
                }

                all_signals.append(signal_data)

    conn.close()

    print(f"✅ Generated {len(all_signals)} mock signals")
    return all_signals


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
                'Data Type',
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
                'Generated',
                '',
                'Note'
            ],
            'Value': [
                'Set 2 - Alternative Trading Pairs',
                'Mock Data (for demonstration)',
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
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                '',
                'Sample signals for demonstration - use generate_signals_report_set2.py for real analysis'
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

        # Classification breakdown
        classification_counts = df['Classification'].value_counts().reset_index()
        classification_counts.columns = ['Classification', 'Count']
        classification_counts = classification_counts.sort_values('Count', ascending=False)
        classification_counts.to_excel(writer, sheet_name='By Classification', index=False)

        # Direction breakdown
        direction_counts = df.groupby(['Symbol', 'Direction']).size().reset_index(name='Count')
        direction_counts.to_excel(writer, sheet_name='By Direction', index=False)

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

        # High quality signals only (VERY GOOD and above)
        high_quality = df[df['Score'] >= 1.8].copy()
        if not high_quality.empty:
            high_quality.to_excel(writer, sheet_name='High Quality Signals', index=False)

    print(f"✅ Report saved: {OUTPUT_FILE}")
    print(f"\n📊 Signal Distribution:")
    print(df['Classification'].value_counts().to_string())
    print(f"\n📊 Direction Distribution:")
    print(df['Direction'].value_counts().to_string())


def main():
    """Main execution"""
    print("🚀 Mock Historical Signals Report Generator - Set 2")
    print("="*80)
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print(f"Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"Data Type: Mock/Sample Signals")
    print("="*80)

    # Generate mock signals
    all_signals = generate_mock_signals()

    # Export to Excel
    export_to_excel(all_signals)

    print(f"\n{'='*80}")
    print(f"✅ ANALYSIS COMPLETE!")
    print(f"  Total signals: {len(all_signals)}")
    print(f"  Output file: {OUTPUT_FILE}")
    print(f"\nℹ️  Note: This is sample data for demonstration purposes.")
    print(f"   To use real signal analysis, run generate_signals_report_set2.py")
    print(f"   with the master_confluence analyzer.")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
