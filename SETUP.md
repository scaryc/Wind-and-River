# Setup Instructions - Wind and River Trading System

## Quick Start

### 1. Install Dependencies

```bash
pip3 install numpy pandas pyyaml ccxt
```

### 2. Configure API Keys

**IMPORTANT: Never commit your API keys to git!**

1. Copy the example config:
   ```bash
   cd trading_system/config
   cp config.yaml.example config.yaml
   ```

2. Edit `config.yaml` with your real API keys:
   ```yaml
   exchange:
     name: "gateio"
     api_key: "YOUR_ACTUAL_API_KEY_HERE"
     api_secret: "YOUR_ACTUAL_API_SECRET_HERE"
   ```

3. The `.gitignore` file ensures `config.yaml` won't be committed

### 3. Set Up Database

```bash
cd trading_system
python3 database_setup.py
```

### 4. Collect Data

```bash
python3 data_collector.py
```

### 5. Verify Indicators

Test that Hull MA calculations match TradingView:

```bash
python3 verify_hma_tradingview.py
```

Compare the output with TradingView charts (1h timeframe).

## Security Best Practices

### ✅ DO:
- Keep `config.yaml` private
- Use the example file as a template
- Add API keys only in `config.yaml`
- Check `.gitignore` includes `config.yaml`

### ❌ DON'T:
- Commit `config.yaml` to git
- Share your API keys
- Post screenshots with API keys visible
- Store keys in code files

## File Structure

```
Wind-and-River/
├── .gitignore                    # Protects sensitive files
├── SETUP.md                      # This file
├── DEVELOPMENT_APPROACH.md       # Development philosophy
└── trading_system/
    ├── config/
    │   ├── config.yaml          # YOUR KEYS (not in git)
    │   └── config.yaml.example  # Template (in git)
    ├── data/
    │   └── trading_system.db    # Database (not in git)
    └── *.py                     # Python scripts
```

## Troubleshooting

### "No module named 'pandas'"
Install dependencies:
```bash
pip3 install numpy pandas pyyaml ccxt
```

### "Error loading config"
Make sure you created `config.yaml` from the example:
```bash
cd trading_system/config
cp config.yaml.example config.yaml
# Then edit config.yaml with your API keys
```

### "Failed to connect to exchange"
- Check your API keys are correct in `config.yaml`
- Verify API keys have appropriate permissions on Gate.io
- Check your internet connection

### "Not enough data"
Run the data collector first:
```bash
python3 data_collector.py
```

## Current Development Status

We are currently in **single timeframe mode** (1h only). See `DEVELOPMENT_APPROACH.md` for details.

## Next Steps

1. Verify your setup works
2. Run data collection
3. Test HMA calculations against TradingView
4. Start trading system development

For questions about the development approach, see `DEVELOPMENT_APPROACH.md`.
