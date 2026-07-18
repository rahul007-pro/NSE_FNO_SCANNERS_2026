
import os
import pandas as pd
import requests
from datetime import datetime


class NSEProfessionalBreakoutScanner:

    def __init__(self):

        self.watchlist = [
            "DRREDDY", "CIPLA", "TORNTPHARM", "NATIONALUM", "MAXHEALTH",
            "PERSISTENT", "ASTRAL", "SUPREMEIND", "WAAREE", "KPITTECH",
            "LUPIN", "MANKIND", "GLENMARK", "MARICO", "NAM-INDIA",
            "PIIND", "UNOMINDA", "SBICARD", "TATACONSUM", "RELIANCE",
            "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN",
            "BHARTIARTL", "ITC", "TRENT", "M&M",
            "MARUTI", "INDIGO", "HINDALCO"
        ]

        self.headers = {
            "User-Agent": "Mozilla/5.0"
        }

    def fetch_market_history(self, ticker):

        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{ticker}.NS?interval=1d&range=120d"
        )

        try:

            response = requests.get(
                url,
                headers=self.headers,
                timeout=10
            )

            if response.status_code != 200:
                return None

            data = response.json()

            if not data.get("chart", {}).get("result"):
                return None

            result = data["chart"]["result"][0]
            quote = result["indicators"]["quote"][0]

            df = pd.DataFrame({
                "Date": [
                    datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                    for ts in result["timestamp"]
                ],
                "Open": quote["open"],
                "High": quote["high"],
                "Low": quote["low"],
                "Close": quote["close"],
                "Volume": quote["volume"]
            })

            df.dropna(inplace=True)

            return df

        except Exception:
            return None

    def execute_scan(self):

        print("=" * 80)
        print("NSE PROFESSIONAL BREAKOUT SCANNER WITH ATR FILTER")
        print("=" * 80)

        user_input = input(
            "Enter target date (YYYY-MM-DD) or press ENTER for latest: "
        ).strip()

        target_date = None

        if user_input:

            try:
                datetime.strptime(user_input, "%Y-%m-%d")
                target_date = user_input
                print(f"\nBacktesting Date Selected: {target_date}")

            except ValueError:
                print("Invalid date format.")
                return

        all_data = []

        print("\nDownloading market data...")

        for ticker in self.watchlist:

            df = self.fetch_market_history(ticker)

            if df is None:
                continue

            if target_date:
                df = df[df["Date"] <= target_date]

            if len(df) < 30:
                continue

            all_data.append((ticker, df))

        if not all_data:
            print("No valid market data found.")
            return

        study_date = all_data[0][1]["Date"].iloc[-1]

        bullish_candidates = []
        bearish_candidates = []

        for ticker, df in all_data:

            try:

                current_close = df["Close"].iloc[-1]
                current_high = df["High"].iloc[-1]
                current_low = df["Low"].iloc[-1]
                current_volume = df["Volume"].iloc[-1]

                previous_close = df["Close"].iloc[-2]

                pct_change = (
                    (current_close - previous_close)
                    / previous_close
                ) * 100

                # EMA20
                ema20 = (
                    df["Close"]
                    .ewm(span=20, adjust=False)
                    .mean()
                    .iloc[-1]
                )

                # Previous completed 5 sessions
                prev5_high = df["High"].iloc[-6:-1].max()
                prev5_low = df["Low"].iloc[-6:-1].min()

                # Previous completed 10 sessions volume
                avg10_volume = (
                    df["Volume"]
                    .iloc[-11:-1]
                    .mean()
                )

                if avg10_volume <= 0:
                    continue

                volume_ratio = (
                    current_volume / avg10_volume
                )

                # =====================================================
                # ATR 14
                # =====================================================

                df["Prev_Close"] = df["Close"].shift(1)

                tr1 = df["High"] - df["Low"]

                tr2 = (
                    df["High"] - df["Prev_Close"]
                ).abs()

                tr3 = (
                    df["Low"] - df["Prev_Close"]
                ).abs()

                df["TR"] = pd.concat(
                    [tr1, tr2, tr3],
                    axis=1
                ).max(axis=1)

                atr14 = (
                    df["TR"]
                    .rolling(14)
                    .mean()
                    .iloc[-1]
                )

                if pd.isna(atr14):
                    continue

                # =====================================================
                # BULLISH BREAKOUT
                # =====================================================

                bullish_breakout = (

                    current_high >
                    (prev5_high * 1.005)

                    and

                    current_close >
                    prev5_high

                    and

                    current_close >
                    ema20

                    and

                    current_volume >
                    (avg10_volume * 1.5)

                    and

                    pct_change > 1

                    and

                    (current_high - prev5_high) >
                    (0.25 * atr14)

                )

                if bullish_breakout:

                    breakout_strength = (
                        (
                            current_high -
                            prev5_high
                        )
                        / prev5_high
                    ) * 100

                    bullish_candidates.append({

                        "Ticker": ticker,
                        "Close": round(current_close, 2),
                        "5D High": round(prev5_high, 2),
                        "EMA20": round(ema20, 2),
                        "ATR14": round(atr14, 2),
                        "% Change": round(pct_change, 2),
                        "Breakout %": round(breakout_strength, 2),
                        "Volume Ratio": round(volume_ratio, 2)

                    })

                # =====================================================
                # BEARISH BREAKDOWN
                # =====================================================

                bearish_breakdown = (

                    current_low <
                    (prev5_low * 0.995)

                    and

                    current_close <
                    prev5_low

                    and

                    current_close <
                    ema20

                    and

                    current_volume >
                    (avg10_volume * 1.5)

                    and

                    pct_change < -1

                    and

                    (prev5_low - current_low) >
                    (0.25 * atr14)

                )

                if bearish_breakdown:

                    breakdown_strength = (
                        (
                            prev5_low -
                            current_low
                        )
                        / prev5_low
                    ) * 100

                    bearish_candidates.append({

                        "Ticker": ticker,
                        "Close": round(current_close, 2),
                        "5D Low": round(prev5_low, 2),
                        "EMA20": round(ema20, 2),
                        "ATR14": round(atr14, 2),
                        "% Change": round(pct_change, 2),
                        "Breakdown %": round(breakdown_strength, 2),
                        "Volume Ratio": round(volume_ratio, 2)

                    })

            except Exception:
                continue

        bullish_df = pd.DataFrame(bullish_candidates)
        bearish_df = pd.DataFrame(bearish_candidates)

        if not bullish_df.empty:
            bullish_df = bullish_df.sort_values(
                by=["Volume Ratio", "Breakout %"],
                ascending=[False, False]
            )

        if not bearish_df.empty:
            bearish_df = bearish_df.sort_values(
                by=["Volume Ratio", "Breakdown %"],
                ascending=[False, False]
            )

        output_file = (
            f"NSE_Professional_Breakout_{study_date}.xlsx"
        )

        with pd.ExcelWriter(
            output_file,
            engine="openpyxl"
        ) as writer:

            bullish_df.to_excel(
                writer,
                sheet_name="Bullish_Breakouts",
                index=False
            )

            bearish_df.to_excel(
                writer,
                sheet_name="Bearish_Breakdowns",
                index=False
            )

        print("\n" + "=" * 80)
        print(f"Study Date : {study_date}")
        print(f"Bullish Breakouts : {len(bullish_df)}")
        print(f"Bearish Breakdowns : {len(bearish_df)}")
        print(f"Excel Report : {os.path.abspath(output_file)}")
        print("=" * 80)

        if not bullish_df.empty:
            print("\nTOP BULLISH BREAKOUTS")
            print(bullish_df.head(10).to_string(index=False))

        if not bearish_df.empty:
            print("\nTOP BEARISH BREAKDOWNS")
            print(bearish_df.head(10).to_string(index=False))


if __name__ == "__main__":
    scanner = NSEProfessionalBreakoutScanner()
    scanner.execute_scan()
