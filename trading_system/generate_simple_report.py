"""
Simplified report generator - analyzes only the latest signal for each coin/timeframe
"""

import sys
import io

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

import pandas as pd
from datetime import datetime
from pathlib import Path

# Just run the master confluence analyzer which already has signals
print("Running master confluence analyzer on current data...")
print("="*80)

import subprocess
result = subprocess.run(
    ['./venv/Scripts/python.exe', 'master_confluence.py'],
    capture_output=True,
    text=True
)

print(result.stdout)
if result.stderr:
    print(result.stderr)

print("\nNow check the signals table in the database for generated signals.")
print("Run: ./venv/Scripts/python.exe view_data.py")
