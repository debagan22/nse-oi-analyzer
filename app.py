import streamlit as st
import pandas as pd
from growwapi import GrowwAPI
from datetime import datetime, timedelta
import io

# 1. Page Setup
st.set_page_config(page_title="F&O Signal Machine", layout="wide", page_icon="🏹")

# 2. Connection Logic
@st.cache_resource
def get_groww_client():
    try:
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"❌ API Connection Failed: {e}")
        return None

# 3. Fetch Full F&O List (Cloud-Safe)
@st.cache_data
def get_full_fo_list():
    try:
        url = "https://groww.in/api/v1/fno/instruments/master/csv"
        df = pd.read_csv(url)
        # Filters only unique underlying stocks in the F&O segment
        fo_list = df[df['segment'] == 'FNO']['underlying_symbol'].unique().tolist()
        return [s for s in fo_list if str(s) != 'nan']
    except:
        return ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "SBIN", "INFY", "TCS", "ITC"]

# 4. Suggestion Logic (Price & OI Buildup)
def generate_trade_plan(symbol, ltp, p_chg, oi_chg):
    # Buffer for Entry: 0.15% for momentum confirmation
    # Target: 1.5% | Stop Loss: 0.8%
    if p_chg > 0.4 and oi_chg > 2.0:
        return {
            "Action": "BUY (Long Buildup)", 
            "Entry": round(ltp * 1.0015, 2), 
            "SL": round(ltp * 0.992, 2), 
            "Target": round(ltp * 1.015, 2),
            "Color": "#d4edda" # Green
        }
    elif p_chg < -0.4 and oi_chg > 2.0:
        return {
            "Action": "SELL (Short Buildup)", 
            "Entry": round(ltp * 0.9985, 2), 
            "SL": round(ltp * 1.008, 2), 
            "Target": round(ltp * 0.985, 2),
            "Color": "#f8d7da" # Red
        }
    elif p_chg > 0.4 and oi_chg < -2.0:
        return {
            "Action": "BUY (Short Covering)", 
            "Entry": ltp, "SL": round(ltp * 0.994, 2), "Target": round(ltp * 1.01, 2),
            "Color": "#d1ecf1" # Blue
        }
    return None

# --- UI Layout ---
st.title("🎯 Live F&O Signal Machine")
st.markdown("Automated scan for **Long/Short Buildups** with entry prices.")

groww = get_groww_client()

if groww:
    # Sidebar Filters
    st.sidebar.header("Scanner Settings")
    search = st.sidebar.text_input("🔍 Search Stock", "").upper()
    scan_limit = st.sidebar.slider("Scan Depth", 10, 150, 40)
    
    fo_master = get_full_fo_list()
    watchlist = [s for s in fo_master if search in s] if search else fo_master[:scan_limit]

    if st.button("🚀 Start Full Market Scan"):
        results = []
        bar = st.progress(0)
        status = st.empty()
        
        for i, sym in enumerate(watchlist):
            try:
                data = groww.get_quote(exchange="NSE", segment="FNO", trading_symbol=sym)
                ltp = data.get('last_price', 0)
                
                # Check if market is open
                if ltp > 0:
                    p_chg = data.get('day_change_perc', 0)
                    oi_chg = data.get('oi_day_change_percentage', 0)
                    plan = generate_trade_plan(sym, ltp, p_chg, oi_chg)
                    
                    if plan:
                        results.append({
                            "Symbol": sym, "LTP": ltp, "Action": plan['Action'],
                            "Entry Above/Below": plan['Entry'], "Stop Loss": plan['SL'],
                            "Target": plan['Target'], "Color": plan['Color']
                        })
                else:
                    status.info("🌙 Market is Closed. Please check back during NSE hours (9:15 - 3:30).")
                    break
            except: continue
            bar.progress((i + 1) / len(watchlist))

        # --- Show Results ---
        if results:
            df = pd.DataFrame(results)
            st.subheader("📊 Found Trading Opportunities")
            
            # Highlight Rows based on Action
            st.table(df.style.apply(lambda x: [f'background-color: {x.Color}'] * len(x), axis=1))
            
            # Export
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Trade Sheet", csv, "trades.csv", "text/csv")
        else:
            st.warning("No high-conviction signals found. Try increasing Scan Depth.")

else:
    st.info("Please set up your Groww API Keys in Streamlit Settings.")
