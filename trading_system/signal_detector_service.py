"""
Signal Detector Service for Wind Catcher & River Turn
Continuously scans user_watchlists and detects new confluence signals
Sends Telegram alerts for EXCELLENT+ signals
"""

import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import time
import json
from datetime import datetime
from utils import connect_to_database, load_config, get_current_timestamp
from master_confluence import analyze_master_confluence
from telegram_bot import TelegramBot


class SignalDetectorService:
    """Background service that detects and alerts on trading signals"""

    def __init__(self):
        """Initialize the signal detector service"""
        self.config = load_config()
        self.scan_interval = self.config['system'].get('signal_scan_interval', 300)
        self.min_score_display = self.config['confluence'].get('min_score_display', 1.2)

        # Initialize Telegram bot
        try:
            self.telegram_bot = TelegramBot()
            if self.telegram_bot.enabled:
                print(f"✅ Telegram alerts enabled (min score: {self.telegram_bot.min_score})")
            else:
                print(f"ℹ️  Telegram alerts disabled")
        except Exception as e:
            print(f"⚠️ Telegram initialization failed: {e}")
            self.telegram_bot = None

    def get_watchlist_entries(self, conn):
        """
        Get all entries from user_watchlists

        Returns:
            list: List of (symbol, timeframe, direction) tuples
        """
        cursor = conn.cursor()
        cursor.execute("""
            SELECT symbol, timeframe, direction
            FROM user_watchlists
            ORDER BY symbol, timeframe
        """)
        entries = cursor.fetchall()
        cursor.close()
        return entries

    def signal_exists_recently(self, conn, symbol, timeframe, hours_window=4):
        """
        Check if a similar signal was already recorded recently

        Args:
            conn: Database connection
            symbol: Trading symbol
            timeframe: Timeframe
            hours_window: Hours to look back (default 4)

        Returns:
            bool: True if recent signal exists
        """
        cursor = conn.cursor()
        cutoff_time = get_current_timestamp() - (hours_window * 3600)

        cursor.execute("""
            SELECT COUNT(*)
            FROM signals
            WHERE symbol = ?
              AND timeframe = ?
              AND timestamp >= ?
        """, (symbol, timeframe, cutoff_time))

        count = cursor.fetchone()[0]
        cursor.close()

        return count > 0

    def save_signal(self, conn, analysis_result):
        """
        Save a signal to the database

        Args:
            conn: Database connection
            analysis_result: Result from analyze_master_confluence

        Returns:
            int: Signal ID if saved, None otherwise
        """
        symbol = analysis_result['symbol']
        timeframe = analysis_result['timeframe']
        timestamp = analysis_result['timestamp']
        price = analysis_result['price']

        confluence = analysis_result['confluence']
        score = confluence['score']
        classification = confluence['classification']
        primary_system = confluence['primary_system']

        # Build indicators_firing JSON
        indicators_firing = {
            'hull': len(analysis_result.get('hull_signals', [])),
            'ao': len(analysis_result.get('ao_signals', [])),
            'alligator': len(analysis_result.get('alligator_signals', [])),
            'ichimoku': len(analysis_result.get('ichimoku_signals', [])),
            'volume': len(analysis_result.get('volume_signals', []))
        }

        # Get volume info
        volume_signals = analysis_result.get('volume_signals', [])
        volume_level = 'NORMAL'
        volume_ratio = 1.0

        if volume_signals:
            volume_level = volume_signals[0].get('level', 'NORMAL')
            volume_ratio = volume_signals[0].get('ratio', 1.0)

        # Build details JSON
        details = {
            'confluence': confluence,
            'hull_signals': analysis_result.get('hull_signals', []),
            'ao_signals': analysis_result.get('ao_signals', []),
            'alligator_signals': analysis_result.get('alligator_signals', []),
            'ichimoku_signals': analysis_result.get('ichimoku_signals', []),
            'volume_signals': volume_signals
        }

        # Signal type
        signal_type = 'confluence_' + classification.lower().replace(' ', '_')

        current_time = get_current_timestamp()

        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO signals (
                    timestamp, symbol, timeframe, system, signal_type,
                    price, confluence_score, confluence_class,
                    indicators_firing, volume_level, volume_ratio,
                    details, notified, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp, symbol, timeframe, primary_system, signal_type,
                price, score, classification,
                json.dumps(indicators_firing), volume_level, volume_ratio,
                json.dumps(details), 0, current_time
            ))

            conn.commit()
            signal_id = cursor.lastrowid
            cursor.close()

            return signal_id

        except Exception as e:
            print(f"⚠️ Error saving signal: {e}")
            cursor.close()
            return None

    def mark_signal_notified(self, conn, signal_id):
        """Mark a signal as notified via Telegram"""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE signals
            SET notified = 1
            WHERE id = ?
        """, (signal_id,))
        conn.commit()
        cursor.close()

    def scan_watchlists(self, conn):
        """
        Scan all watchlist entries for new signals

        Returns:
            dict: Statistics about the scan
        """
        stats = {
            'scanned': 0,
            'signals_found': 0,
            'signals_saved': 0,
            'alerts_sent': 0,
            'errors': []
        }

        # Get watchlist entries
        watchlist = self.get_watchlist_entries(conn)

        if not watchlist:
            print("⚠️ No entries in user_watchlists table")
            return stats

        print(f"\n📊 Scanning {len(watchlist)} watchlist entries...")
        print("-"*60)

        for symbol, timeframe, direction in watchlist:
            stats['scanned'] += 1

            try:
                # Analyze symbol on this timeframe
                result = analyze_master_confluence(conn, symbol, timeframe)

                if not result:
                    continue

                confluence = result['confluence']
                score = confluence['score']
                classification = confluence['classification']
                primary_system = confluence['primary_system']

                # Check if score meets minimum threshold
                if score < self.min_score_display:
                    continue

                # Check if signal matches watchlist direction
                if primary_system != direction:
                    # Signal is opposite direction of what we're watching for
                    continue

                stats['signals_found'] += 1

                # Check if we already recorded this signal recently
                if self.signal_exists_recently(conn, symbol, timeframe, hours_window=4):
                    print(f"  ⏭️  {symbol:8s} {timeframe:4s} - Signal already recorded recently")
                    continue

                # Save signal to database
                signal_id = self.save_signal(conn, result)

                if signal_id:
                    stats['signals_saved'] += 1
                    print(f"  💫 {symbol:8s} {timeframe:4s} - {classification} ({score:.2f}) - Saved (ID: {signal_id})")

                    # Send Telegram alert if enabled and score is high enough
                    if self.telegram_bot and self.telegram_bot.should_send_alert(result):
                        try:
                            success = self.telegram_bot.send_signal_alert(result)

                            if success:
                                self.mark_signal_notified(conn, signal_id)
                                stats['alerts_sent'] += 1
                                print(f"      📱 Telegram alert sent!")
                            else:
                                print(f"      ⚠️  Telegram alert failed")

                        except Exception as e:
                            print(f"      ⚠️  Telegram error: {e}")
                            stats['errors'].append(f"{symbol} {timeframe}: Telegram error - {e}")

            except Exception as e:
                print(f"  ❌ {symbol:8s} {timeframe:4s} - Error: {e}")
                stats['errors'].append(f"{symbol} {timeframe}: {str(e)}")

        return stats

    def run_once(self):
        """Run one scan cycle"""
        print(f"\n{'='*60}")
        print(f"🔍 Signal Detection Cycle - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        conn = connect_to_database()

        try:
            stats = self.scan_watchlists(conn)

            # Print summary
            print(f"\n📋 Scan Summary:")
            print(f"   Entries scanned: {stats['scanned']}")
            print(f"   Signals found: {stats['signals_found']}")
            print(f"   Signals saved: {stats['signals_saved']}")
            print(f"   Telegram alerts sent: {stats['alerts_sent']}")

            if stats['errors']:
                print(f"   ⚠️  Errors: {len(stats['errors'])}")

            return stats

        finally:
            conn.close()

    def run_continuous(self):
        """Run continuous scanning loop"""
        print(f"🚀 Wind Catcher & River Turn - Signal Detector Service")
        print(f"="*60)
        print(f"Scan interval: {self.scan_interval} seconds ({self.scan_interval // 60} minutes)")
        print(f"Min score for display: {self.min_score_display}")

        if self.telegram_bot and self.telegram_bot.enabled:
            print(f"Telegram alerts: ENABLED (min score: {self.telegram_bot.min_score})")
        else:
            print(f"Telegram alerts: DISABLED")

        print(f"="*60)

        cycle_count = 0

        while True:
            cycle_count += 1

            try:
                stats = self.run_once()

                # Send status update to Telegram every 24 hours (assuming 5 min intervals)
                if self.telegram_bot and self.telegram_bot.enabled and cycle_count % 288 == 0:
                    status_msg = f"24-hour status:\n{stats['signals_saved']} new signals\n{stats['alerts_sent']} alerts sent"
                    self.telegram_bot.send_system_status(status_msg)

            except KeyboardInterrupt:
                print("\n\n⚠️ Stopping signal detector service...")
                break
            except Exception as e:
                print(f"\n❌ Error in scan cycle: {e}")
                import traceback
                traceback.print_exc()

            # Sleep until next scan
            print(f"\n💤 Sleeping for {self.scan_interval} seconds...")
            print(f"   Next scan at: {datetime.fromtimestamp(get_current_timestamp() + self.scan_interval).strftime('%H:%M:%S')}")

            try:
                time.sleep(self.scan_interval)
            except KeyboardInterrupt:
                print("\n\n⚠️ Stopping signal detector service...")
                break

        print("\n✅ Signal detector service stopped")


def main():
    """Main entry point"""
    service = SignalDetectorService()

    # Run one scan or continuous?
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        service.run_once()
    else:
        service.run_continuous()


if __name__ == "__main__":
    main()
