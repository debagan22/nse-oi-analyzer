import streamlit as st
import pandas as pd
import requests
import io
import zipfile
from datetime import datetime, timedelta

def get_latest_fno_data():
    session = requests.Session()
    # These specific headers are crucial to look like a real browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nseindia.com/all-reports-derivatives',
    })

    # Try to fetch for the last 5 days
    for i in range(1, 6):
        target_date = datetime.now() - timedelta(days=i)
        if target_date.weekday() >= 5: continue
        
        d, m, y = target_date.strftime("%d"), target_date.strftime("%b").upper(), target_date.strftime("%Y")
        url = f"https://archives.nseindia.com/content/historical/DERIVATIVES/{y}/{m}/fo{d}{m}{y}bhav.csv.zip"
        
        try:
            # We first ping the home page to get a cookie session
            session.get("https://www.nseindia.com", timeout=5)
            response = session.get(url, timeout=10)
            
            if response.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    return pd.read_csv(z.open(z.namelist()[0])), target_date
        except:
            continue
    return None, None

st.title("🛡️ NSE OI Suggestion Engine")

# --- AUTO FETCH ---
data, found_date = get_latest_fno_data()

# --- MANUAL UPLOAD (PLAN B) ---
st.sidebar.header("Data Control")
manual_file = st.sidebar.file_uploader("If auto-fetch fails, upload foXXXXbhav.csv.zip here", type=["zip", "csv"])

if manual_file:
    if manual_file.name.endswith('.zip'):
        with zipfile.ZipFile(manual_file) as z:
            data = pd.read_csv(z.open(z.namelist()[0]))
    else:
        data = pd.read_csv(manual_file)
    found_date = "Manual Upload"

# --- RENDER DATA ---
if data is not None:
    st.success(f"Data Loaded: {found_date}")
    # Process your OI logic here...
    st.dataframe(data.head())
else:
    st.error("Auto-fetch still blocked by NSE firewall.")
    st.info("To fix this right now: Go to [NSE Reports](https://www.nseindia.com/all-reports-derivatives), download the 'Bhavcopy (csv.zip)', and upload it to the sidebar.")
