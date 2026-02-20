import streamlit as st
import pandas as pd
import requests
import io
import zipfile
from datetime import datetime, timedelta

# --- STEP 1: IMPROVED SCRAPER ---
def get_latest_fno_data():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    })
    
    # Try last 5 days
    for i in range(1, 6):
        target_date = datetime.now() - timedelta(days=i)
        if target_date.weekday() >= 5: continue
        
        d, m, y = target_date.strftime("%d"), target_date.strftime("%b").upper(), target_date.strftime("%Y")
        url = f"https://archives.nseindia.com/content/historical/DERIVATIVES/{y}/{m}/fo{d}{m}{y}bhav.csv.zip"
        
        try:
            res = session.get(url, timeout=10)
            if res.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(res.content)) as z:
                    return pd.read_csv(z.open(z.namelist()[0])), target_date
        except: continue
    return None, None

# --- STEP 2: UI LOGIC ---
st.set_page_config(page_title="OI Suggestion Engine", layout="wide")
st.title("🎯 NSE F&O OI Suggestion Engine")

# Auto-fetch attempt
data, found_date = get_latest_fno_data()

# Manual Upload Backup
st.sidebar.header("Data Source")
uploaded_file = st.sidebar.file_uploader("Manual Backup: Upload Bhavcopy CSV", type=["csv", "zip"])

if uploaded_file:
    # Logic to handle manual ZIP or CSV
    if uploaded_file.name.endswith('.zip'):
        with zipfile.ZipFile(uploaded_file) as z:
            data = pd.read_csv(z.open(z.namelist()[0]))
    else:
        data = pd.read_csv(uploaded_file)
    st.sidebar.success("Using Manually Uploaded Data")

# --- STEP 3: THE ANALYSIS ---
if data is not None:
    # Clean up column names (NSE often has trailing spaces)
    data.columns = [c.strip() for c in data.columns]
    
    # Simple OI Logic
    st.subheader("🚀 Top Long Buildup (Buy Suggestions)")
    # Logic: OI Increase + Price Increase
    buildup = data[(data['CHG_IN_OI'] > 0) & (data['CLOSE'] > data['OPEN'])]
    st.dataframe(buildup[['SYMBOL', 'EXPIRY_DATE', 'STRIKE_PR', 'OPTION_TYP', 'CLOSE', 'CHG_IN_OI']].head(10))
else:
    st.warning("Auto-fetch blocked by NSE. Please download the Bhavcopy from NSE and upload it here.")
