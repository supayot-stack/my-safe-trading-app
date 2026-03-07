import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="Gemini Master Quant v2.1", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .highlight-card { background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 20px; border-radius: 10px; border: 1px solid #3b82f6; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & UTILS ---
DB_FILE = "portfolio_data_v2.json"

def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

def format_ticker(ticker):
    ticker = ticker.upper().strip()
    if not ticker: return None
    if ticker.isalpha() and len(ticker) <= 6 and not ticker.endswith(".BK"):
        thai_logic_list = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB", "OR"]
        if ticker in thai_logic_list:
            return ticker + ".BK"
    return ticker

# --- 3. CORE QUANT ENGINE ---
@st.cache_data(ttl=1800)
def get_data(ticker):
    try:
        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['SL'] = df['Close'] - (df['ATR'] * 2.5)
        
        df['Volatility'] = (df['ATR'] / df['Close']) * 100
        df['Vol_Avg20'] = df['Volume'].rolling(20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20']
        
        return df.dropna()
    except:
        return None

# --- 4. SIDEBAR ---
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.title("🛡️ Secure Quant Pro")
    capital = st.number_input("Total Capital (THB):", value=1000000, step=10000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    
    watchlist_input = st.text_area("Add Tickers (comma separated):", "NVDA, AAPL, PTT, DELTA, BTC-USD, GOLD")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = [format_ticker(t) for t in raw_tickers if format_ticker(t)]

# --- 5. DATA PROCESSING ---
results = []
data_dict = {}

with st.spinner('Scanning Market...'):
    for ticker in final_watchlist:
        df = get_data(ticker)
        if df is not None:
            data_dict[ticker] = df
            curr = df.iloc[-1]
            prev = df.iloc[-2] 
            p = curr['Close']
            
            if p > curr['SMA200'] and p > curr['SMA50'] and prev['RSI'] < 45 and curr['Vol_Ratio'] > 1.2:
                sig = "🟢 ACCUMULATE"
            elif curr['RSI'] > 80: 
                sig = "💰 DISTRIBUTION"
            elif p < curr['SMA200']: 
                sig = "🔴 BEARISH"
            else: 
                sig = "⚪ NEUTRAL"

            risk_cash = capital * (risk_pct / 100)
            sl_gap = p - curr['SL']
            safe_sl_gap = max(sl_gap, 0.01) 
            qty = int(risk_cash / safe_sl_gap) if p > curr['SL'] else 0

            results.append({
                "Asset": ticker, "Price": round(p, 2), "Regime": sig, 
                "RSI": round(curr['RSI'], 1), "Target Qty": qty, "Stop-Loss": round(curr['SL'], 2),
                "Volatility %": round(curr['Volatility'], 2), "Vol_Ratio": round(curr['Vol_Ratio'], 2)
            })

res_df = pd.DataFrame(results)

# --- 6. MAIN TERMINAL ---
t1, t2, t3, t4, t5, t6 = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Analytics", "📖 Guide", "🧠 System Architecture"])

with t1:
    st.subheader("📊 Market Opportunities")
    if not res_df.empty:
        st.dataframe(res_df, use_container_width=True, hide_index=True)
    else:
        st.info("กรุณาระบุ Ticker ใน Sidebar เพื่อเริ่มสแกน")

with t2:
    if data_dict:
        sel = st.selectbox("Analyze Asset:", list(data_dict.keys()))
        df_p = data_dict[sel]
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.35])
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SL'], name='Stop-Loss', line=dict(color='red', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Volume', marker_color='#c0c0c0', opacity=0.6), row=3, col=1)
        
        fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

with t3:
    st.subheader("💼 Portfolio Management")
    with st.expander("➕ บันทึกไม้เทรด"):
        c1, c2, c3 = st.columns(3)
        p_asset = c1.selectbox("Asset", final_watchlist)
        p_entry = c2.number_input("Entry Price", value=0.0)
        p_qty = c3.number_input("Quantity", value=0)
        if st.button("Add to Portfolio"):
            st.session_state.my_portfolio[p_asset] = {"entry": p_entry, "qty": p_qty}
            save_portfolio(st.session_state.my_portfolio)
            st.rerun()

    if st.session_state.my_portfolio:
        p_data = []
        for asset, info in st.session_state.my_portfolio.items():
            match = res_df[res_df['Asset'] == asset]
            if not match.empty:
                cp = match.iloc[0]['Price']
                sl = match.iloc[0]['Stop-Loss']
                pnl = (cp - info['entry']) * info['qty']
                status = "✅ HOLD" if cp > sl else "🚨 EXIT NOW"
                p_data.append({"Asset": asset, "Cost": info['entry'], "Price": cp, "Qty": info['qty'], "P/L": round(pnl, 2), "Signal": status})
        
        if p_data:
            st.dataframe(pd.DataFrame(p_data), use_container_width=True, hide_index=True)
            if st.button("🗑️ Reset Portfolio"):
                save_portfolio({}); st.session_state.my_portfolio = {}; st.rerun()

with t4:
    st.subheader("🧪 Advanced Analytics & Risk Control")
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.write("### 🔗 Asset Correlation")
        price_dict = {ticker: df['Close'] for ticker, df in data_dict.items() if df is not None}
        if len(price_dict) > 1:
            corr_df = pd.DataFrame(price_dict).dropna().corr()
            fig_corr = go.Figure(data=go.Heatmap(
                z=corr_df.values, x=corr_df.columns, y=corr_df.columns, 
                colorscale='RdBu_r', zmin=-1, zmax=1,
                text=np.round(corr_df.values, 2), texttemplate="%{text}"
            ))
            fig_corr.update_layout(height=450, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_corr, use_container_width=True)
        else:
            st.info("⚠️ เพิ่มหุ้นอย่างน้อย 2 ตัวเพื่อดู Correlation")

    with col_right:
        st.write("### 🏗️ Future Modules")
        st.checkbox("Backtesting Engine (RSI Strategy)", disabled=True, value=False)
        st.checkbox("Sector Rotation Map", disabled=True, value=False)
        st.checkbox("Fundamental Score (P/E, PEG)", disabled=True, value=False)
        
        st.divider()
        st.write("### 🛡️ Portfolio Health")
        if st.session_state.my_portfolio:
            # คำนวณ Total Cash at Risk: (Entry - StopLoss) * Qty
            total_risk = 0
            for a, info in st.session_state.my_portfolio.items():
                match = res_df[res_df['Asset'] == a]
                if not match.empty:
                    sl = match.iloc[0]['Stop-Loss']
                    total_risk += (info['entry'] - sl) * info['qty']
            
            st.metric("Total Cash at Risk", f"{max(total_risk, 0):,.2f} THB")
            risk_ratio = min(max(total_risk / capital, 0), 1.0) if capital > 0 else 0
            st.progress(risk_ratio)
            st.caption(f"ความเสี่ยงปัจจุบัน: {risk_ratio*100:.2f}% ของเงินต้น")

with t5:
    st.markdown("""
    ### 📖 Quant Terminal Guide
    1. **Scanner:** ดู "Regime" เพื่อหาหุ้นที่พร้อมวิ่ง (Green = เข้าเกณฑ์สะสม)
    2. **Deep-Dive:** ตรวจสอบแนวรับ-แนวต้าน และจุด Stop-loss (เส้นประสีแดง)
    3. **Stop-loss Strategy:** เราใช้ $ATR \times 2.5$ เพื่อให้ราคาหุ้น "หายใจ" ได้ ไม่โดนเขย่าออกก่อนเวลา
    4. **Safety Check:** หาก Correlation สูงเกินไป ควรพิจารณาเลือกเทรดเพียงตัวเดียวในกลุ่มนั้น
    """)

with t6:
    st.header("🧠 System Architecture & Quant Logic")
    st.info("คำอธิบายการทำงานเชิงลึกของระบบ Gemini Master Quant v2.1")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        ### 1. ระบบจัดการข้อมูล (Data Engine & Persistence)
        * **Data Fetching (yf.download):** ดึงข้อมูลย้อนหลัง 2 ปีจาก Yahoo Finance โดยมีการจัดการ Multi-index เพื่อความเสถียร
        * **Ticker Formatting:** มี Logic พิเศษในการแปลงชื่อหุ้นไทย เช่น พิมพ์ PTT ระบบจะเติม .BK ให้โดยอัตโนมัติ
        * **JSON Database:** ใช้ไฟล์ `portfolio_data_v2.json` เพื่อบันทึกพอร์ตจำลอง ข้อมูลไม่หายเมื่อเปิด-ปิดใหม่
        
        ### 2. การคำนวณ Technical & Quant Indicators
        * **Trend Identification:** ใช้ SMA200 (ขาขึ้นระยะยาว) และ SMA50 (ระยะกลาง)
        * **RSI (Wilder's Smoothing):** คำนวณแบบดั้งเดิมที่แม่นยำเพื่อหาจุด Pullback
        * **Volatility-Based Stop-Loss (ATR):**
            * ใช้สูตร $Close - (ATR \\times 2.5)$
            * ช่วยวางจุดตัดขาดทุนในระยะที่ "หุ้นยังหายใจได้" ไม่โดนสะบัดออก (Stop Hunt) ง่ายๆ
        """)
        
    with c2:
        st.markdown("""
        ### 3. กลยุทธ์การคัดกรอง (Signal & Regime Logic)
        * **🟢 ACCUMULATE:** ต้องยืนเหนือ SMA(50, 200) + RSI ย่อตัว < 45 + Volume Spike > 1.2x
        * **💰 DISTRIBUTION:** RSI > 80 เตือนแรงขาย
        * **🔴 BEARISH:** ราคาหลุด SMA200 คือจบคะแนนพิศวาส
        
        ### 4. ระบบคำนวณขนาดไม้ (Position Sizing)
        * **Risk-Based Sizing:** คำนวณจำนวนหุ้นตามความเสี่ยงที่ยอมรับได้ (%)
        * **สูตร:** $$Quantity = \\frac{Capital \\times Risk\%}{Price - StopLoss}$$
        * **ประโยชน์:** ไม่ว่าหุ้นจะผันผวนแค่ไหน ถ้าโดน SL คุณจะขาดทุนเป็นเงินที่คงที่เสมอ
        """)
        
    st.divider()
    st.markdown("""
    ### 5. ส่วนแสดงผล (Professional Visuals)
    * **Candlestick & Subplots:** แยกกราฟราคา, RSI และ Volume (สีเงิน #c0c0c0) ชัดเจน
    * **Correlation Heatmap:** ตรวจสอบความสัมพันธ์ของหุ้นในพอร์ต ป้องกันการกระจุกความเสี่ยง
    
    **สรุปภาพรวม:** โค้ดนี้คือ **Decision Support System** ที่ช่วยให้คุณเทรดด้วย "สถิติ" แทน "อารมณ์"
    """)
