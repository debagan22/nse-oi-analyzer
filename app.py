import streamlit as st
import pandas as pd
from growwapi import GrowwAPI
import pyotp

# 1. AUTHENTICATION SECTION
def get_groww_client():
    try:
        # Accessing secrets you've set in Streamlit Cloud "Advanced Settings"
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        
        # Step: Generate a daily access token
        # Some versions might require a checksum or TOTP, 
        # but the standard SDK uses Key + Secret for the token flow
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"⚠️ Auth Error: {e}")
        return None

# 2. APP UI
st.title("🎯 Groww Option Analyzer")
groww = get_groww_client()

if groww:
    st.success("Successfully connected to Groww API!")
    
    symbol = st.selectbox("Select Index", ["NIFTY", "BANKNIFTY"])
    expiry = st.text_input("Expiry Date (YYYY-MM-DD)", value="2026-02-26")

    if st.button("Fetch OI Data"):
        # Fetching data directly from Groww
        chain = groww.get_option_chain(exchange="NSE", underlying=symbol, expiry_date=expiry)
        df = pd.DataFrame(chain['strikes'])
        
        # Suggestion Logic: Put-Call Ratio (PCR)
        total_pe_oi = df['pe_open_interest'].sum()
        total_ce_oi = df['ce_open_interest'].sum()
        pcr = total_pe_oi / total_ce_oi
        
        st.metric("Current PCR", round(pcr, 2))
        
        if pcr > 1.25:
            st.success("BULLISH SENTIMENT: High Put writing. Look for Buy signals.")
        elif pcr < 0.75:
            st.error("BEARISH SENTIMENT: High Call writing. Look for Sell signals.")
        else:
            st.warning("NEUTRAL SENTIMENT: Market is consolidating.")import streamlit as st
import pandas as pd
from growwapi import GrowwAPI

# 1. Setup Page
st.set_page_config(page_title="Groww Option Advisor", layout="wide")

# 2. Authentication (Automated)
@st.cache_resource
def get_groww_client():
    try:
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        
        # Groww requires a daily access token
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"Failed to log in to Groww: {e}")
        return None

groww = get_groww_client()

if groww:
    st.title("🟢 Groww F&O Suggestion Engine")
    
    # 3. User Interface
    col1, col2 = st.columns(2)
    with col1:
        symbol = st.selectbox("Underlying Asset", ["NIFTY", "BANKNIFTY", "RELIANCE"])
    with col2:
        # Today is Feb 20, 2026. Next weekly expiry is likely Feb 26.
        expiry = st.text_input("Expiry (YYYY-MM-DD)", value="2026-02-26")

    if st.button("Generate Suggestions"):
        # 4. Fetch Option Chain
        chain = groww.get_option_chain(exchange="NSE", underlying=symbol, expiry_date=expiry)
        df = pd.DataFrame(chain['strikes'])

        # 5. Logic: Calculate Put-Call Ratio (PCR)
        total_pe_oi = df['pe_open_interest'].sum()
        total_ce_oi = df['ce_open_interest'].sum()
        pcr = total_pe_oi / total_ce_oi

        # 6. Suggestions
        st.subheader(f"Market Sentiment: {'Bullish' if pcr > 1.1 else 'Bearish' if pcr < 0.8 else 'Neutral'}")
        
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        metric_col1.metric("Current PCR", f"{pcr:.2f}")
        metric_col2.metric("Resistance (Max CE OI)", f"{df.loc[df['ce_open_interest'].idxmax(), 'strike_price']}")
        metric_col3.metric("Support (Max PE OI)", f"{df.loc[df['pe_open_interest'].idxmax(), 'strike_price']}")

        # Actionable Suggestions
        if pcr > 1.2:
            st.success("🎯 SUGGESTION: BUY CALL at Support. High Put writing indicates strong floor.")
        elif pcr < 0.7:
            st.error("🎯 SUGGESTION: BUY PUT at Resistance. High Call writing indicates strong ceiling.")
        else:
            st.warning("🎯 SUGGESTION: WAIT. PCR is neutral; market may be sideways.")
