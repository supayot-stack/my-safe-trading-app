import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- 1. SUPER PRO UI CONFIG (Institutional Dark Mode) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")

st.markdown("""
    <style>
    /* พื้นหลังหลักและฟอนต์ */
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid #30363d;
    }
    
    /* Metric Card Styling ให้เหมือนในรูป */
    .metric-card {
        background-color: #21262d;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #30363d;
        text-align: center;
        margin-bottom: 15px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #58a6ff; /* สีฟ้าอ่อนแบบ Institutional */
    }
    .metric-label {
        font-size: 14px;
        color: #8b949e;
    }
    
    /* ปรับแต่ง Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border-radius: 4px 4px 0 0;
        padding: 8px 20px;
        color: #8b949e;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f6feb !important;
        color: white !important;
    }

    /* กล่องข้อความความสำเร็จด้านล่าง */
    .status-bar {
        background-color: rgba(63, 185, 80, 0.15);
        border: 1px solid #238636;
        color: #3fb950;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
        font-weight: bold;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR (Left Panel) ---
with st.sidebar:
    st.markdown("### 🏆 The Masterpiece")
    st.caption("Institutional Systematic OS")
    st.divider()
    
    fx_rate = st.text_input("FX Rate", value="36.52 THB")
    total_cap = st.text_input("Total Capital (THB)", value="1,000,000")
    risk_pct = st.text_input("Risk Per Trade (%)", value="1.0")
    watchlist = st.text_area("Watchlist (CSV)", value="NVDA, AAPL, PTT, DELTA, BTC-USD", height=150)

# --- 3. MAIN CONTENT (Analytics Hub Header) ---
st.markdown("## 🛡️ Analytics Hub")

# สร้าง Layout แบบ 3 คอลัมน์ (กราฟซ้าย - ตัวเลขกลาง - กราฟขวา)
col_left, col_mid, col_right = st.columns([4, 1.5, 4])

# --- 4. LEFT PANEL: MONTE CARLO ---
with col_left:
    st.markdown("#### 🎲 Monte Carlo Simulation")
    # จำลองข้อมูลเส้นใยแมงมุม (Blue Lines)
    fig_mc = go.Figure()
    x = np.arange(100)
    for i in range(40):
        y = 1000000 + np.random.normal(5000, 20000, 100).cumsum()
        fig_mc.add_trace(go.Scatter(x=x, y=y, mode='lines', line=dict(color='#58a6ff', width=0.5), opacity=0.3, showlegend=False))
    
    fig_mc.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=20, b=0), height=400,
        xaxis=dict(gridcolor='#30363d', title="Number of Trades"),
        yaxis=dict(gridcolor='#30363d', title="Portfolio Value (THB)")
    )
    st.plotly_chart(fig_mc, use_container_width=True)

# --- 5. MIDDLE PANEL: KPI METRICS ---
with col_mid:
    st.markdown("<br><br>", unsafe_allow_html=True) # ปรับระยะให้ตรงกับกราฟ
    
    metrics = [
        ("Win Rate", "58.4%", "#3fb950"),
        ("Profit Factor", "2.14", "#3fb950"),
        ("Avg Trade P/L", "12,450 THB", "#3fb950"),
        ("Max Drawdown", "-8.2%", "#f85149")
    ]
    
    for label, value, color in metrics:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value" style="color: {color};">{value}</div>
            </div>
        """, unsafe_allow_html=True)

# --- 6. RIGHT PANEL: EQUITY CURVE ---
with col_right:
    st.markdown("#### 📈 Equity Curve")
    # จำลองเส้น Equity (Green Line)
    x_date = pd.date_range(start="2024-01-01", periods=100, freq="D")
    y_equity = 1000000 + np.random.normal(1500, 5000, 100).cumsum()
    
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(x=x_date, y=y_equity, mode='lines', line=dict(color='#3fb950', width=2), name="Net Equity"))
    
    fig_eq.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=20, b=0), height=400,
        xaxis=dict(gridcolor='#30363d'),
        yaxis=dict(gridcolor='#30363d', side="left")
    )
    st.plotly_chart(fig_eq, use_container_width=True)

# --- 7. BOTTOM STATUS BAR ---
st.markdown('<div class="status-bar">✅ System Alpha Verified</div>', unsafe_allow_html=True)

st.markdown("<br><br><center><small>🏆 The Masterpiece | Institutional Systematic OS</small></center>", unsafe_allow_html=True)
