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
st.set_page_config(page_title="Ultimate Quant Terminal", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; border-left: 5px solid #00ff00; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #161b22; border-radius: 4px 4px 0px 0px; padding: 10px 20px; color: #8b949e; }
    .stTabs [aria-selected="true"] { background-color: #1f6feb !important; color: white !important; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & LIVE FX ---
DB_FILE = "ultimate_quant_data.json"
BAK_FILE = "ultimate_quant_data.json.bak"
COMMISSION_RATE = 0.0015  # ค่าธรรมเนียม 0.15%

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
    except Exception as e: st.error(f"Error saving: {e}")

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
        # ดึงข้อมูล 3 ปีเพื่อให้ SMA200 เสถียร
        raw_data = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            if isinstance(raw_data.columns, pd.MultiIndex):
                try: df = raw_data.xs(t, axis=1, level=1).copy()
                except: continue
            else: df = raw_data.copy()
            
            # ป้องกัน IndexError โดยตรวจสอบข้อมูลขั้นต่ำ (ต้องมี SMA200)
            if df.empty or len(df) < 250: continue
            
            # คำนวณ Indicators
            df['SMA200'] = df['Close'].rolling(200).mean()
            df['SMA50'] = df['Close'].rolling(50).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            
            # Trailing Stop Logic (Ratchet)
            df['Base_SL'] = df['Close'] - (df['ATR'] * 2.5)
            sl_v, cl_v = df['Base_SL'].values, df['Close'].values
            trailing_sl = np.zeros_like(sl_v)
            trailing_sl[0] = sl_v[0]
            for i in range(1, len(sl_v)):
                trailing_sl[i] = max(trailing_sl[i-1], sl_v[i]) if cl_v[i-1] > trailing_sl[i-1] else sl_v[i]
            df['Trailing_SL'] = trailing_sl
            df['Vol_Avg20'] = df['Volume'].rolling(20).mean()
            df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20'].replace(0, np.nan)
            processed[t] = df.ffill().dropna()
        return processed
    except Exception as e:
        st.error(f"Fetch Error: {e}"); return {}

# --- 4. SIDEBAR ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.title("🛡️ Ultimate Quant")
    st.info(f"💵 1 USD = **{LIVE_USDTHB:.2f} THB**")
    capital = st.number_input("Total Capital (THB):", value=1000000, step=10000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    watchlist_input = st.text_area("Tickers:", "NVDA, AAPL, PTT, DELTA, BTC-USD, GOLD")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))

# --- 5. DATA PROCESSING & SIGNAL SCANNER ---
data_dict = fetch_all_data(final_watchlist)
results = []
for ticker in final_watchlist:
    if ticker not in data_dict or len(data_dict[ticker]) < 2: continue
    df = data_dict[ticker]
    curr, prev = df.iloc[-1], df.iloc[-2]
    p = curr['Close']
    
    # Decision Engine Logic
    if p > curr['SMA200'] and p > curr['SMA50'] and prev['RSI'] < 45 and curr['Vol_Ratio'] > 1.2: sig = "🟢 ACCUMULATE"
    elif curr['RSI'] > 80: sig = "💰 DISTRIBUTION"
    elif p < curr['SMA200']: sig = "🔴 BEARISH"
    else: sig = "⚪ NEUTRAL"

    risk_cash_thb = capital * (risk_pct / 100)
    sl_gap = max(p - curr['Trailing_SL'], 0.01)
    fx_m = LIVE_USDTHB if not ticker.endswith(".BK") else 1
    qty = int((risk_cash_thb / fx_m) / sl_gap) if fx_m > 1 else int(((risk_cash_thb / fx_m) / sl_gap) // 100) * 100

    results.append({"Asset": ticker, "Price": round(p, 2), "Regime": sig, "RSI": round(curr['RSI'], 1), 
                    "Target Qty": qty, "Trailing SL": round(curr['Trailing_SL'], 2), "Currency": "USD" if fx_m > 1 else "THB"})
res_df = pd.DataFrame(results)

# --- 6. MAIN TERMINAL ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics (Tap 6)", "📖 Guide & Logic (Tap 7)"])

with tabs[0]:
    st.subheader("📊 Market Opportunities")
    if not res_df.empty: st.dataframe(res_df, use_container_width=True, hide_index=True)
    else: st.warning("กรุณาระบุ Ticker ใน Sidebar")

with tabs[1]:
    if data_dict:
        sel = st.selectbox("Analyze Asset:", list(data_dict.keys()))
        df_p = data_dict[sel]
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.5, 0.15, 0.35])
        fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='yellow')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['Trailing_SL'], name='Trailing SL', line=dict(color='red', dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
        fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Volume', marker_color='#c0c0c0', opacity=0.6), row=3, col=1)
        fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

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
        p_list = [{"Asset": a, "Cost": i['entry'], "Price": data_dict[a]['Close'].iloc[-1], "Qty": i['qty'], "Status": "✅ HOLD" if data_dict[a]['Close'].iloc[-1] > data_dict[a]['Trailing_SL'].iloc[-1] else "🚨 EXIT"} for a, i in st.session_state.my_portfolio.items() if a in data_dict]
        st.dataframe(pd.DataFrame(p_list), use_container_width=True, hide_index=True)
        if st.button("🗑️ Reset"): save_portfolio({}); st.session_state.my_portfolio = {}; st.rerun()

with tabs[3]:
    st.header("🧪 Backtest (Net of Commissions)")
    sel_bt = st.selectbox("เลือกสินทรัพย์:", list(data_dict.keys()) if data_dict else ["None"], key="bt_sel")
    if sel_bt != "None" and sel_bt in data_dict:
        df_bt = data_dict[sel_bt].iloc[-500:].copy(); fx_mult = LIVE_USDTHB if not sel_bt.endswith(".BK") else 1
        balance, pos, trades, entry_p = capital, 0, [], 0
        for i in range(1, len(df_bt)):
            c_bt, p_bt = df_bt.iloc[i], df_bt.iloc[i-1]
            if pos == 0 and c_bt['Close'] > c_bt['SMA200'] and p_bt['RSI'] < 45 and c_bt['Vol_Ratio'] > 1.2:
                pos = int(((balance * (risk_pct/100)) / fx_mult) / max(c_bt['Close'] - c_bt['Trailing_SL'], 0.01))
                entry_p = c_bt['Close']; balance -= (entry_p * pos * COMMISSION_RATE * fx_mult) # Buy Fee
                trades.append({"Type": "BUY", "Date": df_bt.index[i], "Price": entry_p})
            elif pos > 0 and (c_bt['Close'] < c_bt['Trailing_SL'] or c_bt['RSI'] > 80):
                pnl = ((c_bt['Close'] - entry_p) * pos * fx_mult) - (c_bt['Close'] * pos * COMMISSION_RATE * fx_mult) # Sell Fee
                balance += pnl; trades.append({"Type": "SELL", "Date": df_bt.index[i], "PnL": pnl, "Equity": balance})
                pos = 0
        if trades:
            td_df = pd.DataFrame([t for t in trades if "PnL" in t])
            if not td_df.empty:
                st.metric("Final Balance (Net)", f"{balance:,.2f} THB")
                st.plotly_chart(go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], mode='lines', line=dict(color='#00ff00'))), use_container_width=True)

with tabs[4]:
    st.header("🛡️ Tap 6: Advanced Analytics")
    if 'td_df' in locals() and not td_df.empty:
        col_m1, col_m2 = st.columns([2, 1])
        with col_m1:
            st.subheader("🎲 Monte Carlo Simulation (1,000 Runs)")
            sims = [np.random.choice(td_df['PnL'].values, size=len(td_df), replace=True).cumsum() + capital for _ in range(1000)]
            fig_mc = go.Figure()
            for s in sims[:100]: fig_mc.add_trace(go.Scatter(y=s, mode='lines', line=dict(width=0.5), opacity=0.2, showlegend=False))
            fig_mc.update_layout(title="ความน่าจะเป็นของพอร์ตในอนาคต", template="plotly_dark")
            st.plotly_chart(fig_mc, use_container_width=True)
        with col_m2:
            pf = td_df[td_df['PnL']>0]['PnL'].sum() / abs(td_df[td_df['PnL']<0]['PnL'].sum())
            st.metric("Profit Factor", f"{pf:.2f}")
            st.metric("Max Drawdown", f"{((td_df['Equity'] - td_df['Equity'].cummax()) / td_df['Equity'].cummax()).min()*100:.2f}%")
            st.metric("Expectancy", f"{td_df['PnL'].mean():,.2f} THB")
    else: st.info("กรุณารัน Backtest เพื่อดูวิเคราะห์เชิงลึก")

with tabs[5]:
    st.header("📖 Tap 7: Ultimate Guide & Logic")
    st.markdown("### 📐 สูตรคำนวณไม้เทรด (Position Sizing)")
    st.latex(r"Qty = \frac{Capital \times Risk\%}{Price - Trailing\,SL}")
    st.info("💡 กลยุทธ์นี้เน้น 'การเทรดด้วยสถิติ' ไม่ใช่ความรู้สึก")
    st.markdown("""
    * **🟢 Accumulate:** เข้าซื้อเมื่อราคาย่อตัวลงในแนวโน้มขาขึ้น (Buy the Dip)
    * **🛡️ Trailing Stop:** กำแพงราคาขยับขึ้นตามจุดสูงสุดเพื่อ Lock กำไร และป้องกันเงินต้น
    * **🎲 Monte Carlo:** ใช้การสุ่มลำดับผลกำไรในอดีตเพื่อทดสอบว่าระบบจะทนต่อสภาวะแพ้ติดกันได้หรือไม่
    * **💸 Commissions:** รวมค่าธรรมเนียม 0.15% ทั้งขาซื้อและขาย เพื่อความสมจริงของกำไรสุทธิ
    """)

st.divider(); st.caption("Ultimate Quant Terminal | Built for Professional Systematic Trading")
