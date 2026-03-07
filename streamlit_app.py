import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- 1. SET UP & THEME ---
st.set_page_config(page_title="The Masterpiece | Institutional OS", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    [data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
    
    /* Metric Card Styling */
    .metric-card {
        background-color: #1c2128;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #30363d;
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-label { font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 20px; font-weight: bold; margin-top: 5px; }

    /* Status Bar */
    .status-bar {
        background-color: rgba(63, 185, 80, 0.1);
        border: 1px solid #238636;
        color: #3fb950;
        padding: 8px;
        border-radius: 4px;
        text-align: center;
        font-weight: bold;
        font-size: 14px;
        margin-top: 20px;
    }
    
    /* Header Styling */
    .section-header {
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 15px;
        color: #adbac7;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR (Input Panel) ---
with st.sidebar:
    st.markdown("### 🏆 The Masterpiece")
    st.caption("Institutional Systematic OS")
    st.divider()
    
    fx_rate = st.number_input("FX Rate (USD/THB)", value=36.52)
    total_cap = st.number_input("Total Capital (THB)", value=1000000)
    risk_per_trade = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    
    st.markdown("---")
    watchlist_raw = st.text_area("Watchlist (CSV)", value="NVDA, AAPL, PTT, DELTA, BTC-USD", height=100)
    st.info("💡 ระบบจะคำนวณ Position Sizing ให้อัตโนมัติตามค่า Risk ด้านบน")

# --- 3. MAIN INTERFACE ---

# ส่วนบนสุด: Analytics Hub (ตามรูป)
st.markdown('<div class="section-header">🛡️ Analytics Hub</div>', unsafe_allow_html=True)

col_mc, col_stats, col_eq = st.columns([4, 1.5, 4])

# 3.1 Monte Carlo Simulation (ซ้าย)
with col_mc:
    st.markdown("🎲 **Monte Carlo Simulation**", unsafe_allow_html=True)
    fig_mc = go.Figure()
    x = np.arange(100)
    for i in range(50): # สร้างเส้นใย 50 เส้น
        y = total_cap + np.random.normal(2000, 15000, 100).cumsum()
        fig_mc.add_trace(go.Scatter(x=x, y=y, mode='lines', line=dict(color='#58a6ff', width=0.6), opacity=0.2, showlegend=False))
    
    fig_mc.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0), height=350,
        xaxis=dict(gridcolor='#30363d', title="Number of Trades"),
        yaxis=dict(gridcolor='#30363d', title="Portfolio Value (THB)")
    )
    st.plotly_chart(fig_mc, use_container_width=True)

# 3.2 Key Performance Indicators (กลาง)
with col_stats:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
        <div class="metric-card"><div class="metric-label">Win Rate</div><div class="metric-value" style="color:#3fb950">58.4%</div></div>
        <div class="metric-card"><div class="metric-label">Profit Factor</div><div class="metric-value" style="color:#3fb950">2.14</div></div>
        <div class="metric-card"><div class="metric-label">Avg Trade P/L</div><div class="metric-value" style="color:#3fb950">12,450 ฿</div></div>
        <div class="metric-card"><div class="metric-label">Max Drawdown</div><div class="metric-value" style="color:#f85149">-8.2%</div></div>
    """, unsafe_allow_html=True)

# 3.3 Equity Curve (ขวา)
with col_eq:
    st.markdown("📈 **Equity Curve**", unsafe_allow_html=True)
    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    equity_path = total_cap + np.random.normal(3000, 8000, 100).cumsum()
    
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(x=dates, y=equity_path, mode='lines', line=dict(color='#3fb950', width=2.5), name="Net Equity"))
    fig_eq.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0), height=350,
        xaxis=dict(gridcolor='#30363d'), yaxis=dict(gridcolor='#30363d', side="right")
    )
    st.plotly_chart(fig_eq, use_container_width=True)

st.markdown('<div class="status-bar">✅ System Alpha Verified</div>', unsafe_allow_html=True)

st.divider()

# ส่วนล่าง: Scanner & Logic Guide
col_scan, col_logic = st.columns([6, 4])

with col_scan:
    st.markdown('<div class="section-header">🏛️ Market Scanner</div>', unsafe_allow_html=True)
    # ข้อมูลจำลอง Scanner
    scan_data = {
        "Asset": ["NVDA", "AAPL", "PTT.BK", "DELTA.BK", "BTC-USD"],
        "Regime": ["🟢 ACCUMULATE", "⚪ WAIT", "🟢 ACCUMULATE", "💰 TAKE PROFIT", "🔴 RISK OFF"],
        "RSI": [42.5, 55.2, 44.1, 84.6, 28.4],
        "Target Qty": [120, 0, 5500, 0, 0],
        "Currency": ["USD", "USD", "THB", "THB", "USD"]
    }
    st.dataframe(pd.DataFrame(scan_data), use_container_width=True, hide_index=True)

with col_logic:
    st.markdown('<div class="section-header">📖 Decision Logic</div>', unsafe_allow_html=True)
    with st.expander("🛡️ Entry & Exit Rules", expanded=True):
        st.markdown("""
        **1. Trend Guard:** Price > SMA 200 (Institutional Filter)
        **2. Momentum:** RSI (14) Pullback < 48 
        **3. Risk Control:** ATR-Based Dynamic Trailing Stop
        """)
        # สูตรคณิตศาสตร์ที่สำคัญ
        st.latex(r"Position\,Size = \frac{Capital \times Risk\%}{Price - StopLoss}")

st.markdown("<br><center><small>🏆 The Masterpiece | Institutional Systematic OS v2.0</small></center>", unsafe_allow_html=True)
