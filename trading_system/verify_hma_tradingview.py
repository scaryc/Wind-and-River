#!/usr/bin/env python3
"""
Hull MA Verification Script - Compare with TradingView
This script tests HMA calculations against TradingView for all trading pairs
Timeframe: 1h (single timeframe to match TradingView testing)
"""

import sqlite3
import numpy as np
from datetime import datetime

# ANSI color codes for better readability
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'

def connect_to_database():
    """Connect to SQLite database"""
    return sqlite3.connect('data/trading_system.db')

def get_watchlist(conn):
    """Get all symbols from watchlist"""
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM watchlist ORDER BY symbol")
    return [row[0] for row in cursor.fetchall()]

def get_price_data(conn, symbol, timeframe='1h', limit=100):
    """Get price data for a symbol"""
    query = """
    SELECT DISTINCT timestamp, close
    FROM price_data
    WHERE symbol = ? AND timeframe = ?
    ORDER BY timestamp DESC
    LIMIT ?
    """

    cursor = conn.cursor()
    cursor.execute(query, (symbol, timeframe, limit))
    results = cursor.fetchall()

    if not results:
        return None

    # Sort ascending (oldest first) for indicator calculations
    # Results are currently newest first, so reverse them
    results.reverse()

    # Extract just the close prices
    prices = np.array([row[1] for row in results])
    return prices

def calculate_wma(data, period):
    """
    Calculate Weighted Moving Average
    WMA = (P1*1 + P2*2 + ... + Pn*n) / (1+2+...+n)
    where P1 is oldest, Pn is newest
    """
    if len(data) < period:
        return None

    # Take the most recent 'period' values
    recent_data = data[-period:]

    # Weights: 1, 2, 3, ..., period
    weights = np.arange(1, period + 1)

    # Calculate weighted average
    weighted_sum = np.sum(recent_data * weights)
    weight_sum = np.sum(weights)

    return weighted_sum / weight_sum

def calculate_wma_series(prices, period):
    """Calculate WMA for entire price series"""
    if len(prices) < period:
        return np.array([np.nan] * len(prices))

    weights = np.arange(1, period + 1)
    wma_values = []

    for i in range(len(prices)):
        if i < period - 1:
            wma_values.append(np.nan)
        else:
            window = prices[i-period+1:i+1]
            wma = np.sum(window * weights) / np.sum(weights)
            wma_values.append(wma)

    return np.array(wma_values)

def calculate_hull_ma(prices, period):
    """
    Calculate Hull Moving Average - Complete Implementation
    HMA = WMA(2*WMA(n/2) - WMA(n), sqrt(n))

    Step 1: Calculate WMA(n/2) - faster WMA
    Step 2: Calculate WMA(n) - slower WMA
    Step 3: Calculate 2*WMA(n/2) - WMA(n) - the "raw Hull"
    Step 4: Calculate WMA of the result with sqrt(n) period
    """
    if len(prices) < period:
        return None

    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))

    # Step 1: WMA(n/2) - WMA of half period
    wma_half_series = calculate_wma_series(prices, half_period)

    # Step 2: WMA(n) - WMA of full period
    wma_full_series = calculate_wma_series(prices, period)

    # Step 3: 2*WMA(n/2) - WMA(n)
    raw_hull = 2 * wma_half_series - wma_full_series

    # Step 4: WMA of raw hull with sqrt(n) period
    hull_ma_series = calculate_wma_series(raw_hull, sqrt_period)

    # Return the latest value
    return hull_ma_series[-1] if not np.isnan(hull_ma_series[-1]) else None

def get_latest_candle_info(conn, symbol, timeframe='1h'):
    """Get the latest candle timestamp and price"""
    query = """
    SELECT timestamp, close, open, high, low
    FROM price_data
    WHERE symbol = ? AND timeframe = ?
    ORDER BY timestamp DESC
    LIMIT 1
    """

    cursor = conn.cursor()
    cursor.execute(query, (symbol, timeframe))
    result = cursor.fetchone()

    if result:
        timestamp, close, open_price, high, low = result
        dt = datetime.fromtimestamp(timestamp)
        return {
            'timestamp': timestamp,
            'datetime': dt,
            'close': close,
            'open': open_price,
            'high': high,
            'low': low
        }
    return None

def verify_symbol_hma(conn, symbol):
    """Verify HMA calculation for a specific symbol"""
    print(f"\n{CYAN}{BOLD}{'='*70}{RESET}")
    print(f"{CYAN}{BOLD}Testing: {symbol}{RESET}")
    print(f"{CYAN}{BOLD}{'='*70}{RESET}")

    # Get price data
    prices = get_price_data(conn, symbol, timeframe='1h', limit=100)

    if prices is None or len(prices) < 50:
        print(f"{RED}❌ Not enough data for {symbol}{RESET}")
        return None

    # Get latest candle info
    candle_info = get_latest_candle_info(conn, symbol)

    print(f"\n{BLUE}📊 Latest Candle Info:{RESET}")
    print(f"   Time: {candle_info['datetime'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"   Open:  ${candle_info['open']:.4f}")
    print(f"   High:  ${candle_info['high']:.4f}")
    print(f"   Low:   ${candle_info['low']:.4f}")
    print(f"   Close: ${candle_info['close']:.4f}")

    print(f"\n{BLUE}💹 Price Data:{RESET}")
    print(f"   Data points available: {len(prices)}")
    print(f"   Latest 5 prices: {prices[-5:]}")

    # Calculate Hull MAs
    hull_21 = calculate_hull_ma(prices, 21)
    hull_34 = calculate_hull_ma(prices, 34)

    print(f"\n{GREEN}{BOLD}🎯 Calculated Hull MA Values:{RESET}")
    print(f"{GREEN}{'─'*70}{RESET}")

    if hull_21 is not None:
        print(f"{GREEN}   Hull MA 21: ${hull_21:.6f}{RESET}")

        # Calculate intermediate values for debugging
        half_period_21 = int(21 / 2)  # 10
        sqrt_period_21 = int(np.sqrt(21))  # 4
        wma_half_21 = calculate_wma(prices, half_period_21)
        wma_full_21 = calculate_wma(prices, 21)
        raw_hull_21 = 2 * wma_half_21 - wma_full_21

        print(f"{YELLOW}   Debug Hull 21:{RESET}")
        print(f"   - WMA(10):     ${wma_half_21:.6f}")
        print(f"   - WMA(21):     ${wma_full_21:.6f}")
        print(f"   - Raw Hull:    ${raw_hull_21:.6f} (2*WMA(10) - WMA(21))")
        print(f"   - Final Hull:  ${hull_21:.6f} (WMA(4) of raw hull)")
    else:
        print(f"{RED}   Hull MA 21: Not enough data{RESET}")

    print()

    if hull_34 is not None:
        print(f"{GREEN}   Hull MA 34: ${hull_34:.6f}{RESET}")

        # Calculate intermediate values for debugging
        half_period_34 = int(34 / 2)  # 17
        sqrt_period_34 = int(np.sqrt(34))  # 5
        wma_half_34 = calculate_wma(prices, half_period_34)
        wma_full_34 = calculate_wma(prices, 34)
        raw_hull_34 = 2 * wma_half_34 - wma_full_34

        print(f"{YELLOW}   Debug Hull 34:{RESET}")
        print(f"   - WMA(17):     ${wma_half_34:.6f}")
        print(f"   - WMA(34):     ${wma_full_34:.6f}")
        print(f"   - Raw Hull:    ${raw_hull_34:.6f} (2*WMA(17) - WMA(34))")
        print(f"   - Final Hull:  ${hull_34:.6f} (WMA(5) of raw hull)")
    else:
        print(f"{RED}   Hull MA 34: Not enough data{RESET}")

    print(f"\n{BOLD}📝 TradingView Verification Steps:{RESET}")
    print(f"   1. Open TradingView: {symbol} on 1h timeframe")
    print(f"   2. Add indicator: 'Hull Moving Average' with period 21")
    print(f"   3. Add indicator: 'Hull Moving Average' with period 34")
    print(f"   4. Check the latest (rightmost) values on the chart")
    print(f"   5. Compare with values above")

    return {
        'symbol': symbol,
        'hull_21': hull_21,
        'hull_34': hull_34,
        'price': candle_info['close'],
        'candle_time': candle_info['datetime']
    }

def main():
    """Main verification function"""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}  Hull MA Verification - TradingView Comparison{RESET}")
    print(f"{BOLD}{BLUE}  Timeframe: 1h (Single Timeframe Mode){RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

    # Connect to database
    conn = connect_to_database()

    # Get watchlist
    watchlist = get_watchlist(conn)
    print(f"{BOLD}📋 Trading Pairs to Test: {len(watchlist)}{RESET}")
    print(f"   {', '.join(watchlist)}\n")

    # Verify each symbol
    results = []
    for symbol in watchlist:
        result = verify_symbol_hma(conn, symbol)
        if result:
            results.append(result)

    # Summary
    print(f"\n{BOLD}{GREEN}{'='*70}{RESET}")
    print(f"{BOLD}{GREEN}📊 SUMMARY - All Trading Pairs{RESET}")
    print(f"{BOLD}{GREEN}{'='*70}{RESET}\n")

    if results:
        print(f"{'Symbol':<12} {'Price':<12} {'Hull 21':<12} {'Hull 34':<12} {'Candle Time'}")
        print(f"{'-'*70}")
        for r in results:
            hull_21_str = f"${r['hull_21']:.4f}" if r['hull_21'] else "N/A"
            hull_34_str = f"${r['hull_34']:.4f}" if r['hull_34'] else "N/A"
            time_str = r['candle_time'].strftime('%Y-%m-%d %H:%M')
            print(f"{r['symbol']:<12} ${r['price']:<11.4f} {hull_21_str:<12} {hull_34_str:<12} {time_str}")
    else:
        print(f"{RED}No results to display{RESET}")

    conn.close()

    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}✅ Verification Complete!{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

    print(f"{YELLOW}💡 Next Steps:{RESET}")
    print(f"   1. Open TradingView for each symbol")
    print(f"   2. Set timeframe to 1h")
    print(f"   3. Add Hull MA indicators (periods 21 and 34)")
    print(f"   4. Compare values with the table above")
    print(f"   5. If values match, HMA calculation is correct! ✅")
    print()

if __name__ == "__main__":
    main()
