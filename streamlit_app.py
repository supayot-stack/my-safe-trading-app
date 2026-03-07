import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ (คงเดิม) ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
    .ai-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันดึงข้อมูล (Upgrade: Caching + ATR + Standard RSI) ---
@st.cache_data(ttl=3600)  # Cache ข้อมูล 1 ชั่วโมงเพื่อความรวดเร็ว
def get_data(ticker, interval="1d", data_period="2y"):
    try:
        thai_tickers = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
        if ticker in thai_tickers and "." not in ticker: ticker += ".BK"
        
        df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 1. SMA 200
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        # 2. Standard RSI (Wilder's Smoothing)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0))
        loss = (-delta.where(delta < 0, 0))
        avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
        df['RSI'] = 100 - (100 / (1 + (avg_gain / (avg_loss + 1e-9))))
        
        # 3. ATR (Average True Range) - สำหรับ Dynamic Stop Loss
        high_low = df['High'] - df['Low']
        high_cp = abs(df['High'] - df['Close'].shift())
        low_cp = abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        
        # 4. Dynamic Risk Management (Institutional Standard)
        # ใช้ 2xATR เป็นจุด Stop Loss (สะท้อนความผันผวนจริง)
        df['SL'] = df['Close'] - (df['ATR'] * 2) 
        # ใช้ Risk:Reward = 1:2
        df['TP'] = df['Close'] + ((df['Close'] - df['SL']) * 2)
        
        df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
        return df
    except: return None

# --- 3. ส่วนเมนู (คงเดิม) ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง (Pro)"])

with tab2:
    st.header("📖 กฎเหล็ก 1% และ ATR Stop Loss")
    st.markdown("""
    ### 🛡️ ทำไมต้องใช้ ATR (Average True Range)?
    การใช้จุด Stop Loss แบบ % คงที่ (เช่น 3%) อาจไม่เหมาะกับทุกหุ้น เพราะหุ้นแต่ละตัวผันผวนไม่เท่ากัน
    * **หุ้นซิ่ง (High Volatility):** ต้องวาง Stop Loss ให้กว้างขึ้นเพื่อไม่ให้โดน "สะบัดหลุด"
    * **หุ้นนิ่ง (Low Volatility):** วาง Stop Loss ให้แคบลงเพื่อเพิ่ม Position Size
    * *เราใช้ค่า 2xATR เพื่อเป็นเกราะป้องกันการแกว่งตัวปกติของราคา*
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max + ATR Engine")
    
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

    results = []
    if final_list:
        with st.spinner('กำลังคำนวณด้วย ATR Engine...'):
            for t in final_list:
                df = get_data(t) 
                if df is not None:
                    l = df.iloc[-1]
                    p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                    
                    # Logic สัญญาณเทรด
                    if p > s and r < 45 and v > va: act = "🟢 STRONG BUY"
                    elif r > 70: act = "💰 PROFIT"
                    elif p < s: act = "🔴 EXIT/AVOID"
                    else: act = "⚪ Wait"
                    
                    v_ok = "✅" if v > va else "❌"
                    
                    # Position Sizing จาก ATR Stop Loss
                    risk_amount = portfolio_size * (risk_per_trade / 100)
                    sl_dist = p - l['SL']
                    qty = int(risk_amount / sl_dist) if sl_dist > 0 else 0
                    
                    results.append({
                        "Ticker": t, "Price": round(p,2), "RSI": round(r,1), 
                        "Signal": act, "Vol OK": v_ok, "Qty to Buy": qty,
                        "ATR (Volat.)": round(l['ATR'], 2),
                        "StopLoss": round(l['SL'],2), "Target": round(l['TP'],2)
                    })

        if results:
            res_df = pd.DataFrame(results)
            priority = {"🟢 STRONG BUY": 0, "💰 PROFIT": 1, "⚪ Wait": 2, "🔴 EXIT/AVOID": 3}
            res_df['sort'] = res_df['Signal'].map(priority)
            res_df = res_df.sort_values('sort').drop(columns=['sort'])
            st.subheader("🎯 สรุปสัญญาณและแผนคุมความเสี่ยง (ATR Optimized)")
            st.dataframe(res_df, use_container_width=True, hide_index=True)

    st.divider()

    # --- ส่วนวิเคราะห์รายตัว (คงเดิมพร้อมปรับปรุงกราฟ) ---
    col1, col2 = st.columns([0.6, 0.4])
    
    if results:
        with col1:
            selected_plot = st.selectbox("🔍 วิเคราะห์กราฟละเอียด:", [r['Ticker'] for r in results])
            df_plot = get_data(selected_plot)
            if df_plot is not None:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=2)), row=1, col=1)
                
                # เพิ่มเส้น SL ในกราฟเพื่อให้เห็นภาพ
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Close'] - (df_plot['ATR']*2), name='ATR Stop', line=dict(color='rgba(255, 75, 75, 0.5)', dash='dot')), row=1, col=1)

                fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name='Volume', marker_color='#4A4A4A', opacity=0.4), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='#00ccff', width=1.5)), row=2, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="#ff3366", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="#00ffbb", row=2, col=1)
                
                fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("### 🛠️ เครื่องมือบริหารหน้าตัก")
            target_data = next(item for item in results if item["Ticker"] == selected_plot)
            
            st.markdown(f"""
            <div class="risk-box">
                <h4>คำแนะนำสำหรับ {selected_plot} (ATR Base)</h4>
                <p>คำนวณจากความผันผวน 14 วันล่าสุด</p>
                <ul>
                    <li><b>ความผันผวน (ATR):</b> {target_data['ATR (Volat.)']}</li>
                    <li><b>จำนวนหุ้นที่แนะนำ:</b> {target_data['Qty to Buy']:,} หุ้น</li>
                    <li><b>เงินที่ใช้ซื้อทั้งหมด:</b> {(float(target_data['Price']) * target_data['Qty to Buy']):,.2f} บาท</li>
                    <li><b>จุดหนี (2xATR):</b> {target_data['StopLoss']}</li>
                    <li><b>เป้าหมาย (RR 1:2):</b> {target_data['Target']}</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            # AI Section คงไว้ตามเดิม
            st.markdown("### 🔮 AI Future Insight")
            news_input = st.text_area("วิเคราะห์ข่าว/เหตุการณ์ปัจจุบัน:", placeholder="วางข่าวที่นี่...")
            if st.button("ประมวลผล AI"):
                if news_input:
                    pos_words = ["ดี", "โต", "เพิ่ม", "กำไร", "ชนะ", "บวก", "growth", "profit"]
                    neg_words = ["แย่", "ลด", "ขาดทุน", "สงคราม", "ลบ", "loss", "drop"]
                    score = sum(1 for w in pos_words if w in news_input) - sum(1 for w in neg_words if w in news_input)
                    if score > 0: st.success("📈 AI คาดการณ์: เชิงบวก")
                    elif score < 0: st.error("📉 AI คาดการณ์: เชิงลบ")
                    else: st.warning("⚪ AI คาดการณ์: เป็นกลาง")

if st.button("🔄 อัปเดตข้อมูล"): st.rerun()
