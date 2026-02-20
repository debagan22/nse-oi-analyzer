import streamlit as st
import pandas as pd
from growwapi import GrowwAPI

st.set_page_config(page_title="F&O Stock Advisor", layout="wide")

# --- AUTO-CONFIG FOR EXPIRY ---
EXP_STR = "26FEB"  
YR = "26"      

@st.cache_resource
def get_groww_client():
    try:
        if "GROWW_API_KEY" not in st.secrets:
            st.error("Missing GROWW_API_KEY in Secrets.")
            return None
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        # This function handles the daily token handshake
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"Auth Failed: {e}")
        return None

def get_atm(price, step):
    return int(round(price / step) * step)

st.title("🏹 F&O Option Suggestor")
groww = get_groww_client()

if groww:
    # Dictionary of stocks and their strike steps
    stock_map = {
        "RELIANCE": 20, "HDFCBANK": 10, "SBIN": 5, 
        "ICICIBANK": 10, "INFY": 20, "TCS": 20, "ITC": 5
    }
    
    if st.button("🚀 SCAN LIVE STOCKS"):
        results = []
        progress = st.progress(0)
        
        for i, (sym, step) in enumerate(stock_map.items()):
            try:
                # 1. Fetch Spot Price (CASH segment is usually always available)
                spot_data = groww.get_quote(trading_symbol=sym, exchange="NSE", segment="CASH")
                ltp = spot_data.get('last_price', 0)
                day_chg = spot_data.get('day_change_perc', 0)

                if ltp > 0:
                    atm = get_atm(ltp, step)
                    opt_type = "CE" if day_chg >= 0 else "PE"
                    # Constructing the exact symbol format for Groww
                    opt_sym = f"{sym}{YR}{EXP_STR}{atm}{opt_type}"
                    
                    # 2. Fetch Option Price (FNO segment)
                    opt_data = groww.get_quote(trading_symbol=opt_sym, exchange="NSE", segment="FNO")
                    opt_ltp = opt_data.get('last_price', 0)
                    
                    results.append({
                        "Stock": sym,
                        "Spot Price": ltp,
                        "Suggested Option": opt_sym,
                        "Premium": opt_ltp if opt_ltp else "No F&O Data",
                        "Action": "BUY CALL 🟢" if day_chg >= 0 else "BUY PUT 🔴",
                        "Entry": f"Above {round(opt_ltp * 1.05, 1)}" if opt_ltp else "N/A"
                    })
            except Exception as e:
                continue
            progress.progress((i + 1) / len(stock_map))

        if results:
            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True)
            st.info("💡 If 'Premium' shows 'No F&O Data', your API key lacks Derivative permissions.")
        else:
            st.warning("No data returned. Check API status.")

st.divider()
