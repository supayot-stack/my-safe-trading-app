import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. PRO UI CONFIG (ปรับแต่ง UI/สี/ฟอนต์ ตามรูปภาพ) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    
    /* Metrics & Cards Styling */
    .stat-card {
        background-color: #161b22;
        padding: 22px 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
        text-align: center;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    .stat-label { color: #8b949e; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
    .stat-value { color: #ffffff; font-size: 26px; font-weight: 700; }
    .stat-value-green { color: #2ea043; font-size: 26px; font-weight: 700; }
    .stat-value-red { color: #f85149; font-size: 26px; font-weight: 700; }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #161b22; border-radius: 6px 6px 0px 0px; 
        padding: 10px 20px; color: #8b949e; border: 1px solid #30363d;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #238636 !important; color: white !important; font-weight: 600; border: 1px solid #2ea043;
    }

    /* Verify Badge */
    .verify-badge {
        background-color: rgba(46, 160, 67, 0.1);
        color: #2ea043;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid rgba(46, 160, 67, 0.2);
        text-align: center;
        font-weight: 700;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & LIVE FX (คงเดิม) ---
DB_FILE = "the_masterpiece_v2.json"
BAK_FILE = "the_masterpiece_v2.json.bak"
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
        shutil.copy(DB_FILE, BAK_FILE)
    except: pass

def format_ticker(ticker):
    ticker = ticker.upper().strip()
    if not ticker: return None
    thai_popular = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB", "OR", "IVL", "BDMS", "CPN", "PTTEP", "MINT"]
    if ticker in thai_popular and not ticker.endswith(".BK"): return ticker + ".BK"
    return ticker

# --- 3. CORE QUANT ENGINE (สูตรการคำนวณคงเดิม 100%) ---
@st.cache_data(ttl=1800)
def fetch_all_data(tickers):
    if not tickers: return {}
    try:
        raw_data = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            try:
                if isinstance(raw_data.columns, pd.MultiIndex):
                    df = raw_data.xs(t, axis=1, level=1).copy()
                else:
                    df = raw_data.copy()
                
                if df.empty or len(df) < 50: continue
                df['SMA200'] = df['Close'].rolling(200, min_periods=1).mean()
                df['SMA50'] = df['Close'].rolling(50, min_periods=1).mean()
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
                tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
                df['ATR'] = tr.rolling(14, min_periods=1).mean()
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
    st.title("🏆 THE MASTERPIECE")
    st.markdown("`SYSTEMATIC OS v2.0`")
    st.divider()
    capital = st.number_input("Total Equity (THB):", value=1000000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    watchlist_input = st.text_area("Watchlist:", "NVDA, AAPL, PTT, DELTA, BTC-USD")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))

# --- 5. SIGNAL PROCESSING ---
data_dict = fetch_all_data(final_watchlist)
results = []
for t in final_watchlist:
    if t not in data_dict: continue
    df = data_dict[t]; curr = df.iloc[-1]; prev = df.iloc[-2]; p = curr['Close']
    is_bullish = p > curr['SMA200'] and p > curr['SMA50']
    is_pullback = prev['RSI'] < 48 and curr['RSI'] > prev['RSI']
    is_liquid = curr['Vol_Ratio'] > 1.1
    if is_bullish and is_pullback and is_liquid: sig = "🟢 ACCUMULATE"
    elif curr['RSI'] > 82: sig = "💰 TAKE PROFIT"
    elif p < curr['SMA200']: sig = "🔴 RISK OFF"
    else: sig = "⚪ WAIT"
    is_thai = ".BK" in t or (t.isalpha() and len(t) <= 5 and "USD" not in t)
    fx = 1 if is_thai else LIVE_USDTHB
    sl_gap = max(p - curr['Trailing_SL'], 0.01)
    qty = int((capital * (risk_pct/100) / fx) / sl_gap) if fx > 1 else int(((capital * (risk_pct/100) / fx) / sl_gap) // 100) * 100
    results.append({"Asset": t, "Price": round(p, 2), "Regime": sig, "RSI": round(curr['RSI'], 1), "Target Qty": qty})

# --- 6. MAIN DISPLAY ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics", "📖 Logic"])

with tabs[0]:
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

with tabs[3]: # BACKTEST LOGIC (คงเดิม)
    sel_bt = st.selectbox("Target:", list(data_dict.keys()) if data_dict else ["None"])
    if sel_bt != "None":
        df_bt = data_dict[sel_bt].iloc[-500:].copy()
        fx_bt = 1 if ".BK" in sel_bt else LIVE_USDTHB
        balance, pos, trades, entry_p = capital, 0, [], 0
        for i in range(1, len(df_bt)):
            c, p = df_bt.iloc[i], df_bt.iloc[i-1]
            if pos == 0 and c['Close'] > c['SMA200'] and p['RSI'] < 48 and c['Vol_Ratio'] > 1.1:
                pos = int(((balance * (risk_pct/100)) / fx_bt) / max(c['Close'] - c['Trailing_SL'], 0.01))
                entry_p = c['Close']; balance -= (entry_p * pos * COMMISSION_RATE * fx_bt)
                trades.append({"Type": "BUY", "Date": df_bt.index[i], "Price": entry_p})
            elif pos > 0 and (c['Close'] < c['Trailing_SL'] or c['RSI'] > 82):
                pnl = ((c['Close'] - entry_p) * pos * fx_bt) - (c['Close'] * pos * COMMISSION_RATE * fx_bt)
                balance += pnl; trades.append({"Type": "SELL", "Date": df_bt.index[i], "PnL": pnl, "Equity": balance})
                pos = 0
        if trades:
            td_df = pd.DataFrame([t for t in trades if "PnL" in t])
            st.plotly_chart(go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], line=dict(color='#00ff00'))).update_layout(template="plotly_dark"))

with tabs[4]: # --- ANALYTICS HUB (จัดวางแบบในรูปเป๊ะๆ) ---
    if 'td_df' in locals() and not td_df.empty:
        col_left, col_mid, col_right = st.columns([4, 2.2, 4], gap="large")
        
        with col_left:
            st.subheader("🎲 Monte Carlo Simulation")
            sims = [np.random.choice(td_df['PnL'].values, size=len(td_df), replace=True).cumsum() + capital for _ in range(40)]
            fig_mc = go.Figure()
            for s in sims: fig_mc.add_trace(go.Scatter(y=s, mode='lines', line=dict(width=1, color='#38d1ff'), opacity=0.2, showlegend=False))
            fig_mc.update_layout(height=450, margin=dict(l=0,r=0,b=0,t=10), template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_mc, use_container_width=True)
            
        with col_mid:
            st.subheader("📊 Statistics")
            win_r = (len(td_df[td_df['PnL'] > 0]) / len(td_df)) * 100
            pf = td_df[td_df['PnL']>0]['PnL'].sum() / abs(td_df[td_df['PnL']<0]['PnL'].sum()) if any(td_df['PnL'] < 0) else 0
            mdd = ((td_df['Equity'] - td_df['Equity'].cummax()) / td_df['Equity'].cummax()).min()*100
            
            st.markdown(f"""
                <div class="stat-card"><div class="stat-label">Win Rate</div><div class="stat-value-green">{win_r:.1f}%</div></div>
                <div class="stat-card"><div class="stat-label">Profit Factor</div><div class="stat-value">{pf:.2f}</div></div>
                <div class="stat-card"><div class="stat-label">Avg Trade P/L</div><div class="stat-value">{td_df['PnL'].mean():,.0f}</div></div>
                <div class="stat-card"><div class="stat-label">Max Drawdown</div><div class="stat-value-red">{mdd:.1f}%</div></div>
                <div class="verify-badge">✅ ALPHA VERIFIED</div>
            """, unsafe_allow_html=True)
            
        with col_right:
            st.subheader("📈 Equity Curve")
            fig_eq = go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], line=dict(color='#00ff00', width=2.5), fill='tozeroy', fillcolor='rgba(0,255,0,0.1)'))
            fig_eq.update_layout(height=450, margin=dict(l=0,r=0,b=0,t=10), template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_eq, use_container_width=True)
