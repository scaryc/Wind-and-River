"""
Utility functions for Wind Catcher & River Turn Trading System
Handles paths, configuration, database connections, and common operations
"""

import os
import sys
import sqlite3
import yaml
from pathlib import Path
from datetime import datetime

# Get the absolute path to the trading_system directory
# This works regardless of where the script is run from
TRADING_SYSTEM_DIR = Path(__file__).resolve().parent

# Define all paths relative to TRADING_SYSTEM_DIR
CONFIG_DIR = TRADING_SYSTEM_DIR / 'config'
DATA_DIR = TRADING_SYSTEM_DIR / 'data'
LOGS_DIR = TRADING_SYSTEM_DIR / 'logs'

CONFIG_FILE = CONFIG_DIR / 'config.yaml'
DATABASE_FILE = DATA_DIR / 'trading_system.db'
ALERTS_LOG = LOGS_DIR / 'alerts.log'


def ensure_directories():
    """
    Ensure all required directories exist
    Creates them if they don't exist
    """
    for directory in [CONFIG_DIR, DATA_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def load_config():
    """
    Load configuration from config.yaml with validation

    Returns:
        dict: Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid or missing required fields
    """
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {CONFIG_FILE}\n"
            f"Please create config/config.yaml in the trading_system directory."
        )

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {e}")

    # Validate required fields
    validate_config(config)

    return config


def validate_config(config):
    """
    Validate that configuration has all required fields

    Args:
        config (dict): Configuration dictionary

    Raises:
        ValueError: If required fields are missing or invalid
    """
    if not config:
        raise ValueError("Configuration file is empty")

    # Check for required sections
    required_sections = ['exchange', 'system']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required section in config: '{section}'")

    # Validate exchange section
    exchange = config.get('exchange', {})

    # Check exchange name
    if 'name' not in exchange:
        raise ValueError("Missing required field in exchange config: 'name'")
    if not isinstance(exchange['name'], str):
        raise ValueError("exchange.name must be a string")

    # Validate Hyperliquid-specific config
    if exchange['name'].lower() == 'hyperliquid':
        if 'use_testnet' in exchange and not isinstance(exchange['use_testnet'], bool):
            raise ValueError("exchange.use_testnet must be a boolean (true/false)")
    # For other exchanges that might need API keys
    elif 'api_key' in exchange or 'api_secret' in exchange:
        if not exchange.get('api_key') or not isinstance(exchange['api_key'], str):
            raise ValueError("Invalid value for exchange.api_key")
        if not exchange.get('api_secret') or not isinstance(exchange['api_secret'], str):
            raise ValueError("Invalid value for exchange.api_secret")

    # Validate system section
    system = config.get('system', {})
    if 'test_mode' in system and not isinstance(system['test_mode'], bool):
        raise ValueError("system.test_mode must be a boolean (true/false)")

    if 'max_api_calls_per_second' in system:
        if not isinstance(system['max_api_calls_per_second'], (int, float)):
            raise ValueError("system.max_api_calls_per_second must be a number")
        if system['max_api_calls_per_second'] <= 0:
            raise ValueError("system.max_api_calls_per_second must be positive")


def database_exists():
    """
    Check if database file exists

    Returns:
        bool: True if database exists, False otherwise
    """
    return DATABASE_FILE.exists()


def connect_to_database():
    """
    Connect to SQLite database with proper path handling and validation

    Returns:
        sqlite3.Connection: Database connection

    Raises:
        FileNotFoundError: If database doesn't exist
        sqlite3.Error: If connection fails
    """
    if not database_exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_FILE}\n"
            f"Please run database_setup.py first to create the database."
        )

    try:
        conn = sqlite3.connect(str(DATABASE_FILE))
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        raise sqlite3.Error(f"Failed to connect to database: {e}")


def validate_ohlcv_data(candle):
    """
    Validate OHLCV candle data from exchange

    Args:
        candle (list): [timestamp, open, high, low, close, volume]

    Returns:
        bool: True if valid, False otherwise

    Raises:
        ValueError: If data is invalid with description of the problem
    """
    if not candle or len(candle) < 6:
        raise ValueError(f"Invalid candle format: expected 6 values, got {len(candle) if candle else 0}")

    timestamp, open_price, high, low, close, volume = candle[:6]

    # Validate timestamp (should be positive and reasonable)
    if not isinstance(timestamp, (int, float)) or timestamp <= 0:
        raise ValueError(f"Invalid timestamp: {timestamp}")

    # Timestamps should be in milliseconds (13 digits) or seconds (10 digits)
    if timestamp < 1000000000 or timestamp > 9999999999999:
        raise ValueError(f"Timestamp out of reasonable range: {timestamp}")

    # Validate prices (must be positive numbers)
    prices = {'open': open_price, 'high': high, 'low': low, 'close': close}
    for name, price in prices.items():
        if not isinstance(price, (int, float)):
            raise ValueError(f"Invalid {name} price type: {type(price)}")
        if price <= 0:
            raise ValueError(f"Invalid {name} price: {price} (must be positive)")
        if price > 1e10:  # Sanity check: no crypto costs more than 10 billion
            raise ValueError(f"Invalid {name} price: {price} (unreasonably high)")

    # Validate OHLC relationship (High >= Low, High >= Open/Close, Low <= Open/Close)
    if high < low:
        raise ValueError(f"High ({high}) cannot be less than Low ({low})")
    if high < open_price or high < close:
        raise ValueError(f"High ({high}) must be >= Open ({open_price}) and Close ({close})")
    if low > open_price or low > close:
        raise ValueError(f"Low ({low}) must be <= Open ({open_price}) and Close ({close})")

    # Validate volume (must be non-negative)
    if not isinstance(volume, (int, float)):
        raise ValueError(f"Invalid volume type: {type(volume)}")
    if volume < 0:
        raise ValueError(f"Invalid volume: {volume} (cannot be negative)")

    return True


def normalize_timestamp(timestamp):
    """
    Normalize timestamp to seconds (Unix timestamp)
    Handles both milliseconds and seconds timestamps

    Args:
        timestamp (int/float): Timestamp in seconds or milliseconds

    Returns:
        int: Timestamp in seconds
    """
    # If timestamp is in milliseconds (> 13 digits when ms), convert to seconds
    if timestamp > 10000000000:  # This is year 2286 in seconds, so anything larger is milliseconds
        return int(timestamp // 1000)
    return int(timestamp)


def get_current_timestamp():
    """
    Get current Unix timestamp in seconds

    Returns:
        int: Current timestamp in seconds
    """
    return int(datetime.now().timestamp())


def format_timestamp(timestamp, format_str='%Y-%m-%d %H:%M:%S'):
    """
    Format Unix timestamp to readable string

    Args:
        timestamp (int): Unix timestamp in seconds
        format_str (str): strftime format string

    Returns:
        str: Formatted timestamp
    """
    return datetime.fromtimestamp(timestamp).strftime(format_str)


def log_message(message, level='INFO'):
    """
    Log message to alerts.log file with proper encoding

    Args:
        message (str): Message to log
        level (str): Log level (INFO, WARNING, ERROR, SUCCESS)
    """
    ensure_directories()

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {level}: {message}\n"

    try:
        with open(ALERTS_LOG, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to write to log file: {e}")

    # Also print to console
    print(f"{timestamp} - {message}")


def get_python_executable():
    """
    Get the current Python executable path
    More reliable than using 'py' or 'python'

    Returns:
        str: Path to Python executable
    """
    return sys.executable


# Initialize directories on import
ensure_directories()
