"""
Ichimoku Cloud Analyzer for Wind Catcher & River Turn System
Detects cloud retests and recent Kijun-sen touches with timing
"""

import pandas as pd
import numpy as np
import sqlite3
import yaml
from datetime import datetime

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

def calculate_ichimoku(df, conversion_len=20, base_len=60, lead_span_b_len=120, displacement=30):
    """Calculate Ichimoku Cloud components with your settings: 20, 60, 120, 30"""
    if len(df) < lead_span_b_len + displacement:
        return None
    
    # Tenkan-sen (Conversion Line): (20-period high + 20-period low) / 2
    high_conv = df['high'].rolling(window=conversion_len).max()
    low_conv = df['low'].rolling(window=conversion_len).min()
    tenkan_sen = (high_conv + low_conv) / 2
    
    # Kijun-sen (Base Line): (60-period high + 60-period low) / 2
    high_base = df['high'].rolling(window=base_len).max()
    low_base = df['low'].rolling(window=base_len).min()
    kijun_sen = (high_base + low_base) / 2
    
    # Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2, plotted 30 periods ahead
    senkou_span_a = (tenkan_sen + kijun_sen) / 2
    
    # Senkou Span B (Leading Span B): (120-period high + 120-period low) / 2, plotted 30 periods ahead
    high_lead_b = df['high'].rolling(window=lead_span_b_len).max()
    low_lead_b = df['low'].rolling(window=lead_span_b_len).min()
    senkou_span_b = (high_lead_b + low_lead_b) / 2
    
    # Chikou Span (Lagging Span): Current close plotted 30 periods back
    chikou_span = df['close'].shift(-displacement)
    
    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b,
        'chikou_span': chikou_span
    }

def determine_cloud_color(senkou_a, senkou_b):
    """Determine cloud color: green if A > B, red if A < B"""
    if pd.isna(senkou_a) or pd.isna(senkou_b):
        return 'unknown'
    
    if senkou_a > senkou_b:
        return 'green'
    elif senkou_a < senkou_b:
        return 'red'
    else:
        return 'neutral'

def detect_cloud_color_changes(senkou_a, senkou_b, timestamps, lookback=20):
    """Detect cloud color changes with timing"""
    if len(senkou_a) < lookback or len(senkou_b) < lookback:
        return []
    
    color_changes = []
    
    # Analyze recent periods for color changes
    for i in range(len(senkou_a) - lookback, len(senkou_a)):
        if i <= 0:
            continue
            
        if pd.isna(senkou_a.iloc[i]) or pd.isna(senkou_b.iloc[i]):
            continue
        if pd.isna(senkou_a.iloc[i-1]) or pd.isna(senkou_b.iloc[i-1]):
            continue
        
        prev_color = determine_cloud_color(senkou_a.iloc[i-1], senkou_b.iloc[i-1])
        current_color = determine_cloud_color(senkou_a.iloc[i], senkou_b.iloc[i])
        
        if prev_color != current_color and current_color != 'unknown' and prev_color != 'unknown':
            change_time = timestamps.iloc[i]
            current_time = timestamps.iloc[-1]
            hours_ago = (current_time - change_time) / 3600
            
            if hours_ago <= 48:  # Only track changes within last 48 hours
                color_changes.append({
                    'type': 'cloud_color_change',
                    'description': f'Cloud changed from {prev_color} to {current_color}',
                    'old_color': prev_color,
                    'new_color': current_color,
                    'timestamp': change_time,
                    'hours_ago': hours_ago,
                    'strength': 0.8
                })
    
    return color_changes

def detect_price_cloud_retests(df, senkou_a, senkou_b, color_changes, lookback=20):
    """Detect when price retests newly formed cloud"""
    if not color_changes:
        return []
    
    retests = []
    
    # For each color change, look for price returning to the cloud
    for change in color_changes:
        change_timestamp = change['timestamp']
        
        # Find the index of the color change
        change_index = None
        for i, ts in enumerate(df['timestamp']):
            if ts >= change_timestamp:
                change_index = i
                break
        
        if change_index is None or change_index >= len(df) - 5:
            continue
        
        # Look for price retests after the color change
        for i in range(change_index + 1, min(change_index + lookback, len(df))):
            if pd.isna(senkou_a.iloc[i]) or pd.isna(senkou_b.iloc[i]):
                continue
            
            current_price = df['close'].iloc[i]
            cloud_top = max(senkou_a.iloc[i], senkou_b.iloc[i])
            cloud_bottom = min(senkou_a.iloc[i], senkou_b.iloc[i])
            
            # Check if price is inside the newly formed cloud
            if cloud_bottom <= current_price <= cloud_top:
                retest_time = df['timestamp'].iloc[i]
                current_time = df['timestamp'].iloc[-1]
                hours_ago = (current_time - retest_time) / 3600
                
                if hours_ago <= 24:  # Only recent retests
                    retests.append({
                        'type': 'cloud_retest',
                        'description': f'Price retested newly formed {change["new_color"]} cloud',
                        'cloud_color': change['new_color'],
                        'timestamp': retest_time,
                        'price': current_price,
                        'hours_ago': hours_ago,
                        'strength': 0.9,
                        'related_change': change
                    })
                    break  # Only record first retest per color change
    
    return retests

def detect_kijun_touches(df, kijun_sen, lookback=6):
    """Detect when price touches Kijun-sen with timing - limited to last 6 hours"""
    if len(df) < lookback:
        return []
    
    kijun_touches = []
    
    # Only analyze last 6 periods (6 hours on 1h timeframe)
    for i in range(len(df) - lookback, len(df)):
        if pd.isna(kijun_sen.iloc[i]):
            continue
        
        current_price = df['close'].iloc[i]
        current_high = df['high'].iloc[i]
        current_low = df['low'].iloc[i]
        kijun_value = kijun_sen.iloc[i]
        
        # Check if price touched Kijun (price range includes Kijun value)
        if current_low <= kijun_value <= current_high:
            touch_time = df['timestamp'].iloc[i]
            current_time = df['timestamp'].iloc[-1]
            hours_ago = (current_time - touch_time) / 3600
            
            # Determine if it was support or resistance
            if current_price > kijun_value:
                touch_type = 'support'
            elif current_price < kijun_value:
                touch_type = 'resistance'
            else:
                touch_type = 'exact'
            
            kijun_touches.append({
                'type': 'kijun_touch',
                'description': f'Price touched Kijun-sen as {touch_type}',
                'touch_type': touch_type,
                'timestamp': touch_time,
                'price': current_price,
                'kijun_value': kijun_value,
                'hours_ago': hours_ago,
                'strength': 0.7
            })
    
    return kijun_touches

def analyze_symbol_ichimoku(conn, symbol, timeframe='1h'):
    """Complete Ichimoku analysis for a symbol"""
    df = get_price_data(conn, symbol, timeframe=timeframe, limit=200)
    if df is None or len(df) < 150:
        return None
    
    # Calculate Ichimoku components
    ichimoku = calculate_ichimoku(df, conversion_len=20, base_len=60, lead_span_b_len=120, displacement=30)
    if ichimoku is None:
        return None
    
    # Add to dataframe
    for key, value in ichimoku.items():
        df[key] = value
    
    # Get current values
    latest = df.iloc[-1]
    current_cloud_color = determine_cloud_color(latest['senkou_span_a'], latest['senkou_span_b'])
    
    # Detect events - focus on meaningful signals only
    color_changes = detect_cloud_color_changes(df['senkou_span_a'], df['senkou_span_b'], df['timestamp'])
    retests = detect_price_cloud_retests(df, df['senkou_span_a'], df['senkou_span_b'], color_changes)
    kijun_touches = detect_kijun_touches(df, df['kijun_sen'])
    
    # Only include cloud retests and recent Kijun touches (no color change alerts)
    significant_events = retests + kijun_touches
    
    return {
        'symbol': symbol,
        'timestamp': latest['timestamp'],
        'datetime': latest['datetime'],
        'price': latest['close'],
        'current_cloud_color': current_cloud_color,
        'tenkan_sen': latest['tenkan_sen'],
        'kijun_sen': latest['kijun_sen'],
        'senkou_span_a': latest['senkou_span_a'],
        'senkou_span_b': latest['senkou_span_b'],
        'significant_events': significant_events,
        'quality_score': max([e['strength'] for e in significant_events] + [0])
    }

def main():
    """Main Ichimoku analysis function"""
    print("Wind Catcher & River Turn - Ichimoku Cloud Analysis")
    print("="*70)
    print("Detecting cloud retests and recent Kijun-sen touches...")
    print("-"*70)
    
    conn = connect_to_database()
    
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
    watchlist = [row[0] for row in cursor.fetchall()]
    
    all_results = []
    
    for symbol in watchlist:
        print(f"\n{symbol}:")
        
        result = analyze_symbol_ichimoku(conn, symbol)
        if result:
            # Display current state
            cloud_emoji = {"green": "🟢", "red": "🔴", "neutral": "⚪", "unknown": "❓"}[result['current_cloud_color']]
            
            print(f"  Price: ${result['price']:.4f}")
            print(f"  {cloud_emoji} Cloud Color: {result['current_cloud_color'].upper()}")
            
            # Show indicator values
            if pd.notna(result['kijun_sen']):
                print(f"  📊 Kijun-sen: ${result['kijun_sen']:.4f}")
            if pd.notna(result['tenkan_sen']):
                print(f"  📈 Tenkan-sen: ${result['tenkan_sen']:.4f}")
            if pd.notna(result['senkou_span_a']) and pd.notna(result['senkou_span_b']):
                print(f"  ☁️ Cloud A: ${result['senkou_span_a']:.4f}")
                print(f"  ☁️ Cloud B: ${result['senkou_span_b']:.4f}")
            
            # Show significant events only
            if result['significant_events']:
                print(f"  🚨 ICHIMOKU EVENTS:")
                for event in result['significant_events']:
                    event_time = datetime.fromtimestamp(event['timestamp']).strftime('%H:%M')
                    
                    if event['type'] == 'cloud_retest':
                        emoji = "🎯"
                    elif event['type'] == 'kijun_touch':
                        emoji = "📍"
                    else:
                        emoji = "📌"
                    
                    print(f"    {emoji} {event['description']}")
                    print(f"       ⏰ {event['hours_ago']:.1f}h ago at {event_time} | Price: ${event.get('price', 'N/A')}")
                
                all_results.append(result)
            
            else:
                print(f"  ✅ No recent events - monitoring...")
        
        else:
            print(f"  ❌ Insufficient data")
    
    # Summary
    if all_results:
        print(f"\n🎯 ICHIMOKU SIGNALS SUMMARY ({len(all_results)} symbols)")
        print("="*70)
        
        for result in all_results:
            print(f"\n{result['symbol']}:")
            
            # Group events by type
            retests = [e for e in result['significant_events'] if e['type'] == 'cloud_retest']
            kijun_touches = [e for e in result['significant_events'] if e['type'] == 'kijun_touch']
            
            if retests:
                print("  🎯 CLOUD RETESTS:")
                for event in retests:
                    event_time = datetime.fromtimestamp(event['timestamp']).strftime('%H:%M')
                    print(f"    {event['description']} - {event['hours_ago']:.1f}h ago at {event_time}")
            
            if kijun_touches:
                print("  📍 KIJUN-SEN TOUCHES (Last 6h):")
                for event in kijun_touches:
                    event_time = datetime.fromtimestamp(event['timestamp']).strftime('%H:%M')
                    print(f"    {event['description']} - {event['hours_ago']:.1f}h ago at {event_time}")
    
    else:
        print(f"\n✅ No Ichimoku events detected")
    
    conn.close()
    print(f"\n🎯 Ichimoku analysis complete!")

if __name__ == "__main__":
    main()