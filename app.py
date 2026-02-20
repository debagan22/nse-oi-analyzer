import streamlit as st
import pandas as pd
from growwapi import GrowwAPI

st.set_page_config(page_title="Groww F&O Advisor", layout="wide")

@st.cache_resource
def get_groww_client():
    try:
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"Auth Failed: {e}")
        return None

def get_atm(price, step):
    return int(round(price / step) * step)

st.title("🎯 Groww F&O Option Advisor")

groww = get_groww_client()

if groww:
    # Stock Map with Strike Steps
    stock_map = {
        "RELIANCE": 20, 
        "SBIN": 5, 
        "HDFCBANK": 10, 
        "ICICIBANK": 10, 
        "TCS": 20,
        "INFY": 20,
        "ITC": 5
    }
    
    # FORMAT: [Expiry Date] -> 26FEB
    # Note: Groww typically uses DDMMM format for monthly
    EXPIRY_LABEL = "26FEB" 

    if st.button("🔍 SCAN LIVE OPTIONS"):
        results = []
        
        for sym, step in stock_map.items():
            try:
                # 1. Get Spot Price
                spot_data = groww.get_quote(trading_symbol=sym, exchange="NSE", segment="CASH")
                ltp = spot_data.get('last_price', 0)
                day_chg = spot_data.get('day_change_perc', 0)

                if ltp > 0:
                    atm = get_atm(ltp, step)
                    opt_type = "CE" if day_chg >= 0 else "PE"
                    
                    # 2. Construct Symbol: [Underlying][Expiry][Strike][Type]
                    # Example: RELIANCE26FEB2800CE
                    opt_sym = f"{sym}{EXPIRY_LABEL}{atm}{opt_type}"
                    
                    # 3. Fetch Option Details
                    opt_data = groww.get_quote(trading_symbol=opt_sym, exchange="NSE", segment="FNO")
                    opt_ltp = opt_data.get('last_price', 0)
                    opt_oi = opt_data.get('oi_day_change_percentage', 0)

                    results.append({
                        "STOCK": sym,
                        "SPOT": ltp,
                        "SUGGESTION": opt_sym,
                        "PREMIUM": opt_ltp if opt_ltp else "Check Segment",
                        "OI CHG %": f"{opt_oi if opt_oi else 0:.2f}%",
                        "ACTION": "BUY CALL 🟢" if day_chg >= 0 else "BUY PUT 🔴",
                        "ENTRY": f"Above {round(opt_ltp * 1.05, 1)}" if opt_ltp else "-"
                    })
            except Exception as e:
                st.sidebar.error(f"{sym} Error: {str(e)}")

        if results:
            df = pd.DataFrame(results)
            st.table(df)
            st.success(f"Scanned {len(results)} stocks using {EXPIRY_LABEL} expiry.")
        else:
            st.warning("No data retrieved. Please verify if 26FEB is the correct string for your broker today.")

st.divider()
