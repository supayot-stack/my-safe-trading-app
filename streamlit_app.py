import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Pro", layout="wide")
st.title("🛡️ Safe Heaven Scanner (Smart Dashboard)")

# --- 2. แถบเมนูด้านข้าง ---
st.sidebar.header("⚙️ Settings")

# กำหนดหมวดหมู่หุ้นให้เลือกง่ายๆ
stock_categories = {
    "🌍 Market Indices": ["^GSPC", "^SET50.BK", "GC=F"],
    "💻 Technology": ["NVDA", "AAPL", "MSFT", "GOOGL", "TSLA"],
    "💰 Crypto": ["BTC-USD", "ETH-USD", "BNB-USD"],
    "🇹🇭 Thai Stocks": ["PTT.BK", "AOT.BK", "CPALL.BK", "KBANK.BK"]
}

# รวมหุ้นทั้งหมดเพื่อใช้ในการดึงข้อมูล
all_assets = []
for stocks in stock_categories.values():
    all_assets.extend(stocks)

# เลือกหน่วยเวลา
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
            df = yf.download(ticker, period=period, interval=interval, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if df.empty or len(df) < 200: continue
            df = calculate_indicators(df)
            last = df.iloc[-1]
            last_price, rsi_val, sma_val = float(last['Close']), float(last['RSI']), float(last['SMA200'])
            
            if last_price > sma_val and rsi_val < 40: action = "🟢 BUY"
            elif rsi_val > 75: action = "💰 PROFIT"
            elif last_price < sma_val: action = "🔴 EXIT"
            else: action = "Wait"
                
            results.append({"Ticker": ticker, "Price": f"{last_price:,.2f}", "RSI": round(rsi_val, 2), "Action": action})
        except: continue
    return pd.DataFrame(results)

# --- 4. การแสดงผล ---
summary_df = fetch_data(all_assets, interval_code)

if not summary_df.empty:
    st.subheader(f"🚀 สรุปสัญญาณล่าสุด ({selected_interval})")
    
    # แสดง Card ราคา (เลือกเฉพาะตัวที่มีสัญญาณน่าสนใจมาโชว์)
    display_df = summary_df[summary_df['Action'] != "Wait"].head(4)
    if display_df.empty: display_df = summary_df.head(4)
    
    cols = st.columns(len(display_df))
    for i, (idx, row) in enumerate(display_df.iterrows()):
        with cols[i]:
            bg = "#28a745" if "BUY" in row['Action'] else "#dc3545" if "EXIT" in row['Action'] else "#ffc107" if "PROFIT" in row['Action'] else "#ffffff"
            st.markdown(f"""<div style="background-color:{bg};padding:15px;border-radius:10px;text-align:center;color:white if {bg}!='#ffffff' else black;">
                <b style="font-size:18px;">{row['Ticker']}</b><br><span style="font-size:24px;">{row['Price']}</span><br><b>{row['Action']}</b></div>""", unsafe_allow_html=True)

    st.divider()

    # --- ส่วนการเลือกกราฟแบบจัดหมวดหมู่ ---
    st.subheader("📊 วิเคราะห์กราฟเทคนิคัล")
    
    # สร้างลิสต์รายการแบบมีหมวดหมู่
    formatted_options = []
    for cat, stocks in stock_categories.items():
        formatted_options.append(f"--- {cat} ---")
        formatted_options.extend(stocks)
    
    selected_display = st.selectbox("🔍 เลือกหุ้นที่ต้องการดูข้อมูล:", formatted_options)
    
    # กรองเอาเฉพาะชื่อหุ้น (ตัดชื่อหมวดหมู่ที่ขึ้นต้นด้วย --- ออก)
    if selected_display.startswith("---"):
        st.info("กรุณาเลือกชื่อหุ้นที่อยู่ใต้หมวดหมู่")
    else:
        selected_stock = selected_display
        df_plot = yf.download(selected_stock, period="2y" if interval_code=="1d" else "60d", interval=interval_code, auto_adjust=True)
        if isinstance(df_plot.columns, pd.MultiIndex): df_plot.columns = df_plot.columns.get_level_values(0)
        df_plot = calculate_indicators(df_plot)

        # สร้างกราฟ
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        
        # เพิ่ม Candlestick และเส้น SMA
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='orange', width=2)), row=1, col=1)
        
        # เพิ่ม RSI
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='purple', width=1.5)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        # จัด Layout กราฟให้ดูสะอาดและแสดงชื่อหุ้นชัดๆ
        fig.update_layout(
            title=f"<b>{selected_stock}</b> - {selected_interval} Analysis",
            title_x=0.5,
            height=650,
            template="plotly_white",
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=50, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("🔄 กำลังโหลดข้อมูล... หรือลองเปลี่ยนหน่วยเวลาเป็น '1 วัน'")
