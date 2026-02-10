import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def validate():
    # check a few key tickers
    tickers = ["NVDA", "XOM", "CAT", "UBER", "SPY"]
    print(f"Validating data for: {tickers}")
    
    # Fetch 15m data (what we used)
    print("Fetching 1mo 15m data...")
    df_15m = yf.download(tickers, period="1mo", interval="15m", group_by='ticker', auto_adjust=True, threads=True)
    
    # Fetch 1d data (ground truth for Close)
    print("Fetching 1mo 1d data...")
    df_1d = yf.download(tickers, period="1mo", interval="1d", group_by='ticker', auto_adjust=True, threads=True)
    
    for t in tickers:
        print(f"\n--- {t} ---")
        
        # Check last available day in 1d
        if t not in df_1d.columns.levels[0]:
            print(f"Missing 1d data for {t}")
            continue
            
        d1 = df_1d[t].dropna()
        last_day = d1.index[-1]
        last_close_1d = d1.iloc[-1]['Close']
        print(f"Daily Last Date: {last_day}")
        print(f"Daily Last Close: {last_close_1d:.2f}")
        
        # Check last available data in 15m
        if t not in df_15m.columns.levels[0]:
            print(f"Missing 15m data for {t}")
            continue
            
        d15 = df_15m[t].dropna()
        last_timestamp = d15.index[-1]
        last_close_15m = d15.iloc[-1]['Close']
        
        print(f"Intraday Last Timestamp: {last_timestamp}")
        print(f"Intraday Last Close: {last_close_15m:.2f}")
        
        diff = abs(last_close_15m - last_close_1d)
        print(f"Difference: {diff:.4f}")
        
        if diff > last_close_1d * 0.01: # >1% difference
            print("WARNING: Significant discrepancy between 1d and 15m close!")
        else:
            print("OK: Data matches.")

if __name__ == "__main__":
    validate()
