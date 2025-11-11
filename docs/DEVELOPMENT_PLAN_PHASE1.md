# Wind Catcher & River Turn - Development Plan Phase 1
## Detailed Implementation Roadmap

**Version**: 1.0
**Date**: 2025-11-09
**Scope**: Foundation + Web Interface + Telegram Alerts

---

## 🎯 PROJECT VISION

Build a web-based cryptocurrency trading system that:
- Monitors multiple trading pairs across 3 timeframes (8h, 1h, 15m)
- Generates confluence-based signals using 5 technical indicators
- Provides real-time alerts via Telegram
- Allows manual control of which pairs to scan on which timeframes
- Displays signals in a clean, terminal-style chat interface

---

## 📐 CORE REQUIREMENTS CONSENSUS

### Backtesting
- **Period**: October 3, 2024 → November 3, 2024 (1 month)
- **Pairs**: BTC/USDT, TAO/USDT, HYPE/USDT
- **Purpose**: Validate signal quality manually against TradingView
- **Output**: List of all GOOD+ signals for manual review

### Web Interface Layout
```
┌─────────────────────────────────────────────────────────┐
│         WIND CATCHER & RIVER TURN - Trading System       │
└─────────────────────────────────────────────────────────┘
┌────────────┬──────────────────────────┬────────────────┐
│  WIND      │    SIGNAL CHAT           │   RIVER        │
│  CATCHER   │    TERMINAL              │   TURN         │
│  (25%)     │    (50%)                 │   (25%)        │
│            │                          │                │
│ 8h  WL [+] │ [14:30:22] 🌪️ PERFECT   │ 8h  WL [+]    │
│ ┌────────┐ │ BTC/USDT Bullish        │ ┌────────┐    │
│ │BTC  [x]│ │ $67,234 | Score: 3.2    │ │ETH  [x]│    │
│ │SOL  [x]│ │ Hull+AO+Vol | 8h        │ │SOL  [x]│    │
│ └────────┘ │                          │ └────────┘    │
│            │ [14:28:15] 🌊 GOOD      │                │
│ 1h  WL [+] │ ETH/USDT Bearish        │ 1h  WL [+]    │
│ ┌────────┐ │ $3,456 | Score: 1.5     │ ┌────────┐    │
│ │BTC  [x]│ │ Hull+Ichi | 1h          │ │TAO  [x]│    │
│ │TAO  [x]│ │                          │ │HYPE [x]│    │
│ └────────┘ │ [Scrolling...]          │ └────────┘    │
│            │                          │                │
│ 15m WL [+] │                          │ 15m WL [+]    │
│ ┌────────┐ │                          │ ┌────────┐    │
│ │BTC  [x]│ │                          │ │BTC  [x]│    │
│ │SOL  [x]│ │                          │ │ETH  [x]│    │
│ └────────┘ │                          │ └────────┘    │
└────────────┴──────────────────────────┴────────────────┘
```

### Watchlist Behavior (CRITICAL CLARIFICATION)
- **User-Controlled**: Watchlists are NOT auto-populated by signals
- **Manual Management**: User adds/removes/moves pairs between watchlists
- **Use Case**:
  - Add BTC to "8h Wind Catcher" → system scans BTC on 8h for bullish signals
  - Take long position based on signal
  - Move BTC to "1h River Turn" → system now scans BTC on 1h for bearish exit signals
  - Allows hedging and timeframe strategy switching

### Chat Window Behavior
- **Content**: Only GOOD, EXCELLENT, or PERFECT confluence signals
- **Format**: Terminal-style (new messages append to bottom)
- **Timeframe**: Shows signals from ALL timeframes (8h, 1h, 15m)
- **Action**: Informational only (user analyzes on TradingView independently)

### Technical Decisions
- **API Call Frequency**: Every 5 minutes (balance cost vs freshness)
- **UI Update Frequency**: Every 60 seconds (browser polls server)
- **Backend**: Simple (Flask or FastAPI + SQLite)
- **Frontend**: Simple, visually calming (HTML/CSS/JS, possibly lightweight framework)
- **Platform**: Desktop browser only (no mobile responsive for Phase 1)
- **Verification Scripts**: Skipped for now (trust existing calculations)

---

## 🏗️ ARCHITECTURE OVERVIEW

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                     GATE.IO EXCHANGE                     │
│                      (Data Source)                       │
└────────────────────┬────────────────────────────────────┘
                     │ CCXT API (every 5 min)
                     ↓
┌─────────────────────────────────────────────────────────┐
│              DATA COLLECTION SERVICE                     │
│  - Fetches OHLCV for all pairs in all watchlists       │
│  - Stores in SQLite database                            │
│  - Runs as background job                               │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│                 SQLITE DATABASE                          │
│  - price_data (OHLCV candles)                          │
│  - watchlists (user's pair assignments)                │
│  - signals (generated confluence signals)               │
│  - user_settings                                        │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│              SIGNAL ANALYSIS ENGINE                      │
│  - Calculates 5 indicators per pair/timeframe          │
│  - Detects confluence signals                           │
│  - Stores GOOD+ signals in database                    │
│  - Runs as background job (every 5 min)                │
└────────────┬───────────────────────────┬────────────────┘
             ↓                           ↓
┌────────────────────────┐   ┌──────────────────────────┐
│   TELEGRAM BOT SERVICE │   │   WEB SERVER (Flask)     │
│ - Sends alerts for     │   │ - Serves HTML/CSS/JS     │
│   EXCELLENT+ signals   │   │ - REST API endpoints     │
│ - Runs as bg service   │   │ - Returns watchlists     │
└────────────────────────┘   │ - Returns signal feed    │
                              │ - Updates every 60s      │
                              └──────────┬───────────────┘
                                         ↓
                              ┌──────────────────────────┐
                              │   WEB BROWSER (Frontend) │
                              │ - 3-column layout        │
                              │ - Drag-drop watchlists   │
                              │ - Signal chat feed       │
                              │ - Polls server every 60s │
                              └──────────────────────────┘
```

---

## 📋 DEVELOPMENT PHASES

---

## **PHASE 1A: FOUNDATION & VALIDATION**
### Duration: 1 week
### Priority: CRITICAL (Must complete before UI development)

---

### **GROUP 1.1: Multi-Timeframe Data Collection**

**Objective**: Extend current 1h-only system to collect 8h and 15m data

#### Task 1.1.1: Update Database Schema
**File**: `trading_system/database_setup.py`

**Changes Needed**:
```python
# Existing price_data table already supports multiple timeframes
# Add index for performance
CREATE INDEX idx_symbol_timeframe_timestamp
  ON price_data(symbol, timeframe, timestamp);

# New table: watchlists (replaces simple watchlist table)
CREATE TABLE user_watchlists (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,  -- '8h', '1h', '15m'
    direction TEXT NOT NULL,  -- 'wind_catcher', 'river_turn'
    added_at INTEGER NOT NULL,
    notes TEXT,
    UNIQUE(symbol, timeframe, direction)
);

# New table: signals (already exists, verify schema)
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY,
    timestamp INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,  -- ADD THIS FIELD
    system TEXT NOT NULL,      -- 'wind_catcher' or 'river_turn'
    signal_type TEXT NOT NULL,
    confluence_score REAL NOT NULL,
    confluence_class TEXT NOT NULL,  -- 'GOOD', 'EXCELLENT', 'PERFECT'
    price REAL NOT NULL,
    indicators_firing TEXT,   -- JSON: {"hull": 2, "ao": 1, ...}
    volume_level TEXT,        -- 'NORMAL', 'WARMING', 'HOT', 'CLIMAX'
    volume_ratio REAL,
    details TEXT,             -- JSON: full signal details
    notified BOOLEAN DEFAULT 0,  -- sent to Telegram?
    created_at INTEGER NOT NULL
);

CREATE INDEX idx_signals_timestamp ON signals(timestamp DESC);
CREATE INDEX idx_signals_symbol_timeframe ON signals(symbol, timeframe);
```

**Acceptance Criteria**:
- [ ] Database migration script created
- [ ] New tables created successfully
- [ ] Indexes added for performance
- [ ] Backward compatible with existing data

---

#### Task 1.1.2: Multi-Timeframe Data Collector
**File**: `trading_system/multi_timeframe_collector.py` (NEW)

**Purpose**: Fetch 8h, 1h, 15m candles for all pairs in watchlists

**Key Functions**:
```python
def get_active_watchlist_pairs(conn):
    """Get unique symbols from all user watchlists"""
    # Query user_watchlists table
    # Return set of unique symbols

def fetch_ohlcv_multi_timeframe(exchange, symbol, timeframes, limit):
    """Fetch multiple timeframes for one symbol"""
    # timeframes = ['8h', '1h', '15m']
    # limit = 200 candles per timeframe
    # Return dict: {timeframe: ohlcv_data}

def collect_all_watchlist_data(conn, config):
    """Main collection loop"""
    # 1. Get all pairs from user_watchlists
    # 2. For each pair, fetch 8h, 1h, 15m
    # 3. Store in price_data table
    # 4. Handle API rate limits (sleep between calls)
    # 5. Log progress and errors
```

**Features**:
- Fetch only pairs that are in ANY watchlist
- Handle Gate.io rate limits (max 2 calls/sec)
- Graceful error handling (continue on failures)
- Progress logging

**Acceptance Criteria**:
- [ ] Successfully fetches 8h, 1h, 15m data
- [ ] Stores all timeframes in database
- [ ] Respects API rate limits
- [ ] Handles missing/delisted pairs gracefully
- [ ] Logs collection statistics

---

#### Task 1.1.3: Update Existing Indicators for Multi-Timeframe
**Files**: `indicators.py`, `enhanced_indicators.py`, `alligator_analyzer.py`, `ichimoku_analyzer.py`, `volume_analyzer.py`

**Changes**: Currently hardcoded to `timeframe='1h'`

**Modifications**:
```python
# BEFORE
def analyze_symbol(conn, symbol):
    df = get_price_data(conn, symbol, timeframe='1h', limit=100)

# AFTER
def analyze_symbol(conn, symbol, timeframe='1h'):
    df = get_price_data(conn, symbol, timeframe=timeframe, limit=100)
    # All functions now accept timeframe parameter
```

**Files to Update**:
- `indicators.py`: `analyze_symbol(conn, symbol, timeframe='1h')`
- `enhanced_indicators.py`: `analyze_symbol_with_ao(conn, symbol, timeframe='1h')`
- `alligator_analyzer.py`: `analyze_symbol_alligator(conn, symbol, timeframe='1h')`
- `ichimoku_analyzer.py`: `analyze_symbol_ichimoku(conn, symbol, timeframe='1h')`
- `volume_analyzer.py`: `analyze_symbol_volume(conn, symbol, timeframe='1h')`

**Acceptance Criteria**:
- [ ] All analyzer functions accept timeframe parameter
- [ ] Default remains '1h' for backward compatibility
- [ ] Test with '8h', '1h', '15m' data
- [ ] Results accurate for each timeframe

---

### **GROUP 1.2: Backtesting System**

**Objective**: Generate historical signals for Oct 3 - Nov 3, 2024

---

#### Task 1.2.1: Historical Data Downloader
**File**: `trading_system/backtest_data_downloader.py` (NEW)

**Purpose**: Fetch 1 month of historical data for backtesting

**Specification**:
```python
def download_historical_data(symbol, timeframe, start_date, end_date):
    """
    Download OHLCV data for specified period

    Parameters:
    - symbol: 'BTC/USDT', 'TAO/USDT', 'HYPE/USDT'
    - timeframe: '1h' (backtest only on 1h for now)
    - start_date: '2024-10-03'
    - end_date: '2024-11-03'

    Returns:
    - DataFrame with OHLCV + timestamp
    """
    # Gate.io has limit on historical data per request
    # May need to fetch in chunks (7 days at a time)
    # Combine chunks into single dataset
    # Store in database with is_backtest flag?
```

**Steps**:
1. Convert dates to Unix timestamps
2. Calculate number of candles needed (~744 hours in 31 days)
3. Fetch in batches if needed (Gate.io limit: ~1000 candles/request)
4. Store in database or CSV for backtesting

**Acceptance Criteria**:
- [ ] Downloads complete Oct 3 - Nov 3 data for BTC/USDT
- [ ] Downloads complete Oct 3 - Nov 3 data for TAO/USDT
- [ ] Downloads complete Oct 3 - Nov 3 data for HYPE/USDT
- [ ] Handles API errors gracefully
- [ ] Data stored in usable format (DB or CSV)

---

#### Task 1.2.2: Backtest Signal Generator
**File**: `trading_system/backtest_runner.py` (NEW)

**Purpose**: Replay history and generate signals as if running live

**Logic**:
```python
def run_backtest(symbol, timeframe, start_date, end_date):
    """
    Replay candle-by-candle and detect signals

    Process:
    1. Load historical data
    2. For each candle (starting at candle 150 - need history for indicators):
       a. Calculate all 5 indicators with data up to that point
       b. Check for confluence signals
       c. If GOOD+ signal, record it
    3. Generate report

    Output: CSV or JSON with all signals
    """

# Signal Record Format:
{
    "timestamp": 1696348800,  # Unix timestamp
    "datetime": "2024-10-03 14:00:00",
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "direction": "wind_catcher",  # or "river_turn"
    "confluence_score": 2.8,
    "confluence_class": "EXCELLENT",
    "price": 67234.50,
    "indicators_firing": {
        "hull": 2,
        "ao": 1,
        "alligator": 0,
        "ichimoku": 1,
        "volume": 1
    },
    "volume_level": "HOT",
    "volume_ratio": 2.3,
    "signal_details": "First close above Hull 21, AO bullish, Volume HOT"
}
```

**Features**:
- No lookahead bias (only use data available at that moment)
- Calculate indicators correctly for each timepoint
- Filter: only GOOD, EXCELLENT, PERFECT (score ≥ 1.2)
- Generate both human-readable report and structured data

**Acceptance Criteria**:
- [ ] Replays Oct 3 - Nov 3 correctly
- [ ] Generates signals without lookahead bias
- [ ] Outputs CSV/JSON with all signals
- [ ] Creates summary report (total signals per pair)

---

#### Task 1.2.3: Backtest Report Generator
**File**: `trading_system/backtest_reporter.py` (NEW)

**Purpose**: Create readable report for manual signal review

**Report Format**:
```markdown
# BACKTEST REPORT
## Wind Catcher & River Turn Trading System
**Period**: October 3, 2024 - November 3, 2024
**Timeframe**: 1h
**Pairs**: BTC/USDT, TAO/USDT, HYPE/USDT

---

## SUMMARY

Total Signals: 47
- BTC/USDT: 18 signals (12 bullish, 6 bearish)
- TAO/USDT: 15 signals (8 bullish, 7 bearish)
- HYPE/USDT: 14 signals (9 bullish, 5 bearish)

By Confluence:
- PERFECT (≥3.0): 8 signals
- EXCELLENT (2.5-2.9): 12 signals
- VERY GOOD (1.8-2.4): 15 signals
- GOOD (1.2-1.7): 12 signals

---

## SIGNAL LOG

### BTC/USDT

#### Signal #1 - PERFECT Bullish 🌪️
- **Date**: 2024-10-03 14:00:00 UTC
- **Price**: $67,234.50
- **Score**: 3.2
- **Indicators**: Hull(2), AO(1), Alligator(1), Ichimoku(1), Volume(1)
- **Volume**: HOT (2.3x average)
- **Details**:
  - First close above Hull 21
  - AO bullish divergence detected
  - Price touched Alligator blue line
  - Ichimoku Kijun support
  - Volume confirmation
- **TradingView Link**: [Chart at this timestamp]

#### Signal #2 - EXCELLENT Bearish 🌊
- **Date**: 2024-10-05 08:00:00 UTC
- **Price**: $68,450.00
- **Score**: 2.7
...

[Continue for all 47 signals]

---

## VERIFICATION CHECKLIST

For manual review on TradingView:
- [ ] Signal #1: BTC/USDT 2024-10-03 14:00 - Verified ✓
- [ ] Signal #2: BTC/USDT 2024-10-05 08:00 - Verified ✓
...
```

**Acceptance Criteria**:
- [ ] Generates Markdown report
- [ ] Lists all signals chronologically per pair
- [ ] Includes verification checklist
- [ ] Easy to review on TradingView

---

### **GROUP 1.3: Multi-Timeframe Master Confluence**

**Objective**: Extend master_confluence.py to support 8h, 1h, 15m

---

#### Task 1.3.1: Update Master Confluence for Timeframe Parameter
**File**: `trading_system/master_confluence.py`

**Changes**:
```python
# BEFORE
def analyze_master_confluence(conn, symbol):
    # Hardcoded to 1h

# AFTER
def analyze_master_confluence(conn, symbol, timeframe='1h'):
    """Analyze confluence for specific symbol and timeframe"""
    df = get_price_data(conn, symbol, timeframe=timeframe, limit=200)

    # Call all analyzers with timeframe parameter
    hull_signals = get_hull_signals(conn, symbol, timeframe)
    ao_signals = get_ao_signals(conn, symbol, timeframe)
    alligator_signals = get_alligator_signals(conn, symbol, timeframe)
    ichimoku_signals = get_ichimoku_signals(conn, symbol, timeframe)
    volume_signals = detect_volume_signals(df.copy(), timeframe)

    # Rest of logic remains same
```

**Acceptance Criteria**:
- [ ] Accepts timeframe parameter
- [ ] Works with '8h', '1h', '15m'
- [ ] Returns consistent signal format
- [ ] Tested on all three timeframes

---

#### Task 1.3.2: Signal Detector Service (Background Job)
**File**: `trading_system/signal_detector_service.py` (NEW)

**Purpose**: Continuously scan watchlists and detect new signals

**Logic**:
```python
def run_signal_detection_loop():
    """
    Main service loop - runs every 5 minutes

    Process:
    1. Get all active watchlists from user_watchlists table
    2. For each (symbol, timeframe, direction):
       - Run master_confluence analysis
       - If GOOD+ signal found in correct direction:
         - Check if signal already exists (within last 4 hours)
         - If new: Insert into signals table
         - Flag for Telegram notification
    3. Sleep for 5 minutes
    4. Repeat
    """
    while True:
        try:
            conn = connect_to_database()

            # Get watchlists
            watchlists = get_user_watchlists(conn)
            # Returns: [(symbol, timeframe, direction), ...]

            new_signals = []

            for symbol, timeframe, direction in watchlists:
                result = analyze_master_confluence(conn, symbol, timeframe)

                if result and result['confluence']['score'] >= 1.2:
                    # Check if signal matches watchlist direction
                    signal_system = result['confluence']['primary_system']

                    if signal_system == direction:
                        # Check if signal already recorded
                        if not signal_exists(conn, symbol, timeframe,
                                            timestamp=result['timestamp'],
                                            hours_window=4):
                            # New signal - save it
                            signal_id = save_signal(conn, result)
                            new_signals.append(signal_id)

            conn.close()

            # Log results
            print(f"[{datetime.now()}] Scanned {len(watchlists)} pairs. "
                  f"Found {len(new_signals)} new signals.")

            # Wait 5 minutes
            time.sleep(300)

        except Exception as e:
            print(f"Error in signal detection: {e}")
            time.sleep(60)  # Wait 1 min on error, then retry
```

**Features**:
- Runs as background service (daemon)
- Scans only pairs in user_watchlists
- Respects direction filter (only save matching signals)
- Deduplicates signals (don't alert same signal twice)
- Handles errors gracefully (continues running)

**Acceptance Criteria**:
- [ ] Runs continuously every 5 minutes
- [ ] Scans all watchlist pairs
- [ ] Detects new signals correctly
- [ ] Saves to signals table
- [ ] Logs activity
- [ ] Handles errors without crashing

---

## **PHASE 1B: WEB INTERFACE**
### Duration: 2 weeks
### Priority: HIGH (Core user interface)

---

### **GROUP 1.4: Backend API Development**

**Objective**: Create Flask/FastAPI server with REST endpoints

---

#### Task 1.4.1: Project Structure Setup
**Directory**: `trading_system/web/`

**Structure**:
```
trading_system/web/
├── app.py                    # Main Flask application
├── api/
│   ├── __init__.py
│   ├── watchlist_routes.py   # Watchlist CRUD endpoints
│   ├── signal_routes.py      # Signal feed endpoints
│   └── system_routes.py      # System status endpoints
├── static/
│   ├── css/
│   │   └── style.css         # Main stylesheet
│   ├── js/
│   │   ├── app.js            # Main application logic
│   │   ├── watchlist.js      # Watchlist management
│   │   └── signals.js        # Signal feed updates
│   └── images/
│       └── logo.png
├── templates/
│   ├── index.html            # Main dashboard
│   └── layout.html           # Base template
└── requirements.txt          # Python dependencies
```

**Acceptance Criteria**:
- [ ] Directory structure created
- [ ] Flask app skeleton set up
- [ ] Can run server locally
- [ ] Serves static files correctly

---

#### Task 1.4.2: Database Helper Functions
**File**: `trading_system/web/api/db_helpers.py` (NEW)

**Purpose**: Centralize database operations for API

**Functions**:
```python
# Watchlist Operations
def get_user_watchlists(direction=None, timeframe=None):
    """Get all watchlists, optionally filtered"""

def add_to_watchlist(symbol, timeframe, direction):
    """Add symbol to a specific watchlist"""

def remove_from_watchlist(symbol, timeframe, direction):
    """Remove symbol from watchlist"""

def move_between_watchlists(symbol, from_tf, from_dir, to_tf, to_dir):
    """Move symbol from one watchlist to another"""

# Signal Operations
def get_recent_signals(limit=50, min_score=1.2):
    """Get recent signals for chat feed"""

def get_signal_by_id(signal_id):
    """Get full signal details"""

def mark_signal_notified(signal_id):
    """Mark signal as sent to Telegram"""

# System Status
def get_system_status():
    """Return system health info"""
    return {
        'last_data_update': timestamp,
        'total_signals_today': count,
        'active_watchlist_pairs': count,
        'api_status': 'ok'
    }
```

**Acceptance Criteria**:
- [ ] All functions implemented
- [ ] Error handling included
- [ ] Returns consistent data structures
- [ ] Tested with sample data

---

#### Task 1.4.3: Watchlist API Endpoints
**File**: `trading_system/web/api/watchlist_routes.py`

**Endpoints**:

```python
# GET /api/watchlists
# Returns all watchlists organized by direction and timeframe
{
    "wind_catcher": {
        "8h": ["BTC/USDT", "SOL/USDT"],
        "1h": ["BTC/USDT", "TAO/USDT"],
        "15m": ["BTC/USDT", "SOL/USDT"]
    },
    "river_turn": {
        "8h": ["ETH/USDT", "SOL/USDT"],
        "1h": ["TAO/USDT", "HYPE/USDT"],
        "15m": ["BTC/USDT", "ETH/USDT"]
    }
}

# POST /api/watchlist/add
# Body: {"symbol": "BTC/USDT", "timeframe": "1h", "direction": "wind_catcher"}
# Response: {"success": true, "message": "Added to watchlist"}

# DELETE /api/watchlist/remove
# Body: {"symbol": "BTC/USDT", "timeframe": "1h", "direction": "wind_catcher"}
# Response: {"success": true, "message": "Removed from watchlist"}

# POST /api/watchlist/move
# Body: {
#   "symbol": "BTC/USDT",
#   "from": {"timeframe": "8h", "direction": "wind_catcher"},
#   "to": {"timeframe": "1h", "direction": "river_turn"}
# }
# Response: {"success": true, "message": "Moved to new watchlist"}

# GET /api/watchlist/available-symbols
# Returns list of all symbols from Gate.io
# (For autocomplete when adding new pairs)
```

**Acceptance Criteria**:
- [ ] All endpoints implemented
- [ ] Request validation (check valid timeframes, directions)
- [ ] Error handling with proper HTTP status codes
- [ ] Tested with Postman/curl

---

#### Task 1.4.4: Signal Feed API Endpoints
**File**: `trading_system/web/api/signal_routes.py`

**Endpoints**:

```python
# GET /api/signals/recent?limit=50&since=<timestamp>
# Returns recent signals for chat feed
# If 'since' provided, returns only signals after that timestamp
{
    "signals": [
        {
            "id": 123,
            "timestamp": 1699545600,
            "datetime": "2024-11-09 14:30:00",
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "direction": "wind_catcher",
            "confluence_score": 3.2,
            "confluence_class": "PERFECT",
            "price": 67234.50,
            "indicators_summary": "Hull(2), AO(1), Alligator(1), Ichimoku(1), Volume(1)",
            "volume_level": "HOT",
            "emoji": "⭐",
            "system_emoji": "🌪️"
        },
        ...
    ],
    "latest_timestamp": 1699545600
}

# GET /api/signals/<signal_id>
# Returns full details for specific signal
{
    "id": 123,
    "timestamp": 1699545600,
    "symbol": "BTC/USDT",
    "confluence": {...},
    "indicators_firing": {...},
    "full_details": "..."
}

# GET /api/signals/stats
# Returns signal statistics for dashboard
{
    "total_today": 15,
    "perfect_count": 3,
    "excellent_count": 5,
    "by_direction": {
        "wind_catcher": 8,
        "river_turn": 7
    }
}
```

**Acceptance Criteria**:
- [ ] All endpoints implemented
- [ ] Efficient queries (use indexes)
- [ ] Returns formatted data ready for frontend
- [ ] Tested with sample data

---

#### Task 1.4.5: System Status Endpoints
**File**: `trading_system/web/api/system_routes.py`

**Endpoints**:

```python
# GET /api/system/status
# Overall system health
{
    "status": "ok",  # or "warning", "error"
    "last_data_collection": "2024-11-09 14:25:00",
    "next_data_collection": "2024-11-09 14:30:00",
    "last_signal_scan": "2024-11-09 14:25:00",
    "database_size_mb": 45.2,
    "active_pairs": 8,
    "signals_today": 15
}

# GET /api/system/pairs
# List all available trading pairs (for adding to watchlist)
{
    "pairs": ["BTC/USDT", "ETH/USDT", "SOL/USDT", ...],
    "total": 150
}
```

**Acceptance Criteria**:
- [ ] Returns accurate system status
- [ ] Helps user monitor system health
- [ ] Fast response times

---

### **GROUP 1.5: Frontend Development**

**Objective**: Build clean, calming, functional web interface

**Tech Stack Decision**: HTML + CSS + Vanilla JavaScript (or lightweight Alpine.js/Vue.js)

---

#### Task 1.5.1: Base HTML Structure
**File**: `trading_system/web/templates/index.html`

**Structure**:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wind Catcher & River Turn - Trading System</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <!-- Header -->
    <header class="header">
        <h1>🌪️ Wind Catcher & River Turn 🌊</h1>
        <div class="system-status">
            <span id="status-indicator">●</span>
            <span id="status-text">System Active</span>
        </div>
    </header>

    <!-- Main Container -->
    <div class="main-container">
        <!-- Left: Wind Catcher Watchlists -->
        <aside class="watchlist-panel wind-catcher">
            <h2>🌪️ Wind Catcher (Bullish)</h2>

            <div class="watchlist" data-timeframe="8h">
                <h3>8h Timeframe <button class="add-btn">+</button></h3>
                <ul class="pair-list" id="wind-8h"></ul>
            </div>

            <div class="watchlist" data-timeframe="1h">
                <h3>1h Timeframe <button class="add-btn">+</button></h3>
                <ul class="pair-list" id="wind-1h"></ul>
            </div>

            <div class="watchlist" data-timeframe="15m">
                <h3>15m Timeframe <button class="add-btn">+</button></h3>
                <ul class="pair-list" id="wind-15m"></ul>
            </div>
        </aside>

        <!-- Center: Signal Chat Terminal -->
        <main class="signal-feed">
            <h2>📡 Signal Feed</h2>
            <div id="signal-terminal" class="terminal">
                <!-- Signals appear here, terminal style -->
            </div>
            <div class="terminal-input">
                <span class="prompt">></span>
                <span class="cursor">_</span>
            </div>
        </main>

        <!-- Right: River Turn Watchlists -->
        <aside class="watchlist-panel river-turn">
            <h2>🌊 River Turn (Bearish)</h2>

            <div class="watchlist" data-timeframe="8h">
                <h3>8h Timeframe <button class="add-btn">+</button></h3>
                <ul class="pair-list" id="river-8h"></ul>
            </div>

            <div class="watchlist" data-timeframe="1h">
                <h3>1h Timeframe <button class="add-btn">+</button></h3>
                <ul class="pair-list" id="river-1h"></ul>
            </div>

            <div class="watchlist" data-timeframe="15m">
                <h3>15m Timeframe <button class="add-btn">+</button></h3>
                <ul class="pair-list" id="river-15m"></ul>
            </div>
        </aside>
    </div>

    <script src="/static/js/app.js"></script>
    <script src="/static/js/watchlist.js"></script>
    <script src="/static/js/signals.js"></script>
</body>
</html>
```

**Acceptance Criteria**:
- [ ] Clean semantic HTML
- [ ] Proper structure for CSS styling
- [ ] IDs/classes for JavaScript targeting
- [ ] Responsive to window resizing

---

#### Task 1.5.2: CSS Styling - Calming & Functional
**File**: `trading_system/web/static/css/style.css`

**Design Principles**:
- **Colors**: Calm blues/grays, not harsh whites
- **Font**: Monospace for terminal feel (Fira Code, JetBrains Mono, or Consolas)
- **Spacing**: Generous padding, not cramped
- **Visual Hierarchy**: Clear separation between sections

**Color Palette Suggestion**:
```css
:root {
    /* Dark theme - easier on eyes */
    --bg-primary: #1a1d29;       /* Deep navy */
    --bg-secondary: #242837;     /* Slightly lighter */
    --bg-tertiary: #2d3142;      /* Panel backgrounds */

    --text-primary: #e0e6ed;     /* Light gray */
    --text-secondary: #a0aec0;   /* Muted gray */

    --accent-wind: #4299e1;      /* Calm blue (Wind Catcher) */
    --accent-river: #f56565;     /* Calm red (River Turn) */
    --accent-success: #48bb78;   /* Green */
    --accent-warning: #ed8936;   /* Orange */

    --border: #3d4556;           /* Subtle borders */

    /* Signal colors */
    --perfect: #ffd700;          /* Gold */
    --excellent: #9f7aea;        /* Purple */
    --very-good: #4299e1;        /* Blue */
    --good: #48bb78;             /* Green */
}

/* Base styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    background-color: var(--bg-primary);
    color: var(--text-primary);
    overflow: hidden;  /* Prevent page scroll */
}

/* Header */
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 2rem;
    background-color: var(--bg-secondary);
    border-bottom: 2px solid var(--border);
}

.header h1 {
    font-size: 1.5rem;
    font-weight: 600;
}

.system-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
}

#status-indicator {
    color: var(--accent-success);
    font-size: 1.5rem;
}

/* Main Container: 25/50/25 layout */
.main-container {
    display: grid;
    grid-template-columns: 25% 50% 25%;
    height: calc(100vh - 80px);  /* Full height minus header */
    gap: 1rem;
    padding: 1rem;
}

/* Watchlist Panels */
.watchlist-panel {
    background-color: var(--bg-tertiary);
    border-radius: 8px;
    padding: 1rem;
    overflow-y: auto;
}

.watchlist-panel.wind-catcher {
    border-left: 4px solid var(--accent-wind);
}

.watchlist-panel.river-turn {
    border-right: 4px solid var(--accent-river);
}

.watchlist-panel h2 {
    font-size: 1.25rem;
    margin-bottom: 1.5rem;
    text-align: center;
}

/* Individual Watchlist */
.watchlist {
    background-color: var(--bg-secondary);
    border-radius: 6px;
    padding: 0.75rem;
    margin-bottom: 1rem;
}

.watchlist h3 {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.875rem;
    color: var(--text-secondary);
    margin-bottom: 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.add-btn {
    background-color: var(--accent-success);
    color: white;
    border: none;
    border-radius: 4px;
    padding: 0.25rem 0.5rem;
    cursor: pointer;
    font-size: 1rem;
    transition: opacity 0.2s;
}

.add-btn:hover {
    opacity: 0.8;
}

/* Pair List */
.pair-list {
    list-style: none;
    min-height: 60px;
}

.pair-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem;
    margin-bottom: 0.25rem;
    background-color: var(--bg-tertiary);
    border-radius: 4px;
    cursor: move;  /* Indicate draggable */
    transition: background-color 0.2s;
}

.pair-item:hover {
    background-color: var(--bg-primary);
}

.pair-name {
    font-weight: 500;
}

.remove-btn {
    color: var(--accent-river);
    cursor: pointer;
    font-size: 0.875rem;
}

.remove-btn:hover {
    opacity: 0.7;
}

/* Signal Feed (Terminal) */
.signal-feed {
    background-color: var(--bg-tertiary);
    border-radius: 8px;
    padding: 1rem;
    display: flex;
    flex-direction: column;
}

.signal-feed h2 {
    font-size: 1.25rem;
    margin-bottom: 1rem;
    text-align: center;
}

.terminal {
    flex: 1;
    background-color: var(--bg-primary);
    border-radius: 6px;
    padding: 1rem;
    overflow-y: auto;
    font-family: 'Consolas', monospace;
    font-size: 0.875rem;
    line-height: 1.6;
}

/* Signal Entry */
.signal-entry {
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border);
}

.signal-entry:last-child {
    border-bottom: none;
}

.signal-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}

.signal-timestamp {
    color: var(--text-secondary);
    font-size: 0.75rem;
}

.signal-title {
    font-weight: 600;
    font-size: 1rem;
}

.signal-title.wind-catcher {
    color: var(--accent-wind);
}

.signal-title.river-turn {
    color: var(--accent-river);
}

.signal-body {
    padding-left: 5rem;  /* Indent under timestamp */
    color: var(--text-primary);
}

.signal-detail {
    margin-bottom: 0.25rem;
}

.signal-price {
    font-weight: 600;
    color: var(--accent-success);
}

/* Terminal Input Line (aesthetic only) */
.terminal-input {
    margin-top: 1rem;
    padding: 0.5rem 1rem;
    background-color: var(--bg-primary);
    border-radius: 6px;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.prompt {
    color: var(--accent-success);
    font-weight: 600;
}

.cursor {
    animation: blink 1s infinite;
}

@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}

/* Scrollbar Styling */
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--text-secondary);
}
```

**Acceptance Criteria**:
- [ ] Visually calming color scheme
- [ ] Clear separation between sections
- [ ] Readable typography
- [ ] Smooth transitions/animations
- [ ] Professional appearance

---

#### Task 1.5.3: Watchlist Management JavaScript
**File**: `trading_system/web/static/js/watchlist.js`

**Features**:
- Load watchlists from API
- Add symbols to watchlists
- Remove symbols from watchlists
- Drag-and-drop to move between watchlists

**Key Functions**:
```javascript
// Load and render watchlists
async function loadWatchlists() {
    const response = await fetch('/api/watchlists');
    const data = await response.json();

    // Render each watchlist
    renderWatchlist('wind-catcher', '8h', data.wind_catcher['8h']);
    renderWatchlist('wind-catcher', '1h', data.wind_catcher['1h']);
    // ... etc
}

// Render single watchlist
function renderWatchlist(direction, timeframe, symbols) {
    const listId = direction === 'wind_catcher' ? 'wind' : 'river';
    const container = document.getElementById(`${listId}-${timeframe}`);

    container.innerHTML = '';

    symbols.forEach(symbol => {
        const item = createPairItem(symbol, timeframe, direction);
        container.appendChild(item);
    });
}

// Create draggable pair item
function createPairItem(symbol, timeframe, direction) {
    const li = document.createElement('li');
    li.className = 'pair-item';
    li.draggable = true;
    li.dataset.symbol = symbol;
    li.dataset.timeframe = timeframe;
    li.dataset.direction = direction;

    li.innerHTML = `
        <span class="pair-name">${symbol}</span>
        <span class="remove-btn" onclick="removePair('${symbol}', '${timeframe}', '${direction}')">×</span>
    `;

    // Drag and drop handlers
    li.addEventListener('dragstart', handleDragStart);
    li.addEventListener('dragend', handleDragEnd);

    return li;
}

// Add symbol to watchlist
async function addToWatchlist(symbol, timeframe, direction) {
    const response = await fetch('/api/watchlist/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({symbol, timeframe, direction})
    });

    if (response.ok) {
        loadWatchlists();  // Reload to show new item
    }
}

// Remove symbol from watchlist
async function removePair(symbol, timeframe, direction) {
    const response = await fetch('/api/watchlist/remove', {
        method: 'DELETE',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({symbol, timeframe, direction})
    });

    if (response.ok) {
        loadWatchlists();
    }
}

// Drag and drop handlers
let draggedItem = null;

function handleDragStart(e) {
    draggedItem = {
        symbol: e.target.dataset.symbol,
        timeframe: e.target.dataset.timeframe,
        direction: e.target.dataset.direction
    };
    e.target.style.opacity = '0.5';
}

function handleDragEnd(e) {
    e.target.style.opacity = '1';
}

// Setup drop zones
document.querySelectorAll('.pair-list').forEach(list => {
    list.addEventListener('dragover', e => {
        e.preventDefault();
        list.style.backgroundColor = 'rgba(66, 153, 225, 0.1)';
    });

    list.addEventListener('dragleave', e => {
        list.style.backgroundColor = '';
    });

    list.addEventListener('drop', async (e) => {
        e.preventDefault();
        list.style.backgroundColor = '';

        const toTimeframe = list.id.split('-')[1];
        const toDirection = list.parentElement.classList.contains('wind-catcher')
            ? 'wind_catcher'
            : 'river_turn';

        // API call to move
        await fetch('/api/watchlist/move', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                symbol: draggedItem.symbol,
                from: {
                    timeframe: draggedItem.timeframe,
                    direction: draggedItem.direction
                },
                to: {
                    timeframe: toTimeframe,
                    direction: toDirection
                }
            })
        });

        loadWatchlists();
    });
});

// Initialize
loadWatchlists();
setInterval(loadWatchlists, 60000);  // Reload every 60 seconds
```

**Acceptance Criteria**:
- [ ] Loads watchlists from API
- [ ] Displays symbols in correct lists
- [ ] Add button opens symbol picker
- [ ] Remove button works
- [ ] Drag-and-drop moves symbols between lists
- [ ] Updates reflected in database

---

#### Task 1.5.4: Signal Feed JavaScript
**File**: `trading_system/web/static/js/signals.js`

**Features**:
- Poll for new signals every 60 seconds
- Display signals in terminal format
- Auto-scroll to latest
- Format signals nicely

**Key Functions**:
```javascript
let latestTimestamp = 0;

// Poll for new signals
async function loadSignals() {
    const response = await fetch(`/api/signals/recent?since=${latestTimestamp}&limit=50`);
    const data = await response.json();

    if (data.signals.length > 0) {
        data.signals.forEach(signal => {
            appendSignal(signal);
        });

        latestTimestamp = data.latest_timestamp;

        // Auto-scroll to bottom
        const terminal = document.getElementById('signal-terminal');
        terminal.scrollTop = terminal.scrollHeight;
    }
}

// Append signal to terminal
function appendSignal(signal) {
    const terminal = document.getElementById('signal-terminal');

    const entry = document.createElement('div');
    entry.className = 'signal-entry';

    const directionClass = signal.direction === 'wind_catcher' ? 'wind-catcher' : 'river-turn';
    const emoji = signal.system_emoji;
    const confluenceEmoji = signal.emoji;

    entry.innerHTML = `
        <div class="signal-header">
            <span class="signal-timestamp">[${signal.datetime}]</span>
            <span class="signal-title ${directionClass}">
                ${confluenceEmoji} ${emoji} ${signal.confluence_class} Signal
            </span>
        </div>
        <div class="signal-body">
            <div class="signal-detail">
                <strong>${signal.symbol}</strong> @
                <span class="signal-price">$${signal.price.toFixed(2)}</span> |
                Score: ${signal.confluence_score.toFixed(1)} |
                ${signal.timeframe}
            </div>
            <div class="signal-detail">
                Indicators: ${signal.indicators_summary}
            </div>
            <div class="signal-detail">
                Volume: ${signal.volume_level}
            </div>
        </div>
    `;

    terminal.appendChild(entry);
}

// Initialize
loadSignals();
setInterval(loadSignals, 60000);  // Poll every 60 seconds
```

**Acceptance Criteria**:
- [ ] Loads initial signals on page load
- [ ] Polls for new signals every 60 seconds
- [ ] Displays signals in terminal format
- [ ] Auto-scrolls to show latest
- [ ] Handles empty state gracefully

---

#### Task 1.5.5: Modal for Adding Symbols
**Feature**: When user clicks [+] button, show modal to add symbol

**Implementation**:
```javascript
// Add to watchlist.js

function showAddSymbolModal(timeframe, direction) {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>Add Symbol to Watchlist</h3>
            <input
                type="text"
                id="symbol-input"
                placeholder="Enter symbol (e.g., BTC/USDT)"
                list="symbol-suggestions"
            />
            <datalist id="symbol-suggestions">
                <!-- Populated from API -->
            </datalist>
            <div class="modal-actions">
                <button onclick="closeModal()">Cancel</button>
                <button onclick="confirmAddSymbol('${timeframe}', '${direction}')">Add</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Load available symbols for autocomplete
    loadAvailableSymbols();

    // Focus input
    document.getElementById('symbol-input').focus();
}

async function loadAvailableSymbols() {
    const response = await fetch('/api/system/pairs');
    const data = await response.json();

    const datalist = document.getElementById('symbol-suggestions');
    data.pairs.forEach(pair => {
        const option = document.createElement('option');
        option.value = pair;
        datalist.appendChild(option);
    });
}

async function confirmAddSymbol(timeframe, direction) {
    const symbol = document.getElementById('symbol-input').value.trim();

    if (symbol) {
        await addToWatchlist(symbol, timeframe, direction);
        closeModal();
    }
}

function closeModal() {
    document.querySelector('.modal-overlay').remove();
}
```

**CSS for Modal**:
```css
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.7);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.modal-content {
    background-color: var(--bg-secondary);
    padding: 2rem;
    border-radius: 8px;
    width: 400px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

.modal-content h3 {
    margin-bottom: 1rem;
}

.modal-content input {
    width: 100%;
    padding: 0.75rem;
    background-color: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text-primary);
    font-family: inherit;
    margin-bottom: 1rem;
}

.modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
}

.modal-actions button {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-family: inherit;
}

.modal-actions button:first-child {
    background-color: var(--bg-tertiary);
    color: var(--text-primary);
}

.modal-actions button:last-child {
    background-color: var(--accent-success);
    color: white;
}
```

**Acceptance Criteria**:
- [ ] Modal opens when [+] clicked
- [ ] Shows input with autocomplete
- [ ] Adds symbol to correct watchlist
- [ ] Closes on cancel or after adding
- [ ] Validates symbol exists

---

## **PHASE 1C: TELEGRAM ALERTS**
### Duration: 3-4 days
### Priority: MEDIUM (Nice to have, not blocking)

---

### **GROUP 1.6: Telegram Bot Integration**

**Objective**: Send alerts for EXCELLENT+ signals

---

#### Task 1.6.1: Create Telegram Bot
**Manual Steps** (not code):

1. Open Telegram, message @BotFather
2. Send `/newbot`
3. Follow prompts to create bot
4. Save bot token (e.g., `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
5. Start chat with your new bot
6. Get your chat ID:
   - Message @userinfobot
   - Save your user ID (e.g., `12345678`)

**Save to Config**:
```yaml
# config/config.yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN_HERE"
  chat_id: "YOUR_CHAT_ID_HERE"
  enabled: true
  min_score: 2.5  # Only alert EXCELLENT+ (2.5+)
```

**Acceptance Criteria**:
- [ ] Bot created
- [ ] Token saved to config
- [ ] Chat ID obtained
- [ ] Can send test message manually

---

#### Task 1.6.2: Telegram Alert Service
**File**: `trading_system/telegram_bot.py` (NEW)

**Purpose**: Send formatted alerts to Telegram

**Functions**:
```python
import requests
import yaml
from datetime import datetime

def load_telegram_config():
    """Load Telegram settings from config"""
    with open('config/config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    return config.get('telegram', {})

def send_telegram_message(bot_token, chat_id, message, parse_mode='HTML'):
    """Send message via Telegram Bot API"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': parse_mode
    }

    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False

def format_signal_alert(signal):
    """Format signal as Telegram message"""
    emoji = signal['emoji']
    system_emoji = signal['system_emoji']
    direction = "BULLISH" if signal['direction'] == 'wind_catcher' else "BEARISH"

    message = f"""
🚨 <b>{emoji} {signal['confluence_class']} Signal</b>

{system_emoji} <b>{direction}</b> - {signal['symbol']}
💰 Price: ${signal['price']:.2f}
📊 Score: {signal['confluence_score']:.1f}
⏰ Time: {signal['datetime']}
🕐 Timeframe: {signal['timeframe']}

<b>Indicators:</b>
{signal['indicators_summary']}

<b>Volume:</b> {signal['volume_level']} ({signal['volume_ratio']:.1f}x)

✅ Open TradingView and verify setup!
    """.strip()

    return message

def send_signal_alert(signal):
    """Send signal alert to Telegram"""
    config = load_telegram_config()

    if not config.get('enabled', False):
        return False

    # Check if signal meets minimum score
    min_score = config.get('min_score', 2.5)
    if signal['confluence_score'] < min_score:
        return False

    bot_token = config['bot_token']
    chat_id = config['chat_id']

    message = format_signal_alert(signal)
    success = send_telegram_message(bot_token, chat_id, message)

    return success
```

**Acceptance Criteria**:
- [ ] Can send messages to Telegram
- [ ] Formats signals nicely
- [ ] Only sends if score ≥ min_score
- [ ] Handles errors gracefully

---

#### Task 1.6.3: Integrate with Signal Detector
**File**: `trading_system/signal_detector_service.py` (MODIFY)

**Add Telegram notifications**:
```python
# In run_signal_detection_loop(), after saving new signals:

from telegram_bot import send_signal_alert

# After: signal_id = save_signal(conn, result)
if signal_id:
    # Load full signal for notification
    signal = get_signal_by_id(conn, signal_id)

    # Send to Telegram
    if send_signal_alert(signal):
        mark_signal_notified(conn, signal_id)
        print(f"  📱 Telegram alert sent for {signal['symbol']}")
```

**Acceptance Criteria**:
- [ ] Sends Telegram alert when new EXCELLENT+ signal detected
- [ ] Marks signal as notified in database
- [ ] Doesn't block main detection loop if Telegram fails

---

#### Task 1.6.4: Test Telegram Alerts
**File**: `trading_system/test_telegram.py` (NEW)

**Purpose**: Test Telegram integration

```python
"""Test Telegram Bot"""

from telegram_bot import send_telegram_message, send_signal_alert, load_telegram_config

def test_basic_message():
    """Test sending a basic message"""
    config = load_telegram_config()

    message = "🚀 Test message from Wind Catcher & River Turn system!"

    success = send_telegram_message(
        config['bot_token'],
        config['chat_id'],
        message
    )

    if success:
        print("✅ Basic message sent successfully")
    else:
        print("❌ Failed to send basic message")

def test_signal_alert():
    """Test sending a formatted signal alert"""
    # Create mock signal
    mock_signal = {
        'emoji': '⭐',
        'system_emoji': '🌪️',
        'confluence_class': 'PERFECT',
        'direction': 'wind_catcher',
        'symbol': 'BTC/USDT',
        'price': 67234.50,
        'confluence_score': 3.2,
        'datetime': '2024-11-09 14:30:00',
        'timeframe': '1h',
        'indicators_summary': 'Hull(2), AO(1), Alligator(1), Ichimoku(1), Volume(1)',
        'volume_level': 'HOT',
        'volume_ratio': 2.3
    }

    success = send_signal_alert(mock_signal)

    if success:
        print("✅ Signal alert sent successfully")
    else:
        print("❌ Failed to send signal alert")

if __name__ == "__main__":
    print("Testing Telegram Integration...")
    print("-" * 50)

    test_basic_message()
    print()
    test_signal_alert()
```

**Acceptance Criteria**:
- [ ] Test script runs successfully
- [ ] Receives test messages on Telegram
- [ ] Formatted signal looks good
- [ ] No errors

---

## **PHASE 1D: INTEGRATION & DEPLOYMENT**
### Duration: 3-4 days
### Priority: CRITICAL (Make it all work together)

---

### **GROUP 1.7: System Integration**

**Objective**: Connect all components and run as unified system

---

#### Task 1.7.1: Service Manager Script
**File**: `trading_system/run_services.py` (NEW)

**Purpose**: Start all background services

```python
"""
Service Manager for Wind Catcher & River Turn
Starts all background services in separate threads
"""

import threading
import time
from multi_timeframe_collector import collect_all_watchlist_data
from signal_detector_service import run_signal_detection_loop
from web.app import create_app

def data_collection_service():
    """Background thread: Collect data every 5 minutes"""
    print("🔄 Data Collection Service started")

    while True:
        try:
            print(f"\n[{datetime.now()}] Collecting price data...")
            collect_all_watchlist_data(conn, config)
            print("✅ Data collection complete")
        except Exception as e:
            print(f"❌ Data collection error: {e}")

        time.sleep(300)  # 5 minutes

def signal_detection_service():
    """Background thread: Detect signals every 5 minutes"""
    print("🎯 Signal Detection Service started")
    run_signal_detection_loop()

def web_server_service():
    """Foreground: Run Flask web server"""
    print("🌐 Web Server starting...")
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)

def main():
    """Start all services"""
    print("=" * 60)
    print("🚀 Wind Catcher & River Turn Trading System")
    print("=" * 60)
    print("\nStarting services...\n")

    # Start background services in threads
    data_thread = threading.Thread(target=data_collection_service, daemon=True)
    signal_thread = threading.Thread(target=signal_detection_service, daemon=True)

    data_thread.start()
    signal_thread.start()

    # Give background services time to start
    time.sleep(2)

    # Start web server (foreground)
    web_server_service()

if __name__ == "__main__":
    main()
```

**Acceptance Criteria**:
- [ ] Starts all services successfully
- [ ] Services run concurrently
- [ ] Logs activity from all services
- [ ] Handles Ctrl+C gracefully

---

#### Task 1.7.2: Configuration Management
**File**: `trading_system/config/config.yaml` (UPDATE)

**Add all new settings**:
```yaml
# Exchange Settings
exchange:
  name: "gateio"
  api_key: "YOUR_API_KEY_HERE"
  api_secret: "YOUR_API_SECRET_HERE"

# System Settings
system:
  test_mode: false
  data_collection_interval: 300  # 5 minutes
  signal_scan_interval: 300      # 5 minutes

# Timeframes
timeframes:
  enabled: ['8h', '1h', '15m']
  default: '1h'

# Confluence Scoring
confluence:
  min_score_alert: 2.5       # EXCELLENT+ for Telegram
  min_score_display: 1.2     # GOOD+ for web feed

# Telegram Alerts
telegram:
  enabled: true
  bot_token: "YOUR_BOT_TOKEN_HERE"
  chat_id: "YOUR_CHAT_ID_HERE"
  min_score: 2.5

# Web Interface
web:
  host: "0.0.0.0"
  port: 5000
  update_interval: 60  # seconds

# Initial Watchlist (optional - can be empty)
initial_watchlist:
  wind_catcher:
    8h: ["BTC/USDT", "SOL/USDT"]
    1h: ["BTC/USDT"]
    15m: []
  river_turn:
    8h: []
    1h: ["TAO/USDT"]
    15m: []
```

**Acceptance Criteria**:
- [ ] All settings documented
- [ ] Sensible defaults
- [ ] Config loaded by all services
- [ ] Easy to modify

---

#### Task 1.7.3: Installation & Setup Documentation
**File**: `docs/INSTALLATION.md` (NEW)

**Content**:
```markdown
# Installation & Setup Guide

## Prerequisites
- Python 3.8+
- pip
- SQLite (included with Python)
- Gate.io account with API keys
- Telegram account (for alerts)

## Step 1: Install Dependencies

```bash
cd trading_system
pip install -r requirements.txt
```

## Step 2: Configure API Keys

1. Copy example config:
```bash
cp config/config.yaml.example config/config.yaml
```

2. Edit `config/config.yaml`:
```yaml
exchange:
  api_key: "YOUR_GATEIO_API_KEY"
  api_secret: "YOUR_GATEIO_API_SECRET"
```

## Step 3: Set Up Telegram (Optional)

1. Create bot via @BotFather
2. Get bot token
3. Get your chat ID from @userinfobot
4. Update config:
```yaml
telegram:
  enabled: true
  bot_token: "YOUR_BOT_TOKEN"
  chat_id: "YOUR_CHAT_ID"
```

## Step 4: Initialize Database

```bash
python database_setup.py
```

## Step 5: Initial Data Collection

```bash
python multi_timeframe_collector.py
```

## Step 6: Start System

```bash
python run_services.py
```

## Step 7: Open Web Interface

Open browser to: http://localhost:5000

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### "Database not found"
```bash
python database_setup.py
```

### Telegram not working
Test with: `python test_telegram.py`

### Web interface not loading
Check if port 5000 is available: `netstat -an | grep 5000`
```

**Acceptance Criteria**:
- [ ] Clear step-by-step instructions
- [ ] Covers all setup steps
- [ ] Includes troubleshooting
- [ ] Easy for user to follow

---

#### Task 1.7.4: Testing & Quality Assurance

**Test Checklist**:

**Database Tests**:
- [ ] Database creates successfully
- [ ] All tables exist with correct schema
- [ ] Can insert/query data
- [ ] Indexes work

**Data Collection Tests**:
- [ ] Connects to Gate.io successfully
- [ ] Fetches 8h, 1h, 15m data
- [ ] Stores in database correctly
- [ ] Handles API errors gracefully

**Signal Detection Tests**:
- [ ] Calculates indicators correctly
- [ ] Detects signals
- [ ] Saves to signals table
- [ ] Respects confluence threshold

**Web Interface Tests**:
- [ ] Server starts successfully
- [ ] Page loads correctly
- [ ] Watchlists display
- [ ] Can add/remove symbols
- [ ] Drag-and-drop works
- [ ] Signal feed updates
- [ ] Polling works (60s updates)

**Telegram Tests**:
- [ ] Sends test message
- [ ] Sends signal alerts
- [ ] Only sends EXCELLENT+
- [ ] Formatting looks good

**Integration Tests**:
- [ ] All services start together
- [ ] Data flows correctly: Collection → Analysis → Signals → Web/Telegram
- [ ] System runs for 1+ hour without crashes
- [ ] Performance acceptable (CPU/memory)

**Acceptance Criteria**:
- [ ] All tests pass
- [ ] No critical bugs
- [ ] System stable for extended run

---

## **PHASE 1E: DOCUMENTATION & HANDOFF**
### Duration: 2 days
### Priority: MEDIUM

---

### **GROUP 1.8: User Documentation**

---

#### Task 1.8.1: User Manual
**File**: `docs/USER_MANUAL.md` (NEW)

**Content**:
- How to add symbols to watchlists
- How to move symbols between watchlists
- How to interpret signals in feed
- Signal confluence levels explained
- Recommended workflow
- Best practices

---

#### Task 1.8.2: Development Log
**File**: `docs/DEVELOPMENT_LOG_PHASE1.md` (NEW)

**Content**:
- What was built in Phase 1
- Decisions made and why
- Known limitations
- Future improvements needed
- Lessons learned

---

## 📊 **PHASE 1 SUMMARY**

### **Deliverables**:
1. ✅ Multi-timeframe data collection (8h, 1h, 15m)
2. ✅ Backtesting system with Oct 3 - Nov 3 report
3. ✅ Web interface with:
   - User-controlled watchlists
   - Drag-and-drop symbol management
   - Terminal-style signal feed
   - 60-second auto-updates
4. ✅ Telegram alert system
5. ✅ Signal detection service
6. ✅ Complete documentation

### **Timeline**: 3-4 weeks total

### **Milestones**:
- **Week 1**: Foundation (multi-timeframe, backtesting)
- **Week 2**: Backend API + Database
- **Week 3**: Frontend UI + Integration
- **Week 4**: Telegram + Testing + Documentation

### **Success Criteria**:
- [ ] System runs 24/7 without crashes
- [ ] Detects signals across all timeframes
- [ ] Web interface is functional and pleasant to use
- [ ] Telegram alerts work reliably
- [ ] Backtest report shows sensible signals
- [ ] User can manage watchlists easily

---

## 🚀 **NEXT PHASES (PREVIEW)**

**Phase 2**: Performance & Optimization
- Backtesting engine with P&L simulation
- Signal performance tracking
- Win rate analysis per confluence level
- Indicator effectiveness analysis

**Phase 3**: Advanced Features
- Multi-timeframe alignment scoring
- Advanced chart patterns
- Support/resistance level detection
- Automated trade execution (optional)

**Phase 4**: Production Hardening
- Logging & monitoring
- Error alerting
- Database backups
- Deployment automation

---

## 📝 **NOTES & CONSIDERATIONS**

### **API Costs**:
- Gate.io: Free for public data, rate limited (2 calls/sec)
- With 15 pairs × 3 timeframes = 45 API calls per cycle
- At 2 calls/sec = ~23 seconds per cycle
- Every 5 minutes = acceptable

### **Database Growth**:
- 15 pairs × 3 timeframes × 200 candles = 9,000 candles stored
- Each candle ~100 bytes = 0.9 MB
- Signals: ~50/day × 365 days = ~18,000 signals/year × 500 bytes = 9 MB/year
- **Conclusion**: SQLite is fine, no scaling concerns

### **Performance**:
- Indicator calculations: Fast (pandas vectorized)
- Web server: Flask handles this easily
- Expected load: Single user, minimal traffic
- **Conclusion**: No performance optimization needed initially

### **Maintenance**:
- Keep API keys secure
- Regular backups of database
- Monitor Telegram bot for rate limits
- Update dependencies periodically

---

## ✅ **READY TO BUILD**

This plan is comprehensive, detailed, and actionable. Each task has:
- Clear objective
- Specific files to create/modify
- Acceptance criteria
- Estimated effort

**Next Steps**:
1. Review this plan
2. Clarify any questions
3. Prioritize any changes
4. Start with Phase 1A, Group 1.1, Task 1.1.1

Let's build this! 🚀
