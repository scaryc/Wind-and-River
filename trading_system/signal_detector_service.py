"""
Signal Detector Service
Continuously scans watchlists and detects new signals every 5 minutes
"""

import sqlite3
import time
import json
from datetime import datetime, timedelta
from master_confluence import analyze_master_confluence, connect_to_database
from telegram_bot import send_signal_alert


def get_user_watchlists(conn):
    """Get all active watchlists from user_watchlists table"""
    cursor = conn.cursor()

    query = '''
        SELECT symbol, timeframe, direction
        FROM user_watchlists
        ORDER BY symbol, timeframe, direction
    '''

    cursor.execute(query)
    watchlists = cursor.fetchall()

    return [(symbol, timeframe, direction) for symbol, timeframe, direction in watchlists]


def signal_exists(conn, symbol, timeframe, timestamp, hours_window=4):
    """
    Check if a signal already exists within the time window

    This prevents duplicate alerts for the same signal
    """
    cursor = conn.cursor()

    # Calculate time window
    window_start = timestamp - (hours_window * 3600)
    window_end = timestamp + (hours_window * 3600)

    query = '''
        SELECT COUNT(*)
        FROM signals
        WHERE symbol = ?
        AND timeframe = ?
        AND timestamp >= ?
        AND timestamp <= ?
    '''

    cursor.execute(query, (symbol, timeframe, window_start, window_end))
    count = cursor.fetchone()[0]

    return count > 0


def save_signal(conn, result):
    """Save detected signal to database"""
    cursor = conn.cursor()

    # Prepare indicators_firing JSON
    indicators_firing = {
        'hull': len(result['hull_signals']),
        'ao': len(result['ao_signals']),
        'alligator': len(result['alligator_signals']),
        'ichimoku': len(result['ichimoku_signals']),
        'volume': 1 if result['volume_signals'] and result['volume_signals'][-1]['level'] != 'NORMAL' else 0
    }

    # Get volume info
    volume_level = result['volume_signals'][-1]['level'] if result['volume_signals'] else 'NORMAL'
    volume_ratio = result['volume_signals'][-1]['ratio'] if result['volume_signals'] else 1.0

    # Signal details (top factors)
    details = '; '.join(result['confluence']['factors'][:3])

    try:
        cursor.execute('''
            INSERT INTO signals
            (timestamp, symbol, timeframe, system, signal_type,
             confluence_score, confluence_class, price,
             indicators_firing, volume_level, volume_ratio,
             details, notified, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            int(result['timestamp']),
            result['symbol'],
            result['timeframe'],
            result['confluence']['primary_system'],
            'confluence',
            result['confluence']['score'],
            result['confluence']['classification'],
            result['price'],
            json.dumps(indicators_firing),
            volume_level,
            volume_ratio,
            details,
            0,  # Not notified yet
            int(datetime.now().timestamp())
        ))

        conn.commit()
        signal_id = cursor.lastrowid
        return signal_id

    except Exception as e:
        print(f"  ⚠️  Error saving signal: {e}")
        return None


def get_signal_by_id(conn, signal_id):
    """Get full signal details by ID"""
    cursor = conn.cursor()

    query = '''
        SELECT *
        FROM signals
        WHERE id = ?
    '''

    cursor.execute(query, (signal_id,))
    row = cursor.fetchone()

    if not row:
        return None

    columns = [desc[0] for desc in cursor.description]
    signal = dict(zip(columns, row))

    # Parse JSON fields
    if signal.get('indicators_firing'):
        try:
            signal['indicators_firing'] = json.loads(signal['indicators_firing'])
        except:
            signal['indicators_firing'] = {}

    # Add formatted datetime
    signal['datetime'] = datetime.fromtimestamp(signal['timestamp']).strftime('%Y-%m-%d %H:%M:%S')

    # Add emojis
    signal['system_emoji'] = "🌪️" if signal['system'] == 'wind_catcher' else "🌊"

    confluence_emoji_map = {
        'PERFECT': '⭐',
        'EXCELLENT': '🌟',
        'VERY GOOD': '✨',
        'GOOD': '💫',
        'INTERESTING': '💡'
    }
    signal['emoji'] = confluence_emoji_map.get(signal['confluence_class'], '❓')

    return signal


def mark_signal_notified(conn, signal_id):
    """Mark signal as notified"""
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE signals
            SET notified = 1
            WHERE id = ?
        ''', (signal_id,))

        conn.commit()
        return True

    except Exception as e:
        print(f"  ⚠️  Error marking signal as notified: {e}")
        return False


def run_signal_detection_loop(interval_seconds=300, min_score=1.2):
    """
    Main service loop - runs every 5 minutes

    Parameters:
    - interval_seconds: How often to scan (default: 300 = 5 minutes)
    - min_score: Minimum confluence score to record (default: 1.2 = GOOD+)
    """
    print("="*80)
    print("🎯 SIGNAL DETECTOR SERVICE")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Scan Interval: {interval_seconds} seconds ({interval_seconds//60} minutes)")
    print(f"  Min Score: {min_score} (GOOD+)")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "="*80)
    print("\nService running... Press Ctrl+C to stop\n")

    scan_count = 0

    while True:
        try:
            scan_count += 1
            scan_start = datetime.now()

            print(f"\n[Scan #{scan_count}] {scan_start.strftime('%Y-%m-%d %H:%M:%S')}")
            print("-"*80)

            conn = connect_to_database()

            # Get all active watchlists
            watchlists = get_user_watchlists(conn)

            if not watchlists:
                print("⚠️  No watchlists configured. Add symbols to user_watchlists table.")
                conn.close()
                time.sleep(interval_seconds)
                continue

            print(f"📋 Scanning {len(watchlists)} watchlist entries...")

            new_signals = []
            skipped_count = 0

            for symbol, timeframe, direction in watchlists:
                try:
                    # Analyze confluence for this symbol/timeframe
                    result = analyze_master_confluence(conn, symbol, timeframe=timeframe)

                    if result and result['confluence']['score'] >= min_score:
                        # Check if signal matches watchlist direction
                        signal_system = result['confluence']['primary_system']

                        if signal_system == direction:
                            # Check if signal already exists (avoid duplicates)
                            if not signal_exists(conn, symbol, timeframe,
                                                int(result['timestamp']), hours_window=4):
                                # New signal - save it
                                signal_id = save_signal(conn, result)

                                if signal_id:
                                    new_signals.append(signal_id)

                                    # Print detection
                                    emoji = result['confluence']['emoji']
                                    direction_emoji = "🌪️" if direction == 'wind_catcher' else "🌊"
                                    print(f"  {emoji} {direction_emoji} NEW: {symbol} [{timeframe}] - "
                                          f"${result['price']:.2f} | Score: {result['confluence']['score']:.1f} "
                                          f"({result['confluence']['classification']})")

                                    # Send Telegram notification
                                    signal_details = get_signal_by_id(conn, signal_id)
                                    if signal_details and send_signal_alert(signal_details):
                                        mark_signal_notified(conn, signal_id)
                                        print(f"    📱 Telegram alert sent")
                            else:
                                skipped_count += 1

                except Exception as e:
                    # Log error but continue with other pairs
                    print(f"  ⚠️  Error analyzing {symbol} [{timeframe}]: {e}")

            conn.close()

            # Summary
            scan_duration = (datetime.now() - scan_start).total_seconds()

            print(f"\n✅ Scan complete in {scan_duration:.1f}s")
            print(f"   New signals: {len(new_signals)}")
            print(f"   Duplicates skipped: {skipped_count}")

            if new_signals:
                print(f"   🎉 {len(new_signals)} new signal(s) detected!")

            # Wait for next scan
            next_scan = datetime.now() + timedelta(seconds=interval_seconds)
            print(f"\n⏰ Next scan at: {next_scan.strftime('%Y-%m-%d %H:%M:%S')}")

            time.sleep(interval_seconds)

        except KeyboardInterrupt:
            print("\n\n⏹️  Service stopped by user")
            break

        except Exception as e:
            print(f"\n❌ Error in signal detection loop: {e}")
            import traceback
            traceback.print_exc()
            print(f"\n⏸️  Waiting {interval_seconds//60} minute before retry...")
            time.sleep(interval_seconds)


def test_single_scan():
    """Run a single scan for testing"""
    print("="*80)
    print("🧪 SIGNAL DETECTOR - TEST MODE")
    print("="*80)
    print()

    conn = connect_to_database()

    # Get watchlists
    watchlists = get_user_watchlists(conn)

    if not watchlists:
        print("⚠️  No watchlists configured.")
        print("\n💡 Add test watchlists by running:")
        print("   python multi_timeframe_collector.py")
        conn.close()
        return

    print(f"📋 Found {len(watchlists)} watchlist entries:")
    for symbol, timeframe, direction in watchlists:
        emoji = "🌪️" if direction == 'wind_catcher' else "🌊"
        print(f"  {emoji} {symbol} [{timeframe}] - {direction}")

    print(f"\n🔍 Running test scan...\n")

    signals_found = []

    for symbol, timeframe, direction in watchlists:
        try:
            result = analyze_master_confluence(conn, symbol, timeframe=timeframe)

            if result:
                score = result['confluence']['score']
                print(f"{symbol:12s} [{timeframe}]: Score {score:.2f} "
                      f"({result['confluence']['classification']}) - "
                      f"{result['confluence']['primary_system']}")

                if score >= 1.2 and result['confluence']['primary_system'] == direction:
                    signals_found.append((symbol, timeframe, score))

        except Exception as e:
            print(f"{symbol:12s} [{timeframe}]: ⚠️  Error - {e}")

    print(f"\n✅ Test scan complete!")
    print(f"   Signals found: {len(signals_found)}")

    if signals_found:
        print("\n   Detected signals:")
        for symbol, timeframe, score in signals_found:
            print(f"     - {symbol} [{timeframe}]: Score {score:.2f}")

    conn.close()


def main():
    """Main execution"""
    import sys

    # Check for test mode
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_single_scan()
    else:
        # Run continuous service
        run_signal_detection_loop(interval_seconds=300, min_score=1.2)


if __name__ == "__main__":
    main()
