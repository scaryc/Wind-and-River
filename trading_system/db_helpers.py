"""
Database Helper Functions
Centralized database operations for the trading system
"""

import sqlite3
import json
from datetime import datetime


def connect_to_database(db_path='data/trading_system.db'):
    """Connect to SQLite database"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return None


# ============================================================================
# WATCHLIST OPERATIONS
# ============================================================================

def get_user_watchlists(conn, direction=None, timeframe=None):
    """
    Get user watchlists, optionally filtered

    Parameters:
    - conn: Database connection
    - direction: Filter by direction ('wind_catcher' or 'river_turn')
    - timeframe: Filter by timeframe ('8h', '1h', '15m')

    Returns:
    - dict: Organized watchlists
    """
    cursor = conn.cursor()

    query = 'SELECT symbol, timeframe, direction FROM user_watchlists'
    conditions = []
    params = []

    if direction:
        conditions.append('direction = ?')
        params.append(direction)

    if timeframe:
        conditions.append('timeframe = ?')
        params.append(timeframe)

    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)

    query += ' ORDER BY direction, timeframe, symbol'

    cursor.execute(query, params)
    rows = cursor.fetchall()

    # Organize by direction and timeframe
    watchlists = {
        'wind_catcher': {'8h': [], '1h': [], '15m': []},
        'river_turn': {'8h': [], '1h': [], '15m': []}
    }

    for symbol, tf, dir in rows:
        if dir in watchlists and tf in watchlists[dir]:
            watchlists[dir][tf].append(symbol)

    return watchlists


def add_to_watchlist(conn, symbol, timeframe, direction):
    """Add symbol to a specific watchlist"""
    cursor = conn.cursor()
    current_time = int(datetime.now().timestamp())

    try:
        cursor.execute('''
            INSERT OR IGNORE INTO user_watchlists
            (symbol, timeframe, direction, added_at)
            VALUES (?, ?, ?, ?)
        ''', (symbol, timeframe, direction, current_time))

        conn.commit()
        return cursor.rowcount > 0

    except Exception as e:
        print(f"Error adding to watchlist: {e}")
        return False


def remove_from_watchlist(conn, symbol, timeframe, direction):
    """Remove symbol from watchlist"""
    cursor = conn.cursor()

    try:
        cursor.execute('''
            DELETE FROM user_watchlists
            WHERE symbol = ? AND timeframe = ? AND direction = ?
        ''', (symbol, timeframe, direction))

        conn.commit()
        return cursor.rowcount > 0

    except Exception as e:
        print(f"Error removing from watchlist: {e}")
        return False


def move_between_watchlists(conn, symbol, from_tf, from_dir, to_tf, to_dir):
    """Move symbol from one watchlist to another"""
    # Remove from source
    if remove_from_watchlist(conn, symbol, from_tf, from_dir):
        # Add to destination
        return add_to_watchlist(conn, symbol, to_tf, to_dir)

    return False


# ============================================================================
# SIGNAL OPERATIONS
# ============================================================================

def get_recent_signals(conn, limit=50, min_score=1.2, timeframe=None, symbol=None):
    """
    Get recent signals for display

    Parameters:
    - conn: Database connection
    - limit: Maximum number of signals to return
    - min_score: Minimum confluence score filter
    - timeframe: Optional timeframe filter
    - symbol: Optional symbol filter

    Returns:
    - list: Recent signals
    """
    cursor = conn.cursor()

    query = '''
        SELECT id, timestamp, symbol, timeframe, system, signal_type,
               confluence_score, confluence_class, price,
               indicators_firing, volume_level, volume_ratio,
               details, notified
        FROM signals
        WHERE confluence_score >= ?
    '''

    params = [min_score]

    if timeframe:
        query += ' AND timeframe = ?'
        params.append(timeframe)

    if symbol:
        query += ' AND symbol = ?'
        params.append(symbol)

    query += ' ORDER BY timestamp DESC LIMIT ?'
    params.append(limit)

    cursor.execute(query, params)

    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    signals = []
    for row in rows:
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

        # Create indicators summary
        if signal.get('indicators_firing'):
            ind = signal['indicators_firing']
            ind_parts = []
            if ind.get('hull', 0) > 0:
                ind_parts.append(f"Hull({ind['hull']})")
            if ind.get('ao', 0) > 0:
                ind_parts.append(f"AO({ind['ao']})")
            if ind.get('alligator', 0) > 0:
                ind_parts.append(f"Alligator({ind['alligator']})")
            if ind.get('ichimoku', 0) > 0:
                ind_parts.append(f"Ichimoku({ind['ichimoku']})")
            if ind.get('volume', 0) > 0:
                ind_parts.append(f"Volume({ind['volume']})")

            signal['indicators_summary'] = ', '.join(ind_parts) if ind_parts else 'None'
        else:
            signal['indicators_summary'] = 'None'

        signals.append(signal)

    return signals


def get_signal_by_id(conn, signal_id):
    """Get full signal details by ID"""
    signals = get_recent_signals(conn, limit=1)

    cursor = conn.cursor()
    cursor.execute('SELECT * FROM signals WHERE id = ?', (signal_id,))

    row = cursor.fetchone()
    if not row:
        return None

    columns = [desc[0] for desc in cursor.description]
    signal = dict(zip(columns, row))

    # Parse JSON and add formatting (same as get_recent_signals)
    if signal.get('indicators_firing'):
        try:
            signal['indicators_firing'] = json.loads(signal['indicators_firing'])
        except:
            signal['indicators_firing'] = {}

    signal['datetime'] = datetime.fromtimestamp(signal['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
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
    """Mark signal as sent to Telegram"""
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
        print(f"Error marking signal as notified: {e}")
        return False


# ============================================================================
# SYSTEM STATUS
# ============================================================================

def get_system_status(conn):
    """Return system health information"""
    cursor = conn.cursor()

    # Last data update
    cursor.execute('SELECT MAX(created_at) FROM price_data')
    last_data_update = cursor.fetchone()[0]

    # Signals today
    today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    cursor.execute('SELECT COUNT(*) FROM signals WHERE timestamp >= ?', (today_start,))
    signals_today = cursor.fetchone()[0]

    # Active pairs
    cursor.execute('SELECT COUNT(DISTINCT symbol) FROM user_watchlists')
    active_pairs = cursor.fetchone()[0]

    # Database size
    cursor.execute('SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()')
    db_size_bytes = cursor.fetchone()[0]
    db_size_mb = db_size_bytes / (1024 * 1024)

    return {
        'status': 'ok',
        'last_data_update': datetime.fromtimestamp(last_data_update).strftime('%Y-%m-%d %H:%M:%S') if last_data_update else 'Never',
        'next_data_collection': 'Every 5 minutes',
        'last_signal_scan': 'Real-time',
        'database_size_mb': round(db_size_mb, 2),
        'active_pairs': active_pairs,
        'signals_today': signals_today
    }


def get_available_symbols(conn):
    """Get list of all symbols that have price data"""
    cursor = conn.cursor()

    cursor.execute('SELECT DISTINCT symbol FROM price_data ORDER BY symbol')
    symbols = [row[0] for row in cursor.fetchall()]

    return symbols


# ============================================================================
# STATISTICS
# ============================================================================

def get_signal_stats(conn):
    """Get signal statistics for dashboard"""
    cursor = conn.cursor()

    # Today's signals
    today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())

    cursor.execute('SELECT COUNT(*) FROM signals WHERE timestamp >= ?', (today_start,))
    total_today = cursor.fetchone()[0]

    # By class today
    cursor.execute('''
        SELECT confluence_class, COUNT(*)
        FROM signals
        WHERE timestamp >= ?
        GROUP BY confluence_class
    ''', (today_start,))

    by_class = dict(cursor.fetchall())

    # By direction today
    cursor.execute('''
        SELECT system, COUNT(*)
        FROM signals
        WHERE timestamp >= ?
        GROUP BY system
    ''', (today_start,))

    by_direction = dict(cursor.fetchall())

    return {
        'total_today': total_today,
        'perfect_count': by_class.get('PERFECT', 0),
        'excellent_count': by_class.get('EXCELLENT', 0),
        'by_direction': {
            'wind_catcher': by_direction.get('wind_catcher', 0),
            'river_turn': by_direction.get('river_turn', 0)
        }
    }
