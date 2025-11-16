"""
Telegram Bot Module for Wind Catcher & River Turn
Sends formatted trading signal alerts to Telegram
"""

import requests
from datetime import datetime
from utils import load_config

class TelegramBot:
    """Telegram bot for sending trading signal alerts"""

    def __init__(self):
        """Initialize bot with configuration"""
        self.config = load_config()
        self.telegram_config = self.config.get('telegram', {})
        self.enabled = self.telegram_config.get('enabled', False)
        self.bot_token = self.telegram_config.get('bot_token', '')
        self.chat_id = self.telegram_config.get('chat_id', '')
        self.min_score = self.telegram_config.get('min_score', 2.5)

        # Emojis for signal classification
        self.alert_emojis = self.telegram_config.get('alert_emojis', {
            'perfect': '⭐',
            'excellent': '🌟',
            'very_good': '✨',
            'good': '💫'
        })

        self.system_emojis = self.telegram_config.get('system_emojis', {
            'wind_catcher': '🌪️',
            'river_turn': '🌊'
        })

        # Validate configuration
        if self.enabled:
            self._validate_config()

    def _validate_config(self):
        """Validate Telegram configuration"""
        if not self.bot_token or self.bot_token == 'YOUR_BOT_TOKEN_HERE':
            raise ValueError("Telegram bot_token not configured. Get token from @BotFather")

        if not self.chat_id or self.chat_id == 'YOUR_CHAT_ID_HERE':
            raise ValueError("Telegram chat_id not configured. Get ID from @userinfobot")

    def send_message(self, message, parse_mode='HTML'):
        """
        Send a message to Telegram

        Args:
            message (str): Message text (supports HTML formatting)
            parse_mode (str): 'HTML' or 'Markdown'

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }

        try:
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                return True
            else:
                print(f"⚠️ Telegram API error: {response.status_code}")
                print(f"   Response: {response.text}")
                return False

        except requests.exceptions.Timeout:
            print("⚠️ Telegram request timeout")
            return False
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Telegram request error: {e}")
            return False
        except Exception as e:
            print(f"⚠️ Unexpected error sending Telegram message: {e}")
            return False

    def get_emoji_for_confluence(self, confluence_class):
        """Get emoji for confluence classification"""
        class_lower = confluence_class.lower().replace(' ', '_')
        return self.alert_emojis.get(class_lower, '💫')

    def get_emoji_for_system(self, system):
        """Get emoji for trading system (wind_catcher/river_turn)"""
        return self.system_emojis.get(system, '📊')

    def format_signal_alert(self, signal):
        """
        Format a trading signal as a Telegram message

        Args:
            signal (dict): Signal data from master_confluence analysis

        Returns:
            str: Formatted HTML message
        """
        # Extract signal details
        symbol = signal.get('symbol', 'UNKNOWN')
        timeframe = signal.get('timeframe', '1h')
        price = signal.get('price', 0)
        timestamp = signal.get('timestamp', 0)

        # Confluence data
        confluence = signal.get('confluence', {})
        score = confluence.get('score', 0)
        classification = confluence.get('classification', 'UNKNOWN')
        primary_system = confluence.get('primary_system', 'wind_catcher')

        # Emojis
        confluence_emoji = self.get_emoji_for_confluence(classification)
        system_emoji = self.get_emoji_for_system(primary_system)

        # Direction
        direction = "BULLISH" if primary_system == 'wind_catcher' else "BEARISH"

        # Format timestamp
        dt = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        # Build indicators summary
        indicators_summary = self._format_indicators_summary(signal)

        # Volume info
        volume_info = self._format_volume_info(signal)

        # Build message
        message = f"""
🚨 <b>{confluence_emoji} {classification} Signal</b>

{system_emoji} <b>{direction}</b> - {symbol}
💰 Price: ${price:.2f}
📊 Score: {score:.2f}
⏰ Time: {dt}
🕐 Timeframe: {timeframe}

<b>Indicators:</b>
{indicators_summary}

<b>Volume:</b>
{volume_info}

✅ <i>Review on TradingView before trading</i>
        """.strip()

        return message

    def _format_indicators_summary(self, signal):
        """Format indicators that are firing"""
        hull_signals = signal.get('hull_signals', [])
        ao_signals = signal.get('ao_signals', [])
        alligator_signals = signal.get('alligator_signals', [])
        ichimoku_signals = signal.get('ichimoku_signals', [])
        volume_signals = signal.get('volume_signals', [])

        lines = []

        if hull_signals:
            hull_count = len(hull_signals)
            hull_desc = hull_signals[0].get('description', 'Hull signal') if hull_signals else ''
            lines.append(f"  🌀 Hull MA: {hull_count} signal(s) - {hull_desc}")

        if ao_signals:
            ao_count = len(ao_signals)
            ao_desc = ao_signals[0].get('description', 'AO signal') if ao_signals else ''
            lines.append(f"  📈 AO: {ao_count} signal(s) - {ao_desc}")

        if alligator_signals:
            alligator_count = len(alligator_signals)
            alligator_desc = alligator_signals[0].get('description', 'Alligator signal') if alligator_signals else ''
            lines.append(f"  🐊 Alligator: {alligator_count} signal(s) - {alligator_desc}")

        if ichimoku_signals:
            ichimoku_count = len(ichimoku_signals)
            ichimoku_desc = ichimoku_signals[0].get('description', 'Ichimoku signal') if ichimoku_signals else ''
            lines.append(f"  ☁️ Ichimoku: {ichimoku_count} signal(s) - {ichimoku_desc}")

        if volume_signals:
            volume_count = len(volume_signals)
            volume_desc = volume_signals[0].get('description', 'Volume signal') if volume_signals else ''
            lines.append(f"  📊 Volume: {volume_count} signal(s) - {volume_desc}")

        return '\n'.join(lines) if lines else '  No specific indicators (monitoring)'

    def _format_volume_info(self, signal):
        """Format volume information"""
        volume_signals = signal.get('volume_signals', [])

        if volume_signals:
            vol_signal = volume_signals[0]
            level = vol_signal.get('level', 'NORMAL')
            ratio = vol_signal.get('ratio', 1.0)
            return f"{level} ({ratio:.1f}x average)"

        return "NORMAL"

    def should_send_alert(self, signal):
        """
        Check if signal meets criteria for Telegram alert

        Args:
            signal (dict): Signal data

        Returns:
            bool: True if alert should be sent
        """
        if not self.enabled:
            return False

        confluence = signal.get('confluence', {})
        score = confluence.get('score', 0)

        # Only send EXCELLENT+ signals (score >= min_score)
        return score >= self.min_score

    def send_signal_alert(self, signal):
        """
        Send a signal alert if it meets criteria

        Args:
            signal (dict): Signal data from master_confluence

        Returns:
            bool: True if alert was sent successfully
        """
        if not self.should_send_alert(signal):
            return False

        message = self.format_signal_alert(signal)
        return self.send_message(message)

    def send_test_message(self):
        """Send a test message to verify bot is working"""
        message = """
🚀 <b>Wind Catcher & River Turn</b>
<i>Trading System Test Message</i>

✅ Telegram bot is configured correctly!
📱 You will receive alerts here for EXCELLENT+ signals.

System Status: <b>ACTIVE</b>
        """.strip()

        return self.send_message(message)

    def send_system_status(self, status_message):
        """Send a system status update"""
        message = f"""
🔔 <b>System Status Update</b>

{status_message}

<i>Wind Catcher & River Turn Trading System</i>
        """.strip()

        return self.send_message(message)


def main():
    """Test the Telegram bot"""
    print("🧪 Testing Telegram Bot Configuration")
    print("="*60)

    try:
        bot = TelegramBot()

        if not bot.enabled:
            print("⚠️ Telegram is disabled in config.yaml")
            print("\nTo enable Telegram alerts:")
            print("1. Message @BotFather on Telegram to create a bot")
            print("2. Get your bot token")
            print("3. Message @userinfobot to get your chat_id")
            print("4. Update config/config.yaml with your credentials")
            print("5. Set telegram.enabled = true")
            return

        print(f"✅ Telegram enabled")
        print(f"   Bot token: {bot.bot_token[:10]}...")
        print(f"   Chat ID: {bot.chat_id}")
        print(f"   Min score for alerts: {bot.min_score}")

        # Send test message
        print("\n📤 Sending test message...")
        success = bot.send_test_message()

        if success:
            print("✅ Test message sent successfully!")
            print("   Check your Telegram to confirm receipt")
        else:
            print("❌ Failed to send test message")
            print("   Check your bot token and chat_id")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
