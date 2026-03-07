import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
import shutil

# --- 1. PRO UI CONFIG (ดึง CSS เดิมกลับมาและเสริม Layout Analytics) ---
st.set_page_config(page_title="The Masterpiece", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    
    /* สไตล์สำหรับ Card ในหน้า Analytics */
    .custom-card {
        background-color: #161b22;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #30363d;
        text-align: center;
        margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .card-label { color: #8b949e; font-size: 14px; margin-bottom: 5px; }
    .card-value { color: #ffffff; font-size: 26px; font-weight: bold; }
    .card-value-green { color: #00ff00; font-size: 26px; font-weight: bold; }
    .card-value-red { color: #ff4b4b; font-size: 26px; font-weight: bold; }

    .stMetric { 
        background-color: #161b22; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #30363d; 
        border-left: 5px solid #00ff00;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #161b22; border-radius: 6px 6px 0px 0px; 
        padding: 12px 25px; color: #8b949e;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #238636 !important; color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE & LIVE FX (ดึงกลับมาครบถ้วน) ---
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

# --- 3. CORE QUANT ENGINE (Logic เดิมเป๊ะ) ---
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
    st.title("🏆 The Masterpiece")
    st.markdown("`Institutional Systematic OS`")
    st.divider()
    st.info(f"💵 FX Rate: **{LIVE_USDTHB:.2f} THB**")
    capital = st.number_input("Total Equity (THB):", value=1000000, step=50000)
    risk_pct = st.slider("Risk Per Trade (%)", 0.1, 5.0, 1.0)
    st.divider()
    watchlist_input = st.text_area("Watchlist (CSV):", "NVDA, AAPL, PTT, DELTA, BTC-USD")
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
    results.append({"Asset": t, "Price": round(p, 2), "Regime": sig, "RSI": round(curr['RSI'], 1), "Target Qty": qty, "Currency": "THB" if is_thai else "USD"})

# --- 6. MAIN DISPLAY ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🛡️ Analytics", "📖 Logic Guide"])

with tabs[0]:
    st.subheader("📊 Tactical Opportunities")
    if results: st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
    else: st.warning("Please enter valid tickers in the sidebar.")

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
        fig.update_layout(height=700, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0,r=0,b=0,t=20))
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
                p_list.append({
                    "Asset": a, "Cost": i['entry'], "Price": curr_p, "Qty": i['qty'], 
                    "P/L (THB)": f"{pl_thb:,.2f}", 
                    "Status": "✅ HOLD" if curr_p > data_dict[a]['Trailing_SL'].iloc[-1] else "🚨 EXIT"
                })
        st.dataframe(pd.DataFrame(p_list), use_container_width=True, hide_index=True)
        if st.button("🗑️ Wipe Data"): save_portfolio({}); st.session_state.my_portfolio = {}; st.rerun()

with tabs[3]: # Backtest Logic
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
                pos = int(((balance * (risk_pct/100)) / fx_bt) / max(c['Close'] - c['Trailing_SL'], 0.01))
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

with tabs[4]: # --- ANALYTICS HUB (ปรับ Layout ใหม่ตามรูปภาพที่คุณส่งมา) ---
    st.header("🛡️ Analytics Hub")
    if 'td_df' in locals() and not td_df.empty:
        st.divider()
        # แบ่ง Layout 3 ส่วนตามรูป: กราฟซ้าย - ตัวเลขกลาง - กราฟขวา
        col_left, col_mid, col_right = st.columns([4, 2, 4], gap="medium")
        
        with col_left:
            st.subheader("🎲 Monte Carlo Simulation")
            sims = [np.random.choice(td_df['PnL'].values, size=len(td_df), replace=True).cumsum() + capital for _ in range(50)]
            fig_mc = go.Figure()
            for s in sims: 
                fig_mc.add_trace(go.Scatter(y=s, mode='lines', line=dict(width=1, color='cyan'), opacity=0.15, showlegend=False))
            fig_mc.update_layout(height=450, margin=dict(l=0,r=0,b=0,t=20), template="plotly_dark")
            st.plotly_chart(fig_mc, use_container_width=True)
        
        with col_mid:
            st.subheader("📊 Performance")
            win_r = (len(td_df[td_df['PnL'] > 0]) / len(td_df)) * 100
            pf = td_df[td_df['PnL']>0]['PnL'].sum() / abs(td_df[td_df['PnL']<0]['PnL'].sum()) if any(td_df['PnL'] < 0) else 0
            mdd = ((td_df['Equity'] - td_df['Equity'].cummax()) / td_df['Equity'].cummax()).min()*100
            
            # ใช้ Custom Card HTML สำหรับแสดงผลตัวเลขแบบในรูป
            st.markdown(f"""
                <div class="custom-card"><div class="card-label">Win Rate</div><div class="card-value-green">{win_r:.1f}%</div></div>
                <div class="custom-card"><div class="card-label">Profit Factor</div><div class="card-value">{pf:.2f}</div></div>
                <div class="custom-card"><div class="card-label">Avg Trade P/L</div><div class="card-value">{td_df['PnL'].mean():,.0f} ฿</div></div>
                <div class="custom-card"><div class="card-label">Max Drawdown</div><div class="card-value-red">{mdd:.2f}%</div></div>
            """, unsafe_allow_html=True)
            
        with col_right:
            st.subheader("📈 Equity Curve")
            fig_eq = go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], name='Net Equity', line=dict(color='#00ff00', width=2), fill='tozeroy'))
            fig_eq.update_layout(height=450, margin=dict(l=0,r=0,b=0,t=20), template="plotly_dark")
            st.plotly_chart(fig_eq, use_container_width=True)
            
        st.success("✅ System Alpha Verified")
    else:
        st.info("Please run a Backtest first to see the Analytics.")

with tabs[5]:
    st.header("📖 The Masterpiece Decision Logic")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.markdown("""
        ### 🛡️ Core Entry Framework
        1. **Trend Guard:** ราคาสินทรัพย์ต้องอยู่เหนือ `SMA 200` และ `SMA 50` เพื่อยืนยันว่าเป็นสภาวะขาขึ้นที่แข็งแกร่ง
        2. **Momentum Pullback:** ใช้ `RSI (14)` หาจังหวะที่ราคาย่อตัวลงมาในโซนได้เปรียบ (RSI < 48 และเริ่มฟื้นตัว)
        3. **Liquidity Filter:** `Volume Ratio > 1.1` เพื่อยืนยันว่าการขยับของราคามีปริมาณการซื้อขายสนับสนุนจริง
        """)
    with col_l2:
        st.markdown("""
        ### 🚪 Professional Exit Strategy
        1. **Dynamic Trailing Stop:** ปกป้องกำไรด้วย `ATR * 2.5` ซึ่งเป็นจุด Stop Loss ที่ขยับขึ้นตามความผันผวนจริง
        2. **Overbought Exit:** เมื่อราคาพุ่งทะยานจน `RSI > 82` ระบบจะแนะนำให้ Take Profit เนื่องจากราคามีความตึงตัวสูง
        """)
    st.divider()
    st.latex(r"Position\,Size = \frac{Equity \times Risk\%}{Price - Trailing\,Stop}")

st.divider(); st.caption("🏆 The Masterpiece | Institutional Systematic OS")
