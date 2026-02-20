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

st.title("🏹 F&O Pro: Entry & Exit Scanner")

# Standard Monthly Expiry
EXPIRY = "26FEB"

groww = get_groww_client()

if groww:
    stock_map = {
        "RELIANCE": 20, "SBIN": 5, "HDFCBANK": 10, 
        "ICICIBANK": 10, "INFY": 20, "TCS": 20, "ITC": 5
    }

    if st.button("🚀 SCAN LIVE TRADES"):
        results = []
        progress = st.progress(0)
        
        for i, (sym, step) in enumerate(stock_map.items()):
            try:
                # 1. Get Spot Data
                spot_data = groww.get_quote(trading_symbol=sym, exchange="NSE", segment="CASH")
                ltp = spot_data.get('last_price', 0)
                p_chg = spot_data.get('day_change_perc', 0)
                
                if ltp > 0:
                    atm = get_atm(ltp, step)
                    opt_type = "CE" if p_chg >= 0 else "PE"
                    opt_sym = f"{sym}{EXPIRY}{atm}{opt_type}"
                    
                    # 2. Get Option Data
                    opt_data = groww.get_quote(trading_symbol=opt_sym, exchange="NSE", segment="FNO")
                    opt_ltp = opt_data.get('last_price', 0)

                    if opt_ltp > 0:
                        # CALCULATION LOGIC
                        entry_price = round(opt_ltp * 1.05, 1) # Buy above this
                        target_price = round(opt_ltp * 1.30, 1) # +30%
                        stop_loss = round(opt_ltp * 0.85, 1)   # -15%
                        
                        results.append({
                            "STOCK": sym,
                            "SPOT": ltp,
                            "OPTION": opt_sym,
                            "CURRENT PREM": opt_ltp,
                            "SIGNAL": "BUY CALL 🟢" if opt_type == "CE" else "BUY PUT 🔴",
                            "ENTRY ABOVE": entry_price,
                            "TARGET (EXIT)": target_price,
                            "STOP-LOSS": stop_loss,
                            "RISK:REWARD": "1:2"
                        })
            except:
                continue
            progress.progress((i + 1) / len(stock_map))

        if results:
            # Displaying as a styled table for clarity
            df = pd.DataFrame(results)
            st.table(df)
            st.success("Analysis Complete. Use 'Entry Above' as your trigger price.")
        else:
            st.warning("No data found. Ensure market is open (9:15 AM - 3:30 PM).")

st.divider()
st.info("💡 **Exit Strategy:** If the price hits the **Target**, exit immediately to lock in gains. If it drops to the **Stop-Loss**, exit to protect your capital from further decay.")
