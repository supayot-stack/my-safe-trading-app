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
    
    1. **เส้น SMA 200 (แนวโน้ม):** * ถ้าราคา **อยู่เหนือ** เส้นนี้ = ขาขึ้น (ปลอดภัยที่จะเล่น)
        * ถ้าราคา **อยู่ใต้** เส้นนี้ = ขาลง (อันตราย ห้ามถือ)
    
    2. **RSI 14 (แรงแกว่ง):** * ใช้ดูว่าหุ้น "ถูก" หรือ "แพง" ในขณะนั้น (ต่ำกว่า 40 คือเริ่มถูก / สูงกว่า 75 คือแพงไป)
    """)

    st.markdown("""
    ---
    ### 🚦 วิธีอ่านสัญญาณ (Trading Signals)
    * 🟢 **STRONG BUY:** ราคา > SMA 200 (ขาขึ้น) + RSI < 40 (ย่อตัวลงมาเป็นจุดซื้อที่ได้เปรียบ)
    * 💰 **PROFIT:** RSI > 75 ราคาขึ้นแรงเกินไปแล้ว มีโอกาสย่อตัว ควรพิจารณาขายทำกำไร
    * 🔴 **EXIT/AVOID:** ราคา < SMA 200 แปลว่าเป็นขาลง ให้ขายออกทันทีเพื่อรักษาเงินต้น
    * ⚪ **WAIT:** สัญญาณยังไม่ชัดเจน ให้ถือเงินสดรอ
    
    ---
    ### ⚙️ หน่วยเวลา (Timeframe) กับความหมายของ SMA 200
    * **1 วัน:** SMA 200 คือแนวโน้ม **ระยะยาว (รายปี)** แม่นยำที่สุดสำหรับนักลงทุน
    * **1 ชั่วโมง / 15 นาที / 5 นาที:** SMA 200 จะเปลี่ยนเป็นแนวโน้ม **ระยะสั้น** ของช่วงเวลานั้นๆ เหมาะสำหรับนักเก็งกำไร
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Scanner")
    
    # --- 3. ส่วน Sidebar: การจัดการรายชื่อหุ้น (Asset Management) ---
    st.sidebar.header("🔍 Asset Management")
    
    # รายชื่อแนะนำเริ่มต้น (Top 5)
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    
    # เลือกหุ้นจากรายการหรือลบออก
    selected_assets = st.sidebar.multiselect(
        "เลือกหุ้นจากรายการแนะนำ:",
        options=list(set(default_assets + ["MSFT", "GOOGL", "ETH-USD", "PTT.BK", "CPALL.BK", "GC=F"])),
        default=default_assets
    )

    # เพิ่มหุ้นเอง
    custom_ticker = st.sidebar.text_input("➕ เพิ่มชื่อหุ้นอื่นๆ (เช่น META, OR.BK):").upper().strip()
    
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list:
        final_list.append(custom_ticker)

    st.sidebar.divider()
    
    # --- 4. ส่วน Sidebar: การตั้งค่าหน่วยเวลาตามจริง (Real-time Settings) ---
    st.sidebar.header("⏱️ Timeframe Settings")
    
    # Mapping หน่วยเวลา และคำอธิบายให้ตรงกับการทำงานจริง
    timeframe_config = {
        "1 วัน (Daily)": {
            "iv": "1d", 
            "period": "2y", 
            "desc": "เหมาะสำหรับ: ลงทุนระยะกลาง-ยาว",
            "note": "SMA 200 = แนวโน้ม 200 วัน (หลัก)"
        },
        "1 ชั่วโมง (Hourly)": {
            "iv": "1h", 
            "period": "730d", 
            "desc": "เหมาะสำหรับ: เล่นรอบ (Swing Trade)",
            "note": "SMA 200 = แนวโน้ม ~1 เดือน"
        },
        "15 นาที (15m)": {
            "iv": "15m", 
            "period": "60d", 
            "desc": "เหมาะสำหรับ: เก็งกำไรรายวัน (Day Trade)",
            "note": "SMA 200 = แนวโน้ม ~4 วัน"
        },
        "5 นาที (5m)": {
            "iv": "5m", 
            "period": "60d", 
            "desc": "เหมาะสำหรับ: เทรดเร็ว (Scalping)",
            "note": "SMA 200 = แนวโน้ม ~1 วัน"
        }
    }
    
    selected_tf = st.sidebar.selectbox("เลือกหน่วยเวลา:", list(timeframe_config.keys()), index=0)
    conf = timeframe_config[selected_tf]
    
    st.sidebar.info(f"📋 **{conf['desc']}**\n\n🔍 {conf['note']}")

    # --- 5. ฟังก์ชันดึงข้อมูล (Error Handling & Optimized) ---
    def get_data(ticker, interval, data_period):
        try:
            # ตรวจสอบหุ้นไทย (Auto .BK)
            thai_stocks = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR"]
            if ticker in thai_stocks and "." not in ticker:
                ticker += ".BK"
                
            df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
            
            if df.empty or len(df) < 200: 
                return None
            
            if isinstance(df.columns, pd.MultiIndex): 
                df.columns = df.columns.get_level_values(0)
            
            # คำนวณ SMA 200
            df['SMA200'] = df['Close'].rolling(200).mean()
            
            # คำนวณ RSI 14
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            
            return df
        except:
            return None

    # --- 6. ส่วนประมวลผลการสแกน ---
    results = []
    if not final_list:
        st.warning("👈 กรุณาเลือกหรือเพิ่มรายชื่อหุ้นที่แถบด้านซ้าย")
    else:
        with st.spinner('กำลังประมวลผลข้อมูลล่าสุด...'):
            for t in final_list:
                df = get_data(t, conf['iv'], conf['period'])
                if df is not None:
                    last = df.iloc[-1]
                    p, r, s = last['Close'], last['RSI'], last['SMA200']
                    
                    if p > s and r < 40: act = "🟢 STRONG BUY"
                    elif r > 75: act = "💰 PROFIT"
                    elif p < s: act = "🔴 EXIT/AVOID"
                    else: act = "⚪ Wait"
                    
                    results.append({
                        "Ticker": t, 
                        "Price": f"{p:,.2f}", 
                        "RSI": round(r,1), 
                        "Signal": act
                    })

        if results:
            res_df = pd.DataFrame(results)
            # จัดลำดับ: STRONG BUY ขึ้นก่อน
            priority = {"🟢 STRONG BUY": 0, "💰 PROFIT": 1, "⚪ Wait": 2, "🔴 EXIT/AVOID": 3}
            res_df['sort'] = res_df['Signal'].map(priority)
            res_df = res_df.sort_values('sort').drop(columns=['sort'])
            
            st.subheader(f"🎯 รายการสแกนปัจจุบัน ({selected_tf})")
            st.dataframe(res_df, use_container_width=True, hide_index=True)
            
            st.divider()
            
            # --- 7. ส่วนวิเคราะห์กราฟเทคนิค ---
            analyzable = [r['Ticker'] for r in results]
            selected_plot = st.selectbox("🔍 เลือกดูวิเคราะห์กราฟเทคนิค:", analyzable)
            
            df_plot = get_data(selected_plot, conf['iv'], conf['period'])
            
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
        else:
            st.error("❌ ไม่พบข้อมูลหุ้น (ตรวจสอบชื่อหุ้น หรือข้อมูลไม่เพียงพอสำหรับ SMA 200)")

# บรรทัดสุดท้ายสามารถเพิ่มปุ่ม Refresh ได้ถ้าต้องการ
if st.button("🔄 อัปเดตข้อมูลทั้งหมด"):
    st.rerun()
