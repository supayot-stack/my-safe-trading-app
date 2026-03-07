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
st.set_page_config(page_title="Ultimate Quant Terminal v3.0", layout="wide")
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
DB_FILE = "ultimate_quant_v3.json"
BAK_FILE = "ultimate_quant_v3.json.bak"
COMMISSION_RATE = 0.0015 # 0.15% Per Trade

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
        raw_data = yf.download(tickers, period="3y", interval="1d", auto_adjust=True, progress=False)
        processed = {}
        for t in tickers:
            if isinstance(raw_data.columns, pd.MultiIndex):
                try: df = raw_data.xs(t, axis=1, level=1).copy()
                except: continue
            else: df = raw_data.copy()
            if df.empty or len(df) < 30: continue
            
            # Indicators
            df['SMA200'] = df['Close'].rolling(200).mean()
            df['SMA50'] = df['Close'].rolling(50).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14).mean()
            
            # Trailing Stop Logic
            df['Base_SL'] = df['Close'] - (df['ATR'] * 2.5)
            sl_values = df['Base_SL'].values
            close_values = df['Close'].values
            trailing_sl = np.zeros_like(sl_values)
            trailing_sl[0] = sl_values[0]
            for i in range(1, len(sl_values)):
                if close_values[i-1] > trailing_sl[i-1]:
                    trailing_sl[i] = max(trailing_sl[i-1], sl_values[i])
                else:
                    trailing_sl[i] = sl_values[i]
            df['Trailing_SL'] = trailing_sl
            df['Vol_Avg20'] = df['Volume'].rolling(20).mean()
            df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20'].replace(0, np.nan)
            processed[t] = df.ffill().dropna()
        return processed
    except Exception as e:
        st.error(f"Fetch Error: {e}")
        return {}

# --- 4. SIDEBAR ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.title("🛡️ Ultimate Quant v3.0")
    st.info(f"💵 1 USD = **{LIVE_USDTHB:.2f} THB**")
    capital = st.number_input("Total Capital (THB):", value=1000000, step=10000)
    risk_pct = st.slider("Risk per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    watchlist_input = st.text_area("Tickers (Comma Separated):", "NVDA, AAPL, PTT, DELTA, BTC-USD, GOLD")
    raw_tickers = [t.strip() for t in watchlist_input.split(",") if t.strip()]
    final_watchlist = list(dict.fromkeys([format_ticker(t) for t in raw_tickers if format_ticker(t)]))

# --- 5. DATA PROCESSING ---
data_dict = fetch_all_data(final_watchlist)
results = []
for ticker in final_watchlist:
    if ticker not in data_dict: continue
    df = data_dict[ticker]
    curr, prev = df.iloc[-1], df.iloc[-2]
    p = curr['Close']
    is_above_sma = p > curr['SMA200']
    is_above_mid = p > curr['SMA50']
    
    if is_above_sma and is_above_mid and prev['RSI'] < 45 and curr['Vol_Ratio'] > 1.2: sig = "🟢 ACCUMULATE"
    elif curr['RSI'] > 80: sig = "💰 DISTRIBUTION"
    elif not is_above_sma: sig = "🔴 BEARISH"
    else: sig = "⚪ NEUTRAL"

    risk_cash_thb = capital * (risk_pct / 100)
    sl_gap = max(p - curr['Trailing_SL'], 0.01)
    is_usd = not ticker.endswith(".BK")
    raw_qty = (risk_cash_thb / (LIVE_USDTHB if is_usd else 1)) / sl_gap
    qty = int(raw_qty) if is_usd else int(raw_qty // 100) * 100

    results.append({"Asset": ticker, "Price": round(p, 2), "Regime": sig, "RSI": round(curr['RSI'], 1), 
                    "Target Qty": qty, "Trailing SL": round(curr['Trailing_SL'], 2), "Currency": "USD" if is_usd else "THB"})
res_df = pd.DataFrame(results)

# --- 6. MAIN TERMINAL ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics", "📖 Guide", "🧠 System Logic"])

with tabs[0]:
    st.subheader("📊 Market Opportunities")
    if not res_df.empty: st.dataframe(res_df, use_container_width=True, hide_index=True)
    else: st.warning("ระบุ Ticker ใน Sidebar เพื่อเริ่มวิเคราะห์")

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
        p_entry = c2.number_input("Entry Price", value=0.0)
        p_qty = c3.number_input("Quantity", value=0)
        if st.button("Add to Portfolio") and p_asset != "None":
            st.session_state.my_portfolio[p_asset] = {"entry": p_entry, "qty": p_qty}
            save_portfolio(st.session_state.my_portfolio); st.rerun()

    if st.session_state.my_portfolio:
        p_list = []
        for asset, info in st.session_state.my_portfolio.items():
            if asset in data_dict:
                cp = data_dict[asset]['Close'].iloc[-1]
                sl = data_dict[asset]['Trailing_SL'].iloc[-1]
                curr_l = "USD" if not asset.endswith(".BK") else "THB"
                pnl = (cp - info['entry']) * info['qty']
                p_list.append({"Asset": asset, "Cost": info['entry'], "Price": cp, "Qty": info['qty'], "P/L": f"{pnl:,.2f} {curr_l}", "Status": "✅ HOLD" if cp > sl else "🚨 EXIT"})
        st.dataframe(pd.DataFrame(p_list), use_container_width=True, hide_index=True)
        if st.button("🗑️ Reset Portfolio"): save_portfolio({}); st.session_state.my_portfolio = {}; st.rerun()

with tabs[3]:
    st.header("🧪 Strategy Backtest (Net of Commissions)")
    sel_bt = st.selectbox("เลือกสินทรัพย์:", list(data_dict.keys()) if data_dict else ["None"], key="bt_sel")
    if sel_bt != "None" and sel_bt in data_dict:
        df_bt = data_dict[sel_bt].iloc[-500:].copy() 
        fx_mult = LIVE_USDTHB if not sel_bt.endswith(".BK") else 1
        balance = capital; pos = 0; trades = []; entry_p = 0
        
        for i in range(1, len(df_bt)):
            c_bt, p_bt = df_bt.iloc[i], df_bt.iloc[i-1]
            price = c_bt['Close']
            if pos == 0 and price > c_bt['SMA200'] and p_bt['RSI'] < 45 and c_bt['Vol_Ratio'] > 1.2:
                risk_amt = balance * (risk_pct / 100)
                sl_d = max(price - c_bt['Trailing_SL'], 0.01)
                pos = int((risk_amt / fx_mult) / sl_d)
                entry_p = price
                balance -= (entry_p * pos * COMMISSION_RATE * fx_mult) # Entry Fee
                trades.append({"Type": "BUY", "Date": df_bt.index[i], "Price": entry_p})
            elif pos > 0 and (price < c_bt['Trailing_SL'] or c_bt['RSI'] > 80):
                exit_fee = (price * pos * COMMISSION_RATE * fx_mult)
                pnl = ((price - entry_p) * pos * fx_mult) - exit_fee
                balance += pnl
                trades.append({"Type": "SELL", "Date": df_bt.index[i], "Price": price, "PnL": pnl})
                pos = 0

        if trades:
            td_df = pd.DataFrame([t for t in trades if "PnL" in t])
            if not td_df.empty:
                td_df['Equity'] = td_df['PnL'].cumsum() + capital
                win_rate = (len(td_df[td_df['PnL'] > 0]) / len(td_df)) * 100
                st.metric("Final Balance (Net)", f"{balance:,.2f} THB")
                st.metric("Win Rate", f"{win_rate:.1f}%")
                fig_bt = go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], mode='lines', line=dict(color='#00ff00')))
                st.plotly_chart(fig_bt, use_container_width=True)

with tabs[4]:
    st.header("🛡️ Tap 6: Advanced Analytics & Monte Carlo")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🎲 Monte Carlo Simulation (1,000 Runs)")
        if 'td_df' in locals() and not td_df.empty:
            returns = td_df['PnL'].values
            sims = []
            for _ in range(1000):
                sim_path = np.random.choice(returns, size=len(returns), replace=True).cumsum() + capital
                sims.append(sim_path)
            
            fig_mc = go.Figure()
            for s in sims[:50]: # Plot 50 paths
                fig_mc.add_trace(go.Scatter(y=s, mode='lines', line=dict(width=0.5), opacity=0.3, showlegend=False))
            fig_mc.update_layout(title="Equity Path Probabilities", template="plotly_dark")
            st.plotly_chart(fig_mc, use_container_width=True)
        else: st.info("Run Backtest first to see simulation")

    with col2:
        st.subheader("📊 Risk Metrics")
        if 'td_df' in locals() and not td_df.empty:
            profit_factor = td_df[td_df['PnL']>0]['PnL'].sum() / abs(td_df[td_df['PnL']<0]['PnL'].sum())
            st.metric("Profit Factor", f"{profit_factor:.2f}")
            max_dd = ((td_df['Equity'] - td_df['Equity'].cummax()) / td_df['Equity'].cummax()).min() * 100
            st.metric("Max Drawdown", f"{max_dd:.2f}%", delta_color="inverse")
            expectancy = td_df['PnL'].mean()
            st.metric("Expectancy per Trade", f"{expectancy:,.2f} THB")

with tabs[5]:
    st.header("📖 Tap 7: Ultimate Quant Methodology")
    st.markdown("""
    ### 🛡️ ปรัชญาการเทรด (The Quant Creed)
    1. **วัดผลได้ (Measurable):** เราไม่ใช้ความรู้สึก ทุกจุดเข้าซื้อต้องมีตัวเลขรองรับ
    2. **คุมความเสี่ยง (Risk First):** กำไรเป็นเรื่องของตลาด แต่ขาดทุนเป็นเรื่องของเรา (Position Sizing คือหัวใจ)
    3. **ความสม่ำเสมอ (Consistency):** ระบบจะทำงานได้ดีที่สุดเมื่อเราทำตามวินัย 100%
    
    ### 🛠️ วิธีการใช้ Terminal นี้
    * **Step 1:** ใส่ชื่อหุ้นที่สนใจใน Sidebar (รองรับทั้งหุ้นไทย .BK และหุ้นนอก)
    * **Step 2:** ตรวจสอบ **Scanner** หาหุ้นที่ขึ้น `🟢 ACCUMULATE`
    * **Step 3:** ใช้ **Target Qty** ในการส่งคำสั่งซื้อ (ระบบคำนวณ 1% Risk ให้แล้ว)
    * **Step 4:** ติดตามหน้า **Portfolio** หากขึ้นไฟแดง `🚨 EXIT` ให้ขายทันทีโดยไม่มีข้อแม้
    """)

with tabs[6]:
    st.header("🧠 System Logic & Mathematics")
    st.latex(r"Position\,Size = \frac{Equity \times Risk\%}{Price - Trailing\,SL}")
    st.markdown("""
    * **Trailing Stop (ATR 2.5):** ใช้ค่าความผันผวนจริงเป็นตัวตั้งกำแพง ไม่แคบจนโดนสะบัดหลุด และไม่กว้างจนคืนกำไรหมด
    * **Wilder's Smoothing:** RSI ในระบบนี้ใช้การเกลาค่าแบบ Wilder เพื่อลดสัญญาณหลอกในช่วงตลาดผันผวน
    * **Monte Carlo Engine:** ใช้วิธี *Bootstrap Resampling* เพื่อสุ่มลำดับผลลัพธ์การเทรด ช่วยให้เห็นโอกาสรอดในระยะยาว
    """)

st.divider()
st.caption("Ultimate Quant Terminal v3.0 | Built for Professional Statistical Trading | 2026 Edition")
