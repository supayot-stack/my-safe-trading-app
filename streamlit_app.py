import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil
from datetime import datetime, timedelta

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="The Masterpiece | Secure OS", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #e1e4e8; }
    .stTabs [data-baseweb="tab-list"] { gap: 15px; background-color: transparent; border-bottom: 1px solid #21262d; }
    .stTabs [data-baseweb="tab"] { background-color: transparent !important; color: #8b949e !important; padding: 12px 0px !important; }
    .stTabs [aria-selected="true"] { color: #ffffff !important; border-bottom: 2px solid #58a6ff !important; font-weight: 500 !important; }
    .analytics-card { background-color: #161b22; padding: 15px; border-radius: 6px; border: 1px solid #21262d; margin-bottom: 10px; }
    .status-critical { color: #f85149; font-weight: bold; }
    .status-ok { color: #39d353; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIG & SAFETY PARAMETERS ---
DB_FILE = "the_masterpiece_v3.json"
BAK_FILE = "the_masterpiece_v3.json.bak"
COMMISSION_RATE = 0.0015 
MAX_CAP_PER_STOCK = 0.20  # 🛡️ ห้ามลงเงินเกิน 20% ของพอร์ตในตัวเดียว
STALE_DATA_THRESHOLD_DAYS = 3 # 🛡️ ข้อมูลเก่าเกิน 3 วันถือว่าอันตราย

@st.cache_data(ttl=3600)
def get_live_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", interval="1m", progress=False)
        if not data.empty: return float(data['Close'].iloc[-1])
    except Exception as e:
        st.sidebar.error(f"FX Fetch Error: {e}")
    return 36.5 

LIVE_USDTHB = get_live_fx()

def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except Exception as e:
            st.error(f"Database Load Error: {e}")
            return {}
    return {}

def save_portfolio(data):
    try:
        with open(DB_FILE, "w") as f: json.dump(data, f)
        shutil.copy(DB_FILE, BAK_FILE)
    except Exception as e:
        st.error(f"Database Save Error: {e}")

def format_ticker(ticker):
    ticker = ticker.upper().strip()
    if not ticker: return None
    thai_popular = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB", "OR", "IVL", "BDMS", "CPN", "PTTEP", "MINT"]
    if ticker in thai_popular and not ticker.endswith(".BK"): return ticker + ".BK"
    return ticker

# --- 3. CORE QUANT ENGINE (Enhanced) ---
@st.cache_data(ttl=1800)
def fetch_all_data(tickers):
    if not tickers: return {}
    try:
        raw_data = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            try:
                df = raw_data.xs(t, axis=1, level=1).copy() if isinstance(raw_data.columns, pd.MultiIndex) else raw_data.copy()
                if df.empty or len(df) < 50: continue
                
                # 🛡️ Safety Check: ข้อมูลเก่าไปไหม?
                last_date = df.index[-1].to_pydatetime()
                if (datetime.now() - last_date).days > STALE_DATA_THRESHOLD_DAYS:
                    st.warning(f"⚠️ {t} data is stale (Last: {last_date.date()})")
                
                # Indicators
                df['SMA200'] = df['Close'].rolling(200, min_periods=1).mean()
                df['SMA50'] = df['Close'].rolling(50, min_periods=1).mean()
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
                tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
                df['ATR'] = tr.rolling(14, min_periods=1).mean()
                
                # Trailing SL
                sl_raw = df['Close'] - (df['ATR'] * 2.5)
                tsl = np.zeros(len(df)); tsl[0] = sl_raw.iloc[0]
                for i in range(1, len(df)):
                    tsl[i] = max(tsl[i-1], sl_raw.iloc[i]) if df['Close'].iloc[i-1] > tsl[i-1] else sl_raw.iloc[i]
                df['Trailing_SL'] = tsl
                df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20, min_periods=1).mean().replace(0, np.nan)
                processed[t] = df.ffill().bfill()
            except Exception: continue
        return processed
    except Exception as e:
        st.error(f"Data Fetch Critical Error: {e}")
        return {}

# --- 4. SIDEBAR ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.title("🏆 The Masterpiece")
    st.markdown("`Institutional Systematic OS`")
    st.divider()
    
    # 🛡️ System Health
    health_status = "ONLINE" if not (datetime.now().hour > 23 or datetime.now().hour < 1) else "MARKET CLOSED"
    st.markdown(f"System Health: <span class='status-ok'>{health_status}</span>", unsafe_allow_html=True)
    st.info(f"💵 FX Rate: **{LIVE_USDTHB:.2f} THB**")
    
    capital = st.number_input("Total Capital (THB):", value=1000000, step=50000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    watchlist_input = st.text_area("Watchlist (CSV):", "NVDA, AAPL, PTT, DELTA, BTC-USD, IVL.BK")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))

# --- 5. SIGNAL PROCESSING (With Safety Cap) ---
data_dict = fetch_all_data(final_watchlist)
results = []
for t in final_watchlist:
    if t not in data_dict: continue
    df = data_dict[t]; curr = df.iloc[-1]; prev = df.iloc[-2]; p = curr['Close']
    
    # Logic
    is_bullish = p > curr['SMA200'] and p > curr['SMA50']
    is_pullback = prev['RSI'] < 48 and curr['RSI'] > prev['RSI']
    is_liquid = curr['Vol_Ratio'] > 1.1
    
    sig = "⚪ WAIT"
    if is_bullish and is_pullback and is_liquid: sig = "🟢 ACCUMULATE"
    elif curr['RSI'] > 82: sig = "💰 TAKE PROFIT"
    elif p < curr['SMA200']: sig = "🔴 RISK OFF"
    
    is_thai = ".BK" in t or (t.isalpha() and len(t) <= 5 and "USD" not in t)
    fx = 1 if is_thai else LIVE_USDTHB
    
    # 🛡️ Enhanced Position Sizing with Max Cap
    sl_gap = max(p - curr['Trailing_SL'], p * 0.01) # Minimum 1% stop for safety
    raw_qty = (capital * (risk_pct/100) / fx) / sl_gap
    
    # Apply 20% Capital Cap
    max_qty_allowed = (capital * MAX_CAP_PER_STOCK / fx) / p
    final_qty = min(raw_qty, max_qty_allowed)
    
    qty_display = int(final_qty) if fx > 1 else int(final_qty // 100) * 100
    results.append({"Asset": t, "Price": round(p, 2), "Regime": sig, "RSI": round(curr['RSI'], 1), "Target Qty": qty_display, "Currency": "THB" if is_thai else "USD"})

# --- 6. MAIN DISPLAY ---
tabs = st.tabs(["🏛 Scanner", "📉 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics Hub", "📖 Guide"])

with tabs[0]:
    st.subheader("📊 Tactical Opportunities")
    if results: 
        res_df = pd.DataFrame(results)
        st.dataframe(res_df.style.applymap(lambda x: 'color: #39d353' if x == '🟢 ACCUMULATE' else ('color: #f85149' if x == '🔴 RISK OFF' else ''), subset=['Regime']), use_container_width=True, hide_index=True)
    else: st.warning("Waiting for data...")

with tabs[1]:
    if data_dict:
        sel = st.selectbox("Analyze Asset:", list(data_dict.keys()), key="dive_sel")
        df_p = data_dict[sel]
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.35])
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='Inst. Trend', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['Trailing_SL'], name='TSL', line=dict(color='red', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Vol', marker_color='#c0c0c0', opacity=0.4), row=3, col=1)
        fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,b=0,t=20), paper_bgcolor="#0d1117", plot_bgcolor="#0d1117")
        st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.subheader("💼 Active Position Log")
    with st.expander("➕ Log New Trade"):
        c1, c2, c3 = st.columns(3)
        p_asset = c1.selectbox("Asset", list(data_dict.keys()) if data_dict else ["None"])
        p_entry, p_qty = c2.number_input("Entry Price", 0.0), c3.number_input("Quantity", 0)
        if st.button("Commit to Portfolio") and p_asset != "None":
            st.session_state.my_portfolio[p_asset] = {"entry": p_entry, "qty": p_qty}
            save_portfolio(st.session_state.my_portfolio); st.rerun()
    if st.session_state.my_portfolio:
        p_list = []
        for a, i in st.session_state.my_portfolio.items():
            if a in data_dict:
                curr_p = data_dict[a]['Close'].iloc[-1]
                is_thai = ".BK" in a or (a.isalpha() and len(a) <= 5 and "USD" not in a)
                fx_val = 1 if is_thai else LIVE_USDTHB
                pl_thb = (curr_p - i['entry']) * i['qty'] * fx_val
                p_list.append({"Asset": a, "Cost": i['entry'], "Price": curr_p, "Qty": i['qty'], "P/L (THB)": f"{pl_thb:,.2f}", "Status": "✅ HOLD" if curr_p > data_dict[a]['Trailing_SL'].iloc[-1] else "🚨 EXIT"})
        st.dataframe(pd.DataFrame(p_list), use_container_width=True, hide_index=True)
        if st.button("🗑️ Wipe Data"): save_portfolio({}); st.session_state.my_portfolio = {}; st.rerun()

with tabs[3]:
    st.header("🧪 Strategy Stress Test")
    sel_bt = st.selectbox("Select Target:", list(data_dict.keys()) if data_dict else ["None"], key="bt_sel")
    if sel_bt != "None" and sel_bt in data_dict:
        df_bt = data_dict[sel_bt].iloc[-500:].copy()
        is_thai = ".BK" in sel_bt or (sel_bt.isalpha() and len(sel_bt) <= 5 and "USD" not in sel_bt)
        fx_bt = 1 if is_thai else LIVE_USDTHB
        balance, pos, trades, entry_p = capital, 0, [], 0
        for i in range(1, len(df_bt)):
            c, p = df_bt.iloc[i], df_bt.iloc[i-1]
            if pos == 0 and c['Close'] > c['SMA200'] and p['RSI'] < 48 and c['Vol_Ratio'] > 1.1:
                # 🛡️ Apply safety cap in backtest too
                raw_pos = ((balance * (risk_pct/100)) / fx_bt) / max(c['Close'] - c['Trailing_SL'], 0.01)
                max_pos = (balance * MAX_CAP_PER_STOCK / fx_bt) / c['Close']
                pos = int(min(raw_pos, max_pos))
                entry_p = c['Close']; balance -= (entry_p * pos * COMMISSION_RATE * fx_bt)
                trades.append({"Type": "BUY", "Date": df_bt.index[i], "Price": entry_p})
            elif pos > 0 and (c['Close'] < c['Trailing_SL'] or c['RSI'] > 82):
                pnl = ((c['Close'] - entry_p) * pos * fx_bt) - (c['Close'] * pos * COMMISSION_RATE * fx_bt)
                balance += pnl; trades.append({"Type": "SELL", "Date": df_bt.index[i], "PnL": pnl, "Equity": balance})
                pos = 0
        if trades:
            td_df = pd.DataFrame([t for t in trades if "PnL" in t])
            st.metric("Net Terminal Value", f"{balance:,.2f} THB")
            st.plotly_chart(go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], name='Equity', line=dict(color='#00ff00'))), use_container_width=True)

with tabs[4]:
    if 'td_df' in locals() and not td_df.empty:
        col_left, col_mid, col_right = st.columns([1.2, 0.6, 1.2], gap="large")
        with col_left:
            st.markdown("##### 🎲 Monte Carlo Simulation")
            sims = [np.random.choice(td_df['PnL'].values, size=len(td_df), replace=True).cumsum() + capital for _ in range(100)]
            fig_mc = go.Figure()
            for s in sims: fig_mc.add_trace(go.Scatter(y=s, mode='lines', line=dict(width=0.8, color='#58a6ff'), opacity=0.12, showlegend=False))
            fig_mc.update_layout(height=450, margin=dict(l=0, r=0, b=0, t=10), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_mc, use_container_width=True)
        with col_mid:
            win_r = (len(td_df[td_df['PnL'] > 0]) / len(td_df)) * 100
            pf = td_df[td_df['PnL']>0]['PnL'].sum() / abs(td_df[td_df['PnL']<0]['PnL'].sum()) if any(td_df['PnL'] < 0) else 0
            max_dd = ((td_df['Equity'] - td_df['Equity'].cummax()) / td_df['Equity'].cummax()).min() * 100
            st.markdown(f"""
                <div class="analytics-card"><p style="color: #8b949e; font-size: 13px;">Win Rate</p><h2 style="color: #2ea043;">{win_r:.1f}%</h2></div>
                <div class="analytics-card"><p style="color: #8b949e; font-size: 13px;">Profit Factor</p><h2 style="color: #2ea043;">{pf:.2f}</h2></div>
                <div class="analytics-card" style="border-left: 3px solid #f85149;"><p style="color: #8b949e; font-size: 13px;">Max Drawdown</p><h2 style="color: #f85149;">{max_dd:.1f}%</h2></div>
            """, unsafe_allow_html=True)
        with col_right:
            st.markdown("##### 📈 Equity Curve")
            fig_eq = go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], line=dict(color='#39d353'), fill='tozeroy', fillcolor='rgba(57, 211, 83, 0.08)'))
            fig_eq.update_layout(height=400, margin=dict(l=0, r=0, b=0, t=10), template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_eq, use_container_width=True)

with tabs[5]:
    st.header("📖 Security & Logic Guide")
    st.warning("🛡️ **Safety Cap Active:** This system limits any single position to 20% of total capital to mitigate Gap Risk.")
    st.markdown("""
    1. **Trend Guard:** SMA 200/50 cross confirms institutional trend.
    2. **Momentum:** RSI < 48 indicates pullback opportunity.
    3. **Stop Loss:** ATR-based dynamic stops adjust for market noise.
    """)

st.divider(); st.caption("🏆 The Masterpiece | Institutional Systematic OS v3.1 (Secure)")
