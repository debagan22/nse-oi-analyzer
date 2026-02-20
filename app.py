import streamlit as st
import pandas as pd
from growwapi import GrowwAPI
from datetime import datetime

st.set_page_config(page_title="Groww OI Analyzer", layout="wide")

@st.cache_resource
def get_groww_client():
    try:
        api_key = st.secrets["GROWW_API_KEY"]
        api_secret = st.secrets["GROWW_API_SECRET"]
        access_token = GrowwAPI.get_access_token(api_key=api_key, secret=api_secret)
        return GrowwAPI(access_token)
    except Exception as e:
        st.error(f"Auth Error: {e}")
        return None

st.title("🛡️ Groww F&O Suggestion Engine")
groww = get_groww_client()

if groww:
    col1, col2 = st.columns(2)
    with col1:
        symbol = st.selectbox("Index", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
    with col2:
        # Note: Ensure this date is a VALID upcoming Thursday!
        expiry = st.text_input("Expiry (YYYY-MM-DD)", value="2026-02-26")

    if st.button("Fetch Option Chain"):
        try:
            # 1. Fetch live data
            response = groww.get_option_chain(exchange="NSE", underlying=symbol, expiry_date=expiry)
            
            # 2. Extract 'strikes' (Groww nesting: payload -> strikes)
            # The structure is often response['payload']['strikes'] or response['strikes']
            strikes_data = response.get('payload', {}).get('strikes', response.get('strikes', {}))

            if not strikes_data:
                st.warning(f"No data found for {symbol} on {expiry}. Try the next expiry date.")
            else:
                # 3. Flatten the dictionary into a list for Pandas
                rows = []
                for strike, data in strikes_data.items():
                    rows.append({
                        "Strike": strike,
                        "CE_OI": data.get('CE', {}).get('open_interest', 0),
                        "PE_OI": data.get('PE', {}).get('open_interest', 0),
                        "CE_LTP": data.get('CE', {}).get('ltp', 0),
                        "PE_LTP": data.get('PE', {}).get('ltp', 0)
                    })
                
                df = pd.DataFrame(rows)
                df['Strike'] = pd.to_numeric(df['Strike'])
                df = df.sort_values("Strike")

                # 4. Show Analysis
                total_ce = df['CE_OI'].sum()
                total_pe = df['PE_OI'].sum()
                pcr = total_pe / total_ce if total_ce > 0 else 0
                
                st.metric("Put-Call Ratio (PCR)", f"{pcr:.2f}")
                st.dataframe(df, use_container_width=True)

        except Exception as e:
            st.error(f"Data processing error: {e}")
