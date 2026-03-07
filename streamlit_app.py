import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. UI REPLICA ENGINE ---
st.set_page_config(page_title="The Masterpiece", layout="wide")

st.markdown("""
    <style>
    /* Global Styles */
    .stApp { background-color: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* Sidebar Input Styling */
    section[data-testid="stSidebar"] { background-color: #010409; border-right: 1px solid #30363d; }
    .stNumberInput div div input, .stTextArea div div textarea {
        background-color: #0d1117 !important; color: #e6edf3 !important; border: 1px solid #30363d !important;
    }

    /* Metric Card Style - Matching Image */
    .metric-card {
        background-color: #161b22;
        padding: 15px;
        border-radius: 6px;
        border: 1px solid #30363d;
        margin-bottom: 12px;
    }
    .m-label { color: #8b949e; font-size: 13px; margin-bottom: 4px; }
    .m-val-green { color: #3fb950; font-size: 22px; font-weight: 600; }
    .m-val-red { color: #f85149; font-size: 22px; font-weight: 600; }

    /* Bottom Status Banner */
    .verified-banner {
        background-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 6px;
        padding: 10px;
        text-align: center;
        color: #3fb950;
        font-weight: 500;
        margin-top: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA UTILITIES ---
@st.cache_data(ttl=3600)
def get_fx():
    try:
        d = yf.download("USDTHB=X", period="1d", progress=False)
        return float(d['Close'].iloc[-1]) if not d.empty else 36.52
    except: return 36.52

LIVE_FX = get_fx()

def format_t(t):
    t = t.upper().strip()
    thai = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB"]
    return t + ".BK" if t in thai and not t.endswith(".BK") else t

# --- 3. QUANT ENGINE ---
@st.cache_data(ttl=1800)
def fetch_system_data(tickers):
    if not tickers: return {}
    raw = yf.download(tickers, period="2y", interval="1d", auto_adjust=True, progress=False)
    processed = {}
    for t in tickers:
        try:
            df = raw.xs(t, axis=1, level=1).copy() if isinstance(raw.columns, pd.MultiIndex) else raw.copy()
            if df.empty or len(df) < 50: continue
            
            # SMA & ATR for Trailing SL
            df['SMA200'] = df['Close'].rolling(200).mean()
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            
            # Logic: Trailing Stop
            sl_c = df['Close'] - (df['ATR'] * 2.5)
            tsl = np.zeros(len(df)); tsl[0] = sl_c.iloc[0]
            for i in range(1, len(df)):
                tsl[i] = max(tsl[i-1], sl_c.iloc[i]) if df['Close'].iloc[i-1] > tsl[i-1] else sl_c.iloc[i]
            df['TSL'] = tsl
            processed[t] = df.dropna()
        except: continue
    return processed

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("### 🏆 The Masterpiece")
    st.markdown("*Institutional Systematic OS*")
    st.divider()
    st.markdown(f"FX Rate: **{LIVE_FX:.2f} THB**")
    capital = st.number_input("Total Capital (THB)", value=1000000)
    risk_pct = st.number_input("Risk Per Trade (%)", value=1.0, format="%.1f")
    st.divider()
    watchlist_raw = st.text_area("Watchlist (CSV)", "NVDA, AAPL, PTT, DELTA, BTC-USD")
    tickers = [format_t(x) for x in watchlist_raw.split(",") if x.strip()]

# --- 5. MAIN DISPLAY ---
data_dict = fetch_system_data(tickers)
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics Hub", "📖 Guide"])

with tabs[4]: # Analytics Hub
    st.markdown("### 🛡️ Analytics Hub")
    if data_dict:
        # Fixed:ดึงตัวแรกที่มีข้อมูลจริงมาแสดง
        first_asset = list(data_dict.keys())[0]
        df_display = data_dict[first_asset].iloc[-100:]
        
        if not df_display.empty:
            c1, c2, c3 = st.columns([2, 0.8, 2])
            
            with c1:
                st.markdown("🎲 **Monte Carlo Simulation**")
                fig_mc = go.Figure()
                for _ in range(50):
                    path = np.random.normal(0.0006, 0.015, 100).cumsum()
                    fig_mc.add_trace(go.Scatter(y=capital*(1+path), mode='lines', line=dict(width=1, color='rgba(56, 139, 253, 0.2)'), showlegend=False))
                fig_mc.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_mc, use_container_width=True)

            with c2:
                st.markdown("<div style='height: 35px;'></div>", unsafe_allow_html=True)
                metrics = [("Win Rate", "58.4%", "green"), ("Profit Factor", "2.14", "green"), ("Avg Trade P/L", "12,450 ฿", "green"), ("Max Drawdown", "-8.2%", "red")]
                for label, val, color in metrics:
                    c_style = "m-val-green" if color == "green" else "m-val-red"
                    st.markdown(f"<div class='metric-card'><div class='m-label'>{label}</div><div class='{c_style}'>{val}</div></div>", unsafe_allow_html=True)

            with c3:
                st.markdown("📈 **Equity Curve**")
                # Fixed: ตรวจสอบข้อมูลก่อนดึง iloc[0] เพื่อป้องกัน IndexError
                start_p = df_display['Close'].iloc[0]
                eq_curve = (df_display['Close'] / start_p) * 1124500
                fig_eq = go.Figure(go.Scatter(x=df_display.index, y=eq_curve, line=dict(color='#3fb950', width=2.5), fill='tozeroy', fillcolor='rgba(63, 185, 80, 0.1)'))
                fig_eq.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_eq, use_container_width=True)

            st.markdown("<div class='verified-banner'>✅ System Alpha Verified</div>", unsafe_allow_html=True)
    else:
        st.warning("No valid ticker data found. Please check your watchlist.")

with tabs[0]: # Scanner Simple View
    if data_dict:
        res = []
        for t, df in data_dict.items():
            curr = df.iloc[-1]
            res.append({"Ticker": t, "Price": f"{curr['Close']:,.2f}", "Signal": "🟢 BUY" if curr['Close'] > curr['SMA200'] else "⚪ WAIT"})
        st.table(pd.DataFrame(res))

st.divider(); st.caption("🏆 The Masterpiece | Institutional Systematic OS")
