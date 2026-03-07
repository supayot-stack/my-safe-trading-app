import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="Gemini Master Quant v2.2 Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & SECURITY ---
DB_FILE = "portfolio_data_v2.json"
BAK_FILE = "portfolio_data_v2.json.bak"
USD_THB_RATE = 36.0 # ค่าเงินบาทโดยประมาณ (สามารถพัฒนาให้ดึง Real-time ได้)

def load_portfolio():
    for file in [DB_FILE, BAK_FILE]:
        if os.path.exists(file):
            try:
                with open(file, "r") as f: return json.load(f)
            except: continue
    return {}

def save_portfolio(data):
    try:
        with open(DB_FILE, "w") as f: json.dump(data, f)
        shutil.copy(DB_FILE, BAK_FILE) # Auto-backup
    except Exception as e:
        st.error(f"Error saving portfolio: {e}")

def format_ticker(ticker):
    ticker = ticker.upper().strip()
    if not ticker: return None
    # Auto-mapping หุ้นไทยยอดนิยม
    thai_stocks = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB", "OR", "IVL", "BDMS"]
    if ticker in thai_stocks and not ticker.endswith(".BK"):
        return ticker + ".BK"
    return ticker

# --- 3. CORE QUANT ENGINE (BULK OPTIMIZED) ---
@st.cache_data(ttl=1800)
def fetch_all_data(tickers):
    if not tickers: return {}
    try:
        # ดึงข้อมูลแบบ Bulk เพื่อลด Request (ความปลอดภัยด้าน Stability)
        raw_data = yf.download(tickers, period="2y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            if len(tickers) > 1:
                df = raw_data.xs(t, axis=1, level=1) if isinstance(raw_data.columns, pd.MultiIndex) else raw_data
            else:
                df = raw_data
            
            if df.empty or len(df) < 200: continue
            
            # --- Indicators ---
            df['SMA200'] = df['Close'].rolling(200).mean()
            df['SMA50'] = df['Close'].rolling(50).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            df['SL'] = df['Close'] - (df['ATR'] * 2.5)
            df['Vol_Avg20'] = df['Volume'].rolling(20).mean()
            df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20']
            processed[t] = df.dropna()
        return processed
    except Exception as e:
        st.error(f"Data Fetch Error: {e}")
        return {}

# --- 4. SIDEBAR & LOGIC ---
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.title("🛡️ Secure Quant Pro v2.2")
    capital = st.number_input("Total Capital (THB):", value=1000000, step=10000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    watchlist_input = st.text_area("Add Tickers (comma separated):", "NVDA, AAPL, PTT, DELTA, BTC-USD, GOLD")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))

# --- 5. DATA PROCESSING (CURRENCY AWARE) ---
data_dict = fetch_all_data(final_watchlist)
results = []

for ticker, df in data_dict.items():
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    p = curr['Close']
    
    # Strategy Logic
    if p > curr['SMA200'] and p > curr['SMA50'] and prev['RSI'] < 45 and curr['Vol_Ratio'] > 1.2:
        sig = "🟢 ACCUMULATE"
    elif curr['RSI'] > 80: sig = "💰 DISTRIBUTION"
    elif p < curr['SMA200']: sig = "🔴 BEARISH"
    else: sig = "⚪ NEUTRAL"

    # --- Secure Position Sizing (Currency Aware) ---
    risk_cash_thb = capital * (risk_pct / 100)
    sl_gap = p - curr['SL']
    safe_sl_gap = max(sl_gap, 0.01)
    
    # เช็คว่าเป็นหุ้น USD หรือไม่ (Logic พื้นฐาน: ไม่มี .BK)
    is_usd = not ticker.endswith(".BK")
    if is_usd:
        risk_cash_converted = risk_cash_thb / USD_THB_RATE
        qty = int(risk_cash_converted / safe_sl_gap) if p > curr['SL'] else 0
    else:
        qty = int(risk_cash_thb / safe_sl_gap) if p > curr['SL'] else 0

    results.append({
        "Asset": ticker, "Price": round(p, 2), "Regime": sig, 
        "RSI": round(curr['RSI'], 1), "Target Qty": qty, "Stop-Loss": round(curr['SL'], 2),
        "Currency": "USD" if is_usd else "THB"
    })

res_df = pd.DataFrame(results)

# --- 6. MAIN TERMINAL ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Analytics", "📖 Guide", "🧠 System Architecture"])

with tabs[0]:
    st.subheader("📊 Market Opportunities")
    st.dataframe(res_df, use_container_width=True, hide_index=True)

with tabs[1]:
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

with tabs[2]:
    st.subheader("💼 Portfolio Management")
    with st.expander("➕ บันทึกไม้เทรด"):
        c1, c2, c3 = st.columns(3)
        p_asset = c1.selectbox("Asset", list(data_dict.keys()) if data_dict else ["None"])
        p_entry = c2.number_input("Entry Price", value=0.0)
        p_qty = c3.number_input("Quantity", value=0)
        if st.button("Add to Portfolio") and p_asset != "None":
            st.session_state.my_portfolio[p_asset] = {"entry": p_entry, "qty": p_qty}
            save_portfolio(st.session_state.my_portfolio)
            st.rerun()

    if st.session_state.my_portfolio:
        p_data = []
        for asset, info in st.session_state.my_portfolio.items():
            if asset in data_dict:
                cp = data_dict[asset]['Close'].iloc[-1]
                sl = data_dict[asset]['SL'].iloc[-1]
                pnl = (cp - info['entry']) * info['qty']
                status = "✅ HOLD" if cp > sl else "🚨 EXIT NOW"
                p_data.append({"Asset": asset, "Cost": info['entry'], "Price": cp, "Qty": info['qty'], "P/L": round(pnl, 2), "Signal": status})
        if p_data:
            st.dataframe(pd.DataFrame(p_data), use_container_width=True, hide_index=True)
            if st.button("🗑️ Reset Portfolio"):
                save_portfolio({}); st.session_state.my_portfolio = {}; st.rerun()

with tabs[3]:
    st.subheader("🧪 Advanced Analytics")
    col_left, col_right = st.columns([2, 1])
    with col_left:
        price_dict = {t: df['Close'] for t, df in data_dict.items()}
        if len(price_dict) > 1:
            corr_df = pd.DataFrame(price_dict).dropna().corr()
            fig_corr = go.Figure(data=go.Heatmap(z=corr_df.values, x=corr_df.columns, y=corr_df.columns, colorscale='RdBu_r', zmin=-1, zmax=1, text=np.round(corr_df.values, 2), texttemplate="%{text}"))
            fig_corr.update_layout(height=450, template="plotly_dark")
            st.plotly_chart(fig_corr, use_container_width=True)
    with col_right:
        st.write("### 🏗️ Future Modules")
        for m in ["Backtesting Engine", "Sector Rotation", "Fundamental Score"]: st.checkbox(m, disabled=True)
        st.divider()
        st.write("### 🛡️ Risk Summary")
        if st.session_state.my_portfolio:
            total_risk_thb = 0
            for a, info in st.session_state.my_portfolio.items():
                if a in data_dict:
                    sl = data_dict[a]['SL'].iloc[-1]
                    risk = (info['entry'] - sl) * info['qty']
                    if not a.endswith(".BK"): risk *= USD_THB_RATE # แปลงความเสี่ยงหุ้นนอกกลับเป็น THB
                    total_risk_thb += max(risk, 0)
            st.metric("Total Cash at Risk (THB)", f"{total_risk_thb:,.2f}")
            st.progress(min(total_risk_thb / capital, 1.0))

with tabs[5]:
    st.header("🧠 System Architecture & Quant Logic")
    st.markdown("""
    ### 1. ระบบจัดการข้อมูล (Data Engine & Persistence)
    * **Bulk Download:** ดึงข้อมูลรวดเดียวเพื่อลด Request และป้องกันการโดน Yahoo Finance แบน
    * **Currency Aware:** ระบบแยกแยะหุ้น THB/USD และใช้ FX Rate ในการคำนวณเงินต้นที่เสี่ยงได้
    * **Auto-Backup:** ทุกการบันทึกพอร์ตจะทำไฟล์สำรอง `.bak` ทันทีเพื่อความปลอดภัย
    
    ### 2. สูตรคำนวณเด่น
    * **Position Sizing (USD):** $$Quantity = \\frac{(Capital_{THB} \\times Risk\%) / FX\_Rate}{Price_{USD} - SL_{USD}}$$
    * **RSI Wilder's Smoothing:** ลดความผันผวนของอินดิเคเตอร์เพื่อหาจุดเข้าที่นิ่งขึ้น
    """)
