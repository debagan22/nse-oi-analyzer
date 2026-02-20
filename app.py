import streamlit as st
import pandas as pd
from growwapi import GrowwAPI

st.set_page_config(page_title="F&O Data Pro", layout="wide")

@st.cache_resource
def get_groww_client():
    try:
        # Check if secrets exist before trying to use them
        if "GROWW_API_KEY" not in st.secrets:
            st.error("Missing GROWW_API_KEY in Streamlit Secrets!")
            return None
            
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        # Note: If this fails, your access_token might be expired
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"Authentication Failed: {e}")
        return None

def get_suggestion(ltp, p_chg, oi_chg):
    # Buy if Price Up and OI Up
    if p_chg > 0.2 and oi_chg > 1.0:
        return {"View": "BULLISH 📈", "Entry": f"Above {round(ltp*1.001, 1)}", "Tgt": round(ltp*1.015, 1), "SL": round(ltp*0.992, 1), "Color": "#d4edda"}
    # Sell if Price Down and OI Up
    elif p_chg < -0.2 and oi_chg > 1.0:
        return {"View": "BEARISH 📉", "Entry": f"Below {round(ltp*0.999, 1)}", "Tgt": round(ltp*0.985, 1), "SL": round(ltp*1.008, 1), "Color": "#f8d7da"}
    return {"View": "NEUTRAL 😴", "Entry": "Wait", "Tgt": "-", "SL": "-", "Color": "#ffffff"}

st.title("🏹 Live F&O Signal Scanner")

groww = get_groww_client()

if groww:
    # A smaller test list to ensure we don't hit rate limits
    stocks = ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "SBIN", "ICICIBANK", "INFY", "TCS"]
    
    if st.button("🔍 START LIVE SCAN"):
        results = []
        progress = st.progress(0)
        
        for i, sym in enumerate(stocks):
            try:
                # Try getting quote from FNO segment
                data = groww.get_quote(trading_symbol=sym, exchange="NSE", segment="FNO")
                
                # DEBUG: Uncomment the line below to see raw data in your sidebar if it fails
                # st.sidebar.write(f"Raw data for {sym}:", data)

                ltp = data.get('last_price', 0)
                p_chg = data.get('day_change_perc', 0)
                oi_chg = data.get('oi_day_change_percentage', 0)

                if ltp > 0:
                    sug = get_suggestion(ltp, p_chg, oi_chg)
                    results.append({
                        "STOCK": sym, "LTP": ltp, "PRICE %": f"{p_chg:.2f}%",
                        "OI %": f"{oi_chg:.2f}%", "SIGNAL": sug['View'],
                        "ENTRY": sug['Entry'], "TARGET": sug['Tgt'], "STOP-LOSS": sug['SL'], "Color": sug['Color']
                    })
            except Exception as e:
                st.sidebar.warning(f"Error on {sym}: {e}")
                continue
            progress.progress((i + 1) / len(stocks))

        if results:
            df = pd.DataFrame(results)
            # Apply color coding to the table
            st.table(df.style.apply(lambda x: [f'background-color: {x.Color}'] * len(x), axis=1))
        else:
            st.error("No data returned. Check if your Groww API has 'Live F&O' permissions active.")

# The horizontal rule must be a string in st.markdown or use st.divider()
st.divider()
st.info("💡 Green = Long Buildup (Buy) | Red = Short Buildup (Sell) | White = No Volume/OI")
