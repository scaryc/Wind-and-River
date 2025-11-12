"""
Service Manager for Wind Catcher & River Turn Trading System
Starts and manages all background services
"""

import threading
import time
import signal
import sys
from datetime import datetime

# Import service modules
from multi_timeframe_collector import collect_all_watchlist_data, load_config, connect_to_database
from signal_detector_service import run_signal_detection_loop
from web.app import create_app


# Global shutdown flag
shutdown_flag = threading.Event()


def data_collection_service():
    """Background thread: Collect data every 5 minutes"""
    print("🔄 Data Collection Service started")

    while not shutdown_flag.is_set():
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📥 Collecting price data...")

            config = load_config()
            conn = connect_to_database()

            if config and conn:
                collect_all_watchlist_data(
                    conn,
                    config,
                    timeframes=['8h', '1h', '15m'],
                    limit=200
                )
                conn.close()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Data collection complete")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Configuration or database error")

        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Data collection error: {e}")

        # Wait 5 minutes or until shutdown
        shutdown_flag.wait(timeout=300)


def signal_detection_service():
    """Background thread: Detect signals every 5 minutes"""
    print("🎯 Signal Detection Service started")

    try:
        run_signal_detection_loop(interval_seconds=300, min_score=1.2)
    except Exception as e:
        print(f"❌ Signal detection error: {e}")


def web_server_service():
    """Foreground: Run Flask web server"""
    print("🌐 Web Server starting...")

    try:
        app = create_app()
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ Web server error: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print("\n\n⏹️  Shutdown signal received...")
    print("Stopping all services...")
    shutdown_flag.set()

    # Give threads time to finish
    time.sleep(2)

    print("✅ All services stopped")
    sys.exit(0)


def print_banner():
    """Print startup banner"""
    print("="*80)
    print("🚀 WIND CATCHER & RIVER TURN TRADING SYSTEM")
    print("="*80)
    print("\nServices:")
    print("  1. 📥 Data Collection Service (every 5 minutes)")
    print("  2. 🎯 Signal Detection Service (every 5 minutes)")
    print("  3. 🌐 Web Dashboard (http://localhost:5000)")
    print("\nPress Ctrl+C to stop all services")
    print("="*80)
    print()


def check_configuration():
    """Check if system is properly configured"""
    print("🔍 Checking configuration...")

    # Check config file
    try:
        config = load_config()
        if not config:
            print("⚠️  Warning: Could not load config.yaml")
            return False

        print("✅ Configuration file loaded")

        # Check database
        conn = connect_to_database()
        if not conn:
            print("⚠️  Warning: Could not connect to database")
            return False

        # Check if watchlists exist
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_watchlists")
        count = cursor.fetchone()[0]

        if count == 0:
            print("⚠️  Warning: No symbols in user_watchlists")
            print("💡 Run multi_timeframe_collector.py to add test watchlists")

        conn.close()
        print("✅ Database connection OK")

        return True

    except Exception as e:
        print(f"❌ Configuration check failed: {e}")
        return False


def main():
    """Main service manager"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Print banner
    print_banner()

    # Check configuration
    if not check_configuration():
        print("\n⚠️  System may not be fully configured")
        print("Continue anyway? (y/n): ", end='')

        try:
            response = input().lower()
            if response != 'y':
                print("Exiting...")
                sys.exit(0)
        except:
            pass

    print("\n🚀 Starting all services...\n")

    # Start background services in daemon threads
    data_thread = threading.Thread(
        target=data_collection_service,
        daemon=True,
        name="DataCollector"
    )

    signal_thread = threading.Thread(
        target=signal_detection_service,
        daemon=True,
        name="SignalDetector"
    )

    # Start threads
    data_thread.start()
    print("✅ Data collection service started")

    signal_thread.start()
    print("✅ Signal detection service started")

    # Give background services time to initialize
    time.sleep(2)

    print("\n" + "="*80)
    print("🌐 Starting web server...")
    print("="*80)
    print()

    # Start web server in foreground
    web_server_service()


if __name__ == "__main__":
    main()
