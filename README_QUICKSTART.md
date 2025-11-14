# Wind Catcher & River Turn - Quick Start Guide

## 🚀 Automated Setup (Easiest!)

Double-click this file to do everything automatically:
```
setup_and_run.bat
```

This will:
1. ✅ Install all dependencies
2. ✅ Test Hyperliquid connection
3. ✅ Create database
4. ✅ Check watchlist
5. ✅ Collect initial data

---

## 📋 If Watchlist is Empty

After setup, add your coins:
```
add_coins.bat
```

Add coins like: `BTC`, `ETH`, `SOL` (without /USDT)

Then run setup again to collect data.

---

## 🎯 Daily Usage

### Option 1: Quick Dashboard
```
quick_start.bat
```
Updates data and shows dashboard

### Option 2: Continuous Monitoring
```
start_monitoring.bat
```
Runs auto-updater for 24/7 monitoring

---

## 🔧 Manual Commands

If you prefer terminal commands:

```bash
cd "c:\Users\peter\wind and river\trading_system"

# Add coins
python update_watchlist.py

# Collect data
python data_collector.py

# View dashboard
python trading_dashboard.py

# Start monitoring
python auto_updater.py
```

---

## ⚠️ Important Notes

1. **Coin Format:** Use `BTC` not `BTC/USDT`
2. **Add Coins First:** System needs at least one coin in watchlist
3. **Internet Required:** Hyperliquid needs internet connection
4. **No API Keys:** Hyperliquid doesn't require API keys for market data

---

## 📁 Batch Files Reference

| File | What It Does |
|------|--------------|
| `setup_and_run.bat` | Complete first-time setup |
| `add_coins.bat` | Add/remove coins from watchlist |
| `quick_start.bat` | Update data + show dashboard |
| `start_monitoring.bat` | 24/7 continuous monitoring |

---

## 🆘 Troubleshooting

**Error: pip not found**
- Install Python first, make sure "Add to PATH" was checked

**Empty watchlist error**
- Run `add_coins.bat` and add at least one coin

**Hyperliquid connection failed**
- Check internet connection
- Try testnet: set `use_testnet: true` in `trading_system/config/config.yaml`

---

**Start here:** Double-click `setup_and_run.bat` 🚀
