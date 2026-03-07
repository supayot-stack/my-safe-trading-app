import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max V.2", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
    .info-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ส่วนเมนู (Tabs) ---
tab1, tab2, tab3 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง (Dynamic)", "⚙️ การทำงานของระบบ (Internal)"])

with tab2:
    st.header("🛡️ กลไก Dynamic Stop Loss (ATR)")
    st.markdown("""
    ### 🌀 ATR คืออะไร?
    **Average True Range (ATR)** คือตัววัดความผันผวนของราคาหุ้นในช่วงที่ผ่านมา
    
    1. **Dynamic Risk:** ระบบจะไม่ใช้ 3% ตายตัว แต่จะใช้ **2 x ATR** เพื่อตั้งจุดหนี
    2. **Whipsaw Protection:** ช่วยป้องกันการโดนสะบัดหลุดในหุ้นที่ผันผวนสูง
    3. **Smart Sizing:** ถ้าหุ้นผันผวนมาก (ATR สูง) ระบบจะสั่งให้ซื้อหุ้นน้อยลงเพื่อคุมความเสี่ยงให้เท่าเดิม
    
    > **สรุป:** ยิ่งหุ้นซิ่ง จุดหนีจะยิ่งลึก และจำนวนหุ้นจะยิ่งน้อยลง เพื่อรักษาเงินต้น 1% ของพอร์ตไว้อย่างเคร่งครัด
    """)
    

with tab3:
    st.header("⚙️ ระบบภายใน Version 2.0 (ATR Enabled)")
    st.info("""
    **อัปเกรดล่าสุด:**
    - เปลี่ยนจาก Fixed Stop Loss (3%) เป็น **Dynamic Stop Loss (2x ATR)**
    - เพิ่มการแสดงค่า ATR ในตารางสแกน
    - ปรับปรุงการคำนวณ Position Sizing ให้สอดคล้องกับความผันผวนรายวัน
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max V.2")
    
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

    # --- 4. ฟังก์ชันดึงข้อมูล (เพิ่มการคำนวณ ATR) ---
    def get_data(ticker, interval, data_period):
        try:
            thai_tickers = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
            if ticker in thai_tickers and "." not in ticker: ticker += ".BK"
            df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            # Indicators พื้นฐาน
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
            
            # --- ส่วนคำนวณ ATR (Dynamic Stop Loss) ---
            high_low = df['High'] - df['Low']
            high_cp = abs(df['High'] - df['Close'].shift())
            low_cp = abs(df['Low'] - df['Close'].shift())
            df['TR'] = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
            df['ATR'] = df['TR'].rolling(14).mean()
            
            # ตั้ง SL ที่ 2x ATR และ TP ที่ 3x ATR (Risk:Reward Ratio 1:1.5)
            df['SL'] = df['Close'] - (df['ATR'] * 2)
            df['TP'] = df['Close'] + (df['ATR'] * 3)
            return df
        except: return None

    # --- 5. ประมวลผลและตารางผลลัพธ์ ---
    results = []
    if final_list:
        with st.spinner('กำลังคำนวณ Dynamic Plan...'):
            for t in final_list:
                df = get_data(t, "1d", "2y") 
                if df is not None:
                    l = df.iloc[-1]
                    p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                    atr = l['ATR']
                    
                    if p > s and r < 40 and v > va: act = "🟢 STRONG BUY"
                    elif r > 75: act = "💰 PROFIT"
                    elif p < s: act = "🔴 EXIT/AVOID"
                    else: act = "⚪ Wait"
                    
                    # คำนวณจำนวนหุ้นจากระยะ ATR (Dynamic Risk)
                    risk_amount = portfolio_size * (risk_per_trade / 100)
                    sl_dist = p - l['SL']
                    qty = int(risk_amount / sl_dist) if sl_dist > 0 else 0
                    
                    results.append({
                        "Ticker": t, "Price": round(p,2), "RSI": round(r,1), 
                        "Signal": act, "ATR": round(atr,2), "Qty": qty,
                        "StopLoss": round(l['SL'],2), "Target": round(l['TP'],2)
                    })

        if results:
            res_df = pd.DataFrame(results)
            priority = {"🟢 STRONG BUY": 0, "💰 PROFIT": 1, "⚪ Wait": 2, "🔴 EXIT/AVOID": 3}
            res_df['sort'] = res_df['Signal'].map(priority)
            res_df = res_df.sort_values('sort').drop(columns=['sort'])
            st.subheader("🎯 สรุปสัญญาณและ Dynamic Stop Loss")
            st.dataframe(res_df, use_container_width=True, hide_index=True)

    st.divider()

    # --- 6. รายตัว ---
    col1, col2 = st.columns([0.6, 0.4])
    if results:
        with col1:
            selected_plot = st.selectbox("🔍 วิเคราะห์กราฟละเอียด:", [r['Ticker'] for r in results])
            df_plot = get_data(selected_plot, "1d", "2y")
            if df_plot is not None:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=2)), row=1, col=1)
                fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name='Volume', marker_color='#4A4A4A', opacity=0.6), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='#00ccff', width=1.5)), row=2, col=1)
                fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("### 🛠️ การบริหารหน้าตัก (ATR Based)")
            target_data = next(item for item in results if item["Ticker"] == selected_plot)
            st.markdown(f"""
            <div class="risk-box">
                <h4>Dynamic Plan: {selected_plot}</h4>
                <ul>
                    <li><b>ATR (ความผันผวน):</b> {target_data['ATR']}</li>
                    <li><b>จำนวนหุ้นที่แนะนำ:</b> {target_data['Qty']:,} หุ้น</li>
                    <li><b>จุดหนี (2x ATR):</b> {target_data['StopLoss']}</li>
                    <li><b>เป้ากำไร (3x ATR):</b> {target_data['Target']}</li>
                    <li><b>ความเสียหายหากแพ้:</b> {(portfolio_size * risk_per_trade / 100):,.2f} บาท</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            st.caption("หมายเหตุ: ระยะ Stop Loss จะปรับเปลี่ยนทุกวันตามความผันผวนของราคา")

if st.button("🔄 อัปเดตข้อมูล"): st.rerun()
