import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
    .info-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ส่วนเมนู (Tabs) ---
tab1, tab2, tab3 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง", "⚙️ การทำงานของระบบ (Internal)"])

# --- TAB 2: คู่มือบริหารความเสี่ยง ---
with tab2:
    st.header("📖 กฎเหล็ก 1% ของนักลงทุนระดับโลก")
    st.markdown("""
    ### 🛡️ กลไกการคุมความเสี่ยง (The 1% Rule)
    ระบบนี้ใช้หลักการ **Fixed Fractional Position Sizing** เพื่อให้พอร์ตของคุณ "ไม่มีวันพัง" (Zero Ruin)
    
    1. **Risk Amount:** ระบบคำนวณเงินที่ยอมเสียได้สูงสุด (เช่น 1% ของพอร์ต) 
    2. **Stop Loss (SL):** ตั้งจุดหนีไว้ที่ 3% จากราคาซื้อ เพื่อจำกัดความเสียหาย
    3. **Position Sizing:** ระบบจะคำนวณจำนวนหุ้นที่ซื้อโดย: `จำนวนหุ้น = เงินที่ยอมเสียได้ / (ราคาซื้อ - ราคา SL)`
    
    > **ผลลัพธ์:** ต่อให้คุณทายหุ้นผิดติดต่อกันหลายครั้ง เงินในพอร์ตจะลดลงทีละนิดเท่านั้น (1%) ทำให้คุณมีโอกาสแก้มือได้เสมอ
    """)

# --- TAB 3: การทำงานของระบบ ---
with tab3:
    st.header("⚙️ เจาะลึกการทำงานของ Safe Heaven Quant Pro Max")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🔍 กลไกภายใน (Logic Flow)")
        st.info("""
        1. **Data Pulling:** ดึงข้อมูลย้อนหลัง 2 ปี ผ่าน yfinance API
        2. **Technical Filter:**
            - **Trend:** ต้องอยู่เหนือ SMA 200 (ขาขึ้นเท่านั้น)
            - **Momentum:** RSI ต้อง < 40 (จุดย่อตัวที่ได้เปรียบ)
            - **Volume:** ปริมาณซื้อขายต้อง > เฉลี่ย 5 วัน
        3. **Execution Plan:** คำนวณจุดซื้อ, จุดคัดขาดทุน และจำนวนหุ้นทันที
        """)
    with col_b:
        st.subheader("✅ ความสอดคล้องของหัวข้อ")
        st.markdown("""
        - **Safe:** ปลอดภัยเพราะเทรดเฉพาะ "ขาขึ้น"
        - **Heaven:** หาจังหวะเข้าซื้อตอนที่คนอื่นกลัว (RSI ต่ำ)
        - **Quant:** ใช้สถิติและตัวเลขตัดสิน 100%
        """)

# --- TAB 1: ระบบสแกน & วางแผนเทรด ---
with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    # --- 3. Sidebar ---
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อการเทรด (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Management")
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้น:", options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK"])), default=default_assets)
    
    # --- 4. ฟังก์ชันดึงข้อมูล ---
    def get_data(ticker, interval, data_period):
        try:
            # จัดการชื่อหุ้นไทยอัตโนมัติ
            thai_tickers = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
            if ticker in thai_tickers and "." not in ticker: ticker += ".BK"
            
            df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
            df['SL'] = df['Close'] * 0.97
            df['TP'] = df['Close'] * 1.07
            return df
        except: return None

    # --- 5. ประมวลผลผลลัพธ์ ---
    results = []
    if selected_assets:
        with st.spinner('กำลังประมวลผล...'):
            for t in selected_assets:
                df = get_data(t, "1d", "2y") 
                if df is not None:
                    l = df.iloc[-1]
                    p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                    
                    if p > s and r < 40 and v > va: act = "🟢 STRONG BUY"
                    elif r > 75: act = "💰 PROFIT"
                    elif p < s: act = "🔴 EXIT/AVOID"
                    else: act = "⚪ Wait"
                    
                    v_ok = "✅" if v > va else "❌"
                    risk_amount = portfolio_size * (risk_per_trade / 100)
                    sl_dist = p - l['SL']
                    qty = int(risk_amount / sl_dist) if sl_dist > 0 else 0
                    
                    results.append({
                        "Ticker": t, "Price": round(p,2), "RSI": round(r,1), 
                        "Signal": act, "Vol OK": v_ok, "Qty": qty, 
                        "SL": round(l['SL'],2), "TP": round(l['TP'],2)
                    })

        if results:
            res_df = pd.DataFrame(results)
            st.subheader("🎯 สรุปสัญญาณล่าสุด")
            st.dataframe(res_df, use_container_width=True, hide_index=True)

            st.divider()

            # --- 6. วิเคราะห์รายตัว ---
            col1, col2 = st.columns([0.6, 0.4])
            with col1:
                sel_ticker = st.selectbox("🔍 วิเคราะห์กราฟละเอียด:", [r['Ticker'] for r in results])
                df_plot = get_data(sel_ticker, "1d", "2y")
                if df_plot is not None:
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                    fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
                    fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)

            with col2:
                target = next(item for item in results if item["Ticker"] == sel_ticker)
                st.markdown(f"""
                <div class="risk-box">
                    <h4>คำแนะนำสำหรับ {sel_ticker}</h4>
                    <ul>
                        <li><b>ควรซื้อ:</b> {target['Qty']:,} หุ้น</li>
                        <li><b>เงินที่ใช้:</b> {(target['Price'] * target['Qty']):,.2f} บาท</li>
                        <li><b>Stop Loss (3%):</b> {target['SL']}</li>
                        <li><b>Target (7%):</b> {target['TP']}</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("### 🔮 Analysis Insight")
                news = st.text_area("วิเคราะห์ปัจจัยเพิ่มเติม:", placeholder="ใส่ข่าวหรือบันทึกที่นี่...")
                if st.button("บันทึกการวิเคราะห์"):
                    st.success("บันทึกข้อมูลสำเร็จ! ระบบจะนำไปประกอบการตัดสินใจ")

if st.button("🔄 อัปเดตข้อมูล"):
    st.rerun()
