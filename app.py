import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from growwapi import GrowwAPI

# --- Market Timing Helper ---
def is_market_open():
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    # Weekends
    if now.weekday() >= 5: return False
    # Market Hours (9:15 AM to 3:30 PM)
    start = now.replace(hour=9, minute=15, second=0)
    end = now.replace(hour=15, minute=30, second=0)
    return start <= now <= end

@st.cache_resource
def get_groww_client():
    try:
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        return None

def get_price(groww, sym, segment="CASH"):
    """Fetches Live price if open, else fetches the last EOD candle."""
    if is_market_open():
        data = groww.get_quote(trading_symbol=sym, exchange="NSE", segment=segment)
        return data.get('last_price', 0), "LIVE"
    else:
        # Fallback to last historical candle (EOD)
        try:
            # Note: Stock EOD usually uses 'NSE-SYMBOL' format in Groww
            hist = groww.get_historical_candles(
                exchange="NSE", 
                segment=segment, 
                groww_symbol=f"NSE-{sym}" if segment=="CASH" else sym,
                candle_interval="5" 
            )
            if hist:
                return hist[-1][4], "EOD" # Index 4 is usually 'Close'
        except: pass
    return 0, "OFFLINE"

# --- Main App ---
st.title("🎯 Hybrid F&O Scanner (Live/EOD)")
m_status = "🟢 OPEN" if is_market_open() else "🔴 CLOSED"
st.subheader(f"Market Status: {m_status}")

groww = get_groww_client()
EXPIRY = "24FEB" # NSE Monthly

if groww:
    stocks = {"RELIANCE": 20, "SBIN": 5, "HDFCBANK": 10}
    
    if st.button("🔍 SCAN NOW"):
        results = []
        for sym, step in stocks.items():
            # 1. Get Spot (Live or EOD)
            spot_price, source = get_price(groww, sym, "CASH")
            
            if spot_price > 0:
                atm = int(round(spot_price / step) * step)
                opt_sym = f"{sym} {EXPIRY} {atm} CE" # Using space format
                
                # 2. Get Option Price
                opt_price, _ = get_price(groww, opt_sym, "FNO")
                
                if opt_price > 0:
                    results.append({
                        "STOCK": sym,
                        "SPOT": spot_price,
                        "DATA TYPE": source,
                        "OPTION": opt_sym,
                        "PREMIUM": opt_price,
                        "ENTRY": round(opt_price * 1.05, 1),
                        "EXIT (TARGET)": round(opt_price * 1.30, 1),
                        "STOP-LOSS": round(opt_price * 0.85, 1)
                    })
        
        if results:
            st.table(pd.DataFrame(results))
        else:
            st.warning("Could not fetch data. Check API subscription or symbol format.")
