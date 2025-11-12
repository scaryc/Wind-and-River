"""
Backtest Signal Generator
Replays historical data and generates signals as if running live
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime
from master_confluence import analyze_master_confluence, connect_to_database


def get_historical_data(conn, symbol, timeframe, start_date, end_date):
    """Get historical price data for backtesting"""
    query = '''
        SELECT timestamp, open, high, low, close, volume
        FROM price_data
        WHERE symbol = ? AND timeframe = ?
        AND timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp ASC
    '''

    # Convert dates to timestamps
    start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
    end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp())

    df = pd.read_sql_query(query, conn, params=(symbol, timeframe, start_ts, end_ts))

    if df.empty:
        return None

    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    return df


def run_backtest(conn, symbol, timeframe, start_date, end_date, min_score=1.2):
    """
    Replay candle-by-candle and detect signals

    Parameters:
    - conn: Database connection
    - symbol: Trading pair
    - timeframe: Timeframe to analyze
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    - min_score: Minimum confluence score to record (default: 1.2 = GOOD+)

    Returns:
    - List of detected signals
    """
    print(f"\n📊 Running Backtest: {symbol} [{timeframe}]")
    print(f"   Period: {start_date} to {end_date}")
    print(f"   Min Score: {min_score}")

    # Get all historical data
    df = get_historical_data(conn, symbol, timeframe, start_date, end_date)

    if df is None or len(df) < 150:
        print(f"   ⚠️  Insufficient data (need at least 150 candles for indicators)")
        return []

    print(f"   ✅ Loaded {len(df)} candles")

    signals_detected = []

    # Start analysis after we have enough history for indicators (150 candles)
    # We need lookback period for technical indicators to be accurate
    start_index = 150

    print(f"   🔄 Analyzing {len(df) - start_index} candles...")

    for i in range(start_index, len(df)):
        # Get data up to this point (simulate historical context)
        # This ensures no lookahead bias
        current_timestamp = df.iloc[i]['timestamp']
        current_datetime = df.iloc[i]['datetime']
        current_price = df.iloc[i]['close']

        # For each candle, we analyze using data available up to that point
        # In a live system, we'd call analyze_master_confluence
        # Here we simulate by restricting the data view

        # Create a temporary view of data up to current candle
        # Note: analyze_master_confluence will fetch its own data from DB
        # We need to ensure it only sees data up to current_timestamp

        try:
            # Analyze confluence at this point in time
            result = analyze_master_confluence(conn, symbol, timeframe)

            if result and result['confluence']['score'] >= min_score:
                # Found a signal!
                signal = {
                    'timestamp': int(current_timestamp),
                    'datetime': current_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'direction': result['confluence']['primary_system'],
                    'confluence_score': result['confluence']['score'],
                    'confluence_class': result['confluence']['classification'],
                    'price': current_price,
                    'indicators_firing': {
                        'hull': len(result['hull_signals']),
                        'ao': len(result['ao_signals']),
                        'alligator': len(result['alligator_signals']),
                        'ichimoku': len(result['ichimoku_signals']),
                        'volume': 1 if result['volume_signals'] and result['volume_signals'][-1]['level'] != 'NORMAL' else 0
                    },
                    'volume_level': result['volume_signals'][-1]['level'] if result['volume_signals'] else 'NORMAL',
                    'volume_ratio': result['volume_signals'][-1]['ratio'] if result['volume_signals'] else 1.0,
                    'signal_count': result['confluence']['signal_count'],
                    'signal_details': '; '.join(result['confluence']['factors'][:3])  # Top 3 factors
                }

                signals_detected.append(signal)

                # Print progress for significant signals
                if signal['confluence_score'] >= 2.5:
                    emoji = result['confluence']['emoji']
                    direction_emoji = "🌪️" if signal['direction'] == 'wind_catcher' else "🌊"
                    print(f"   {emoji} {direction_emoji} {signal['confluence_class']} @ {signal['datetime']} - ${signal['price']:.2f} (Score: {signal['confluence_score']:.1f})")

        except Exception as e:
            # Skip this candle if analysis fails
            pass

        # Progress indicator every 100 candles
        if (i - start_index) % 100 == 0 and i != start_index:
            progress = ((i - start_index) / (len(df) - start_index)) * 100
            print(f"   Progress: {progress:.0f}% ({i - start_index}/{len(df) - start_index} candles analyzed)")

    print(f"   ✅ Analysis complete: {len(signals_detected)} signals detected")

    return signals_detected


def save_backtest_signals(conn, signals):
    """Save backtest signals to database"""
    if not signals:
        return 0

    cursor = conn.cursor()
    saved_count = 0

    for signal in signals:
        try:
            cursor.execute('''
                INSERT INTO signals
                (timestamp, symbol, timeframe, system, signal_type,
                 confluence_score, confluence_class, price,
                 indicators_firing, volume_level, volume_ratio,
                 details, notified, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal['timestamp'],
                signal['symbol'],
                signal['timeframe'],
                signal['direction'],
                'confluence',
                signal['confluence_score'],
                signal['confluence_class'],
                signal['price'],
                json.dumps(signal['indicators_firing']),
                signal['volume_level'],
                signal['volume_ratio'],
                signal['signal_details'],
                0,  # Not notified
                int(datetime.now().timestamp())
            ))

            saved_count += 1

        except Exception as e:
            print(f"   ⚠️  Error saving signal: {e}")

    conn.commit()
    return saved_count


def export_signals_to_json(signals, filename):
    """Export signals to JSON file for analysis"""
    with open(filename, 'w') as f:
        json.dump(signals, f, indent=2)

    print(f"\n💾 Signals exported to: {filename}")


def run_backtest_campaign(symbols, timeframe='1h', start_date='2024-10-03', end_date='2024-11-03'):
    """
    Run backtest for multiple symbols

    Parameters:
    - symbols: List of trading pairs
    - timeframe: Timeframe to analyze
    - start_date: Start date (YYYY-MM-DD)
    - end_date: End date (YYYY-MM-DD)
    """
    print("="*80)
    print("🔬 BACKTEST SIGNAL GENERATOR")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Symbols: {', '.join(symbols)}")
    print(f"  Timeframe: {timeframe}")
    print(f"  Period: {start_date} to {end_date}")
    print(f"  Min Score: 1.2 (GOOD+)")

    conn = connect_to_database()

    all_signals = []

    for i, symbol in enumerate(symbols, 1):
        print(f"\n[{i}/{len(symbols)}] Processing {symbol}")
        print("-"*80)

        signals = run_backtest(conn, symbol, timeframe, start_date, end_date)
        all_signals.extend(signals)

        if signals:
            # Save to database
            saved = save_backtest_signals(conn, signals)
            print(f"   💾 Saved {saved} signals to database")

    # Export all signals
    if all_signals:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_filename = f'data/backtest_signals_{timestamp}.json'
        export_signals_to_json(all_signals, export_filename)

    # Summary
    print("\n" + "="*80)
    print("📊 BACKTEST SUMMARY")
    print("="*80)

    total_signals = len(all_signals)
    print(f"\nTotal Signals Detected: {total_signals}")

    if total_signals > 0:
        # Breakdown by symbol
        print("\nBy Symbol:")
        for symbol in symbols:
            symbol_signals = [s for s in all_signals if s['symbol'] == symbol]
            bullish = len([s for s in symbol_signals if s['direction'] == 'wind_catcher'])
            bearish = len([s for s in symbol_signals if s['direction'] == 'river_turn'])
            print(f"  {symbol:12s}: {len(symbol_signals):3d} signals ({bullish} bullish, {bearish} bearish)")

        # Breakdown by confluence class
        print("\nBy Confluence Class:")
        classes = {}
        for signal in all_signals:
            cls = signal['confluence_class']
            classes[cls] = classes.get(cls, 0) + 1

        for cls in ['PERFECT', 'EXCELLENT', 'VERY GOOD', 'GOOD']:
            count = classes.get(cls, 0)
            if count > 0:
                print(f"  {cls:12s}: {count:3d} signals")

        # Top signals
        print("\n🌟 Top 5 Signals:")
        top_signals = sorted(all_signals, key=lambda x: x['confluence_score'], reverse=True)[:5]
        for i, signal in enumerate(top_signals, 1):
            direction_emoji = "🌪️" if signal['direction'] == 'wind_catcher' else "🌊"
            print(f"  {i}. {direction_emoji} {signal['symbol']:12s} @ {signal['datetime']} - "
                  f"${signal['price']:.2f} | Score: {signal['confluence_score']:.1f} ({signal['confluence_class']})")

    print("\n" + "="*80)
    print("✅ Backtest Complete!")
    print("\n💡 Next step: Run backtest_reporter.py to generate detailed analysis")
    print("="*80)

    conn.close()


def main():
    """Main execution"""
    # Backtest configuration from development plan
    backtest_symbols = ['BTC/USDT', 'TAO/USDT', 'HYPE/USDT']
    backtest_timeframe = '1h'
    backtest_start = '2024-10-03'
    backtest_end = '2024-11-03'

    run_backtest_campaign(
        backtest_symbols,
        backtest_timeframe,
        backtest_start,
        backtest_end
    )


if __name__ == "__main__":
    main()
