"""
Test Script for Telegram Bot Integration
Tests message sending, formatting, and signal alerts
"""

from datetime import datetime
from telegram_bot import TelegramBot
from utils import load_config


def test_basic_message():
    """Test sending a basic message"""
    print("\n" + "="*60)
    print("TEST 1: Basic Message")
    print("="*60)

    try:
        bot = TelegramBot()

        if not bot.enabled:
            print("❌ Telegram is disabled in config.yaml")
            print("\n📋 To enable Telegram:")
            print("   1. Create bot with @BotFather on Telegram")
            print("   2. Get bot token")
            print("   3. Message @userinfobot to get your chat_id")
            print("   4. Edit config/config.yaml:")
            print("      telegram:")
            print("        enabled: true")
            print('        bot_token: "YOUR_BOT_TOKEN"')
            print('        chat_id: "YOUR_CHAT_ID"')
            return False

        message = "🚀 <b>Test Message</b>\n\nTelegram bot is working correctly!"

        print("📤 Sending test message...")
        success = bot.send_message(message)

        if success:
            print("✅ Basic message sent successfully!")
            print("   Check your Telegram to confirm receipt")
            return True
        else:
            print("❌ Failed to send message")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_alert_formatting():
    """Test signal alert message formatting"""
    print("\n" + "="*60)
    print("TEST 2: Signal Alert Formatting")
    print("="*60)

    try:
        bot = TelegramBot()

        # Create mock signal data
        mock_signal = {
            'symbol': 'BTC',
            'timeframe': '1h',
            'price': 45234.50,
            'timestamp': int(datetime.now().timestamp()),
            'confluence': {
                'score': 3.2,
                'class': 'PERFECT',
                'primary_system': 'wind_catcher',
                'signal_count': 5
            },
            'hull_signals': [
                {'type': 'hull_bullish_break', 'description': 'First close above Hull 21', 'strength': 0.7}
            ],
            'ao_signals': [
                {'type': 'ao_bullish_divergence', 'description': 'Regular bullish divergence', 'strength': 0.9}
            ],
            'alligator_signals': [
                {'type': 'alligator_blue_line_contact', 'description': 'Bullish retracement to blue line', 'strength': 0.8}
            ],
            'ichimoku_signals': [
                {'type': 'kijun_touch', 'description': 'Kijun support touch', 'strength': 0.8}
            ],
            'volume_signals': [
                {'level': 'HOT', 'ratio': 2.3, 'description': 'Elevated volume'}
            ]
        }

        print("📝 Formatting mock PERFECT signal...")
        message = bot.format_signal_alert(mock_signal)

        print("\n📄 Formatted Message:")
        print("-"*60)
        # Print without HTML tags for readability
        import re
        plain_message = re.sub('<[^>]+>', '', message)
        print(plain_message)
        print("-"*60)

        if not bot.enabled:
            print("\n⚠️ Telegram disabled - cannot send")
            return True

        print("\n📤 Sending formatted signal alert...")
        success = bot.send_message(message)

        if success:
            print("✅ Signal alert sent successfully!")
            return True
        else:
            print("❌ Failed to send signal alert")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_excellent_signal():
    """Test EXCELLENT signal (lower score)"""
    print("\n" + "="*60)
    print("TEST 3: EXCELLENT Signal Alert")
    print("="*60)

    try:
        bot = TelegramBot()

        mock_signal = {
            'symbol': 'ETH',
            'timeframe': '4h',
            'price': 3124.75,
            'timestamp': int(datetime.now().timestamp()),
            'confluence': {
                'score': 2.7,
                'class': 'EXCELLENT',
                'primary_system': 'river_turn',
                'signal_count': 3
            },
            'hull_signals': [
                {'type': 'hull_bearish_break', 'description': 'First close below Hull 21', 'strength': 0.7}
            ],
            'ao_signals': [],
            'alligator_signals': [],
            'ichimoku_signals': [
                {'type': 'kijun_touch', 'description': 'Kijun resistance touch', 'strength': 0.8}
            ],
            'volume_signals': [
                {'level': 'WARMING', 'ratio': 1.7, 'description': 'Above average volume'}
            ]
        }

        print("📝 Formatting mock EXCELLENT signal (bearish)...")
        message = bot.format_signal_alert(mock_signal)

        if not bot.enabled:
            print("\n⚠️ Telegram disabled - cannot send")
            return True

        print("📤 Sending EXCELLENT signal alert...")
        success = bot.send_message(message)

        if success:
            print("✅ EXCELLENT signal sent successfully!")
            return True
        else:
            print("❌ Failed to send signal")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_should_send_alert():
    """Test alert filtering logic"""
    print("\n" + "="*60)
    print("TEST 4: Alert Filtering Logic")
    print("="*60)

    try:
        bot = TelegramBot()

        test_cases = [
            ({'confluence': {'score': 3.5}}, True, 'PERFECT (3.5)'),
            ({'confluence': {'score': 2.5}}, True, 'EXCELLENT (2.5)'),
            ({'confluence': {'score': 2.0}}, False, 'VERY GOOD (2.0)'),
            ({'confluence': {'score': 1.5}}, False, 'GOOD (1.5)'),
        ]

        print(f"Min score for alerts: {bot.min_score}\n")

        all_passed = True

        for signal, expected, description in test_cases:
            result = bot.should_send_alert(signal)
            status = "✅" if result == expected else "❌"
            print(f"{status} {description}: {'SEND' if result else 'SKIP'} (expected: {'SEND' if expected else 'SKIP'})")

            if result != expected:
                all_passed = False

        if all_passed:
            print("\n✅ All filtering tests passed!")
            return True
        else:
            print("\n❌ Some filtering tests failed")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_config_validation():
    """Test configuration validation"""
    print("\n" + "="*60)
    print("TEST 5: Configuration Validation")
    print("="*60)

    try:
        config = load_config()
        telegram_config = config.get('telegram', {})

        print("📋 Telegram Configuration:")
        print(f"   Enabled: {telegram_config.get('enabled', False)}")
        print(f"   Bot Token: {telegram_config.get('bot_token', 'NOT SET')[:20]}...")
        print(f"   Chat ID: {telegram_config.get('chat_id', 'NOT SET')}")
        print(f"   Min Score: {telegram_config.get('min_score', 2.5)}")

        bot = TelegramBot()

        if bot.enabled:
            print("\n✅ Configuration valid!")
            return True
        else:
            print("\n⚠️ Telegram disabled (this is OK if intentional)")
            return True

    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("🧪 Wind Catcher & River Turn - Telegram Bot Tests")
    print("="*60)

    results = {
        'config': test_config_validation(),
        'basic_message': test_basic_message(),
        'formatting': test_signal_alert_formatting(),
        'excellent_signal': test_excellent_signal(),
        'filtering': test_should_send_alert(),
    }

    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)

    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
