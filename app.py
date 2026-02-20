import streamlit as st
import pandas as pd
from growwapi import GrowwAPI

st.set_page_config(page_title="F&O Data Pro", layout="wide")

@st.cache_resource
def get_groww_client():
    try:
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"Authentication Failed: {e}")
        return None

def get_suggestion(ltp, p_chg, oi_chg):
    # Bullish: Price Up + OI Up
    if p_chg > 0.2 and oi_chg > 1.0:
        return {"View": "BULLISH 📈", "Entry": f"Above {round(ltp*1.001, 1)}", "Tgt": round(ltp*1.015, 1), "SL": round(ltp*0.992, 1), "Color": "#d4edda"}
    # Bearish: Price Down + OI Up
    elif p_chg < -0.2 and oi_chg > 1.0:
        return {"View": "BEARISH 📉", "Entry": f"Below {round(ltp*0.999, 1)}", "Tgt": round(ltp*0.985, 1), "SL": round(ltp*1.008, 1), "Color": "#f8d7da"}
    return {"View": "NEUTRAL 😴", "Entry": "Wait", "Tgt": "-", "SL": "-", "Color": "#ffffff"}

st.title("🏹 High-Speed F&O Scanner")
groww = get_groww_client()

if groww:
    if st.button("🔍 START LIVE SCAN"):
        # List of underlyings (Indices and Stocks)
        stocks = ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "SBIN", "ICICIBANK", "INFY", "TCS"]
        results = []
        progress = st.progress(0)
        
        for i, sym in enumerate(stocks):
            try:
                # FIX: Use segment="CASH" for indices and stock names
                # Groww requires segment="CASH" for NIFTY, BANKNIFTY, and stock names
                data = groww.get_quote(trading_symbol=sym, exchange="NSE", segment="CASH")
                
                ltp = data.get('last_price', 0)
                p_chg = data.get('day_change_perc', 0)
                # OI is only available in specific F&O contract calls. 
                # For basic scanning, we focus on Price and Volume momentum.
                oi_chg = data.get('oi_day_change_percentage', 0) 

                if ltp > 0:
                    sug = get_suggestion(ltp, p_chg, oi_chg)
                    results.append({
                        "STOCK": sym, 
                        "LTP": ltp, 
                        "PRICE %": f"{p_chg:.2f}%",
                        "SIGNAL": sug['View'],
                        "ENTRY": sug['Entry'], 
                        "TARGET": sug['Tgt'], 
                        "STOP-LOSS": sug['SL'], 
                        "Color": sug['Color']
                    })
            except Exception as e:
                st.sidebar.error(f"Error on {sym}: {e}")
                continue
            progress.progress((i + 1) / len(stocks))

        if results:
            df = pd.DataFrame(results)
            st.table(df.style.apply(lambda x: [f'background-color: {x.Color}'] * len(x), axis=1))
        else:
            st.error("No data returned. Ensure your segment permissions are active on Groww.")

st.divider()
st.info("💡 Note: For 'NIFTY' and 'BANKNIFTY', we use the CASH segment to get the underlying Index price.")
