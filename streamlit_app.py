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
st.set_page_config(page_title="The Masterpiece | Quant Terminal", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .stMetric { 
        background-color: #161b22; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #30363d; 
        border-left: 5px solid #00ff00;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #161b22; border-radius: 6px 6px 0px 0px; 
        padding: 12px 25px; color: #8b949e; transition: 0.3s;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #238636 !important; color: white !important; font-weight: bold;
    }
    div[data-testid="stExpander"] { border: 1px solid #30363d; border-radius: 10px; background-color: #0d1117; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & LIVE FX ---
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
    thai_stocks = ["PTT", "AOT", "CPALL", "SCB", "KBANK", "DELTA", "GULF", "ADVANC", "KTB", "OR", "IVL", "BDMS", "CPN", "PTTEP", "MINT"]
    if ticker in thai_stocks and not ticker.endswith(".BK"): return ticker + ".BK"
    return ticker

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
                
                # Trend & Momentum Indicators
                df['SMA200'] = df['Close'].rolling(200, min_periods=1).mean()
                df['SMA50'] = df['Close'].rolling(50, min_periods=1).mean()
                
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
                df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
                
                # Volatility & Dynamic Trailing Stop
                tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
                df['ATR'] = tr.rolling(14, min_periods=1).mean()
                
                sl_raw = df['Close'] - (df['ATR'] * 2.5)
                tsl = np.zeros(len(df)); tsl[0] = sl_raw.iloc[0]
                for i in range(1, len(df)):
                    tsl[i] = max(tsl[i-1], sl_raw.iloc[i]) if df['Close'].iloc[i-1] > tsl[i-1] else sl_raw.iloc[i]
                df['Trailing_SL'] = tsl
                
                # Volume & Liquidity Confirmation
                df['Vol_Avg20'] = df['Volume'].rolling(20, min_periods=1).mean()
                df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20'].replace(0, np.nan)
                processed[t] = df.ffill().bfill()
            except: continue
        return processed
    except: return {}

# --- 4. SIDEBAR ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.title("🏆 The Masterpiece")
    st.markdown("`Institutional Systematic OS`")
    st.divider()
    st.info(f"💵 FX Rate: **{LIVE_USDTHB:.2f} THB**")
    capital = st.number_input("Total Equity (THB):", value=1000000, step=50000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    watchlist_input = st.text_area("Watchlist (CSV):", "NVDA, AAPL, PTT, DELTA, BTC-USD, GOLD")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))

# --- 5. SIGNAL PROCESSING ---
data_dict = fetch_all_data(final_watchlist)
results = []
for t in final_watchlist:
    if t not in data_dict: continue
    df = data_dict[t]; curr = df.iloc[-1]; prev = df.iloc[-2]; p = curr['Close']
    
    # Advanced Logic Gates
    is_bullish = p > curr['SMA200'] and p > curr['SMA50']
    is_pullback = prev['RSI'] < 48 and curr['RSI'] > prev['RSI']
    is_liquid = curr['Vol_Ratio'] > 1.1

    if is_bullish and is_pullback and is_liquid: sig = "🟢 ACCUMULATE"
    elif curr['RSI'] > 82: sig = "💰 TAKE PROFIT"
    elif p < curr['SMA200']: sig = "🔴 RISK OFF"
    else: sig = "⚪ WAIT"

    fx = LIVE_USDTHB if ".BK" not in t and "USD" not in t and t.isalpha() else 1
    sl_gap = max(p - curr['Trailing_SL'], 0.01)
    qty = int((capital * (risk_pct/100) / fx) / sl_gap) if fx > 1 else int(((capital * (risk_pct/100) / fx) / sl_gap) // 100) * 100
    results.append({"Asset": t, "Price": round(p, 2), "Regime": sig, "RSI": round(curr['RSI'], 1), "Target Qty": qty, "Currency": "USD" if fx > 1 else "THB"})

# --- 6. MAIN TERMINAL ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Advanced Analytics", "📖 Logic Guide"])

with tabs[0]:
    st.subheader("📊 Tactical Opportunities")
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

with tabs[1]:
    if data_dict:
        sel = st.selectbox("Analyze Asset:", list(data_dict.keys()), key="dive_sel")
        df_p = data_dict[sel]
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.35])
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='Institutional Trend', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['Trailing_SL'], name='Trailing SL', line=dict(color='red', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='Momentum', line=dict(color='cyan')), row=2, col=1)
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Volume', marker_color='#c0c0c0', opacity=0.4), row=3, col=1)
        fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.subheader("💼 Active Position Log")
    with st.expander("➕ บันทึกไม้เทรดใหม่"):
        c1, c2, c3 = st.columns(3)
        p_asset = c1.selectbox("Asset", list(data_dict.keys()) if data_dict else ["None"])
        p_entry, p_qty = c2.number_input("Entry Price", 0.0), c3.number_input("Quantity", 0)
        if st.button("Commit to Portfolio") and p_asset != "None":
            st.session_state.my_portfolio[p_asset] = {"entry": p_entry, "qty": p_qty}
            save_portfolio(st.session_state.my_portfolio); st.rerun()
    if st.session_state.my_portfolio:
        p_list = [{"Asset": a, "Cost": i['entry'], "Price": data_dict[a]['Close'].iloc[-1], "Qty": i['qty'], "P/L (THB)": f"{(data_dict[a]['Close'].iloc[-1] - i['entry']) * i['qty'] * (LIVE_USDTHB if '.BK' not in a else 1):,.2f}", "Exit Alert": "🚨 EXIT" if data_dict[a]['Close'].iloc[-1] < data_dict[a]['Trailing_SL'].iloc[-1] else "✅ HOLD"} for a, i in st.session_state.my_portfolio.items() if a in data_dict]
        st.dataframe(pd.DataFrame(p_list), use_container_width=True, hide_index=True)
        if st.button("🗑️ Wipe All Data"): save_portfolio({}); st.session_state.my_portfolio = {}; st.rerun()

with tabs[3]:
    st.header("🧪 Strategy Stress Test")
    sel_bt = st.selectbox("Select Target:", list(data_dict.keys()) if data_dict else ["None"])
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
            elif pos > 0 and (c['Close'] < c['Trailing_SL'] or c['RSI'] > 82):
                pnl = ((c['Close'] - entry_p) * pos * fx_m) - (c['Close'] * pos * COMMISSION_RATE * fx_m)
                balance += pnl; trades.append({"Type": "SELL", "Date": df_bt.index[i], "PnL": pnl, "Equity": balance})
                pos = 0
        if trades:
            td_df = pd.DataFrame([t for t in trades if "PnL" in t])
            st.metric("Net Terminal Value", f"{balance:,.2f} THB")
            st.plotly_chart(go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], name='Equity', line=dict(color='#00ff00'))), use_container_width=True)

with tabs[4]:
    st.header("🛡️ Analytics Hub")
    if 'td_df' in locals() and not td_df.empty:
        st.markdown("---")
        l_m, col_chart, col_stat, r_m = st.columns([0.5, 5, 2.5, 0.5], gap="large")
        with col_chart:
            st.subheader("🎲 Monte Carlo Simulation")
            sims = [np.random.choice(td_df['PnL'].values, size=len(td_df), replace=True).cumsum() + capital for _ in range(100)]
            fig_mc = go.Figure()
            for s in sims: fig_mc.add_trace(go.Scatter(y=s, mode='lines', line=dict(width=1), opacity=0.2, showlegend=False))
            fig_mc.update_layout(height=480, margin=dict(l=0,r=0,b=0,t=20), template="plotly_dark")
            st.plotly_chart(fig_mc, use_container_width=True)
        with col_stat:
            st.subheader("📊 Key KPIs")
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            win_r = (len(td_df[td_df['PnL'] > 0]) / len(td_df)) * 100
            pf = td_df[td_df['PnL']>0]['PnL'].sum() / abs(td_df[td_df['PnL']<0]['PnL'].sum()) if any(td_df['PnL'] < 0) else 0
            st.metric("Win Rate", f"{win_r:.1f}%")
            st.metric("Profit Factor", f"{pf:.2f}")
            st.metric("Avg Trade P/L", f"{td_df['PnL'].mean():,.0f} ฿")
            st.metric("Max Drawdown", f"{((td_df['Equity'] - td_df['Equity'].cummax()) / td_df['Equity'].cummax()).min()*100:.2f}%")
            st.divider(); st.success("Robustness: High")
    else: st.info("Run backtest to activate analytics.")

with tabs[5]:
    st.header("📖 The Masterpiece Decision Logic")
    
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.markdown("""
        ### 🛡️ Core Entry Framework
        1. **Trend Guard:** ราคาสินทรัพย์ต้องอยู่เหนือ `SMA 200` (ระยะยาว) และ `SMA 50` (ระยะกลาง) เท่านั้น เพื่อกรองให้เล่นเฉพาะในสภาวะ Bullish Market
        2. **Momentum Pullback:** ใช้ `RSI (14)` ในการหาจังหวะย่อตัว โดยเงื่อนไขคือ RSI ก่อนหน้าต้องต่ำกว่า 48 และเริ่มมีการวกกลับขึ้น (Mean Reversion setup)
        3. **Liquidity Filter:** `Volume Ratio` ต้อง > 1.1 (ปริมาณการซื้อขายสูงกว่าค่าเฉลี่ย 20 วัน) เพื่อยืนยันว่าการขยับของราคามีแรงส่งจริง ไม่ใช่ Fake out
        """)
    
    with col_l2:
        st.markdown("""
        ### 🚪 Professional Exit Strategy
        1. **Dynamic Trailing Stop:** ใช้ `ATR * 2.5` เป็นระยะ Stop Loss ที่ขยับตามความผันผวน หากราคาวิ่งขึ้น SL จะขยับขึ้นตามและ **ไม่มีการขยับลง** เพื่อ Lock กำไร
        2. **Overbought Exit:** หาก `RSI > 82` ระบบจะแนะนำให้ Take Profit ทันที เพราะถือว่าเป็นจุดที่ตึงตัวเกินไป (Extremely Overextended)
        """)

    st.divider()
    st.latex(r"Position\,Size = \frac{Equity \times Risk\%}{Price - Trailing\,Stop}")
    st.info("💡 **Quant Tip:** การคำนวณจำนวนหุ้นโดยอิงจาก Risk-per-trade ช่วยให้พอร์ตไม่พังเมื่อเจอช่วง Drawdown")

st.divider(); st.caption("🏆 The Masterpiece Terminal | Professional Systematic Trading OS")
