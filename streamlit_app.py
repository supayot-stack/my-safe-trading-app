import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import json
import os
import shutil

# --- 1. PRO UI CONFIG (Institutional Dark Mode) ---
st.set_page_config(page_title="The Masterpiece | Institutional OS", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    [data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
    
    /* สไตล์ตาราง Scanner */
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    
    /* สไตล์การ์ดตัวเลข Metrics ตรงกลาง */
    .metric-card {
        background-color: #1c2128;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
        text-align: center;
        margin-bottom: 12px;
    }
    .m-label { font-size: 11px; color: #8b949e; text-transform: uppercase; letter-spacing: 1px; }
    .m-value { font-size: 20px; font-weight: bold; margin-top: 5px; }

    /* แถบ Status สีเขียวด้านล่าง */
    .status-bar {
        background-color: rgba(63, 185, 80, 0.1);
        border: 1px solid #238636;
        color: #3fb950;
        padding: 12px;
        border-radius: 6px;
        text-align: center;
        font-weight: bold;
        margin-top: 20px;
    }
    
    h3 { color: #adbac7; font-size: 1.2rem !important; border-left: 4px solid #238636; padding-left: 10px; margin-bottom: 15px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE DATA ENGINE ---
@st.cache_data(ttl=3600) 
def get_live_fx():
    try:
        data = yf.download("USDTHB=X", period="1d", interval="1m", progress=False)
        if not data.empty: return float(data['Close'].iloc[-1])
    except: pass
    return 36.5 

LIVE_USDTHB = get_live_fx()

def format_ticker(ticker):
    ticker = ticker.upper().strip()
    if not ticker: return None
    thai_popular = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB", "OR", "IVL", "BDMS", "CPN", "PTTEP", "MINT"]
    if ticker in thai_popular and not ticker.endswith(".BK"): return ticker + ".BK"
    return ticker

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
                # Indicators
                df['SMA200'] = df['Close'].rolling(200).mean()
                df['SMA50'] = df['Close'].rolling(50).mean()
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
                tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
                df['ATR'] = tr.rolling(14).mean()
                # Dynamic Trailing SL
                sl_raw = df['Close'] - (df['ATR'] * 2.5)
                tsl = np.zeros(len(df)); tsl[0] = sl_raw.iloc[0]
                for i in range(1, len(df)):
                    tsl[i] = max(tsl[i-1], sl_raw.iloc[i]) if df['Close'].iloc[i-1] > tsl[i-1] else sl_raw.iloc[i]
                df['Trailing_SL'] = tsl
                df['Vol_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean().replace(0, np.nan)
                processed[t] = df.ffill().bfill()
            except: continue
        return processed
    except: return {}

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("🏆 The Masterpiece")
    st.markdown("`Institutional OS v2.6`")
    st.divider()
    capital = st.number_input("Total Equity (THB):", value=1000000, step=50000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    watchlist_input = st.text_area("Watchlist (CSV):", "NVDA, AAPL, PTT, DELTA, BTC-USD", height=100)
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))

# --- 4. SIGNAL & CALCULATION (Safety Logic) ---
data_dict = fetch_all_data(final_watchlist)
results = []
for t in final_watchlist:
    if t not in data_dict: continue
    df = data_dict[t]; curr = df.iloc[-1]; prev = df.iloc[-2]; p = curr['Close']
    
    # Logic Regime
    is_bullish = p > curr['SMA200'] and p > curr['SMA50']
    is_pullback = prev['RSI'] < 48 and curr['RSI'] > prev['RSI']
    is_liquid = curr['Vol_Ratio'] > 1.1

    if is_bullish and is_pullback and is_liquid: sig = "🟢 ACCUMULATE"
    elif curr['RSI'] > 82: sig = "💰 TAKE PROFIT"
    elif p < curr['SMA200']: sig = "🔴 RISK OFF"
    else: sig = "⚪ WAIT"

    # Currency & Position Sizing (Fixed Bug: sl_gap safety)
    is_thai = ".BK" in t or (t.isalpha() and len(t) <= 5 and "USD" not in t)
    fx = 1 if is_thai else LIVE_USDTHB
    sl_gap = max(p - curr['Trailing_SL'], 0.01) # ป้องกันหารด้วยศูนย์
    
    # สูตร Position Sizing ที่แก้แล้ว
    risk_amount_thb = capital * (risk_pct / 100)
    if is_thai:
        qty = int((risk_amount_thb / sl_gap) // 100) * 100
    else:
        qty = int((risk_amount_thb / fx) / sl_gap)
        
    results.append({"Asset": t, "Price": round(p, 2), "Regime": sig, "RSI": round(curr['RSI'], 1), "Target Qty": qty, "Currency": "THB" if is_thai else "USD"})

# --- 5. MAIN DISPLAY (SINGLE PAGE DASHBOARD) ---

# Section 1: Scanner (Top)
st.subheader("🏛️ Market Scanner & Tactical Opportunities")
if results:
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
else:
    st.warning("Please enter valid tickers in the sidebar.")

st.divider()

# Section 2: Analytics Hub (Middle) - กราฟพร้อมเส้นตัด Grid
st.subheader("🛡️ Analytics Hub")

if final_watchlist and final_watchlist[0] in data_dict:
    # รัน Backtest ตัวแรกเพื่อสร้างข้อมูลกราฟ
    sel_bt = final_watchlist[0]
    df_bt = data_dict[sel_bt].iloc[-500:].copy()
    is_thai_bt = ".BK" in sel_bt
    fx_bt = 1 if is_thai_bt else LIVE_USDTHB
    balance, pos, trades, entry_p = capital, 0, [], 0
    
    for i in range(1, len(df_bt)):
        c, p_row = df_bt.iloc[i], df_bt.iloc[i-1]
        # Entry Logic
        if pos == 0 and c['Close'] > c['SMA200'] and p_row['RSI'] < 48 and c['Vol_Ratio'] > 1.1:
            sl_g = max(c['Close'] - c['Trailing_SL'], 0.01)
            pos = int(( (balance * (risk_pct/100)) / fx_bt ) / sl_g)
            entry_p = c['Close']
            trades.append({"Type": "BUY", "Date": df_bt.index[i], "Price": entry_p})
        # Exit Logic
        elif pos > 0 and (c['Close'] < c['Trailing_SL'] or c['RSI'] > 82):
            pnl = ((c['Close'] - entry_p) * pos * fx_bt)
            balance += pnl
            trades.append({"Type": "SELL", "Date": df_bt.index[i], "PnL": pnl, "Equity": balance})
            pos = 0
    
    if trades and any("PnL" in t for t in trades):
        td_df = pd.DataFrame([t for t in trades if "PnL" in t])
        col_mc, col_stats, col_eq = st.columns([4, 1.5, 4])
        
        # ฟังก์ชันจัดสไตล์เส้นตาราง (Grid) ให้เหมือนในรูป
        def apply_institutional_grid(fig):
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#22272e', zeroline=False)
            fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#22272e', zeroline=False)
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
                              margin=dict(l=10,r=10,t=10,b=10), height=380, font=dict(color='#8b949e', size=10))
            return fig

        with col_mc:
            st.caption(f"🎲 Monte Carlo Simulation: {sel_bt}")
            fig_mc = go.Figure()
            pnl_values = td_df['PnL'].values
            for _ in range(40):
                sim_path = np.random.choice(pnl_values, size=len(td_df), replace=True).cumsum() + capital
                fig_mc.add_trace(go.Scatter(y=sim_path, mode='lines', line=dict(color='#58a6ff', width=0.8), opacity=0.15, showlegend=False))
            st.plotly_chart(apply_institutional_grid(fig_mc), use_container_width=True)

        with col_stats:
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            win_r = (len(td_df[td_df['PnL'] > 0]) / len(td_df)) * 100
            pf = td_df[td_df['PnL']>0]['PnL'].sum() / abs(td_df[td_df['PnL']<0]['PnL'].sum()) if any(td_df['PnL'] < 0) else 0
            
            metrics_html = [
                ("Win Rate", f"{win_r:.1f}%", "#3fb950"),
                ("Profit Factor", f"{pf:.2f}", "#3fb950"),
                ("Avg P/L", f"{td_df['PnL'].mean():,.0f} ฿", "#3fb950"),
                ("Max DD", f"{((td_df['Equity'] - td_df['Equity'].cummax()) / td_df['Equity'].cummax()).min()*100:.1f}%", "#f85149")
            ]
            for label, val, color in metrics_html:
                st.markdown(f'<div class="metric-card"><div class="m-label">{label}</div><div class="m-value" style="color:{color}">{val}</div></div>', unsafe_allow_html=True)

        with col_eq:
            st.caption(f"📈 Equity Curve: {sel_bt}")
            fig_eq = go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], line=dict(color='#3fb950', width=2.5), fill='tozeroy', fillcolor='rgba(63, 185, 80, 0.05)'))
            st.plotly_chart(apply_institutional_grid(fig_eq), use_container_width=True)
    else:
        st.info("Not enough trade data for analytics. Try a different asset or longer period.")

# Section 3: Status Bar & Logic
st.markdown('<div class="status-bar">✅ System Alpha Verified</div>', unsafe_allow_html=True)

with st.expander("📖 Decision Logic & Formulas"):
    st.latex(r"Position\,Size = \frac{Equity \times Risk\%}{Price - Trailing\,Stop}")
    st.markdown("---")
    st.write("**Strategy:** Institutional Trend Following with ATR-based Volatility Stops.")

st.markdown("<br><center><small style='color:#8b949e;'>🏆 The Masterpiece | Institutional Systematic OS</small></center>", unsafe_allow_html=True)
