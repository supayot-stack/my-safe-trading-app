import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Pro", layout="wide")

# CSS ตกแต่งให้ดูสะอาดตา
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .stSelectbox label { font-size: 18px; font-weight: bold; color: #1e1e1e; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Safe Heaven Scanner")

# --- 2. การตั้งค่าหุ้นและหมวดหมู่ ---
# จัดกลุ่มหุ้นให้คุณเลือกง่ายๆ ตามกลุ่มอุตสาหกรรม
stock_categories = {
    "🏆 ดัชนีหลัก (Indices)": ["^GSPC", "^SET50.BK", "GC=F"],
    "🚀 หุ้นเทคโนโลยี (Tech)": ["NVDA", "AAPL", "MSFT", "GOOGL", "TSLA"],
    "🏦 การเงิน & ไทย (Thai/Finance)": ["SCB.BK", "KBANK.BK", "PTT.BK", "AOT.BK"],
    "🪙 คริปโต (Crypto)": ["BTC-USD", "ETH-USD"]
}

# รวมหุ้นทั้งหมดเพื่อใช้ในการดึงข้อมูล
all_assets = []
for stocks in stock_categories.values():
    all_assets.extend(stocks)

# เลือกหน่วยเวลาที่แถบด้านข้าง
st.sidebar.header("⏱️ การตั้งค่าเวลา")
interval_opt = {"1 นาที": "1m", "5 นาที": "5m", "1 ชั่วโมง": "1h", "1 วัน": "1d"}
selected_interval = st.sidebar.selectbox("เลือกหน่วยเวลา:", list(interval_opt.keys()), index=3)
interval_code = interval_opt[selected_interval]

# --- 3. ฟังก์ชันคำนวณ ---
def calculate_indicators(df):
    df['SMA200'] = df['Close'].rolling(window=200).mean()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

@st.cache_data(ttl=30)
def fetch_data(tickers, interval):
    results = []
    period = "2y" if interval == "1d" else "60d"
    for ticker in tickers:
        try:
            df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if df.empty or len(df) < 200: continue
            df = calculate_indicators(df)
            last = df.iloc[-1]
            p, r, s = float(last['Close']), float(last['RSI']), float(last['SMA200'])
            
            if p > s and r < 40: action = "🟢 BUY"
            elif r > 75: action = "💰 PROFIT"
            elif p < s: action = "🔴 EXIT"
            else: action = "Wait"
                
            results.append({"Ticker": ticker, "Price": p, "RSI": round(r, 2), "Action": action})
        except: continue
    return pd.DataFrame(results)

# --- 4. การแสดงผลส่วนบน (Dashboard Cards) ---
summary_df = fetch_data(all_assets, interval_code)

if not summary_df.empty:
    st.subheader(f"📊 สรุปตลาดปัจจุบัน ({selected_interval})")
    
    # ดึงเฉพาะหุ้นที่มีสัญญาณแรงๆ มาโชว์ 4 ตัวแรก
    top_picks = summary_df[summary_df['Action'] != "Wait"].head(4)
    if top_picks.empty: top_picks = summary_df.head(4)
    
    cols = st.columns(len(top_picks))
    for i, (idx, row) in enumerate(top_picks.iterrows()):
        with cols[i]:
            color = "#28a745" if "BUY" in row['Action'] else "#dc3545" if "EXIT" in row['Action'] else "#ffc107" if "PROFIT" in row['Action'] else "#333"
            st.markdown(f"""
                <div style="background-color: white; padding: 20px; border-radius: 15px; border-left: 8px solid {color}; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
                    <small style="color: gray;">{row['Ticker']}</small>
                    <h2 style="margin: 0;">{row['Price']:,.2f}</h2>
                    <b style="color: {color};">{row['Action']}</b>
                </div>
            """, unsafe_allow_html=True)

    st.divider()

    # --- 5. ส่วนวิเคราะห์กราฟ (แยกหมวดหมู่ชัดเจน) ---
    st.subheader("🔍 วิเคราะห์กราฟรายตัว")
    
    # สร้างรายการเลือกหุ้นแบบมีหัวข้อหมวดหมู่
    select_list = []
    for cat, stocks in stock_categories.items():
        select_list.append(f"--- {cat} ---")
        select_list.extend(stocks)
    
    choice = st.selectbox("เลือกหุ้นที่คุณต้องการดู:", select_list)

    if not choice.startswith("---"):
        selected_stock = choice
        df_plot = yf.download(selected_stock, period="2y" if interval_code=="1d" else "60d", interval=interval_code, auto_adjust=True, progress=False)
        if isinstance(df_plot.columns, pd.MultiIndex): df_plot.columns = df_plot.columns.get_level_values(0)
        df_plot = calculate_indicators(df_plot)

        # สร้างกราฟสวยๆ
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        
        # กราฟแท่งเทียน
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='ราคา'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='เส้นแนวโน้ม SMA200', line=dict(color='#FF6F00', width=2)), row=1, col=1)
        
        # กราฟ RSI
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI (14)', line=dict(color='#7B1FA2', width=1.5)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#E57373", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#81C784", row=2, col=1)

        # ปรับแต่ง Layout
        fig.update_layout(
            title=f"<b>วิเคราะห์หุ้น: {selected_stock} ({selected_interval})</b>",
            title_font_size=24,
            title_x=0.5,
            height=650,
            template="plotly_white",
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=60, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

else:
    st.info("🔄 กำลังเตรียมข้อมูลตลาด... หากรอนานเกินไปโปรดลองเลือกหน่วยเวลาเป็น '1 วัน'")
