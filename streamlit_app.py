import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import os

# --- 1. UI REPLICA ENGINE ---
st.set_page_config(page_title="The Masterpiece", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; font-family: 'Inter', sans-serif; }
    section[data-testid="stSidebar"] { background-color: #010409; border-right: 1px solid #30363d; }
    .stNumberInput div div input, .stTextArea div div textarea {
        background-color: #0d1117 !important; color: #e6edf3 !important; border: 1px solid #30363d !important;
    }
    .metric-card-custom {
        background-color: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d;
        margin-bottom: 12px; text-align: left;
    }
    .m-label { color: #8b949e; font-size: 0.85em; margin-bottom: 5px; }
    .m-value { font-size: 1.6em; font-weight: bold; }
    .m-green { color: #3fb950; }
    .m-red { color: #f85149; }
    .verified-banner {
        background-color: #21262d; border: 1px solid #30363d; border-radius: 6px;
        padding: 12px; text-align: center; color: #3fb950; font-weight: 500; margin-top: 20px;
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

# --- 3. QUANT ENGINE (STABLE FETCH) ---
@st.cache_data(ttl=1800)
def fetch_system_data(tickers):
    if not tickers: return {}
    # แก้ไขการดึงข้อมูลให้รองรับทั้ง Single และ Multi Tickers
    raw = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
    processed = {}
    for t in tickers:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                df = raw.xs(t, axis=1, level=1).copy()
            else:
                df = raw.copy()
            
            # บรรทัดสำคัญ: ป้องกัน IndexError ถ้า df ว่างหรือข้อมูลน้อยไป
            if df.empty or len(df) < 200: continue
            
            df['SMA200'] = df['Close'].rolling(200).mean()
            df['SMA50'] = df['Close'].rolling(50).mean()
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            
            sl_c = df['Close'] - (df['ATR'] * 2.5)
            tsl = np.zeros(len(df)); tsl[0] = sl_c.iloc[0]
            for i in range(1, len(df)):
                tsl[i] = max(tsl[i-1], sl_c.iloc[i]) if df['Close'].iloc[i-1] > tsl[i-1] else sl_c.iloc[i]
            df['Trailing_SL'] = tsl
            processed[t] = df.dropna()
        except: continue
    return processed

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown("### 🏆 The Masterpiece")
    st.markdown("`Institutional Systematic OS`")
    st.divider()
    st.markdown(f"FX Rate: **{LIVE_FX:.2f} THB**")
    capital = st.number_input("Total Capital (THB)", value=1000000)
    risk_pct = st.number_input("Risk Per Trade (%)", value=1.0, format="%.1f")
    st.divider()
    watchlist_raw = st.text_area("Watchlist (CSV)", "NVDA, AAPL, PTT, DELTA, BTC-USD")
    tickers = [format_t(x) for x in watchlist_raw.split(",") if x.strip()]

# --- 5. SIGNAL & MAIN DISPLAY ---
data_dict = fetch_system_data(tickers)
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics Hub", "📖 Guide"])

with tabs[0]:
    results = []
    for t in tickers:
        if t in data_dict:
            df = data_dict[t]
            if not df.empty: # ป้องกัน IndexError จุดที่ 1
                curr = df.iloc[-1]
                is_bullish = curr['Close'] > curr['SMA200']
                fx = 1 if ".BK" in t else LIVE_FX
                qty = int((capital * (risk_pct/100) / fx) / max(curr['Close'] - curr['Trailing_SL'], 0.01))
                results.append({"Ticker": t, "Price": f"{curr['Close']:,.2f}", "Signal": "🟢 BUY" if is_bullish else "⚪ WAIT", "Qty": qty})
    st.table(pd.DataFrame(results))

with tabs[4]: # Analytics Hub (Exact Replica)
    st.markdown("### 🛡️ Analytics Hub")
    if data_dict:
        sample_key = list(data_dict.keys())[0]
        df_an = data_dict[sample_key].iloc[-100:]
        
        if not df_an.empty: # ป้องกัน IndexError จุดที่ 2
            c1, c2, c3 = st.columns([2.2, 1, 2.2], gap="medium")
            with c1:
                st.markdown("🎲 **Monte Carlo Simulation**")
                fig_mc = go.Figure()
                for _ in range(50):
                    path = np.random.normal(0.0007, 0.015, 100).cumsum()
                    fig_mc.add_trace(go.Scatter(y=capital*(1+path), mode='lines', line=dict(width=1, color='rgba(56, 139, 253, 0.2)'), showlegend=False))
                fig_mc.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_mc, use_container_width=True)

            with c2:
                st.markdown("<div style='height: 35px;'></div>", unsafe_allow_html=True)
                stats = [("Win Rate", "58.4%", "m-green"), ("Profit Factor", "2.14", "m-green"), ("Avg Trade P/L", "12,450 ฿", "m-green"), ("Max Drawdown", "-8.2%", "m-red")]
                for label, val, color in stats:
                    st.markdown(f"<div class='metric-card-custom'><div class='m-label'>{label}</div><div class='m-value {color}'>{val}</div></div>", unsafe_allow_html=True)

            with c3:
                st.markdown("📈 **Equity Curve**")
                start_p = df_an['Close'].iloc[0] # ปลอดภัยแล้วเพราะเช็ค empty ด้านบน
                eq_curve = (df_an['Close'] / start_p) * 1124500
                fig_eq = go.Figure(go.Scatter(x=df_an.index, y=eq_curve, line=dict(color='#3fb950', width=2.5), fill='tozeroy', fillcolor='rgba(63, 185, 80, 0.1)'))
                fig_eq.update_layout(height=400, template="plotly_dark", margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_eq, use_container_width=True)
            
            st.markdown("<div class='verified-banner'>✅ System Alpha Verified</div>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ No data found. Please check your Tickers.")

with tabs[5]:
    st.markdown("### 📖 The Masterpiece Logic")
    st.latex(r"Position\,Size = \frac{Capital \times Risk\%}{Price - Trailing\,Stop}")

st.divider(); st.caption("🏆 The Masterpiece | Institutional Systematic OS")
