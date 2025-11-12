"""
Backtest Report Generator
Creates readable Markdown report for manual signal review
"""

import sqlite3
import json
from datetime import datetime
from master_confluence import connect_to_database


def get_backtest_signals(conn, start_date='2024-10-03', end_date='2024-11-03'):
    """Get all signals from backtest period"""
    query = '''
        SELECT *
        FROM signals
        WHERE timestamp >= ? AND timestamp <= ?
        ORDER BY confluence_score DESC, timestamp DESC
    '''

    start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp())
    end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp())

    cursor = conn.cursor()
    cursor.execute(query, (start_ts, end_ts))

    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    signals = []
    for row in rows:
        signal = dict(zip(columns, row))

        # Parse JSON fields
        if signal.get('indicators_firing'):
            try:
                signal['indicators_firing'] = json.loads(signal['indicators_firing'])
            except:
                signal['indicators_firing'] = {}

        signals.append(signal)

    return signals


def generate_summary_section(signals):
    """Generate summary section of report"""
    total_signals = len(signals)

    # Count by symbol
    by_symbol = {}
    for signal in signals:
        symbol = signal['symbol']
        direction = signal['system']

        if symbol not in by_symbol:
            by_symbol[symbol] = {'total': 0, 'bullish': 0, 'bearish': 0}

        by_symbol[symbol]['total'] += 1
        if direction == 'wind_catcher':
            by_symbol[symbol]['bullish'] += 1
        else:
            by_symbol[symbol]['bearish'] += 1

    # Count by confluence class
    by_class = {}
    for signal in signals:
        cls = signal['confluence_class']
        by_class[cls] = by_class.get(cls, 0) + 1

    # Generate markdown
    md = []
    md.append("## SUMMARY\n")
    md.append(f"**Total Signals**: {total_signals}\n")

    # By symbol
    md.append("\n### Signals by Symbol\n")
    for symbol, counts in sorted(by_symbol.items()):
        md.append(f"- **{symbol}**: {counts['total']} signals "
                  f"({counts['bullish']} bullish 🌪️, {counts['bearish']} bearish 🌊)")

    # By confluence class
    md.append("\n### Signals by Confluence Level\n")
    for cls in ['PERFECT', 'EXCELLENT', 'VERY GOOD', 'GOOD', 'INTERESTING']:
        count = by_class.get(cls, 0)
        if count > 0:
            if cls == 'PERFECT':
                emoji = "⭐"
                range_str = "(≥3.0)"
            elif cls == 'EXCELLENT':
                emoji = "🌟"
                range_str = "(2.5-2.9)"
            elif cls == 'VERY GOOD':
                emoji = "✨"
                range_str = "(1.8-2.4)"
            elif cls == 'GOOD':
                emoji = "💫"
                range_str = "(1.2-1.7)"
            else:
                emoji = "💡"
                range_str = "(0.8-1.1)"

            md.append(f"- {emoji} **{cls}** {range_str}: {count} signals")

    return '\n'.join(md)


def generate_signal_details(signals):
    """Generate detailed signal log"""
    md = []
    md.append("\n## SIGNAL LOG\n")

    # Group signals by symbol
    by_symbol = {}
    for signal in signals:
        symbol = signal['symbol']
        if symbol not in by_symbol:
            by_symbol[symbol] = []
        by_symbol[symbol].append(signal)

    # Sort signals within each symbol by timestamp
    for symbol in by_symbol:
        by_symbol[symbol].sort(key=lambda x: x['timestamp'])

    # Generate sections for each symbol
    for symbol in sorted(by_symbol.keys()):
        md.append(f"\n### {symbol}\n")

        symbol_signals = by_symbol[symbol]

        for i, signal in enumerate(symbol_signals, 1):
            # Signal header
            dt = datetime.fromtimestamp(signal['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            direction = "Bullish" if signal['system'] == 'wind_catcher' else "Bearish"
            direction_emoji = "🌪️" if signal['system'] == 'wind_catcher' else "🌊"

            confluence_emoji_map = {
                'PERFECT': '⭐',
                'EXCELLENT': '🌟',
                'VERY GOOD': '✨',
                'GOOD': '💫',
                'INTERESTING': '💡'
            }
            confluence_emoji = confluence_emoji_map.get(signal['confluence_class'], '❓')

            md.append(f"#### Signal #{i} - {confluence_emoji} {signal['confluence_class']} {direction} {direction_emoji}\n")

            # Signal details
            md.append(f"- **Date**: {dt} UTC")
            md.append(f"- **Price**: ${signal['price']:.2f}")
            md.append(f"- **Confluence Score**: {signal['confluence_score']:.2f}")
            md.append(f"- **Timeframe**: {signal['timeframe']}")

            # Indicators
            if signal.get('indicators_firing'):
                indicators = signal['indicators_firing']
                ind_list = []
                if indicators.get('hull', 0) > 0:
                    ind_list.append(f"Hull({indicators['hull']})")
                if indicators.get('ao', 0) > 0:
                    ind_list.append(f"AO({indicators['ao']})")
                if indicators.get('alligator', 0) > 0:
                    ind_list.append(f"Alligator({indicators['alligator']})")
                if indicators.get('ichimoku', 0) > 0:
                    ind_list.append(f"Ichimoku({indicators['ichimoku']})")
                if indicators.get('volume', 0) > 0:
                    ind_list.append(f"Volume({indicators['volume']})")

                md.append(f"- **Indicators**: {', '.join(ind_list)}")

            # Volume
            if signal.get('volume_level'):
                vol_emoji = {
                    'CLIMAX': '🔥',
                    'HOT': '🌡️',
                    'WARMING': '📈',
                    'NORMAL': '📊'
                }.get(signal['volume_level'], '📊')

                md.append(f"- **Volume**: {vol_emoji} {signal['volume_level']} "
                          f"({signal.get('volume_ratio', 1.0):.1f}x average)")

            # Details
            if signal.get('details'):
                md.append(f"- **Details**: {signal['details']}")

            md.append("")  # Empty line

    return '\n'.join(md)


def generate_verification_checklist(signals):
    """Generate checklist for manual verification on TradingView"""
    md = []
    md.append("\n## VERIFICATION CHECKLIST\n")
    md.append("Use this checklist to manually verify signals on TradingView:\n")

    for i, signal in enumerate(signals, 1):
        dt = datetime.fromtimestamp(signal['timestamp']).strftime('%Y-%m-%d %H:%M')
        direction_emoji = "🌪️" if signal['system'] == 'wind_catcher' else "🌊"

        md.append(f"- [ ] **Signal #{i}**: {signal['symbol']} @ {dt} "
                  f"{direction_emoji} ${signal['price']:.2f} (Score: {signal['confluence_score']:.1f})")

    return '\n'.join(md)


def generate_markdown_report(signals, start_date, end_date):
    """Generate complete Markdown report"""
    md = []

    # Header
    md.append("# BACKTEST REPORT")
    md.append("## Wind Catcher & River Turn Trading System\n")
    md.append(f"**Period**: {start_date} to {end_date}")
    md.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md.append(f"**Timeframe**: 1h")
    md.append("\n---\n")

    # Summary
    md.append(generate_summary_section(signals))

    # Signal details
    md.append(generate_signal_details(signals))

    # Verification checklist
    md.append(generate_verification_checklist(signals))

    # Footer
    md.append("\n---\n")
    md.append("## NOTES\n")
    md.append("- All times are in UTC")
    md.append("- Verify signals on TradingView before trading")
    md.append("- Confluence scores: PERFECT (≥3.0), EXCELLENT (2.5-2.9), VERY GOOD (1.8-2.4), GOOD (1.2-1.7)")
    md.append("- 🌪️ = Wind Catcher (Bullish), 🌊 = River Turn (Bearish)")

    return '\n'.join(md)


def save_report(report_text, filename):
    """Save report to file"""
    with open(filename, 'w') as f:
        f.write(report_text)

    print(f"✅ Report saved to: {filename}")


def print_quick_summary(signals):
    """Print quick summary to console"""
    print("\n" + "="*80)
    print("📊 QUICK SUMMARY")
    print("="*80)

    print(f"\nTotal Signals: {len(signals)}")

    # Top 10 signals
    if signals:
        print("\n🌟 Top 10 Signals by Confluence Score:")
        print("-"*80)

        top_signals = sorted(signals, key=lambda x: x['confluence_score'], reverse=True)[:10]

        for i, signal in enumerate(top_signals, 1):
            dt = datetime.fromtimestamp(signal['timestamp']).strftime('%Y-%m-%d %H:%M')
            direction_emoji = "🌪️" if signal['system'] == 'wind_catcher' else "🌊"

            confluence_emoji_map = {
                'PERFECT': '⭐',
                'EXCELLENT': '🌟',
                'VERY GOOD': '✨',
                'GOOD': '💫',
                'INTERESTING': '💡'
            }
            emoji = confluence_emoji_map.get(signal['confluence_class'], '❓')

            print(f"{i:2d}. {emoji} {direction_emoji} {signal['symbol']:12s} @ {dt} - "
                  f"${signal['price']:>8.2f} | Score: {signal['confluence_score']:.2f} ({signal['confluence_class']})")

    print("="*80)


def main():
    """Main execution"""
    print("="*80)
    print("📝 BACKTEST REPORT GENERATOR")
    print("="*80)

    # Configuration
    start_date = '2024-10-03'
    end_date = '2024-11-03'

    print(f"\nGenerating report for period: {start_date} to {end_date}")

    # Connect to database
    conn = connect_to_database()

    # Get signals
    print("Loading signals from database...")
    signals = get_backtest_signals(conn, start_date, end_date)

    print(f"✅ Found {len(signals)} signals")

    if len(signals) == 0:
        print("\n⚠️  No signals found in database for this period.")
        print("💡 Make sure you've run backtest_runner.py first!")
        conn.close()
        return

    # Generate report
    print("\nGenerating Markdown report...")
    report = generate_markdown_report(signals, start_date, end_date)

    # Save report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'data/backtest_report_{timestamp}.md'
    save_report(report, filename)

    # Print summary
    print_quick_summary(signals)

    print(f"\n📄 Full report available at: {filename}")
    print("\n💡 Next steps:")
    print("   1. Review the report to understand signal quality")
    print("   2. Verify top signals on TradingView")
    print("   3. Use insights to refine confluence parameters if needed")

    conn.close()


if __name__ == "__main__":
    main()
