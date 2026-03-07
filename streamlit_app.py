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
    เน้นการ **"ซื้อเมื่อย่อในขาขึ้น"** โดยใช้ SMA 200 ยืนยันแนวโน้ม และ RSI 14 ดูจุดเข้าซื้อที่ได้เปรียบ
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Scanner")

    # --- ส่วนการจัดการรายชื่อหุ้น (Add/Remove) ---
    st.sidebar.header("🔍 Asset Management")
    
    # หุ้นแนะนำ (Top 5 / Popular)
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    
    # ส่วนเลือกหุ้นจากรายการหรือลบออก
    selected_assets = st.sidebar.multiselect(
        "เลือกหุ้นจากรายการแนะนำ:",
        options=default_assets + ["MSFT", "GOOGL", "ETH-USD", "PTT.BK", "CPALL.BK"],
        default=default_assets
    )

    # ส่วนพิมพ์เพิ่มเอง (Add Custom Ticker)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มชื่อหุ้นอื่นๆ (เช่น META, GC=F):").upper()
    
    # รวมรายชื่อหุ้นทั้งหมด
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list:
        final_list.append(custom_ticker)

    st.sidebar.divider()
    
    # --- Settings ---
    st.sidebar.header("⏱️ Settings")
    itv_map = {"1 วัน": "1d", "1 ชั่วโมง": "1h", "5 นาที": "5m"}
    itv = st.sidebar.selectbox("หน่วยเวลา:", list(itv_map.keys()), index=0)

    # ฟังก์ชันดึงข้อมูล (เหมือนเดิมแต่ปรับปรุง error handling)
    def get_data(ticker, interval):
        try:
            # แก้ไข ticker สำหรับตลาดไทยถ้าลืมใส่ .BK
            if any(thai_stock in ticker for thai_stock in ["PTT", "AOT", "KBANK", "CPALL"]) and "." not in ticker:
                ticker += ".BK"
                
            df = yf.download(ticker, period="2y" if interval=="1d" else "60d", interval=interval, auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            
            # จัดการ Column MultiIndex (yfinance version ใหม่ๆ)
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            return df
        except:
            return None

    # --- การสแกน ---
    results = []
    if not final_list:
        st.warning("⚠️ กรุณาเลือกหรือเพิ่มหุ้นอย่างน้อย 1 ตัวในแถบด้านซ้าย")
    else:
        with st.spinner('กำลังประมวลผลข้อมูล...'):
            for t in final_list:
                df = get_data(t, itv_map[itv])
                if df is not None:
                    last = df.iloc[-1]
                    p, r, s = last['Close'], last['RSI'], last['SMA200']
                    
                    if p > s and r < 40: act, col = "🟢 STRONG BUY", "#00ffbb"
                    elif r > 75: act, col = "💰 PROFIT", "#ffcc00"
                    elif p < s: act, col = "🔴 EXIT/AVOID", "#ff3366"
                    else: act, col = "⚪ Wait", "#787b86"
                    
                    results.append({"Ticker": t, "Price": f"{p:,.2f}", "RSI": round(r,1), "Signal": act})

        if results:
            res_df = pd.DataFrame(results)
            st.subheader(f"🎯 รายการสแกนปัจจุบัน ({itv})")
            st.dataframe(res_df, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # เลือกหุ้นเพื่อดูกราฟ (เฉพาะจากที่มีข้อมูล)
            analyzable_assets = [r['Ticker'] for r in results]
            selected_plot = st.selectbox("🔍 เลือกดูวิเคราะห์กราฟเทคนิค:", analyzable_assets)
            
            df_plot = get_data(selected_plot, itv_map[itv])
            if df_plot is not None:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                
                # กราฟราคา & SMA200
                fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=2)), row=1, col=1)
                
                # กราฟ RSI
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='#00ccff', width=1.5)), row=2, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="#ff3366", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="#00ffbb", row=2, col=1)
                
                fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig, use_container_width=True)
