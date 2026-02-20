import streamlit as st
import pandas as pd
from growwapi import GrowwAPI
from datetime import datetime

st.set_page_config(page_title="Options Entry/Exit Pro", layout="wide")

# --- Configuration ---
EXPIRY_DATE = "2026-02-26"  # Format: YYYY-MM-DD
EXPIRY_SHORT = "26FEB"     # Format for symbol: DDMMM (e.g., 26FEB)
YEAR_SHORT = "26"          # Last two digits of year

@st.cache_resource
def get_groww_client():
    try:
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"Connect your API first! Error: {e}")
        return None

def get_atm_strike(price, step=50):
    return int(round(price / step) * step)

st.title("🎯 Options Entry/Exit Advisor")
groww = get_groww_client()

if groww:
    # We focus on the big movers
    underlyings = {"NIFTY": 50, "BANKNIFTY": 100}
    
    if st.button("🔍 SCAN OPTIONS NOW"):
        results = []
        for symbol, step in underlyings.items():
            try:
                # 1. Get Spot Price
                spot_data = groww.get_quote(trading_symbol=symbol, exchange="NSE", segment="CASH")
                spot_price = spot_data.get('last_price')
                p_chg = spot_data.get('day_change_perc', 0)
                
                if spot_price:
                    atm = get_atm_strike(spot_price, step)
                    
                    # 2. Construct CE and PE Symbols
                    # Format: NIFTY + 26 + FEB + 24500 + CE
                    ce_sym = f"{symbol}{YEAR_SHORT}{EXPIRY_SHORT}{atm}CE"
                    pe_sym = f"{symbol}{YEAR_SHORT}{EXPIRY_SHORT}{atm}PE"
                    
                    # 3. Fetch Option Data
                    ce_data = groww.get_quote(trading_symbol=ce_sym, exchange="NSE", segment="FNO")
                    pe_data = groww.get_quote(trading_symbol=pe_sym, exchange="NSE", segment="FNO")
                    
                    # 4. Suggestions based on Trend
                    if p_chg > 0: # Bullish Trend
                        results.append({
                            "CONTRACT": ce_sym, "LTP": ce_data.get('last_price'),
                            "ACTION": "BUY CALL 🟢", "ENTRY": f"Above {round(ce_data.get('last_price',0)*1.05, 1)}",
                            "TARGET": round(ce_data.get('last_price',0)*1.30, 1),
                            "STOPLOSS": round(ce_data.get('last_price',0)*0.80, 1)
                        })
                    else: # Bearish Trend
                        results.append({
                            "CONTRACT": pe_sym, "LTP": pe_data.get('last_price'),
                            "ACTION": "BUY PUT 🔴", "ENTRY": f"Above {round(pe_data.get('last_price',0)*1.05, 1)}",
                            "TARGET": round(pe_data.get('last_price',0)*1.30, 1),
                            "STOPLOSS": round(pe_data.get('last_price',0)*0.80, 1)
                        })
            except Exception as e:
                st.error(f"Error fetching {symbol}: {e}")

        if results:
            st.table(pd.DataFrame(results))
        else:
            st.warning("No data found. Ensure EXPIRY_DATE is correct in the code.")

st.divider()
st.info("💡 **Strategy:** This suggests buying the ATM option if the trend is strong. Entry is set 5% above current price to confirm momentum.")
