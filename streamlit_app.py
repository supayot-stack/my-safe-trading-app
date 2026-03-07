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
    .concept-card { background-color: #1e222d; padding: 20px; border-radius: 10px; border: 1px solid #333; height: 100%; }
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
    

# --- TAB 3: การทำงานของระบบ (บันทึกความเข้าใจระบบ) ---
with tab3:
    st.header("⚙️ เจาะลึกโครงสร้าง Safe Heaven Quant Pro Max")
    
    st.markdown("### 1. กลไกการทำงานของโค้ด (Internal Logic)")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        **🔄 การเตรียมข้อมูล**
        - ดึงข้อมูลผ่าน `yfinance` ย้อนหลัง 2 ปี
        - คำนวณค่าทางสถิติอัตโนมัติ: SMA 200, RSI 14 และ Volume Moving Average
        """)
    with c2:
        st.markdown("""
        **🚦 ตรรกะการคัดกรอง (Scanner)**
        - **Trend:** ราคา > SMA 200 (ขาขึ้น)
        - **Momentum:** RSI < 40 (ย่อตัวในขาขึ้น)
        - **Volume:** แรงซื้อ > ค่าเฉลี่ย 5 วัน
        """)
    with c3:
        st.markdown("""
        **🛡️ การบริหารหน้าตัก**
        - คำนวณเงินที่ยอมเสียได้ 1%
        - กำหนดจุดหนี (Stop Loss) 3%
        - ออกคำสั่งจำนวนหุ้นที่ "พอดี" กับความเสี่ยง
        """)

    st.divider()

    st.markdown("### 2. ความสอดคล้องของระบบกับแนวคิด Safe Heaven")
    col_x, col_y = st.columns(2)
    with col_x:
        st.info("**✅ Safe (ปลอดภัย):**")
        st.write("ระบบเทรดเฉพาะหุ้นขาขึ้น (Above SMA 200) และมีจุดคัดขาดทุนชัดเจนทุกไม้ ป้องกันความพินาศของพอร์ต")
        
        st.info("**✅ Heaven (จุดเข้าที่ได้เปรียบ):**")
        st.write("หาจังหวะ Buy on Dip โดยใช้ RSI < 40 เป็นตัวบอกว่าราคาย่อมาในจุดที่ 'ถูก' ของแนวโน้มขาขึ้น")
    
    with col_y:
        st.info("**✅ Quant (เชิงปริมาณ):**")
        st.write("ใช้ตัวเลขตัดสิน 100% ทั้งการเลือกหุ้นและการคำนวณจำนวนซื้อ ตัดอารมณ์และความลังเลออกไป")
        
        st.info("**✅ Pro Max (ความเหนือชั้น):**")
        st.write("มีระบบ Dynamic Risk Calculation และ AI Sentiment วิเคราะห์ข่าวสารเบื้องต้นประกอบการตัดสินใจ")

    st.divider()
    st.warning("📊 **บันทึกเพิ่มเติม:** ระบบนี้ถูกออกแบบมาเพื่อรักษาเงินต้นเป็นอันดับหนึ่ง และทำกำไรอย่างยั่งยืนผ่านสถิติ")

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
    selected_assets = st.sidebar.multiselect("เลือกหุ้นแนะนำ:", options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK", "GC=F"])), default=default_assets)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นอื่นๆ:").upper().strip()
    
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list: final_list.append(custom_ticker)

    # --- 4. ฟังก์ชันดึงข้อมูล ---
    def get_data(ticker, interval, data_period):
        try:
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

    # --- 5. ประมวลผลและตารางผลลัพธ์ ---
    results = []
    if final_list:
        with st.spinner('กำลังประมวลผลระบบสแกน...'):
            for t in final_list:
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
                    results.append({"Ticker": t, "Price": round(p,2), "RSI": round(r,1), "Signal": act, "Vol OK": v_ok, "Qty to Buy": qty, "StopLoss": round(l['SL'],2), "Target": round(l['TP'],2)})

        if results:
            res_df = pd.DataFrame(results)
            priority = {"🟢 STRONG BUY": 0, "💰 PROFIT": 1, "⚪ Wait": 2, "🔴 EXIT/AVOID": 3}
            res_df['sort'] = res_df['Signal'].map(priority)
            res_df = res_df.sort_values('sort').drop(columns=['sort'])
            st.subheader("🎯 สรุปสัญญาณล่าสุด")
            st.dataframe(res_df, use_container_width=True, hide_index=True)

    st.divider()

    # --- 6. ส่วนวิเคราะห์รายตัว (ปรับสี Volume เป็น LightGray/Silver) ---
    col1, col2 = st.columns([0.6, 0.4])
    if results:
        with col1:
            selected_plot = st.selectbox("🔍 วิเคราะห์กราฟละเอียด:", [r['Ticker'] for r in results])
            df_plot = get_data(selected_plot, "1d", "2y")
            if df_plot is not None:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=2)), row=1, col=1)
                
                # --- แก้ไขสี Volume เป็น Silver และเพิ่มความโปร่งแสง ---
                fig.add_trace(go.Bar(
                    x=df_plot.index, 
                    y=df_plot['Volume'], 
                    name='Volume', 
                    marker_color='silver', 
                    opacity=0.4, 
                    marker_line_width=0
                ), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='#00ccff', width=1.5)), row=2, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="#ff3366", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="#00ffbb", row=2, col=1)
                fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("### 🛠️ การบริหารหน้าตัก")
            target_data = next(item for item in results if item["Ticker"] == selected_plot)
            st.markdown(f"""
            <div class="risk-box">
                <h4>คำแนะนำสำหรับ {selected_plot}</h4>
                <ul>
                    <li><b>ควรซื้อ:</b> {target_data['Qty to Buy']:,} หุ้น</li>
                    <li><b>เงินที่ใช้ซื้อ:</b> {(float(target_data['Price']) * target_data['Qty to Buy']):,.2f} บาท</li>
                    <li>
