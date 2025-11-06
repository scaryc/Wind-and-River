"""
Enhanced Hull Moving Average Analyzer for Wind Catcher & River Turn System
Detects Hull breaks and cross retests with timing
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

def detect_hull_breaks(df):
    """Detect Hull MA breaks (Pattern 1)"""
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
                    'type': 'hull_bullish_break',
                    'system': 'wind_catcher',
                    'description': 'First close above Hull 21',
                    'strength': 0.7,
                    'timestamp': df['timestamp'].iloc[latest_idx]
                })
            
            # Bearish break  
            elif current_price < current_hull_21 and prev_price >= prev_hull_21:
                signals.append({
                    'type': 'hull_bearish_break',
                    'system': 'river_turn',
                    'description': 'First close below Hull 21',
                    'strength': 0.7,
                    'timestamp': df['timestamp'].iloc[latest_idx]
                })
    
    return signals

def detect_hull_cross_retests(df, lookback=20):
    """Detect Hull 21/34 cross followed by price retest of the lines"""
    if len(df) < lookback:
        return []
    
    retests = []
    
    # Look for Hull 21/34 crosses in recent history
    for i in range(len(df) - lookback, len(df) - 5):  # Don't check too recent for cross
        if (pd.isna(df['hull_21'].iloc[i]) or pd.isna(df['hull_34'].iloc[i]) or
            pd.isna(df['hull_21'].iloc[i-1]) or pd.isna(df['hull_34'].iloc[i-1])):
            continue
        
        # Current and previous Hull values
        curr_21 = df['hull_21'].iloc[i]
        curr_34 = df['hull_34'].iloc[i]
        prev_21 = df['hull_21'].iloc[i-1]
        prev_34 = df['hull_34'].iloc[i-1]
        
        cross_detected = False
        cross_type = None
        
        # Bullish cross: Hull 21 crosses above Hull 34
        if curr_21 > curr_34 and prev_21 <= prev_34:
            cross_detected = True
            cross_type = 'bullish'
        
        # Bearish cross: Hull 21 crosses below Hull 34
        elif curr_21 < curr_34 and prev_21 >= prev_34:
            cross_detected = True
            cross_type = 'bearish'
        
        if cross_detected:
            # Look for price retests after the cross
            for j in range(i + 1, min(i + 15, len(df))):  # Check next 15 periods
                if (pd.isna(df['hull_21'].iloc[j]) or pd.isna(df['hull_34'].iloc[j])):
                    continue
                
                current_price = df['close'].iloc[j]
                current_high = df['high'].iloc[j]
                current_low = df['low'].iloc[j]
                hull_21_val = df['hull_21'].iloc[j]
                hull_34_val = df['hull_34'].iloc[j]
                
                retest_detected = False
                retest_line = None
                retest_strength = 0.6
                
                if cross_type == 'bullish':
                    # After bullish cross, look for retests as support
                    # Hull 34 retest (stronger signal)
                    if current_low <= hull_34_val <= current_high and current_price >= hull_34_val:
                        retest_detected = True
                        retest_line = 'Hull 34'
                        retest_strength = 0.8  # Hull 34 retest is stronger
                    
                    # Hull 21 retest (weaker signal)
                    elif current_low <= hull_21_val <= current_high and current_price >= hull_21_val:
                        retest_detected = True
                        retest_line = 'Hull 21'
                        retest_strength = 0.6
                
                elif cross_type == 'bearish':
                    # After bearish cross, look for retests as resistance
                    # Hull 34 retest (stronger signal)
                    if current_low <= hull_34_val <= current_high and current_price <= hull_34_val:
                        retest_detected = True
                        retest_line = 'Hull 34'
                        retest_strength = 0.8  # Hull 34 retest is stronger
                    
                    # Hull 21 retest (weaker signal) 
                    elif current_low <= hull_21_val <= current_high and current_price <= hull_21_val:
                        retest_detected = True
                        retest_line = 'Hull 21'
                        retest_strength = 0.6
                
                if retest_detected:
                    # Check timing - only recent retests
                    retest_time = df['timestamp'].iloc[j]
                    current_time = df['timestamp'].iloc[-1]
                    hours_ago = (current_time - retest_time) / 3600
                    
                    if hours_ago <= 12:  # Only retests within last 12 hours
                        system = 'wind_catcher' if cross_type == 'bullish' else 'river_turn'
                        support_resistance = 'support' if cross_type == 'bullish' else 'resistance'
                        
                        retests.append({
                            'type': f'hull_cross_retest_{cross_type}',
                            'system': system,
                            'description': f'{retest_line} {support_resistance} retest after cross',
                            'strength': retest_strength,
                            'timestamp': retest_time,
                            'hours_ago': hours_ago,
                            'retest_line': retest_line
                        })
                        break  # Only record first retest per cross
    
    return retests

def analyze_symbol_hull(conn, symbol):
    """Complete Hull MA analysis for a symbol"""
    df = get_price_data(conn, symbol, timeframe='1h', limit=200)
    if df is None or len(df) < 50:
        return None
    
    # Calculate Hull MAs
    df['hull_21'] = calculate_hull_ma(df['close'], 21)
    df['hull_34'] = calculate_hull_ma(df['close'], 34)
    
    # Detect signals
    hull_breaks = detect_hull_breaks(df)
    cross_retests = detect_hull_cross_retests(df)
    
    # Combine all Hull signals
    all_hull_signals = hull_breaks + cross_retests
    
    # Get latest values
    latest = df.iloc[-1]
    
    # Hull trend analysis
    hull_trend = "BULLISH" if latest['close'] > latest['hull_21'] else "BEARISH"
    hull_cross_status = "Above" if latest['hull_21'] > latest['hull_34'] else "Below"
    
    return {
        'symbol': symbol,
        'timestamp': latest['timestamp'],
        'datetime': latest['datetime'],
        'price': latest['close'],
        'hull_21': latest['hull_21'],
        'hull_34': latest['hull_34'],
        'hull_trend': hull_trend,
        'hull_cross_status': hull_cross_status,
        'hull_breaks': hull_breaks,
        'cross_retests': cross_retests,
        'all_signals': all_hull_signals,
        'quality_score': max([s['strength'] for s in all_hull_signals] + [0])
    }

def main():
    """Main Hull analysis function"""
    print("Wind Catcher & River Turn - Enhanced Hull MA Analysis")
    print("="*70)
    print("Detecting Hull breaks and cross retests with timing...")
    print("-"*70)
    
    conn = connect_to_database()
    
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
    watchlist = [row[0] for row in cursor.fetchall()]
    
    all_results = []
    
    for symbol in watchlist:
        print(f"\n{symbol}:")
        
        result = analyze_symbol_hull(conn, symbol)
        if result:
            # Display current state
            trend_emoji = "🟢" if result['hull_trend'] == "BULLISH" else "🔴"
            cross_emoji = "⬆️" if result['hull_cross_status'] == "Above" else "⬇️"
            
            print(f"  Price: ${result['price']:.4f}")
            print(f"  {trend_emoji} Hull Trend: {result['hull_trend']}")
            print(f"  {cross_emoji} Hull 21 vs 34: {result['hull_cross_status']}")
            
            if pd.notna(result['hull_21']) and pd.notna(result['hull_34']):
                print(f"  📊 Hull 21: ${result['hull_21']:.4f}")
                print(f"  📊 Hull 34: ${result['hull_34']:.4f}")
            
            # Show Hull break signals
            if result['hull_breaks']:
                print(f"  🚨 HULL BREAKS:")
                for signal in result['hull_breaks']:
                    system_emoji = "🌪️" if signal['system'] == 'wind_catcher' else "🌊"
                    signal_time = datetime.fromtimestamp(signal['timestamp']).strftime('%H:%M')
                    print(f"    {system_emoji} {signal['description']} at {signal_time}")
            
            # Show cross retest signals
            if result['cross_retests']:
                print(f"  🎯 CROSS RETESTS:")
                for signal in result['cross_retests']:
                    system_emoji = "🌪️" if signal['system'] == 'wind_catcher' else "🌊"
                    signal_time = datetime.fromtimestamp(signal['timestamp']).strftime('%H:%M')
                    strength_stars = "⭐" if signal['strength'] >= 0.8 else "✨"
                    print(f"    {system_emoji} {strength_stars} {signal['description']}")
                    print(f"       ⏰ {signal['hours_ago']:.1f}h ago at {signal_time}")
            
            if result['all_signals']:
                all_results.append(result)
            
            if not result['all_signals']:
                print(f"  ✅ No Hull signals - monitoring...")
        
        else:
            print(f"  ❌ Insufficient data")
    
    # Summary
    if all_results:
        print(f"\n🎯 HULL SIGNALS SUMMARY ({len(all_results)} symbols)")
        print("="*70)
        
        for result in all_results:
            print(f"\n{result['symbol']}:")
            
            if result['hull_breaks']:
                print("  🚨 BREAKS:")
                for signal in result['hull_breaks']:
                    system_emoji = "🌪️" if signal['system'] == 'wind_catcher' else "🌊"
                    signal_time = datetime.fromtimestamp(signal['timestamp']).strftime('%H:%M')
                    print(f"    {system_emoji} {signal['description']} at {signal_time}")
            
            if result['cross_retests']:
                print("  🎯 CROSS RETESTS:")
                for signal in result['cross_retests']:
                    system_emoji = "🌪️" if signal['system'] == 'wind_catcher' else "🌊"
                    signal_time = datetime.fromtimestamp(signal['timestamp']).strftime('%H:%M')
                    quality = "HIGH" if signal['strength'] >= 0.8 else "MEDIUM"
                    print(f"    {system_emoji} {signal['description']} - {quality} quality")
                    print(f"        ⏰ {signal['hours_ago']:.1f}h ago at {signal_time}")
    
    else:
        print(f"\n✅ No Hull signals detected")
    
    conn.close()
    print(f"\n🎯 Hull analysis complete!")

if __name__ == "__main__":
    main()