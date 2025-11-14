"""
Auto-Updater for Wind Catcher & River Turn Trading System
Automatically updates data and checks for new signals every hour
"""

import time
import schedule
import subprocess
from datetime import datetime, timedelta
from utils import (
    load_config, connect_to_database, validate_ohlcv_data,
    normalize_timestamp, get_current_timestamp, log_message,
    get_python_executable, TRADING_SYSTEM_DIR
)
from hyperliquid_connector import connect_to_hyperliquid

def connect_to_exchange(config):
    """Connect to Hyperliquid DEX with proper error handling"""
    try:
        exchange_name = config['exchange']['name'].lower()

        if exchange_name == 'hyperliquid':
            use_testnet = config['exchange'].get('use_testnet', False)
            connector = connect_to_hyperliquid(use_testnet=use_testnet)
            return connector
        else:
            log_message(f"Unsupported exchange: {exchange_name}", "ERROR")
            return None

    except KeyError as e:
        log_message(f"Missing configuration: {e}", "ERROR")
        return None
    except Exception as e:
        log_message(f"Exchange connection failed: {e}", "ERROR")
        return None

def get_watchlist(conn):
    """Get active symbols from watchlist"""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
        return [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()

def update_price_data(connector, conn, symbol, timeframe='1h', limit=5):
    """Update latest price data for a symbol with validation"""
    cursor = None
    try:
        # Fetch recent data
        ohlcv_data = connector.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

        if not ohlcv_data:
            return 0

        cursor = conn.cursor()
        stored_count = 0
        skipped_count = 0
        current_time = get_current_timestamp()

        for candle in ohlcv_data:
            try:
                # Validate candle data
                validate_ohlcv_data(candle)

                # Normalize timestamp
                timestamp = normalize_timestamp(candle[0])
                open_price = candle[1]
                high_price = candle[2]
                low_price = candle[3]
                close_price = candle[4]
                volume = candle[5]

                cursor.execute('''
                    INSERT OR REPLACE INTO price_data
                    (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (symbol, timeframe, timestamp, open_price, high_price,
                      low_price, close_price, volume, current_time))

                stored_count += 1

            except ValueError as e:
                skipped_count += 1
                log_message(f"Skipped invalid candle for {symbol}: {e}", "WARNING")
            except Exception as e:
                log_message(f"Error storing {symbol}: {e}", "ERROR")

        conn.commit()

        if skipped_count > 0:
            log_message(f"Skipped {skipped_count} invalid candles for {symbol}", "WARNING")

        return stored_count

    except Exception as e:
        log_message(f"Error fetching {symbol}: {e}", "ERROR")
        return 0
    finally:
        if cursor:
            cursor.close()

def check_for_new_signals(conn):
    """Check for new trading signals and log them"""
    cursor = conn.cursor()
    try:
        # Get recent signals (last hour)
        one_hour_ago = int((datetime.now() - timedelta(hours=1)).timestamp())

        # For now, just check if we have recent data
        cursor.execute('''
            SELECT symbol, close, timestamp FROM price_data
            WHERE timestamp >= ? AND timeframe = '1h'
            ORDER BY timestamp DESC
        ''', (one_hour_ago,))

        recent_data = cursor.fetchall()

        if recent_data:
            log_message(f"✅ Data updated for {len(set([row[0] for row in recent_data]))} symbols")

            # Log latest prices
            latest_prices = {}
            for symbol, price, timestamp in recent_data:
                if symbol not in latest_prices or timestamp > latest_prices[symbol]['timestamp']:
                    latest_prices[symbol] = {'price': price, 'timestamp': timestamp}

            for symbol, data in latest_prices.items():
                time_str = datetime.fromtimestamp(data['timestamp']).strftime('%H:%M')
                log_message(f"📊 {symbol}: ${data['price']:.4f} at {time_str}")

        return len(recent_data)
    finally:
        cursor.close()

def daily_data_collection():
    """Comprehensive daily data collection"""
    log_message("🌅 Starting daily data collection", "INFO")

    try:
        config = load_config()
        connector = connect_to_exchange(config)
        conn = connect_to_database()
    except Exception as e:
        log_message(f"❌ Setup failed: {e}", "ERROR")
        return

    if not connector:
        log_message("❌ Could not connect to exchange", "ERROR")
        return

    watchlist = get_watchlist(conn)
    total_collected = 0

    for symbol in watchlist:
        collected = update_price_data(connector, conn, symbol, timeframe='1h', limit=25)  # Last 25 hours
        total_collected += collected
        time.sleep(1)  # Be nice to API

    log_message(f"✅ Daily collection complete: {total_collected} candles updated", "SUCCESS")

    # Check for signals
    signal_count = check_for_new_signals(conn)

    conn.close()
    return total_collected

def hourly_update():
    """Quick hourly update"""
    log_message("🔄 Hourly update starting", "INFO")

    try:
        config = load_config()
        connector = connect_to_exchange(config)
        conn = connect_to_database()
    except Exception as e:
        log_message(f"❌ Hourly update setup failed: {e}", "ERROR")
        return

    if not connector:
        log_message("❌ Hourly update failed - no exchange connection", "ERROR")
        return

    watchlist = get_watchlist(conn)
    total_collected = 0

    for symbol in watchlist:
        collected = update_price_data(connector, conn, symbol, timeframe='1h', limit=2)  # Last 2 hours
        total_collected += collected
        time.sleep(0.5)  # Be nice to API

    log_message(f"🔄 Hourly update complete: {total_collected} candles", "INFO")

    # Check for new signals
    signal_count = check_for_new_signals(conn)

    conn.close()

def run_trading_dashboard():
    """Run the complete trading dashboard"""
    log_message("📊 Running trading dashboard analysis", "INFO")

    try:
        # Get correct Python executable
        python_exe = get_python_executable()
        dashboard_script = TRADING_SYSTEM_DIR / 'trading_dashboard.py'

        # Run the dashboard with proper paths and timeout
        result = subprocess.run(
            [python_exe, str(dashboard_script)],
            capture_output=True,
            text=True,
            cwd=str(TRADING_SYSTEM_DIR),
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            log_message("📊 Dashboard analysis completed successfully", "SUCCESS")
        else:
            log_message(f"⚠️ Dashboard analysis had issues: {result.stderr}", "WARNING")

    except subprocess.TimeoutExpired:
        log_message("❌ Dashboard analysis timed out after 5 minutes", "ERROR")
    except FileNotFoundError:
        log_message(f"❌ trading_dashboard.py not found at {dashboard_script}", "ERROR")
    except Exception as e:
        log_message(f"❌ Dashboard analysis failed: {e}", "ERROR")

def schedule_tasks():
    """Schedule all automated tasks"""

    # Daily comprehensive data collection at 6 AM
    schedule.every().day.at("06:00").do(daily_data_collection)

    # Hourly updates during market hours
    schedule.every().hour.at(":05").do(hourly_update)  # 5 minutes past each hour

    # Trading dashboard runs 3x per day
    schedule.every().day.at("08:00").do(run_trading_dashboard)  # Morning
    schedule.every().day.at("14:00").do(run_trading_dashboard)  # Afternoon
    schedule.every().day.at("20:00").do(run_trading_dashboard)  # Evening

    log_message("⏰ Scheduled tasks configured:", "INFO")
    log_message("   📅 06:00 - Daily data collection", "INFO")
    log_message("   🔄 Every hour - Data updates", "INFO")
    log_message("   📊 08:00, 14:00, 20:00 - Dashboard analysis", "INFO")

def main():
    """Main auto-updater function"""
    print("🚀 Wind Catcher & River Turn - Auto-Updater Starting")
    print("="*60)

    log_message("🚀 Auto-updater system starting", "INFO")

    # Schedule all tasks
    schedule_tasks()

    print("✅ Scheduler configured and running")
    print(f"📝 Check {TRADING_SYSTEM_DIR / 'logs' / 'alerts.log'} for activity")
    print("⏰ Next tasks:")

    # Show upcoming tasks
    upcoming = schedule.jobs[:3]  # Show next 3 jobs
    for job in upcoming:
        print(f"   {job}")

    print("\n🔄 System running... Press Ctrl+C to stop")
    print("-"*60)

    # Run the scheduler
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        log_message("⏹️ Auto-updater stopped by user", "INFO")
        print("\n⏹️ Auto-updater stopped")

if __name__ == "__main__":
    main()