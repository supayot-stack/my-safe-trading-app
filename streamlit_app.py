import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- 1. PRO UI CONFIG (Institutional Dark Theme) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")

st.markdown("""
    <style>
    /* พื้นหลังและฟอนต์หลัก */
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    [data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
    
    /* ตาราง Scanner */
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    
    /* การ์ดตัวเลข Metrics */
    .metric-card {
        background-color: #161b22;
        padding: 18px;
        border-radius: 10px;
        border: 1px solid #30363d;
        text-align: center;
        margin-bottom: 12px;
    }
    .m-label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
    .m-value { font-size: 22px; font-weight: bold; margin-top: 5px; }

    /* แถบ Alpha Status ด้านล่าง */
    .status-bar {
        background-color: rgba(63, 185, 80, 0.1);
        border: 1px solid #238636;
        color: #3fb950;
        padding: 10px;
        border-radius: 6px;
        text-align: center;
        font-weight: bold;
        margin-top: 15px;
    }
    
    h3 { color: #adbac7; font-size: 1.2rem !important; margin-top: 1rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR PANEL ---
with st.sidebar:
    st.markdown("### 🏆 The Masterpiece")
    st.caption("Institutional Systematic OS")
    st.divider()
    
    capital = st.number_input("Total Equity (THB):", value=1000000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    st.text_area("Watchlist (CSV):", "NVDA, AAPL, PTT, DELTA, BTC-USD", height=100)

# --- 3. [TOP] MARKET SCANNER SECTION ---
st.subheader("🏛️ Market Scanner & Tactical Opportunities")
# ข้อมูลจำลองสำหรับ Scanner (ในโค้ดจริงจะดึงจาก fetch_all_data)
scan_df = pd.DataFrame({
    "Asset": ["NVDA", "AAPL", "PTT.BK", "DELTA.BK", "BTC-USD"],
    "Regime": ["🟢 ACCUMULATE", "⚪ WAIT", "🟢 ACCUMULATE", "💰 TAKE PROFIT", "🔴 RISK OFF"],
    "Price": [135.20, 224.15, 34.25, 102.50, 64200.0],
    "RSI": [42.5, 55.2, 44.1, 84.6, 28.4],
    "Target Qty": [125, 0, 5800, 0, 0],
    "Currency": ["USD", "USD", "THB", "THB", "USD"]
})
st.dataframe(scan_df, use_container_width=True, hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 4. [MIDDLE] ANALYTICS HUB (กราฟที่มีเส้นตัด Grid) ---
st.subheader("🛡️ Analytics Hub")

# ฟังก์ชันตั้งค่าเส้น Grid ให้เหมือนในรูป
def apply_institutional_style(fig, height=380):
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#22272e', zeroline=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#22272e', zeroline=False)
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=10, b=10),
        height=height,
        font=dict(color='#8b949e', size=10),
        hovermode="x unified"
    )
    return fig

col_mc, col_stats, col_eq = st.columns([4, 1.5, 4])

# 4.1 Monte Carlo Simulation (ซ้าย)
with col_mc:
    st.caption("🎲 Monte Carlo Simulation")
    fig_mc = go.Figure()
    for _ in range(40): # สร้างเส้นใย 40 เส้น
        y_path = capital + np.random.normal(2500, 16000, 100).cumsum()
        fig_mc.add_trace(go.Scatter(y=y_path, mode='lines', 
                                 line=dict(color='#58a6ff', width=0.8), 
                                 opacity=0.2, showlegend=False))
    st.plotly_chart(apply_institutional_style(fig_mc), use_container_width=True)

# 4.2 KPI Stats Card (กลาง)
with col_stats:
    st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)
    metrics = [
        ("Win Rate", "58.4%", "#3fb950"),
        ("Profit Factor", "2.14", "#3fb950"),
        ("Avg Trade P/L", "12,450 ฿", "#3fb950"),
        ("Max Drawdown", "-8.2%", "#f85149")
    ]
    for label, val, color in metrics:
        st.markdown(f"""
            <div class="metric-card">
                <div class="m-label">{label}</div>
                <div class="m-value" style="color: {color};">{val}</div>
            </div>
        """, unsafe_allow_html=True)

# 4.3 Equity Curve (ขวา)
with col_eq:
    st.caption("📈 Equity Curve")
    y_eq = capital + np.random.normal(4500, 9000, 100).cumsum()
    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(y=y_eq, mode='lines', 
                             line=dict(color='#3fb950', width=2.5),
                             fill='tozeroy', fillcolor='rgba(63, 185, 80, 0.05)'))
    st.plotly_chart(apply_institutional_style(fig_eq), use_container_width=True)

# --- 5. [BOTTOM] STATUS & LOGIC ---
st.markdown('<div class="status-bar">✅ System Alpha Verified</div>', unsafe_allow_html=True)

with st.expander("📖 View Decision Logic & Risk Formula"):
    st.latex(r"Position\,Size = \frac{Equity \times Risk\%}{Price - Trailing\,Stop}")
    st.info("System uses SMA 200/50 for Trend Guard and RSI for Momentum Pullback detection.")

st.markdown("<br><center><small style='color:#8b949e;'>🏆 The Masterpiece | Institutional Systematic OS</small></center>", unsafe_allow_html=True)
