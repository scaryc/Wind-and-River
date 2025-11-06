"""
Modified Alligator Analyzer for Wind Catcher & River Turn System
Detects sleeping/awake states and retracement opportunities with timing
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

def calculate_sma(prices, period):
    """Calculate Simple Moving Average"""
    return prices.rolling(window=period, min_periods=period).mean()

def calculate_modified_alligator(df, multiplier=10):
    """Calculate Modified Alligator with 10x multiplier"""
    if len(df) < 130:
        return None, None, None
    
    jaw_period = 13 * multiplier     # 130
    teeth_period = 8 * multiplier    # 80
    lips_period = 5 * multiplier     # 50
    
    median_price = (df['high'] + df['low']) / 2
    
    jaw = calculate_sma(median_price, jaw_period)
    teeth = calculate_sma(median_price, teeth_period)
    lips = calculate_sma(median_price, lips_period)
    
    return jaw, teeth, lips

def determine_alligator_state(jaw, teeth, lips, threshold_pct=0.15):
    """Determine if Alligator is sleeping or awake"""
    if pd.isna(jaw) or pd.isna(teeth) or pd.isna(lips):
        return 'unknown', 0.0, 'none'
    
    max_val = max(jaw, teeth, lips)
    min_val = min(jaw, teeth, lips)
    
    if max_val == 0:
        return 'unknown', 0.0, 'none'
    
    spread_pct = ((max_val - min_val) / max_val) * 100
    
    if spread_pct <= threshold_pct:
        return 'sleeping', spread_pct, 'consolidation'
    else:
        if lips > teeth > jaw:
            return 'awake', spread_pct, 'bullish'
        elif lips < teeth < jaw:
            return 'awake', spread_pct, 'bearish'
        else:
            return 'awake', spread_pct, 'mixed'

def detect_state_transitions(states, timestamps, lookback=10):
    """Detect transitions between sleeping and awake states with timing"""
    if len(states) < lookback or len(timestamps) < lookback:
        return None
    
    recent_states = states[-lookback:]
    recent_timestamps = timestamps[-lookback:]
    
    transitions = []
    
    for i in range(1, len(recent_states)):
        prev_state = recent_states[i-1]
        curr_state = recent_states[i]
        transition_time = recent_timestamps[i]
        
        if prev_state == 'awake' and curr_state == 'sleeping':
            confirmed = True
            check_periods = min(3, len(recent_states) - i - 1)
            for j in range(1, check_periods + 1):
                if i + j < len(recent_states) and recent_states[i + j] != 'sleeping':
                    confirmed = False
                    break
            
            if confirmed:
                hours_ago = (recent_timestamps[-1] - transition_time) / 3600
                transitions.append({
                    'type': 'awake_to_sleeping',
                    'description': 'Market entered consolidation phase',
                    'strength': 0.6,
                    'significance': 'medium',
                    'trigger_timestamp': transition_time,
                    'hours_ago': hours_ago
                })
        
        elif prev_state == 'sleeping' and curr_state == 'awake':
            confirmed = True
            check_periods = min(3, len(recent_states) - i - 1)
            for j in range(1, check_periods + 1):
                if i + j < len(recent_states) and recent_states[i + j] != 'awake':
                    confirmed = False
                    break
            
            if confirmed:
                hours_ago = (recent_timestamps[-1] - transition_time) / 3600
                transitions.append({
                    'type': 'sleeping_to_awake',
                    'description': 'Market broke out of consolidation',
                    'strength': 0.7,
                    'significance': 'high',
                    'trigger_timestamp': transition_time,
                    'hours_ago': hours_ago
                })
    
    if transitions:
        return [transitions[-1]]
    
    return transitions

def determine_price_zone(price, jaw, teeth, lips, trend_direction):
    """Determine which zone price is in relative to Alligator lines"""
    if trend_direction == 'bullish':
        red_line = lips
        blue_line = jaw
        
        if price > red_line:
            return 'above_red'
        elif abs(price - blue_line) / blue_line < 0.002:
            return 'at_blue_line'
        elif price < blue_line:
            return 'below_blue'
        elif red_line >= price >= blue_line:
            return 'between_red_blue'
        else:
            return 'unknown'
    
    elif trend_direction == 'bearish':
        red_line = lips
        blue_line = jaw
        
        if price < red_line:
            return 'above_red'
        elif abs(price - blue_line) / blue_line < 0.002:
            return 'at_blue_line'
        elif price > blue_line:
            return 'below_blue'
        elif red_line <= price <= blue_line:
            return 'between_red_blue'
        else:
            return 'unknown'
    
    return 'unknown'

def analyze_retracement_history(df, jaw, teeth, lips, trend_direction, lookback=20):
    """Analyze price movement through Alligator zones with timing"""
    if len(df) < lookback or trend_direction == 'mixed':
        return []
    
    events = []
    
    for i in range(len(df) - lookback, len(df)):
        if (pd.isna(jaw.iloc[i]) or pd.isna(teeth.iloc[i]) or pd.isna(lips.iloc[i])):
            continue
        
        current_price = df['close'].iloc[i]
        current_time = df['timestamp'].iloc[i]
        
        prev_zone = None
        if i > 0 and not (pd.isna(jaw.iloc[i-1]) or pd.isna(teeth.iloc[i-1]) or pd.isna(lips.iloc[i-1])):
            prev_price = df['close'].iloc[i-1]
            prev_zone = determine_price_zone(prev_price, jaw.iloc[i-1], teeth.iloc[i-1], lips.iloc[i-1], trend_direction)
        
        current_zone = determine_price_zone(current_price, jaw.iloc[i], teeth.iloc[i], lips.iloc[i], trend_direction)
        
        if prev_zone and current_zone != prev_zone:
            if current_zone == 'between_red_blue':
                events.append({
                    'type': 'zone_entry',
                    'description': 'Price entered red-blue zone',
                    'timestamp': current_time,
                    'price': current_price,
                    'zone': 'between_red_blue',
                    'strength': 0.7
                })
            
            elif prev_zone == 'between_red_blue' and current_zone != 'between_red_blue':
                if current_zone == 'above_red':
                    direction = 'upward'
                    desc = 'Price broke above red line (bullish exit)'
                elif current_zone == 'below_blue':
                    direction = 'downward' 
                    desc = 'Price broke below blue line (bearish exit)'
                else:
                    direction = 'unknown'
                    desc = 'Price left red-blue zone'
                
                events.append({
                    'type': 'zone_exit',
                    'description': desc,
                    'timestamp': current_time,
                    'price': current_price,
                    'direction': direction,
                    'strength': 0.6
                })
        
        if current_zone == 'at_blue_line':
            events.append({
                'type': 'blue_line_contact',
                'description': 'Price touched blue line',
                'timestamp': current_time,
                'price': current_price,
                'zone': 'at_blue_line',
                'strength': 0.9
            })
    
    recent_events = []
    current_time = df['timestamp'].iloc[-1]
    for event in events:
        hours_ago = (current_time - event['timestamp']) / 3600
        if hours_ago <= 10:
            event['hours_ago'] = hours_ago
            recent_events.append(event)
    
    return recent_events

def analyze_symbol_alligator(conn, symbol):
    """Complete Alligator analysis for a symbol"""
    df = get_price_data(conn, symbol, timeframe='1h', limit=200)
    if df is None or len(df) < 150:
        return None
    
    jaw, teeth, lips = calculate_modified_alligator(df, multiplier=10)
    if jaw is None:
        return None
    
    df['jaw'] = jaw
    df['teeth'] = teeth  
    df['lips'] = lips
    
    states = []
    spreads = []
    directions = []
    timestamps = []
    
    for i in range(len(df)):
        if i < 130:
            states.append('unknown')
            spreads.append(0)
            directions.append('none')
        else:
            state, spread, direction = determine_alligator_state(
                df['jaw'].iloc[i], df['teeth'].iloc[i], df['lips'].iloc[i]
            )
            states.append(state)
            spreads.append(spread)
            directions.append(direction)
        
        timestamps.append(df['timestamp'].iloc[i])
    
    current_state = states[-1]
    current_spread = spreads[-1]
    current_direction = directions[-1]
    
    transitions = detect_state_transitions(states, timestamps)
    retracement_events = analyze_retracement_history(df, jaw, teeth, lips, current_direction)
    
    latest = df.iloc[-1]
    
    return {
        'symbol': symbol,
        'timestamp': latest['timestamp'],
        'datetime': latest['datetime'],
        'price': latest['close'],
        'alligator_state': current_state,
        'trend_direction': current_direction,
        'line_spread_pct': current_spread,
        'jaw_value': latest['jaw'],
        'teeth_value': latest['teeth'],
        'lips_value': latest['lips'],
        'transitions': transitions or [],
        'retracement_events': retracement_events,
        'quality_score': max([t['strength'] for t in (transitions or [])] + 
                           [r['strength'] for r in retracement_events] + [0])
    }

def main():
    """Main Alligator analysis function"""
    print("Wind Catcher & River Turn - Modified Alligator Analysis")
    print("="*70)
    print("Detecting sleep/awake states and retracement opportunities...")
    print("-"*70)
    
    conn = connect_to_database()
    
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
    watchlist = [row[0] for row in cursor.fetchall()]
    
    all_results = []
    
    for symbol in watchlist:
        print(f"\n{symbol}:")
        
        result = analyze_symbol_alligator(conn, symbol)
        if result:
            state_emoji = "😴" if result['alligator_state'] == 'sleeping' else "👁️"
            direction_emoji = {"bullish": "🟢", "bearish": "🔴", "mixed": "🟡", "none": "⚪"}[result['trend_direction']]
            
            print(f"  Price: ${result['price']:.4f}")
            print(f"  {state_emoji} State: {result['alligator_state'].upper()}")
            print(f"  {direction_emoji} Direction: {result['trend_direction'].upper()}")
            print(f"  📏 Line Spread: {result['line_spread_pct']:.2f}%")
            
            if pd.notna(result['jaw_value']):
                print(f"  🔵 Jaw (Blue): ${result['jaw_value']:.4f}")
                print(f"  🟢 Teeth (Green): ${result['teeth_value']:.4f}")  
                print(f"  🔴 Lips (Red): ${result['lips_value']:.4f}")
            
            if result['transitions']:
                print(f"  🚨 TRANSITIONS:")
                for transition in result['transitions']:
                    trigger_time = datetime.fromtimestamp(transition['trigger_timestamp']).strftime('%H:%M')
                    print(f"    {transition['description']} (Strength: {transition['strength']:.1f})")
                    print(f"    ⏰ Triggered: {transition['hours_ago']:.1f}h ago at {trigger_time}")
                
                all_results.append(result)
            
            if result['retracement_events']:
                print(f"  🎯 RETRACEMENT EVENTS:")
                for event in result['retracement_events']:
                    event_time = datetime.fromtimestamp(event['timestamp']).strftime('%H:%M')
                    
                    if event['type'] == 'zone_entry':
                        emoji = "🟡"
                    elif event['type'] == 'blue_line_contact':
                        emoji = "🔴"
                    elif event['type'] == 'zone_exit':
                        emoji = "↗️" if event['direction'] == 'upward' else "↘️"
                    else:
                        emoji = "📍"
                    
                    print(f"    {emoji} {event['description']}")
                    print(f"       ⏰ {event['hours_ago']:.1f}h ago at {event_time} | Price: ${event['price']:.4f}")
                
                all_results.append(result)
            
            if not result['transitions'] and not result['retracement_events']:
                print(f"  ✅ No signals - monitoring...")
        
        else:
            print(f"  ❌ Insufficient data")
    
    if all_results:
        print(f"\n🎯 ALLIGATOR SIGNALS SUMMARY ({len(all_results)} symbols)")
        print("="*70)
        
        transition_signals = [r for r in all_results if r['transitions']]
        retracement_signals = [r for r in all_results if r['retracement_events']]
        
        if transition_signals:
            print("🔄 STATE TRANSITIONS:")
            for result in transition_signals:
                for transition in result['transitions']:
                    significance_emoji = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}[transition['significance']]
                    trigger_time = datetime.fromtimestamp(transition['trigger_timestamp']).strftime('%H:%M')
                    print(f"  {significance_emoji} {result['symbol']:12s} - {transition['description']}")
                    print(f"      ⏰ Triggered {transition['hours_ago']:.1f}h ago at {trigger_time}")
        
        if retracement_signals:
            print("\n🎯 RETRACEMENT EVENTS:")
            for result in retracement_signals:
                for event in result['retracement_events']:
                    event_time = datetime.fromtimestamp(event['timestamp']).strftime('%H:%M')
                    
                    if event['type'] == 'blue_line_contact':
                        priority_emoji = "⭐"
                    elif event['type'] == 'zone_entry':
                        priority_emoji = "✨"
                    elif event['type'] == 'zone_exit':
                        priority_emoji = "↗️" if event['direction'] == 'upward' else "↘️"
                    else:
                        priority_emoji = "💡"
                    
                    print(f"  {priority_emoji} {result['symbol']:12s} - {event['description']}")
                    print(f"      ⏰ {event['hours_ago']:.1f}h ago at {event_time}")
    
    else:
        print(f"\n✅ No Alligator signals detected")
    
    conn.close()
    print(f"\n🎯 Alligator analysis complete!")

if __name__ == "__main__":
    main()