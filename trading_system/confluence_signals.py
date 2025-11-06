"""
Confluence Signal Detector for Wind Catcher & River Turn Trading System
Combines Hull MA patterns + Volume analysis for high-confidence signals
"""

import pandas as pd
import numpy as np
import sqlite3
import yaml
from datetime import datetime, timedelta

# Import functions from our other modules
import sys
import os

def load_config():
    """Load configuration"""
    with open('config/config.yaml', 'r') as file:
        return yaml.safe_load(file)

def connect_to_database():
    """Connect to database"""
    return sqlite3.connect('data/trading_system.db')

def get_price_data(conn, symbol, timeframe='1h', limit=100):
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

# Hull Moving Average functions (from indicators.py)
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

def detect_hull_signals(df):
    """Detect Hull MA signals"""
    if len(df) < 50:
        return None
    
    df['hull_21'] = calculate_hull_ma(df['close'], 21)
    df['hull_34'] = calculate_hull_ma(df['close'], 34)
    
    signals = []
    
    if len(df) >= 3:
        latest_idx = len(df) - 1
        prev_idx = latest_idx - 1
        
        current_price = df['close'].iloc[latest_idx]
        current_hull_21 = df['hull_21'].iloc[latest_idx]
        prev_price = df['close'].iloc[prev_idx]
        prev_hull_21 = df['hull_21'].iloc[prev_idx]
        
        if pd.notna(current_hull_21) and pd.notna(prev_hull_21):
            # Bullish break
            if current_price > current_hull_21 and prev_price <= prev_hull_21:
                signals.append({
                    'type': 'hull_bullish',
                    'system': 'wind_catcher',
                    'description': 'First close above Hull 21',
                    'strength': 0.7,
                    'timestamp': df['timestamp'].iloc[latest_idx]
                })
            
            # Bearish break  
            elif current_price < current_hull_21 and prev_price >= prev_hull_21:
                signals.append({
                    'type': 'hull_bearish',
                    'system': 'river_turn',
                    'description': 'First close below Hull 21', 
                    'strength': 0.7,
                    'timestamp': df['timestamp'].iloc[latest_idx]
                })
    
    return signals

def detect_volume_signals(df, monitoring_candles=3):
    """Detect volume signals"""
    if len(df) < 24:
        return None
    
    # Calculate volume baseline (5-day rolling average)
    baseline_periods = min(120, len(df))  # 120 hours = 5 days
    df['volume_baseline'] = df['volume'].rolling(window=baseline_periods, min_periods=24).mean()
    
    # Check recent volume
    recent_data = df.tail(monitoring_candles)
    volume_signals = []
    
    for idx, row in recent_data.iterrows():
        if pd.isna(row['volume_baseline']):
            continue
            
        volume_ratio = row['volume'] / row['volume_baseline']
        
        if volume_ratio >= 3.0:
            level = "CLIMAX"
            strength = 1.0
        elif volume_ratio >= 2.0:
            level = "HOT" 
            strength = 0.8
        elif volume_ratio >= 1.5:
            level = "WARMING"
            strength = 0.6
        else:
            level = "NORMAL"
            strength = 0.2
        
        volume_signals.append({
            'timestamp': row['timestamp'],
            'level': level,
            'ratio': volume_ratio,
            'strength': strength
        })
    
    return volume_signals

def calculate_confluence_score(hull_signals, volume_signals):
    """Calculate combined confluence score"""
    if not hull_signals or not volume_signals:
        return None
    
    total_score = 0
    confluence_factors = []
    
    # Hull MA signal strength
    for hull_sig in hull_signals:
        total_score += hull_sig['strength']
        confluence_factors.append(f"Hull: {hull_sig['description']}")
    
    # Volume confirmation
    latest_volume = volume_signals[-1]
    total_score += latest_volume['strength']
    confluence_factors.append(f"Volume: {latest_volume['level']} ({latest_volume['ratio']:.1f}x)")
    
    # Bonus for volume confirmation
    if latest_volume['ratio'] >= 1.5:  # Volume warming or higher
        total_score += 0.3
        confluence_factors.append("Volume confirmation bonus")
    
    return {
        'score': total_score,
        'factors': confluence_factors,
        'classification': classify_signal_strength(total_score)
    }

def classify_signal_strength(score):
    """Classify signal based on confluence score"""
    if score >= 1.8:
        return "PERFECT"  # High confluence
    elif score >= 1.2:
        return "GOOD"     # Medium confluence
    elif score >= 0.8:
        return "INTERESTING"  # Low confluence
    else:
        return "WEAK"     # Very low confluence

def analyze_confluence(conn, symbol, timeframe='1h'):
    """Analyze confluence signals for a symbol"""
    
    # Get price data
    df = get_price_data(conn, symbol, timeframe, limit=100)
    if df is None or len(df) < 50:
        return None
    
    # Detect Hull signals
    hull_signals = detect_hull_signals(df)
    if not hull_signals:
        return None
    
    # Detect volume signals
    volume_signals = detect_volume_signals(df)
    if not volume_signals:
        return None
    
    # Calculate confluence
    confluence = calculate_confluence_score(hull_signals, volume_signals)
    if not confluence:
        return None
    
    # Get latest data for display
    latest = df.iloc[-1]
    
    return {
        'symbol': symbol,
        'timestamp': latest['timestamp'],
        'datetime': latest['datetime'],
        'price': latest['close'],
        'hull_signals': hull_signals,
        'volume_signals': volume_signals,
        'confluence': confluence,
        'system': hull_signals[0]['system']  # wind_catcher or river_turn
    }

def main():
    """Main confluence analysis function"""
    print("🚀 Wind Catcher & River Turn - Confluence Signal Detector")
    print("="*70)
    print("🎯 Combining Hull MA Patterns + Volume Analysis")
    print("-"*70)
    
    # Connect to database
    conn = connect_to_database()
    
    # Get watchlist
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
    watchlist = [row[0] for row in cursor.fetchall()]
    
    print(f"📊 Scanning {len(watchlist)} symbols for confluence signals...")
    
    all_signals = []
    
    for symbol in watchlist:
        print(f"\n🔍 {symbol}:")
        
        result = analyze_confluence(conn, symbol)
        if result:
            # Display basic info
            print(f"  💰 Price: ${result['price']:.4f}")
            
            # Display Hull signals
            for hull_sig in result['hull_signals']:
                system_emoji = "🌪️" if hull_sig['system'] == 'wind_catcher' else "🌊"
                print(f"  {system_emoji} {hull_sig['description']}")
            
            # Display volume info
            latest_vol = result['volume_signals'][-1]
            vol_emoji = {"CLIMAX": "🔥", "HOT": "🌡️", "WARMING": "📈", "NORMAL": "📊"}[latest_vol['level']]
            print(f"  {vol_emoji} Volume: {latest_vol['level']} ({latest_vol['ratio']:.1f}x avg)")
            
            # Display confluence score
            conf = result['confluence']
            conf_emoji = {"PERFECT": "⭐", "GOOD": "✨", "INTERESTING": "💡", "WEAK": "🔍"}[conf['classification']]
            print(f"  {conf_emoji} Confluence: {conf['classification']} (Score: {conf['score']:.1f})")
            
            # Add to signals list
            all_signals.append(result)
            
        else:
            print(f"  ✅ No signals detected")
    
    # Summary of active confluence signals
    if all_signals:
        # Filter by significance
        significant_signals = [s for s in all_signals if s['confluence']['classification'] in ['GOOD', 'PERFECT']]
        
        print(f"\n🎯 CONFLUENCE SIGNALS SUMMARY")
        print("="*70)
        
        if significant_signals:
            print(f"🚨 HIGH-CONFIDENCE SIGNALS ({len(significant_signals)}):")
            for signal in significant_signals:
                system_emoji = "🌪️" if signal['system'] == 'wind_catcher' else "🌊"
                conf_emoji = {"PERFECT": "⭐", "GOOD": "✨"}[signal['confluence']['classification']]
                time_str = signal['datetime'].strftime('%H:%M')
                
                print(f"  {conf_emoji} {system_emoji} {signal['symbol']:12s} - "
                      f"{signal['confluence']['classification']} confluence at {time_str}")
                print(f"      💰 ${signal['price']:.4f} | Score: {signal['confluence']['score']:.1f}")
        
        # Show all other signals
        other_signals = [s for s in all_signals if s['confluence']['classification'] == 'INTERESTING']
        if other_signals:
            print(f"\n💡 WATCH LIST SIGNALS ({len(other_signals)}):")
            for signal in other_signals:
                system_emoji = "🌪️" if signal['system'] == 'wind_catcher' else "🌊"
                time_str = signal['datetime'].strftime('%H:%M')
                print(f"  💡 {system_emoji} {signal['symbol']:12s} - Developing setup at {time_str}")
    else:
        print(f"\n✅ No confluence signals detected - system monitoring normally")
    
    conn.close()
    print(f"\n🎯 Confluence analysis complete!")

if __name__ == "__main__":
    main()