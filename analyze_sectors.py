import yfinance as yf
import pandas as pd
from tabulate import tabulate
import time
from datetime import datetime, timedelta
import argparse
import sys

# Define Sectors and Top 5 Constituents
SECTORS = {
    "XLK": ["NVDA", "AAPL", "MSFT", "AVGO", "MU"],
    "XLV": ["LLY", "JNJ", "ABBV", "UNH", "MRK"],
    "XLF": ["BRK-B", "JPM", "V", "MA", "BAC"],
    "XLY": ["AMZN", "TSLA", "HD", "MCD", "TJX"],
    "XLP": ["WMT", "COST", "PG", "KO", "PM"],
    "XLC": ["META", "GOOGL", "GOOG", "NFLX", "DIS"],
    "XLE": ["XOM", "CVX", "COP", "WMB", "EOG"],
    "XLI": ["GE", "CAT", "RTX", "BA", "UBER"],
    "XLB": ["LIN", "NEM", "FCX", "SHW", "CRH"],
    "XLU": ["NEE", "CEG", "SO", "DUK", "AEP"],
    "XLRE": ["WELL", "PLD", "EQIX", "AMT", "SPG"]
}

def fetch_data():
    all_tickers = []
    for sector, stocks in SECTORS.items():
        all_tickers.append(sector)
        all_tickers.extend(stocks)
    
    all_tickers = list(set(all_tickers))
    print(f"Fetching data for {len(all_tickers)} tickers (1mo history, 15m interval)...")
    
    # Fetch 1mo to ensure we have 2 weeks of 15m data
    try:
        data = yf.download(all_tickers, period="1mo", interval="15m", group_by='ticker', auto_adjust=True, threads=True)
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def filter_data_by_date(df, start_date=None, end_date=None):
    if df is None or df.empty:
        return df
    
    # Ensure index is timezone aware (Yahoo usually returns EST/EDT)
    # We will assume user input is in the same timezone or purely naive matching string
    
    filtered = df.copy()
    
    if start_date:
        filtered = filtered[filtered.index >= start_date]
    if end_date:
        filtered = filtered[filtered.index <= end_date]
        
    return filtered

def analyze_sector(sector_ticker, holdings, data, start_arg=None, end_arg=None):
    # Check data existence

    if sector_ticker not in data.columns.levels[0]:
        return None

    sector_raw = data[sector_ticker].dropna()
    sector_df = filter_data_by_date(sector_raw, start_arg, end_arg)
    
    if sector_df.empty:
        return None

    # Calculate metrics
    s_start_price = sector_df.iloc[0]['Open']
    s_end_price = sector_df.iloc[-1]['Close']
    s_high_price = sector_df['High'].max()
    s_return = (s_end_price - s_start_price) / s_start_price * 100
    
    print(f"\n{sector_ticker} Analysis Window: {sector_df.index[0]} to {sector_df.index[-1]}")
    
    stats = []
    for stock in holdings:
        if stock not in data.columns.levels[0]:
            continue
            
        stock_raw = data[stock].dropna()
        stock_df = filter_data_by_date(stock_raw, start_arg, end_arg)
        
        if stock_df.empty:
            continue
            
        st_start = stock_df.iloc[0]['Open']
        st_end = stock_df.iloc[-1]['Close']
        st_high = stock_df['High'].max()
        st_return = (st_end - st_start) / st_start * 100
        
        rel_strength = st_return - s_return
        
        role = "NEUTRAL"
        if rel_strength > 1.0: # Stricter for 2 weeks? Keeping threshold simple
            role = "ENGINE"
        elif rel_strength < -1.0:
            role = "BRAKE"
            
        stats.append({
            "Ticker": stock,
            "Role": role,
            "Start Price": st_start,
            "High Price": st_high,
            "Close Price": st_end,
            "Return(%)": st_return,
            "Rel vs Sec": rel_strength
        })

    stats_df = pd.DataFrame(stats)
    if not stats_df.empty:
        stats_df = stats_df.sort_values("Return(%)", ascending=False)
        print(f"Sector {sector_ticker}: Start={s_start_price:.2f}, End={s_end_price:.2f}, High={s_high_price:.2f}, Return={s_return:.2f}%")
        print(tabulate(stats_df, headers="keys", tablefmt="grid", floatfmt=".2f"))
        return stats_df
    return None

def main():
    parser = argparse.ArgumentParser(description='Market Analysis Engine')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD or YYYY-MM-DD HH:MM)')
    parser.add_argument('--days', type=int, default=14, help='Number of days to look back if no start date provided')
    
    args = parser.parse_args()
    
    data = fetch_data()
    if data is None or data.empty:
        print("No data.")
        return

    # Determine date range
    start_dt = None
    end_dt = None
    
    # Helper to parse simplified date strings if needed, 
    # but pandas string comparison usually works well with YYYY-MM-DD
    if args.start:
        start_dt = args.start
    if args.end:
        end_dt = args.end
        
    if not start_dt and not end_dt:
        # Default to last N days relative to the actual data received
        # Get the very last timestamp in the dataset
        last_timestamp = data.index[-1]
        start_dt = (last_timestamp - timedelta(days=args.days)).strftime("%Y-%m-%d")
        print(f"Auto-range: Last {args.days} days ({start_dt} to present)")

    all_stats = {}
    with open("analysis_output.txt", "w", encoding='utf-8') as f:
        f.write(f"MARKET ANALYSIS REPORT (Window: {start_dt} -> {end_dt if end_dt else 'Latest'})\n")
        f.write("="*60 + "\n")

        for sector, holdings in SECTORS.items():
            result = analyze_sector(sector, holdings, data, start_dt, end_dt)
            if result is not None:
                sector_metrics, stats_df = result
                f.write(sector_metrics + "\n")
                f.write(tabulate(stats_df, headers="keys", tablefmt="grid", floatfmt=".2f") + "\n\n")

def analyze_sector(sector_ticker, holdings, data, start_arg=None, end_arg=None):
    # Check data existence
    if sector_ticker not in data.columns.levels[0]:
        return None

    sector_raw = data[sector_ticker].dropna()
    sector_df = filter_data_by_date(sector_raw, start_arg, end_arg)
    
    if sector_df.empty:
        return None

    # Calculate metrics
    s_start_price = sector_df.iloc[0]['Open']
    s_end_price = sector_df.iloc[-1]['Close']
    s_high_price = sector_df['High'].max()
    s_return = (s_end_price - s_start_price) / s_start_price * 100
    
    sector_info = f"\n{sector_ticker} Analysis Window: {sector_df.index[0]} to {sector_df.index[-1]}\n"
    sector_info += f"Sector {sector_ticker}: Start={s_start_price:.2f}, End={s_end_price:.2f}, High={s_high_price:.2f}, Return={s_return:.2f}%"
    
    stats = []
    for stock in holdings:
        if stock not in data.columns.levels[0]:
            continue
            
        stock_raw = data[stock].dropna()
        stock_df = filter_data_by_date(stock_raw, start_arg, end_arg)
        
        if stock_df.empty:
            continue
            
        st_start = stock_df.iloc[0]['Open']
        st_end = stock_df.iloc[-1]['Close']
        st_high = stock_df['High'].max()
        st_return = (st_end - st_start) / st_start * 100
        
        rel_strength = st_return - s_return
        
        role = "NEUTRAL"
        if rel_strength > 1.0: 
            role = "ENGINE"
        elif rel_strength < -1.0:
            role = "BRAKE"
            
        stats.append({
            "Ticker": stock,
            "Role": role,
            "Start Price": st_start,
            "High Price": st_high,
            "Close Price": st_end,
            "Return(%)": st_return,
            "Rel vs Sec": rel_strength
        })

    stats_df = pd.DataFrame(stats)
    if not stats_df.empty:
        stats_df = stats_df.sort_values("Return(%)", ascending=False)
        return sector_info, stats_df
    return None

if __name__ == "__main__":
    main()
