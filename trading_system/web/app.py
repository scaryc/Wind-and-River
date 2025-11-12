"""
Flask Web Application for Wind Catcher & River Turn
Main web server for the trading system dashboard
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sys
import os

# Add parent directory to path to import db_helpers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_helpers import (
    connect_to_database,
    get_user_watchlists,
    add_to_watchlist,
    remove_from_watchlist,
    move_between_watchlists,
    get_recent_signals,
    get_signal_by_id,
    get_system_status,
    get_available_symbols,
    get_signal_stats
)


def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    CORS(app)  # Enable CORS for API requests

    # ========================================================================
    # PAGE ROUTES
    # ========================================================================

    @app.route('/')
    def index():
        """Main dashboard page"""
        return render_template('index.html')

    # ========================================================================
    # WATCHLIST API ENDPOINTS
    # ========================================================================

    @app.route('/api/watchlists', methods=['GET'])
    def api_get_watchlists():
        """Get all watchlists organized by direction and timeframe"""
        try:
            conn = connect_to_database()
            watchlists = get_user_watchlists(conn)
            conn.close()

            return jsonify(watchlists), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/watchlist/add', methods=['POST'])
    def api_add_to_watchlist():
        """Add symbol to watchlist"""
        try:
            data = request.json

            # Validate required fields
            symbol = data.get('symbol')
            timeframe = data.get('timeframe')
            direction = data.get('direction')

            if not all([symbol, timeframe, direction]):
                return jsonify({'error': 'Missing required fields'}), 400

            # Validate timeframe
            if timeframe not in ['8h', '1h', '15m']:
                return jsonify({'error': 'Invalid timeframe'}), 400

            # Validate direction
            if direction not in ['wind_catcher', 'river_turn']:
                return jsonify({'error': 'Invalid direction'}), 400

            conn = connect_to_database()
            success = add_to_watchlist(conn, symbol, timeframe, direction)
            conn.close()

            if success:
                return jsonify({'success': True, 'message': 'Added to watchlist'}), 200
            else:
                return jsonify({'success': False, 'message': 'Already in watchlist'}), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/watchlist/remove', methods=['DELETE'])
    def api_remove_from_watchlist():
        """Remove symbol from watchlist"""
        try:
            data = request.json

            symbol = data.get('symbol')
            timeframe = data.get('timeframe')
            direction = data.get('direction')

            if not all([symbol, timeframe, direction]):
                return jsonify({'error': 'Missing required fields'}), 400

            conn = connect_to_database()
            success = remove_from_watchlist(conn, symbol, timeframe, direction)
            conn.close()

            if success:
                return jsonify({'success': True, 'message': 'Removed from watchlist'}), 200
            else:
                return jsonify({'success': False, 'message': 'Not found in watchlist'}), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/watchlist/move', methods=['POST'])
    def api_move_watchlist():
        """Move symbol between watchlists"""
        try:
            data = request.json

            symbol = data.get('symbol')
            from_data = data.get('from', {})
            to_data = data.get('to', {})

            from_timeframe = from_data.get('timeframe')
            from_direction = from_data.get('direction')
            to_timeframe = to_data.get('timeframe')
            to_direction = to_data.get('direction')

            if not all([symbol, from_timeframe, from_direction, to_timeframe, to_direction]):
                return jsonify({'error': 'Missing required fields'}), 400

            conn = connect_to_database()
            success = move_between_watchlists(
                conn, symbol,
                from_timeframe, from_direction,
                to_timeframe, to_direction
            )
            conn.close()

            if success:
                return jsonify({'success': True, 'message': 'Moved to new watchlist'}), 200
            else:
                return jsonify({'success': False, 'message': 'Move failed'}), 500

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ========================================================================
    # SIGNAL API ENDPOINTS
    # ========================================================================

    @app.route('/api/signals/recent', methods=['GET'])
    def api_get_recent_signals():
        """Get recent signals for chat feed"""
        try:
            # Get query parameters
            limit = int(request.args.get('limit', 50))
            since = request.args.get('since')  # Unix timestamp
            timeframe = request.args.get('timeframe')
            symbol = request.args.get('symbol')

            conn = connect_to_database()
            signals = get_recent_signals(
                conn,
                limit=limit,
                timeframe=timeframe,
                symbol=symbol
            )
            conn.close()

            # Filter by since timestamp if provided
            if since:
                since_ts = int(since)
                signals = [s for s in signals if s['timestamp'] > since_ts]

            # Get latest timestamp
            latest_timestamp = max([s['timestamp'] for s in signals]) if signals else 0

            return jsonify({
                'signals': signals,
                'latest_timestamp': latest_timestamp
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/signals/<int:signal_id>', methods=['GET'])
    def api_get_signal(signal_id):
        """Get full details for specific signal"""
        try:
            conn = connect_to_database()
            signal = get_signal_by_id(conn, signal_id)
            conn.close()

            if signal:
                return jsonify(signal), 200
            else:
                return jsonify({'error': 'Signal not found'}), 404

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/signals/stats', methods=['GET'])
    def api_get_signal_stats():
        """Get signal statistics for dashboard"""
        try:
            conn = connect_to_database()
            stats = get_signal_stats(conn)
            conn.close()

            return jsonify(stats), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ========================================================================
    # SYSTEM API ENDPOINTS
    # ========================================================================

    @app.route('/api/system/status', methods=['GET'])
    def api_get_system_status():
        """Get overall system health"""
        try:
            conn = connect_to_database()
            status = get_system_status(conn)
            conn.close()

            return jsonify(status), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/system/pairs', methods=['GET'])
    def api_get_available_pairs():
        """Get list of available trading pairs"""
        try:
            conn = connect_to_database()
            symbols = get_available_symbols(conn)
            conn.close()

            return jsonify({
                'pairs': symbols,
                'total': len(symbols)
            }), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return app


def main():
    """Run the web server"""
    print("="*80)
    print("🌐 Wind Catcher & River Turn - Web Dashboard")
    print("="*80)

    app = create_app()

    host = '0.0.0.0'
    port = 5000

    print(f"\n🚀 Starting web server...")
    print(f"   URL: http://localhost:{port}")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print("\nPress Ctrl+C to stop\n")
    print("="*80)

    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    main()
