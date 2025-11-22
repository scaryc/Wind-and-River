"""
Complete Trading Dashboard for Wind Catcher & River Turn System
Your daily morning script - shows everything at once
"""

import sys
import io

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
import sqlite3
import yaml
from datetime import datetime, timedelta
import time

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

def analyze_complete_symbol(conn, symbol):
    """Complete analysis for one symbol"""
    df = get_price_data(conn, symbol, timeframe='1h', limit=100)
    if df is None or len(df) < 50:
        return None
    
    # Calculate indicators
    df['hull_21'] = calculate_hull_ma(df['close'], 21)
    df['hull_34'] = calculate_hull_ma(df['close'], 34)
    
    # Volume analysis
    baseline_periods = min(120, len(df))
    df['volume_baseline'] = df['volume'].rolling(window=baseline_periods, min_periods=24).mean()
    
    # Get latest values
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    # Hull signals
    hull_signals = []
    if pd.notna(latest['hull_21']) and pd.notna(prev['hull_21']):
        # Bullish break
        if latest['close'] > latest['hull_21'] and prev['close'] <= prev['hull_21']:
            hull_signals.append({
                'type': 'wind_catcher',
                'description': 'First close above Hull 21',
                'strength': 0.7
            })
        # Bearish break
        elif latest['close'] < latest['hull_21'] and prev['close'] >= prev['hull_21']:
            hull_signals.append({
                'type': 'river_turn', 
                'description': 'First close below Hull 21',
                'strength': 0.7
            })
    
    # Volume analysis
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
    
    # Calculate confluence
    confluence_score = 0
    if hull_signals:
        confluence_score += hull_signals[0]['strength']
    confluence_score += volume_strength
    
    # Volume confirmation bonus
    if volume_ratio >= 1.5:
        confluence_score += 0.3
    
    # Classify confluence
    if confluence_score >= 1.8:
        confluence_class = "PERFECT"
        conf_emoji = "⭐"
    elif confluence_score >= 1.2:
        confluence_class = "GOOD"
        conf_emoji = "✨"
    elif confluence_score >= 0.8:
        confluence_class = "INTERESTING"
        conf_emoji = "💡"
    else:
        confluence_class = "NONE"
        conf_emoji = "✅"
    
    # Hull MA trend analysis
    hull_21_trend = "BULLISH" if latest['close'] > latest['hull_21'] else "BEARISH"
    hull_trend_emoji = "🟢" if hull_21_trend == "BULLISH" else "🔴"
    
    return {
        'symbol': symbol,
        'timestamp': latest['timestamp'],
        'datetime': latest['datetime'],
        'price': latest['close'],
        'price_change_24h': ((latest['close'] - df['close'].iloc[-25]) / df['close'].iloc[-25] * 100) if len(df) >= 25 else 0,
        'hull_21': latest['hull_21'],
        'hull_21_trend': hull_21_trend,
        'hull_signals': hull_signals,
        'volume_level': volume_level,
        'volume_ratio': volume_ratio,
        'volume_emoji': volume_emoji,
        'confluence_score': confluence_score,
        'confluence_class': confluence_class,
        'conf_emoji': conf_emoji,
        'hull_trend_emoji': hull_trend_emoji
    }

def print_market_overview(results):
    """Print market overview section"""
    print("📊 MARKET OVERVIEW")
    print("="*80)
    
    for result in results:
        if result:
            change_str = f"{result['price_change_24h']:+.1f}%" if result['price_change_24h'] != 0 else "0.0%"
            change_color = "🟢" if result['price_change_24h'] > 0 else "🔴" if result['price_change_24h'] < 0 else "⚪"
            
            print(f"{result['symbol']:12s} ${result['price']:>10.4f} {change_color}{change_str:>6s} "
                  f"{result['hull_trend_emoji']} {result['volume_emoji']} {result['conf_emoji']}")

def print_active_signals(results):
    """Print active signals section"""
    signals = [r for r in results if r and r['hull_signals']]
    
    print(f"\n🚨 ACTIVE SIGNALS ({len(signals)})")
    print("="*80)
    
    if signals:
        for result in signals:
            for signal in result['hull_signals']:
                system_emoji = "🌪️" if signal['type'] == 'wind_catcher' else "🌊"
                time_str = result['datetime'].strftime('%H:%M')
                
                print(f"{system_emoji} {result['symbol']:12s} ${result['price']:>10.4f} - {signal['description']}")
                print(f"   {result['volume_emoji']} Volume: {result['volume_level']} ({result['volume_ratio']:.1f}x)")
                print(f"   {result['conf_emoji']} Confluence: {result['confluence_class']} (Score: {result['confluence_score']:.1f}) at {time_str}")
                print()
    else:
        print("✅ No active Hull MA signals detected")

def print_volume_alerts(results):
    """Print volume alerts section"""
    volume_alerts = [r for r in results if r and r['volume_ratio'] >= 1.5]
    
    print(f"🌡️ VOLUME ALERTS ({len(volume_alerts)})")
    print("="*80)
    
    if volume_alerts:
        for result in volume_alerts:
            print(f"{result['volume_emoji']} {result['symbol']:12s} ${result['price']:>10.4f} - "
                  f"{result['volume_level']} ({result['volume_ratio']:.1f}x average)")
    else:
        print("📊 All volumes normal - no elevated activity")

def print_confluence_summary(results):
    """Print confluence signals summary"""
    high_conf = [r for r in results if r and r['confluence_class'] in ['PERFECT', 'GOOD']]
    medium_conf = [r for r in results if r and r['confluence_class'] == 'INTERESTING']
    
    print(f"\n🎯 CONFLUENCE SUMMARY")
    print("="*80)
    
    if high_conf:
        print("🚨 HIGH CONFIDENCE SETUPS:")
        for result in high_conf:
            if result['hull_signals']:
                system_emoji = "🌪️" if result['hull_signals'][0]['type'] == 'wind_catcher' else "🌊"
                print(f"  {result['conf_emoji']} {system_emoji} {result['symbol']:12s} - "
                      f"{result['confluence_class']} (Score: {result['confluence_score']:.1f})")
    
    if medium_conf:
        print("💡 DEVELOPING SETUPS:")
        for result in medium_conf:
            if result['hull_signals']:
                system_emoji = "🌪️" if result['hull_signals'][0]['type'] == 'wind_catcher' else "🌊"
                print(f"  {result['conf_emoji']} {system_emoji} {result['symbol']:12s} - "
                      f"Watch for volume confirmation")
    
    if not high_conf and not medium_conf:
        print("✅ No confluence signals - normal market monitoring")

def print_trading_recommendations(results):
    """Print trading recommendations"""
    print(f"\n📋 TRADING RECOMMENDATIONS")
    print("="*80)
    
    perfect_signals = [r for r in results if r and r['confluence_class'] == 'PERFECT']
    good_signals = [r for r in results if r and r['confluence_class'] == 'GOOD']
    watch_signals = [r for r in results if r and r['confluence_class'] == 'INTERESTING']
    
    if perfect_signals:
        print("⭐ EXECUTE NOW (Perfect Confluence):")
        for result in perfect_signals:
            if result['hull_signals']:
                action = "LONG" if result['hull_signals'][0]['type'] == 'wind_catcher' else "SHORT"
                print(f"   → Consider {action} position on {result['symbol']} at ${result['price']:.4f}")
    
    if good_signals:
        print("✨ HIGH PROBABILITY (Good Confluence):")
        for result in good_signals:
            if result['hull_signals']:
                action = "LONG" if result['hull_signals'][0]['type'] == 'wind_catcher' else "SHORT"
                print(f"   → Prepare {action} setup on {result['symbol']} at ${result['price']:.4f}")
    
    if watch_signals:
        print("💡 MONITOR CLOSELY (Developing):")
        for result in watch_signals:
            if result['hull_signals']:
                print(f"   → Watch {result['symbol']} for volume confirmation")
    
    if not any([perfect_signals, good_signals, watch_signals]):
        print("✅ No immediate action required - continue monitoring")

def analyze_multi_timeframe(conn, symbol, timeframes=['3m', '5m', '30m', '1h', '2h', '4h']):
    """Analyze symbol across multiple timeframes"""
    results = {}

    for tf in timeframes:
        df = get_price_data(conn, symbol, timeframe=tf, limit=100)
        if df is None or len(df) < 50:
            results[tf] = None
            continue

        # Calculate indicators
        df['hull_21'] = calculate_hull_ma(df['close'], 21)

        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        # Hull signals
        signal_type = None
        if pd.notna(latest['hull_21']) and pd.notna(prev['hull_21']):
            if latest['close'] > latest['hull_21'] and prev['close'] <= prev['hull_21']:
                signal_type = 'BULLISH'
            elif latest['close'] < latest['hull_21'] and prev['close'] >= prev['hull_21']:
                signal_type = 'BEARISH'

        # Current trend
        trend = "BULLISH" if latest['close'] > latest['hull_21'] else "BEARISH"

        results[tf] = {
            'timeframe': tf,
            'price': latest['close'],
            'hull_21': latest['hull_21'],
            'trend': trend,
            'signal': signal_type
        }

    return results

def print_multi_timeframe_overview(conn, symbols, timeframes=['3m', '5m', '30m', '1h', '2h', '4h']):
    """Print multi-timeframe overview for all symbols"""
    print("\n📊 MULTI-TIMEFRAME OVERVIEW")
    print("="*80)

    # Header
    header = f"{'Symbol':<12}"
    for tf in timeframes:
        header += f"{tf:>8}"
    print(header)
    print("-"*80)

    for symbol in symbols:
        mtf_results = analyze_multi_timeframe(conn, symbol, timeframes)

        # Symbol row
        row = f"{symbol:<12}"
        for tf in timeframes:
            if mtf_results.get(tf):
                if mtf_results[tf]['signal'] == 'BULLISH':
                    row += "     🌪️ "
                elif mtf_results[tf]['signal'] == 'BEARISH':
                    row += "     🌊 "
                elif mtf_results[tf]['trend'] == 'BULLISH':
                    row += "     🟢 "
                else:
                    row += "     🔴 "
            else:
                row += "      - "
        print(row)

    print("\nLegend: 🌪️=Bullish Signal | 🌊=Bearish Signal | 🟢=Bullish Trend | 🔴=Bearish Trend")

def print_timeframe_alignment(conn, symbols, timeframes=['3m', '5m', '30m', '1h', '2h', '4h']):
    """Print symbols with multi-timeframe alignment"""
    print("\n🎯 TIMEFRAME ALIGNMENT (Confluence Across TFs)")
    print("="*80)

    alignments = []

    for symbol in symbols:
        mtf_results = analyze_multi_timeframe(conn, symbol, timeframes)

        bullish_count = sum(1 for tf in timeframes if mtf_results.get(tf) and mtf_results[tf]['trend'] == 'BULLISH')
        bearish_count = sum(1 for tf in timeframes if mtf_results.get(tf) and mtf_results[tf]['trend'] == 'BEARISH')

        if bullish_count >= 4:
            alignments.append({
                'symbol': symbol,
                'direction': 'BULLISH',
                'count': bullish_count,
                'emoji': '🌪️'
            })
        elif bearish_count >= 4:
            alignments.append({
                'symbol': symbol,
                'direction': 'BEARISH',
                'count': bearish_count,
                'emoji': '🌊'
            })

    if alignments:
        for align in alignments:
            print(f"{align['emoji']} {align['symbol']:<12} {align['direction']:<7} - {align['count']}/{len(timeframes)} timeframes aligned")
    else:
        print("⚠️  No strong multi-timeframe alignment detected")

def main():
    """Main dashboard function"""
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # New timeframes for day trading
    TIMEFRAMES = ['3m', '5m', '30m', '1h', '2h', '4h']

    print("🚀 WIND CATCHER & RIVER TURN TRADING SYSTEM")
    print("="*80)
    print(f"📅 {current_time} | Multi-Timeframe Analysis")
    print(f"⏱️  Timeframes: {', '.join(TIMEFRAMES)}")
    print("="*80)

    # Connect to database
    conn = connect_to_database()

    # Get watchlist
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT symbol FROM watchlist WHERE active = 1")
    watchlist = [row[0] for row in cursor.fetchall()]

    # Normalize symbols
    normalized_watchlist = []
    for symbol in watchlist:
        if '/' in symbol:
            normalized_watchlist.append(symbol.split('/')[0])
        else:
            normalized_watchlist.append(symbol)

    print(f"📈 Analyzing {len(normalized_watchlist)} symbols: {', '.join(normalized_watchlist)}")
    print("-"*80)

    # Multi-timeframe overview
    print_multi_timeframe_overview(conn, normalized_watchlist, TIMEFRAMES)

    # Timeframe alignment
    print_timeframe_alignment(conn, normalized_watchlist, TIMEFRAMES)

    # Analyze 1h timeframe for detailed signals (compatibility with old dashboard)
    results = []
    for symbol in normalized_watchlist:
        result = analyze_complete_symbol(conn, symbol)
        results.append(result)
        time.sleep(0.1)  # Small delay

    # Print detailed sections for 1h
    print("\n" + "="*80)
    print("📊 DETAILED 1H ANALYSIS")
    print("="*80)
    print_active_signals(results)
    print_volume_alerts(results)
    print_confluence_summary(results)
    print_trading_recommendations(results)

    # Footer
    print("\n" + "="*80)
    print("🎯 Analysis complete! System monitoring continues...")
    print("💡 Tip: Run this dashboard regularly to check for multi-timeframe setups")
    print("💡 Collecting data every 1 minute - optimized for day trading")
    print("="*80)

    conn.close()

if __name__ == "__main__":
    main()