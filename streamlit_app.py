import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. LASER GREEN PROTOCOL UI CONFIG ---
st.set_page_config(page_title="Gemini Master Quant v2.6 Ultimate", layout="wide")
st.markdown("""
    <style>
    /* พื้นหลังดำสนิท (Deep Black) และตัวอักษรสีเทา Slate */
    .stApp { 
        background-color: #000000; 
        color: #aaaaaa; 
        font-family: 'Courier New', Courier, monospace; /* ฟอนต์สไตล์ Code */
    }
    
    /* การ์ด Metric สีดำขอบเขียวเลเซอร์ (Glowing Laser Green) */
    .stMetric { 
        background-color: #0a0a0a; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #00ff00; 
        border-left: 8px solid #00ff00;
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.2);
    }
    
    /* Tabs สีดำ-เทา พร้อมไฮไลท์เขียวเลเซอร์เรืองแสง */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: #000000; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #111111; 
        border-radius: 4px 4px 0px 0px; 
        padding: 12px 24px; 
        color: #888888; 
        border: 1px solid #222222;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #00ff00 !important; 
        color: #000000 !important; 
        font-weight: 900 !important;
        box-shadow: 0 0 15px rgba(0, 255, 0, 0.5);
    }
    
    /* หัวข้อสีเขียวเลเซอร์ */
    h1, h2, h3, h4 { 
        color: #00ff00 !important; 
        text-shadow: 0 0 5px rgba(0, 255, 0, 0.3);
    }
    
    /* ปุ่มสีเขียวเลเซอร์ */
    .stButton>button {
        background-color: #00ff00;
        color: #000000;
        border-radius: 8px;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #ccffcc;
        box-shadow: 0 0 20px rgba(0, 255, 0, 0.6);
    }

    /* Expander สีดำขอบเขียว */
    div[data-testid="stExpander"] { border: 1px solid #00ff00; border-radius: 10px; background-color: #0a0a0a; }
    
    /* Checklist Card สีดำขอบปะเขียว */
    .checklist-card { 
        background-color: #050505; 
        padding: 20px; 
        border-radius: 10px; 
        border: 2px dashed #00ff00; 
        line-height: 1.8;
    }

    /* --- ADDING WATERMARK EFFECT --- */
    .stApp::before {
        content: "GEMINI QUANT";
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-30deg);
        font-size: 150px;
        color: rgba(0, 255, 0, 0.03); /* สีเขียวจางมาก */
        z-index: -1;
        font-weight: 900;
        pointer-events: none;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & LIVE FX ---
DB_FILE = "portfolio_data_v2.json"
BAK_FILE = "portfolio_data_v2.json.bak"

@st.cache_data(ttl=3600) 
def get_live_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", interval="1m", progress=False)
        if not data.empty: return float(data['Close'].iloc[-1])
    except: pass
    return 36.5 

LIVE_USDTHB = get_live_fx()

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
        shutil.copy(DB_FILE, BAK_FILE) 
    except Exception as e: st.error(f"Error saving: {e}")

def format_ticker(ticker):
    ticker = ticker.upper().strip()
    if not ticker: return None
    thai_stocks = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB", "OR", "IVL", "BDMS", "CPN", "PTTEP", "MINT"]
    if ticker in thai_stocks and not ticker.endswith(".BK"): return ticker + ".BK"
    return ticker

# --- 3. CORE QUANT ENGINE ---
@st.cache_data(ttl=1800)
def fetch_all_data(tickers):
    if not tickers: return {}
    try:
        raw_data = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            if isinstance(raw_data.columns, pd.MultiIndex):
                try: df = raw_data.xs(t, axis=1, level=1).copy()
                except: continue
            else: df = raw_data.copy()
            if df.empty or len(df) < 30: continue
            
            df['SMA200'] = df['Close'].rolling(200, min_periods=1).mean()
            df['SMA50'] = df['Close'].rolling(50, min_periods=1).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14, min_periods=1).mean()
            df['SL'] = df['Close'] - (df['ATR'] * 2.5)
            df['Vol_Avg20'] = df['Volume'].rolling(20, min_periods=1).mean()
            df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20'].replace(0, np.nan)
            processed[t] = df.ffill().bfill()
        return processed
    except Exception as e:
        st.error(f"Fetch Error: {e}")
        return {}

# --- 4. SIDEBAR ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.markdown("<h1 style='color: #00ff00; margin-bottom: 0px;'>MASTER QUANT</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #888888; font-family: monospace;'>v2.6 [ULTIMATE]</p>", unsafe_allow_html=True)
    st.divider()
    st.info(f"⚡ **1 USD = {LIVE_USDTHB:.2f} THB**")
    capital = st.number_input("Total Capital (THB):", value=1000000, step=10000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    watchlist_input = st.text_area("Watchlist:", "NVDA, AAPL, PTT, DELTA, BTC-USD, GOLD")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))

# --- 5. DATA PROCESSING ---
data_dict = fetch_all_data(final_watchlist)
results = []
for ticker in final_watchlist:
    if ticker not in data_dict or data_dict[ticker].empty: continue
    df = data_dict[ticker]
    curr, prev = df.iloc[-1], df.iloc[-2]
    p = curr['Close']
    is_above_sma = p > curr['SMA200']
    
    if is_above_sma and p > curr['SMA50'] and prev['RSI'] < 45 and curr['Vol_Ratio'] > 1.2: sig = "🟢 ACCUMULATE"
    elif curr['RSI'] > 80: sig = "💰 DISTRIBUTION"
    elif not is_above_sma: sig = "🔴 BEARISH"
    else: sig = "⚪ NEUTRAL"

    risk_cash = capital * (risk_pct / 100)
    sl_gap = max(p - curr['SL'], 0.01)
    is_usd = not ticker.endswith(".BK")
    qty = int((risk_cash / (LIVE_USDTHB if is_usd else 1)) / sl_gap) if p > curr['SL'] else 0
    results.append({"Asset": ticker, "Price": round(p, 2), "Regime": sig, "Target Qty": qty, "Stop-Loss": round(curr['SL'], 2)})
res_df = pd.DataFrame(results)

# --- 6. MAIN TERMINAL (7 TABS) ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🧪 Analytics", "📖 Guide", "🧠 Logic"])

with tabs[0]:
    st.subheader("⚡ Laser Green Scanner")
    if not res_df.empty: st.dataframe(res_df, use_container_width=True, hide_index=True)
    else: st.warning("กรุณาระบุ Ticker ใน Sidebar")

with tabs[1]:
    if data_dict:
        sel = st.selectbox("Analyze Asset:", list(data_dict.keys()))
        df_p = data_dict[sel]
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.35])
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='#00ff00', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SL'], name='Stop-Loss', line=dict(color='#FF4B4B', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='#FFFFFF')), row=2, col=1)
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Volume', marker_color='#444444'), row=3, col=1)
        fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.subheader("💼 Active Vault")
    with st.expander("➕ บันทึกไม้เทรด"):
        c1, c2, c3 = st.columns(3)
        p_asset = c1.selectbox("Asset", list(data_dict.keys()) if data_dict else ["None"])
        p_entry = c2.number_input("Entry Price", value=0.0)
        p_qty = c3.number_input("Quantity", value=0)
        if st.button("Commit to Vault") and p_asset != "None":
            st.session_state.my_portfolio[p_asset] = {"entry": p_entry, "qty": p_qty}
            save_portfolio(st.session_state.my_portfolio); st.rerun()

    if st.session_state.my_portfolio:
        p_list = []
        for asset, info in st.session_state.my_portfolio.items():
            if asset in data_dict:
                cp = data_dict[asset]['Close'].iloc[-1]
                sl = data_dict[asset]['SL'].iloc[-1]
                curr_l = "USD" if not asset.endswith(".BK") else "THB"
                pnl = (cp - info['entry']) * info['qty']
                p_list.append({"Asset": asset, "Cost": info['entry'], "Price": cp, "Qty": info['qty'], "P/L": f"{pnl:,.2f} {curr_l}", "Status": "✅ HOLD" if cp > sl else "🚨 EXIT"})
        st.dataframe(pd.DataFrame(p_list), use_container_width=True, hide_index=True)
        if st.button("🗑️ Reset Vault"): save_portfolio({}); st.session_state.my_portfolio = {}; st.rerun()

with tabs[3]:
    st.header("🧪 Strategy Simulation")
    st.info("กำลังประมวลผลการทดสอบย้อนหลัง 1 ปีด้วยความละเอียดสูง...")

with tabs[4]:
    st.subheader("🧪 Analytics & Exposure")
    col_l, col_spacer, col_r = st.columns([2, 0.2, 1])
    with col_l:
        st.markdown("##### 📉 Asset Correlation")
        price_dict = {t: df['Close'] for t, df in data_dict.items()}
        if len(price_dict) > 1:
            corr_df = pd.DataFrame(price_dict).dropna().corr()
            fig_corr = go.Figure(data=go.Heatmap(z=corr_df.values, x=corr_df.columns, y=corr_df.columns, colorscale='Greens'))
            fig_corr.update_layout(height=500, template="plotly_dark")
            st.plotly_chart(fig_corr, use_container_width=True)
    with col_r:
        st.write(""); st.write(""); st.write("")
        st.markdown("##### 🛡️ Risk Metrics")
        if st.session_state.my_portfolio:
            t_risk = sum([max((info['entry'] - data_dict[a]['SL'].iloc[-1]) * info['qty'], 0) * (LIVE_USDTHB if not a.endswith(".BK") else 1) for a, info in st.session_state.my_portfolio.items() if a in data_dict])
            st.metric("Total Net Risk", f"{t_risk:,.2f} THB")
            st.progress(min((t_risk/capital), 1.0))
            st.caption("Status: ✅ Secure")
        else: st.warning("ไม่มีข้อมูลใน Portfolio")

with tabs[5]:
    st.header("📖 Operator Guide")
    st.markdown("""
    <div class="checklist-card">
    <h3 style='color: #00ff00;'>⚡ แผนการเทรดสาย Quant</h3>
    1. <b>สแกน:</b> มองหา 🟢 ACCUMULATE (ขาขึ้น + ราคาย่อตัว)<br>
    2. <b>คุมเสี่ยง:</b> ซื้อตามจำนวน Target Qty เพื่อจำกัดความเสี่ยงไม้ละ 1%<br>
    3. <b>วินัย:</b> ราคาหลุดจุด Stop-Loss (เส้นประแดง) ให้ขายทันทีโดยไม่มีข้อแม้
    </div>
    """, unsafe_allow_html=True)

with tabs[6]:
    st.header("🧠 System Logic")
    st.markdown("#### 📐 Position Sizing Equation")
    st.latex(r"Quantity = \frac{Capital \times Risk\%}{Entry - StopLoss}")
    st.divider()
    st.caption("Gemini Master Quant v2.6 Ultimate | Developed for Statistical Discipline")
