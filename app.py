import streamlit as st
import pandas as pd
from growwapi import GrowwAPI

st.set_page_config(page_title="F&O Diagnostics", layout="wide")

@st.cache_resource
def get_groww_client():
    try:
        if "GROWW_API_KEY" not in st.secrets:
            st.error("🔑 Secrets missing: Add GROWW_API_KEY and GROWW_API_SECRET to Streamlit.")
            return None
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"❌ Auth Failed: {e}")
        return None

st.title("🏹 High-Sensitivity F&O Scanner")
groww = get_groww_client()

# CONFIG - Note: For 26 Feb Expiry, the code must match broker's string
EXP_STR = "26FEB" 
YR = "26"

if groww:
    # A smaller, simplified list to test connectivity
    test_stocks = {"RELIANCE": 20, "SBIN": 5, "HDFCBANK": 10}
    
    if st.button("🚀 Run Live Diagnostics"):
        results = []
        status_col = st.columns(1)[0]
        
        for sym, step in test_stocks.items():
            try:
                # STEP 1: Get Spot Price (Use CASH segment)
                # Some API versions require the prefix 'NSE:'
                spot = groww.get_quote(trading_symbol=sym, exchange="NSE", segment="CASH")
                ltp = spot.get('last_price', 0)
                
                if ltp > 0:
                    atm = int(round(ltp / step) * step)
                    # STEP 2: Construct Option Symbol
                    # Format: RELIANCE26FEB2800CE
                    opt_sym = f"{sym}{YR}{EXP_STR}{atm}CE"
                    
                    # STEP 3: Get Option Quote
                    opt_data = groww.get_quote(trading_symbol=opt_sym, exchange="NSE", segment="FNO")
                    opt_ltp = opt_data.get('last_price', 0)
                    
                    results.append({
                        "Stock": sym,
                        "Spot Price": ltp,
                        "Contract": opt_sym,
                        "Opt LTP": opt_ltp if opt_ltp else "No Premium Data",
                        "Status": "✅ Success" if opt_ltp else "⚠️ No Opt Data"
                    })
                else:
                    st.sidebar.error(f"Failed to get price for {sym}. Response: {spot}")
            except Exception as e:
                st.sidebar.warning(f"Error on {sym}: {e}")
                continue

        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True)
        else:
            st.error("Total Failure: No data returned for any symbols. See Sidebar for errors.")

---

### 🔍 Top 3 Reasons for "No Data" Today:

1.  **The Symbol String Mismatch:** Brokers change their naming slightly. In 2026, some APIs require `NSE:RELIANCE26FEB2800CE` (with a colon) or `RELIANCE262262800CE` (using the day in numbers). If the string is off by one character, it returns "No Data."

2.  **API Permissions (F&O Activation):**
    Even if you can trade in the Groww app, your **API User** might not have "Derivative Data" permissions enabled. You can check this by trying to fetch `segment="CASH"`—if Cash works but `segment="FNO"` fails, your API is restricted.

3.  **Token Expiry:**
    Groww access tokens usually expire every 24 hours. If your app has been running for more than a day, you must **Re-deploy** or **Refresh** to trigger a new `access_token` generation.

**Would you like me to add a "Raw Response Viewer" so we can see the exact JSON text the broker is sending back to find the exact error code?**
