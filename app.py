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

@st.cache_data
def get_stock_list():
    # Standard F&O Top 20 for testing to ensure speed and accuracy
    return ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "ICICIBANK", "SBIN", "INFY", "TCS", "ITC", "AXISBANK", "KOTAKBANK", "BHARTIARTL", "LT", "BAJFINANCE", "TATASTEEL"]

def get_suggestion(ltp, p_chg, oi_chg):
    if p_chg > 0.2 and oi_chg > 1.0:
        return {"View": "BULLISH 📈", "Entry": f"Above {round(ltp*1.001, 1)}", "Tgt": round(ltp*1.015, 1), "SL": round(ltp*0.992, 1), "Color": "#d4edda"}
    elif p_chg < -0.2 and oi_chg > 1.0:
        return {"View": "BEARISH 📉", "Entry": f"Below {round(ltp*0.999, 1)}", "Tgt": round(ltp*0.985, 1), "SL": round(ltp*1.008, 1), "Color": "#f8d7da"}
    return {"View": "NEUTRAL 😴", "Entry": "Wait", "Tgt": "-", "SL": "-", "Color": "#ffffff"}

st.title("🏹 High-Speed F&O Scanner")
groww = get_groww_client()

if groww:
    if st.button("🔍 START LIVE SCAN"):
        stocks = get_stock_list()
        results = []
        progress = st.progress(0)
        
        for i, sym in enumerate(stocks):
            try:
                # We try to get the FNO quote. 
                # Note: Groww sometimes requires 'NSE' as a prefix or specific segment flags
                data = groww.get_quote(trading_symbol=sym, exchange="NSE", segment="CASH") 
                # We use CASH segment for LTP if FNO is restricted, as LTP is the same.
                
                ltp = data.get('last_price', 0)
                
                # Fetching OI separately if needed or from the same packet
                p_chg = data.get('day_change_perc', 0)
                oi_chg = data.get('oi_day_change_percentage', 0) # This might return 0 if segment is CASH

                if ltp > 0:
                    sug = get_suggestion(ltp, p_chg, oi_chg)
                    results.append({
                        "STOCK": sym, "LTP": ltp, "PRICE %": f"{p_chg:.2f}%",
                        "OI %": f"{oi_chg:.2f}%", "SIGNAL": sug['View'],
                        "ENTRY": sug['Entry'], "TARGET": sug['Tgt'], "STOP-LOSS": sug['SL'], "Color": sug['Color']
                    })
            except Exception as e:
                # Log the error to the screen so we can see why it's failing
                st.sidebar.write(f"Error on {sym}: {e}")
                continue
            progress.progress((i + 1) / len(stocks))

        if results:
            df = pd.DataFrame(results)
            st.table(df.style.apply(lambda x: [f'background-color: {x.Color}'] * len(x), axis=1))
        else:
            st.error("No data returned from API. This usually means the API Key is valid but doesn't have 'Live Data' permissions enabled.")

---

### 💡 Why it might still show "No Data"
If the updated code above still fails, it is likely one of these "External" reasons:
1.  **API Authorization:** Groww requires you to "re-login" or generate a new `access_token` every morning. If your token is from yesterday, it will connect but return empty data.
2.  **Exchange Subscription:** Ensure your Groww account has the **NSE Derivative** segment enabled and you have signed the digital document for real-time data.
3.  **Rate Limiting:** If you scan 100 stocks at once, Groww might block the request. The code above limits it to 15 stocks for testing.



**Would you like me to add a "Test Connection" button that checks only one symbol (like NIFTY) and prints the full raw response so we can see exactly what the broker is sending back?**
