import streamlit as st
import pandas as pd
import requests
import io
import zipfile
from datetime import datetime, timedelta

# 1. DEFINE THE FUNCTION FIRST
def get_latest_fno_data():
    for i in range(4):
        target_date = datetime.now() - timedelta(days=i)
        if target_date.weekday() >= 5: continue 
        
        day = target_date.strftime("%d")
        month = target_date.strftime("%b").upper()
        year = target_date.strftime("%Y")
        url = f"https://archives.nseindia.com/content/historical/DERIVATIVES/{year}/{month}/fo{day}{month}{year}bhav.csv.zip"
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    csv_filename = z.namelist()[0]
                    return pd.read_csv(z.open(csv_filename)), target_date
        except:
            continue
    return None, None

# 2. NOW CALL THE FUNCTION
st.title("📈 NSE OI Analyzer")

data, found_date = get_latest_fno_data()

if data is not None:
    st.write(f"Successfully loaded data for {found_date.date()}")
    # Your OI logic goes here...
else:
    st.error("Could not fetch data from NSE.")
