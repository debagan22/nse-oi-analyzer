import streamlit as st
# ... (include the get_latest_fno_data function here)

st.set_page_config(page_title="NSE OI Dashboard", layout="wide")
st.title("🚀 NSE F&O OI-Based Suggestion Engine")

data, found_date = get_latest_fno_data()

if data is not None:
    st.success(f"Showing Data for: {found_date.strftime('%d-%b-%Y')}")
    
    # Process OI Change
    # Filter for OPTIONS only to keep it clean
    df_opt = data[data['INSTRUMENT'].str.contains('OPT')]
    
    # Suggestion Logic: Group by Symbol to see where OI is building
    summary = df_opt.groupby('SYMBOL').agg({
        'CLOSE': 'mean',
        'CHG_IN_OI': 'sum',
        'OPEN_INT': 'sum'
    }).reset_index()

    # Create Columns for Suggestions
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔥 Top Long Buildup (Buy Call)")
        # Price Up + OI Up
        long_buildup = summary[summary['CHG_IN_OI'] > 0].sort_values(by='CHG_IN_OI', ascending=False).head(5)
        st.table(long_buildup[['SYMBOL', 'CHG_IN_OI']])

    with col2:
        st.subheader("🐻 Top Short Buildup (Buy Put)")
        # Price Down + OI Up (Simplified)
        short_buildup = summary[summary['CHG_IN_OI'] > 0].sort_values(by='CHG_IN_OI', ascending=True).head(5)
        st.table(short_buildup[['SYMBOL', 'CHG_IN_OI']])
else:
    st.error("Could not fetch data. NSE server might be down or it's a holiday.")
