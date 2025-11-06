"""
Data Collector for Wind Catcher & River Turn Trading System
This script fetches price data from Gate.io and saves it to the database
"""

import ccxt
import yaml
import sqlite3
import time
from datetime import datetime, timezone

def load_config():
    """Load configuration from config.yaml"""
    try:
        with open('config/config.yaml', 'r') as file:
            config = yaml.safe_load(file)
            return config
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

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
        print(f"❌ Failed to connect to exchange: {e}")
        return None

def connect_to_database():
    """Connect to SQLite database"""
    try:
        conn = sqlite3.connect('data/trading_system.db')
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return None

def get_watchlist(conn):
    """Get active coins from watchlist"""
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
    symbols = [row[0] for row in cursor.fetchall()]
    return symbols

def fetch_and_store_ohlcv(exchange, conn, symbol, timeframe='1h', limit=24):
    """Fetch OHLCV data and store in database"""
    try:
        # Fetch data from exchange
        ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        if not ohlcv_data:
            print(f"⚠️ No data received for {symbol}")
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
                print(f"⚠️ Error storing candle for {symbol}: {e}")
        
        conn.commit()
        return stored_count
        
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")
        return 0

def show_latest_prices(conn):
    """Show the latest prices we've stored"""
    cursor = conn.cursor()
    
    print("\n📊 Latest Stored Prices:")
    print("-" * 60)
    
    cursor.execute('''
        SELECT symbol, close, timestamp, timeframe
        FROM price_data 
        WHERE (symbol, timestamp) IN (
            SELECT symbol, MAX(timestamp) 
            FROM price_data 
            GROUP BY symbol
        )
        ORDER BY symbol
    ''')
    
    results = cursor.fetchall()
    
    for symbol, price, timestamp, timeframe in results:
        # Convert timestamp to readable date
        dt = datetime.fromtimestamp(timestamp)
        date_str = dt.strftime('%Y-%m-%d %H:%M')
        
        print(f"{symbol:12s} ${price:>10.2f} ({timeframe}) at {date_str}")

def show_database_stats(conn):
    """Show database statistics"""
    cursor = conn.cursor()
    
    print("\n📈 Database Statistics:")
    print("-" * 40)
    
    # Total records
    cursor.execute("SELECT COUNT(*) FROM price_data")
    total_records = cursor.fetchone()[0]
    print(f"Total price records: {total_records}")
    
    # Records per symbol
    cursor.execute('''
        SELECT symbol, COUNT(*) as count 
        FROM price_data 
        GROUP BY symbol 
        ORDER BY symbol
    ''')
    
    symbol_counts = cursor.fetchall()
    for symbol, count in symbol_counts:
        print(f"  {symbol}: {count} candles")
    
    # Date range
    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM price_data")
    min_ts, max_ts = cursor.fetchone()
    
    if min_ts and max_ts:
        min_date = datetime.fromtimestamp(min_ts).strftime('%Y-%m-%d %H:%M')
        max_date = datetime.fromtimestamp(max_ts).strftime('%Y-%m-%d %H:%M')
        print(f"Data range: {min_date} to {max_date}")

def main():
    """Main data collection function"""
    print("🚀 Wind Catcher & River Turn - Data Collector")
    print("="*50)
    
    # Load configuration
    config = load_config()
    if not config:
        return
    
    # Connect to exchange
    print("Connecting to Gate.io...")
    exchange = connect_to_exchange(config)
    if not exchange:
        return
    print("✅ Connected to Gate.io")
    
    # Connect to database
    print("Connecting to database...")
    conn = connect_to_database()
    if not conn:
        return
    print("✅ Connected to database")
    
    # Get watchlist
    watchlist = get_watchlist(conn)
    print(f"📋 Found {len(watchlist)} coins in watchlist: {', '.join(watchlist)}")
    
    # Collect data for each symbol
    print("\n📥 Collecting price data...")
    total_stored = 0
    
    for symbol in watchlist:
        print(f"Fetching {symbol}...", end=' ')
        stored = fetch_and_store_ohlcv(exchange, conn, symbol, timeframe='1h', limit=24)
        total_stored += stored
        print(f"✅ Stored {stored} candles")
        time.sleep(1)  # Be nice to the API
    
    print(f"\n✅ Collection complete! Stored {total_stored} total candles")
    
    # Show results
    show_latest_prices(conn)
    show_database_stats(conn)
    
    # Close connection
    conn.close()
    print("\n🎯 Data collection finished!")

if __name__ == "__main__":
    main()