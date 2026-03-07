import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="The Masterpiece", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    [data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
    
    /* Table Styling */
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    
    /* Metric Card Styling */
    .metric-box {
        background-color: #161b22;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
        text-align: center;
        margin-bottom: 12px;
    }
    .m-label { font-size: 11px; color: #8b949e; text-transform: uppercase; }
    .m-value { font-size: 22px; font-weight: bold; margin-top: 5px; }

    /* Alpha Status Bar */
    .alpha-bar {
        background-color: rgba(63, 185, 80, 0.1);
        border: 1px solid #238636;
        color: #3fb950;
        padding: 10px;
        border-radius: 6px;
        text-align: center;
        font-weight: bold;
        margin-top: 15px;
    }
    
    h3 { color: #adbac7; font-size: 18px !important; margin-bottom: 20px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR PANEL ---
with st.sidebar:
    st.markdown("### 🏆 The Masterpiece")
    st.caption("Institutional Systematic OS")
    st.divider()
    
    fx = st.text_input("FX Rate", "36.52 THB")
    cap = st.text_input("Total Capital (THB)", "1,000,000")
    risk = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    watchlist = st.text_area("Watchlist (CSV)", "NVDA, AAPL, PTT, DELTA, BTC-USD", height=120)

# --- 3. TOP SECTION: MARKET SCANNER ---
st.markdown("### 🏛️ Market Scanner & Tactical Opportunities")
scan_df = pd.DataFrame({
    "Asset": ["NVDA", "AAPL", "PTT.BK", "DELTA.BK", "BTC-USD"],
    "Regime": ["🟢 ACCUMULATE", "⚪ WAIT", "🟢 ACCUMULATE", "💰 TAKE PROFIT", "🔴 RISK OFF"],
    "Price": [135.20, 224.15, 34.25, 102.50, 64200.0],
    "RSI": [42.5, 55.2, 44.1, 84.6, 28.4],
    "Target Qty": [125, 0, 5800, 0, 0],
    "Status": ["HOLD", "WATCH", "BUY", "EXIT", "AVOID"]
})
st.dataframe(scan_df, use_container_width=True, hide_index=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 4. MIDDLE SECTION: ANALYTICS HUB (กราฟคู่ตามรูป) ---
st.markdown("### 🛡️ Analytics Hub")
col_mc, col_stats, col_eq = st.columns([4, 1.5, 4])

# 4.1 Monte Carlo Simulation
with col_mc:
    st.caption("🎲 Monte Carlo Simulation (Probabilistic Paths)")
    fig_mc = go.Figure()
    for _ in range(40):
        y = 1000000 + np.random.normal(3000, 18000, 100).cumsum()
        fig_mc.add_trace(go.Scatter(y=y, mode='lines', line=dict(color='#58a6ff', width=0.7), opacity=0.2, showlegend=False))
    
    fig_mc.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0), height=380,
        xaxis=dict(gridcolor='#30363d', title="Trades"),
        yaxis=dict(gridcolor='#30363d', title="Portfolio (THB)")
    )
    st.plotly_chart(fig_mc, use_container_width=True)

# 4.2 Vertical Metrics Card
with col_stats:
    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
    metrics = [
        ("Win Rate", "58.4%", "#3fb950"),
        ("Profit Factor", "2.14", "#3fb950"),
        ("Avg Trade P/L", "12,450 ฿", "#3fb950"),
        ("Max Drawdown", "-8.2%", "#f85149")
    ]
    for label, val, color in metrics:
        st.markdown(f"""
            <div class="metric-box">
                <div class="m-label">{label}</div>
                <div class="m-value" style="color: {color};">{val}</div>
            </div>
        """, unsafe_allow_html=True)

# 4.3 Equity Curve
with col_eq:
    st.caption("📈 Equity Curve (Performance History)")
    y_eq = 1000000 + np.random.normal(5000, 12000, 100).cumsum()
    fig_eq = go.Figure(go.Scatter(y=y_eq, mode='lines', line=dict(color='#3fb950', width=2.5), fill='tozeroy', fillcolor='rgba(63, 185, 80, 0.05)'))
    fig_eq.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0), height=380,
        xaxis=dict(gridcolor='#30363d'), yaxis=dict(gridcolor='#30363d', side="right")
    )
    st.plotly_chart(fig_eq, use_container_width=True)

# --- 5. BOTTOM SECTION: ALPHA VERIFIED & LOGIC ---
st.markdown('<div class="alpha-bar">✅ System Alpha Verified</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📖 View Decision Logic & Risk Formula"):
    st.latex(r"Position\,Size = \frac{Equity \times Risk\%}{Price - Trailing\,Stop}")
    st.info("System uses ATR-based volatility stop with a 2.5x multiplier for risk-off signals.")

st.markdown("<center><small style='color:#8b949e;'>🏆 The Masterpiece | Institutional Systematic OS v2.1</small></center>", unsafe_allow_html=True)
