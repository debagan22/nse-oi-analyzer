import streamlit as st
import pandas as pd
from growwapi import GrowwAPI
import pyotp
import time

# 1. Page Configuration
st.set_page_config(page_title="Groww OI Advisor", layout="wide", page_icon="🎯")

# 2. Authentication Function
def get_groww_client():
    try:
        # Accessing secrets set in Streamlit Cloud or local secrets.toml
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        
        # Step: Generate a daily access token using the SDK
        # This bypasses the need for manual browser login
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"⚠️ Authentication Error: {e}")
        st.info("Check if your Key/Secret are correct in Streamlit Secrets.")
        return None

# 3. Main Application UI
st.title("🛡️ Groww F&O Suggestion Engine")
st.markdown("---")

groww = get_groww_client()

if groww:
    st.sidebar.success("Connected to Groww API")
    
    # Input controls
    col_a, col_b = st.columns(2)
    with col_a:
        symbol = st.selectbox("Underlying Index", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
    with col_b:
        # Note: Expiry format for Groww is usually YYYY-MM-DD
        expiry = st.text_input("Expiry Date (YYYY-MM-DD)", value="2026-02-26")

    if st.button("Analyze Market Sentiment"):
        with st.spinner("Fetching live Option Chain..."):
            try:
                # Fetch data directly from Groww's high-speed servers
                chain = groww.get_option_chain(
                    exchange="NSE", 
                    underlying=symbol, 
                    expiry_date=expiry
                )
                
                # Process the 'strikes' list into a DataFrame
                df = pd.DataFrame(chain['strikes'])
                
                # Cleanup and Calculation
                total_pe_oi = df['pe_open_interest'].sum()
                total_ce_oi = df['ce_open_interest'].sum()
                pcr = total_pe_oi / total_ce_oi
                
                # Find Max Pain (Highest OI levels)
                max_ce_strike = df.loc[df['ce_open_interest'].idxmax(), 'strike_price']
                max_pe_strike = df.loc[df['pe_open_interest'].idxmax(), 'strike_price']

                # Display Dashboard
                m1, m2, m3 = st.columns(3)
                m1.metric("PCR (Put-Call Ratio)", f"{pcr:.2f}")
                m2.metric("Resistance (Max CE)", f"₹{max_ce_strike}")
                m3.metric("Support (Max PE)", f"₹{max_pe_strike}")

                st.subheader("🤖 Trading Suggestion")
                if pcr > 1.25:
                    st.success("🎯 **BULLISH:** Heavy Put writing. Market has a strong floor. Look to Buy Calls on dips.")
                elif pcr < 0.75:
                    st.error("🎯 **BEARISH:** Heavy Call writing. Market has a strong ceiling. Look to Buy Puts on rallies.")
                else:
                    st.warning("🎯 **NEUTRAL:** Market is in a range. Avoid aggressive long/short positions.")

                # Show table for detail-oriented users
                with st.expander("Show Raw Option Chain Data"):
                    st.dataframe(df[['strike_price', 'ce_open_interest', 'pe_open_interest', 'ce_ltp', 'pe_ltp']])

            except Exception as e:
                st.error(f"Error fetching data: {e}")
else:
    st.warning("Awaiting API Connection. Please ensure your Secrets are configured correctly.")

st.markdown("---")
st.caption("Data provided via Groww Trading API. Not financial advice.")
