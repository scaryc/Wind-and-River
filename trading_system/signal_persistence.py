"""
Signal Persistence for Wind Catcher & River Turn Trading System
Stores and retrieves trading signals from the database
"""

from utils import connect_to_database, get_current_timestamp, log_message


def save_signal(conn, symbol, system, signal_type, price, notes="", timestamp=None):
    """
    Save a trading signal to the database

    Args:
        conn: Database connection
        symbol (str): Trading pair symbol (e.g., 'BTC/USDT')
        system (str): 'wind_catcher' or 'river_turn'
        signal_type (str): Type of signal (e.g., 'hull_bullish_break', 'ao_divergence')
        price (float): Price when signal was detected
        notes (str): Additional notes about the signal
        timestamp (int): Signal timestamp (defaults to current time)

    Returns:
        int: Signal ID if successful, None otherwise
    """
    if timestamp is None:
        timestamp = get_current_timestamp()

    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO signals
            (timestamp, symbol, system, signal_type, price, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, symbol, system, signal_type, price, notes, get_current_timestamp()))

        conn.commit()
        signal_id = cursor.lastrowid

        log_message(
            f"Signal saved: {system.upper()} - {signal_type} on {symbol} at ${price:.4f}",
            "INFO"
        )

        return signal_id

    except Exception as e:
        log_message(f"Error saving signal: {e}", "ERROR")
        return None
    finally:
        cursor.close()


def save_signals_batch(conn, signals_list):
    """
    Save multiple signals at once

    Args:
        conn: Database connection
        signals_list (list): List of signal dictionaries with keys:
                            symbol, system, signal_type, price, notes, timestamp

    Returns:
        int: Number of signals saved successfully
    """
    saved_count = 0
    cursor = conn.cursor()

    try:
        current_time = get_current_timestamp()

        for signal_data in signals_list:
            try:
                timestamp = signal_data.get('timestamp', current_time)
                symbol = signal_data['symbol']
                system = signal_data['system']
                signal_type = signal_data['signal_type']
                price = signal_data['price']
                notes = signal_data.get('notes', '')

                cursor.execute('''
                    INSERT INTO signals
                    (timestamp, symbol, system, signal_type, price, notes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, symbol, system, signal_type, price, notes, current_time))

                saved_count += 1

            except KeyError as e:
                log_message(f"Missing required field in signal data: {e}", "ERROR")
            except Exception as e:
                log_message(f"Error saving individual signal: {e}", "ERROR")

        conn.commit()

        if saved_count > 0:
            log_message(f"Saved {saved_count} signals to database", "INFO")

        return saved_count

    except Exception as e:
        log_message(f"Error in batch signal save: {e}", "ERROR")
        return saved_count
    finally:
        cursor.close()


def get_recent_signals(conn, hours=24, system=None, symbol=None):
    """
    Get recent signals from database

    Args:
        conn: Database connection
        hours (int): Number of hours to look back
        system (str): Filter by system ('wind_catcher', 'river_turn', or None for all)
        symbol (str): Filter by symbol (or None for all)

    Returns:
        list: List of signal dictionaries
    """
    cursor = conn.cursor()
    try:
        # Calculate cutoff timestamp
        cutoff_timestamp = get_current_timestamp() - (hours * 3600)

        # Build query with optional filters
        query = '''
            SELECT id, timestamp, symbol, system, signal_type, price, notes, created_at
            FROM signals
            WHERE timestamp >= ?
        '''
        params = [cutoff_timestamp]

        if system:
            query += ' AND system = ?'
            params.append(system)

        if symbol:
            query += ' AND symbol = ?'
            params.append(symbol)

        query += ' ORDER BY timestamp DESC'

        cursor.execute(query, params)
        rows = cursor.fetchall()

        signals = []
        for row in rows:
            signals.append({
                'id': row[0],
                'timestamp': row[1],
                'symbol': row[2],
                'system': row[3],
                'signal_type': row[4],
                'price': row[5],
                'notes': row[6],
                'created_at': row[7]
            })

        return signals

    except Exception as e:
        log_message(f"Error fetching signals: {e}", "ERROR")
        return []
    finally:
        cursor.close()


def get_signal_stats(conn, days=7):
    """
    Get signal statistics for the past N days

    Args:
        conn: Database connection
        days (int): Number of days to analyze

    Returns:
        dict: Statistics dictionary
    """
    cursor = conn.cursor()
    try:
        cutoff_timestamp = get_current_timestamp() - (days * 24 * 3600)

        # Total signals
        cursor.execute('SELECT COUNT(*) FROM signals WHERE timestamp >= ?', (cutoff_timestamp,))
        total_signals = cursor.fetchone()[0]

        # Signals by system
        cursor.execute('''
            SELECT system, COUNT(*) as count
            FROM signals
            WHERE timestamp >= ?
            GROUP BY system
        ''', (cutoff_timestamp,))
        system_counts = dict(cursor.fetchall())

        # Signals by symbol
        cursor.execute('''
            SELECT symbol, COUNT(*) as count
            FROM signals
            WHERE timestamp >= ?
            GROUP BY symbol
            ORDER BY count DESC
            LIMIT 10
        ''', (cutoff_timestamp,))
        top_symbols = cursor.fetchall()

        # Most common signal types
        cursor.execute('''
            SELECT signal_type, COUNT(*) as count
            FROM signals
            WHERE timestamp >= ?
            GROUP BY signal_type
            ORDER BY count DESC
            LIMIT 10
        ''', (cutoff_timestamp,))
        top_signal_types = cursor.fetchall()

        return {
            'days': days,
            'total_signals': total_signals,
            'wind_catcher_count': system_counts.get('wind_catcher', 0),
            'river_turn_count': system_counts.get('river_turn', 0),
            'top_symbols': top_symbols,
            'top_signal_types': top_signal_types
        }

    except Exception as e:
        log_message(f"Error calculating signal stats: {e}", "ERROR")
        return None
    finally:
        cursor.close()


def cleanup_old_signals(conn, days_to_keep=30):
    """
    Remove signals older than specified days

    Args:
        conn: Database connection
        days_to_keep (int): Number of days of signals to keep

    Returns:
        int: Number of signals deleted
    """
    cursor = conn.cursor()
    try:
        cutoff_timestamp = get_current_timestamp() - (days_to_keep * 24 * 3600)

        cursor.execute('DELETE FROM signals WHERE timestamp < ?', (cutoff_timestamp,))
        deleted_count = cursor.rowcount

        conn.commit()

        if deleted_count > 0:
            log_message(f"Cleaned up {deleted_count} old signals (older than {days_to_keep} days)", "INFO")

        return deleted_count

    except Exception as e:
        log_message(f"Error cleaning up signals: {e}", "ERROR")
        return 0
    finally:
        cursor.close()


# Example usage
if __name__ == "__main__":
    print("Signal Persistence Module - Test")
    print("="*60)

    try:
        conn = connect_to_database()

        # Test: Save a signal
        print("\n1. Testing save_signal()...")
        signal_id = save_signal(
            conn,
            symbol="BTC/USDT",
            system="wind_catcher",
            signal_type="hull_bullish_break",
            price=45000.50,
            notes="First close above Hull 21 with high volume"
        )
        print(f"   Saved signal ID: {signal_id}")

        # Test: Get recent signals
        print("\n2. Testing get_recent_signals()...")
        recent = get_recent_signals(conn, hours=24)
        print(f"   Found {len(recent)} signals in last 24 hours")

        # Test: Get stats
        print("\n3. Testing get_signal_stats()...")
        stats = get_signal_stats(conn, days=7)
        if stats:
            print(f"   Total signals (7 days): {stats['total_signals']}")
            print(f"   Wind Catcher: {stats['wind_catcher_count']}")
            print(f"   River Turn: {stats['river_turn_count']}")

        conn.close()
        print("\n✅ All tests completed successfully!")

    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("   Run database_setup.py first")
    except Exception as e:
        print(f"❌ Error: {e}")
