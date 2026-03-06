import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Scanner", layout="wide")
st.title("🛡️ Safe Heaven Scanner (Fixed Mode)")

# --- 2. แถบเมนูข้าง ---
st.sidebar.header("⚙️ Settings")
assets = st.sidebar.multiselect(
    "เลือกสินทรัพย์ที่ต้องการ:", 
    ["^GSPC", "^SET50.BK", "BTC-USD", "GC=F", "NVDA", "AAPL", "TSLA", "MSFT", "PTT.BK", "AOT.BK"],
    default=["^GSPC", "^SET50.BK", "BTC-USD"]
)

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

@st.cache_data(ttl=60)
def fetch_data(tickers):
    results = []
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            if df.empty or len(df) < 200: 
                continue
            
            df = calculate_indicators(df)
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            last_price = float(last['Close'])
            prev_price = float(prev['Close'])
            change_pct = ((last_price - prev_price) / prev_price) * 100
            
            # ตรวจสอบการย่อหน้าในบล็อกเงื่อนไข (จุดที่เคย Error)
            if last_price > float(last['SMA200']) and float(last['RSI']) < 40:
                action = "🟢 BUY"
            elif float(last['RSI']) > 75:
                action = "💰 PROFIT"
            elif last_price < float(last['SMA200']):
                action = "🔴 EXIT"
            else:
                action = "Wait"
                
            results.append({
                "Ticker": ticker,
                "Price": f"{last_price:,.2f}",
                "Change %": f"{change_pct:.2f}%",
                "RSI": round(float(last['RSI']), 2),
                "Trend": "📈 Up" if last_price > float(last['SMA200']) else "📉 Down",
                "Action": action
            })
        except: 
            continue
    return pd.DataFrame(results)

# --- 4. การแสดงผล ---
if assets:
    summary_df = fetch_data(assets)
    if not summary_df.empty:
        st.subheader("🚀 สรุปสัญญาณปัจจุบัน")
        cols = st.columns(len(summary_df))
        for i, row in summary_df.iterrows():
            with cols[i]:
                # เลือกสีตามสถานะ
                bg = "#ffffff"; txt = "#212529"
                if "BUY" in row['Action']: bg = "#28a745"; txt = "#ffffff"
                elif "EXIT" in row['Action']: bg = "#dc3545"; txt = "#ffffff"
                elif "PROFIT" in row['Action']: bg = "#ffc107"; txt = "#212529"
                
                st.markdown(f"""
                    <div style="background-color: {bg}; padding: 20px; border-radius: 15px; text-align: center; border: 1px solid #ddd; color: {txt};">
                        <h3 style="margin:0;">{row['Ticker']}</h3>
                        <h2 style="margin:10px 0;">{row['Price']}</h2>
                        <div style="font-weight: bold;">{row['Action']}</div>
                    </div>
                """, unsafe_allow_html=True)

        st.divider()
        st.subheader("📊 ตารางเปรียบเทียบ")
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

        st.divider()
        selected = st.selectbox("🔍 เลือกดูวิเคราะห์กราฟ:", assets)
        df_plot = yf.download(selected, period="2y", interval="1d", auto_adjust=True)
        if isinstance(df_plot.columns, pd.MultiIndex): 
            df_plot.columns = df_plot.columns.get_level_values(0)
        df_plot = calculate_indicators(df_plot)

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='orange', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='purple', width=1.5)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        fig.update_layout(height=650, template="plotly_white", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("🔄 กำลังโหลดข้อมูล หรือไม่มีหุ้นที่มีประวัติยาวพอ (ต้องมีข้อมูล 200 วันขึ้นไป)")
else:
    st.info("👈 เลือกหุ้นที่แถบด้านข้างเพื่อเริ่มต้น")
