"""
Flask Web Application for Wind Catcher & River Turn
Main application file with API routes
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sqlite3
from datetime import datetime
import json
import sys
import os

# Add parent directory to path to import utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

from utils import DATABASE_FILE, load_config, get_current_timestamp

app = Flask(__name__)
CORS(app)  # Enable CORS for API requests

# Load configuration
config = load_config()


def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(str(DATABASE_FILE))
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


# ============================================================================
# WEB ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': get_current_timestamp(),
        'version': '1.0.0'
    })


# ============================================================================
# API ROUTES - WATCHLISTS
# ============================================================================

@app.route('/api/watchlists', methods=['GET'])
def get_watchlists():
    """
    Get all watchlists organized by direction and timeframe

    Returns:
        {
            "wind_catcher": {
                "8h": ["BTC", "SOL"],
                "1h": ["BTC", "TAO"],
                "15m": ["BTC", "SOL"]
            },
            "river_turn": {
                "8h": ["ETH", "SOL"],
                "1h": ["TAO", "HYPE"],
                "15m": ["BTC", "ETH"]
            }
        }
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT symbol, timeframe, direction
            FROM user_watchlists
            ORDER BY symbol, timeframe
        """)

        rows = cursor.fetchall()

        # Organize by direction and timeframe
        watchlists = {
            'wind_catcher': {'8h': [], '1h': [], '15m': [], '4h': []},
            'river_turn': {'8h': [], '1h': [], '15m': [], '4h': []}
        }

        for row in rows:
            symbol = row['symbol']
            timeframe = row['timeframe']
            direction = row['direction']

            if timeframe not in watchlists[direction]:
                watchlists[direction][timeframe] = []

            watchlists[direction][timeframe].append(symbol)

        return jsonify(watchlists)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/watchlist/add', methods=['POST'])
def add_to_watchlist():
    """
    Add a symbol to a watchlist

    Body: {"symbol": "BTC", "timeframe": "1h", "direction": "wind_catcher"}
    """
    data = request.get_json()

    symbol = data.get('symbol')
    timeframe = data.get('timeframe')
    direction = data.get('direction')

    # Validation
    if not symbol or not timeframe or not direction:
        return jsonify({'error': 'Missing required fields'}), 400

    if direction not in ['wind_catcher', 'river_turn']:
        return jsonify({'error': 'Invalid direction'}), 400

    if timeframe not in ['15m', '1h', '4h', '8h']:
        return jsonify({'error': 'Invalid timeframe'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO user_watchlists
            (symbol, timeframe, direction, added_at, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (symbol, timeframe, direction, get_current_timestamp(), 'Added via web'))

        conn.commit()

        return jsonify({
            'success': True,
            'message': f'Added {symbol} to {direction} {timeframe}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/watchlist/remove', methods=['DELETE'])
def remove_from_watchlist():
    """
    Remove a symbol from a watchlist

    Body: {"symbol": "BTC", "timeframe": "1h", "direction": "wind_catcher"}
    """
    data = request.get_json()

    symbol = data.get('symbol')
    timeframe = data.get('timeframe')
    direction = data.get('direction')

    if not symbol or not timeframe or not direction:
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM user_watchlists
            WHERE symbol = ? AND timeframe = ? AND direction = ?
        """, (symbol, timeframe, direction))

        conn.commit()

        return jsonify({
            'success': True,
            'message': f'Removed {symbol} from {direction} {timeframe}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/watchlist/move', methods=['POST'])
def move_watchlist_entry():
    """
    Move a symbol from one watchlist to another

    Body: {
        "symbol": "BTC",
        "from": {"timeframe": "8h", "direction": "wind_catcher"},
        "to": {"timeframe": "1h", "direction": "river_turn"}
    }
    """
    data = request.get_json()

    symbol = data.get('symbol')
    from_data = data.get('from', {})
    to_data = data.get('to', {})

    if not symbol or not from_data or not to_data:
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Remove from old location
        cursor.execute("""
            DELETE FROM user_watchlists
            WHERE symbol = ? AND timeframe = ? AND direction = ?
        """, (symbol, from_data['timeframe'], from_data['direction']))

        # Add to new location
        cursor.execute("""
            INSERT OR REPLACE INTO user_watchlists
            (symbol, timeframe, direction, added_at, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (symbol, to_data['timeframe'], to_data['direction'],
              get_current_timestamp(), 'Moved via web'))

        conn.commit()

        return jsonify({
            'success': True,
            'message': f'Moved {symbol} to {to_data["direction"]} {to_data["timeframe"]}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# ============================================================================
# API ROUTES - SIGNALS
# ============================================================================

@app.route('/api/signals/recent', methods=['GET'])
def get_recent_signals():
    """
    Get recent signals for the signal feed

    Query params:
        - limit: Max number of signals (default 50)
        - since: Unix timestamp, only return signals after this time

    Returns:
        {
            "signals": [...],
            "latest_timestamp": 1234567890
        }
    """
    limit = request.args.get('limit', 50, type=int)
    since = request.args.get('since', 0, type=int)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT
                id, timestamp, symbol, timeframe, system, signal_type,
                price, confluence_score, confluence_class,
                indicators_firing, volume_level, volume_ratio,
                created_at
            FROM signals
            WHERE confluence_score >= 1.2
        """

        params = []

        if since > 0:
            query += " AND timestamp > ?"
            params.append(since)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        signals = []
        latest_timestamp = 0

        for row in rows:
            signal = {
                'id': row['id'],
                'timestamp': row['timestamp'],
                'datetime': datetime.fromtimestamp(row['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                'symbol': row['symbol'],
                'timeframe': row['timeframe'],
                'direction': row['system'],
                'confluence_score': row['confluence_score'],
                'confluence_class': row['confluence_class'],
                'price': row['price'],
                'volume_level': row['volume_level'],
                'volume_ratio': row['volume_ratio'],
                'indicators_summary': _format_indicators_summary(row['indicators_firing']),
                'emoji': _get_confluence_emoji(row['confluence_class']),
                'system_emoji': '🌪️' if row['system'] == 'wind_catcher' else '🌊'
            }

            signals.append(signal)
            latest_timestamp = max(latest_timestamp, row['timestamp'])

        return jsonify({
            'signals': signals,
            'latest_timestamp': latest_timestamp
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/signals/stats', methods=['GET'])
def get_signal_stats():
    """
    Get signal statistics for dashboard

    Returns:
        {
            "total_today": 15,
            "perfect_count": 3,
            "excellent_count": 5,
            "by_direction": {"wind_catcher": 8, "river_turn": 7}
        }
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get today's signals
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_timestamp = int(today_start.timestamp())

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN confluence_score >= 3.0 THEN 1 ELSE 0 END) as perfect,
                SUM(CASE WHEN confluence_score >= 2.5 AND confluence_score < 3.0 THEN 1 ELSE 0 END) as excellent,
                SUM(CASE WHEN system = 'wind_catcher' THEN 1 ELSE 0 END) as wind_catcher,
                SUM(CASE WHEN system = 'river_turn' THEN 1 ELSE 0 END) as river_turn
            FROM signals
            WHERE timestamp >= ?
        """, (today_timestamp,))

        row = cursor.fetchone()

        return jsonify({
            'total_today': row['total'] or 0,
            'perfect_count': row['perfect'] or 0,
            'excellent_count': row['excellent'] or 0,
            'by_direction': {
                'wind_catcher': row['wind_catcher'] or 0,
                'river_turn': row['river_turn'] or 0
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/system/status', methods=['GET'])
def get_system_status():
    """Get system status information"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get latest price data timestamp
        cursor.execute("""
            SELECT MAX(timestamp) as latest_data
            FROM price_data
        """)
        latest_data = cursor.fetchone()['latest_data']

        # Get count of active watchlist pairs
        cursor.execute("""
            SELECT COUNT(DISTINCT symbol || timeframe) as active_pairs
            FROM user_watchlists
        """)
        active_pairs = cursor.fetchone()['active_pairs']

        # Get today's signal count
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_timestamp = int(today_start.timestamp())

        cursor.execute("""
            SELECT COUNT(*) as signals_today
            FROM signals
            WHERE timestamp >= ?
        """, (today_timestamp,))
        signals_today = cursor.fetchone()['signals_today']

        # Get database size
        db_size_mb = os.path.getsize(str(DATABASE_FILE)) / (1024 * 1024)

        return jsonify({
            'status': 'ok',
            'last_data_update': datetime.fromtimestamp(latest_data).strftime('%Y-%m-%d %H:%M:%S') if latest_data else 'N/A',
            'active_pairs': active_pairs,
            'signals_today': signals_today,
            'database_size_mb': round(db_size_mb, 2),
            'telegram_enabled': config.get('telegram', {}).get('enabled', False)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _format_indicators_summary(indicators_json):
    """Format indicators firing JSON as readable string"""
    if not indicators_json:
        return "No indicators"

    try:
        indicators = json.loads(indicators_json)
        parts = []

        if indicators.get('hull', 0) > 0:
            parts.append(f"Hull({indicators['hull']})")
        if indicators.get('ao', 0) > 0:
            parts.append(f"AO({indicators['ao']})")
        if indicators.get('alligator', 0) > 0:
            parts.append(f"Alligator({indicators['alligator']})")
        if indicators.get('ichimoku', 0) > 0:
            parts.append(f"Ichimoku({indicators['ichimoku']})")
        if indicators.get('volume', 0) > 0:
            parts.append(f"Volume({indicators['volume']})")

        return ", ".join(parts) if parts else "No indicators"

    except:
        return "Unknown"


def _get_confluence_emoji(confluence_class):
    """Get emoji for confluence classification"""
    emojis = {
        'PERFECT': '⭐',
        'EXCELLENT': '🌟',
        'VERY GOOD': '✨',
        'GOOD': '💫',
        'INTERESTING': '💡',
        'WEAK': '🔍'
    }
    return emojis.get(confluence_class, '💫')


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("🚀 Wind Catcher & River Turn - Web Interface")
    print("="*60)
    print(f"Starting Flask server...")
    print(f"Database: {DATABASE_FILE}")
    print(f"Open browser to: http://localhost:5000")
    print("="*60)

    # Check if flask-cors is installed
    try:
        import flask_cors
    except ImportError:
        print("\n⚠️  Warning: flask-cors not installed")
        print("   Install with: pip install flask-cors")
        print()

    app.run(host='0.0.0.0', port=5000, debug=True)
