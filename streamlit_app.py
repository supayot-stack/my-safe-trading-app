import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอและสไตล์ ---
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

# --- 2. ส่วนเมนู (Tabs) ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง (Pro)"])

with tab2:
    st.header("📖 กฎเหล็ก 1% ของนักลงทุนระดับโลก")
    st.markdown("""
    ### 🛡️ ทำอย่างไรให้ "ห้ามพัง" (Zero Ruin)
    1. **The 1% Rule:** ในแต่ละการเทรด ถ้าผิดทาง คุณควรเสียเงินไม่เกิน **1% ของเงินต้นทั้งหมด**
    2. **Position Sizing:** ซื้อจำนวนหุ้นให้สัมพันธ์กับระยะห่างของจุด Stop Loss
    """)
    st.info("💡 สูตร: จำนวนหุ้น = (เงินทุนทั้งหมด x %ความเสี่ยง) / (ราคาซื้อ - ราคา Stop Loss)")

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    # --- 3. Sidebar: Fix Syntax Error Line 42 ---
    st.sidebar.header("💰 Portfolio Settings")
    # แก้ไขจุดที่ลืมปิดเครื่องหมายคำพูดตรงนี้
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อการเทรด (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Management")
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้นแนะนำ:", options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK"])), default=default_assets)
    custom_ticker = st.sidebar.text_input("➕ เพิ่มหุ้นอื่นๆ:").upper().strip()
    
    final_list = list(selected_assets)
    if custom_ticker and custom_ticker not in final_list:
        final_list.append(custom_ticker)

    # --- 4. ฟังก์ชันดึงข้อมูลและการคำนวณ ---
    def get_data(ticker, interval="1d", data_period="2y"):
        try:
            thai_stocks = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB", "DELTA"]
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
            df['SL'] = df['Close'] * 0.97
            df['TP'] = df['Close'] * 1.07
            return df
        except Exception as e:
            return None

    # --- 5. การประมวลผล ---
    results = []
    if final_list:
        with st.spinner('กำลังคำนวณแผนการเทรด...'):
            for t in final_list:
                df = get_data(t) 
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
            st.subheader("🎯 สรุปสัญญาณและแผนคุมความเสี่ยง")
            st.dataframe(res_df, use_container_width=True, hide_index=True)

    st.divider()

    # --- 6. กราฟและการบริหารความเสี่ยง ---
    col1, col2 = st.columns([0.6, 0.4])
    if results:
        with col1:
            selected_plot = st.selectbox("🔍 วิเคราะห์กราฟละเอียด:", [r['Ticker'] for r in results])
            df_plot = get_data(selected_plot)
            if df_plot is not None:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=2)), row=1, col=1)
                fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['Volume'], name='Volume', marker_color='#4A4A4A', opacity=0.5), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['RSI'], name='RSI', line=dict(color='#00ccff', width=1.5)), row=2, col=1)
                fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False, showlegend=False)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True, 'scrollZoom': True})

        with col2:
            st.markdown("### 🛠️ เครื่องมือบริหารหน้าตัก")
            target_data = next(item for item in results if item["Ticker"] == selected_plot)
            st.markdown(f"""
            <div class="risk-box">
                <h4>คำแนะนำสำหรับ {selected_plot}</h4>
                <p>จำนวนหุ้นที่ควรซื้อ: <b>{target_data['Qty to Buy']:,}</b> หุ้น</p>
                <p>Stop Loss (3%): <span style="color:#ff4b4b;">{target_data['StopLoss']}</span></p>
            </div>
            """, unsafe_allow_html=True)
