import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. TERMINAL UI STYLE ---
st.set_page_config(page_title="Institutional Quant V4", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .status-box { 
        background-color: #161b22; padding: 15px; border-radius: 8px; 
        border: 1px solid #30363d; border-left: 5px solid #58a6ff;
    }
    .metric-title { color: #8b949e; font-size: 0.9em; }
    .metric-value { color: #ffffff; font-size: 1.2em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ADVANCED QUANT ENGINE ---
@st.cache_data(ttl=3600)
def get_advanced_data(ticker):
    try:
        # Smart Thai Ticker
        thai_core = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB", "BDMS", "GULF"]
        if ticker in thai_core and "." not in ticker: ticker += ".BK"

        df = yf.download(ticker, period="2y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # A. Dual Trend + ADX (Trend Strength)
        df['SMA200'] = df['Close'].rolling(200).mean()
        df['SMA50'] = df['Close'].rolling(50).mean()
        
        # ADX Calculation (Trend Strength)
        plus_dm = df['High'].diff().clip(lower=0)
        minus_dm = (-df['Low'].diff()).clip(lower=0)
        tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        atr_adx = tr.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).mean() / atr_adx)
        minus_di = 100 * (minus_dm.rolling(14).mean() / atr_adx)
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        df['ADX'] = dx.rolling(14).mean()

        # B. RSI & ATR
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
        df['ATR'] = tr.rolling(14).mean()

        # C. Institutional Levels
        df['SL'] = df['Close'] - (df['ATR'] * 2.5)
        df['TP'] = df['Close'] + (df['ATR'] * 5.0) 
        
        # D. Volume Flow
        df['Vol_Avg20'] = df['Volume'].rolling(20).mean()
        df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20']

        return df.dropna()
    except: return None

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🏦 Institutional Port")
    total_fund = st.number_input("Equity (THB):", value=1000000, step=50000)
    risk_limit = st.slider("Risk Limit per Trade (%)", 0.1, 3.0, 1.0, 0.1)
    
    st.divider()
    watchlist = st.multiselect("Watchlist:", ["NVDA", "AAPL", "BTC-USD", "SET50.BK", "GOLD"], default=["NVDA", "BTC-USD"])
    custom = st.text_input("➕ Add Ticker:").upper().strip()
    
    all_assets = list(watchlist)
    if custom and custom not in all_assets: all_assets.append(custom)

# --- 4. MAIN TERMINAL ---
tab1, tab2 = st.tabs(["🏛 Quant Scanner", "📊 Advanced Analytics"])

scan_results = []
if all_assets:
    for t in all_assets:
        df = get_advanced_data(t)
        if df is not None:
            l = df.iloc[-1]
            p, r, s200, s50, vr, adx = l['Close'], l['RSI'], l['SMA200'], l['SMA50'], l['Vol_Ratio'], l['ADX']
            
            # Logic Upgrade: ADX > 20 (Must have trend) + Price > SMA + RSI Low + Vol Surge
            if p > s200 and p > s50 and r < 45 and vr > 1.1 and adx > 20:
                signal = "🟢 ACCUMULATE"
            elif r > 75: signal = "💰 DISTRIBUTION"
            elif p < s200: signal = "🔴 BEARISH"
            elif adx <= 20: signal = "⚪ SIDEWAY"
            else: signal = "⚪ NEUTRAL"

            # Position Size Calculation
            risk_cash = total_fund * (risk_limit / 100)
            sl_dist = p - l['SL']
            qty = int(risk_cash / sl_dist) if sl_dist > 0 else 0
            qty = min(qty, int(total_fund / p))

            scan_results.append({
                "Asset": t, "Price": round(p, 2), "Signal": signal,
                "ADX": f"{int(adx)}", "Vol-R": f"{vr:.1f}x", "Qty": qty,
                "Exp.Profit": f"{(qty * (l['TP']-p)):,.0f}", "Max Loss": f"{(qty * sl_dist):,.0f}",
                "SL": round(l['SL'], 2), "TP": round(l['TP'], 2)
            })

with tab1:
    st.subheader("🏛 Institutional Order Flow")
    if scan_results:
        st.dataframe(pd.DataFrame(scan_results), use_container_width=True, hide_index=True)
        
        # Portfolio Summary
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Capital", f"{total_fund:,.0f}")
        with c2: st.metric("Risk Budget", f"{(total_fund*(risk_limit/100)):,.0f}")
        with c3: 
            strong_buys = sum(1 for x in scan_results if "ACCUMULATE" in x['Signal'])
            st.metric("Strong Buys", strong_buys)
        with c4:
            total_invest = sum(float(x['Price']) * x['Qty'] for x in scan_results if "ACCUMULATE" in x['Signal'])
            st.metric("Potential Investment", f"{total_invest:,.0f}")

with tab2:
    if scan_results:
        sel = st.selectbox("Select Asset for Deep Analysis:", [r['Asset'] for r in scan_results])
        df_p = get_advanced_data(sel)
        
        if df_p is not None:
            # Bloomberg-Style Terminal Chart
            fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.02, row_heights=[0.4, 0.15, 0.15, 0.3])
            
            # Row 1: Price + SMA + Institutional SL
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='#ffcc00', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SL'], name='Stop Loss', line=dict(color='#f85149', dash='dot')), row=1, col=1)
            
            # Row 2: RSI
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='#58a6ff')), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="#f85149", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#3fb950", row=2, col=1)

            # Row 3: ADX (Trend Strength)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['ADX'], name='ADX (Strength)', fill='tozeroy', line=dict(color='#bc8cff')), row=3, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="#8b949e", row=3, col=1)

            # Row 4: Volume Force
            v_colors = ['#3fb950' if c >= o else '#f85149' for o, c in zip(df_p['Open'], df_p['Close'])]
            fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Volume', marker_color=v_colors), row=4, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['Vol_Avg20'], name='Avg Vol (20)', line=dict(color='white', width=1)), row=4, col=1)

            fig.update_layout(height=900, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # Insight Box
            t_data = next(i for i in scan_results if i["Asset"] == sel)
            st.markdown(f"""
                <div class="status-box">
                    <h4>🏛 Institutional Insight: {sel}</h4>
                    <div style="display:flex; justify-content:space-between;">
                        <div><span class="metric-title">Market Signal:</span> <br><span class="metric-value">{t_data['Signal']}</span></div>
                        <div><span class="metric-title">Trend Strength (ADX):</span> <br><span class="metric-value">{t_data['ADX']}</span></div>
                        <div><span class="metric-title">Volume Flow:</span> <br><span class="metric-value">{t_data['Vol-R']}</span></div>
                        <div><span class="metric-title">Risk/Reward:</span> <br><span class="metric-value">1 : 2.0</span></div>
                    </div>
                    <hr style="border:0.1px solid #30363d">
                    <p>🎯 แผนการเข้าเทรด: ซื้อ <b>{t_data['Qty']}</b> หุ้น | วาง SL ที่ <b>{t_data['SL']}</b> | เป้าหมายกำไร <b>{t_data['TP']}</b></p>
                </div>
            """, unsafe_allow_html=True)

if st.button("🔄 Sync Terminal"): st.rerun()
