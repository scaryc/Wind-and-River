# Hull MA Debug Script - ENA/USDT Focus
# Let's find what's wrong with our Hull MA calculation

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

def get_recent_data(symbol='ENA/USDT', periods=100):
    """Get recent price data with timestamps"""
    conn = sqlite3.connect('data/trading_system.db')
    
    query = """
    SELECT timestamp, close
    FROM price_data 
    WHERE symbol = ? AND timeframe = '1h'
    ORDER BY timestamp DESC 
    LIMIT ?
    """
    
    df = pd.read_sql_query(query, conn, params=(symbol, periods))
    conn.close()
    
    if df.empty:
        return None, None
    
    df = df.sort_values('timestamp')
    return df['close'].values, df['timestamp'].values

def wma_basic(data, period):
    """Basic WMA calculation"""
    if len(data) < period:
        return None
    
    recent_data = data[-period:]
    weights = np.arange(1, period + 1)
    return np.sum(recent_data * weights) / np.sum(weights)

def wma_tradingview_style(data, period):
    """TradingView-style WMA (might use different weighting)"""
    if len(data) < period:
        return None
    
    recent_data = data[-period:]
    # Try reverse weighting (most recent gets weight 1, oldest gets highest weight)
    weights = np.arange(period, 0, -1)
    return np.sum(recent_data * weights) / np.sum(weights)

def hull_ma_original(data, period):
    """Original Hull MA: WMA(2*WMA(n/2) - WMA(n), sqrt(n))"""
    if len(data) < period:
        return None
    
    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))
    
    wma_half = wma_basic(data, half_period)
    wma_full = wma_basic(data, period)
    
    if wma_half is None or wma_full is None:
        return None
    
    # Step 1: Calculate 2*WMA(n/2) - WMA(n)
    raw_hull = 2 * wma_half - wma_full
    
    # Step 2: This should be WMA of the raw_hull series with sqrt(n) period
    # But we only have one value, so we return it (this might be the issue!)
    return raw_hull

def hull_ma_with_series(data, period):
    """Hull MA calculated with proper series for final WMA"""
    if len(data) < period + int(np.sqrt(period)):
        return None
    
    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))
    
    # Calculate raw hull values for multiple points
    hull_series = []
    for i in range(period - 1, len(data)):
        subset = data[:i+1]
        if len(subset) >= period:
            wma_half = wma_basic(subset, half_period)
            wma_full = wma_basic(subset, period)
            if wma_half is not None and wma_full is not None:
                hull_raw = 2 * wma_half - wma_full
                hull_series.append(hull_raw)
    
    if len(hull_series) >= sqrt_period:
        # Final WMA of hull series
        return wma_basic(np.array(hull_series), sqrt_period)
    
    return None

def hull_ma_step_by_step(data, period):
    """Hull MA with detailed step-by-step breakdown"""
    if len(data) < period:
        return None, {}
    
    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))
    
    # Show the data we're working with
    recent_data = data[-period:]
    
    # Calculate components
    wma_half = wma_basic(data, half_period)
    wma_full = wma_basic(data, period)
    
    if wma_half is None or wma_full is None:
        return None, {}
    
    raw_hull = 2 * wma_half - wma_full
    
    details = {
        'period': period,
        'half_period': half_period,
        'sqrt_period': sqrt_period,
        'data_points_used': len(recent_data),
        'last_5_prices': data[-5:],
        'wma_half_period': half_period,
        'wma_half_value': wma_half,
        'wma_full_period': period,
        'wma_full_value': wma_full,
        'formula': f"2 * {wma_half:.6f} - {wma_full:.6f}",
        'raw_hull_result': raw_hull
    }
    
    return raw_hull, details

def show_price_data(data, timestamps, symbol):
    """Show recent price data with timestamps"""
    print(f"\n=== {symbol} RECENT PRICE DATA ===")
    print("DateTime (UTC)          | Price")
    print("-" * 40)
    
    # Show last 10 prices
    for i in range(max(0, len(data)-10), len(data)):
        dt = datetime.fromtimestamp(timestamps[i]).strftime('%Y-%m-%d %H:%M')
        print(f"{dt} | {data[i]:8.6f}")

def main():
    print("=== ENA/USDT HULL MA DEBUG ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Get ENA data
    data, timestamps = get_recent_data('ENA/USDT', 100)
    
    if data is None:
        print("❌ No ENA/USDT data found!")
        print("Run: python data_collector.py first")
        return
    
    print(f"✅ Found {len(data)} price points for ENA/USDT")
    
    # Show recent price data
    show_price_data(data, timestamps, 'ENA/USDT')
    
    print(f"\n=== HULL MA 21 ANALYSIS ===")
    
    # Test Hull 21 with step-by-step breakdown
    hull_21, details_21 = hull_ma_step_by_step(data, 21)
    
    if hull_21 is not None:
        print(f"Hull MA 21 Result: {hull_21:.6f}")
        print(f"Formula used: {details_21['formula']}")
        print(f"WMA({details_21['wma_half_period']}) = {details_21['wma_half_value']:.6f}")
        print(f"WMA({details_21['wma_full_period']}) = {details_21['wma_full_value']:.6f}")
        print(f"Last 5 prices used: {details_21['last_5_prices']}")
    
    print(f"\n=== HULL MA 34 ANALYSIS ===")
    
    # Test Hull 34 with step-by-step breakdown
    hull_34, details_34 = hull_ma_step_by_step(data, 34)
    
    if hull_34 is not None:
        print(f"Hull MA 34 Result: {hull_34:.6f}")
        print(f"Formula used: {details_34['formula']}")
        print(f"WMA({details_34['wma_half_period']}) = {details_34['wma_half_value']:.6f}")
        print(f"WMA({details_34['wma_full_period']}) = {details_34['wma_full_value']:.6f}")
        print(f"Last 5 prices used: {details_34['last_5_prices']}")
    
    # Test alternative Hull MA calculation
    print(f"\n=== ALTERNATIVE HULL MA CALCULATION ===")
    hull_21_alt = hull_ma_with_series(data, 21)
    hull_34_alt = hull_ma_with_series(data, 34)
    
    if hull_21_alt is not None:
        print(f"Hull MA 21 (with series): {hull_21_alt:.6f}")
    
    if hull_34_alt is not None:
        print(f"Hull MA 34 (with series): {hull_34_alt:.6f}")
    
    print(f"\n=== VERIFICATION INSTRUCTIONS ===")
    print("1. Open TradingView: ENA/USDT on 1-hour timeframe")
    print("2. Add Hull Moving Average indicator")
    print("3. Set period to 21, then add another with period 34")
    print("4. Check the EXACT values on the latest candle")
    print("5. Compare with our calculations above")
    print(f"\nOur calculations:")
    if hull_21 is not None:
        print(f"   Hull MA 21: {hull_21:.6f}")
    if hull_34 is not None:
        print(f"   Hull MA 34: {hull_34:.6f}")
    
    print(f"\nAlternative calculations:")
    if hull_21_alt is not None:
        print(f"   Hull MA 21 (alt): {hull_21_alt:.6f}")
    if hull_34_alt is not None:
        print(f"   Hull MA 34 (alt): {hull_34_alt:.6f}")

if __name__ == "__main__":
    main()