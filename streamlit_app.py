import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. GLOBAL INSTITUTIONAL UI CONFIG ---
st.set_page_config(page_title="CORE", layout="wide")
st.markdown("""
    <style>
    /* Dark Theme & Typography */
    .stApp { background-color: #0d1117; color: #c9d1d9; font-family: 'Inter', sans-serif; }
    .stMetric { background-color: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d; }
    [data-testid="stMetricValue"] { color: #58a6ff; font-size: 1.8rem; font-weight: 700; }
    
    /* Global Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #161b22; 
        border-radius: 6px 6px 0 0; 
        padding: 12px 24px; 
        color: #8b949e; 
        font-weight: 500;
        border: 1px solid transparent;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #1f6feb !important; 
        color: #ffffff !important; 
        border: 1px solid #388bfd;
    }
    
    /* Clean Cards */
    div[data-testid="stExpander"] { border: 1px solid #30363d; border-radius: 8px; background-color: #0d1117; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & GLOBAL FX ---
DB_FILE = "core_vault.json"
BAK_FILE = "core_vault.json.bak"

@st.cache_data(ttl=3600)
def get_fx_rate():
    try:
        # ดึงค่าเงิน USD/THB แบบเรียลไทม์
        data = yf.download("USDTHB=X", period="1d", interval="1m", progress=False)
        if not data.empty: return float(data['Close'].iloc[-1])
    except: pass
    return 36.5 

LIVE_USDTHB = get_fx_rate()

def load_vault():
    for f in [DB_FILE, BAK_FILE]:
        if os.path.exists(f):
            try:
                with open(f, "r") as file: return json.load(file)
            except: continue
    return {}

def save_vault(data):
    try:
        with open(DB_FILE, "w") as f: json.dump(data, f)
        shutil.copy(DB_FILE, BAK_FILE)
    except: pass

def format_ticker(t):
    t = t.upper().strip()
    if not t: return None
    set_list = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB", "OR"]
    if t in set_list and not t.endswith(".BK"): return t + ".BK"
    return t

# --- 3. QUANT ENGINE (Institutional Logic) ---
@st.cache_data(ttl=1800)
def fetch_data(tickers):
    if not tickers: return {}
    try:
        raw = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            if isinstance(raw.columns, pd.MultiIndex):
                try: df = raw.xs(t, axis=1, level=1).copy()
                except: continue
            else: df = raw.copy()
            if df.empty or len(df) < 30: continue
            
            # Indicators
            df['SMA200'] = df['Close'].rolling(200).mean()
            df['SMA50'] = df['Close'].rolling(50).mean()
            # RSI Calculation
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            # Volatility (ATR)
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            
            # --- Trailing Stop-Loss Algorithm ---
            df['Base_SL'] = df['Close'] - (df['ATR'] * 2.5)
            sl_vals = df['Base_SL'].values
            close_vals = df['Close'].values
            trailing_sl = np.zeros_like(sl_vals)
            trailing_sl[0] = sl_vals[0]
            for i in range(1, len(sl_vals)):
                if close_vals[i-1] > trailing_sl[i-1]:
                    trailing_sl[i] = max(trailing_sl[i-1], sl_vals[i])
                else:
                    trailing_sl[i] = sl_vals[i]
            df['Trailing_SL'] = trailing_sl
            
            df['Vol_Avg'] = df['Volume'].rolling(20).mean()
            df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg'].replace(0, np.nan)
            processed[t] = df.ffill().bfill()
        return processed
    except: return {}

# --- 4. TERMINAL SIDEBAR ---
if 'vault' not in st.session_state: st.session_state.vault = load_vault()

with st.sidebar:
    st.title("CORE")
    st.caption("Global Asset Management Terminal")
    st.divider()
    capital = st.number_input("Portfolio Equity (THB)", value=1000000, step=50000)
    risk_pct = st.slider("Risk per Position (%)", 0.5, 3.0, 1.0)
    st.divider()
    universe_in = st.text_area("Asset Universe", "NVDA, AAPL, PTT, DELTA, BTC-USD, GOLD")
    raw_list = [t.strip() for t in universe_in.split(",") if t.strip()]
    universe = list(dict.fromkeys([format_ticker(t) for t in raw_list if format_ticker(t)]))
    st.info(f"FX Rate: 1 USD = {LIVE_USDTHB:.2f} THB")

# --- 5. EXECUTION & ANALYSIS ---
data = fetch_data(universe)
scanner_res = []
for t in universe:
    if t not in data: continue
    df = data[t]; c = df.iloc[-1]; p = df.iloc[-2]
    px = c['Close']
    
    # Logic Signal
    trend = px > c['SMA200'] and px > c['SMA50']
    dip = p['RSI'] < 45
    vol = c['Vol_Ratio'] > 1.2
    
    if trend and dip and vol: sig = "🟢 ACCUMULATE"
    elif c['RSI'] > 80: sig = "💰 DISTRIBUTION"
    elif px < c['SMA200']: sig = "🔴 BEARISH"
    else: sig = "⚪ NEUTRAL"

    # Sizing
    risk_thb = capital * (risk_pct / 100)
    sl_gap = max(px - c['Trailing_SL'], 0.01)
    is_usd = not t.endswith(".BK")
    qty = int((risk_thb / (LIVE_USDTHB if is_usd else 1)) / sl_gap)
    if is_usd is False: qty = (qty // 100) * 100

    scanner_res.append({
        "Asset": t, "Price": round(px, 2), "Signal": sig, 
        "RSI": round(c['RSI'], 1), "Target Qty": qty, "Stop Loss": round(c['Trailing_SL'], 2)
    })

# --- 6. MAIN TERMINAL INTERFACE ---
tabs = st.tabs(["Scanner", "Chart", "Portfolio", "Backtest", "Analytics", "Manual", "Logic"])

with tabs[0]:
    st.subheader("Global Market Intelligence")
    if scanner_res: st.dataframe(pd.DataFrame(scanner_res), use_container_width=True, hide_index=True)

with tabs[1]:
    if data:
        sel = st.selectbox("View Asset:", list(data.keys()))
        df_p = data[sel]
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['Trailing_SL'], name="Trailing SL", line=dict(color='#ff4b4b', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name="SMA200", line=dict(color='#f1c40f')), row=1, col=1)
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name="Volume", marker_color="#30363d"), row=2, col=1)
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.subheader("Portfolio Custody")
    with st.expander("Commit New Position"):
        c1, c2, c3 = st.columns(3)
        t_add = c1.selectbox("Asset", list(data.keys()) if data else ["None"])
        p_add = c2.number_input("Entry Price")
        q_add = c3.number_input("Quantity", step=1)
        if st.button("Add to Vault") and t_add != "None":
            st.session_state.vault[t_add] = {"entry": p_add, "qty": q_add}
            save_vault(st.session_state.vault); st.rerun()
    
    if st.session_state.vault:
        p_data = []
        for t, info in st.session_state.vault.items():
            if t in data:
                cur_px = data[t]['Close'].iloc[-1]
                sl_px = data[t]['Trailing_SL'].iloc[-1]
                pnl = (cur_px - info['entry']) * info['qty']
                status = "✅ HOLD" if cur_px > sl_px else "🚨 BREACH"
                p_data.append({"Asset": t, "Entry": info['entry'], "Current": cur_px, "PnL": round(pnl, 2), "Status": status})
        st.dataframe(pd.DataFrame(p_data), use_container_width=True, hide_index=True)
        if st.button("Purge Vault"): save_vault({}); st.session_state.vault = {}; st.rerun()

with tabs[3]:
    st.subheader("Strategy Simulation (1-Year)")
    sel_bt = st.selectbox("Asset to Test:", list(data.keys()) if data else ["None"], key="bt")
    if sel_bt != "None":
        df_bt = data[sel_bt].iloc[-252:].copy()
        cash = capital; pos = 0; log = []
        for i in range(1, len(df_bt)):
            c_bt = df_bt.iloc[i]; p_bt = df_bt.iloc[i-1]
            if pos == 0 and c_bt['Close'] > c_bt['SMA200'] and p_bt['RSI'] < 45 and c_bt['Vol_Ratio'] > 1.2:
                pos = (cash * 0.2) / c_bt['Close'] # 20% allocation per trade
                log.append(f"BUY at {c_bt['Close']:.2f}")
            elif pos > 0 and (c_bt['Close'] < c_bt['Trailing_SL'] or c_bt['RSI'] > 80):
                cash += (c_bt['Close'] - df_bt.iloc[i-1]['Close']) * pos # Simplified PnL
                pos = 0; log.append(f"SELL at {c_bt['Close']:.2f}")
        st.write(f"Final Balance (Simulated): {cash:,.2f} THB")
        st.caption("Note: การทดสอบใช้การจำลองสถิติย้อนหลัง 1 ปี (Historical Simulation)")

with tabs[4]:
    st.subheader("Risk & Analytics")
    if len(data) > 1:
        prices = pd.DataFrame({t: df['Close'] for t, df in data.items()}).dropna()
        corr = prices.corr()
        fig_corr = go.Figure(data=go.Heatmap(z=corr.values, x=corr.columns, y=corr.columns, colorscale='RdBu_r'))
        fig_corr.update_layout(title="Asset Correlation Matrix", template="plotly_dark")
        st.plotly_chart(fig_corr, use_container_width=True)
    else: st.info("Add more assets to see correlation analytics.")

with tabs[5]:
    st.header("📖 Operator's Manual")
    st.markdown("""
    ### ขั้นตอนการปฏิบัติงาน (Standard Operating Procedure)
    1.  **Preparation:** ระบุเงินทุนทั้งหมดใน **Portfolio Equity** และกำหนดความเสี่ยงที่รับได้ (Risk per Position)
    2.  **Asset Selection:** ใส่ชื่อ Ticker ใน **Asset Universe** (รองรับทั้งหุ้นไทย หุ้นสหรัฐฯ ทองคำ และ Crypto)
    3.  **Analysis:** ตรวจสอบสถานะในหน้า **Scanner**
        * **🟢 ACCUMULATE:** จังหวะสะสมเมื่อราคาย่อตัวในแนวโน้มขาขึ้น
        * **💰 DISTRIBUTION:** จังหวะแบ่งขายเมื่อราคาเริ่มตึงตัวเกินไป
    4.  **Risk Management:** ปฏิบัติตาม **Target Qty** เพื่อให้แน่ใจว่าหากผิดทาง คุณจะเสียเงินไม่เกินที่กำหนดไว้ใน Risk %
    """)

with tabs[6]:
    st.header("🧠 System Intelligence")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        #### ⚙️ Core Algorithm
        * **Trend Filter:** ใช้ SMA 200 เป็นตัวแยก Regime ระหว่าง Bull/Bear
        * **Mean Reversion DIP:** ใช้ Wilder's RSI ในการหาจุดที่ราคาย่อตัวลงมาในโซนได้เปรียบ
        * **Liquidity Verification:** คำนวณ Relative Volume เพื่อยืนยันว่ามีแรงซื้อจริงในตลาด
        """)
        st.latex(r"Position\,Size = \frac{Equity \times Risk\%}{Entry - Stop\,Loss}")
    with c2:
        st.markdown("""
        #### 🛡️ Protection Logic
        * **Active Trailing SL:** ระบบจะดึงเส้น Stop Loss ขึ้นตามราคาโดยอัตโนมัติ (Lock-in Profit) แต่จะไม่เลื่อนลงตามราคาที่ลดลง
        * **FX Sync:** รวมค่าความผันผวนของอัตราแลกเปลี่ยนในการคำนวณจำนวนหุ้นสำหรับสินทรัพย์ต่างประเทศ
        """)
    st.divider()
    st.caption("CORE | Powered by Institutional Grade Quant Logic")
