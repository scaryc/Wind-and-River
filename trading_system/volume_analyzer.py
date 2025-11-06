"""
Volume Climax Detector for Wind Catcher & River Turn Trading System
Based on your trading philosophy:
- Baseline: 5-day rolling average volume
- Monitor: Last 3-hour candles 
- Alert Gradients: 1.5x, 2x, 3x average
"""

import pandas as pd
import numpy as np
import sqlite3
import yaml
from datetime import datetime, timedelta

def load_config():
    """Load configuration"""
    with open('config/config.yaml', 'r') as file:
        return yaml.safe_load(file)

def connect_to_database():
    """Connect to database"""
    return sqlite3.connect('data/trading_system.db')

def get_volume_data(conn, symbol, timeframe='1h', days_back=7):
    """Get volume data for analysis"""
    # Calculate timestamp for X days ago
    days_ago = datetime.now() - timedelta(days=days_back)
    timestamp_limit = int(days_ago.timestamp())
    
    query = '''
        SELECT timestamp, volume, close
        FROM price_data 
        WHERE symbol = ? AND timeframe = ? AND timestamp >= ?
        ORDER BY timestamp ASC
    '''
    
    df = pd.read_sql_query(query, conn, params=(symbol, timeframe, timestamp_limit))
    
    if df.empty:
        return None
        
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
    return df

def calculate_volume_baseline(df, baseline_hours=120):  # 5 days = 120 hours
    """Calculate 5-day rolling average volume baseline"""
    if len(df) < baseline_hours:
        # Use available data if we don't have full 5 days
        baseline_hours = max(24, len(df) // 2)  # At least 24 hours
    
    df['volume_baseline'] = df['volume'].rolling(window=baseline_hours, min_periods=24).mean()
    return df

def detect_volume_climax(df, monitoring_candles=3):
    """
    Detect volume climax based on your specifications:
    - 1.5x average = "Warming up"
    - 2.0x average = "Hot" 
    - 3.0x average = "Climax"
    """
    if len(df) < monitoring_candles:
        return None
    
    # Get the last X candles for monitoring
    recent_data = df.tail(monitoring_candles).copy()
    
    volume_signals = []
    
    for idx, row in recent_data.iterrows():
        if pd.isna(row['volume_baseline']):
            continue
            
        volume_ratio = row['volume'] / row['volume_baseline']
        timestamp = row['timestamp']
        datetime_str = row['datetime'].strftime('%H:%M')
        
        # Determine volume level
        if volume_ratio >= 3.0:
            level = "CLIMAX"
            strength = 1.0
            emoji = "🔥"
        elif volume_ratio >= 2.0:
            level = "HOT"
            strength = 0.8
            emoji = "🌡️"
        elif volume_ratio >= 1.5:
            level = "WARMING"
            strength = 0.6
            emoji = "📈"
        else:
            level = "NORMAL"
            strength = 0.2
            emoji = "📊"
        
        volume_signals.append({
            'timestamp': timestamp,
            'datetime': datetime_str,
            'volume': row['volume'],
            'baseline': row['volume_baseline'],
            'ratio': volume_ratio,
            'level': level,
            'strength': strength,
            'emoji': emoji
        })
    
    return volume_signals

def analyze_volume_patterns(volume_signals):
    """Analyze volume patterns for trading signals"""
    if not volume_signals or len(volume_signals) < 2:
        return None
    
    patterns = []
    
    # Check for escalating volume (building climax)
    if len(volume_signals) >= 3:
        ratios = [sig['ratio'] for sig in volume_signals]
        if ratios[-1] > ratios[-2] > ratios[-3]:  # Increasing volume
            patterns.append({
                'type': 'escalating_volume',
                'description': 'Volume building toward climax',
                'strength': 0.7,
                'significance': 'High'
            })
    
    # Check for volume spike (sudden climax)
    latest = volume_signals[-1]
    if latest['ratio'] >= 2.5:  # Hot or Climax level
        patterns.append({
            'type': 'volume_spike',
            'description': f"Volume spike: {latest['ratio']:.1f}x average",
            'strength': min(1.0, latest['ratio'] / 3.0),
            'significance': 'Critical'
        })
    
    # Check for sustained high volume
    high_volume_count = sum(1 for sig in volume_signals if sig['ratio'] >= 1.5)
    if high_volume_count >= 2:
        patterns.append({
            'type': 'sustained_volume',
            'description': f'{high_volume_count} periods of elevated volume',
            'strength': 0.6,
            'significance': 'Medium'
        })
    
    return patterns if patterns else None

def analyze_symbol_volume(conn, symbol, timeframe='1h'):
    """Analyze volume for a single symbol"""
    
    # Get volume data
    df = get_volume_data(conn, symbol, timeframe, days_back=7)
    if df is None or len(df) < 24:
        return None
    
    # Calculate baseline
    df = calculate_volume_baseline(df)
    
    # Detect volume climax
    volume_signals = detect_volume_climax(df, monitoring_candles=3)
    if not volume_signals:
        return None
    
    # Analyze patterns
    patterns = analyze_volume_patterns(volume_signals)
    
    # Get latest price for context
    latest_price = df['close'].iloc[-1]
    latest_volume_signal = volume_signals[-1]
    
    return {
        'symbol': symbol,
        'latest_price': latest_price,
        'volume_signals': volume_signals,
        'patterns': patterns,
        'current_level': latest_volume_signal['level'],
        'current_ratio': latest_volume_signal['ratio']
    }

def main():
    """Main volume analysis function"""
    print("🚀 Wind Catcher & River Turn - Volume Climax Detector")
    print("="*60)
    
    # Connect to database
    conn = connect_to_database()
    
    # Get watchlist
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
    watchlist = [row[0] for row in cursor.fetchall()]
    
    print(f"📊 Analyzing volume patterns for {len(watchlist)} symbols...")
    print("-" * 60)
    
    volume_alerts = []
    
    for symbol in watchlist:
        print(f"\n📈 {symbol}:")
        
        result = analyze_symbol_volume(conn, symbol)
        if result:
            print(f"  Price: ${result['latest_price']:.4f}")
            print(f"  Current Volume Level: {result['current_level']} ({result['current_ratio']:.1f}x)")
            
            # Show recent volume signals
            print(f"  Last 3 Volume Readings:")
            for vol_sig in result['volume_signals']:
                print(f"    {vol_sig['datetime']}: {vol_sig['emoji']} {vol_sig['level']} "
                      f"({vol_sig['ratio']:.1f}x avg)")
            
            # Show patterns if detected
            if result['patterns']:
                print(f"  🚨 VOLUME PATTERNS:")
                for pattern in result['patterns']:
                    print(f"    🔍 {pattern['description']} "
                          f"(Strength: {pattern['strength']:.1f}, {pattern['significance']})")
                
                # Add to alerts if significant
                if any(p['significance'] in ['High', 'Critical'] for p in result['patterns']):
                    volume_alerts.append(result)
            
            else:
                print(f"  ✅ No significant volume patterns")
        else:
            print(f"  ❌ Insufficient volume data")
    
    # Summary of volume alerts
    if volume_alerts:
        print(f"\n🎯 VOLUME ALERTS SUMMARY ({len(volume_alerts)} total):")
        print("-" * 60)
        for alert in volume_alerts:
            level_emoji = {"CLIMAX": "🔥", "HOT": "🌡️", "WARMING": "📈"}.get(
                alert['current_level'], "📊"
            )
            print(f"  {level_emoji} {alert['symbol']:12s} - {alert['current_level']} "
                  f"({alert['current_ratio']:.1f}x avg)")
            
            if alert['patterns']:
                for pattern in alert['patterns']:
                    if pattern['significance'] in ['High', 'Critical']:
                        print(f"    └─ {pattern['description']}")
    else:
        print(f"\n✅ No significant volume alerts - normal market activity")
    
    conn.close()
    print("\n🎯 Volume analysis complete!")

if __name__ == "__main__":
    main()