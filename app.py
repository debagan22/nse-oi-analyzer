import streamlit as st
import pandas as pd
from growwapi import GrowwAPI

st.set_page_config(page_title="F&O Smart Advisor", layout="wide")

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

st.title("🎯 Pro Stock Options Advisor")
groww = get_groww_client()

if groww:
    # Top stocks
    stock_map = {"RELIANCE": 20, "SBIN": 5, "HDFCBANK": 10, "ICICIBANK": 10, "TCS": 20}
    
    # 2026 Date format: DDMMM (e.g., 26FEB)
    EXP_STR = "26FEB"  
    YR = "26"

    if st.button("🔍 START SCAN"):
        results = []
        errors = []
        
        for sym, step in stock_map.items():
            try:
                # 1. Fetch Spot Price - Trying without 'NSE:' prefix first
                # If this fails, try: trading_symbol=f"NSE:{sym}"
                spot_data = groww.get_quote(trading_symbol=sym, exchange="NSE", segment="CASH")
                ltp = spot_data.get('last_price', 0)
                day_chg = spot_data.get('day_change_perc', 0)

                if ltp > 0:
                    atm = get_atm(ltp, step)
                    opt_type = "CE" if day_chg >= 0 else "PE"
                    
                    # Constructing the exact symbol: e.g., RELIANCE26FEB2800CE
                    # We will try both with and without the NSE: prefix
                    opt_sym = f"{sym}{YR}{EXP_STR}{atm}{opt_type}"
                    
                    # 2. Fetch Option Quote
                    opt_data = groww.get_quote(trading_symbol=opt_sym, exchange="NSE", segment="FNO")
                    opt_ltp = opt_data.get('last_price', 0)

                    results.append({
                        "STOCK": sym,
                        "LTP": ltp,
                        "OPTION": opt_sym,
                        "PREMIUM": opt_ltp if opt_ltp else "No Data",
                        "ACTION": "BUY CALL 🟢" if day_chg >= 0 else "BUY PUT 🔴",
                        "ENTRY": f"Above {round(opt_ltp * 1.05, 1)}" if opt_ltp else "-"
                    })
                else:
                    errors.append(f"{sym}: Could not get LTP (Check if symbol exists)")

            except Exception as e:
                errors.append(f"{sym}: {str(e)}")

        if results:
            st.table(pd.DataFrame(results))
        
        if errors:
            with st.expander("🛠️ Technical Error Logs"):
                for err in errors:
                    st.write(err)

st.divider()
st.info("💡 **Fixing 'Bad Request':** Ensure your Streamlit Secrets are correct. If Spot Price loads but F&O fails, your API token may not have Derivative (F&O) access.")
