# Hull MA Debug Script - BTC/USDT Focus

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

def get_recent_data(symbol='BTC/USDT', periods=100):
    """Get recent price data"""
    conn = sqlite3.connect('data/trading_system.db')
    
    query = """
    SELECT DISTINCT timestamp, close
    FROM price_data 
    WHERE symbol = ? AND timeframe = '1h'
    ORDER BY timestamp DESC 
    LIMIT ?
    """
    
    df = pd.read_sql_query(query, conn, params=(symbol, periods))
    conn.close()
    return df.sort_values('timestamp')['close'].values

def wma_method1(data, period):
    """Your current WMA method"""
    if len(data) < period:
        return None
    
    weights = np.arange(1, period + 1)
    recent_data = data[-period:]
    return np.sum(recent_data * weights) / np.sum(weights)

def wma_method2(data, period):
    """Alternative WMA method - more standard approach"""
    if len(data) < period:
        return None
    
    recent_data = data[-period:]
    weights = np.arange(1, period + 1)
    
    # Ensure arrays are same length
    if len(recent_data) != len(weights):
        return None
    
    return np.dot(recent_data, weights) / np.sum(weights)

def wma_method3(data, period):
    """TradingView-style WMA calculation"""
    if len(data) < period:
        return None
    
    recent_data = data[-period:]
    weights = []
    
    # Build weights: 1, 2, 3, ..., period
    for i in range(1, period + 1):
        weights.append(i)
    
    weights = np.array(weights)
    numerator = np.sum(recent_data * weights)
    denominator = np.sum(weights)
    
    return numerator / denominator

def hull_ma_test(data, period, wma_func, method_name):
    """Test Hull MA with different WMA methods"""
    if len(data) < period:
        return None, f"{method_name}: Not enough data"
    
    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))
    
    # Calculate WMA components
    wma_half = wma_func(data, half_period)
    wma_full = wma_func(data, period)
    
    if wma_half is None or wma_full is None:
        return None, f"{method_name}: WMA calculation failed"
    
    # Hull MA formula
    hull_value = 2 * wma_half - wma_full
    
    # Show intermediate values for debugging
    return hull_value, {
        'method': method_name,
        'wma_half': wma_half,
        'wma_full': wma_full,
        'hull_raw': hull_value,
        'half_period': half_period,
        'full_period': period,
        'sqrt_period': sqrt_period
    }

def test_individual_wma():
    """Test WMA calculation with known values"""
    print("=== WMA CALCULATION TEST ===")
    
    # Test with simple known values
    test_data = np.array([1, 2, 3, 4, 5])
    period = 3
    
    print(f"Test data: {test_data}")
    print(f"Last {period} values: {test_data[-period:]}")
    print(f"Weights for period {period}: [1, 2, 3]")
    
    # Manual calculation: (3*1 + 4*2 + 5*3) / (1+2+3) = (3+8+15) / 6 = 26/6 = 4.333
    expected = (3*1 + 4*2 + 5*3) / (1+2+3)
    print(f"Expected WMA: {expected:.6f}")
    
    wma1 = wma_method1(test_data, period)
    wma2 = wma_method2(test_data, period)
    wma3 = wma_method3(test_data, period)
    
    print(f"Method 1: {wma1:.6f}")
    print(f"Method 2: {wma2:.6f}")
    print(f"Method 3: {wma3:.6f}")
    print()

def test_symbol(symbol):
    """Test Hull MA calculation for a specific symbol"""
    print(f"\n=== TESTING {symbol} ===")
    
    # Get data
    data = get_recent_data(symbol, 100)
    
    if len(data) < 50:
        print(f"Not enough data for {symbol}")
        return
    
    print(f"Testing with {len(data)} price points")
    print(f"Latest prices: {data[-5:]}")
    
    # Test Hull 21
    print(f"\n=== {symbol} HULL MA 21 ===")
    for wma_func, method_name in [(wma_method1, "Current"), (wma_method2, "Alternative"), (wma_method3, "TradingView")]:
        hull_value, details = hull_ma_test(data, 21, wma_func, method_name)
        if hull_value is not None:
            print(f"{method_name:12s}: {hull_value:.6f}")
        print()
    
    # Test Hull 34
    print(f"=== {symbol} HULL MA 34 ===")
    for wma_func, method_name in [(wma_method1, "Current"), (wma_method2, "Alternative"), (wma_method3, "TradingView")]:
        hull_value, details = hull_ma_test(data, 34, wma_func, method_name)
        if hull_value is not None:
            print(f"{method_name:12s}: {hull_value:.6f}")
            if isinstance(details, dict):
                print(f"             WMA(17):      {details['wma_half']:.6f}")
                print(f"             WMA(34):      {details['wma_full']:.6f}")
        print()

def main():
    print("=== HULL MA CALCULATION DEBUG ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Test WMA calculation first
    test_individual_wma()
    
    # Test only ENA/USDT
    test_symbol('ENA/USDT')
    
    print("\n=== INSTRUCTIONS ===")
    print("1. Open TradingView: ENA/USDT on 1-hour timeframe")
    print("2. Add Hull MA indicators with periods 21 and 34")  
    print("3. Compare the Hull values above with TradingView")
    print("4. Tell me the exact Hull 21 and Hull 34 values from TradingView")

if __name__ == "__main__":
    main()