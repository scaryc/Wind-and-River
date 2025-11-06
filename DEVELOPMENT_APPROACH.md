# Wind and River Trading System - Development Approach

## Single Timeframe First (Current Phase)

### Philosophy
**"Build it right on one timeframe, then expand"**

We are currently developing and testing the system using **only the 1-hour (1h) timeframe**. This approach allows us to:

1. **Verify Accuracy**: Ensure all indicators (Hull MA, Alligator, Ichimoku) match TradingView exactly
2. **Debug Easily**: Single timeframe = simpler debugging
3. **Test Thoroughly**: Validate signals and confluence logic completely
4. **Build Confidence**: Know the system works before adding complexity

### Current Timeframe
- **Primary Timeframe**: 1h (hourly)
- **All testing**: 1h data
- **All verification**: Against TradingView 1h charts

### Future: Multi-Timeframe System

Once the 1h system is proven and working correctly:

1. Add 4h timeframe for higher timeframe trend
2. Add 15m timeframe for entry timing
3. Implement multi-timeframe confluence
4. Test the complete system

### Why This Approach?

**Problem with multi-timeframe from start:**
- Hard to debug (which timeframe has the error?)
- Complex to test
- Difficult to verify against TradingView
- More variables = more bugs

**Benefits of single timeframe first:**
- Clear verification path
- Easy debugging
- Simple testing
- Fast iteration
- Confidence building

## Current Development Status

### ✅ Completed
- Database setup
- Data collection from Gate.io
- Hull MA indicator (verified against TradingView)
- Alligator indicator
- Ichimoku indicator
- Basic signal detection
- 1h timeframe implementation

### 🔄 In Progress
- HMA verification against TradingView (run `verify_hma_tradingview.py`)
- Signal confluence logic
- Testing and validation

### 📋 Next Steps
1. Verify all indicators match TradingView on 1h
2. Test signal generation thoroughly
3. Validate confluence scoring
4. Paper trade on 1h only
5. Once proven → expand to multi-timeframe

## Testing Your Indicators

### HMA Verification
Run the verification script to test Hull MA calculations:

```bash
cd trading_system
python3 verify_hma_tradingview.py
```

This will:
1. Calculate Hull MA 21 and 34 for all trading pairs
2. Show detailed breakdown of calculations
3. Provide exact values to compare with TradingView

### How to Verify on TradingView
1. Open TradingView
2. Select your trading pair (e.g., BTC/USDT)
3. Set timeframe to **1h**
4. Add indicator: "Hull Moving Average" with period 21
5. Add indicator: "Hull Moving Average" with period 34
6. Compare the rightmost (latest) values with the script output

### What to Check
- Values should match within 0.01% (accounting for data timing)
- If values don't match, we have a calculation error to fix
- All three pairs (BTC/USDT, ENA/USDT, HYPE/USDT) should match

## Directory Structure

```
trading_system/
├── config/
│   ├── config.yaml          # Your API keys (DO NOT commit!)
│   └── config.yaml.example  # Template (safe to commit)
├── data/
│   └── trading_system.db    # SQLite database
├── indicators.py            # Hull MA, Alligator, Ichimoku
├── data_collector.py        # Fetch price data
├── verify_hma_tradingview.py # Test HMA calculations
└── ...other scripts
```

## Important Notes

### API Key Security
- **NEVER** commit `config.yaml` to git
- Copy `config.yaml.example` to `config.yaml`
- Add your real API keys only to `config.yaml`
- The `.gitignore` file protects `config.yaml`

### Timeframe Consistency
- All current development uses **1h only**
- Do not mix timeframes yet
- Verify everything on 1h first
- Multi-timeframe comes later

### Data Quality
- Ensure you have at least 100 candles of 1h data
- Run `data_collector.py` regularly to update data
- Check data freshness before testing

## Questions?

If you see timeframe mismatches or errors:
1. Remember we're in "single timeframe mode"
2. Everything should be 1h
3. If you see multiple timeframes, that's the bug
4. Fix by forcing everything to use 1h

This approach ensures quality over speed. A working 1h system is better than a broken multi-timeframe system.
