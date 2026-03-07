import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. PRO UI CONFIG (จัดรูปแบบ CSS ให้เหมือนในรูปที่สุด) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #e1e4e8; }
    
    /* ปรับแต่ง Tabs ให้ดู Clean และเป็น Flat Design แบบในรูป */
    .stTabs [data-baseweb="tab-list"] {
        gap: 15px;
        background-color: transparent;
        border-bottom: 1px solid #21262d;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        border: none !important;
        color: #8b949e !important;
        padding: 12px 0px !important;
        font-size: 15px !important;
    }
    /* เมื่อเลือก Tab: ใช้เส้นใต้สีเขียว/ขาว และเปลี่ยนสีตัวอักษร */
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background-color: transparent !important;
        border-bottom: 2px solid #58a6ff !important;
        font-weight: 500 !important;
    }
    
    /* สไตล์สำหรับ Metric Card ในหน้า Analytics (ปรับให้เป็นกล่องสีเทาเรียบๆ แบบในรูป) */
    .analytics-card {
        background-color: #161b22; 
        padding: 15px; 
        border-radius: 6px; 
        border: 1px solid #21262d; 
        margin-bottom: 10px;
    }
    
    /* สไตล์สำหรับป้ายชื่อและค่าในแถบด้านข้าง */
    .sidebar-label { color: #8b949e; font-size: 14px; margin-bottom: 2px; }
    .sidebar-value { color: #e1e4e8; font-size: 14px; margin-bottom: 5px; }
    .sidebar-input-box {
        background-color: #161b22;
        border-radius: 4px;
        padding: 8px;
        margin-bottom: 10px;
        color: #e1e4e8;
        font-size: 14px;
        border: 1px solid #21262d;
    }
    
    /* สไตล์แถบสถานะด้านล่าง */
    .system-verified-bar {
        background-color: #161b22;
        padding: 10px;
        border-radius: 6px;
        text-align: center;
        border: 1px solid #21262d;
        margin-top: 20px;
    }
    .verified-text {
        color: #39d353;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR (จัดรูปแบบให้เหมือนในรูปที่สุด) ---
with st.sidebar:
    # Gold Trophy Icon & Title
    st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 24px; color: gold; margin-right: 10px;">🏆</span>
            <span style="font-size: 20px; font-weight: bold; color: white;">The Masterpiece</span>
        </div>
        <p style="color: #8b949e; margin-top: -5px; margin-bottom: 20px;"> Institutional Systematic OS</p>
    """, unsafe_allow_html=True)
    
    st.divider()

    # FX Rate
    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
            <p class="sidebar-label" style="margin: 0;">FX Rate</p>
            <p class="sidebar-value" style="margin: 0;">36.52 THB</p>
        </div>
        <div class="sidebar-input-box" style="height: 38px;"></div>
    """, unsafe_allow_html=True)
    
    # Total Capital (THB)
    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
            <p class="sidebar-label" style="margin: 0;">Total Capital (THB)</p>
            <p class="sidebar-value" style="margin: 0;">1,000,000</p>
        </div>
        <div class="sidebar-input-box" style="height: 38px;"></div>
    """, unsafe_allow_html=True)

    # Risk Per Trade (%)
    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
            <p class="sidebar-label" style="margin: 0;">Risk Per Trade (%)</p>
            <p class="sidebar-value" style="margin: 0;">1.0</p>
        </div>
        <div class="sidebar-input-box" style="height: 38px;"></div>
    """, unsafe_allow_html=True)
    
    # Watchlist (CSV)
    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
            <p class="sidebar-label" style="margin: 0;">Watchlist (CSV)</p>
            <p class="sidebar-value" style="margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 150px;">NVDA, AAPL, PTT, DELTA, BTC-USD</p>
        </div>
        <div class="sidebar-input-box" style="height: 100px;"></div>
    """, unsafe_allow_html=True)

    st.divider()

# --- 3. CORE QUANT ENGINE (จำลองข้อมูลแบ็คเทส) ---
# จำลองข้อมูลการซื้อขาย
num_trades = 100
capital = 1000000
final_capital = 1124500.25
equity_dates = pd.date_range(start="2024-01-01", periods=num_trades, freq="W")
equity_values = np.linspace(start=capital, stop=final_capital, num=num_trades) + np.random.normal(scale=10000, size=num_trades)

td_df = pd.DataFrame({
    'Date': equity_dates,
    'Equity': equity_values,
    'PnL': equity_values - np.roll(equity_values, 1)
})
td_df.iloc[0, 2] = 0  # ลบ PnL ของวันแรก

# --- 4. MAIN DISPLAY (จัดรูปแบบ Tabs ให้เหมือนในรูปที่สุด) ---
tabs = st.tabs(["🏛 Scanner", "📉 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics Hub", "📖 Guide & Logic"])

# แสดงเฉพาะ Analytics Hub
with tabs[4]:
    # แบ่งเป็น 3 คอลัมน์ [1.2, 0.6, 1.2]
    col_left, col_mid, col_right = st.columns([1.2, 0.6, 1.2], gap="large")
    
    with col_left:
        st.markdown("##### 🎲 Monte Carlo Simulation")
        # จำลอง Monte Carlo
        num_simulations = 100
        sims = [np.cumsum(np.random.normal(scale=20000, size=num_trades)) + capital for _ in range(num_simulations)]
        
        fig_mc = go.Figure()
        for s in sims:
            fig_mc.add_trace(go.Scatter(y=s, mode='lines', line=dict(width=0.8, color='#58a6ff'), opacity=0.12, showlegend=False))
            
        fig_mc.update_layout(
            height=450, margin=dict(l=0, r=0, b=0, t=10), template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title="Number of Trades", yaxis_title="Portfolio Value (THB)",
            xaxis=dict(gridcolor='#21262d'), yaxis=dict(gridcolor='#21262d')
        )
        st.plotly_chart(fig_mc, use_container_width=True)

    with col_mid:
        win_r = 58.4
        pf = 2.14
        avg_pnl = 12450
        max_dd = -8.2

        st.markdown(f"""
            <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 30px;">
                <div class="analytics-card">
                    <p style="color: #8b949e; margin: 0; font-size: 13px;">Win Rate</p>
                    <h2 style="color: #2ea043; margin: 0; font-size: 24px;">{win_r:.1f}%</h2>
                </div>
                <div class="analytics-card">
                    <p style="color: #8b949e; margin: 0; font-size: 13px;">Profit Factor</p>
                    <h2 style="color: #2ea043; margin: 0; font-size: 24px;">{pf:.2f}</h2>
                </div>
                <div class="analytics-card">
                    <p style="color: #8b949e; margin: 0; font-size: 13px;">Avg Trade P/L</p>
                    <h2 style="color: #2ea043; margin: 0; font-size: 24px;">{avg_pnl:,.0f} <span style="font-size: 14px; color:#e1e4e8">THB</span></h2>
                </div>
                <div class="analytics-card" style="border-left-color: #f85149;">
                    <p style="color: #8b949e; margin: 0; font-size: 13px;">Max Drawdown</p>
                    <h2 style="color: #f85149; margin: 0; font-size: 24px;">{max_dd:.1f}%</h2>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_right:
        st.markdown("##### 📈 Equity Curve")
        st.markdown(f"**Final Balance (Net)**: <span style='color:#2ea043; font-size: 18px;'>{final_capital:,.2f} THB</span>", unsafe_allow_html=True)
        
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(x=td_df['Date'], y=td_df['Equity'], name='Net Equity', 
                                    line=dict(color='#39d353', width=1.5), fill='tozeroy', fillcolor='rgba(57, 211, 83, 0.08)'))
        
        # เพิ่มคำอธิบายประกอบ
        fig_eq.add_annotation(
            x=td_df['Date'].iloc[-1],
            y=td_df['Equity'].iloc[-1],
            text="Net Equity",
            showarrow=True,
            arrowhead=1,
            ax=30,
            ay=-30,
            font=dict(color="#39d353")
        )

        fig_eq.update_layout(
            height=400, margin=dict(l=0, r=0, b=0, t=10), template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title="Date", yaxis_title="Portfolio Value (THB)",
            xaxis=dict(gridcolor='#21262d'), yaxis=dict(gridcolor='#21262d')
        )
        st.plotly_chart(fig_eq, use_container_width=True)

    # แถบ Status ด้านล่าง
    st.markdown("""
        <div class="system-verified-bar">
            ✅ <span class="verified-text">System Alpha Verified</span>
        </div>
    """, unsafe_allow_html=True)

# --- 5. ท้ายหน้า ---
st.divider()
# Gold Trophy Icon & Title in caption
st.caption("""
    <div style="display: flex; align-items: center; justify-content: start;">
        <span style="font-size: 16px; color: gold; margin-right: 5px;">🏆</span>
        <span style="font-size: 14px; color: #8b949e;">The Masterpiece | Institutional Systematic OS</span>
    </div>
""", unsafe_allow_html=True)
