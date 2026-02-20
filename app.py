import streamlit as st
import pandas as pd
from growwapi import GrowwAPI

st.set_page_config(page_title="F&O Stock Advisor", layout="wide")

@st.cache_resource
def get_groww_client():
    try:
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"API Connection Error: {e}")
        return None

def get_atm(price, step):
    return int(round(price / step) * step)

st.title("🏹 F&O Advisor (Space-Separated Format)")

# Your verified format: NIFTY 27FEB 22000 CE
# Based on your input, we'll use 24FEB (Tuesday Expiry) for stocks
EXPIRY = "24FEB" 

groww = get_groww_client()

if groww:
    stock_map = {
        "RELIANCE": 20, "SBIN": 5, "HDFCBANK": 10, 
        "ICICIBANK": 10, "INFY": 20, "TCS": 20, "ITC": 5
    }

    if st.button("🚀 SCAN LIVE STOCKS"):
        results = []
        
        for sym, step in stock_map.items():
            try:
                # 1. Get Spot Price
                spot_data = groww.get_quote(trading_symbol=sym, exchange="NSE", segment="CASH")
                ltp = spot_data.get('last_price', 0)
                p_chg = spot_data.get('day_change_perc', 0)
                
                if ltp > 0:
                    atm = get_atm(ltp, step)
                    opt_type = "CE" if p_chg >= 0 else "PE"
                    
                    # UPDATED FORMAT: [SYMBOL] [DATE] [STRIKE] [TYPE]
                    # Example: RELIANCE 24FEB 2800 CE
                    opt_sym_space = f"{sym} {EXPIRY} {atm} {opt_type}"
                    opt_sym_no_space = f"{sym}{EXPIRY}{atm}{opt_type}"
                    
                    # 2. Try Space Format first
                    opt_data = groww.get_quote(trading_symbol=opt_sym_space, exchange="NSE", segment="FNO")
                    opt_ltp = opt_data.get('last_price', 0)
                    
                    # Fallback to No-Space if 0
                    if not opt_ltp:
                        opt_data = groww.get_quote(trading_symbol=opt_sym_no_space, exchange="NSE", segment="FNO")
                        opt_ltp = opt_data.get('last_price', 0)
                        final_sym = opt_sym_no_space
                    else:
                        final_sym = opt_sym_space

                    if opt_ltp > 0:
                        results.append({
                            "STOCK": sym,
                            "SPOT": ltp,
                            "OPTION": final_sym,
                            "PREMIUM": opt_ltp,
                            "SIGNAL": "BUY CALL 🟢" if opt_type == "CE" else "BUY PUT 🔴",
                            "ENTRY ABOVE": round(opt_ltp * 1.05, 1),
                            "TARGET": round(opt_ltp * 1.30, 1),
                            "STOP-LOSS": round(opt_ltp * 0.85, 1)
                        })
            except: continue

        if results:
            st.table(pd.DataFrame(results))
        else:
            st.warning("No data found. Ensure your Groww segment for F&O is active.")

st.divider()
st.info(f"💡 Format used: **{stock_map.keys().__iter__().__next__()} {EXPIRY} [STRIKE] [TYPE]**")
