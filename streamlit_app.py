import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. Settings & Caching ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")

# Add caching to prevent repeated API calls
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def get_cached_data(ticker, interval):
    try:
        period = "2y" if interval == "1d" else "60d"
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
        if df.empty or len(df) < 200:
            return None
        
        # Flatten columns if MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Calculations
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        return df
    except Exception:
        return None

# ... (Keep your existing CSS and Sidebar) ...

with tab1:
    st.title("🛡️ Safe Heaven Quant Scanner")
    
    # Logic to build the results list
    results = []
    # (Loop through all_assets using get_cached_data instead)
    
    # --- New Feature: Summary Metrics ---
    if results:
        res_df = pd.DataFrame(results)
        
        # Create columns for Top Picks
        buys = res_df[res_df['Signal'] == "STRONG BUY"]
        if not buys.empty:
            st.success(f"🔥 Found {len(buys)} Strong Buy Opportunities!")
            cols = st.columns(len(buys[:4])) # Show up to 4 cards
            for i, row in buys.iterrows():
                with cols[i % 4]:
                    st.metric(label=row['Ticker'], value=row['Price'], delta=f"RSI: {row['RSI']}")
        
        st.subheader("🎯 Market Overview")
        # Use st.dataframe with styling
        st.dataframe(res_df.drop(columns=['Color']).style.apply(lambda x: [f"background-color: {res_df.loc[i, 'Color']}33" for i in x.index], subset=['Signal']), use_container_width=True)
