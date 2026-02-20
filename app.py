import streamlit as st
import pandas as pd
from growwapi import GrowwAPI

st.set_page_config(page_title="F&O Pro Scanner", layout="wide")

@st.cache_resource
def get_groww_client():
    try:
        if "GROWW_API_KEY" not in st.secrets:
            st.error("Missing GROWW_API_KEY in Secrets.")
            return None
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"Auth Failed: {e}")
        return None

def get_atm(price, step):
    return int(round(price / step) * step)

st.title("🏹 F&O Smart Entry Advisor")
groww = get_groww_client()

if groww:
    # Top Stock Underlyings
    stock_map = {"RELIANCE": 20, "SBIN": 5, "HDFCBANK": 10, "ICICIBANK": 10, "TCS": 20}
    
    # 2026 Date Formatting
    EXP_STR = "26FEB"  # 26 Feb Expiry
    YR = "26"

    if st.button("🚀 RUN SMART SCAN"):
        results = []
        status_log = []
        
        for sym, step in stock_map.items():
            try:
                # 1. Fetch Cash Price
                spot_data = groww.get_quote(trading_symbol=sym, exchange="NSE", segment="CASH")
                ltp = spot_data.get('last_price', 0)
                day_chg = spot_data.get('day_change_perc', 0)

                if ltp > 0:
                    atm = get_atm(ltp, step)
                    opt_type = "CE" if day_chg >= 0 else "PE"
                    
                    # Try Format A: RELIANCE26FEB2800CE
                    opt_sym_a = f"{sym}{YR}{EXP_STR}{atm}{opt_type}"
                    # Try Format B: RELIANCE26FEB262800CE (Some brokers repeat the year)
                    opt_sym_b = f"{sym}{EXP_STR}{YR}{atm}{opt_type}"

                    # Attempting to fetch premium
                    opt_data = groww.get_quote(trading_symbol=opt_sym_a, exchange="NSE", segment="FNO")
                    opt_ltp = opt_data.get('last_price', 0)
                    
                    # Fallback to Format B if A returns 0
                    if not opt_ltp:
                        opt_data = groww.get_quote(trading_symbol=opt_sym_b, exchange="NSE", segment="FNO")
                        opt_ltp = opt_data.get('last_price', 0)
                        final_sym = opt_sym_b
                    else:
                        final_sym = opt_sym_a

                    results.append({
                        "Stock": sym,
                        "Spot": ltp,
                        "Contract": final_sym,
                        "Premium": opt_ltp if opt_ltp else "Pending",
                        "Signal": "BUY CALL 🟢" if day_chg >= 0 else "BUY PUT 🔴",
                        "Entry Rate": f"Above {round(opt_ltp * 1.05, 1)}" if opt_ltp else "Wait for Breakout"
                    })
                else:
                    status_log.append(f"Could not find Spot Price for {sym}")

            except Exception as e:
                status_log.append(f"Error on {sym}: {str(e)}")

        if results:
            st.table(pd.DataFrame(results))
        if status_log:
            with st.expander("🔍 View Connection Logs"):
                for log in status_log:
                    st.write(log)
else:
    st.info("Awaiting API configuration in Streamlit Secrets.")
