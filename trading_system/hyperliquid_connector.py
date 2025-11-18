"""
Hyperliquid DEX Connector for Wind Catcher & River Turn Trading System
Handles all Hyperliquid API interactions for market data
"""

from hyperliquid.info import Info
from hyperliquid.utils import constants
from datetime import datetime, timedelta
from utils import normalize_timestamp, log_message


class HyperliquidConnector:
    """
    Connector for Hyperliquid DEX
    Provides methods to fetch market data from Hyperliquid
    """

    def __init__(self, use_testnet=False):
        """
        Initialize Hyperliquid connector

        Args:
            use_testnet (bool): Use testnet if True, mainnet if False
        """
        self.api_url = constants.TESTNET_API_URL if use_testnet else constants.MAINNET_API_URL
        self.use_testnet = use_testnet

        try:
            # Initialize Info API (read-only, no credentials needed for public data)
            self.info = Info(self.api_url, skip_ws=True)
            self.connected = True
            log_message(
                f"✅ Connected to Hyperliquid {'Testnet' if use_testnet else 'Mainnet'}",
                "INFO"
            )
        except Exception as e:
            self.connected = False
            log_message(f"❌ Failed to connect to Hyperliquid: {e}", "ERROR")
            raise

    def fetch_ohlcv(self, symbol, timeframe='1h', limit=100):
        """
        Fetch OHLCV candle data from Hyperliquid

        Args:
            symbol (str): Trading pair symbol (e.g., 'BTC/USDT' or 'BTC')
            timeframe (str): Candle interval ('1m', '5m', '15m', '1h', '4h', '1d', etc.)
            limit (int): Number of candles to fetch (max 5000)

        Returns:
            list: List of candles in format [[timestamp_ms, open, high, low, close, volume], ...]
                  Returns empty list on error

        Note:
            Hyperliquid uses coin names without /USDT suffix (e.g., 'BTC' not 'BTC/USDT')
        """
        if not self.connected:
            log_message("❌ Not connected to Hyperliquid", "ERROR")
            return []

        try:
            # Convert symbol format: 'BTC/USDT' -> 'BTC'
            coin_name = self._normalize_symbol(symbol)

            # Validate timeframe
            if not self._validate_timeframe(timeframe):
                log_message(f"❌ Invalid timeframe: {timeframe}", "ERROR")
                return []

            # Limit max to 5000 (Hyperliquid's limit)
            limit = min(limit, 5000)

            # Calculate time range (ending now, going back 'limit' candles)
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = self._calculate_start_time(end_time, timeframe, limit)

            # Fetch candles from Hyperliquid
            # Note: Hyperliquid SDK v0.20+ uses different API
            candles = self.info.candles_snapshot(
                coin_name,  # First positional arg: symbol
                timeframe,  # Second positional arg: interval
                start_time,  # Third positional arg: startTime
                end_time    # Fourth positional arg: endTime
            )

            # Convert to standard format
            formatted_candles = self._format_candles(candles)

            log_message(
                f"📥 Fetched {len(formatted_candles)} candles for {coin_name} ({timeframe})",
                "INFO"
            )

            return formatted_candles

        except Exception as e:
            log_message(f"❌ Error fetching {symbol} data: {e}", "ERROR")
            return []

    def get_available_markets(self):
        """
        Get list of available trading pairs on Hyperliquid

        Returns:
            list: List of available market symbols
        """
        try:
            # Get all available markets
            meta = self.info.meta()
            universe = meta.get('universe', [])

            # Extract coin names
            markets = [asset['name'] for asset in universe]

            log_message(f"📋 Found {len(markets)} available markets", "INFO")
            return markets

        except Exception as e:
            log_message(f"❌ Error fetching markets: {e}", "ERROR")
            return []

    def _normalize_symbol(self, symbol):
        """
        Normalize symbol format for Hyperliquid

        Args:
            symbol (str): Symbol like 'BTC/USDT' or 'BTC'

        Returns:
            str: Normalized symbol like 'BTC'
        """
        # Remove /USDT suffix if present
        if '/' in symbol:
            return symbol.split('/')[0]
        return symbol

    def _validate_timeframe(self, timeframe):
        """
        Validate if timeframe is supported by Hyperliquid

        Args:
            timeframe (str): Timeframe to validate

        Returns:
            bool: True if valid, False otherwise
        """
        valid_timeframes = [
            '1m', '3m', '5m', '15m', '30m',
            '1h', '2h', '4h', '8h', '12h',
            '1d', '3d', '1w', '1M'
        ]
        return timeframe in valid_timeframes

    def _calculate_start_time(self, end_time, timeframe, limit):
        """
        Calculate start time based on end time, timeframe, and number of candles

        Args:
            end_time (int): End timestamp in milliseconds
            timeframe (str): Candle interval
            limit (int): Number of candles needed

        Returns:
            int: Start timestamp in milliseconds
        """
        # Convert timeframe to milliseconds
        timeframe_ms = self._timeframe_to_ms(timeframe)

        # Calculate start time
        start_time = end_time - (timeframe_ms * limit)

        return start_time

    def _timeframe_to_ms(self, timeframe):
        """
        Convert timeframe string to milliseconds

        Args:
            timeframe (str): Timeframe like '1h', '4h', '1d'

        Returns:
            int: Milliseconds for one candle
        """
        # Parse timeframe
        if timeframe.endswith('m'):
            minutes = int(timeframe[:-1])
            return minutes * 60 * 1000
        elif timeframe.endswith('h'):
            hours = int(timeframe[:-1])
            return hours * 60 * 60 * 1000
        elif timeframe.endswith('d'):
            days = int(timeframe[:-1])
            return days * 24 * 60 * 60 * 1000
        elif timeframe.endswith('w'):
            weeks = int(timeframe[:-1])
            return weeks * 7 * 24 * 60 * 60 * 1000
        elif timeframe.endswith('M'):
            months = int(timeframe[:-1])
            return months * 30 * 24 * 60 * 60 * 1000  # Approximate
        else:
            # Default to 1 hour
            return 60 * 60 * 1000

    def _format_candles(self, candles):
        """
        Format Hyperliquid candle data to standard OHLCV format

        Args:
            candles (list): Raw candles from Hyperliquid

        Returns:
            list: Formatted candles [[timestamp_ms, open, high, low, close, volume], ...]

        Hyperliquid format:
            {
                't': timestamp,
                'T': close_timestamp,
                'o': open,
                'h': high,
                'l': low,
                'c': close,
                'v': volume,
                'n': num_trades,
                's': symbol,
                'i': interval
            }
        """
        formatted = []

        for candle in candles:
            try:
                # Extract fields (Hyperliquid returns strings for prices)
                timestamp = int(candle['t'])
                open_price = float(candle['o'])
                high_price = float(candle['h'])
                low_price = float(candle['l'])
                close_price = float(candle['c'])
                volume = float(candle['v'])

                # Format as [timestamp_ms, open, high, low, close, volume]
                formatted_candle = [
                    timestamp,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume
                ]

                formatted.append(formatted_candle)

            except (KeyError, ValueError) as e:
                log_message(f"⚠️ Error formatting candle: {e}", "WARNING")
                continue

        return formatted


def connect_to_hyperliquid(use_testnet=False):
    """
    Factory function to create Hyperliquid connector

    Args:
        use_testnet (bool): Use testnet if True

    Returns:
        HyperliquidConnector: Connected instance or None on error
    """
    try:
        connector = HyperliquidConnector(use_testnet=use_testnet)
        return connector
    except Exception as e:
        log_message(f"❌ Failed to create Hyperliquid connector: {e}", "ERROR")
        return None


# Example usage and testing
if __name__ == "__main__":
    import sys
    import io

    # Fix Windows console encoding
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print("🔗 Hyperliquid Connector Test")
    print("="*60)

    # Test connection
    print("\n1. Testing connection...")
    connector = connect_to_hyperliquid(use_testnet=False)

    if connector:
        print("✅ Connected successfully!")

        # Test fetching candles
        print("\n2. Fetching BTC candles (1h, last 10)...")
        candles = connector.fetch_ohlcv('BTC', timeframe='1h', limit=10)

        if candles:
            print(f"✅ Fetched {len(candles)} candles")
            print("\nLatest candle:")
            latest = candles[-1]
            print(f"  Timestamp: {datetime.fromtimestamp(latest[0]/1000)}")
            print(f"  Open:  ${latest[1]:.2f}")
            print(f"  High:  ${latest[2]:.2f}")
            print(f"  Low:   ${latest[3]:.2f}")
            print(f"  Close: ${latest[4]:.2f}")
            print(f"  Volume: {latest[5]:.2f}")

        # Test getting markets
        print("\n3. Fetching available markets...")
        markets = connector.get_available_markets()
        if markets:
            print(f"✅ Found {len(markets)} markets")
            print(f"Sample markets: {markets[:10]}")

    else:
        print("❌ Connection failed")

    print("\n" + "="*60)
    print("✅ Test complete!")
