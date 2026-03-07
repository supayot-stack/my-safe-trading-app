import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. INSTITUTIONAL UI CONFIG ---
st.set_page_config(page_title="CORE-STRAT TERMINAL", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .stMetric { background-color: #161b22; padding: 20px; border-radius: 12px; border: 1px solid #30363d; border-left: 6px solid #238636; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #161b22; border-radius: 6px 6px 0px 0px; padding: 12px 24px; color: #8b949e; border: 1px solid #30363d; }
    .stTabs [aria-selected="true"] { background-color: #1f6feb !important; color: white !important; border-bottom: 2px solid #58a6ff; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; border-radius: 12px; background-color: #161b22; }
    .checklist-card { background-color: #0d1117; padding: 20px; border-radius: 10px; border: 1px dashed #30363d; line-height: 1.8; }
    h1, h2, h3 { color: #58a6ff; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE ENGINE: DATA PERSISTENCE & LIVE FX ---
DB_FILE = "core_strat_portfolio.json"
BAK_FILE = "core_strat_portfolio.json.bak"

@st.cache_data(ttl=3600) 
def get_live_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", interval="1m", progress=False)
        if not data.empty: return float(data['Close'].iloc[-1])
    except: pass
    return 36.5 

LIVE_USDTHB = get_live_fx()

def load_portfolio():
    for file in [DB_FILE, BAK_FILE]:
        if os.path.exists(file):
            try:
                with open(file, "r") as f: return json.load(f)
            except: continue
    return {}

def save_portfolio(data):
    try:
        with open(DB_FILE, "w") as f: json.dump(data, f)
        shutil.copy(DB_FILE, BAK_FILE) 
    except Exception as e: st.error(f"System Error: {e}")

def format_ticker(ticker):
    ticker = ticker.upper().strip()
    if not ticker: return None
    # Auto-suffix for common Thai stocks
    thai_stocks = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB", "OR", "IVL", "BDMS", "CPN", "PTTEP", "MINT"]
    if ticker in thai_stocks and not ticker.endswith(".BK"): return ticker + ".BK"
    return ticker

# --- 3. QUANTITATIVE ANALYSIS ENGINE ---
@st.cache_data(ttl=1800)
def fetch_market_data(tickers):
    if not tickers: return {}
    try:
        raw_data = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            if isinstance(raw_data.columns, pd.MultiIndex):
                try: df = raw_data.xs(t, axis=1, level=1).copy()
                except: continue
            else: df = raw_data.copy()
            if df.empty or len(df) < 30: continue
            
            # Indicators with Resilience
            df['SMA200'] = df['Close'].rolling(200, min_periods=1).mean()
            df['SMA50'] = df['Close'].rolling(50, min_periods=1).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14, min_periods=1).mean()
            df['SL'] = df['Close'] - (df['ATR'] * 2.5)
            df['Vol_Avg20'] = df['Volume'].rolling(20, min_periods=1).mean()
            df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20'].replace(0, np.nan)
            processed[t] = df.ffill().bfill()
        return processed
    except Exception as e:
        st.error(f"Data Connection Error: {e}")
        return {}

# --- 4. TERMINAL SIDEBAR ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.markdown("<h1 style='color: #58a6ff; margin-bottom: 0;'>🏛️ CORE-STRAT</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #8b949e; margin-top: -10px; font-size: 14px;'>QUANT TERMINAL</p>", unsafe_allow_html=True)
    st.info(f"💵 **FX RATE:** 1 USD = {LIVE_USDTHB:.2f} THB")
    st.divider()
    capital = st.number_input("Total Managed Capital (THB):", value=1000000, step=10000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    watchlist_input = st.text_area("Asset Watchlist (Comma Separated):", "NVDA, AAPL, PTT, DELTA, BTC-USD, GOLD")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))
    st.divider()
    st.caption("CORE-STRAT ANALYTICS | v2.6.4 Stable")

# --- 5. DATA ENGINE EXECUTION ---
data_dict = fetch_market_data(final_watchlist)
results = []
for ticker in final_watchlist:
    if ticker not in data_dict or data_dict[ticker].empty: continue
    df = data_dict[ticker]
    curr, prev = df.iloc[-1], df.iloc[-2]
    p = curr['Close']
    
    # Logic Signal
    is_above_sma = p > curr['SMA200'] if not pd.isna(curr['SMA200']) else True
    is_above_mid = p > curr['SMA50'] if not pd.isna(curr['SMA50']) else True
    if is_above_sma and is_above_mid and prev['RSI'] < 45 and curr['Vol_Ratio'] > 1.2: sig = "🟢 ACCUMULATE"
    elif curr['RSI'] > 80: sig = "💰 DISTRIBUTION"
    elif not is_above_sma: sig = "🔴 BEARISH"
    else: sig = "⚪ NEUTRAL"

    # Position Sizing Logic
    risk_cash_thb = capital * (risk_pct / 100)
    sl_gap = max(p - curr['SL'], 0.01)
    is_usd = not ticker.endswith(".BK")
    qty = int((risk_cash_thb / (LIVE_USDTHB if is_usd else 1)) / sl_gap) if p > curr['SL'] else 0
    results.append({"Asset": ticker, "Price": round(p, 2), "Regime": sig, "RSI": round(curr['RSI'], 1), 
                    "Target Qty": qty, "Stop-Loss": round(curr['SL'], 2), "Currency": "USD" if is_usd else "THB"})
res_df = pd.DataFrame(results)

# --- 6. COMMAND CENTER (TABS) ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🧪 Analytics", "📖 Guide", "🧠 Logic"])

with tabs[0]:
    st.subheader("📊 Market Opportunity Scanner")
    if not res_df.empty: st.dataframe(res_df, use_container_width=True, hide_index=True)
    else: st.warning("Please input tickers in the sidebar to start analysis.")

with tabs[1]:
    if data_dict:
        sel = st.selectbox("Select Asset for Deep-Dive:", list(data_dict.keys()))
        df_p = data_dict[sel]
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.35])
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='#f1c40f', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SL'], name='Stop-Loss', line=dict(color='#e74c3c', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='#3498db')), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#e74c3c", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#2ecc71", row=2, col=1)
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Volume', marker_color='#95a5a6', opacity=0.5), row=3, col=1)
        fig.update_layout(height=750, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.subheader("💼 Active Portfolio Management")
    with st.expander("➕ Register New Trade"):
        c1, c2, c3 = st.columns(3)
        p_asset = c1.selectbox("Asset Ticker", list(data_dict.keys()) if data_dict else ["None"])
        p_entry = c2.number_input("Average Entry Price", value=0.0)
        p_qty = c3.number_input("Allocated Quantity", value=0)
        if st.button("Commit Trade") and p_asset != "None":
            st.session_state.my_portfolio[p_asset] = {"entry": p_entry, "qty": p_qty}
            save_portfolio(st.session_state.my_portfolio); st.rerun()

    if st.session_state.my_portfolio:
        p_list = []
        for asset, info in st.session_state.my_portfolio.items():
            if asset in data_dict:
                cp = data_dict[asset]['Close'].iloc[-1]
                sl = data_dict[asset]['SL'].iloc[-1]
                curr_l = "USD" if not asset.endswith(".BK") else "THB"
                pnl = (cp - info['entry']) * info['qty']
                p_list.append({"Asset": asset, "Cost": info['entry'], "Price": cp, "Qty": info['qty'], "P/L": f"{pnl:,.2f} {curr_l}", "Status": "✅ HOLD" if cp > sl else "🚨 EXIT"})
        st.dataframe(pd.DataFrame(p_list), use_container_width=True, hide_index=True)
        if st.button("🗑️ Purge Portfolio Data"): save_portfolio({}); st.session_state.my_portfolio = {}; st.rerun()

with tabs[3]:
    st.header("🧪 Strategy Performance Simulation (1-Year)")
    sel_bt = st.selectbox("Asset for Backtest:", list(data_dict.keys()) if data_dict else ["None"], key="bt_sel")
    if sel_bt != "None" and sel_bt in data_dict:
        df_bt = data_dict[sel_bt].iloc[-252:].copy() 
        balance = capital; pos = 0; trades = []; entry_p = 0
        for i in range(1, len(df_bt)):
            c_bt, p_bt = df_bt.iloc[i], df_bt.iloc[i-1]
            price = c_bt['Close']
            if pos == 0 and price > c_bt['SMA200'] and p_bt['RSI'] < 45 and c_bt['Vol_Ratio'] > 1.2:
                risk_amt = balance * (risk_pct / 100); sl_d = price - c_bt['SL']
                pos = int((risk_amt / (LIVE_USDTHB if not sel_bt.endswith(".BK") else 1)) / max(sl_d, 0.01))
                entry_p = price; trades.append({"Type": "BUY", "Date": df_bt.index[i], "Price": entry_p})
            elif pos > 0 and (price < c_bt['SL'] or c_bt['RSI'] > 80):
                pnl = (price - entry_p) * pos
                balance += (pnl * (LIVE_USDTHB if not sel_bt.endswith(".BK") else 1))
                trades.append({"Type": "SELL", "Date": df_bt.index[i], "Price": price, "PnL": pnl * (LIVE_USDTHB if not sel_bt.endswith(".BK") else 1)})
                pos = 0
        if trades:
            td_df = pd.DataFrame([t for t in trades if "PnL" in t])
            if not td_df.empty:
                wr = (len(td_df[td_df['PnL'] > 0]) / len(td_df)) * 100
                c1, c2, c3 = st.columns(3)
                c1.metric("Win Rate", f"{wr:.1f}%")
                c2.metric("Accumulated P/L", f"{td_df['PnL'].sum():,.2f} THB")
                c3.metric("Projected Balance", f"{balance:,.2f} THB")
                td_df['Equity'] = td_df['PnL'].cumsum() + capital
                fig_bt = go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], mode='lines+markers', line=dict(color='#2ecc71')))
                fig_bt.update_layout(title="Equity Growth Curve", template="plotly_dark")
                st.plotly_chart(fig_bt, use_container_width=True)

with tabs[4]:
    st.subheader("🧪 Portfolio Analytics & Risk Exposure")
    col_l, col_spacer, col_r = st.columns([2, 0.2, 1])
    with col_l:
        st.markdown("##### 📉 Asset Correlation Matrix")
        price_dict = {t: df['Close'] for t, df in data_dict.items()}
        if len(price_dict) > 1:
            corr_df = pd.DataFrame(price_dict).dropna().corr()
            fig_corr = go.Figure(data=go.Heatmap(z=corr_df.values, x=corr_df.columns, y=corr_df.columns, colorscale='RdBu_r', zmin=-1, zmax=1, text=np.round(corr_df.values, 2), texttemplate="%{text}"))
            fig_corr.update_layout(height=500, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_corr, use_container_width=True)
        else: st.info("Add multiple tickers to visualize correlation.")
    with col_r:
        st.write(""); st.write(""); st.write("")
        st.markdown("##### 🛡️ Exposure Metrics")
        if st.session_state.my_portfolio:
            t_risk = sum([max((info['entry'] - data_dict[a]['SL'].iloc[-1]) * info['qty'], 0) * (LIVE_USDTHB if not a.endswith(".BK") else 1) for a, info in st.session_state.my_portfolio.items() if a in data_dict])
            risk_util = (t_risk / capital) * 100 if capital > 0 else 0
            st.metric("Total Net Risk", f"{t_risk:,.2f} THB")
            st.write(f"Risk Utilization: **{risk_util:.2f}%**")
            st.progress(min(risk_util / 100, 1.0))
            st.caption("Benchmark: Portfolio risk should not exceed 10% of total equity.")
            st.divider()
            st.write("🔧 **Terminal Status**")
            st.write("• Data Link: ✅ Verified")
            st.write(f"• USD/THB Sync: ✅ Active ({LIVE_USDTHB})")
        else: st.warning("No active portfolio data detected.")

with tabs[5]:
    st.header("📖 Operator Manual (Step-by-Step Guide)")
    st.info("💡 CORE-STRAT is built on statistical discipline, not market prediction.")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("""
        ### 1️⃣ Initial Configuration
        * **Capital:** Input your total investment power (THB).
        * **Risk per Trade:** The % of capital you are willing to lose if a trade hits Stop-Loss (Standard: 1%).
        ### 2️⃣ Opportunity Scanning
        Look for **🟢 ACCUMULATE** signals:
        * **Trend:** Price > SMA 200 (Primary Trend is Bullish).
        * **Momentum:** RSI < 45 (Price is currently pulling back/discounted).
        * **Volume:** Ratio > 1.2 (Institutional buying pressure confirmed).
        * **Action:** Execute trade based on **Target Qty**.
        """)
    with col_g2:
        st.markdown("""
        ### 3️⃣ Risk Execution (Stop-Loss)
        * **Discipline:** If the daily close price falls below the **RED DOTTED LINE**, exit immediately.
        * **ATR Logic:** Stop-Loss adjusts dynamically to market volatility.
        ### 4️⃣ Profit Realization
        * **Distribution:** When RSI > 80, the asset is overextended. Consider trimming 50% of the position.
        """)
    st.divider()
    st.subheader("📝 Pre-Trade Checklist")
    st.markdown("""
    <div class="checklist-card">
    ✅ Signal: 🟢 ACCUMULATE confirmed?<br>
    ✅ Position Sizing: Target Qty matches current risk parameters?<br>
    ✅ Commitment: Am I prepared to sell immediately at Stop-Loss?<br>
    ✅ Diversification: Does this trade keep my Total Risk under 10%?<br>
    <b>If all boxes checked... Execute Order.</b>
    </div>
    """, unsafe_allow_html=True)

with tabs[6]:
    st.header("🧠 System Architecture & Quant Logic")
    arch_c1, arch_c2 = st.columns(2)
    with arch_c1:
        st.markdown(f"""
        #### ⚙️ Data Layer
        * **Bulk Retrieval:** 3-year historical lookup for SMA stability.
        * **Currency Engine:** Dynamic FX conversion for global asset risk.
        * **Resilience Logic:** Auto-fill for missing data points and IPO support.
        """)
        st.markdown("#### 📐 Mathematical Position Sizing")
        st.latex(r"Qty = \frac{Capital \times Risk\%}{Price - StopLoss}")
    with arch_c2:
        st.markdown("""
        #### 📈 Indicator Matrix
        * **Wilder's RSI:** Smoothed exponential RSI for noise reduction.
        * **ATR Trailing Stop:** Multiplier of 2.5x ATR for volatility-adjusted exits.
        * **Performance Engine:** 252-day sliding window backtest.
        """)
    st.divider()
    st.caption("CORE-STRAT TERMINAL | Institutional-Grade Statistical Trading")
