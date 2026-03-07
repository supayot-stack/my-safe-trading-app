import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTING ---
st.set_page_config(page_title="Safe Heaven Quant Pro ATR", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. TABS ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & ATR", "📖 คู่มือเทคนิค"])

with tab2:
    st.header("🛡️ ระบบ ATR Stop Loss")
    st.markdown("""
    **ATR (Average True Range)** ช่วยให้เราวางจุดหนีตามความผันผวนจริง:
    - **หุ้นเหวี่ยงแรง:** SL จะกว้างขึ้นเพื่อลดการโดนสะบัด (False Break)
    - **หุ้นนิ่ง:** SL จะแคบลงเพื่อเพิ่มจำนวนหุ้นที่ซื้อได้
    """)
    

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro + ATR")
    
    # --- 3. Sidebar ---
    st.sidebar.header("💰 Portfolio Settings")
    p_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    r_pct = st.sidebar.slider("ความเสี่ยงต่อไม้ (%):", 0.5, 5.0, 1.0)
    atr_mult = st.sidebar.slider("ATR Multiplier:", 1.0, 3.0, 1.5)
    
    st.sidebar.divider()
    assets = st.sidebar.multiselect("เลือกหุ้น:", 
                                    options=["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK", "PTT.BK", "CPALL.BK"], 
                                    default=["NVDA", "AAPL", "BTC-USD"])

    # --- 4. ฟังก์ชันดึงข้อมูล & คำนวณ ATR ---
    def get_data(ticker):
        try:
            df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
            if df.empty or len(df) < 200: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            
            # SMA & Volume Avg
            df['SMA200'] = df['Close'].rolling(200).mean()
            df['Vol_Avg'] = df['Volume'].rolling(5).mean()
            
            # RSI Calculation (Fixed Syntax)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            
            # ATR Calculation
            high_low = df['High'] - df['Low']
            high_close = (df['High'] - df['Close'].shift()).abs()
            low_close = (df['Low'] - df['Close'].shift()).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            
            # Set SL/TP
            df['SL'] = df['Close'] - (df['ATR'] * atr_mult)
            df['TP'] = df['Close'] + (df['ATR'] * (atr_mult * 2))
            return df
        except: return None

    # --- 5. ประมวลผล ---
    results = []
    if assets:
        with st.spinner('กำลังคำนวณ...'):
            for t in assets:
                df = get_data(t)
                if df is not None:
                    l = df.iloc[-1]
                    p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg']
                    
                    if p > s and r < 45 and v > va: sig = "🟢 BUY"
                    elif r > 75: sig = "💰 PROFIT"
                    elif p < s: sig = "🔴 EXIT"
                    else: sig = "⚪ WAIT"
                    
                    # Risk Management
                    risk_amt = p_size * (r_pct / 100)
                    dist = p - l['SL']
                    qty = int(risk_amt / dist) if dist > 0 else 0
                    
                    results.append({
                        "Ticker": t, "Price": round(p,2), "RSI": round(r,1), 
                        "Signal": sig, "Vol OK": "✅" if v > va else "❌",
                        "Qty": qty, "SL (ATR)": round(l['SL'],2), "TP": round(l['TP'],2)
                    })

        if results:
            res_df = pd.DataFrame(results)
            st.subheader("🎯 สรุปสัญญาณล่าสุด")
            st.dataframe(res_df, use_container_width=True, hide_index=True)

            # --- 6. กราฟ ---
            st.divider()
            c1, c2 = st.columns([0.6, 0.4])
            with c1:
                sel = st.selectbox("🔍 เลือกหุ้นเพื่อดูรายละเอียด:", [r['Ticker'] for r in results])
                df_p = get_data(sel)
                if df_p is not None:
                    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                                        vertical_spacing=0.03, row_heights=[0.6, 0.2, 0.2])
                    
                    # Candlestick
                    fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
                    
                    # Volume (New!)
                    v_colors = ['red' if df_p['Open'][i] > df_p['Close'][i] else 'green' for i in range(len(df_p))]
                    fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Volume', marker_color=v_colors), row=2, col=1)
                    
                    # RSI
                    fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=3, col=1)
                    
                    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)

            with c2:
                row = next(item for item in results if item["Ticker"] == sel)
                st.markdown(f"""
                <div class="risk-box">
                    <h3>แผนเทรด {sel}</h3>
                    <p><b>จำนวนที่ควรซื้อ:</b> {row['Qty']:,} หุ้น</p>
                    <hr>
                    <p><b>จุดคัดขาดทุน (ATR SL):</b> {row['SL (ATR)']}</p>
                    <p><b>เป้ากำไร:</b> {row['TP']}</p>
                    <p><b>ใช้เงินลงทุนโดยประมาณ:</b> {(row['Price']*row['Qty']):,.0f} บาท</p>
                </div>
                """, unsafe_allow_html=True)

if st.button("🔄 Refresh Data"): st.rerun()
