import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Classic", layout="wide")

# CSS: เน้นตัวเลขใหญ่ๆ และพื้นหลังสะอาด
st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    h1 { color: #1e222d; font-family: sans-serif; }
    .status-box {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #dee2e6;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Safe Heaven Scanner")

# --- 2. ตั้งค่าหุ้น (จัดกลุ่มแบบเรียบง่าย) ---
assets = {
    "🇺🇸 USA/Global": ["^GSPC", "GC=F", "NVDA", "AAPL", "TSLA", "MSFT"],
    "🇹🇭 Thai Market": ["^SET50.BK", "PTT.BK", "AOT.BK", "SCB.BK", "KBANK.BK"],
    "₿ Crypto": ["BTC-USD", "ETH-USD"]
}

# รวมหุ้นทั้งหมด
all_list = []
for v in assets.values(): all_list.extend(v)

st.sidebar.header("⏱️ เลือกหน่วยเวลา")
itv = st.sidebar.selectbox("หน่วยเวลา:", ["1 วัน", "1 ชั่วโมง", "5 นาที"], index=0)
itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}

# --- 3. ฟังก์ชันคำนวณ ---
def get_data(ticker, interval):
    period = "2y" if interval == "1d" else "60d"
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    if df.empty or len(df) < 200: return None
    
    # SMA 200 & RSI 14
    df['SMA200'] = df['Close'].rolling(200).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
    return df

# --- 4. แสดงผล Dashboard ---
st.subheader(f"📈 สรุปสัญญาณล่าสุด ({itv})")
cols = st.columns(4)
summary_data = []

# ดึงข้อมูลมาโชว์ 4 ตัวหลัก (ดัชนีและบิทคอยน์)
main_picks = ["^GSPC", "^SET50.BK", "BTC-USD", "GC=F"]
for i, ticker in enumerate(main_picks):
    df = get_data(ticker, itv_map[itv])
    if df is not None:
        last = df.iloc[-1]
        p, r, s = last['Close'], last['RSI'], last['SMA200']
        
        # ตัดสินใจสีและคำพูด
        if p > s and r < 40: status, color = "น่าซื้อ (Buy)", "#26a69a"
        elif r > 75: status, color = "ขายทำกำไร", "#f57c00"
        elif p < s: status, color = "อันตราย (Avoid)", "#ef5350"
        else: status, color = "ถือ/รอชม", "#787b86"
        
        with cols[i]:
            st.markdown(f"""
                <div class="status-box" style="border-top: 5px solid {color};">
                    <div style="font-size: 16px; color: #787b86;">{ticker}</div>
                    <div style="font-size: 28px; font-weight: bold;">{p:,.2f}</div>
                    <div style="color: {color}; font-weight: bold;">{status}</div>
                </div>
            """, unsafe_allow_html=True)

st.divider()

# --- 5. กราฟรายตัว (เน้นความชัดเจน) ---
st.subheader("🔍 วิเคราะห์กราฟละเอียด")
selected = st.selectbox("เลือกชื่อหุ้น:", all_list)

df_plot = get_data(selected, itv_map[itv])
if df_plot is not None:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    # แท่งเทียนสีมาตรฐาน
    fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], 
                                 low=df_plot['Low'], close=df_plot['Close'], name='ราคา'), row=1, col=1)
    
    # เส้น SMA 200 สีส้ม (มองเห็นง่ายที่สุดบนแท่งเทียน)
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='เส้นแบ่งแนวโน้ม', 
                             line=dict(color='#ff9800', width=2)), row=1, col=1)
    
    # RSI สีน้ำเงิน
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', 
                             line=dict(color='#2196f3', width=1.5)), row=2, col=1)
    
    # เส้นประขอบเขต RSI
    fig.add_hline(y=70, line_dash="dash", line_color="#ef5350", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#26a69a", row=2, col=1)

    fig.update_layout(
        height=600, template="plotly_white", xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("ไม่พบข้อมูลหุ้นตัวนี้ หรือข้อมูลไม่เพียงพอสำหรับคำนวณ SMA 200")
