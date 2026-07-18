import os
import pandas as pd
import requests
from datetime import datetime

class NSEVCPDailyScanner:
    def __init__(self):
        # Broad base of highly liquid F&O scripts representing thematic sectors
        self.watchlist = [
            "DRREDDY", "CIPLA", "TORNTPHARM", "NATIONALUM", "MAXHEALTH",
            "PERSISTENT", "ASTRAL", "SUPREMEIND", "WAAREE", "KPITTECH",
            "LUPIN", "MANKIND", "GLENMARK", "MARICO", "NAM-INDIA",
            "PIIND", "UNOMINDA", "SBICARD", "TATACONSUM", "RELIANCE", 
            "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL", 
            "ITC", "TRENT", "M&M", "MARUTI", "INDIGO", "HINDALCO", "KOTAKBANK"
        ]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def fetch_equity_history(self, ticker):
        """Fetches up to 60 days of daily bar intervals to trace multi-wave VCP cycles."""
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

    def execute_eod_vcp_scan(self):
        print("=" * 70)
        print("     MARK MINERVINI VCP / INVERTED DISTRIBUTION SCANNER     ")
        print("=" * 70)
        
        # User Date Prompt Interface Handler
        user_prompt = input("Enter historic backdate (YYYY-MM-DD) or press [ENTER] for Latest EOD: ").strip()
        
        target_backdate = None
        if user_prompt != "":
            try:
                datetime.strptime(user_prompt, "%Y-%m-%d")
                target_backdate = user_prompt
                print(f"[+] Rolling backend dataframes to target date context: {target_backdate}")
            except ValueError:
                print("[-] Incorrect format structure. Please run again using YYYY-MM-DD (e.g., 2026-06-29).")
                return
        else:
            print("[+] Querying live exchange pipelines for the latest closed session...")

        raw_scanned_pool = []
        
        for ticker in self.watchlist:
            df = self.fetch_equity_history(ticker)
            if df is None or len(df) < 25:
                continue
            
            # Truncate dates cleanly if backtesting via prompt input
            if target_backdate:
                df = df[df['Date'] <= target_backdate]
                if len(df) < 20:
                    continue
            
            raw_scanned_pool.append((ticker, df))
            
        if not raw_scanned_pool:
            print("[-] Structural Error: No active market data rows loaded from proxy pools.")
            return

        # Synchronize exact session date under execution
        actual_processing_date = raw_scanned_pool[0][1]['Date'].iloc[-1]
        print(f"[✓] Data synchronization stable. Processing actual date: {actual_processing_date}")
        
        buy_candidates = []
        sell_candidates = []
        
        for ticker, df in raw_scanned_pool:
            # Capture latest day stats
            ltp = df['Close'].iloc[-1]
            day_high = df['High'].iloc[-1]
            day_low = df['Low'].iloc[-1]
            day_vol = df['Volume'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            intraday_chg = ((ltp - prev_close) / prev_close) * 100
            
            # Simple Moving Averages
            sma_20 = df['Close'].iloc[-20:].mean()
            sma_50 = df['Close'].iloc[-50:].mean()
            
            # Parse past 15-day lookup frames to gauge diminishing swing structures (T counts)
            historical_window = df.iloc[-16:-1]
            wave_high = historical_window['High'].max()
            wave_low = historical_window['Low'].min()
            avg_volume = historical_window['Volume'].mean()
            
            vol_dry_ratio = day_vol / avg_volume if avg_volume > 0 else 1.0
            
            # Formulate triggers
            buy_trigger = round(day_high + 0.55, 2)
            sell_trigger = round(day_low - 0.55, 2)
            
            # --- MINERVINI BUY SIDE FILTER (VCP ACCUMULATION) ---
            if ltp > sma_20 and sma_20 > sma_50:
                if ltp >= (wave_high * 0.94) and vol_dry_ratio < 1.25:
                    buy_candidates.append({
                        "Ticker": ticker,
                        "EOD Closing Price": round(ltp, 2),
                        "Intraday Change %": round(intraday_chg, 2),
                        "Pivot Breakout Trigger": buy_trigger,
                        "Defensive Stop Loss": round(day_low * 0.985, 2),
                        "Volume Dry-up Ratio": round(vol_dry_ratio, 2),
                        "Entry Execution Strategy": f"Buy ONLY if price breaks above the pivot of ₹{buy_trigger} on a 15-min candle. Volatility has compressed and supply is dried up; this trigger ensures you catch the momentum as institutional markup begins."
                    })
            
            # --- SELL SIDE FILTER (INVERTED DISTRIBUTION VCP) ---
            elif ltp < sma_20 and sma_20 < sma_50:
                if ltp <= (wave_low * 1.06):
                    sell_candidates.append({
                        "Ticker": ticker,
                        "EOD Closing Price": round(ltp, 2),
                        "Intraday Change %": round(intraday_chg, 2),
                        "Pivot Breakdown Trigger": sell_trigger,
                        "Defensive Stop Loss": round(day_high * 1.015, 2),
                        "Volume Exhaustion Ratio": round(vol_dry_ratio, 2),
                        "Entry Execution Strategy": f"Short ONLY if price breaks below the horizontal floor of ₹{sell_trigger}. Diminishing bounces indicate the absence of institutional buyers. Selling pressure will cascade once this support cracks."
                    })

        # Convert arrays to DataFrames
        buy_df = pd.DataFrame(buy_candidates)
        sell_df = pd.DataFrame(sell_candidates)
        
        # Sort files to surface the tightest, lowest-risk entry profiles to the top
        if not buy_df.empty: buy_df = buy_df.sort_values(by="Volume Dry-up Ratio", ascending=True)
        if not sell_df.empty: sell_df = sell_df.sort_values(by="Volume Exhaustion Ratio", ascending=True)
        
        # Generate Excel spreadsheet output
        output_name = f"NSE_Minervini_Scanner_{actual_processing_date}.xlsx"
        with pd.ExcelWriter(output_name, engine='openpyxl') as writer:
            if not buy_df.empty:
                buy_df.to_excel(writer, sheet_name='Bullish Buy Watchlist', index=False)
            else:
                pd.DataFrame([{"Alert": "No stocks met strict VCP buy limits today"}]).to_excel(writer, sheet_name='Bullish Buy Watchlist', index=False)
                
            if not sell_df.empty:
                sell_df.to_excel(writer, sheet_name='Bearish Sell Watchlist', index=False)
            else:
                pd.DataFrame([{"Alert": "No stocks met strict Inverted VCP limits today"}]).to_excel(writer, sheet_name='Bearish Sell Watchlist', index=False)

        print("-" * 70)
        print(f"[✓] Daily Analysis Complete!")
        print(f"[✓] Excel File Saved inside current directory: '{os.path.abspath(output_name)}'")
        print("=" * 70)

if __name__ == "__main__":
    scanner = NSEVCPDailyScanner()
    scanner.execute_eod_vcp_scan()