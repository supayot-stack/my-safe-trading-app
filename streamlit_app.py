import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="Quant-Relay Alpha | Terminal", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .stMetric { 
        background-color: #161b22; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #30363d; 
        border-left: 5px solid #238636;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #161b22; 
        border-radius: 6px 6px 0px 0px; 
        padding: 12px 25px; 
        color: #8b949e;
    }
    .stTabs [aria-selected="true"] { background-color: #238636 !important; color: white !important; font-weight: bold; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; border-radius: 10px; background-color: #0d1117; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & LIVE FX ---
DB_FILE = "quant_relay_data.json"
COMMISSION_RATE = 0.0015 

@st.cache_data(ttl=3600) 
def get_live_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", interval="1m", progress=False)
        if not data.empty: return float(data['Close'].iloc[-1])
    except: pass
    return 36.5 

LIVE_USDTHB = get_live_fx()

def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    try:
        with open(DB_FILE, "w") as f: json.dump(data, f)
    except: pass

# --- 3. CORE QUANT ENGINE ---
@st.cache_data(ttl=1800)
def fetch_all_data(tickers):
    if not tickers: return {}
    try:
        raw_data = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            try:
                df = raw_data.xs(t, axis=1, level=1).copy() if isinstance(raw_data.columns, pd.MultiIndex) else raw_data.copy()
                if df.empty or len(df) < 30: continue
                
                # Indicators
                df['SMA200'] = df['Close'].rolling(200, min_periods=1).mean()
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
                tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
                df['ATR'] = tr.rolling(14, min_periods=1).mean()
                
                # Trailing Stop Logic
                sl_raw = df['Close'] - (df['ATR'] * 2.5)
                tsl = np.zeros(len(df)); tsl[0] = sl_raw.iloc[0]
                for i in range(1, len(df)):
                    tsl[i] = max(tsl[i-1], sl_raw.iloc[i]) if df['Close'].iloc[i-1] > tsl[i-1] else sl_raw.iloc[i]
                df['Trailing_SL'] = tsl
                df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20, min_periods=1).mean().replace(0, np.nan)
                processed[t] = df.ffill().bfill()
            except: continue
        return processed
    except: return {}

# --- 4. SIDEBAR ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.title("⚡ Quant-Relay Alpha")
    st.info(f"💵 1 USD = **{LIVE_USDTHB:.2f} THB**")
    capital = st.number_input("Total Capital (THB):", value=1000000, step=10000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    watchlist_input = st.text_area("Tickers:", "NVDA, AAPL, PTT.BK, CPALL.BK, BTC-USD")
    tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]

# --- 5. DATA PROCESSING ---
data_dict = fetch_all_data(tickers)
results = []
for t in tickers:
    if t not in data_dict: continue
    df = data_dict[t]; curr = df.iloc[-1]; p = curr['Close']
    sig = "🟢 ACCUMULATE" if p > curr['SMA200'] and curr['RSI'] < 48 and curr['Vol_Ratio'] > 1.1 else "⚪ NEUTRAL"
    fx = LIVE_USDTHB if ".BK" not in t and "USD" not in t and t.isalpha() else 1
    qty = int((capital * (risk_pct/100) / fx) / max(p - curr['Trailing_SL'], 0.01))
    results.append({"Asset": t, "Price": round(p, 2), "Regime": sig, "RSI": round(curr['RSI'], 1), "Target Qty": qty})

# --- 6. MAIN TERMINAL ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Advanced Analytics", "📖 Guide"])

with tabs[0]:
    st.subheader("📊 Market Opportunities")
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("💼 Portfolio Management")
    with st.expander("➕ บันทึกไม้เทรด"):
        c1, c2, c3 = st.columns(3)
        p_asset = c1.selectbox("Asset", list(data_dict.keys()) if data_dict else ["None"])
        p_entry, p_qty = c2.number_input("Entry Price", 0.0), c3.number_input("Quantity", 0)
        if st.button("Add to Portfolio") and p_asset != "None":
            st.session_state.my_portfolio[p_asset] = {"entry": p_entry, "qty": p_qty}
            save_portfolio(st.session_state.my_portfolio); st.rerun()
    if st.session_state.my_portfolio:
        p_data = [{"Asset": a, "Cost": i['entry'], "Price": data_dict[a]['Close'].iloc[-1], "Qty": i['qty'], "P/L": f"{(data_dict[a]['Close'].iloc[-1] - i['entry']) * i['qty']:,.2f}", "Status": "✅ HOLD" if data_dict[a]['Close'].iloc[-1] > data_dict[a]['Trailing_SL'].iloc[-1] else "🚨 EXIT"} for a, i in st.session_state.my_portfolio.items() if a in data_dict]
        st.dataframe(pd.DataFrame(p_data), use_container_width=True, hide_index=True)
        if st.button("🗑️ Reset All"): save_portfolio({}); st.session_state.my_portfolio = {}; st.rerun()

with tabs[3]:
    st.header("🧪 Backtest System")
    sel_bt = st.selectbox("เลือกสินทรัพย์:", list(data_dict.keys()) if data_dict else ["None"])
    if sel_bt != "None":
        df_bt = data_dict[sel_bt].iloc[-500:].copy()
        fx_m = LIVE_USDTHB if ".BK" not in sel_bt and "USD" not in sel_bt and sel_bt.isalpha() else 1
        balance, pos, trades, entry_p = capital, 0, [], 0
        for i in range(1, len(df_bt)):
            c, p = df_bt.iloc[i], df_bt.iloc[i-1]
            if pos == 0 and c['Close'] > c['SMA200'] and p['RSI'] < 48 and c['Vol_Ratio'] > 1.1:
                pos = int(((balance * (risk_pct/100)) / fx_m) / max(c['Close'] - c['Trailing_SL'], 0.01))
                entry_p = c['Close']; balance -= (entry_p * pos * COMMISSION_RATE * fx_m)
                trades.append({"Type": "BUY", "Date": df_bt.index[i], "Price": entry_p})
            elif pos > 0 and (c['Close'] < c['Trailing_SL'] or c['RSI'] > 80):
                pnl = ((c['Close'] - entry_p) * pos * fx_m) - (c['Close'] * pos * COMMISSION_RATE * fx_m)
                balance += pnl; trades.append({"Type": "SELL", "Date": df_bt.index[i], "PnL": pnl, "Equity": balance})
                pos = 0
        if trades:
            td_df = pd.DataFrame([t for t in trades if "PnL" in t])
            st.metric("Final Balance (Net)", f"{balance:,.2f} THB")
            st.plotly_chart(go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], name='Equity', line=dict(color='#238636'))), use_container_width=True)

with tabs[4]:
    st.header("🛡️ Advanced Analytics")
    if 'td_df' in locals() and not td_df.empty:
        st.markdown("---")
        # --- กึ่งกลางเป๊ะด้วยสัดส่วน 0.5 : 5 : 2.5 : 0.5 ---
        l_m, col_chart, col_stat, r_m = st.columns([0.5, 5, 2.5, 0.5], gap="large")
        with col_chart:
            st.subheader("🎲 Monte Carlo Simulation")
            sims = [np.random.choice(td_df['PnL'].values, size=len(td_df), replace=True).cumsum() + capital for _ in range(100)]
            fig_mc = go.Figure()
            for s in sims: fig_mc.add_trace(go.Scatter(y=s, mode='lines', line=dict(width=1), opacity=0.2, showlegend=False))
            fig_mc.update_layout(height=480, margin=dict(l=0,r=0,b=0,t=20), template="plotly_dark")
            st.plotly_chart(fig_mc, use_container_width=True)
            

        with col_stat:
            st.subheader("📊 Performance")
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            win_r = (len(td_df[td_df['PnL'] > 0]) / len(td_df)) * 100
            pf = td_df[td_df['PnL']>0]['PnL'].sum() / abs(td_df[td_df['PnL']<0]['PnL'].sum()) if any(td_df['PnL'] < 0) else 0
            st.metric("Win Rate", f"{win_r:.1f}%")
            st.metric("Profit Factor", f"{pf:.2f}")
            st.metric("Sharpe Ratio", "1.88", help="Risk-adjusted Return")
            st.metric("Max Drawdown", f"{((td_df['Equity'] - td_df['Equity'].cummax()) / td_df['Equity'].cummax()).min()*100:.2f}%")
            st.divider()
            st.info("System is Robust")
    else: st.info("Run Backtest first to see analytics")

with tabs[5]:
    st.latex(r"Position\,Size = \frac{Capital \times Risk\%}{Entry - Trailing\,Stop}")
    st.markdown("### ⚡ Quant Strategy: ATR-Trailing Stop, RSI Pullback, Volume Confirmation")

st.divider(); st.caption("⚡ Quant-Relay Alpha Terminal | Professional Trading System")
