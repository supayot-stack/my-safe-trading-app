import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .guide-box { background-color: #1e222d; padding: 20px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ส่วนเมนู (Tabs) ---
tab1, tab2 = st.tabs(["📊 ระบบสแกนและกราฟ", "📖 คู่มือการใช้งานสำหรับมือใหม่"])

with tab2:
    st.header("📖 คู่มือการใช้งาน Safe Heaven Scanner")
    
    st.markdown("""
    ### 🛡️ กลยุทธ์นี้คืออะไร?
    กลยุทธ์นี้เน้นการ **"ซื้อเมื่อย่อในขาขึ้น"** และ **"หนีเมื่อเป็นขาลง"** โดยใช้เครื่องมือหลัก 2 ตัว:
    
    1. **เส้น SMA 200 (แนวโน้มระยะยาว):** * ถ้าราคา **อยู่เหนือ** เส้นนี้ = ขาขึ้น (ปลอดภัยที่จะเล่น)
        * ถ้าราคา **อยู่ใต้** เส้นนี้ = ขาลง (อันตราย ห้ามถือ)
    
    2. **RSI 14 (แรงแกว่ง):** * ใช้ดูว่าหุ้น "ถูก" หรือ "แพง" เกินไปในขณะนั้น
    """)

    

    st.markdown("""
    ---
    ### 🚦 วิธีอ่านสัญญาณ (Trading Signals)
    * 🟢 **STRONG BUY:** ราคาอยู่เหนือเส้น SMA 200 (ขาขึ้นชัดเจน) แต่ RSI ต่ำกว่า 40 (ราคาเพิ่งย่อตัวลงมา เป็นจุดซื้อที่ได้เปรียบ)
    * 💰 **TAKE PROFIT:** RSI สูงกว่า 75 แปลว่าราคาขึ้นแรงเกินไปแล้ว มีโอกาสย่อตัวสูง ควรพิจารณาขายทำกำไร
    * 🔴 **EXIT/AVOID:** ราคาหลุดเส้น SMA 200 ลงมา แปลว่าเปลี่ยนเป็นขาลงแล้ว ให้ขายออกทันทีเพื่อรักษาเงินต้น
    * ⚪ **WAIT:** สัญญาณยังไม่ชัดเจน ให้ถือเงินสดรอไปก่อน
    
    ---
    ### ⚙️ การตั้งค่าหน่วยเวลา (Timeframe)
    * **1 วัน (1d):** สำหรับนักลงทุนระยะกลาง-ยาว (ถือหลักสัปดาห์/เดือน) แม่นยำที่สุด
    * **1 ชั่วโมง / 5 นาที:** สำหรับนักเก็งกำไรระยะสั้น (Day Trade) สัญญาณจะมาไวแต่มีความเสี่ยงผันผวนสูง
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Scanner")
    
    # (ส่วนโค้ดการทำงานเดิมที่คุณชอบ)
    stock_categories = {
        "🌍 Indices": ["^GSPC", "^SET50.BK", "GC=F"],
        "💻 Tech": ["NVDA", "AAPL", "TSLA", "MSFT"],
        "₿ Crypto": ["BTC-USD", "ETH-USD"],
        "🇹🇭 Thai": ["PTT.BK", "AOT.BK", "KBANK.BK"]
    }
    
    all_assets = [s for cat in stock_categories.values() for s in cat]
    
    st.sidebar.header("⏱️ Settings")
    itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
    itv = st.sidebar.selectbox("หน่วยเวลา:", list(itv_map.keys()), index=0)
    
    # ฟังก์ชันคำนวณและดึงข้อมูล
    def get_data(ticker, interval):
        try:
            df = yf.download(ticker, period="2y" if interval=="1d" else "60d", interval=interval, auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            if len(df) < 200: return None
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            return df
        except: return None

    # สแกนหาตัวที่มีสัญญาณ
    results = []
    for t in all_assets:
        df = get_data(t, itv_map[itv])
        if df is not None:
            last = df.iloc[-1]
            p, r, s = last['Close'], last['RSI'], last['SMA200']
            if p > s and r < 40: act, col = "STRONG BUY", "#00ffbb"
            elif r > 75: act, col = "PROFIT", "#ffcc00"
            elif p < s: act, col = "EXIT", "#ff3366"
            else: act, col = "Wait", "#787b86"
            results.append({"Ticker": t, "Price": f"{p:,.2f}", "RSI": round(r,1), "Signal": act, "Color": col})
    
    if results:
        res_df = pd.DataFrame(results)
        st.subheader(f"🎯 รายการสแกนปัจจุบัน ({itv})")
        st.dataframe(res_df.drop(columns=['Color']), use_container_width=True, hide_index=True)
        
        st.divider()
        selected = st.selectbox("🔍 เลือกดูวิเคราะห์กราฟ:", all_assets)
        df_plot = get_data(selected, itv_map[itv])
        
        if df_plot is not None:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='#00ccff', width=1.5)), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="#ff3366", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#00ffbb", row=2, col=1)
            fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig, use_container_width=True)
