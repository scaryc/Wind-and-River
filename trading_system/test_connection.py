"""
Your First Trading System Script
This connects to Gate.io and fetches current prices
"""

import ccxt
import yaml
import time
from datetime import datetime

def load_config():
    """Load settings from your config file"""
    try:
        with open('config/config.yaml', 'r') as file:
            config = yaml.safe_load(file)
            print("✅ Config loaded successfully!")
            return config
    except FileNotFoundError:
        print("❌ Config file not found. Make sure config/config.yaml exists")
        return None
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

def connect_to_exchange(config):
    """Connect to Gate.io exchange"""
    try:
        # Create exchange connection
        exchange = ccxt.gateio({
            'apiKey': config['exchange']['api_key'],
            'secret': config['exchange']['api_secret'],
            'enableRateLimit': True,  # Automatic rate limiting
            'options': {
                'defaultType': 'spot',  # Start with spot market
            }
        })
        
        # Test the connection
        exchange.load_markets()
        print(f"✅ Connected to {config['exchange']['name']}!")
        print(f"   Found {len(exchange.markets)} markets")
        return exchange
        
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return None

def fetch_prices(exchange, watchlist):
    """Fetch current prices for your watchlist"""
    print("\n📊 Current Prices:")
    print("-" * 40)
    
    for symbol in watchlist:
        try:
            # Fetch ticker data
            ticker = exchange.fetch_ticker(symbol)
            
            # Extract key information
            current_price = ticker['last']
            change_24h = ticker['percentage'] if ticker['percentage'] else 0
            volume_24h = ticker['quoteVolume'] if ticker['quoteVolume'] else 0
            
            # Display nicely
            print(f"\n{symbol}:")
            print(f"  Price: ${current_price:,.2f}")
            print(f"  24h Change: {change_24h:+.2f}%")
            print(f"  24h Volume: ${volume_24h:,.0f}")
            
            # Small delay to be nice to the API
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ⚠️ Error fetching {symbol}: {e}")

def main():
    """Main function - this runs everything"""
    print("=" * 50)
    print("🚀 Wind Catcher & River Turn Trading System")
    print("   Connection Test Script")
    print("=" * 50)
    
    # Step 1: Load configuration
    config = load_config()
    if not config:
        print("\n⚠️ Please create config/config.yaml first!")
        return
    
    # Step 2: Check if using default keys
    if config['exchange']['api_key'] == "YOUR_API_KEY_HERE":
        print("\n⚠️ Please add your Gate.io API keys to config/config.yaml")
        print("   1. Log into Gate.io")
        print("   2. Go to Account → API Management")
        print("   3. Create a new API key (READ-ONLY for safety!)")
        print("   4. Copy the keys into config/config.yaml")
        return
    
    # Step 3: Connect to exchange
    exchange = connect_to_exchange(config)
    if not exchange:
        print("\n⚠️ Could not connect to exchange. Check your API keys.")
        return
    
    # Step 4: Fetch current prices
    watchlist = config.get('watchlist', ['BTC/USDT'])
    fetch_prices(exchange, watchlist)
    
    print("\n" + "=" * 50)
    print("✅ Test completed successfully!")
    print("   Your connection to Gate.io is working!")
    print("=" * 50)

# This is the entry point - when you run the script, it starts here
if __name__ == "__main__":
    main()