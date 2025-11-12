"""
Telegram Bot Integration
Sends formatted alerts for EXCELLENT+ signals
"""

import requests
import yaml
from datetime import datetime


def load_telegram_config():
    """Load Telegram settings from config"""
    try:
        with open('config/config.yaml', 'r') as file:
            config = yaml.safe_load(file)
        return config.get('telegram', {})
    except Exception as e:
        print(f"Error loading Telegram config: {e}")
        return {}


def send_telegram_message(bot_token, chat_id, message, parse_mode='HTML'):
    """Send message via Telegram Bot API"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': parse_mode
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200

    except Exception as e:
        print(f"Telegram send error: {e}")
        return False


def format_signal_alert(signal):
    """Format signal as Telegram message"""
    # Determine direction
    direction = "BULLISH" if signal.get('system') == 'wind_catcher' else "BEARISH"
    direction_emoji = signal.get('system_emoji', "🌪️" if direction == "BULLISH" else "🌊")

    # Get confluence emoji
    emoji = signal.get('emoji', '🌟')

    # Format indicators
    indicators_summary = signal.get('indicators_summary', 'N/A')

    # Build message
    message = f"""
🚨 <b>{emoji} {signal.get('confluence_class', 'SIGNAL')}</b>

{direction_emoji} <b>{direction}</b> - {signal.get('symbol', 'N/A')}
💰 Price: ${signal.get('price', 0):.2f}
📊 Score: {signal.get('confluence_score', 0):.1f}
⏰ Time: {signal.get('datetime', 'N/A')}
🕐 Timeframe: {signal.get('timeframe', 'N/A')}

<b>Indicators:</b>
{indicators_summary}

<b>Volume:</b> {signal.get('volume_level', 'N/A')}
{f"({signal.get('volume_ratio', 1):.1f}x)" if signal.get('volume_ratio') else ''}

✅ Open TradingView and verify setup!
    """.strip()

    return message


def send_signal_alert(signal):
    """
    Send signal alert to Telegram

    Parameters:
    - signal: Signal dict with all required fields

    Returns:
    - bool: True if sent successfully
    """
    config = load_telegram_config()

    # Check if Telegram is enabled
    if not config.get('enabled', False):
        return False

    # Check if signal meets minimum score
    min_score = config.get('min_score', 2.5)
    signal_score = signal.get('confluence_score', 0)

    if signal_score < min_score:
        return False

    # Get bot credentials
    bot_token = config.get('bot_token')
    chat_id = config.get('chat_id')

    if not bot_token or not chat_id or bot_token == 'YOUR_BOT_TOKEN_HERE':
        print("⚠️  Telegram not configured. Set bot_token and chat_id in config.yaml")
        return False

    # Format and send message
    message = format_signal_alert(signal)
    success = send_telegram_message(bot_token, chat_id, message)

    if success:
        print(f"📱 Telegram alert sent: {signal.get('symbol')} - {signal.get('confluence_class')}")
    else:
        print(f"❌ Failed to send Telegram alert for {signal.get('symbol')}")

    return success


def test_telegram_connection():
    """Test Telegram bot connection"""
    print("="*60)
    print("🧪 Testing Telegram Bot Connection")
    print("="*60)

    config = load_telegram_config()

    if not config.get('enabled'):
        print("\n⚠️  Telegram is disabled in config.yaml")
        print("Set telegram.enabled to true to enable alerts")
        return False

    bot_token = config.get('bot_token')
    chat_id = config.get('chat_id')

    if not bot_token or bot_token == 'YOUR_BOT_TOKEN_HERE':
        print("\n❌ Bot token not configured")
        print("Set telegram.bot_token in config.yaml")
        return False

    if not chat_id or chat_id == 'YOUR_CHAT_ID_HERE':
        print("\n❌ Chat ID not configured")
        print("Set telegram.chat_id in config.yaml")
        return False

    # Send test message
    print(f"\nBot Token: {bot_token[:10]}...")
    print(f"Chat ID: {chat_id}")
    print("\nSending test message...")

    test_message = """
🧪 <b>Test Message</b>

🚀 Wind Catcher & River Turn Trading System

This is a test message to verify your Telegram bot is working correctly.

If you received this message, your bot is configured properly!
    """.strip()

    success = send_telegram_message(bot_token, chat_id, test_message)

    if success:
        print("\n✅ Test message sent successfully!")
        print("Check your Telegram to confirm receipt.")
    else:
        print("\n❌ Failed to send test message")
        print("Check your bot token and chat ID")

    return success


def test_signal_alert():
    """Test sending a formatted signal alert"""
    print("="*60)
    print("🧪 Testing Signal Alert Format")
    print("="*60)

    # Create mock signal
    mock_signal = {
        'emoji': '⭐',
        'system_emoji': '🌪️',
        'confluence_class': 'PERFECT',
        'system': 'wind_catcher',
        'symbol': 'BTC/USDT',
        'price': 67234.50,
        'confluence_score': 3.2,
        'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'timeframe': '1h',
        'indicators_summary': 'Hull(2), AO(1), Alligator(1), Ichimoku(1), Volume(1)',
        'volume_level': 'HOT',
        'volume_ratio': 2.3
    }

    print("\nMock signal:")
    print(f"  {mock_signal['symbol']} - {mock_signal['confluence_class']}")
    print(f"  Score: {mock_signal['confluence_score']}")
    print("\nSending formatted alert...")

    success = send_signal_alert(mock_signal)

    if success:
        print("\n✅ Signal alert sent successfully!")
    else:
        print("\n⚠️  Signal alert not sent (may be disabled or below threshold)")

    return success


def main():
    """Main test function"""
    import sys

    print("\n🤖 Telegram Bot Test Suite\n")

    if len(sys.argv) > 1:
        if sys.argv[1] == '--test-connection':
            test_telegram_connection()
        elif sys.argv[1] == '--test-alert':
            test_signal_alert()
        else:
            print("Usage:")
            print("  python telegram_bot.py --test-connection")
            print("  python telegram_bot.py --test-alert")
    else:
        print("Running all tests...\n")
        test_telegram_connection()
        print()
        test_signal_alert()


if __name__ == "__main__":
    main()
