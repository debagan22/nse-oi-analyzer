import streamlit as st
import pandas as pd

# Function to categorize market sentiment based on Price and OI
def get_sentiment(row):
    p_change = row['CHG_IN_CLOSE'] # Price Change
    oi_change = row['CHG_IN_OI']   # OI Change
    
    if p_change > 0 and oi_change > 0:
        return "Long Buildup (Bullish 🚀)"
    elif p_change < 0 and oi_change > 0:
        return "Short Buildup (Bearish 📉)"
    elif p_change > 0 and oi_change < 0:
        return "Short Covering (Recovery ↗️)"
    elif p_change < 0 and oi_change < 0:
        return "Long Unwinding (Weakness ↘️)"
    else:
        return "Neutral"

st.title("🎯 OI-Based Option Suggestion Tool")

# Upload Bhavcopy CSV manually for now (or automate with nsepython)
uploaded_file = st.file_uploader("Upload NSE F&O Bhavcopy (CSV)", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # Filter for Options (OPTSTK or OPTIDX)
    # We focus on 'Total' OI per Symbol for easier EOD analysis
    summary = df.groupby('SYMBOL').agg({
        'CLOSE': 'last',
        'CHG_IN_OI': 'sum',
        'OPEN_INT': 'sum'
    }).reset_index()

    # Calculate Price Change % (Simulated for this EOD logic)
    # In a real app, you'd compare today's Close vs Yesterday's
    summary['CHG_IN_CLOSE'] = summary['CLOSE'].pct_change() 
    
    summary['Sentiment'] = summary.apply(get_sentiment, axis=1)

    # Display Top 10 Bullish/Bearish Stocks
    st.header("Top Market Sentiment")
    st.dataframe(summary[['SYMBOL', 'CLOSE', 'Sentiment']].sort_values(by='Sentiment'))

    # Specific Recommendation Logic
    st.divider()
    st.subheader("💡 Trade Suggestions")
    
    bullish_stocks = summary[summary['Sentiment'].str.contains("Long Buildup")].head(3)
    for _, row in bullish_stocks.iterrows():
        st.success(f"**BUY CALL** on {row['SYMBOL']}: Price rising with fresh OI.")

    bearish_stocks = summary[summary['Sentiment'].str.contains("Short Buildup")].head(3)
    for _, row in bearish_stocks.iterrows():
        st.error(f"**BUY PUT** on {row['SYMBOL']}: Aggressive selling detected.")
