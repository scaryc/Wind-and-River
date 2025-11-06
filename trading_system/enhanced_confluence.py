"""
Enhanced Confluence System for Wind Catcher & River Turn
Combines Hull MA + Volume + AO Divergence signals
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
    """Get price data for analysis"""
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

# Technical Analysis Functions
def calculate_wma(prices, period):
    """Calculate Weighted Moving Average"""
    if len(prices) < period:
        return pd.Series([np.nan] * len(prices), index=prices.index)
    
    weights = np.arange(1, period + 1)
    wma = []
    
    for i in range(len(prices)):
        if i < period - 1:
            wma.append(np.nan)
        else:
            price_window = prices.iloc[i-period+1:i+1]
            weighted_sum = np.sum(price_window * weights)
            weight_sum = np.sum(weights)
            wma.append(weighted_sum / weight_sum)
    
    return pd.Series(wma, index=prices.index)

def calculate_hull_ma(prices, period):
    """Calculate Hull Moving Average"""
    if len(prices) < period:
        return pd.Series([np.nan] * len(prices), index=prices.index)
    
    half_period = int(period / 2)
    wma_half = calculate_wma(prices, half_period)
    wma_full = calculate_wma(prices, period)
    diff = 2 * wma_half - wma_full
    sqrt_period = int(np.sqrt(period))
    hull_ma = calculate_wma(diff, sqrt_period)
    
    return hull_ma

def calculate_sma(prices, period):
    """Calculate Simple Moving Average"""
    return prices.rolling(window=period, min_periods=period).mean()

def calculate_awesome_oscillator(df, fast_period=5, slow_period=34):
    """Calculate Awesome Oscillator"""
    median_price = (df['high'] + df['low']) / 2
    fast_sma = calculate_sma(median_price, fast_period)
    slow_sma = calculate_sma(median_price, slow_period)
    return fast_sma - slow_sma

def find_pivots(data, order=5):
    """Find pivot highs and lows"""
    if len(data) < order * 2 + 1:
        return [], []
    
    highs = argrelextrema(data.values, np.greater, order=order)[0]
    lows = argrelextrema(data.values, np.less, order=order)[0]
    
    return highs.tolist(), lows.tolist()

def detect_ao_divergences(price_data, ao_data, lookback_bars=50):
    """Detect AO divergences (simplified for confluence)"""
    if len(price_data) < lookback_bars or len(ao_data) < lookback_bars:
        return []
    
    # Focus on recent data
    recent_price = price_data.tail(lookback_bars)
    recent_ao = ao_data.tail(lookback_bars)
    
    # Find pivots
    price_highs, price_lows = find_pivots(recent_price, order=5)
    ao_highs, ao_lows = find_pivots(recent_ao, order=5)
    
    divergences = []
    
    # Check for recent divergences (last 20 bars)
    if len(price_lows) >= 2 and len(ao_lows) >= 2:
        # Bullish divergence check
        recent_price_lows = [p for p in price_lows if p >= len(recent_price) - 20]
        recent_ao_lows = [a for a in ao_lows if a >= len(recent_ao) - 20]
        
        if len(recent_price_lows) >= 2 and len(recent_ao_lows) >= 2:
            p1, p2 = recent_price_lows[-2], recent_price_lows[-1]
            a1, a2 = recent_ao_lows[-2], recent_ao_lows[-1]
            
            if (recent_price.iloc[p2] < recent_price.iloc[p1] and 
                recent_ao.iloc[a2] > recent_ao.iloc[a1] and
                abs(p1 - a1) <= 5 and abs(p2 - a2) <= 5):
                
                divergences.append({
                    'type': 'bullish',
                    'strength': 0.8,
                    'system': 'wind_catcher',
                    'description': 'AO bullish divergence'
                })
    
    if len(price_highs) >= 2 and len(ao_highs) >= 2:
        # Bearish divergence check
        recent_price_highs = [p for p in price_highs if p >= len(recent_price) - 20]
        recent_ao_highs = [a for a in ao_highs if a >= len(recent_ao) - 20]
        
        if len(recent_price_highs) >= 2 and len(recent_ao_highs) >= 2:
            p1, p2 = recent_price_highs[-2], recent_price_highs[-1]
            a1, a2 = recent_ao_highs[-2], recent_ao_highs[-1]
            
            if (recent_price.iloc[p2] > recent_price.iloc[p1] and 
                recent_ao.iloc[a2] < recent_ao.iloc[a1] and
                abs(p1 - a1) <= 5 and abs(p2 - a2) <= 5):
                
                divergences.append({
                    'type': 'bearish',
                    'strength': 0.8,
                    'system': 'river_turn',
                    'description': 'AO bearish divergence'
                })
    
    return divergences

def analyze_enhanced_confluence(conn, symbol):
    """Complete enhanced confluence analysis"""
    df = get_price_data(conn, symbol, timeframe='1h', limit=200)
    if df is None or len(df) < 100:
        return None
    
    # Calculate all indicators
    df['hull_21'] = calculate_hull_ma(df['close'], 21)
    df['hull_34'] = calculate_hull_ma(df['close'], 34)
    df['ao'] = calculate_awesome_oscillator(df)
    
    # Volume analysis
    baseline_periods = min(120, len(df))
    df['volume_baseline'] = df['volume'].rolling(window=baseline_periods, min_periods=24).mean()
    
    # Get latest values
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    signals = []
    confluence_factors = []
    total_score = 0
    
    # 1. Hull MA signals
    hull_signals = []
    if pd.notna(latest['hull_21']) and pd.notna(prev['hull_21']):
        # Bullish break
        if latest['close'] > latest['hull_21'] and prev['close'] <= prev['hull_21']:
            hull_signals.append({
                'type': 'wind_catcher',
                'description': 'Hull bullish break',
                'strength': 0.7
            })
            total_score += 0.7
            confluence_factors.append("Hull bullish break")
        
        # Bearish break
        elif latest['close'] < latest['hull_21'] and prev['close'] >= prev['hull_21']:
            hull_signals.append({
                'type': 'river_turn',
                'description': 'Hull bearish break', 
                'strength': 0.7
            })
            total_score += 0.7
            confluence_factors.append("Hull bearish break")
    
    # 2. Volume analysis
    volume_ratio = latest['volume'] / latest['volume_baseline'] if pd.notna(latest['volume_baseline']) else 0
    
    if volume_ratio >= 3.0:
        volume_level = "CLIMAX"
        volume_strength = 1.0
        volume_emoji = "🔥"
    elif volume_ratio >= 2.0:
        volume_level = "HOT"
        volume_strength = 0.8
        volume_emoji = "🌡️"
    elif volume_ratio >= 1.5:
        volume_level = "WARMING"
        volume_strength = 0.6
        volume_emoji = "📈"
    else:
        volume_level = "NORMAL"
        volume_strength = 0.2
        volume_emoji = "📊"
    
    total_score += volume_strength
    confluence_factors.append(f"Volume: {volume_level}")
    
    # Volume confirmation bonus
    if volume_ratio >= 1.5:
        total_score += 0.3
        confluence_factors.append("Volume confirmation bonus")
    
    # 3. AO Divergence analysis
    ao_divergences = detect_ao_divergences(df['close'], df['ao'])
    
    for divergence in ao_divergences:
        total_score += divergence['strength']
        confluence_factors.append(divergence['description'])
        signals.append(divergence)
    
    # 4. Determine primary system and classification
    primary_system = None
    if hull_signals:
        primary_system = hull_signals[0]['type']
    elif ao_divergences:
        primary_system = ao_divergences[0]['system']
    
    # Confluence classification
    if total_score >= 1.8:
        confluence_class = "PERFECT"
        conf_emoji = "⭐"
    elif total_score >= 1.2:
        confluence_class = "GOOD"
        conf_emoji = "✨"
    elif total_score >= 0.8:
        confluence_class = "INTERESTING"
        conf_emoji = "💡"
    else:
        confluence_class = "NONE"
        conf_emoji = "✅"
    
    # Hull trend analysis
    hull_trend = "BULLISH" if latest['close'] > latest['hull_21'] else "BEARISH"
    hull_trend_emoji = "🟢" if hull_trend == "BULLISH" else "🔴"
    
    return {
        'symbol': symbol,
        'timestamp': latest['timestamp'],
        'datetime': latest['datetime'],
        'price': latest['close'],
        'hull_signals': hull_signals,
        'ao_divergences': ao_divergences,
        'ao_current': latest['ao'],
        'volume_level': volume_level,
        'volume_ratio': volume_ratio,
        'volume_emoji': volume_emoji,
        'confluence_score': total_score,
        'confluence_class': confluence_class,
        'confluence_factors': confluence_factors,
        'conf_emoji': conf_emoji,
        'primary_system': primary_system,
        'hull_trend': hull_trend,
        'hull_trend_emoji': hull_trend_emoji
    }

def main():
    """Main enhanced confluence analysis"""
    print("🚀 Wind Catcher & River Turn - Enhanced Confluence System")
    print("="*80)
    print("🎯 Hull MA + Volume + AO Divergence Analysis")
    print("-"*80)
    
    # Connect to database
    conn = connect_to_database()
    
    # Get watchlist
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
    watchlist = [row[0] for row in cursor.fetchall()]
    
    results = []
    
    for symbol in watchlist:
        print(f"\n🔍 {symbol}:")
        
        result = analyze_enhanced_confluence(conn, symbol)
        if result:
            # Display results
            print(f"  💰 Price: ${result['price']:.4f} {result['hull_trend_emoji']}")
            
            # Show Hull signals
            if result['hull_signals']:
                for signal in result['hull_signals']:
                    system_emoji = "🌪️" if signal['type'] == 'wind_catcher' else "🌊"
                    print(f"  {system_emoji} {signal['description']}")
            
            # Show AO divergences
            if result['ao_divergences']:
                for div in result['ao_divergences']:
                    div_emoji = "🌪️" if div['type'] == 'bullish' else "🌊"
                    print(f"  {div_emoji} {div['description']}")
            
            # Show volume
            print(f"  {result['volume_emoji']} Volume: {result['volume_level']} ({result['volume_ratio']:.1f}x)")
            
            # Show AO status
            ao_trend = "📈" if result['ao_current'] > 0 else "📉"
            print(f"  {ao_trend} AO: {result['ao_current']:.3f}")
            
            # Show confluence
            print(f"  {result['conf_emoji']} Confluence: {result['confluence_class']} (Score: {result['confluence_score']:.1f})")
            
            if result['confluence_score'] >= 0.8:
                results.append(result)
        
        else:
            print(f"  ❌ Insufficient data")
    
    # Enhanced Summary
    if results:
        print(f"\n🎯 ENHANCED CONFLUENCE SUMMARY ({len(results)} signals)")
        print("="*80)
        
        perfect_signals = [r for r in results if r['confluence_class'] == 'PERFECT']
        good_signals = [r for r in results if r['confluence_class'] == 'GOOD']
        interesting_signals = [r for r in results if r['confluence_class'] == 'INTERESTING']
        
        if perfect_signals:
            print("⭐ PERFECT CONFLUENCE SETUPS:")
            for result in perfect_signals:
                system_emoji = "🌪️" if result['primary_system'] == 'wind_catcher' else "🌊"
                print(f"  {result['conf_emoji']} {system_emoji} {result['symbol']:12s} ${result['price']:.4f}")
                print(f"      Factors: {', '.join(result['confluence_factors'])}")
        
        if good_signals:
            print("✨ GOOD CONFLUENCE SETUPS:")
            for result in good_signals:
                system_emoji = "🌪️" if result['primary_system'] == 'wind_catcher' else "🌊"
                print(f"  {result['conf_emoji']} {system_emoji} {result['symbol']:12s} ${result['price']:.4f}")
        
        if interesting_signals:
            print("💡 DEVELOPING SETUPS:")
            for result in interesting_signals:
                system_emoji = "🌪️" if result['primary_system'] == 'wind_catcher' else "🌊"
                print(f"  {result['conf_emoji']} {system_emoji} {result['symbol']:12s} ${result['price']:.4f}")
    
    else:
        print(f"\n✅ No significant confluence signals detected")
    
    conn.close()
    print(f"\n🎯 Enhanced confluence analysis complete!")

if __name__ == "__main__":
    main()