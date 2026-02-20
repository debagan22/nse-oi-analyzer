import streamlit as st
import pandas as pd
from growwapi import GrowwAPI

st.set_page_config(page_title="F&O Terminal Fix", layout="wide")

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

st.title("🏹 Ultimate Symbol Debugger")
groww = get_groww_client()

if groww:
    # 1. SIDEBAR SEARCH - Use this if the main scan fails
    st.sidebar.header("🔍 Manual Symbol Test")
    manual_sym = st.sidebar.text_input("Enter exact symbol from Groww App", "RELIANCE24FEB2800CE")
    if st.sidebar.button("Test Manual Symbol"):
        try:
            res = groww.get_quote(trading_symbol=manual_sym.upper(), exchange="NSE", segment="FNO")
            st.sidebar.write(res)
        except Exception as e:
            st.sidebar.error(f"Error: {e}")

    # 2. MAIN SCANNER
    stock_map = {"RELIANCE": 20, "SBIN": 5, "HDFCBANK": 10}
    
    if st.button("🚀 RUN TRIPLE-FORMAT SCAN"):
        results = []
        for sym, step in stock_map.items():
            try:
                # Get Spot
                spot = groww.get_quote(trading_symbol=sym, exchange="NSE", segment="CASH")
                ltp = spot.get('last_price', 0)
                if ltp > 0:
                    atm = get_atm(ltp, step)
                    
                    # TRYING 3 DIFFERENT GROWW FORMATS FOR 2026
                    # A: Standard (RELIANCE24FEB2800CE)
                    # B: Year-Month-Day (RELIANCE262242800CE)
                    # C: Short Month (RELIANCE24FEB262800CE)
                    formats = [
                        f"{sym}24FEB{atm}CE",
                        f"{sym}26224{atm}CE",
                        f"{sym}24FEB26{atm}CE"
                    ]
                    
                    found_data = False
                    for fmt in formats:
                        opt_data = groww.get_quote(trading_symbol=fmt, exchange="NSE", segment="FNO")
                        if opt_data.get('last_price', 0) > 0:
                            results.append({
                                "Stock": sym,
                                "Used Format": fmt,
                                "LTP": opt_data['last_price'],
                                "Target": round(opt_data['last_price'] * 1.3, 1),
                                "StopLoss": round(opt_data['last_price'] * 0.8, 1)
                            })
                            found_data = True
                            break
                    
                    if not found_data:
                        st.write(f"❌ All formats failed for {sym}. Tested: {formats}")
            except Exception as e:
                continue

        if results:
            st.table(pd.DataFrame(results))
