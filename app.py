import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from growwapi import GrowwAPI

st.set_page_config(page_title="F&O Multi-Scanner", layout="wide")

def get_next_tuesday():
    """Calculates the upcoming Tuesday for Weekly Index Expiry."""
    today = datetime.now()
    days_ahead = (1 - today.weekday()) % 7 
    if days_ahead == 0 and today.hour > 15: # If today is Tuesday after market close
        days_ahead = 7
    next_tue = today + timedelta(days_ahead)
    return next_tue.strftime("%d%b").upper() # Format: 24FEB

@st.cache_resource
def get_groww_client():
    try:
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"API Connection Failed: {e}")
        return None

st.title("🚀 Weekly & Monthly F&O Scanner")

# Config
WEEKLY_EXP = get_next_tuesday() 
MONTHLY_EXP = "24FEB" # NSE shifted monthly to last Tuesday in 2026

groww = get_groww_client()

if groww:
    # Adding Indices back with their unique steps
    full_map = {
        "NIFTY": {"step": 50, "exp": WEEKLY_EXP},
        "BANKNIFTY": {"step": 100, "exp": WEEKLY_EXP},
        "RELIANCE": {"step": 20, "exp": MONTHLY_EXP},
        "SBIN": {"step": 5, "exp": MONTHLY_EXP},
        "HDFCBANK": {"step": 10, "exp": MONTHLY_EXP}
    }

    if st.button("🔍 SCAN ALL EXPIRIES"):
        results = []
        for sym, cfg in full_map.items():
            try:
                # 1. Get Spot
                segment = "CASH" if sym not in ["NIFTY", "BANKNIFTY"] else "INDEX"
                spot_data = groww.get_quote(trading_symbol=sym, exchange="NSE", segment=segment)
                ltp = spot_data.get('last_price', 0)
                
                if ltp > 0:
                    atm = int(round(ltp / cfg['step']) * cfg['step'])
                    opt_type = "CE" if spot_data.get('day_change_perc', 0) >= 0 else "PE"
                    
                    # 2. Build Symbol: [Name][Expiry][Strike][Type]
                    opt_sym = f"{sym}{cfg['exp']}{atm}{opt_type}"
                    
                    # 3. Get Premium
                    opt_data = groww.get_quote(trading_symbol=opt_sym, exchange="NSE", segment="FNO")
                    opt_ltp = opt_data.get('last_price', 0)

                    results.append({
                        "Symbol": sym,
                        "Type": "Weekly" if cfg['exp'] == WEEKLY_EXP else "Monthly",
                        "Expiry": cfg['exp'],
                        "Contract": opt_sym,
                        "Premium": opt_ltp if opt_ltp else "No Quote",
                        "Signal": "BULLISH 🟢" if opt_type == "CE" else "BEARISH 🔴"
                    })
            except: continue

        st.table(pd.DataFrame(results))
        st.caption(f"Note: Weekly Expiry detected as {WEEKLY_EXP}. Monthly as {MONTHLY_EXP}.")
