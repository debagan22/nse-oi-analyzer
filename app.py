import streamlit as st
import pandas as pd
from growwapi import GrowwAPI
from datetime import datetime, timedelta

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

# --- NEW: Fixed Instrument Loading ---
@st.cache_data
def fetch_fo_list_safe():
    try:
        # Groww provides a public URL for the instrument master
        # We read it directly into memory using Pandas, bypassing the local disk
        url = "https://groww.in/api/v1/fno/instruments/master/csv" # Official Master URL
        df = pd.read_csv(url)
        
        # Filter for the FNO segment
        fo_stocks = df[df['segment'] == 'FNO']['underlying_symbol'].unique().tolist()
        return [s for s in fo_stocks if str(s) != 'nan']
    except Exception as e:
        st.warning(f"Could not fetch live instrument list, using default watchlist. Error: {e}")
        return ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "SBIN", "INFY", "TCS"]

# --- Helper: Signal Logic ---
def get_signal(price_chg, oi_chg):
    if price_chg > 0 and oi_chg > 0: return "BUY (Long Buildup)", "#d4edda"
    if price_chg < 0 and oi_chg > 0: return "SELL (Short Buildup)", "#f8d7da"
    if price_chg > 0 and oi_chg < 0: return "BUY (Short Covering)", "#d1ecf1"
    if price_chg < 0 and oi_chg < 0: return "SELL (Long Unwinding)", "#fff3cd"
    return "Neutral", "#ffffff"

st.title("🏹 Universal F&O Buy/Sell Advisor")

groww = get_groww_client()

if groww:
    fo_watchlist = fetch_fo_list_safe()[:30] # Limit to 30 for speed
    
    if st.button("🚀 Analyze Market"):
        results = []
        progress = st.progress(0)
        status_box = st.empty()
        
        for i, symbol in enumerate(fo_watchlist):
            try:
                # Get Quote
                data = groww.get_quote(exchange="NSE", segment="FNO", trading_symbol=symbol)
                ltp = data.get('last_price', 0)
                
                # Market Hours Check
                if ltp == 0:
                    status_box.info("🌙 Market Closed: Fetching EOD Data...")
                    # Fallback logic for EOD
                    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    start_time = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")
                    hist = groww.get_historical_candle_data(symbol, "NSE", "1D", start_time, end_time)
                    candles = hist.get('candles', [])
                    if len(candles) >= 2:
                        ltp = candles[-1][4]
                        price_chg = ((candles[-1][4] - candles[-2][4]) / candles[-2][4]) * 100
                        oi_chg = 0 # EOD OI requires specialized endpoint
                    else: continue
                else:
                    status_box.success("☀️ Market Open: Real-Time Scan...")
                    price_chg = data.get('day_change_perc', 0)
                    oi_chg = data.get('oi_day_change_percentage', 0)

                signal, color = get_signal(price_chg, oi_chg)
                results.append({
                    "Symbol": symbol, "LTP": ltp, "Price %": f"{price_chg:.2f}%",
                    "OI %": f"{oi_chg:.2f}%", "Signal": signal, "Entry": f"At {ltp}", "Color": color
                })
            except: continue
            progress.progress((i + 1) / len(fo_watchlist))

        if results:
            df = pd.DataFrame(results)
            st.table(df.style.apply(lambda x: [f'background-color: {x.Color}'] * len(x), axis=1))
        else:
            st.error("Could not retrieve data. Check API subscription.")
