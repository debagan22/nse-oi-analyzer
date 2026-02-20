import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from growwapi import GrowwAPI

@st.cache_resource
def get_groww_client():
    # Ensure your API key has the "Live Data" or "Historical Data" subscription active
    try:
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        return None

def get_eod_price(groww, sym, segment="CASH", is_option=False, strike=None, opt_type=None):
    """
    Constructs the specific 'Groww Symbol' required for historical data.
    Format: NSE-RELIANCE-24Feb26-2800-CE
    """
    try:
        # Construct Groww-specific historical symbol
        if is_option:
            # Note the case: Feb (Mixed case) is often used in Groww historical strings
            g_sym = f"NSE-{sym}-24Feb26-{strike}-{opt_type}"
        else:
            g_sym = f"NSE-{sym}"

        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        start_time = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

        candles = groww.get_historical_candles(
            exchange="NSE",
            segment=segment,
            groww_symbol=g_sym,
            start_time=start_time,
            end_time=end_time,
            candle_interval="day" # Use day candle for stable EOD data
        )
        if candles and len(candles) > 0:
            return candles[-1][4] # Closing price
    except:
        return 0
    return 0

st.title("🎯 F&O Recovery Scanner")
groww = get_groww_client()

if groww:
    stocks = {"RELIANCE": 20, "SBIN": 5, "HDFCBANK": 10}
    
    if st.button("🔍 FETCH LAST CLOSING DATA"):
        results = []
        for sym, step in stocks.items():
            # 1. Get Spot EOD
            spot = get_eod_price(groww, sym, segment="CASH")
            
            if spot > 0:
                strike = int(round(spot / step) * step)
                opt_type = "CE" # Defaulting for scan
                
                # 2. Get Option EOD
                opt_price = get_eod_price(groww, sym, "FNO", True, strike, opt_type)
                
                if opt_price > 0:
                    results.append({
                        "STOCK": sym,
                        "LAST SPOT": spot,
                        "CONTRACT": f"{sym} 24FEB {strike} {opt_type}",
                        "LAST PREMIUM": opt_price,
                        "PLAN ENTRY": round(opt_price * 1.05, 1)
                    })
        
        if results:
            st.table(pd.DataFrame(results))
        else:
            st.error("Still no data. Please verify: 1. You paid the ₹499 API subscription. 2. F&O is active in your Groww App.")
