import streamlit as st
import pandas as pd
from growwapi import GrowwAPI
import io

st.set_page_config(page_title="Simplified F&O Advisor", layout="wide")

@st.cache_resource
def get_groww_client():
    try:
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"Connect your Groww API in Secrets first! Error: {e}")
        return None

@st.cache_data
def get_stock_list():
    try:
        url = "https://groww.in/api/v1/fno/instruments/master/csv"
        df = pd.read_csv(url)
        return df[df['segment'] == 'FNO']['underlying_symbol'].unique().tolist()
    except:
        return ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "SBIN", "INFY", "TCS", "ITC"]

# --- The Logic: Simple Entry/Exit Calculation ---
def get_suggestion(ltp, p_chg, oi_chg):
    # If Price & OI both UP -> BUY
    if p_chg > 0.1 and oi_chg > 0.5:
        return {
            "View": "BULLISH 📈",
            "Entry": f"Above {round(ltp + (ltp*0.001), 1)}", # 0.1% buffer
            "Target": round(ltp + (ltp*0.015), 1),        # 1.5% profit
            "StopLoss": round(ltp - (ltp*0.008), 1),      # 0.8% risk
            "Color": "#d4edda"
        }
    # If Price DOWN & OI UP -> SELL
    elif p_chg < -0.1 and oi_chg > 0.5:
        return {
            "View": "BEARISH 📉",
            "Entry": f"Below {round(ltp - (ltp*0.001), 1)}",
            "Target": round(ltp - (ltp*0.015), 1),
            "StopLoss": round(ltp + (ltp*0.008), 1),
            "Color": "#f8d7da"
        }
    return {"View": "NEUTRAL 😴", "Entry": "Wait", "Target": "-", "StopLoss": "-", "Color": "#ffffff"}

st.title("🏹 Simplified F&O Entry/Exit Advisor")
groww = get_groww_client()

if groww:
    stocks = get_stock_list()
    # Let user decide how many stocks to scan
    scan_count = st.slider("Select how many stocks to scan:", 5, 100, 25)
    
    if st.button("🔍 SCAN MARKET NOW"):
        results = []
        bar = st.progress(0)
        
        for i, sym in enumerate(stocks[:scan_count]):
            try:
                data = groww.get_quote(exchange="NSE", segment="FNO", trading_symbol=sym)
                ltp = data.get('last_price', 0)
                if ltp > 0:
                    p_chg = data.get('day_change_perc', 0)
                    oi_chg = data.get('oi_day_change_percentage', 0)
                    sug = get_suggestion(ltp, p_chg, oi_chg)
                    
                    results.append({
                        "STOCK": sym,
                        "LTP": ltp,
                        "PRICE %": f"{p_chg:.2f}%",
                        "OI %": f"{oi_chg:.2f}%",
                        "SIGNAL": sug['View'],
                        "ENTRY": sug['Entry'],
                        "TARGET": sug['Target'],
                        "STOP-LOSS": sug['StopLoss'],
                        "Color": sug['Color']
                    })
            except: continue
            bar.progress((i + 1) / scan_count)

        if results:
            df = pd.DataFrame(results)
            
            # Helper to color the rows
            def style_rows(row):
                return [f'background-color: {row.Color}'] * len(row)

            st.subheader("📋 Market Analysis & Trade Plan")
            st.dataframe(
                df.drop(columns=['Color']).style.apply(style_rows, axis=1),
                use_container_width=True,
                height=600
            )
            
            # Quick Export
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Save this Trade Plan", csv, "my_trades.csv", "text/csv")
        else:
            st.warning("No data found. Ensure market is open!")

st.divider()
st.info("💡 **How to read:** Green rows are Buy opportunities. Red rows are Sell opportunities. 'Entry' tells you the price level to wait for before jumping in.")
