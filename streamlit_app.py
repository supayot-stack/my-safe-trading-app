import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. PRO UI CONFIG (Institutional Dark Mode) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")

st.markdown("""
    <style>
    /* พื้นหลังหลักและ Sidebar */
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    
    /* สไตล์การ์ดตัวเลข (Metric) ให้เหมือนในรูปเป๊ะ */
    [data-testid="stMetric"] {
        background-color: #1b2128; 
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 15px !important;
        margin-bottom: 10px;
    }
    [data-testid="stMetricValue"] { color: #2ea043 !important; font-family: 'Courier New', monospace; font-weight: bold; }
    [data-testid="stMetricLabel"] { color: #8b949e !important; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 1px; }
    
    /* ปรับแต่ง Tabs ให้ดู Clean */
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; border-bottom: 1px solid #30363d; gap: 20px; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; padding: 10px 0px; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border-bottom: 2px solid #ffffff !important; }

    /* System Alpha Verified Badge */
    .alpha-verified {
        background: rgba(35, 134, 54, 0.1);
        border: 1px solid #238636;
        color: #3fb950;
        padding: 10px;
        text-align: center;
        border-radius: 4px;
        font-weight: bold;
        margin-top: 15px;
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE (Pre-fetching) ---
@st.cache_data(ttl=3600)
def get_masterpiece_data():
    # ดึงข้อมูลจริงมาทำตัวอย่างเพื่อให้ Dashboard ไม่ว่าง
    df = yf.download("NVDA", period="2y", interval="1d", progress=False)
    close = df['Close']
    rets = close.pct_change().dropna()
    return rets, close

# ดึงข้อมูลเตรียมไว้
returns, price_data = get_masterpiece_data()
current_capital = 1000000
equity_path = (1 + returns).cumprod() * current_capital

# --- 3. SIDEBAR ---
with st.sidebar:
    st.markdown("## 🏆 The Masterpiece")
    st.markdown("`Institutional Systematic OS`")
    st.divider()
    st.text_input("FX Rate", value="36.52 THB")
    st.number_input("Total Capital (THB)", value=current_capital)
    st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    st.text_area("Watchlist (CSV)", "NVDA, AAPL, PTT, DELTA, BTC-USD")

# --- 4. MAIN LAYOUT ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics Hub", "📖 Guide & Logic"])

with tabs[4]: # Analytics Hub
    # จัดวาง Layout 3 ส่วน: กราฟ MC | ตัวเลขสถิติ | กราฟ Equity
    col_left, col_mid, col_right = st.columns([3, 1.2, 3])

    with col_left:
        st.markdown("##### 🎲 Monte Carlo Simulation")
        fig_mc = go.Figure()
        # จำลองเส้นทางเดินราคา 50 เส้นทาง
        for _ in range(50):
            sim_rets = np.random.choice(returns, size=len(returns), replace=True)
            sim_path = (1 + sim_rets).cumprod() * current_capital
            fig_mc.add_trace(go.Scatter(y=sim_path, mode='lines', line=dict(color='#58a6ff', width=0.8), opacity=0.15, showlegend=False))
        
        fig_mc.update_layout(
            height=420, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(title="Number of Trades", showgrid=True, gridcolor='#21262d'),
            yaxis=dict(title="Portfolio Value (THB)", showgrid=True, gridcolor='#21262d')
        )
        st.plotly_chart(fig_mc, use_container_width=True)

    with col_mid:
        st.metric("Win Rate", "58.4%")
        st.metric("Profit Factor", "2.14")
        st.metric("Avg Trade P/L", "12,450 THB")
        st.metric("Max Drawdown", "-8.2%")

    with col_right:
        st.markdown("##### 📈 Equity Curve")
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(
            x=equity_path.index, y=equity_path, 
            mode='lines', line=dict(color='#2ea043', width=2),
            fill='tozeroy', fillcolor='rgba(46, 160, 67, 0.05)', name="Net Equity"
        ))
        
        fig_eq.update_layout(
            height=420, template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(showgrid=True, gridcolor='#21262d'),
            yaxis=dict(side="right", showgrid=True, gridcolor='#21262d')
        )
        st.plotly_chart(fig_eq, use_container_width=True)

    st.markdown('<div class="alpha-verified">✅ System Alpha Verified</div>', unsafe_allow_html=True)

# Footer
st.divider()
st.caption("🏆 The Masterpiece | Institutional Systematic OS v2.0")
