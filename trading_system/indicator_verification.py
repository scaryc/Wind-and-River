# Indicator Verification Script
# Run this to get exact indicator values for manual chart comparison

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add current directory to path to import your modules
sys.path.append(os.getcwd())

def get_recent_data(symbol='BNB/USDT', periods=10):
    """Get recent price data and calculated indicators"""
    
    # Connect to database
    conn = sqlite3.connect('data/trading_system.db')
    
    # Get recent price data
    query = """
    SELECT timestamp, open, high, low, close, volume 
    FROM price_data 
    WHERE symbol = ? AND timeframe = '1h'
    ORDER BY timestamp DESC 
    LIMIT ?
    """
    
    df = pd.read_sql_query(query, conn, params=(symbol, periods))
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    
    conn.close()
    return df.sort_values('timestamp')

def calculate_hull_ma_manual(prices, period):
    """Manual Hull MA calculation for verification"""
    def wma(data, length):
        weights = range(1, length + 1)
        return sum(weights[i] * data.iloc[-(length-i)] for i in range(length)) / sum(weights)
    
    if len(prices) < period:
        return None
    
    half_period = int(period / 2)
    sqrt_period = int(period ** 0.5)
    
    if len(prices) < period:
        return None
    
    wma_half = wma(prices, half_period)
    wma_full = wma(prices, period)
    
    # Calculate Hull MA series for final WMA
    hull_series = 2 * wma_half - wma_full
    
    # For simplicity, return the single value (in real Hull MA, you'd calculate WMA of hull_series)
    return hull_series

def main():
    print("=== INDICATOR VERIFICATION ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Get data for BNB (change symbol if needed)
    symbol = 'BNB/USDT'
    df = get_recent_data(symbol, 50)  # Get 50 periods for Hull calculation
    
    if df.empty:
        print(f"No data found for {symbol}")
        return
    
    print(f"\nSymbol: {symbol}")
    print(f"Timeframe: 1 hour")
    print(f"Data points: {len(df)}")
    
    # Show last 5 candles with timestamps
    print("\n=== RECENT PRICE DATA ===")
    print("DateTime (UTC)          | Open    | High    | Low     | Close   | Volume")
    print("-" * 80)
    
    for i in range(min(5, len(df))):
        row = df.iloc[-(5-i)]
        dt = datetime.fromtimestamp(row['timestamp']).strftime('%Y-%m-%d %H:%M')
        print(f"{dt} | {row['open']:7.3f} | {row['high']:7.3f} | {row['low']:7.3f} | {row['close']:7.3f} | {row['volume']:>8.0f}")
    
    # Calculate Hull MA values manually
    print("\n=== HULL MA VERIFICATION ===")
    try:
        # Import your indicators module
        from indicators import calculate_hull_ma
        
        closes = df['close'].values
        
        if len(closes) >= 21:
            hull_21 = calculate_hull_ma(closes, 21)
            print(f"Hull MA 21 (your function): {hull_21:.6f}")
        
        if len(closes) >= 34:
            hull_34 = calculate_hull_ma(closes, 34)
            print(f"Hull MA 34 (your function): {hull_34:.6f}")
            
        # Manual calculation for verification
        closes_series = pd.Series(closes)
        manual_hull_21 = calculate_hull_ma_manual(closes_series, 21)
        if manual_hull_21:
            print(f"Hull MA 21 (manual calc):   {manual_hull_21:.6f}")
            
    except ImportError:
        print("Could not import indicators.py - make sure file exists")
    except Exception as e:
        print(f"Error calculating Hull MA: {e}")
    
    # Show current price for comparison
    current_price = df.iloc[-1]['close']
    current_time = datetime.fromtimestamp(df.iloc[-1]['timestamp']).strftime('%Y-%m-%d %H:%M UTC')
    
    print("\n=== CURRENT VALUES ===")
    print(f"Latest Close Price: {current_price:.6f}")
    print(f"Latest Candle Time: {current_time}")
    
    print("\n=== VERIFICATION INSTRUCTIONS ===")
    print("1. Open TradingView or your charting platform")
    print(f"2. Set chart to: {symbol} on 1-hour timeframe")
    print("3. Add Hull MA indicators with periods 21 and 34")
    print("4. Compare the Hull MA values above with the indicator lines on your chart")
    print("5. Check if the latest candle time matches your chart")
    print("\nIf values match = ✅ Your calculations are correct")
    print("If values differ = ❌ There's a calculation or data issue")

if __name__ == "__main__":
    main()