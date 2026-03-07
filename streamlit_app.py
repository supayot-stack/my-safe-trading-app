import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTING & STYLE ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { 
        background-color: #2c3333; 
        padding: 20px; 
        border-radius: 12px; 
        border-left: 6px solid #ff4b4b; 
        margin-top: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. TABS ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง (Pro)"])

with tab2:
    st.header("📖 กฎเหล็ก 1% ของนักลงทุนระดับโลก")
    st.markdown("""
    ### 🛡️ กลไกการคุมความเสี่ยง (The 1% Rule)
    หัวใจสำคัญคือ **"ขาดทุนได้ แต่ห้ามพัง"**
    * **Risk Per Trade:** กำหนดว่าถ้าผิดทาง จะยอมเสียเงินไม่เกินกี่บาท (เช่น 1% ของพอร์ต)
    * **Position Sizing:** ซื้อจำนวนหุ้นให้สัมพันธ์กับจุด Stop Loss
    """)
    st.info("💡 สูตร: จำนวนหุ้น = (เงินต้น x %ความเสี่ยง) / (ราคาซื้อ - ราคา Stop Loss)")

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    # --- 3. SIDEBAR ---
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อการเทรด (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Management")
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้น:", options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK", "GC=F"])), default=default_assets)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นอื่นๆ (เช่น PTT, BTC-USD):").upper().strip()
    
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list:
        final_list.append(custom_ticker)

    # --- 4. DATA ENGINE ---
    def get_data(ticker, interval, data_period):
        try:
            # แปลงชื่อหุ้นไทย (ถ้าไม่มี .BK)
            thai_stocks = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB", "DELTA", "GULF"]
            if ticker in thai_stocks and "." not in ticker:
                ticker += ".BK"
            
            df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
            
            if df.empty or len(df) < 200:
                return None
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Indicators
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
            
            # Risk Management Lines
            df['SL'] = df['Close'] * 0.97
            df['TP'] = df['Close'] * 1.07
            return df
        except Exception as e:
            return None

    # --- 5. SCANNING & TABLE ---
    results = []
    if final_list:
        with st.spinner('กำลังประมวลผล Quantitative Data...'):
            for t in final_list:
                df = get_data(t, "1d", "2y") 
                if df is not None:
                    l = df.iloc[-1]
                    p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                    
                    if p > s and r < 40 and v > va: act = "🟢 STRONG BUY"
                    elif r > 75: act = "💰 PROFIT"
                    elif p < s: act = "🔴 EXIT/AVOID"
                    else: act = "⚪ Wait"
                    
                    risk_amount = portfolio_size * (risk_per_trade / 100)
                    sl_dist = p - l['SL']
                    qty = int(risk_amount / sl_dist) if sl_dist > 0 else 0
                    
                    results.append({
                        "Ticker": t, "Price": round(p,2), "RSI": round(r,1), 
                        "Signal": act, "Vol OK": "✅" if v > va else "❌", "Qty to Buy": qty,
                        "StopLoss": round(l['SL'],2), "Target": round(l['TP'],2)
                    })

        if results:
            res_df = pd.DataFrame(results)
            priority = {"🟢 STRONG BUY": 0, "💰 PROFIT": 1, "⚪ Wait": 2, "🔴 EXIT/AVOID": 3}
            res_df['sort'] = res_df['Signal'].map(priority)
            res_df = res_df.sort_values('sort').drop(columns=['sort'])
            st.subheader("🎯 สรุปสัญญาณล่าสุด")
            st.dataframe(res_df, use_container_width=True, hide_index=True)

    st.divider()

    # --- 6. VISUALIZATION & AI ---
    col1, col2 = st.columns([0.6, 0.4])
    if results:
        with col1:
            selected_plot = st.selectbox("🔍 วิเคราะห์กราฟละเอียด:", [r['Ticker'] for r in results])
            df_plot = get_data(selected_plot, "1d", "2y")
            if df_plot is not None:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                
                # Main Chart
                fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=2)), row=1, col=1)
                fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name='Volume', marker_color='#4A4A4A', opacity=0.5), row=1, col=1)
                
                # RSI Subplot
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='#00ccff', width=1.5)), row=2, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="#ff3366", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="#00ffbb", row=2, col=1)
                
                fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False, showlegend=False)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'scrollZoom': True})

        with col2:
            st.markdown("### 🛠️ Position Manager")
            target_data = next(item for item in results if item["Ticker"] == selected_plot)
            st.markdown(f"""
            <div class="risk-box">
                <h4>Recommendation for {selected_plot}</h4>
                <hr>
                <p>จำนวนหุ้นที่ควรซื้อ: <b>{target_data['Qty to Buy']:,}</b> หุ้น</p>
                <p>เงินทุนที่ใช้: <b>{(float(target_data['Price']) * target_data['Qty to Buy']):,.2f}</b> บาท</p>
                <p>Stop Loss (3%): <b style="color:#ff4b4b;">{target_data['StopLoss']}</b></p>
                <p>เป้าหมายกำไร (7%): <b style="color:#00ffbb;">{target_data['Target']}</b></p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("### 🔮 AI Future Insight")
            news_input = st.text_area("วิเคราะห์ข่าววันนี้:", placeholder="วางพาดหัวข่าวที่นี่...")
            if st.button("ประมวลผล AI"):
                if news_input:
                    pos = ["ดี", "โต", "กำไร", "ชนะ", "บวก", "growth", "profit"]
                    neg = ["แย่", "ลด", "ขาดทุน", "ลบ", "loss", "drop"]
                    score = sum(1 for w in pos if w in news_input) - sum(1 for w in neg if w in news_input)
                    if score > 0: st.success("📈 AI View: เชิงบวก - กราฟเทคนิคได้รับแรงหนุน")
                    elif score < 0: st.error("📉 AI View: เชิงลบ - ระวังปัจจัยภายนอกกระทบราคา")
                    else: st.warning("⚪ AI View: เป็นกลาง - ตลาดรอดูท่าที")

if st.button("🔄 Refresh Data"):
    st.rerun()
