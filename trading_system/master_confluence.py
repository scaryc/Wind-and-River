"""
Master Confluence System for Wind Catcher & River Turn
Imports from dedicated analyzer files to maintain modular architecture
"""

import pandas as pd
import numpy as np
from datetime import datetime
from utils import load_config, connect_to_database

# Import analyzer modules properly
try:
    import enhanced_hull_analyzer
    import enhanced_indicators
    import alligator_analyzer
    import ichimoku_analyzer
except ImportError as e:
    print(f"❌ Error importing analyzer modules: {e}")
    print("   Make sure all analyzer files are in the same directory")
    raise

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

# Analyzer wrapper functions with proper error handling
def get_hull_signals(conn, symbol):
    """Get Hull MA signals from enhanced_hull_analyzer"""
    try:
        result = enhanced_hull_analyzer.analyze_symbol_hull(conn, symbol)
        return result['all_signals'] if result else []
    except Exception as e:
        print(f"⚠️ Error getting Hull signals for {symbol}: {e}")
        return []

def get_ao_signals(conn, symbol):
    """Get AO divergence signals from enhanced_indicators"""
    try:
        result = enhanced_indicators.analyze_symbol_with_ao(conn, symbol)
        if result and result.get('ao_analysis', {}).get('divergences'):
            signals = []
            for div in result['ao_analysis']['divergences']:
                signals.append({
                    'type': div['type'],
                    'system': 'wind_catcher' if 'bullish' in div['type'] else 'river_turn',
                    'description': div['description'],
                    'strength': div['strength']
                })
            return signals
        return []
    except Exception as e:
        print(f"⚠️ Error getting AO signals for {symbol}: {e}")
        return []

def get_alligator_signals(conn, symbol):
    """Get Alligator signals from alligator_analyzer"""
    try:
        result = alligator_analyzer.analyze_symbol_alligator(conn, symbol)
        if result and result.get('retracement_events'):
            signals = []
            for event in result['retracement_events']:
                if event['type'] in ['blue_line_contact', 'zone_entry']:
                    system = 'wind_catcher' if 'bullish' in event.get('description', '') else 'river_turn'
                    signals.append({
                        'type': f"alligator_{event['type']}",
                        'system': system,
                        'description': event['description'],
                        'strength': event['strength']
                    })
            return signals
        return []
    except Exception as e:
        print(f"⚠️ Error getting Alligator signals for {symbol}: {e}")
        return []

def get_ichimoku_signals(conn, symbol):
    """Get Ichimoku signals from ichimoku_analyzer"""
    try:
        result = ichimoku_analyzer.analyze_symbol_ichimoku(conn, symbol)
        if result and result.get('significant_events'):
            signals = []
            for event in result['significant_events']:
                if event['type'] == 'kijun_touch':
                    system = 'wind_catcher' if event['touch_type'] == 'support' else 'river_turn'
                elif event['type'] == 'cloud_retest':
                    system = 'wind_catcher' if 'green' in event.get('cloud_color', '') else 'river_turn'
                else:
                    system = 'wind_catcher'

                signals.append({
                    'type': event['type'],
                    'system': system,
                    'description': event['description'],
                    'strength': event['strength']
                })
            return signals
        return []
    except Exception as e:
        print(f"⚠️ Error getting Ichimoku signals for {symbol}: {e}")
        return []

def detect_volume_signals(df, monitoring_candles=3):
    """Detect volume signals"""
    if len(df) < 24:
        return []
    
    baseline_periods = min(120, len(df))
    df['volume_baseline'] = df['volume'].rolling(window=baseline_periods, min_periods=24).mean()
    
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

def calculate_master_confluence(hull_signals, ao_signals, alligator_signals, ichimoku_signals, volume_signals):
    """Calculate master confluence score from all indicators"""
    total_score = 0
    confluence_factors = []
    primary_system = None
    signal_count = 0
    
    # Hull MA signals
    for signal in hull_signals:
        total_score += signal['strength']
        confluence_factors.append(signal['description'])
        signal_count += 1
        if not primary_system:
            primary_system = signal['system']
    
    # AO divergences
    for signal in ao_signals:
        total_score += signal['strength']
        confluence_factors.append(signal['description'])
        signal_count += 1
        if not primary_system:
            primary_system = signal['system']
    
    # Alligator signals
    for signal in alligator_signals:
        total_score += signal['strength']
        confluence_factors.append(signal['description'])
        signal_count += 1
        if not primary_system:
            primary_system = signal['system']
    
    # Ichimoku signals
    for signal in ichimoku_signals:
        total_score += signal['strength']
        confluence_factors.append(signal['description'])
        signal_count += 1
        if not primary_system:
            primary_system = signal['system']
    
    # Volume confirmation
    if volume_signals:
        latest_volume = volume_signals[-1]
        total_score += latest_volume['strength']
        confluence_factors.append(f"Volume: {latest_volume['level']}")
        
        # Volume confirmation bonus
        if latest_volume['ratio'] >= 1.5:
            total_score += 0.3
            confluence_factors.append("Volume confirmation bonus")
    
    # Enhanced classification with higher thresholds for multi-indicator confluence
    if total_score >= 3.0:
        confluence_class = "PERFECT"
        conf_emoji = "⭐"
    elif total_score >= 2.5:
        confluence_class = "EXCELLENT"
        conf_emoji = "🌟"
    elif total_score >= 1.8:
        confluence_class = "VERY GOOD"
        conf_emoji = "✨"
    elif total_score >= 1.2:
        confluence_class = "GOOD"
        conf_emoji = "💫"
    elif total_score >= 0.8:
        confluence_class = "INTERESTING"
        conf_emoji = "💡"
    else:
        confluence_class = "WEAK"
        conf_emoji = "🔍"
    
    return {
        'score': total_score,
        'classification': confluence_class,
        'emoji': conf_emoji,
        'factors': confluence_factors,
        'primary_system': primary_system,
        'signal_count': signal_count
    }

def analyze_master_confluence(conn, symbol):
    """Master confluence analysis combining all indicators"""
    df = get_price_data(conn, symbol, timeframe='1h', limit=200)
    if df is None or len(df) < 150:
        return None
    
    # Get signals from all dedicated analyzers
    hull_signals = get_hull_signals(conn, symbol)
    ao_signals = get_ao_signals(conn, symbol)
    alligator_signals = get_alligator_signals(conn, symbol)
    ichimoku_signals = get_ichimoku_signals(conn, symbol)
    volume_signals = detect_volume_signals(df.copy())
    
    # Calculate master confluence
    confluence = calculate_master_confluence(
        hull_signals, ao_signals, alligator_signals, ichimoku_signals, volume_signals
    )
    
    # Get latest values
    latest = df.iloc[-1]
    
    return {
        'symbol': symbol,
        'timestamp': latest['timestamp'],
        'datetime': latest['datetime'],
        'price': latest['close'],
        'hull_signals': hull_signals,
        'ao_signals': ao_signals,
        'alligator_signals': alligator_signals,
        'ichimoku_signals': ichimoku_signals,
        'volume_signals': volume_signals,
        'confluence': confluence
    }

def main():
    """Main master confluence analysis"""
    print("Wind Catcher & River Turn - Master Confluence System")
    print("="*80)
    print("Combining Hull + AO + Alligator + Ichimoku + Volume Analysis")
    print("-"*80)

    try:
        conn = connect_to_database()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT symbol FROM watchlist WHERE active = 1")
        watchlist = [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
    
    results = []
    
    for symbol in watchlist:
        print(f"\n{symbol}:")
        
        result = analyze_master_confluence(conn, symbol)
        if result:
            confluence = result['confluence']
            
            print(f"  Price: ${result['price']:.4f}")
            print(f"  {confluence['emoji']} Confluence: {confluence['classification']} (Score: {confluence['score']:.1f})")
            print(f"  Signals: {confluence['signal_count']} indicators active")
            
            # Show signals by category
            if result['hull_signals']:
                print(f"    Hull MA: {len(result['hull_signals'])} signals")
                for signal in result['hull_signals']:
                    system_emoji = "🌪️" if signal['system'] == 'wind_catcher' else "🌊"
                    print(f"      {system_emoji} {signal['description']}")
            
            if result['ao_signals']:
                print(f"    AO Divergence: {len(result['ao_signals'])} signals")
                for signal in result['ao_signals']:
                    system_emoji = "🌪️" if signal['system'] == 'wind_catcher' else "🌊"
                    print(f"      {system_emoji} {signal['description']}")
            
            if result['alligator_signals']:
                print(f"    Alligator: {len(result['alligator_signals'])} signals")
                for signal in result['alligator_signals']:
                    system_emoji = "🌪️" if signal['system'] == 'wind_catcher' else "🌊"
                    print(f"      {system_emoji} {signal['description']}")
            
            if result['ichimoku_signals']:
                print(f"    Ichimoku: {len(result['ichimoku_signals'])} signals")
                for signal in result['ichimoku_signals']:
                    system_emoji = "🌪️" if signal['system'] == 'wind_catcher' else "🌊"
                    print(f"      {system_emoji} {signal['description']}")
            
            # Show volume context
            if result['volume_signals']:
                latest_vol = result['volume_signals'][-1]
                vol_emoji = {"CLIMAX": "🔥", "HOT": "🌡️", "WARMING": "📈", "NORMAL": "📊"}[latest_vol['level']]
                print(f"    {vol_emoji} Volume: {latest_vol['level']} ({latest_vol['ratio']:.1f}x)")
            
            if confluence['signal_count'] > 0:
                results.append(result)
        
        else:
            print(f"  ❌ Insufficient data")
    
    # Master Summary
    if results:
        print(f"\n🎯 MASTER CONFLUENCE SUMMARY ({len(results)} symbols)")
        print("="*80)
        
        # Sort by confluence score
        results.sort(key=lambda x: x['confluence']['score'], reverse=True)
        
        for result in results:
            confluence = result['confluence']
            system_emoji = "🌪️" if confluence['primary_system'] == 'wind_catcher' else "🌊"
            time_str = result['datetime'].strftime('%H:%M')
            
            print(f"\n{confluence['emoji']} {system_emoji} {result['symbol']:12s} "
                  f"${result['price']:.4f} - {confluence['classification']} "
                  f"(Score: {confluence['score']:.1f}) at {time_str}")
            print(f"    {confluence['signal_count']} indicators firing")
            
            # Show breakdown by indicator type
            indicator_breakdown = []
            if result['hull_signals']:
                indicator_breakdown.append(f"Hull({len(result['hull_signals'])})")
            if result['ao_signals']:
                indicator_breakdown.append(f"AO({len(result['ao_signals'])})")
            if result['alligator_signals']:
                indicator_breakdown.append(f"Alligator({len(result['alligator_signals'])})")
            if result['ichimoku_signals']:
                indicator_breakdown.append(f"Ichimoku({len(result['ichimoku_signals'])})")
            
            if indicator_breakdown:
                print(f"    Breakdown: {', '.join(indicator_breakdown)}")
    
    else:
        print(f"\n✅ No confluence signals detected")
    
    conn.close()
    print(f"\n🎯 Master confluence analysis complete!")
    print("🔧 Note: Using modular imports from dedicated analyzer files")

if __name__ == "__main__":
    main()