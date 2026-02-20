import streamlit as st
import pandas as pd
import requests
import io
import zipfile
from datetime import datetime, timedelta

def get_latest_fno_data():
    session = requests.Session()
    # Comprehensive headers to look like a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Referer': 'https://www.nseindia.com/all-reports-derivatives'
    }
    
    # Try to fetch for the last 3 working days
    for i in range(1, 4):
        target_date = datetime.now() - timedelta(days=i)
        if target_date.weekday() >= 5: continue # Skip Sat/Sun
        
        d, m, y = target_date.strftime("%d"), target_date.strftime("%b").upper(), target_date.strftime("%Y")
        url = f"https://archives.nseindia.com/content/historical/DERIVATIVES/{y}/{m}/fo{d}{m}{y}bhav.csv.zip"
        
        try:
            # Visit home page first to get cookies
            session.get("https://www.nseindia.com", headers=headers, timeout=5)
            response = session.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    return pd.read_csv(z.open(z.namelist()[0])), target_date
        except: continue
    return None, None

st.set_page_config(page_title="NSE F&O Analyzer", layout="wide")
st.title("🛡️ NSE OI Suggestion Engine")

# --- DATA LOADING ---
data, found_date = get_latest_fno_data()

# Sidebar fallback
st.sidebar.header("Data Control")
manual_file = st.sidebar.file_uploader("Backup: Upload Bhavcopy (zip/csv)", type=["zip", "csv"])

if manual_file:
    if manual_file.name.endswith('.zip'):
        with zipfile.ZipFile(manual_file) as z:
            data = pd.read_csv(z.open(z.namelist()[0]))
    else:
        data = pd.read_csv(manual_file)
    found_date = "Manual Upload"

# --- ANALYSIS SECTION ---
if data is not None:
    st.success(f"Data Source: {found_date}")
    data.columns = [c.strip() for c in data.columns] # Clean spaces
    
    # Simple OI Logic for Suggestion
    # Long Buildup = Price Up + OI Up
    buildup = data[(data['CHG_IN_OI'] > 0) & (data['CLOSE'] > data['OPEN'])]
    
    st.subheader("💡 Buy Suggestions (Long Buildup)")
    st.dataframe(buildup[['SYMBOL', 'STRIKE_PR', 'OPTION_TYP', 'CLOSE', 'CHG_IN_OI']].sort_values(by='CHG_IN_OI', ascending=False).head(10))
else:
    st.error("❌ Auto-fetch blocked by NSE Firewall.")
    st.info("To fix this now: Download the 'Bhavcopy (csv.zip)' from the link below and upload it here.")
    st.markdown("[Go to NSE Daily Reports](https://www.nseindia.com/all-reports-derivatives)")
