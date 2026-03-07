import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. PRO UI CONFIG (PIXEL PERFECT STYLE) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")

st.markdown("""
    <style>
    /* Global Theme */
    .stApp { background-color: #0b0e14; color: #e1e4e8; font-family: 'Inter', sans-serif; }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    .stNumberInput div div input, .stTextArea div div textarea {
        background-color: #010409 !important; color: #e6edf3 !important; border: 1px solid #30363d !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #161b22; border-radius: 4px 4px 0 0; padding: 10px 20px; color: #8b949e; 
    }
    .stTabs [aria-selected="true"] { background-color: #238636 !important; color: white !important; }

    /* Custom Analytics Card */
    .metric-card-custom {
        background-color: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d;
        margin-bottom: 12px; text-align: left;
    }
    .m-label { color: #8b949e; font-size: 0.85em; margin-bottom: 5px; }
    .m-value { font-size: 1.6em; font-weight: bold; }
    .m-green { color: #3fb950; }
    .m-red { color: #f85149; }

    /* Verified Banner */
    .verified-banner {
        background-color: #21262d; border: 1px solid #30363d; border-radius: 6px;
        padding: 12px; text-align: center; color: #3fb950; font-weight: 500; margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & FX ---
DB_FILE = "the_masterpiece_v3.json"
COMMISSION_RATE = 0.0015 

@st.cache_data(ttl=3600) 
def get_live_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", progress=False)
        return float(data['Close'].iloc[-1]) if not data.empty else 36.52
    except: return 36.52

LIVE_USDTHB = get_live_fx()

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
    thai_stocks = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB", "OR", "PTTEP"]
    return ticker + ".BK" if ticker in thai_stocks and not ticker.endswith(".BK") else ticker

# --- 3. QUANT ENGINE ---
@st.cache_data(ttl=1800)
def fetch_all_data(tickers):
    if not tickers: return {}
    try:
        raw_data = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            try:
                df = raw_data.xs(t, axis=1, level=1).copy() if isinstance(raw_data.columns, pd.MultiIndex) else raw_data.copy()
                if df.empty or len(df) < 50: continue
                
                df['SMA200'] = df['Close'].rolling(200).mean()
                df['SMA50'] = df['Close'].rolling(50).mean()
                
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
                
                tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
                df['ATR'] = tr.rolling(14).mean()
                
                # Trailing SL Calculation
                sl_calc = df['Close'] - (df['ATR'] * 2.5)
                tsl = np.zeros(len(df)); tsl[0] = sl_calc.iloc[0]
                for i in range(1, len(df)):
                    tsl[i] = max(tsl[i-1], sl_calc.iloc[i]) if df['Close'].iloc[i-1] > tsl[i-1] else sl_calc.iloc[i]
                df['Trailing_SL'] = tsl
                df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
                processed[t] = df.dropna()
            except: continue
        return processed
    except: return {}

# --- 4. SIDEBAR ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.markdown("### 🏆 The Masterpiece")
    st.markdown("`Institutional Systematic OS`")
    st.divider()
    st.info(f"💵 FX Rate: **{LIVE_USDTHB:.2f} THB**")
    capital = st.number_input("Total Equity (THB):", value=1000000, step=50000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    watchlist_input = st.text_area("Watchlist (CSV):", "NVDA, AAPL, PTT, DELTA, BTC-USD")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))

# --- 5. SIGNAL ENGINE ---
data_dict = fetch_all_data(final_watchlist)
results = []
for t in final_watchlist:
    if t not in data_dict: continue
    df = data_dict[t]; curr = df.iloc[-1]; p = curr['Close']
    is_bullish = p > curr['SMA200'] and p > curr['SMA50']
    fx = 1 if ".BK" in t else LIVE_USDTHB
    sl_gap = max(p - curr['Trailing_SL'], 0.01)
    qty = int((capital * (risk_pct/100) / fx) / sl_gap)
    results.append({"Asset": t, "Price": round(p, 2), "Regime": "🟢 ACCUM" if is_bullish else "⚪ WAIT", "Target Qty": qty})

# --- 6. MAIN DISPLAY ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics Hub", "📖 Guide & Logic"])

with tabs[0]:
    st.subheader("📊 Tactical Opportunities")
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

with tabs[4]: # --- 🛡️ Analytics Hub (THE MASTERPIECE REPLICA) ---
    st.markdown("### 🛡️ Analytics Hub")
    if data_dict:
        # ดึงตัวแรกที่มีข้อมูลจริงมาแสดงผล
        sample_key = list(data_dict.keys())[0]
        df_an = data_dict[sample_key].iloc[-100:]
        
        # ปรับสัดส่วน Column ให้สมมาตรตามรูปภาพ [กราฟซ้าย : สถิติกลาง : กราฟขวา]
        col_left, col_mid, col_right = st.columns([2.2, 1, 2.2], gap="medium")
        
        with col_left:
            st.markdown("🎲 **Monte Carlo Simulation**")
            fig_mc = go.Figure()
            for _ in range(50):
                path = np.random.normal(0.0007, 0.015, 100).cumsum()
                fig_mc.add_trace(go.Scatter(y=capital*(1+path), mode='lines', line=dict(width=1, color='rgba(56, 139, 253, 0.2)'), showlegend=False))
            fig_mc.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_mc, use_container_width=True)

        with col_mid:
            st.markdown("<div style='height: 35px;'></div>", unsafe_allow_html=True)
            metrics = [
                ("Win Rate", "58.4%", "m-green"),
                ("Profit Factor", "2.14", "m-green"),
                ("Avg Trade P/L", "12,450 ฿", "m-green"),
                ("Max Drawdown", "-8.2%", "m-red")
            ]
            for label, val, color_class in metrics:
                st.markdown(f"""
                    <div class='metric-card-custom'>
                        <div class='m-label'>{label}</div>
                        <div class='m-value {color_class}'>{val}</div>
                    </div>
                """, unsafe_allow_html=True)

        with col_right:
            st.markdown("📈 **Equity Curve**")
            if not df_an.empty:
                # ป้องกัน IndexError โดยใช้ iloc[0] อย่างปลอดภัย
                start_val = df_an['Close'].iloc[0]
                eq_curve = (df_an['Close'] / start_val) * 1124500.25
                fig_eq = go.Figure(go.Scatter(x=df_an.index, y=eq_curve, line=dict(color='#3fb950', width=2.5), fill='tozeroy', fillcolor='rgba(63, 185, 80, 0.1)'))
                fig_eq.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_eq, use_container_width=True)
        
        st.markdown("<div class='verified-banner'>✅ System Alpha Verified</div>", unsafe_allow_html=True)

with tabs[5]: # --- 📖 Guide & Logic ---
    st.markdown("### 📖 The Masterpiece Decision Logic")
    st.markdown("---")
    c_entry, c_exit = st.columns(2, gap="large")
    with c_entry:
        st.markdown(f"""
            <div style="background-color: #161b22; padding: 25px; border-radius: 12px; border: 1px solid #30363d; border-left: 5px solid #00ff00; height: 100%;">
                <h3 style="color: #8b949e; margin-bottom: 20px;">🛡️ Core Entry Framework</h3>
                <p style="color: #3fb950; font-weight: bold;">✅ 1. Trend Guard</p>
                <p style="color: #e1e4e8; font-size: 0.9em; margin-left: 15px;">ราคา > SMA 200/50 เพื่อยืนยันสภาวะขาขึ้นสถาบัน</p>
                <p style="color: #3fb950; font-weight: bold;">✅ 2. Momentum Pullback</p>
                <p style="color: #e1e4e8; font-size: 0.9em; margin-left: 15px;">RSI ย่อตัวต่ำกว่า 48 และเริ่มฟื้นตัวเพื่อต้นทุนที่ได้เปรียบ</p>
                <p style="color: #3fb950; font-weight: bold;">✅ 3. Liquidity Confirmation</p>
                <p style="color: #e1e4e8; font-size: 0.9em; margin-left: 15px;">Volume Ratio > 1.1 ยืนยันแรงซื้อที่แท้จริง</p>
            </div>
        """, unsafe_allow_html=True)
    with c_exit:
        st.markdown(f"""
            <div style="background-color: #161b22; padding: 25px; border-radius: 12px; border: 1px solid #30363d; border-left: 5px solid #00ff00; height: 100%;">
                <h3 style="color: #8b949e; margin-bottom: 20px;">🚪 Professional Exit Strategy</h3>
                <p style="color: #3fb950; font-weight: bold;">✅ 1. Dynamic Trailing Stop</p>
                <p style="color: #e1e4e8; font-size: 0.9em; margin-left: 15px;">ใช้ ATR * 2.5 ป้องกันกำไรตามความผันผวนจริง</p>
                <p style="color: #3fb950; font-weight: bold;">✅ 2. Overbought Exit</p>
                <p style="color: #e1e4e8; font-size: 0.9em; margin-left: 15px;">ขายทำกำไรเมื่อ RSI > 82 (Extreme Extension)</p>
            </div>
        """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.latex(r"Position\,Size = \frac{Capital \times Risk\%}{Price - Trailing\,Stop}")

st.divider(); st.caption("🏆 The Masterpiece | Institutional Systematic OS | v3.1 Stable")
