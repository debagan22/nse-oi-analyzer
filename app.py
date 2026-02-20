import streamlit as st
import pandas as pd
from growwapi import GrowwAPI
import time

st.set_page_config(page_title="Live F&O Scanner", layout="wide")

@st.cache_resource
def get_groww_client():
    try:
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"Auth Error: {e}")
        return None

groww = get_groww_client()

# A list of high-liquidity F&O stocks. 
# You can expand this to all 180+ stocks once you verify speed.
FO_WATCHLIST = [
    "NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "ICICIBANK", "SBIN", 
    "INFY", "TCS", "TATASTEEL", "ADANIENT", "ITC", "BHARTIARTL"
]

st.title("🏹 Live F&O Buy/Sell Advisor")

if groww:
    if st.button("🚀 Start Live Market Scan"):
        results = []
        progress = st.progress(0)
        
        for i, stock in enumerate(FO_WATCHLIST):
            try:
                # Fetching snapshot with OI data
                snap = groww.get_quote(exchange="NSE", segment="FNO", trading_symbol=stock)
                
                ltp = snap.get('last_price', 0)
                price_chg = snap.get('day_change_perc', 0)
                oi_chg = snap.get('oi_day_change_percentage', 0)

                # --- AI STRATEGY LOGIC ---
                if price_chg > 0.5 and oi_chg > 2:
                    signal = "BUY (Long Buildup)"
                    rate = f"Above {round(ltp * 1.002, 2)}" # Entry slightly above LTP
                    color = "#d4edda" # Green
                elif price_chg < -0.5 and oi_chg > 2:
                    signal = "SELL (Short Buildup)"
                    rate = f"Below {round(ltp * 0.998, 2)}" # Entry slightly below LTP
                    color = "#f8d7da" # Red
                elif price_chg > 0.5 and oi_chg < -2:
                    signal = "BUY (Short Covering)"
                    rate = f"At Market ({ltp})"
                    color = "#d1ecf1" # Blue
                elif price_chg < -0.5 and oi_chg < -2:
                    signal = "SELL (Long Unwinding)"
                    rate = f"At Market ({ltp})"
                    color = "#fff3cd" # Yellow
                else:
                    signal = "WAIT (Neutral)"
                    rate = "N/A"
                    color = "#ffffff"

                results.append({
                    "Stock": stock,
                    "LTP": ltp,
                    "Price %": f"{price_chg:.2f}%",
                    "OI %": f"{oi_chg:.2f}%",
                    "Signal": signal,
                    "Entry Rate": rate,
                    "Color": color
                })
            except:
                continue
            progress.progress((i + 1) / len(FO_WATCHLIST))

        # --- DISPLAY AS STYLED TABLE ---
        df = pd.DataFrame(results)
        
        def apply_row_style(row):
            return [f'background-color: {row["Color"]}'] * len(row)

        st.subheader("📊 Live Trading Signals")
        if not df.empty:
            st.dataframe(df.style.apply(apply_row_style, axis=1).hide(axis='index'), use_container_width=True)
        else:
            st.warning("No data returned. Ensure the market is open or check API subscription.")

else:
    st.info("Please connect your Groww API via Secrets to start.")
