import os
import pandas as pd
import requests
from datetime import datetime

class NSEHistoricalMomentumScanner:
    def __init__(self):
        # Master Watchlist representing highly liquid NSE F&O underlying scripts
        self.watchlist = [
            "DRREDDY", "CIPLA", "TORNTPHARM", "NATIONALUM", "MAXHEALTH",
            "PERSISTENT", "ASTRAL", "SUPREMEIND", "WAAREE", "KPITTECH",
            "LUPIN", "MANKIND", "GLENMARK", "MARICO", "NAM-INDIA",
            "PIIND", "UNOMINDA", "SBICARD", "TATACONSUM", "RELIANCE", 
            "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL", 
            "ITC", "TRENT", "M&M", "MARUTI", "INDIGO", "HINDALCO"
        ]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def fetch_market_history(self, ticker):
        """
        Fetches up to 60 days of historical bar trends to allow 
        seamless calculation of deep historical dates.
        """
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.NS?interval=1d&range=60d"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return None
            
            data = response.json()
            result = data['chart']['result'][0]
            timestamps = result['timestamp']
            indicators = result['indicators']['quote'][0]
            
            df = pd.DataFrame({
                'Date': [datetime.fromtimestamp(ts).strftime('%Y-%m-%d') for ts in timestamps],
                'Close': indicators['close'],
                'High': indicators['high'],
                'Low': indicators['low'],
                'Volume': indicators['volume']
            }).dropna()
            return df
        except Exception:
            return None

    def execute_scan(self):
        print("=" * 60)
        print("          NSE F&O INTRADAY MOMENTUM ENGINE          ")
        print("=" * 60)
        
        # 1. Capture user choice input for dynamic date processing
        user_input = input("Enter target backdate (YYYY-MM-DD) or press [ENTER] for Latest Live Session: ").strip()
        
        target_date = None
        if user_input != "":
            try:
                # Validate date format structural strings
                datetime.strptime(user_input, "%Y-%m-%d")
                target_date = user_input
                print(f"[+] Initializing Backdate Time-Machine to study: {target_date}")
            except ValueError:
                print("[-] Invalid format. Exiting run. Please use standard YYYY-MM-DD layout (e.g. 2026-06-25).")
                return
        else:
            print("[+] No date entered. Processing latest completed market session data...")

        all_data = []
        print("[*] Contacting exchange server pipelines...")
        
        for ticker in self.watchlist:
            df = self.fetch_market_history(ticker)
            if df is None or len(df) < 15:
                continue
            
            # 2. Dynamic Time-Machine Truncation Logic
            if target_date:
                # Slice away data rows that occurred AFTER the targeted historical prompt date
                df = df[df['Date'] <= target_date]
                if len(df) < 9:
                    continue
            
            all_data.append((ticker, df))
            
        if not all_data:
            print("[-] Critical Error: No data logs retrieved matching the date criteria constraints.")
            return

        # Isolate the exact runtime session date we are evaluating
        actual_study_date = all_data[0][1]['Date'].iloc[-1]
        print(f"[✓] Data arrays aligned. Confirmed actual target date under calculation: {actual_study_date}")
        
        # --- PHASE 1: IDENTIFY THE SELECTED DAY'S EXTREME GAINERS/LOSERS ---
        session_performance = []
        for ticker, df in all_data:
            study_close = df['Close'].iloc[-1]
            study_prev_close = df['Close'].iloc[-2]
            pct_change = ((study_close - study_prev_close) / study_prev_close) * 100
            
            session_performance.append({
                'Ticker': ticker,
                'Close': study_close,
                '% Change': pct_change,
                'df': df
            })
            
        perf_df = pd.DataFrame(session_performance)
        top_gainers = perf_df.sort_values(by='% Change', ascending=False).head(5)
        top_losers = perf_df.sort_values(by='% Change', ascending=True).head(5)
        
        # --- PHASE 2 & 3: HISTORICAL LOOKBACK & NEXT-SESSION PATTERN DETECTION ---
        predictions = []
        
        for item in session_performance:
            ticker = item['Ticker']
            df = item['df']
            
            # Isolate the exact 7-day trailing lookback right before our targeted execution day
            lookback_window = df.iloc[-8:-1]
            lb_max_high = lookback_window['High'].max()
            lb_min_low = lookback_window['Low'].min()
            lb_avg_vol = lookback_window['Volume'].mean()
            
            # Targeted active day records
            latest_close = df['Close'].iloc[-1]
            latest_vol = df['Volume'].iloc[-1]
            latest_pct_val = item['% Change']  # FIXED: Removed the messy duplicate text assignment typo
            
            vol_expansion = latest_vol / lb_avg_vol if lb_avg_vol > 0 else 1.0
            
            momentum_bias = "Neutral Consolidation"
            priority_score = 0.0
            
            # Pattern Alpha: Volatility Compression Upside Outbreak 
            if latest_close > lb_max_high and latest_vol > lb_avg_vol:
                momentum_bias = "Pattern Alpha Breakout (Bullish Momentum Target)"
                priority_score = latest_pct_val * vol_expansion
                
            # Pattern Beta: Support Level Capitulation Breakdown
            elif latest_close < lb_min_low and latest_vol > lb_avg_vol:
                momentum_bias = "Pattern Beta Breakdown (Bearish Momentum Target)"
                priority_score = latest_pct_val * vol_expansion
                
            predictions.append({
                "Ticker Symbol": ticker,
                "LTP on Studied Session (INR)": round(latest_close, 2),
                "Intraday Change %": round(latest_pct_val, 2),
                "7-Session Looking Ceiling": round(lb_max_high, 2),
                "7-Session Looking Floor": round(lb_min_low, 2),
                "Volume Multiple Expansion": round(vol_expansion, 2),
                "Structural Signature": momentum_bias,
                "Next Session Priority Score": round(priority_score, 2)
            })

        predict_df = pd.DataFrame(predictions)
        
        potential_gainers = predict_df[predict_df['Next Session Priority Score'] > 0].sort_values(by='Next Session Priority Score', ascending=False).head(5)
        potential_losers = predict_df[predict_df['Next Session Priority Score'] < 0].sort_values(by='Next Session Priority Score', ascending=True).head(5)

        # --- PHASE 4: REFORMAT OUTPUT FILE DISTRIBUTIONS ---
        output_filename = f"NSE_Momentum_Scan_{actual_study_date}.xlsx"
        
        with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
            # Sheet 1: Summary mapping profiles
            summary_sheets = []
            for idx, r in top_gainers.iterrows():
                summary_sheets.append({"Ticker": r['Ticker'], "Type": "Top Gainer", "% Change": round(r['% Change'], 2), "LTP": round(r['Close'], 2)})
            for idx, r in top_losers.iterrows():
                summary_sheets.append({"Ticker": r['Ticker'], "Type": "Top Loser", "% Change": round(r['% Change'], 2), "LTP": round(r['Close'], 2)})
            
            pd.DataFrame(summary_sheets).to_excel(writer, sheet_name='Study Session Summary', index=False)
            
            # Sheet 2 & 3: Pattern Calculations for the Following Day
            potential_gainers[["Ticker Symbol", "LTP on Studied Session (INR)", "Intraday Change %", "Volume Multiple Expansion", "Structural Signature"]].to_excel(writer, sheet_name='Potential Next-Day Gainers', index=False)
            potential_losers[["Ticker Symbol", "LTP on Studied Session (INR)", "Intraday Change %", "Volume Multiple Expansion", "Structural Signature"]].to_excel(writer, sheet_name='Potential Next-Day Losers', index=False)
            
            # Sheet 4: Complete Underlying Logs
            predict_df.to_excel(writer, sheet_name='All Scanned Derivatives', index=False)

        print("-" * 60)
        print(f"[✓] Processing Complete for targeted reference date context!")
        print(f"[✓] Dynamic Spreadsheet Generated: '{os.path.abspath(output_filename)}'")
        print("-" * 60)

if __name__ == "__main__":
    scanner = NSEHistoricalMomentumScanner()
    scanner.execute_scan()
