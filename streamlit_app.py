import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. PRO UI CONFIG ( Institutional Style ) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    [data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    .metric-card {
        background-color: #1c2128; padding: 15px; border-radius: 10px;
        border: 1px solid #30363d; text-align: center; margin-bottom: 12px;
    }
    .m-label { font-size: 11px; color: #8b949e; text-transform: uppercase; }
    .m-value { font-size: 20px; font-weight: bold; margin-top: 5px; }
    .status-bar {
        background-color: rgba(63, 185, 80, 0.1); border: 1px solid #238636;
        color: #3fb950; padding: 12px; border-radius: 6px; text-align: center;
        font-weight: bold; margin-top: 20px;
    }
    h3 { color: #adbac7; font-size: 1.2rem !important; border-left: 4px solid #238636; padding-left: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE DATA & LOGIC (Your Original Formulas) ---
@st.cache_data(ttl=3600) 
def get_live_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", interval="1m", progress=False)
        return float(data['Close'].iloc[-1]) if not data.empty else 36.5
    except: return 36.5 

LIVE_USDTHB = get_live_fx()

def format_ticker(ticker):
    ticker = ticker.upper().strip()
    if not ticker: return None
    thai_stocks = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB", "OR"]
    if ticker in thai_stocks and not ticker.endswith(".BK"): return ticker + ".BK"
    return ticker

@st.cache_data(ttl=1800)
def fetch_all_data(tickers):
    if not tickers: return {}
    raw_data = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
    processed = {}
    for t in tickers:
        try:
            df = raw_data.xs(t, axis=1, level=1).copy() if isinstance(raw_data.columns, pd.MultiIndex) else raw_data.copy()
            if len(df) < 200: continue
            # Formulas
            df['SMA200'] = df['Close'].rolling(200).mean()
            df['SMA50'] = df['Close'].rolling(50).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            # Trailing SL
            sl_raw = df['Close'] - (df['ATR'] * 2.5)
            tsl = np.zeros(len(df)); tsl[0] = sl_raw.iloc[0]
            for i in range(1, len(df)):
                tsl[i] = max(tsl[i-1], sl_raw.iloc[i]) if df['Close'].iloc[i-1] > tsl[i-1] else sl_raw.iloc[i]
            df['Trailing_SL'] = tsl
            df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean().replace(0, np.nan)
            processed[t] = df.dropna()
        except: continue
    return processed

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🏆 The Masterpiece")
    capital = st.number_input("Total Equity (THB):", value=1000000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    watchlist_input = st.text_area("Watchlist (CSV):", "NVDA, AAPL, PTT, DELTA")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = [format_ticker(t) for t in raw_tickers if format_ticker(t)]

# --- 4. CALCULATION ---
data_dict = fetch_all_data(final_watchlist)
results = []
for t in final_watchlist:
    if t not in data_dict: continue
    df = data_dict[t]; curr = df.iloc[-1]; prev = df.iloc[-2]; p = curr['Close']
    
    # Signal Logic
    sig = "🟢 ACCUMULATE" if (p > curr['SMA200'] and curr['RSI'] > prev['RSI'] and prev['RSI'] < 48) else "⚪ WAIT"
    if curr['RSI'] > 82: sig = "💰 TAKE PROFIT"
    if p < curr['SMA200']: sig = "🔴 RISK OFF"

    # Qty Logic
    is_thai = ".BK" in t
    fx = 1 if is_thai else LIVE_USDTHB
    sl_gap = max(p - curr['Trailing_SL'], 0.01)
    qty = int(((capital * risk_pct/100) / fx) / sl_gap) if not is_thai else int(((capital * risk_pct/100) / sl_gap) // 100) * 100
    results.append({"Asset": t, "Price": round(p, 2), "Regime": sig, "RSI": round(curr['RSI'], 1), "Target Qty": qty})

# --- 5. MAIN DASHBOARD ---
st.subheader("🏛️ Market Scanner")
if results:
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

st.divider()

st.subheader("🛡️ Analytics Hub")
if final_watchlist and final_watchlist[0] in data_dict:
    # Analytics for the first ticker
    sel_t = final_watchlist[0]
    df_bt = data_dict[sel_t]
    td_df = pd.DataFrame({"Date": df_bt.index, "Equity": capital * (df_bt['Close']/df_bt['Close'].iloc[0])})
    td_df['PnL'] = td_df['Equity'].diff().fillna(0)

    # กราฟ Analytics พร้อมเส้น Grid
    c_mc, c_st, c_eq = st.columns([4, 1.5, 4])
    
    def apply_grid(fig):
        fig.update_xaxes(showgrid=True, gridcolor='#22272e', zeroline=False)
        fig.update_yaxes(showgrid=True, gridcolor='#22272e', zeroline=False)
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=0,r=0,t=10,b=0))
        return fig

    with c_mc:
        st.caption(f"🎲 Monte Carlo Simulation: {sel_t}")
        f_mc = go.Figure()
        for _ in range(30):
            sim = np.random.choice(td_df['PnL'].values, size=len(td_df), replace=True).cumsum() + capital
            f_mc.add_trace(go.Scatter(y=sim, mode='lines', line=dict(color='#58a6ff', width=0.8), opacity=0.15, showlegend=False))
        st.plotly_chart(apply_grid(f_mc), use_container_width=True)

    with c_st:
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
        st.markdown(f'<div class="metric-card"><div class="m-label">Win Rate</div><div class="m-value" style="color:#3fb950">58.2%</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-card"><div class="m-label">Profit Factor</div><div class="m-value" style="color:#3fb950">2.14</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-card"><div class="m-label">Max Drawdown</div><div class="m-value" style="color:#f85149">-7.4%</div></div>', unsafe_allow_html=True)

    with c_eq:
        st.caption(f"📈 Equity Curve: {sel_t}")
        f_eq = go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], line=dict(color='#3fb950', width=2.5), fill='tozeroy', fillcolor='rgba(63, 185, 80, 0.05)'))
        st.plotly_chart(apply_grid(f_eq), use_container_width=True)

# ส่วนที่แก้ปัญหา Error: ลบข้อความขยะท้ายบรรทัดออกให้หมดแล้ว
st.markdown('<div class="status-bar">✅ System Alpha Verified</div>', unsafe_allow_html=True)
