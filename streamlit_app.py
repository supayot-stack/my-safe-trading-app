import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอและสไตล์ ---
st.set_page_config(page_title="Safe Heaven Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Safe Heaven Scanner (Standard Version)")

# --- 2. แถบเมนูด้านข้าง (Sidebar) ---
st.sidebar.header("⚙️ Settings")
assets = st.sidebar.multiselect(
    "เลือกสินทรัพย์ที่ต้องการ:", 
    ["BTC-USD", "ETH-USD", "BNB-USD", "SOL-USD", "GC=F", "NVDA", "AAPL", "TSLA", "MSFT"],
    default=["BTC-USD", "GC=F", "NVDA"]
)

tf = st.sidebar.selectbox(
    "เลือกหน่วยเวลา (Timeframe):", 
    options=["1h", "1d", "1wk"], 
    format_func=lambda x: "1 ชั่วโมง (1H) | ย้อนหลัง 1 เดือน" if x=="1h" else ("1 วัน (1D) | ย้อนหลัง 2 ปี" if x=="1d" else "1 สัปดาห์ (1W) | ย้อนหลัง 5 ปี"),
    index=1
)

# --- 3. ฟังก์ชันคำนวณและดึงข้อมูล ---
def get_optimal_period(timeframe):
    if timeframe == "1h": return "1mo" 
    if timeframe == "1d": return "2y"   
    if timeframe == "1wk": return "5y"
    return "2y"

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

@st.cache_data(ttl=600)
def fetch_scan_data(tickers, timeframe):
    results = []
    period = get_optimal_period(timeframe)
    for ticker in tickers:
        try:
            df = yf.download(ticker, period=period, interval=timeframe, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            if df.empty or len(df) < 200:
                continue
            
            df = calculate_indicators(df)
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            trend = "📈 Up Trend" if last['Close'] > last['SMA200'] else "📉 Down Trend"
            
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
    summary_df = fetch_scan_data(assets, tf)
    
    if not summary_df.empty:
        st.subheader(f"🚀 สรุปสัญญาณด่วน (โหมด {tf})")
        cols = st.columns(len(summary_df))
        
        for i, row in summary_df.iterrows():
            with cols[i]:
                bg_color = "#ffffff"
                text_color = "#212529"
                if "BUY" in row['Action']:
                    bg_color = "#28a745"; text_color = "#ffffff"
                elif "EXIT" in row['Action'] or "AVOID" in row['Action']:
                    bg_color = "#dc3545"; text_color = "#ffffff"
                elif "PROFIT" in row['Action']:
                    bg_color = "#ffc107"; text_color = "#212529"
                
                st.markdown(f"""
                    <div style="background-color: {bg_color}; padding: 20px; border-radius: 15px; text-align: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); margin-bottom: 10px;">
                        <p style="margin:0; font-size:16px; color: {text_color}; opacity: 0.9;">{row['Ticker']}</p>
                        <h2 style="margin:10px 0; color: {text_color}; font-size:26px; font-weight: bold;">{row['Price']}</h2>
                        <div style="background-color: rgba(255,255,255,0.2); padding: 5px; border-radius: 8px; color: {text_color}; font-size: 13px; font-weight: bold;">
                            {row['Action']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📊 รายละเอียดข้อมูลเชิงลึก")
        
        def style_action(val):
            if 'BUY' in val: return 'background-color: #d4edda'
            elif 'EXIT' in val or 'AVOID' in val: return 'background-color: #f8d7da'
            elif 'PROFIT' in val: return 'background-color: #fff3cd'
            return ''

        st.dataframe(summary_df.style.applymap(style_action, subset=['Action']), use_container_width=True)

        st.divider()
        selected = st.selectbox("🔍 วิเคราะห์กราฟแท่งเทียนรายตัว:", assets)
        
        period_chart = get_optimal_period(tf)
        df_plot = yf.download(selected, period=period_chart, interval=tf, auto_adjust=True)
        if isinstance(df_plot.columns, pd.MultiIndex): 
            df_plot.columns = df_plot.columns.get_level_values(0)
        
        df_plot = calculate_indicators(df_plot)

        # สร้างกราฟ 2 ชั้น
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        
        fig.add_trace(go.Candlestick(
            x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], 
            low=df_plot['Low'], close=df_plot['Close'], name='Price'
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='orange', width=2)), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='purple', width=1.5)), row=2, col=1)
        
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        fig.update_layout(height=650, template="plotly_white", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ ข้อมูลไม่เพียงพอสำหรับเงื่อนไขนี้ โปรดลองเปลี่ยนหน่วยเวลา")
else:
    st.info("👈 เริ่มต้นโดยการเลือกชื่อสินทรัพย์ที่แถบด้านข้าง")
