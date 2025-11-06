"""
Enhanced Indicators for Wind Catcher & River Turn Trading System
Awesome Oscillator with Divergence Detection
"""

import pandas as pd
import numpy as np
import sqlite3
import yaml
from datetime import datetime
from scipy.signal import argrelextrema

def load_config():
    """Load configuration"""
    with open('config/config.yaml', 'r') as file:
        return yaml.safe_load(file)

def connect_to_database():
    """Connect to database"""
    return sqlite3.connect('data/trading_system.db')

def get_price_data(conn, symbol, timeframe='1h', limit=200):
    """Get price data for analysis - need more bars for divergence detection"""
    query = '''
        SELECT timestamp, open, high, low, close, volume
        FROM price_data 
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp DESC
        LIMIT ?
    '''
    
    df = pd.read_sql_query(query, conn, params=(symbol, timeframe, limit))
    
    if df.empty:
        return None
    
    df = df.sort_values('timestamp').reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    return df

def calculate_sma(prices, period):
    """Calculate Simple Moving Average"""
    return prices.rolling(window=period, min_periods=period).mean()

def calculate_awesome_oscillator(df, fast_period=5, slow_period=34):
    """
    Calculate Awesome Oscillator (AO) - Bill Williams
    AO = SMA(high+low)/2, 5) - SMA((high+low)/2, 34)
    """
    if len(df) < slow_period:
        return pd.Series([np.nan] * len(df))
    
    # Calculate median price (high+low)/2
    median_price = (df['high'] + df['low']) / 2
    
    # Calculate fast and slow SMAs
    fast_sma = calculate_sma(median_price, fast_period)
    slow_sma = calculate_sma(median_price, slow_period)
    
    # AO = Fast SMA - Slow SMA
    ao = fast_sma - slow_sma
    
    return ao

def find_pivots(data, order=5):
    """
    Find pivot highs and lows in price or oscillator data
    order: number of bars on each side to confirm pivot
    """
    if len(data) < order * 2 + 1:
        return [], []
    
    # Find local maxima (pivot highs)
    highs = argrelextrema(data.values, np.greater, order=order)[0]
    
    # Find local minima (pivot lows) 
    lows = argrelextrema(data.values, np.less, order=order)[0]
    
    return highs.tolist(), lows.tolist()

def detect_regular_divergence(price_data, oscillator_data, price_pivots, osc_pivots, divergence_type='bullish'):
    """
    Detect regular divergence between price and oscillator
    Regular Bullish: Price makes lower low, oscillator makes higher low
    Regular Bearish: Price makes higher high, oscillator makes lower high
    """
    divergences = []
    
    if len(price_pivots) < 2 or len(osc_pivots) < 2:
        return divergences
    
    # Look at the last few pivots
    recent_price_pivots = price_pivots[-3:] if len(price_pivots) >= 3 else price_pivots
    recent_osc_pivots = osc_pivots[-3:] if len(osc_pivots) >= 3 else osc_pivots
    
    for i in range(1, len(recent_price_pivots)):
        price_pivot1 = recent_price_pivots[i-1]
        price_pivot2 = recent_price_pivots[i]
        
        # Find corresponding oscillator pivots (within reasonable time window)
        osc_pivot1 = None
        osc_pivot2 = None
        
        # Find closest oscillator pivots to price pivots
        for osc_pivot in recent_osc_pivots:
            if abs(osc_pivot - price_pivot1) <= 5:  # Within 5 bars
                osc_pivot1 = osc_pivot
            if abs(osc_pivot - price_pivot2) <= 5:
                osc_pivot2 = osc_pivot
        
        if osc_pivot1 is None or osc_pivot2 is None:
            continue
        
        if divergence_type == 'bullish':
            # Bullish divergence: Price lower low, oscillator higher low
            price_lower = price_data.iloc[price_pivot2] < price_data.iloc[price_pivot1]
            osc_higher = oscillator_data.iloc[osc_pivot2] > oscillator_data.iloc[osc_pivot1]
            
            if price_lower and osc_higher:
                divergences.append({
                    'type': 'regular_bullish',
                    'price_pivot1': price_pivot1,
                    'price_pivot2': price_pivot2,
                    'osc_pivot1': osc_pivot1,
                    'osc_pivot2': osc_pivot2,
                    'strength': 0.8,
                    'description': 'Regular bullish divergence detected'
                })
        
        elif divergence_type == 'bearish':
            # Bearish divergence: Price higher high, oscillator lower high
            price_higher = price_data.iloc[price_pivot2] > price_data.iloc[price_pivot1]
            osc_lower = oscillator_data.iloc[osc_pivot2] < oscillator_data.iloc[osc_pivot1]
            
            if price_higher and osc_lower:
                divergences.append({
                    'type': 'regular_bearish',
                    'price_pivot1': price_pivot1,
                    'price_pivot2': price_pivot2,
                    'osc_pivot1': osc_pivot1,
                    'osc_pivot2': osc_pivot2,
                    'strength': 0.8,
                    'description': 'Regular bearish divergence detected'
                })
    
    return divergences

def analyze_ao_divergences(df):
    """Analyze Awesome Oscillator for divergences"""
    if len(df) < 100:
        return None
    
    # Calculate AO
    df['ao'] = calculate_awesome_oscillator(df)
    
    # Remove NaN values
    valid_data = df.dropna().copy()
    if len(valid_data) < 50:
        return None
    
    # Find pivots in price (using highs for bearish, lows for bullish)
    price_highs, price_lows = find_pivots(valid_data['high'], order=5)
    price_highs_low, price_lows_low = find_pivots(valid_data['low'], order=5)
    
    # Find pivots in AO
    ao_highs, ao_lows = find_pivots(valid_data['ao'], order=5)
    
    divergences = []
    
    # Detect bullish divergences (price lows vs AO lows)
    if len(price_lows_low) >= 2 and len(ao_lows) >= 2:
        bullish_divs = detect_regular_divergence(
            valid_data['low'], valid_data['ao'], 
            price_lows_low, ao_lows, 'bullish'
        )
        divergences.extend(bullish_divs)
    
    # Detect bearish divergences (price highs vs AO highs)
    if len(price_highs) >= 2 and len(ao_highs) >= 2:
        bearish_divs = detect_regular_divergence(
            valid_data['high'], valid_data['ao'],
            price_highs, ao_highs, 'bearish'
        )
        divergences.extend(bearish_divs)
    
    # Get current AO values
    latest = valid_data.iloc[-1]
    prev = valid_data.iloc[-2] if len(valid_data) > 1 else latest
    
    # AO momentum analysis
    ao_momentum = "bullish" if latest['ao'] > prev['ao'] else "bearish"
    ao_position = "above_zero" if latest['ao'] > 0 else "below_zero"
    
    return {
        'ao_current': latest['ao'],
        'ao_previous': prev['ao'],
        'ao_momentum': ao_momentum,
        'ao_position': ao_position,
        'divergences': divergences,
        'price_pivots_high': price_highs,
        'price_pivots_low': price_lows_low,
        'ao_pivots_high': ao_highs,
        'ao_pivots_low': ao_lows
    }

def analyze_symbol_with_ao(conn, symbol):
    """Complete analysis including AO divergences"""
    df = get_price_data(conn, symbol, timeframe='1h', limit=200)
    if df is None or len(df) < 100:
        return None
    
    # AO analysis
    ao_analysis = analyze_ao_divergences(df)
    if not ao_analysis:
        return None
    
    # Get latest price data
    latest = df.iloc[-1]
    
    result = {
        'symbol': symbol,
        'timestamp': latest['timestamp'],
        'datetime': latest['datetime'],
        'price': latest['close'],
        'ao_analysis': ao_analysis
    }
    
    return result

def main():
    """Main AO analysis function"""
    print("🚀 Wind Catcher & River Turn - Awesome Oscillator Analysis")
    print("="*70)
    print("📊 Analyzing AO patterns and divergences...")
    print("-"*70)
    
    # Connect to database
    conn = connect_to_database()
    
    # Get watchlist
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
    watchlist = [row[0] for row in cursor.fetchall()]
    
    all_results = []
    
    for symbol in watchlist:
        print(f"\n🔍 {symbol}:")
        
        result = analyze_symbol_with_ao(conn, symbol)
        if result:
            ao_analysis = result['ao_analysis']
            
            # Display current AO status
            print(f"  💰 Price: ${result['price']:.4f}")
            print(f"  📊 AO Current: {ao_analysis['ao_current']:.6f}")
            print(f"  📈 AO Momentum: {ao_analysis['ao_momentum'].upper()}")
            print(f"  📍 AO Position: {ao_analysis['ao_position'].replace('_', ' ').upper()}")
            
            # Display divergences
            if ao_analysis['divergences']:
                print(f"  🚨 DIVERGENCES DETECTED ({len(ao_analysis['divergences'])}):")
                for div in ao_analysis['divergences']:
                    div_emoji = "🌪️" if 'bullish' in div['type'] else "🌊"
                    print(f"    {div_emoji} {div['description']} (Strength: {div['strength']:.1f})")
                
                all_results.append(result)
            else:
                print(f"  ✅ No divergences detected")
            
            # Show pivot information
            print(f"  📌 Recent Pivots - Price H/L: {len(ao_analysis['price_pivots_high'])}/{len(ao_analysis['price_pivots_low'])}, "
                  f"AO H/L: {len(ao_analysis['ao_pivots_high'])}/{len(ao_analysis['ao_pivots_low'])}")
        
        else:
            print(f"  ❌ Insufficient data for AO analysis")
    
    # Summary
    if all_results:
        print(f"\n🎯 AO DIVERGENCE SUMMARY ({len(all_results)} symbols with signals)")
        print("="*70)
        
        for result in all_results:
            ao_analysis = result['ao_analysis']
            time_str = result['datetime'].strftime('%H:%M')
            
            for div in ao_analysis['divergences']:
                div_emoji = "🌪️" if 'bullish' in div['type'] else "🌊"
                system = "Wind Catcher" if 'bullish' in div['type'] else "River Turn"
                print(f"  {div_emoji} {result['symbol']:12s} - {system} divergence signal at {time_str}")
    
    else:
        print(f"\n✅ No AO divergences detected across watchlist")
    
    conn.close()
    print(f"\n🎯 AO analysis complete!")

if __name__ == "__main__":
    main()