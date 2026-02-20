import streamlit as st
import pandas as pd
from growwapi import GrowwAPI
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="24/7 F&O Advisor", layout="wide")

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

# --- Helper: Get Build-up Signal ---
def get_signal(price_chg, oi_chg):
    if price_chg > 0 and oi_chg > 0: return "BUY (Long Buildup)", "#d4edda"
    if price_chg < 0 and oi_chg > 0: return "SELL (Short Buildup)", "#f8d7da"
    if price_chg > 0 and oi_chg < 0: return "BUY (Short Covering)", "#d1ecf1"
    if price_chg < 0 and oi_chg < 0: return "SELL (Long Unwinding)", "#fff3cd"
    return "Neutral", "#ffffff"

st.title("🏹 Universal F&O Buy/Sell Advisor")

if groww:
    # 1. Load F&O List Automatically
    @st.cache_data(ttl=3600)
    def fetch_fo_list():
        all_instruments = groww.get_all_instruments()
        # Filter for FNO segment and unique underlying symbols
        fo_df = all_instruments[all_instruments['segment'] == 'FNO']
        return fo_df['underlying_symbol'].unique().tolist()

    fo_watchlist = fetch_fo_list()[:30] # Scanning top 30 for speed
    
    status_placeholder = st.empty()
    if st.button("🚀 Analyze Market"):
        results = []
        progress = st.progress(0)
        
        for i, symbol in enumerate(fo_watchlist):
            try:
                # Attempt Live Data
                data = groww.get_quote(exchange="NSE", segment="FNO", trading_symbol=symbol)
                ltp = data.get('last_price', 0)
                
                # Check if market is closed (LTP is 0 or price change is null)
                if ltp == 0:
                    status_placeholder.info("🌙 Market Closed: Computing EOD Analysis...")
                    # Fetch last 2 days of daily candles to calculate change
                    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    start_time = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
                    
                    hist = groww.get_historical_candle_data(
                        trading_symbol=symbol,
                        exchange="NSE",
                        interval="1D",
                        start_time=start_time,
                        end_time=end_time
                    )
                    candles = hist.get('candles', [])
                    if len(candles) >= 2:
                        last_close = candles[-1][4]  # Close price of latest candle
                        prev_close = candles[-2][4]  # Close price of previous candle
                        ltp = last_close
                        price_chg = ((last_close - prev_close) / prev_close) * 100
                        # Note: EOD OI change usually requires specialized OI history API
                        oi_chg = 0 # Placeholder if EOD OI is restricted
                    else: continue
                else:
                    status_placeholder.success("☀️ Market Open: Real-Time Analysis...")
                    price_chg = data.get('day_change_perc', 0)
                    oi_chg = data.get('oi_day_change_percentage', 0)

                signal, color = get_signal(price_chg, oi_chg)
                results.append({
                    "Symbol": symbol,
                    "LTP": ltp,
                    "Price %": f"{price_chg:.2f}%",
                    "OI %": f"{oi_chg:.2f}%",
                    "Signal": signal,
                    "Entry Rate": f"At {ltp}",
                    "Color": color
                })
            except: continue
            progress.progress((i + 1) / len(fo_watchlist))

        df = pd.DataFrame(results)
        st.dataframe(df.style.apply(lambda x: [f'background-color: {x.Color}'] * len(x), axis=1).hide(axis='index'), use_container_width=True)
else:
    st.warning("Missing API Keys in Secrets.")
