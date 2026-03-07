import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import google.generativeai as genai
import os

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
    .ai-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ส่วนเมนู (Tabs) ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง (Pro)"])

with tab2:
    st.header("📖 กฎเหล็ก 1% ของนักลงทุนระดับโลก")
    st.markdown("""
    ### 🛡️ ทำอย่างไรให้ "ห้ามพัง" (Zero Ruin)
    1. **Never Bet All:** อย่าลงเงินทั้งหมดในหุ้นตัวเดียว
    2. **The 1% Rule:** ในแต่ละการเทรด ถ้าผิดทาง (Stop Loss) คุณควรเสียเงินไม่เกิน **1% ของเงินต้นทั้งหมด**
    3. **Position Sizing:** คำนวณจำนวนหุ้นที่จะซื้อจากระยะห่างของจุด Stop Loss
    
    ---
    ### 🚦 ตัวอย่างการคำนวณ
    * มีเงิน 100,000 บาท ยอมเสียได้ 1% = 1,000 บาท
    * ซื้อหุ้นราคา 100 บาท Stop Loss ที่ 97 บาท (ส่วนต่าง 3 บาท)
    * จำนวนหุ้นที่ซื้อได้ = 1,000 / 3 = **333 หุ้น**
    * *ผลลัพธ์:* ถ้าหุ้นตกไปที่ 97 บาท คุณจะเสียแค่ 1,000 บาท (พอร์ตเหลือ 99,000 ยังสู้ต่อได้สบาย)*
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max + Risk Manager")
    
    # --- 3. Sidebar: Settings & Portfolio ---
    st.sidebar.header("🔑 AI Settings")
    gemini_api_key = st.sidebar.text_input("ใส่ Gemini API Key:", type="password", help="รับฟรีได้ที่ Google AI Studio")
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)

    st.sidebar.divider()
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

    # --- 4. ฟังก์ชันดึงข้อมูล (Quantitative + Risk Calculations + ATR) ---
    @st.cache_data(ttl=3600) # Cache ข้อมูล 1 ชั่วโมงเพื่อความเร็ว
    def get_data(ticker, interval, data_period):
        try:
            # จัดการชื่อหุ้นไทยอัตโนมัติ
            thai_tickers = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
            if ticker in thai_tickers and "." not in ticker: ticker += ".BK"
            
            df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            # คำนวณอินดิเคเตอร์พื้นฐาน
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
            
            # 🚀 NEW: คำนวณ ATR (Average True Range) 14 วัน
            high_low = df['High'] - df['Low']
            high_close = (df['High'] - df['Close'].shift()).abs()
            low_close = (df['Low'] - df['Close'].shift()).abs()
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df['ATR'] = true_range.rolling(14).mean()
            
            # 🚀 NEW: Dynamic Stop Loss & Take Profit (Risk/Reward 1:2)
            df['SL'] = df['Close'] - (df['ATR'] * 1.5)
            df['TP'] = df['Close'] + (df['ATR'] * 3.0)
            
            return df
        except Exception: 
            return None

    # --- 5. ประมวลผลและตารางผลลัพธ์ ---
    results = []
    if final_list:
        with st.spinner('กำลังคำนวณแผนการเทรด...'):
            for t in final_list:
                df = get_data(t, "1d", "2y") 
                if df is not None:
                    l = df.iloc[-1]
                    p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                    
                    # ตรรกะสัญญาณ (Trend + Momentum + Volume)
                    # แก้ไข: เพิ่ม Buy on Dip (ราคาเหนือ SMA200 แต่ RSI ต่ำ)
                    if p > s and r < 40 and v > va: act = "🟢 STRONG BUY"
                    elif p > s and r < 40: act = "🟡 BUY ON DIP"
                    elif r > 75: act = "💰 PROFIT TAKING"
                    elif p < s: act = "🔴 AVOID"
                    else: act = "⚪ WAIT"
                    
                    # ยืนยันแรงซื้อ (Volume Confirmation)
                    v_ok = "✅" if v > va else "❌"
                    
                    # คำนวณจำนวนหุ้น (Position Sizing จาก ATR)
                    risk_amount = portfolio_size * (risk_per_trade / 100)
                    sl_dist = p - l['SL']
                    qty = int(risk_amount / sl_dist) if sl_dist > 0 else 0
                    
                    results.append({
                        "Ticker": t, "Price": round(p,2), "RSI": round(r,1), 
                        "Signal": act, "Vol OK": v_ok, "Qty to Buy": qty,
                        "StopLoss": round(l['SL'],2), "Target": round(l['TP'],2)
                    })

        if results:
            res_df = pd.DataFrame(results)
            priority = {"🟢 STRONG BUY": 0, "🟡 BUY ON DIP": 1, "💰 PROFIT TAKING": 2, "⚪ WAIT": 3, "🔴 AVOID": 4}
            res_df['sort'] = res_df['Signal'].map(priority)
            res_df = res_df.sort_values('sort').drop(columns=['sort'])
            st.subheader("🎯 สรุปสัญญาณและแผนคุมความเสี่ยง (ATR-Based)")
            st.dataframe(res_df, use_container_width=True, hide_index=True)

    st.divider()

    # --- 6. ส่วนวิเคราะห์รายตัว: กราฟ + AI + Risk Manager ---
    col1, col2 = st.columns([0.6, 0.4])
    
    if results:
        with col1:
            selected_plot = st.selectbox("🔍 วิเคราะห์กราฟละเอียด:", [r['Ticker'] for r in results])
            df_plot = get_data(selected_plot, "1d", "2y")
            if df_plot is not None:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                
                # กราฟราคา
                fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=2)), row=1, col=1)
                
                # ปรับสี Volume
                fig.add_trace(go.Bar(
                    x=df_plot.index, y=df_plot['Volume'], name='Volume', 
                    marker_color='#4A4A4A', opacity=0.6, marker_line_width=0
                ), row=1, col=1)
                
                # กราฟ RSI
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
                <h4>คำแนะนำสำหรับ {selected_plot}</h4>
                <p>กรณีเข้าซื้อที่ราคาปัจจุบัน ({target_data['Price']})</p>
                <ul>
                    <li><b>จำนวนหุ้นที่ซื้อได้ (เซฟโซน):</b> {target_data['Qty to Buy']:,} หุ้น</li>
                    <li><b>เงินที่ต้องใช้ทั้งหมด:</b> {(float(target_data['Price']) * target_data['Qty to Buy']):,.2f} บาท</li>
                    <li><b>จุดหนีอัตโนมัติ (ATR Stop Loss):</b> {target_data['StopLoss']}</li>
                    <li><b>เป้าทำกำไร (Take Profit 1:2):</b> {target_data['Target']}</li>
                    <li><b>ความเสียหายเต็มที่หากแพ้:</b> {(portfolio_size * risk_per_trade / 100):,.2f} บาท ({risk_per_trade}%)</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # --- AI Future Insight ---
            st.markdown("### 🧠 AI Future Insight (Powered by Gemini)")
            news_input = st.text_area("วิเคราะห์ข่าว/เหตุการณ์ปัจจุบัน:", placeholder="วางข่าวที่นี่ เช่น งบไตรมาส 3 โต 20% แต่ผู้บริหารลดเป้าปีหน้า...")
            
            if st.button("ประมวลผล AI แบบลึกซึ้ง"):
                if not gemini_api_key:
                    st.warning("⚠️ โปรดใส่ Gemini API Key ในแถบด้านซ้ายก่อนใช้งาน (รับฟรีที่ Google AI Studio)")
                elif news_input:
                    with st.spinner('AI กำลังวิเคราะห์ความเชื่อมโยงของข่าวกับตลาด...'):
                        try:
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            prompt = f"""
                            ในฐานะนักวิเคราะห์ Quant ระดับโลก จงประเมินข่าวต่อไปนี้ว่ามีผลกระทบต่อราคาหุ้นอย่างไร:
                            "{news_input}"
                            
                            ตอบกลับสั้นๆ 3 ข้อ:
                            1. ทิศทาง: (เชิงบวก / เชิงลบ / เป็นกลาง)
                            2. เหตุผล: (สรุปสั้นๆ ไม่เกิน 2 บรรทัด)
                            3. คำแนะนำการเทรด: (เช่น ควรตั้ง Stop loss ให้แคบลง หรือ ทยอยสะสม)
                            """
                            response = model.generate_content(prompt)
                            
                            st.markdown(f"""
                            <div class="ai-box">
                                <b>💡 ผลการวิเคราะห์จาก AI:</b><br>{response.text}
                            </div>
                            """, unsafe_allow_html=True)
                            
                        except Exception as e:
                            st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อ AI: โปรดตรวจสอบ API Key หรือลองอีกครั้ง")

if st.button("🔄 อัปเดตข้อมูล (Clear Cache)"): 
    st.cache_data.clear()
    st.rerun()
