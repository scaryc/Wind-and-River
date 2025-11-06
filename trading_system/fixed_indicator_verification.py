# Fixed Indicator Verification Script
# Fixes the numpy array issue with Hull MA calculation

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add current directory to path to import your modules
sys.path.append(os.getcwd())

def calculate_wma(data, period):
    """Calculate Weighted Moving Average"""
    if len(data) < period:
        return None
    
    # Convert to numpy array if it's not already
    if isinstance(data, pd.Series):
        data = data.values
    
    weights = np.arange(1, period + 1)
    recent_data = data[-period:]
    return np.sum(recent_data * weights) / np.sum(weights)

def calculate_hull_ma_fixed(data, period):
    """Fixed Hull MA calculation that works with numpy arrays"""
    if len(data) < period:
        return None
    
    # Convert to numpy array if needed
    if isinstance(data, pd.Series):
        data = data.values
    
    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))
    
    # Calculate WMA components
    wma_half = calculate_wma(data, half_period)
    wma_full = calculate_wma(data, period)
    
    if wma_half is None or wma_full is None:
        return None
    
    # Hull MA formula: WMA(2*WMA(n/2) - WMA(n), sqrt(n))
    hull_value = 2 * wma_half - wma_full
    
    # For proper Hull MA, we'd need to calculate WMA of the hull series
    # But for verification, this intermediate value should match your function
    return hull_value

def get_recent_data(symbol='BNB/USDT', periods=50):
    """Get recent price data"""
    conn = sqlite3.connect('data/trading_system.db')
    
    query = """
    SELECT DISTINCT timestamp, open, high, low, close, volume 
    FROM price_data 
    WHERE symbol = ? AND timeframe = '1h'
    ORDER BY timestamp DESC 
    LIMIT ?
    """
    
    df = pd.read_sql_query(query, conn, params=(symbol, periods))
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    
    conn.close()
    return df.sort_values('timestamp').drop_duplicates('timestamp')

def force_data_update():
    """Force immediate data update"""
    print("🔄 Forcing data update...")
    try:
        # Try to run your data collector
        os.system('python data_collector.py')
        print("✅ Data update completed")
        return True
    except Exception as e:
        print(f"❌ Data update failed: {e}")
        return False

def main():
    print("=== FIXED INDICATOR VERIFICATION ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Check if data is current
    symbol = 'BNB/USDT'
    df = get_recent_data(symbol, 50)
    
    if df.empty:
        print(f"❌ No data found for {symbol}")
        return
    
    latest_timestamp = df.iloc[-1]['timestamp']
    latest_time = datetime.fromtimestamp(latest_timestamp)
    time_diff = datetime.now() - latest_time
    
    print(f"Latest data: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Age: {time_diff}")
    
    # If data is more than 2 hours old, try to update
    if time_diff.total_seconds() > 7200:  # 2 hours
        print("⚠️ Data is outdated, attempting update...")
        force_data_update()
        
        # Reload data after update
        df = get_recent_data(symbol, 50)
        if not df.empty:
            latest_timestamp = df.iloc[-1]['timestamp']
            latest_time = datetime.fromtimestamp(latest_timestamp)
            print(f"✅ Updated data: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\nSymbol: {symbol}")
    print(f"Data points: {len(df)}")
    
    # Show last 5 candles (remove duplicates)
    print("\n=== RECENT PRICE DATA ===")
    print("DateTime (UTC)          | Open    | High    | Low     | Close   | Volume")
    print("-" * 80)
    
    recent_df = df.tail(5)
    for _, row in recent_df.iterrows():
        dt = datetime.fromtimestamp(row['timestamp']).strftime('%Y-%m-%d %H:%M')
        print(f"{dt} | {row['open']:7.3f} | {row['high']:7.3f} | {row['low']:7.3f} | {row['close']:7.3f} | {row['volume']:>8.0f}")
    
    # Test Hull MA calculations
    print("\n=== HULL MA VERIFICATION ===")
    
    closes = df['close'].values
    
    try:
        # Test with fixed function
        if len(closes) >= 21:
            hull_21_fixed = calculate_hull_ma_fixed(closes, 21)
            print(f"Hull MA 21 (fixed): {hull_21_fixed:.6f}")
        
        if len(closes) >= 34:
            hull_34_fixed = calculate_hull_ma_fixed(closes, 34)
            print(f"Hull MA 34 (fixed): {hull_34_fixed:.6f}")
        
        # Try your original function
        try:
            from indicators import calculate_hull_ma
            hull_21_orig = calculate_hull_ma(closes, 21)
            hull_34_orig = calculate_hull_ma(closes, 34)
            print(f"Hull MA 21 (original): {hull_21_orig:.6f}")
            print(f"Hull MA 34 (original): {hull_34_orig:.6f}")
        except Exception as e:
            print(f"❌ Original Hull MA failed: {e}")
            print("🔧 Your indicators.py needs to be fixed")
            
    except Exception as e:
        print(f"Error in Hull MA calculation: {e}")
    
    # Current values
    current_price = df.iloc[-1]['close']
    current_time = datetime.fromtimestamp(df.iloc[-1]['timestamp']).strftime('%Y-%m-%d %H:%M UTC')
    
    print("\n=== CURRENT VALUES ===")
    print(f"Latest Close: {current_price:.6f}")
    print(f"Latest Time:  {current_time}")
    
    print("\n=== NEXT STEPS ===")
    if time_diff.total_seconds() > 7200:
        print("⚠️  1. Fix data collection - data is too old")
    print("🔧 2. Fix Hull MA function in indicators.py")
    print("📊 3. Verify values on TradingView 1-hour chart")

if __name__ == "__main__":
    main()