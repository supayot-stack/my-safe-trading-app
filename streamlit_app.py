import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Pro", layout="wide")
st.title("🛡️ Safe Heaven Scanner (Fixed & Final)")

# --- 2. แถบเมนูด้านข้าง ---
st.sidebar.header("⚙️ Settings")

# รายชื่อหุ้นและดัชนี
assets = st.sidebar.multiselect(
    "เลือกสินทรัพย์:", 
    ["^GSPC", "^SET50.BK", "BTC-USD", "ETH-USD", "GC=F", "NVDA", "AAPL", "TSLA", "MSFT", "PTT.BK", "AOT.BK"],
    default=["^GSPC", "BTC-USD", "^SET50.BK"]
)

# เลือกหน่วยเวลา
interval_opt = {
    "1 นาที": "1m",
    "5 นาที": "5m",
    "15 นาที": "15m",
    "1 ชั่วโมง": "1h",
    "1 วัน": "1d"
}
selected_interval = st.sidebar.selectbox("เลือกหน่วยเวลา:", list(interval_opt.keys()), index=4)
interval_code = interval_opt[selected_interval]

# --- 3. ฟังก์ชันคำนวณ ---
def calculate_indicators(df):
    # SMA 200
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

@st.cache_data(ttl=30)
def fetch_data(tickers, interval):
    results = []
    # กำหนดความยาวข้อมูลให้พอสำหรับ SMA200
    period = "2y" if interval == "1d" else "60d"
    if interval in ["1m", "5m"]: period = "7d"

    for ticker in tickers:
        try:
            df = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df.empty or len(df) < 200:
                continue
            
            df = calculate_indicators(df)
            last = df.iloc[-1]
            
            last_price = float(last['Close'])
            rsi_val = float(last['RSI'])
            sma_val = float(last['SMA200'])
            
            # ตรรกะสัญญาณแบบเด็ดขาด
            if last_price > sma_val and rsi_val < 40:
                action = "🟢 BUY"
            elif rsi_val > 75:
                action = "💰 PROFIT"
            elif last_price < sma_val:
                action = "🔴 EXIT"
            else:
                action = "Wait"
                
            results.append({
                "Ticker": ticker,
                "Price": f"{last_price:,.2f}",
                "RSI": round(rsi_val, 2),
                "Action": action
            })
        except:
            continue
    return pd.DataFrame(results)

# --- 4. การแสดงผล ---
if assets:
    summary_df = fetch_data(assets, interval_code)
    
    if not summary_df.empty:
        st.subheader(f"🚀 สัญญาณล่าสุด ({selected_interval})")
        
        # แสดงผล Card
        cols = st.columns(len(summary_df))
        for i, row in summary_df.iterrows():
            with cols[i]:
                bg = "#ffffff"; txt = "#212529"
                if "BUY" in row['Action']: bg = "#28a745"; txt = "#ffffff"
                elif "EXIT" in row['Action']: bg = "#dc3545"; txt = "#ffffff"
                elif "PROFIT" in row['Action']: bg = "#ffc107"; txt = "#212529"
                
                st.markdown(f"""
                    <div style="background-color: {bg}; padding: 15px; border-radius: 12px; text-align: center; border: 1px solid #ddd; color: {txt};">
                        <h4 style="margin:0;">{row['Ticker']}</h4>
                        <h2 style="margin:5px 0;">{row['Price']}</h2>
                        <div style="font-weight: bold;">{row['Action']}</div>
                    </div>
                """, unsafe_allow_html=True)

        st.divider()
        selected_stock = st.selectbox("🔍 วิเคราะห์กราฟ:", assets)
        
        # ดึงข้อมูลกราฟใหม่
        df_plot = yf.download(selected_stock, period="60d" if interval_code != "1d" else "2y", interval=interval_code, auto_adjust=True)
        if isinstance(df_plot.columns, pd.MultiIndex):
            df_plot.columns = df_plot.columns.get_level_values(0)
        df_plot = calculate_indicators(df_plot)

        # สร้างกราฟ 2 ชั้น
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        
        # ราคา + SMA
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='orange', width=2)), row=1, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='purple', width=1.5)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        fig.update_layout(height=600, template="plotly_white", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("🔄 ข้อมูลกำลังโหลด หรือ Timeframe นี้มีข้อมูลไม่พอสำหรับ SMA 200")
else:
    st.info("👈 เลือกหุ้นที่แถบด้านข้างเพื่อเริ่มต้น")
