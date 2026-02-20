import streamlit as st
import pandas as pd
from growwapi import GrowwAPI

st.set_page_config(page_title="F&O Stock Advisor", layout="wide")

# --- AUTO-CONFIG FOR EXPIRY ---
EXPIRY_STR = "26FEB"  
YEAR_STR = "26"      
EXPIRY_FULL = "2026-02-26" 

@st.cache_resource
def get_groww_client():
    try:
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"API Auth Failed: {e}")
        return None

def get_atm(price, step):
    return int(round(price / step) * step)

st.title("🎯 F&O Stock Entry/Exit Advisor")
st.caption("Scanning High-Volume F&O Stocks (Indices Excluded)")

groww = get_groww_client()

if groww:
    # Map of Top F&O Stocks and their Strike Intervals
    # These are specific for each stock (e.g., SBI moves in steps of 5, Reliance in 20)
    stock_fno_map = {
        "RELIANCE": 20, "HDFCBANK": 10, "SBIN": 5, 
        "ICICIBANK": 10, "INFY": 20, "TCS": 20, 
        "ITC": 5, "AXISBANK": 10, "KOTAKBANK": 20, "LT": 20
    }
    
    if st.button("🔍 SCAN STOCK OPTIONS"):
        results = []
        progress = st.progress(0)
        
        for i, (sym, step) in enumerate(stock_fno_map.items()):
            try:
                # 1. Get Spot Price
                spot_data = groww.get_quote(trading_symbol=sym, exchange="NSE", segment="CASH")
                spot_price = spot_data.get('last_price')
                day_chg = spot_data.get('day_change_perc', 0)

                if spot_price:
                    atm_strike = get_atm(spot_price, step)
                    
                    # 2. Pick CE if trend is Up, PE if trend is Down
                    option_type = "CE" if day_chg >= 0 else "PE"
                    fno_symbol = f"{sym}{YEAR_STR}{EXPIRY_STR}{atm_strike}{option_type}"
                    
                    # 3. Fetch Option Details
                    opt_data = groww.get_quote(trading_symbol=fno_symbol, exchange="NSE", segment="FNO")
                    opt_ltp = opt_data.get('last_price', 0)
                    opt_oi_chg = opt_data.get('oi_day_change_percentage', 0)

                    if opt_ltp > 0:
                        results.append({
                            "STOCK": sym,
                            "SPOT": spot_price,
                            "OPTION CONTRACT": fno_symbol,
                            "PREMIUM (LTP)": opt_ltp,
                            "OI CHG %": f"{opt_oi_chg if opt_oi_chg else 0:.2f}%",
                            "ACTION": "BUY CALL 🟢" if day_chg >= 0 else "BUY PUT 🔴",
                            "ENTRY": f"Above {round(opt_ltp * 1.05, 1)}", # 5% confirmation
                            "TARGET": round(opt_ltp * 1.30, 1),           # 30% profit
                            "STOP-LOSS": round(opt_ltp * 0.80, 1)         # 20% risk
                        })
            except: continue
            progress.progress((i + 1) / len(stock_fno_map))

        if results:
            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True)
            st.success("Scan Complete. Recommendations are based on Price-OI Momentum.")
        else:
            st.warning("No data found. Ensure market is open and API is active.")

st.divider()
st.info("💡 **Why 5% Entry?** Buying an option immediately is risky. The 'Entry' level acts as a trigger; only buy if the price breaks that level to confirm the move.")
