import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")

# CSS ตกแต่งเมนูคู่มือและหน้าจอ
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .guide-section { 
        background-color: #1e222d; 
        padding: 25px; 
        border-radius: 15px; 
        margin-bottom: 20px; 
        border: 1px solid #30363d; 
    }
    h2, h3 { color: #58a6ff; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. การสร้าง Tabs ---
tab1, tab2 = st.tabs(["📊 ระบบสแกนและกราฟ", "📖 คู่มือการทำงานของระบบ"])

with tab2:
    st.header("📖 เจาะลึกการทำงานของ Safe Heaven Scanner")
    
    # ส่วนที่ 1: การนำเข้าข้อมูล
    with st.container():
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
        st.subheader("🏗️ 1. ส่วนการนำเข้าข้อมูล (Data Fetching)")
        st.write("ส่วนนี้เปรียบเสมือน **'ท่อน้ำเลี้ยง'** ของโปรแกรมครับ เราใช้ไลบรารีที่ชื่อว่า `yfinance` เพื่อดึงข้อมูลราคาหุ้นจาก Yahoo Finance ทั่วโลก")
        st.markdown("""
        * **Ticker:** คือชื่อย่อหุ้น (เช่น BTC-USD, PTT.BK)
        * **Period & Interval:** โปรแกรมจะสั่งให้ไปดึงข้อมูลย้อนหลัง 2 ปี (2y) เพื่อให้มีข้อมูลเพียงพอสำหรับการคำนวณเส้นค่าเฉลี่ย 200 วัน
        * **Auto Adjust:** เราสั่งให้ปรับราคา (Adjusted Close) อัตโนมัติ เพื่อให้ราคาที่ได้มาสะท้อนมูลค่าจริงหลังการปันผลหรือแตกหุ้นแล้ว
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    # ส่วนที่ 2: สมองกล
    with st.container():
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
        st.subheader("🧬 2. ส่วนสมองกล (Indicators Calculation)")
        st.write("เมื่อได้ตัวเลขราคาดิบๆ มาแล้ว โปรแกรมจะนำมาเข้าสูตรทางคณิตศาสตร์ 2 สูตรที่เรากำหนดไว้:")
        st.markdown("""
        * **SMA 200 (Simple Moving Average):** คือการเอาราคาปิดย้อนหลัง 200 วันมาบวกกันแล้วหาร 200 เพื่อดู **"แนวโน้มระยะยาว"**
        * **RSI (Relative Strength Index):** เป็นสูตรวัด **"แรงแกว่ง"** ของราคา โดยเทียบแรงซื้อกับแรงขายในรอบ 14 วัน (14 แท่งเทียน) เพื่อดูว่าหุ้นตอนนี้ **"ถูกเกินไป"** หรือ **"แพงเกินไป"**
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    # ส่วนที่ 3: ตรรกะการตัดสินใจ (Trading Logic)
    with st.container():
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
        st.subheader("🎯 3. ส่วนตรรกะการตัดสินใจ (Trading Logic)")
        st.write("นี่คือหัวใจของกลยุทธ์ **Safe Heaven** ที่เราเขียนไว้ ซึ่งโปรแกรมจะอ่านค่าและตัดสินใจตามเงื่อนไข (If-Else) ดังนี้:")
        
        st.markdown("""
        | เงื่อนไข (Condition) | คำแนะนำ (Action) | ความหมาย |
        | :--- | :--- | :--- |
        | **ราคา > SMA 200** และ **RSI < 40** | 🟢 **STRONG BUY** | หุ้นเป็นขาขึ้น แต่เพิ่งย่อตัวลงมาจน **"ถูก"** |
        | **RSI > 75** | 💰 **PROFIT** | ราคาขึ้นมาแรงเกินไปแล้ว (Overbought) **ควรขาย** |
        | **ราคา < SMA 200** | 🔴 **EXIT/AVOID** | หุ้นหลุดแนวโน้มขาขึ้น กลายเป็นขาลง **ห้ามถือ** |
        | อื่นๆ | **WAIT** | รอจังหวะที่เหมาะสม **ยังไม่มีสัญญาณ** |
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    # ส่วนที่ 4: การแสดงผล
    with st.container():
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
        st.subheader("🎨 4. ส่วนการแสดงผล (Frontend/UI)")
        st.write("เราใช้ Streamlit และ Plotly ในการวาดภาพออกมาให้คุณเห็น:")
        st.markdown("""
        * **Streamlit (Layout):** จัดวางกล่องข้อมูล (Metric Cards) และตัวเลือก (Sidebar) ให้ดูง่าย
        * **Plotly (Interactive Graph):** วาดแท่งเทียนสีเขียว-แดง และเส้น Indicator ต่างๆ แบบที่คุณสามารถซูมเข้า-ออก หรือเอาเมาส์ไปชี้เพื่อดูราคาในแต่ละวันได้
        * **CSS Style:** เราใส่คำสั่งตกแต่งเพื่อให้พื้นหลังเป็น Dark Mode และเปลี่ยนสีปุ่มให้โดดเด่นเหมือนแอปเทรดมืออาชีพ
        """)
        st.info("💡 **สรุปภาพรวม:** โปรแกรมจะทำงานเป็นวงจรคือ: **ดึงข้อมูล (Fetch) ➡️ คำนวณ (Calc) ➡️ ตัดสินใจ (Logic) ➡️ วาดรูป (Show)** วนไปเรื่อยๆ")
        st.markdown('</div>', unsafe_allow_html=True)

with tab1:
    st.title("🛡️ Safe Heaven Quant Scanner")
    
    # รายชื่อหุ้นแยกหมวดหมู่
    stock_categories = {
        "🌍 Global Indices": ["^GSPC", "^SET50.BK", "GC=F"],
        "💻 Tech Giants": ["NVDA", "AAPL", "TSLA", "MSFT"],
        "₿ Crypto": ["BTC-USD", "ETH-USD"],
        "🇹🇭 Thai Stocks": ["PTT.BK", "AOT.BK", "SCB.BK", "KBANK.BK"]
    }
    all_list = [s for cat in stock_categories.values() for s in cat]
    
    st.sidebar.header("⏱️ Settings")
    itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
    itv_label = st.sidebar.selectbox("เลือกหน่วยเวลา:", list(itv_map.keys()), index=0)
    itv_code = itv_map[itv_label]
    
    def fetch_quant_data(ticker, interval):
        try:
            p = "2y" if interval == "1d" else "60d"
            df = yf.download(ticker, period=p, interval=interval, auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if len(df) < 200: return None
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            return df
        except: return None

    # สแกนตลาด
    st.subheader(f"🎯 รายการสแกนสัญญาณ ({itv_label})")
    results = []
    for t in all_list:
        data = fetch_quant_data(t, itv_code)
        if data is not None:
            l = data.iloc[-1]
            p, r, s = l['Close'], l['RSI'], l['SMA200']
            if p > s and r < 40: sig = "🟢 STRONG BUY"
            elif r > 75: sig = "💰 PROFIT"
            elif p < s: sig = "🔴 EXIT"
            else: sig = "WAIT"
            results.append({"หุ้น": t, "ราคา": f"{p:,.2f}", "RSI": round(r,1), "สัญญาณ": sig})
    
    if results:
        st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
    
    st.divider()
    
    # วิเคราะห์กราฟละเอียด
    selected_asset = st.selectbox("🔍 วิเคราะห์กราฟรายตัว:", all_list)
    plot_df = fetch_quant_data(selected_asset, itv_code)
    
    if plot_df is not None:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=plot_df.index, open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['RSI'], name='RSI', line=dict(color='#00ccff', width=1.5)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ff3366", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#00ffbb", row=2, col=1)
        fig.update_layout(height=650, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)
