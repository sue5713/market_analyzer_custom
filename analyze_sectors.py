import yfinance as yf
import pandas as pd
from tabulate import tabulate
import argparse
from datetime import datetime, timedelta
import pytz

# Define Sectors and Top 5 Constituents
SECTORS = {
    "XLK": ["AAPL", "NVDA", "MSFT", "AVGO", "CRM"],
    "XLV": ["LLY", "UNH", "JNJ", "ABBV", "MRK"],
    "XLF": ["BRK-B", "JPM", "V", "MA", "GS"],
    "XLY": ["AMZN", "TSLA", "HD", "MCD", "NKE"],
    "XLC": ["META", "GOOGL", "GOOG", "NFLX", "DIS"],
    "XLI": ["CAT", "GE", "UNP", "HON", "RTX"],
    "XLP": ["PG", "COST", "KO", "PEP", "WMT"],
    "XLE": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "XLRE": ["PLD", "AMT", "EQIX", "WELL", "PSA"],
    "XLU": ["NEE", "SO", "DUK", "CEG", "SRE"],
    "XLB": ["LIN", "APD", "SHW", "CTVA", "FCX"]
}

SECTOR_NAMES = {
    "XLK": "情報技術", "XLV": "ヘルスケア", "XLF": "金融", "XLY": "一般消費財",
    "XLP": "生活必需品", "XLC": "通信", "XLE": "エネルギー", "XLI": "資本財",
    "XLB": "素材", "XLU": "公共事業", "XLRE": "不動産",
    "QQQ": "NAS100", "SPY": "S&P500", "DIA": "NYダウ"
}

INDICES = ["QQQ", "SPY", "DIA"]
MACRO_TICKERS = ["GLD", "FXY", "UUP", "TLT"]
MACRO_NAMES = {
    "GLD": "ゴールド (Gold)",
    "FXY": "日本円 (Yen)",
    "UUP": "ドル指数 (USD)",
    "TLT": "米国債20年超 (Bonds)"
}

def fetch_data(start_str=None, end_str=None):
    all_tickers = []
    for sector, stocks in SECTORS.items():
        all_tickers.append(sector)
        all_tickers.extend(stocks)
    all_tickers.extend(INDICES)
    all_tickers.extend(MACRO_TICKERS)
    
    all_tickers = list(set(all_tickers))
    
    # Determine interval and period based on start_date
    interval = "15m"
    use_period = False
    
    if start_str:
        try:
            start_dt = pd.to_datetime(start_str)
            days_ago = (datetime.now() - start_dt).days
            if days_ago > 59:
                interval = "1d"
                print(f"Start date is {days_ago} days ago. Switching to daily interval (1d).")
        except:
            pass
    else:
        use_period = True

    print(f"Fetching data for {len(all_tickers)} tickers (Interval: {interval})...")
    
    try:
        if use_period:
            data = yf.download(all_tickers, period="1mo", interval="15m", group_by='ticker', auto_adjust=True, threads=True)
        else:
            # yfinance expects end date to be exclusive, so add 1 day to cover the full end date if needed, 
            # but usually for 'end' arg provided by user we assume it includes that day? 
            # actually yfinance download 'end' is exclusive. 
            # Converting string to datetime to add offset safely
            s_dt = pd.to_datetime(start_str)
            e_dt = pd.to_datetime(end_str) + timedelta(days=1)
            
            data = yf.download(all_tickers, start=s_dt.strftime("%Y-%m-%d"), end=e_dt.strftime("%Y-%m-%d"), interval=interval, group_by='ticker', auto_adjust=True, threads=True)
            
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def filter_data_by_date(df, start_date_str=None, end_date_str=None):
    if df is None or df.empty: return df
    filtered = df.copy()
    is_tz_aware = filtered.index.tzinfo is not None
    timezone = pytz.timezone("America/New_York")
    
    if start_date_str:
        try:
            start_dt = pd.to_datetime(start_date_str)
            if is_tz_aware and start_dt.tzinfo is None:
                start_dt = timezone.localize(start_dt)
            filtered = filtered[filtered.index >= start_dt]
        except: pass

    if end_date_str:
        try:
            end_dt = pd.to_datetime(end_date_str)
            if is_tz_aware and end_dt.tzinfo is None:
                end_dt = timezone.localize(end_dt)
            filtered = filtered[filtered.index <= end_dt]
        except: pass
    return filtered

def calculate_mdd_rf(df):
    """
    Calculate Maximum Drawdown (MDD) and Recovery Factor (RF).
    MDD: Max percentage drop from peak to trough within the period.
    RF: Net Return / |MDD|.
    """
    if df.empty: return 0.0, 0.0

    # Calculate High water mark
    roll_max = df['High'].cummax()
    # Drawdown = (Low - HighWaterMark) / HighWaterMark
    daily_dd = (df['Low'] - roll_max) / roll_max
    mdd = daily_dd.min() # This is a negative float, e.g. -0.05 for -5%
    
    # Return for the period
    start_p = df.iloc[0]['Open']
    end_p = df.iloc[-1]['Close']
    ret = (end_p - start_p) / start_p # Float, e.g. 0.10 for 10%

    # RF Calculation
    rf = 0.0
    if mdd == 0:
        if ret > 0: rf = 99.99 # Infinite recovery (no drawdown)
        else: rf = 0.0 # No return, no drawdown
    else:
        rf = ret / abs(mdd)
        
    return mdd * 100, rf # Return MDD as percentage (negative) and RF (ratio)

def analyze_last_day_shape(df, prev_close=None):
    if df.empty: return 0, "N/A", 0, 0, 0, 0, ""
    last_date = df.index[-1].date()
    # Handle duplicate indices if any, or strictly filter by date
    last_day_df = df[df.index.date == last_date]
    if last_day_df.empty: return 0, "N/A", 0, 0, 0, 0, ""
        
    open_p = last_day_df.iloc[0]['Open']
    close_p = last_day_df.iloc[-1]['Close']
    high_p = last_day_df['High'].max()
    low_p = last_day_df['Low'].min()
    
    # Use Prev Close for % change if available, else Open (Intraday)
    base_p = prev_close if prev_close is not None else open_p
    move_pct = (close_p - base_p) / base_p * 100
    
    range_len = high_p - low_p
    date_str = last_date.strftime("%m/%d")
    if range_len == 0: return 0, "Doji", move_pct, open_p, high_p, close_p, date_str
    
    close_pos = (close_p - low_p) / range_len
    
    desc = ""
    score = 0 # -2 to +2
    
    if close_pos > 0.8:
        desc = "高値引け (Strong)"
        score = 2
    elif close_pos < 0.2:
        desc = "安値引け (Weak)"
        score = -2
    elif move_pct > 0.3:
        desc = "陽線 (Pos)"
        score = 1
    elif move_pct < -0.3:
        desc = "陰線 (Neg)"
        score = -1
    else:
        desc = "保ち合い (Neut)"
        score = 0
        
    return score, desc, move_pct, open_p, high_p, close_p, date_str

def generate_three_scenarios(trend_return, last_score, last_move):
    """
    Generate 3 distinct scenarios: Good (Bull), Avg (Base), Bad (Bear).
    Returns: Grade, Scenarios Dict
    """
    grade = "普"
    scenarios = {
        "Good": "",
        "Avg": "",
        "Bad": ""
    }
    
    # 1. Strong Uptrend (>3%)
    if trend_return > 3.0:
        if last_score >= 1: # Uptrend + Strong
            grade = "良"
            scenarios["Avg"] = "上昇トレンド継続。高値更新を試す動き。"
            scenarios["Good"] = "勢いが加速し、帯状に上昇する (Band Walk)。"
            scenarios["Bad"] = "利益確定売りで一時的な調整が入る。"
        elif last_score <= -1: # Uptrend + Weak
            grade = "普"
            scenarios["Avg"] = "上昇一服。調整局面入りを示唆。"
            scenarios["Good"] = "押し目を形成し、再度上昇に転じる。"
            scenarios["Bad"] = "直近安値を割り込み、トレンドが崩れる。"
        else: # Uptrend + Neutral
            grade = "良"
            scenarios["Avg"] = "上昇トレンド継続。押し目待ち。"
            scenarios["Good"] = "もみ合いを上放れし、再加速する。"
            scenarios["Bad"] = "調整が長引き、レンジ相場へ移行する。"
            
    # 2. Strong Downtrend (<-3%)
    elif trend_return < -3.0:
        if last_score >= 1: # Downtrend + Strong
            grade = "普"
            scenarios["Avg"] = "自律反発。ショートカバー優勢。"
            scenarios["Good"] = "底打ちを確認し、本格的なリバウンドへ。"
            scenarios["Bad"] = "あくまで一時的な反発で、再度安値を更新。"
        elif last_score <= -1: # Downtrend + Weak
            grade = "悪"
            scenarios["Avg"] = "下落継続。安値模索の展開。"
            scenarios["Good"] = "セリングクライマックスを迎え、急反発する。"
            scenarios["Bad"] = "売りが売りを呼び、パニック的な下げになる。"
        else:
            grade = "悪"
            scenarios["Avg"] = "下落トレンド継続。戻り売り警戒。"
            scenarios["Good"] = "下げ止まり、底固めの動きへ。"
            scenarios["Bad"] = "ジリジリと下値を切り下げる。"
            
    # 3. Range / Neutral
    else:
        if last_score >= 1: # Range + Strong
            grade = "良"
            scenarios["Avg"] = "レンジ上限へのトライ。"
            scenarios["Good"] = "レンジを上抜け、新たな上昇トレンドへ。"
            scenarios["Bad"] = "レンジ上限で跳ね返され、再度保ち合いへ。"
        elif last_score <= -1: # Range + Weak
            grade = "悪"
            scenarios["Avg"] = "レンジ下限へのトライ。"
            scenarios["Good"] = "下限でサポートされ、反発する。"
            scenarios["Bad"] = "レンジを下抜け、下落トレンド入りする。"
        else:
            grade = "普"
            scenarios["Avg"] = "方向感なし。様子見。"
            scenarios["Good"] = "材料出現で動意づく。"
            scenarios["Bad"] = "出来高細り、閑散相場となる。"
            
    return grade, scenarios

def analyze_ticker(ticker, data, start_arg, end_arg):
    try:
        if ticker not in data.columns.levels[0]: return None
        raw = data[ticker].dropna()
    except KeyError:
        return None
    except Exception as e:
        # Fallback for flat index if only one ticker or other structure
        if ticker in data.columns:
            raw = data[ticker].dropna()
        else:
            return None
    df = filter_data_by_date(raw, start_arg, end_arg)
    if df.empty: return None
    
    start_p = df.iloc[0]['Open']
    end_p = df.iloc[-1]['Close']
    high_p = df['High'].max()
    
    # Convert timestamps to JST for display
    jst = pytz.timezone('Asia/Tokyo')
    first_ts = df.index[0]
    last_ts = df.index[-1]
    
    if first_ts.tzinfo is not None:
        first_jst = first_ts.astimezone(jst)
        last_jst = last_ts.astimezone(jst)
        start_date_str = first_jst.strftime("%m/%d %H:%M")
        end_date_str = last_jst.strftime("%m/%d %H:%M") + " JST"
    else:
        # For daily data (no timezone info), just show date
        start_date_str = first_ts.strftime("%m/%d")
        end_date_str = last_ts.strftime("%m/%d")
    
    ret = (end_p - start_p) / start_p * 100
    
    # Calculate Previous Close for accurate Daily % Change
    prev_close = None
    try:
        current_date = df.index[-1].date()
        # Look at raw data strictly before the current day
        past_data = raw[raw.index.date < current_date]
        if not past_data.empty:
            prev_close = past_data.iloc[-1]['Close']
    except Exception:
        pass

    score, desc, move, l_open, l_high, l_close, l_date = analyze_last_day_shape(df, prev_close)
    
    grade, scenarios = generate_three_scenarios(ret, score, move)
    
    mdd, rf = calculate_mdd_rf(df)
    
    return {
        "Ticker": ticker,
        "Start": start_p,
        "High": high_p,
        "End": end_p,
        "Return": ret,
        "DateRange": f"{start_date_str} - {end_date_str}",
        "LastScore": score,
        "LastDesc": desc,
        "LastMove": move,
        "LastOpen": l_open,
        "LastHigh": l_high,
        "LastClose": l_close,
        "LastDate": l_date,
        "Grade": grade,
        "Scenarios": scenarios,
        "MDD": mdd,
        "RF": rf
    }

def analyze_sector(sector_ticker, holdings, data, start_arg=None, end_arg=None):
    s_res = analyze_ticker(sector_ticker, data, start_arg, end_arg)
    if not s_res: return None
    
    stats = []
    
    # Force minimal 5 stocks? We have 5 in holdings.
    # We want to classify ALL 5 into Engine or Brake.
    # Logic: 
    #   Engine: Return > Sector Return (Leaders)
    #   Brake: Return <= Sector Return (Laggards)
    
    for stock in holdings:
        st_res = analyze_ticker(stock, data, start_arg, end_arg)
        if not st_res: continue
        
        rel_trend = st_res['Return'] - s_res['Return']
        role = "NEUTRAL"
        reason = ""
        
        # Forced Classification
        if rel_trend > 0:
            role = "ENGINE (牽引)"
            if st_res['LastScore'] >= 0:
                reason = f"トレンド牽引 (+{st_res['Return']:.1f}%)"
            else:
                reason = f"トレンドは強いが、直近で失速 ({st_res['LastDesc']})"
        else:
            role = "BRAKE (重石)"
            if st_res['LastScore'] > 0:
                reason = f"出遅れだが、直近は買われている ({st_res['LastDesc']})"
            else:
                reason = f"トレンドも直近も弱い ({st_res['LastDesc']})"
                
        st_res['Role'] = role
        st_res['Reason'] = reason
        stats.append(st_res)

    stats_df = pd.DataFrame(stats)
    if not stats_df.empty:
        stats_df = stats_df.sort_values("Return", ascending=False)
        
    # Calculate Fund Quality (Breadth)
    # How many are Engines (Outperforming sector)?
    # If 4-5: Broad participation (Healthy)
    # If 1-2: Narrow participation (Selective)
    current_engines = [s for s in stats if "ENGINE" in s['Role']]
    engine_count = len(current_engines)
    total_count = len(stats)
    
    quality = "普通 (Mixed)"
    if total_count > 0:
        ratio = engine_count / total_count
        if ratio >= 0.8: # 4 or 5 out of 5
            quality = "健全な広がり (Healthy)"
        elif ratio <= 0.2: # 1 out of 5
            quality = "一部への逃避 (Selective)"
        elif ratio > 0.5:
            quality = "やや広い (Broad)"
        else:
            quality = "選別色あり (Mixed)"
    
    return {
        "sector": sector_ticker,
        "name": SECTOR_NAMES.get(sector_ticker, sector_ticker),
        "return": s_res['Return'],
        "start_p": s_res['Start'],
        "end_p": s_res['End'],
        "date_range": s_res['DateRange'],
        "last_desc": s_res['LastDesc'],
        "last_move": s_res['LastMove'],
        "last_date": s_res['LastDate'],
        "grade": s_res['Grade'],
        "quality": quality,
        "scenarios": s_res['Scenarios'],
        "stats": stats_df,
        "MDD": s_res['MDD'],
        "RF": s_res['RF']
    }

def generate_narrative_report(results, index_results, macro_results, start_dt_str, end_dt_str):
    # Use actual analyzed range from one of the results if possible for more precision
    analyzed_range = f"{start_dt_str} 〜 {end_dt_str}"
    if index_results:
        # Extract existing range from index result, assuming format "MM/DD HH:MM - MM/DD HH:MM JST"
        # But here start_dt_str is YYYY-MM-DD. 
        # analyze_ticker returns DateRange in detailed format.
        analyzed_range = index_results[0]['DateRange'] 

    report = []
    report.append("【天才投資家レポート】")
    report.append(f"分析期間: {analyzed_range}\n")
    
    # 1. Indices (Detailed)
    report.append("### ① 全体観 (Indices)")
    for idx_res in index_results:
        idx = idx_res['Ticker']
        name = SECTOR_NAMES.get(idx, idx)
        
        report.append(f"**{name} ({idx})**: {idx_res['Grade']}")
        report.append(f"  Price: {idx_res['Start']:.2f} -> {idx_res['End']:.2f} ({idx_res['Return']:+.2f}%) [{idx_res['DateRange']}]")
        report.append(f"  📊 **リカバリー・ファクター (RF): {idx_res['RF']:.2f}** | **最大ドローダウン (MDD): {idx_res['MDD']:.1f}%**")
        report.append(f"  直近: {idx_res['LastDesc']} ({idx_res['LastMove']:+.1f}%) [{idx_res['LastDate']}]")
        
        # Drivers/Draggers Logic
        related_sectors = []
        if idx == "QQQ": related_sectors = ["XLK", "XLC", "XLY"]
        elif idx == "DIA": related_sectors = ["XLI", "XLF", "XLV"]
        else: related_sectors = ["XLK", "XLF", "XLV", "XLY", "XLI", "XLE"]
        
        drivers = []
        draggers = []
        
        for sec_ticker in related_sectors:
            if sec_ticker in results:
                sec_ret = results[sec_ticker]['return']
                sec_name = results[sec_ticker]['name']
                if sec_ret > idx_res['Return'] + 0.5:
                    drivers.append(f"- {sec_name}: {sec_ret:+.1f}%")
                elif sec_ret < idx_res['Return'] - 0.5:
                    draggers.append(f"- {sec_name}: {sec_ret:+.1f}%")
                    
        if drivers:
            report.append("🔥 **Engine (牽引)**:")
            report.extend(drivers)
        if draggers: 
            report.append("🧊 **Brake (重石)**:")
            report.extend(draggers)
        report.append("")

    report.append("="*40 + "\n")
    
    # 2. Sector Analysis
    sorted_secs = sorted(results.values(), key=lambda x: x['return'], reverse=True)
    winner = sorted_secs[0]
    loser = sorted_secs[-1]

    # Macro Conclusion
    # Determine Risk Sentiment based on Tech/ConsDisc vs Utilities/Staples
    risk_on_score = 0
    if "XLK" in results and "XLY" in results:
        risk_on_avg = (results["XLK"]["return"] + results["XLY"]["return"]) / 2
        risk_off_avg = 0
        count = 0
        if "XLU" in results: 
            risk_off_avg += results["XLU"]["return"]
            count += 1
        if "XLP" in results:
            risk_off_avg += results["XLP"]["return"]
            count += 1
        
        if count > 0:
            risk_off_avg /= count
            if risk_on_avg > risk_off_avg + 1.0:
                risk_on_score = 1 # Risk On
            elif risk_on_avg < risk_off_avg - 1.0:
                risk_on_score = -1 # Risk Off
    
    flow_desc = ""
    if risk_on_score == 1:
        flow_desc = "成長株への資金回帰が見られ、市場心理は「リスク選好 (Risk On)」です。"
    elif risk_on_score == -1:
        flow_desc = "ディフェンシブセクターへの逃避が見られ、市場心理は「リスク回避 (Risk Off)」です。"
    else:
        flow_desc = "セクター間の循環色が強く、方向感を探る展開です。"

    report.append("### ② マクロ結論: 資金流動")
    report.append(f"資金は**「{loser['name']}」から「{winner['name']}」へ**シフトしています。")
    report.append(f"【真実の眼】 {flow_desc}")
    report.append(f"勝者({winner['name']})は{winner['quality']}な買いが入っており、敗者({loser['name']})は資金流出が鮮明です。")
    report.append("\n" + "-"*20 + "\n")

    for res in sorted_secs:
        sec_name = res['name']
        ticker = res['sector']
        stats = res['stats']
        
        engines = stats[stats['Role'].str.contains('ENGINE')]
        brakes = stats[stats['Role'].str.contains('BRAKE')]
        
        report.append(f"## {sec_name} ({ticker})")
        report.append(f"**判定**: {res['grade']}")
        report.append(f"**資金の質の判定**: {res['quality']}")
        
        report.append(f"**Price**: ${res['start_p']:.2f} -> ${res['end_p']:.2f} ({res['return']:+.2f}%) [{res['date_range']}]")
        report.append(f"📊 **リカバリー・ファクター (RF): {res['RF']:.2f}** | **最大ドローダウン (MDD): {res['MDD']:.1f}%**")
        report.append(f"**直近**: {res['last_desc']} [{res['last_date']}]")
        
        if not engines.empty:
            report.append("🔥 **Engine (牽引)**:")
            for _, row in engines.iterrows():
                # Ticker: Trend: ... [RF:X.XX] / Last: ... -> Reason
                trend_str = f"Trend: {row['Start']:.2f}->{row['High']:.2f}->{row['End']:.2f} ({row['Return']:+.1f}%) [{row['DateRange']}] (始値->高値->終値) **[RF:{row['RF']:.2f}]**"
                last_str = f"Last: {row['LastOpen']:.2f}->{row['LastHigh']:.2f}->{row['LastClose']:.2f} ({row['LastMove']:+.1f}%) [{row['LastDate']}] (始値->高値->終値)"
                report.append(f"- {row['Ticker']}: {trend_str} / {last_str} -> {row['Reason']}")
        
        if not brakes.empty:
            report.append("🧊 **Brake (重石)**:")
            for _, row in brakes.iterrows():
                trend_str = f"Trend: {row['Start']:.2f}->{row['High']:.2f}->{row['End']:.2f} ({row['Return']:+.1f}%) [{row['DateRange']}] (始値->高値->終値) **[RF:{row['RF']:.2f}]**"
                last_str = f"Last: {row['LastOpen']:.2f}->{row['LastHigh']:.2f}->{row['LastClose']:.2f} ({row['LastMove']:+.1f}%) [{row['LastDate']}] (始値->高値->終値)"
                report.append(f"- {row['Ticker']}: {trend_str} / {last_str} -> {row['Reason']}")
        
        report.append("\n" + "-"*20 + "\n")

    # 3. Rankings Section
    report.append("### ③ リカバリー・ファクター (RF) ランキング")
    report.append("「リスクあたりのリターン効率」を比較します。数値が高いほど優秀です。\n")
    
    # Sector Ranking
    sorted_rf_sectors = sorted(results.values(), key=lambda x: x['RF'], reverse=True)
    report.append("【セクター別 RF ランキング】")
    rank_str_list = []
    medals = ["🥇", "🥈", "🥉"]
    for i, res in enumerate(sorted_rf_sectors):
        rank_icon = medals[i] if i < 3 else f"{i+1}."
        rank_str_list.append(f"{rank_icon} **{res['name']} ({res['sector']})**: RF {res['RF']:.2f} (Return: {res['return']:+.1f}% / MDD: {res['MDD']:.1f}%)")
    report.append(" ".join(rank_str_list))
    report.append("")
    
    # Stock Ranking
    all_stocks = []
    for res in results.values():
        if not res['stats'].empty:
            for _, row in res['stats'].iterrows():
                all_stocks.append(row)
    
    # Sort all stocks by RF
    sorted_stocks_rf = sorted(all_stocks, key=lambda x: x['RF'], reverse=True)
    top_10 = sorted_stocks_rf[:10]
    bottom_5 = sorted_stocks_rf[-5:]
    
    report.append("【銘柄別 RF ランキング (Top 10)】")
    top_str_list = []
    for i, row in enumerate(top_10):
        rank_icon = medals[i] if i < 3 else f"{i+1}."
        top_str_list.append(f"{rank_icon} **{row['Ticker']}**: RF {row['RF']:.2f} (Return: {row['Return']:+.1f}% / MDD: {row['MDD']:.1f}%)")
    report.append(" ".join(top_str_list))
    report.append("")
    
    report.append("【銘柄別 RF ワースト (Bottom 5)】")
    btm_str_list = []
    for row in bottom_5:
        btm_str_list.append(f"💀 **{row['Ticker']}**: RF {row['RF']:.2f} (Return: {row['Return']:+.1f}% / MDD: {row['MDD']:.1f}%)")
    report.append(" ".join(btm_str_list))
    
    report.append("\n" + "="*40 + "\n")

    # 4. Macro Section
    report.append("### ④ 注目マクロ指標 (Macro)")
    for res in macro_results:
        m_ticker = res['Ticker']
        m_name = MACRO_NAMES.get(m_ticker, m_ticker)
        report.append(f"**{m_name} ({m_ticker})**: {res['Return']:+.2f}%")
        report.append(f"  Price: {res['Start']:.2f} -> {res['End']:.2f} [{res['DateRange']}]")
        report.append(f"  直近: {res['LastDesc']} ({res['LastMove']:+.2f}%) [{res['LastDate']}]")
        report.append(f"  RF: {res['RF']:.2f} | MDD: {res['MDD']:.1f}%")
        report.append("")
    
    return "\n".join(report)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=str)
    parser.add_argument('--end', type=str)
    parser.add_argument('--days', type=int, default=14)
    args = parser.parse_args()

    # Use JST for default dates to align with user time (and correct US close relative to JST morning)
    jst = pytz.timezone('Asia/Tokyo')
    end_dt = datetime.now(jst)
    
    if args.end: end_dt = pd.to_datetime(args.end)
    start_dt = end_dt - timedelta(days=args.days)
    if args.start: start_dt = pd.to_datetime(args.start)
        
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")
    
    print(f"Analyzing {start_str} to {end_str}...")
    
    data = fetch_data(start_str, end_str)
    if data is None: return

    index_results = []
    for idx in INDICES:
        res = analyze_ticker(idx, data, start_str, end_str)
        if res: index_results.append(res)

    macro_results = []
    for m in MACRO_TICKERS:
        res = analyze_ticker(m, data, start_str, end_str)
        if res: macro_results.append(res)

    results = {}
    for sector, holdings in SECTORS.items():
        res = analyze_sector(sector, holdings, data, start_str, end_str)
        if res: results[sector] = res

    if results:
        report = generate_narrative_report(results, index_results, macro_results, start_str, end_str)
        with open("analysis_output.txt", "w", encoding='utf-8') as f:
            f.write(report)
        print("Report Generated.")

if __name__ == "__main__":
    main()
