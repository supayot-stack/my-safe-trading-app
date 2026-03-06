import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Real-time", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Safe Heaven Scanner (Real-time Version)")

# --- 2. แถบเมนูด้านข้าง (เหลือแค่เลือกหุ้น) ---
st.sidebar.header("⚙️ Settings")
assets = st.sidebar.multiselect(
    "เลือกสินทรัพย์ที่ต้องการ:", 
    ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "GC=F", "NVDA", "AAPL", "TSLA", "MSFT"],
    default=["BTC-USD", "GC=F", "NVDA"]
)

# --- 3. ฟังก์ชันคำนวณและดึงข้อมูล ---
def calculate_indicators(df):
    # SMA 200 (หัวใจหลัก)
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

@st.cache_data(ttl=60) # อัปเดตข้อมูลทุก 60 วินาที (เกือบ Real-time)
def fetch_scan_data(tickers):
    results = []
    for ticker in tickers:
        try:
            # ดึงข้อมูลรายวัน ย้อนหลัง 2 ปี เพื่อความแม่นยำของ SMA200
            df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            if df.empty or len(df) < 200:
                continue
            
            df = calculate_indicators(df)
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # ตรวจสอบแนวโน้ม
            trend = "📈 Up Trend" if last['Close'] > last['SMA200'] else "📉 Down Trend"
            
            # ตรรกะสัญญาณ
            if trend == "📈 Up Trend" and last['RSI'] < 40:
                action = "🟢 STRONG BUY"
            elif last['RSI'] > 75:
                action = "💰 TAKE PROFIT"
            elif trend == "📉 Down Trend":
                action = "🔴 EXIT/AVOID"
            else:
                action = "Wait"
                
            results.append({
                "Ticker": ticker,
                "Price": f"{float(last['Close']):,.2f}",
                "Change %": f"{((float(last['Close']) - float(prev['Close'])) / float(prev['Close']) * 100):.2f}%",
                "RSI": round(float(last['RSI']), 2),
                "Trend": trend,
                "Action": action
            })
        except:
            continue
    return pd.DataFrame(results)

# --- 4. ส่วนการแสดงผล (Main UI) ---
if assets:
    # ดึงข้อมูลล่าสุด
    summary_df = fetch_scan_data(assets)
    
    if not summary_df.empty:
        st.subheader("🚀 สรุปสัญญาณปัจจุบัน (Update ทุก 1 นาที)")
        cols = st.columns(len(summary_df))
        
        for i, row in summary_df.iterrows():
            with cols[i]:
                # กำหนดสีตามสถานะล่าสุด
                bg_color = "#ffffff"; text_color = "#212529"
                if "BUY" in row['Action']:
                    bg_color = "#28a745"; text_color = "#ffffff"
                elif "EXIT" in row['Action'] or "AVOID" in row['Action']:
                    bg_color = "#dc3545"; text_color = "#ffffff"
                elif "PROFIT" in row['Action']:
                    bg_color = "#ffc107"; text_color = "#212529"
                
                st.markdown(f"""
                    <div style="background-color: {bg_color}; padding: 20px; border-radius: 15px; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); margin-bottom: 10px;">
                        <p style="margin:0; font-size:16px; color: {text_color}; opacity: 0.8;">{row['Ticker']}</p>
                        <h2 style="margin:10px 0; color: {text_color}; font-size:26px; font-weight: bold;">{row['Price']}</h2>
                        <div style="background-color: rgba(255,255,255,0.2); padding: 5px; border-radius: 8px; color: {text_color}; font-size: 13px; font-weight: bold;">
                            {row['Action']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📊 ตารางวิเคราะห์เชิงลึก")
        
        # ฟังก์ชันใส่สีในตาราง
        def style_action(val):
            if 'BUY' in val: return 'background-color: #d4edda'
            elif 'EXIT' in val or 'AVOID' in val: return 'background-color: #f8d7da'
            elif 'PROFIT' in val: return 'background-color: #fff3cd'
            return ''

        st.dataframe(summary_df.style.applymap(style_action, subset=['Action']), use_container_width=True)

        st.divider()
        selected = st.selectbox("🔍 วิเคราะห์กราฟแท่งเทียนรายตัว:", assets)
        
        # ดึงข้อมูลมาวาดกราฟ
        df_plot = yf.download(selected, period="2y", interval="1d", auto_adjust=True)
        if isinstance(df_plot.columns, pd.MultiIndex): 
            df_plot.columns = df_plot.columns.get_level_values(0)
        df_plot = calculate_indicators(df_plot)

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        
        fig.add_trace(go.Candlestick(
            x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], 
            low=df_plot['Low'], close=df_plot['Close'], name='ราคา'
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='เส้นแนวโน้ม 200 วัน', line=dict(color='orange', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='purple', width=1.5)), row=2, col=1)
        
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row
