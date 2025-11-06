"""
Historical Data Collector - Get more price history for indicators
This collects more historical data so Hull MA indicators can work properly
"""

import ccxt
import yaml
import sqlite3
import time
from datetime import datetime

def load_config():
    """Load configuration"""
    with open('config/config.yaml', 'r') as file:
        return yaml.safe_load(file)

def connect_to_exchange(config):
    """Connect to Gate.io"""
    exchange = ccxt.gateio({
        'apiKey': config['exchange']['api_key'],
        'secret': config['exchange']['api_secret'],
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    exchange.load_markets()
    return exchange

def connect_to_database():
    """Connect to database"""
    return sqlite3.connect('data/trading_system.db')

def get_watchlist(conn):
    """Get watchlist symbols"""
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
    return [row[0] for row in cursor.fetchall()]

def collect_historical_data(exchange, conn, symbol, timeframe='1h', days_back=7):
    """Collect several days of historical data"""
    
    # Calculate how many candles we need (24 hours * days)
    if timeframe == '1h':
        limit = 24 * days_back
    elif timeframe == '4h':
        limit = 6 * days_back
    elif timeframe == '1d':
        limit = days_back
    else:
        limit = 100  # Default
    
    print(f"Collecting {limit} candles of {timeframe} data for {symbol}...")
    
    try:
        # Fetch historical data
        ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        if not ohlcv_data:
            print(f"❌ No data received for {symbol}")
            return 0
        
        cursor = conn.cursor()
        stored_count = 0
        current_time = int(datetime.now().timestamp())
        
        for candle in ohlcv_data:
            timestamp = candle[0] // 1000  # Convert to seconds
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
                print(f"⚠️ Error storing data: {e}")
        
        conn.commit()
        print(f"✅ Stored {stored_count} candles for {symbol} ({timeframe})")
        return stored_count
        
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
        return 0

def check_data_count(conn):
    """Check how much data we have"""
    cursor = conn.cursor()
    
    print("\n📊 Data Summary:")
    print("-" * 40)
    
    cursor.execute('''
        SELECT symbol, timeframe, COUNT(*) as count
        FROM price_data 
        GROUP BY symbol, timeframe
        ORDER BY symbol, timeframe
    ''')
    
    results = cursor.fetchall()
    for symbol, timeframe, count in results:
        print(f"  {symbol} ({timeframe}): {count} candles")
    
    # Total count
    cursor.execute("SELECT COUNT(*) FROM price_data")
    total = cursor.fetchone()[0]
    print(f"\nTotal records: {total}")

def main():
    """Main function to collect historical data"""
    print("🚀 Historical Data Collector")
    print("="*50)
    
    # Load config and connect
    config = load_config()
    exchange = connect_to_exchange(config)
    conn = connect_to_database()
    
    # Get watchlist
    watchlist = get_watchlist(conn)
    print(f"📋 Collecting data for: {', '.join(watchlist)}")
    
    # Collect data for multiple timeframes
    timeframes_to_collect = ['1h', '4h']  # Start with these two
    days_back = 10  # Get 10 days of history
    
    total_collected = 0
    
    for timeframe in timeframes_to_collect:
        print(f"\n📥 Collecting {timeframe} data ({days_back} days)...")
        
        for symbol in watchlist:
            collected = collect_historical_data(
                exchange, conn, symbol, timeframe, days_back
            )
            total_collected += collected
            time.sleep(1)  # Be nice to API
    
    print(f"\n✅ Collection complete! Total candles stored: {total_collected}")
    
    # Show data summary
    check_data_count(conn)
    
    conn.close()
    print("\n🎯 Ready for indicator analysis!")

if __name__ == "__main__":
    main()