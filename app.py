import streamlit as st
import pandas as pd
from growwapi import GrowwAPI
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="Pro F&O Advisor", layout="wide")

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

@st.cache_data
def fetch_fo_list_safe():
    try:
        url = "https://groww.in/api/v1/fno/instruments/master/csv"
        df = pd.read_csv(url)
        fo_stocks = df[df['segment'] == 'FNO']['underlying_symbol'].unique().tolist()
        return [s for s in fo_stocks if str(s) != 'nan']
    except:
        return ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "SBIN", "INFY", "TCS"]

# --- Logic: Trade Math ---
def calculate_trade_params(symbol, ltp, price_chg, oi_chg):
    # Determine Signal
    if price_chg > 0 and oi_chg > 0:
        sig, col, sl_pct, tgt_pct = "BUY (Long Buildup)", "#d4edda", 0.99, 1.02
    elif price_chg < 0 and oi_chg > 0:
        sig, col, sl_pct, tgt_pct = "SELL (Short Buildup)", "#f8d7da", 1.01, 0.98
    elif price_chg > 0 and oi_chg < 0:
        sig, col, sl_pct, tgt_pct = "BUY (Short Covering)", "#d1ecf1", 0.992, 1.015
    elif price_chg < 0 and oi_chg < 0:
        sig, col, sl_pct, tgt_pct = "SELL (Long Unwinding)", "#fff3cd", 1.008, 0.985
    else:
        return None

    return {
        "Symbol": symbol,
        "LTP": round(ltp, 2),
        "Signal": sig,
        "Stop Loss": round(ltp * sl_pct, 2),
        "Target": round(ltp * tgt_pct, 2),
        "Color": col
    }

st.title("🏹 Pro F&O Trade Advisor")

groww = get_groww_client()

if groww:
    # --- Sidebar Search & Filters ---
    st.sidebar.header("Filter Options")
    search_query = st.sidebar.text_input("🔍 Search Stock (e.g. RELIANCE)", "").upper()
    scan_limit = st.sidebar.slider("Number of stocks to scan", 10, 100, 30)
    
    fo_watchlist = fetch_fo_list_safe()
    # Filter watchlist based on search
    if search_query:
        fo_watchlist = [s for s in fo_watchlist if search_query in s]
    
    if st.button("🚀 Generate Trade Signals"):
        results = []
        progress = st.progress(0)
        
        for i, symbol in enumerate(fo_watchlist[:scan_limit]):
            try:
                data = groww.get_quote(exchange="NSE", segment="FNO", trading_symbol=symbol)
                ltp = data.get('last_price', 0)
                
                # EOD Fallback if market closed
                if ltp == 0:
                    hist = groww.get_historical_candle_data(symbol, "NSE", "1D", 
                           (datetime.now()-timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"), 
                           datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    candles = hist.get('candles', [])
                    if len(candles) >= 2:
                        ltp = candles[-1][4]
                        price_chg = ((candles[-1][4] - candles[-2][4]) / candles[-2][4]) * 100
                        oi_chg = 1.0 # Static placeholder for EOD OI
                    else: continue
                else:
                    price_chg = data.get('day_change_perc', 0)
                    oi_chg = data.get('oi_day_change_percentage', 0)

                trade = calculate_trade_params(symbol, ltp, price_chg, oi_chg)
                if trade: results.append(trade)
            except: continue
            progress.progress((i + 1) / len(fo_watchlist[:scan_limit]))

        if results:
            df = pd.DataFrame(results)
            
            # --- Display Results ---
            st.subheader("🎯 Daily Trade Plan")
            st.dataframe(df.style.apply(lambda x: [f'background-color: {x.Color}'] * len(x), axis=1).hide(axis='index'), use_container_width=True)
            
            # --- Download Button ---
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Trade Report (CSV)",
                data=csv,
                file_name=f"FO_Signals_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv',
            )
        else:
            st.warning("No actionable signals found for the selected stocks.")

else:
    st.info("Awaiting API Connection...")
