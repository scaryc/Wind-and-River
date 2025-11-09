# Wind Catcher & River Turn - Quick Reference Guide

## 🚀 Quick Start

```bash
# 1. Collect latest data
python3 data_collector.py

# 2. Run master analysis
python3 master_confluence.py

# 3. View individual indicators (optional)
python3 enhanced_hull_analyzer.py
python3 enhanced_indicators.py
python3 alligator_analyzer.py
python3 ichimoku_analyzer.py
python3 volume_analyzer.py
```

---

## 📊 5 Core Indicators

| Indicator | What It Does | Best Signals |
|-----------|--------------|--------------|
| **Hull MA** | Trend direction & reversals | First close above/below Hull 21 |
| **AO Divergence** | Hidden momentum shifts | Price diverges from oscillator |
| **Alligator** | Market phase & retracements | Blue line touches, Sleep→Awake |
| **Ichimoku** | Cloud support/resistance | Cloud retests, Kijun touches |
| **Volume** | Conviction confirmation | WARMING (1.5x), HOT (2x), CLIMAX (3x) |

---

## 🎯 Signal Types

### Wind Catcher 🌪️ (Bullish)
- First close **above** Hull 21
- AO **bullish** divergence (price ↓, AO ↑)
- Alligator blue line **support**
- Ichimoku Kijun **support** / Green cloud retest
- Volume **confirmation**

### River Turn 🌊 (Bearish)
- First close **below** Hull 21
- AO **bearish** divergence (price ↑, AO ↓)
- Alligator blue line **resistance**
- Ichimoku Kijun **resistance** / Red cloud retest
- Volume **confirmation**

---

## ⭐ Confluence Scoring

| Score | Class | Action | Emoji |
|-------|-------|--------|-------|
| ≥ 3.0 | PERFECT | Strong entry | ⭐ |
| 2.5-2.9 | EXCELLENT | High confidence | 🌟 |
| 1.8-2.4 | VERY GOOD | Good entry | ✨ |
| 1.2-1.7 | GOOD | Standard entry | 💫 |
| 0.8-1.1 | INTERESTING | Watch only | 💡 |
| < 0.8 | WEAK | Ignore | 🔍 |

---

## 📏 Signal Strength Values

| Signal Type | Strength | Importance |
|-------------|----------|------------|
| Hull MA break | 0.7 | Primary |
| AO divergence | 0.8 | High |
| Alligator blue touch | 0.9 | Very High |
| Ichimoku cloud retest | 0.9 | Very High |
| Ichimoku Kijun touch | 0.7 | Medium |
| Volume CLIMAX | 1.0 | Maximum |
| Volume HOT | 0.8 | High |
| Volume WARMING | 0.6 | Medium |
| Volume bonus | +0.3 | Bonus |

---

## 🎬 Trading Rules

### Entry Checklist
- [ ] Confluence ≥ GOOD (1.2+)
- [ ] Minimum 2 indicator types
- [ ] Volume ≥ WARMING (1.5x)
- [ ] Direction matches bias
- [ ] Clear stop loss level

### Position Sizing
- **PERFECT/EXCELLENT**: 1.5-2x standard size
- **VERY GOOD/GOOD**: 1x standard size
- **INTERESTING**: Watch only, no entry

### Stop Loss Guidelines
- **Wind Catcher**: Below swing low or Hull 34
- **River Turn**: Above swing high or Hull 34
- **Alligator**: Beyond blue line (Jaw)
- **Ichimoku**: Beyond cloud boundary

### Profit Targets
- **Conservative**: 1.5R (1.5x risk)
- **Standard**: 2R (2x risk)
- **Aggressive**: 3R (PERFECT only)

---

## 🔍 Indicator Settings

### Hull MA
- Fast: 21 periods
- Slow: 34 periods
- Formula: WMA(2×WMA(n/2) - WMA(n), √n)

### Awesome Oscillator
- Fast: 5-period SMA
- Slow: 34-period SMA
- Median price: (H+L)/2

### Modified Alligator (10x multiplier)
- Jaw (Blue): 130 SMA
- Teeth (Green): 80 SMA
- Lips (Red): 50 SMA
- Sleep threshold: 0.15% spread

### Ichimoku Cloud
- Tenkan-sen: 20
- Kijun-sen: 60
- Senkou B: 120
- Displacement: 30

### Volume
- Baseline: 120-hour (5-day) average
- Monitor: Last 3 candles
- Levels: 1.5x, 2x, 3x average

---

## 📁 File Structure

```
Wind-and-River/
├── .gitignore                          # Protects API keys
├── SETUP.md                            # Installation guide
├── DEVELOPMENT_APPROACH.md             # Dev philosophy
├── SYSTEM_DESCRIPTION.md               # This complete guide
├── QUICK_REFERENCE.md                  # Quick lookup
└── trading_system/
    ├── config/
    │   ├── config.yaml.example         # Template (safe)
    │   └── config.yaml                 # YOUR KEYS (not in git)
    ├── data/
    │   └── trading_system.db           # Price database
    ├── database_setup.py               # Setup database
    ├── data_collector.py               # Fetch data
    ├── indicators.py                   # Hull MA
    ├── enhanced_indicators.py          # AO divergence
    ├── alligator_analyzer.py           # Alligator
    ├── ichimoku_analyzer.py            # Ichimoku
    ├── volume_analyzer.py              # Volume
    ├── master_confluence.py            # Complete system
    └── verify_hma_tradingview.py       # Verification
```

---

## 🔧 Common Commands

### Database
```bash
python3 database_setup.py          # Initialize database
```

### Data Collection
```bash
python3 data_collector.py          # Manual collection
python3 auto_updater.py            # Auto-update
```

### Analysis
```bash
python3 master_confluence.py       # Full analysis (use this!)
python3 confluence_signals.py      # Hull + Volume only
python3 enhanced_confluence.py     # Multi-indicator
```

### Individual Indicators
```bash
python3 indicators.py              # Hull MA only
python3 enhanced_indicators.py     # AO divergences
python3 alligator_analyzer.py      # Alligator patterns
python3 ichimoku_analyzer.py       # Ichimoku signals
python3 volume_analyzer.py         # Volume climax
```

### Verification
```bash
python3 verify_hma_tradingview.py  # Compare with TradingView
python3 test_connection.py         # Test Gate.io connection
```

### Watchlist Management
```bash
python3 update_watchlist.py        # Add/remove pairs
```

---

## 💡 Reading Signal Output

### Example Output
```
⭐ 🌪️ BTC/USDT $67,500 - PERFECT (Score: 3.2) at 14:00
  5 indicators firing
  Breakdown: Hull(2), AO(1), Alligator(1), Ichimoku(1)
```

**Decoding**:
- ⭐ = PERFECT confluence
- 🌪️ = Wind Catcher (bullish)
- Score: 3.2 = Very strong
- 5 indicators = Multiple confirmations
- Hull(2) = 2 Hull signals active

### Volume Indicators
- 📊 NORMAL = < 1.5x average
- 📈 WARMING = 1.5x - 2x average
- 🌡️ HOT = 2x - 3x average
- 🔥 CLIMAX = ≥ 3x average

---

## ⚡ Pro Tips

1. **Wait for confluence** - Never trade single indicators
2. **Volume validates** - Best signals have elevated volume
3. **Higher score = higher probability** - Focus on 2.5+
4. **2+ indicator types minimum** - Diversify confirmations
5. **Verify regularly** - Run verification scripts weekly
6. **Single timeframe now** - 1h only until mastered
7. **Track performance** - Note which setups work best

---

## 🚨 Warning Signs (Don't Trade)

❌ Score < 1.2 (below GOOD)
❌ Only 1 indicator firing
❌ Volume is NORMAL (no confirmation)
❌ Conflicting signals (some bullish, some bearish)
❌ Insufficient data (< 150 candles)
❌ During major news events
❌ Low liquidity pairs

---

## 📞 Troubleshooting

### "No data"
```bash
python3 data_collector.py  # Collect data first
```

### "Module not found"
```bash
pip3 install numpy pandas pyyaml ccxt
```

### "API key error"
Check `config/config.yaml` has valid keys

### "Values don't match TradingView"
```bash
python3 verify_hma_tradingview.py  # Debug calculations
```

---

## 🎯 Daily Checklist

Morning Routine:
1. [ ] Run `data_collector.py` - Get fresh data
2. [ ] Run `master_confluence.py` - Analyze all pairs
3. [ ] Review PERFECT/EXCELLENT signals
4. [ ] Check volume confirmation
5. [ ] Verify on TradingView charts
6. [ ] Set alerts for developing setups

Before Each Trade:
1. [ ] Confluence ≥ GOOD?
2. [ ] 2+ indicator types?
3. [ ] Volume elevated?
4. [ ] Direction clear?
5. [ ] Stop loss defined?
6. [ ] Risk acceptable?

---

## 🔗 Quick Links

- **Setup**: See SETUP.md
- **Full Description**: See SYSTEM_DESCRIPTION.md
- **Development**: See DEVELOPMENT_APPROACH.md
- **Issues**: GitHub Issues

---

**Current Version**: 1.0 (Single Timeframe Mode)
**Timeframe**: 1h only
**Exchange**: Gate.io
**Last Updated**: 2025-11-09
