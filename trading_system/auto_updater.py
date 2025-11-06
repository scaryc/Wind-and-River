"""
Auto-Updater for Wind Catcher & River Turn Trading System
Automatically updates data and checks for new signals every hour
"""

import ccxt
import yaml
import sqlite3
import time
import schedule
from datetime import datetime, timedelta
import os

def load_config():
    """Load configuration"""
    with open('config/config.yaml', 'r') as file:
        return yaml.safe_load(file)

def connect_to_exchange(config):
    """Connect to Gate.io exchange"""
    try:
        exchange = ccxt.gateio({
            'apiKey': config['exchange']['api_key'],
            'secret': config['exchange']['api_secret'],
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        exchange.load_markets()
        return exchange
    except Exception as e:
        print(f"❌ Exchange connection failed: {e}")
        return None

def connect_to_database():
    """Connect to database"""
    return sqlite3.connect('data/trading_system.db')

def get_watchlist(conn):
    """Get active symbols from watchlist"""
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
    return [row[0] for row in cursor.fetchall()]

def update_price_data(exchange, conn, symbol, timeframe='1h', limit=5):
    """Update latest price data for a symbol"""
    try:
        # Fetch recent data
        ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        if not ohlcv_data:
            return 0
        
        cursor = conn.cursor()
        stored_count = 0
        current_time = int(datetime.now().timestamp())
        
        for candle in ohlcv_data:
            timestamp = candle[0] // 1000
            open_price = candle[1]
            high_price = candle[2]
            low_price = candle[3]
            close_price = candle[4]
            volume = candle[5]
            
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO price_data 
                    (symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (symbol, timeframe, timestamp, open_price, high_price, 
                      low_price, close_price, volume, current_time))
                
                stored_count += 1
                
            except Exception as e:
                print(f"⚠️ Error storing {symbol}: {e}")
        
        conn.commit()
        return stored_count
        
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
        return 0

def log_alert(message, level='INFO'):
    """Log alerts to file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Ensure logs directory exists
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    log_entry = f"[{timestamp}] {level}: {message}\n"
    
    # Write to alerts log with UTF-8 encoding
    with open('logs/alerts.log', 'a', encoding='utf-8') as f:
        f.write(log_entry)
    
    print(f"{timestamp} - {message}")

def check_for_new_signals(conn):
    """Check for new trading signals and log them"""
    # Import functions from trading_dashboard
    import sys
    sys.path.append('.')
    
    # This is a simplified version - in a real system you'd import the full analysis
    cursor = conn.cursor()
    
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
        log_alert(f"✅ Data updated for {len(set([row[0] for row in recent_data]))} symbols")
        
        # Here you could add more sophisticated signal detection
        # For now, we'll just log the data update
        latest_prices = {}
        for symbol, price, timestamp in recent_data:
            if symbol not in latest_prices or timestamp > latest_prices[symbol]['timestamp']:
                latest_prices[symbol] = {'price': price, 'timestamp': timestamp}
        
        for symbol, data in latest_prices.items():
            time_str = datetime.fromtimestamp(data['timestamp']).strftime('%H:%M')
            log_alert(f"📊 {symbol}: ${data['price']:.4f} at {time_str}")
    
    return len(recent_data)

def daily_data_collection():
    """Comprehensive daily data collection"""
    log_alert("🌅 Starting daily data collection", "INFO")
    
    config = load_config()
    exchange = connect_to_exchange(config)
    conn = connect_to_database()
    
    if not exchange:
        log_alert("❌ Could not connect to exchange", "ERROR")
        return
    
    watchlist = get_watchlist(conn)
    total_collected = 0
    
    for symbol in watchlist:
        collected = update_price_data(exchange, conn, symbol, timeframe='1h', limit=25)  # Last 25 hours
        total_collected += collected
        time.sleep(1)  # Be nice to API
    
    log_alert(f"✅ Daily collection complete: {total_collected} candles updated", "SUCCESS")
    
    # Check for signals
    signal_count = check_for_new_signals(conn)
    
    conn.close()
    return total_collected

def hourly_update():
    """Quick hourly update"""
    log_alert("🔄 Hourly update starting", "INFO")
    
    config = load_config()
    exchange = connect_to_exchange(config)
    conn = connect_to_database()
    
    if not exchange:
        log_alert("❌ Hourly update failed - no exchange connection", "ERROR")
        return
    
    watchlist = get_watchlist(conn)
    total_collected = 0
    
    for symbol in watchlist:
        collected = update_price_data(exchange, conn, symbol, timeframe='1h', limit=2)  # Last 2 hours
        total_collected += collected
        time.sleep(0.5)  # Be nice to API
    
    log_alert(f"🔄 Hourly update complete: {total_collected} candles", "INFO")
    
    # Check for new signals
    signal_count = check_for_new_signals(conn)
    
    conn.close()

def run_trading_dashboard():
    """Run the complete trading dashboard"""
    log_alert("📊 Running trading dashboard analysis", "INFO")
    
    try:
        # Run the dashboard (you would import and call the main function)
        import subprocess
        result = subprocess.run(['py', 'trading_dashboard.py'], 
                              capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            log_alert("📊 Dashboard analysis completed successfully", "SUCCESS")
        else:
            log_alert(f"⚠️ Dashboard analysis had issues: {result.stderr}", "WARNING")
            
    except Exception as e:
        log_alert(f"❌ Dashboard analysis failed: {e}", "ERROR")

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
    
    log_alert("⏰ Scheduled tasks configured:", "INFO")
    log_alert("   📅 06:00 - Daily data collection", "INFO")
    log_alert("   🔄 Every hour - Data updates", "INFO")  
    log_alert("   📊 08:00, 14:00, 20:00 - Dashboard analysis", "INFO")

def main():
    """Main auto-updater function"""
    print("🚀 Wind Catcher & River Turn - Auto-Updater Starting")
    print("="*60)
    
    log_alert("🚀 Auto-updater system starting", "INFO")
    
    # Schedule all tasks
    schedule_tasks()
    
    print("✅ Scheduler configured and running")
    print("📝 Check logs/alerts.log for activity")
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
        log_alert("⏹️ Auto-updater stopped by user", "INFO")
        print("\n⏹️ Auto-updater stopped")

if __name__ == "__main__":
    main()