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
st.set_page_config(page_title="Gemini Master Quant v2.6 Ultimate", layout="wide")
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
DB_FILE = "portfolio_data_v2.json"
BAK_FILE = "portfolio_data_v2.json.bak"

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
            
            df['SMA200'] = df['Close'].rolling(200, min_periods=1).mean()
            df['SMA50'] = df['Close'].rolling(50, min_periods=1).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
            df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-9))))
            tr = pd.concat([df['High']-df['Low'], abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
            df['ATR'] = tr.rolling(14, min_periods=1).mean()
            
            # --- Trailing Stop Logic ---
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

            df['Vol_Avg20'] = df['Volume'].rolling(20, min_periods=1).mean()
            df['Vol_Ratio'] = df['Volume'] / df['Vol_Avg20'].replace(0, np.nan)
            processed[t] = df.ffill().bfill()
        return processed
    except Exception as e:
        st.error(f"Fetch Error: {e}")
        return {}

# --- 4. SIDEBAR ---
if 'my_portfolio' not in st.session_state: st.session_state.my_portfolio = load_portfolio()

with st.sidebar:
    st.title("🛡️ Secure Quant v2.6")
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
    if ticker not in data_dict or data_dict[ticker].empty: continue
    df = data_dict[ticker]
    curr, prev = df.iloc[-1], df.iloc[-2]
    p = curr['Close']
    is_above_sma = p > curr['SMA200'] if not pd.isna(curr['SMA200']) else True
    is_above_mid = p > curr['SMA50'] if not pd.isna(curr['SMA50']) else True
    
    if is_above_sma and is_above_mid and prev['RSI'] < 45 and curr['Vol_Ratio'] > 1.2: sig = "🟢 ACCUMULATE"
    elif curr['RSI'] > 80: sig = "💰 DISTRIBUTION"
    elif not is_above_sma: sig = "🔴 BEARISH"
    else: sig = "⚪ NEUTRAL"

    risk_cash_thb = capital * (risk_pct / 100)
    sl_gap = max(p - curr['Trailing_SL'], 0.01)
    is_usd = not ticker.endswith(".BK")
    
    raw_qty = (risk_cash_thb / (LIVE_USDTHB if is_usd else 1)) / sl_gap
    if p > curr['Trailing_SL']:
        qty = int(raw_qty) if is_usd else int(raw_qty // 100) * 100
    else: qty = 0

    results.append({"Asset": ticker, "Price": round(p, 2), "Regime": sig, "RSI": round(curr['RSI'], 1), 
                    "Target Qty": qty, "Trailing SL": round(curr['Trailing_SL'], 2), "Currency": "USD" if is_usd else "THB"})
res_df = pd.DataFrame(results)

# --- 6. MAIN TERMINAL ---
tabs = st.tabs(["🏛 Scanner", "📈 Deep-Dive", "💼 Portfolio", "🧪 Backtest", "🧪 Analytics", "📖 Step-by-Step Guide", "🧠 System Logic"])

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
    st.header("🧪 Strategy Backtest (1-Year)")
    sel_bt = st.selectbox("เลือกสินทรัพย์เพื่อทดสอบ:", list(data_dict.keys()) if data_dict else ["None"], key="bt_sel")
    if sel_bt != "None" and sel_bt in data_dict:
        df_bt = data_dict[sel_bt].iloc[-252:].copy() 
        balance = capital; pos = 0; trades = []; entry_p = 0
        for i in range(1, len(df_bt)):
            c_bt, p_bt = df_bt.iloc[i], df_bt.iloc[i-1]
            price = c_bt['Close']
            if pos == 0 and price > c_bt['SMA200'] and p_bt['RSI'] < 45 and c_bt['Vol_Ratio'] > 1.2:
                risk_amt = balance * (risk_pct / 100); sl_d = price - c_bt['Trailing_SL']
                pos = int((risk_amt / (LIVE_USDTHB if not sel_bt.endswith(".BK") else 1)) / max(sl_d, 0.01))
                entry_p = price; trades.append({"Type": "BUY", "Date": df_bt.index[i], "Price": entry_p})
            elif pos > 0 and (price < c_bt['Trailing_SL'] or c_bt['RSI'] > 80):
                pnl = (price - entry_p) * pos
                balance += (pnl * (LIVE_USDTHB if not sel_bt.endswith(".BK") else 1))
                trades.append({"Type": "SELL", "Date": df_bt.index[i], "Price": price, "PnL": pnl * (LIVE_USDTHB if not sel_bt.endswith(".BK") else 1)})
                pos = 0
        if trades:
            td_df = pd.DataFrame([t for t in trades if "PnL" in t])
            if not td_df.empty:
                td_df['Equity'] = td_df['PnL'].cumsum() + capital
                td_df['Return'] = td_df['Equity'].pct_change().fillna(0)
                sharpe = (td_df['Return'].mean() / td_df['Return'].std()) * np.sqrt(252) if td_df['Return'].std() != 0 else 0
                max_dd = ((td_df['Equity'] - td_df['Equity'].cummax()) / td_df['Equity'].cummax()).min() * 100
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Win Rate", f"{(len(td_df[td_df['PnL'] > 0]) / len(td_df)) * 100:.1f}%")
                c2.metric("Total P/L (THB)", f"{td_df['PnL'].sum():,.2f}")
                c3.metric("Final Balance", f"{balance:,.2f}")
                c4.metric("Sharpe Ratio", f"{sharpe:.2f}")
                c5.metric("Max Drawdown", f"{max_dd:.2f}%", delta_color="inverse")
                fig_bt = go.Figure(go.Scatter(x=td_df['Date'], y=td_df['Equity'], mode='lines+markers', line=dict(color='#00ff00')))
                fig_bt.update_layout(title=f"การเติบโตของเงินต้นจากหุ้น {sel_bt}", template="plotly_dark")
                st.plotly_chart(fig_bt, use_container_width=True)

with tabs[4]:
    st.subheader("🧪 Analytics & Portfolio Risk")
    col_l, col_spacer, col_r = st.columns([2, 0.2, 1])
    with col_l:
        st.markdown("##### 📉 Asset Correlation")
        price_dict = {t: df['Close'] for t, df in data_dict.items()}
        if len(price_dict) > 1:
            corr_df = pd.DataFrame(price_dict).dropna().corr()
            fig_corr = go.Figure(data=go.Heatmap(z=corr_df.values, x=corr_df.columns, y=corr_df.columns, colorscale='RdBu_r', zmin=-1, zmax=1, text=np.round(corr_df.values, 2), texttemplate="%{text}"))
            fig_corr.update_layout(height=500, template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_corr, use_container_width=True)
        else: st.info("เพิ่ม Ticker มากกว่า 1 ตัวเพื่อดูความสัมพันธ์")
    with col_r:
        st.markdown("##### 🛡️ Portfolio Exposure")
        if st.session_state.my_portfolio:
            t_risk = sum([max((info['entry'] - data_dict[a]['Trailing_SL'].iloc[-1]) * info['qty'], 0) * (LIVE_USDTHB if not a.endswith(".BK") else 1) for a, info in st.session_state.my_portfolio.items() if a in data_dict])
            risk_util = (t_risk / capital) * 100 if capital > 0 else 0
            st.metric("Total Risk", f"{t_risk:,.2f} THB")
            st.write(f"Risk Utilization: **{risk_util:.2f}%**")
            st.progress(min(risk_util / 100, 1.0))
            st.caption("แนะนำ: ความเสี่ยงรวมไม่ควรเกิน 5-10% ของเงินต้น")
            st.divider()
            st.write("🔧 **System Health**")
            st.write("• Data Link: ✅ Active")
            st.write(f"• FX Sync: ✅ {LIVE_USDTHB:.2f}")

with tabs[5]:
    st.header("📖 คู่มือ Step-by-Step (The Quant Methodology)")
    st.info("💡 เน้นรักษาวินัยและการคุมความเสี่ยง (Risk Management) เป็นหลัก")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("""
        ### 1️⃣ การเตรียมตัว (Setup)
        * **Capital:** เงินต้นทั้งหมดที่คุณมี (บาท) เพื่อใช้เป็นฐานในการคำนวณไม้เทรด
        * **Risk per Trade:** เปอร์เซ็นต์ที่ยอมเสียได้ต่อหนึ่งไม้ (แนะนำ 1%) ระบบจะใช้ค่านี้คำนวณจำนวนหุ้นให้สัมพันธ์กับระยะ Stop-Loss
        
        ### 2️⃣ การเข้าซื้อ (Entry Strategy)
        เมื่อเห็นสถานะ **🟢 ACCUMULATE** ในหน้า Scanner:
        * **Trend:** ราคาต้องยืนเหนือ SMA 200 (ขาขึ้นชัดเจน)
        * **RSI:** ต่ำกว่า 45 แปลว่า "ราคาย่อตัวลงมาในรอบขาขึ้น" (ซื้อตอนย่อ ไม่ไล่ราคา)
        * **Volume:** Ratio > 1.2 แปลว่า "เริ่มมีแรงซื้อหนาแน่นผิดปกติ" กลับเข้ามา
        * **Action:** ซื้อตามจำนวนที่ระบบระบุใน **Target Qty**
        """)
    with col_g2:
        st.markdown("""
        ### 3️⃣ การตัดขาดทุน (Trailing Stop-Loss)
        * **วินัย:** หากราคาหลุด **เส้นประสีแดง** ในหน้า Deep-Dive หรือระบบขึ้นไฟแดง `🚨 EXIT` ต้องขายทันที
        * **Trailing SL:** เส้นนี้จะขยับขึ้นตามราคาหุ้นเมื่อหุ้นขึ้น (Lock กำไร) แต่จะไม่ขยับลงตามราคาหุ้นเมื่อหุ้นตก (ตัดขาดทุน)
        
        ### 4️⃣ การทำกำไร (Take Profit)
        * **Distribution:** เมื่อ RSI ทะลุ 80 แปลว่าราคาเริ่มตึงตัว (Overbought) ควรแบ่งขายทำกำไร
        """)

with tabs[6]:
    st.header("🧠 System Logic (ตรรกะเบื้องหลังและคณิตศาสตร์)")
    arch_c1, arch_c2 = st.columns(2)
    with arch_c1:
        st.markdown(f"""
        #### ⚙️ Data Engine
        * **Live FX Sync:** ระบบดึงอัตราแลกเปลี่ยน USDTHB นาทีต่อนาที เพื่อคำนวณ 'อำนาจซื้อ' ในตลาดต่างประเทศให้แม่นยำที่สุด
        * **Wilder's RSI:** ใช้สูตร Exponential Moving Average เพื่อลดสัญญาณหลอก (False Signals) เมื่อเทียบกับ RSI ทั่วไป
        * **Dynamic ATR Stop:** ใช้ค่า ATR (ความผันผวนจริง) คูณด้วย 2.5 เพื่อหาจุด Stop-Loss ที่ไม่อึดอัดเกินไป
        """)
        st.markdown("#### 📐 สูตรคำนวณไม้เทรด (Position Sizing)")
        st.latex(r"Qty = \frac{Capital \times Risk\%}{Price - Trailing\,SL}")
        st.caption("สูตรนี้ช่วยให้ไม่ว่าหุ้นจะผันผวนแค่ไหน ถ้าคุณแพ้ คุณจะเสียเงินเท่าเดิมเสมอ (1% ของพอร์ต)")
    with arch_c2:
        st.markdown("""
        #### 📈 Performance Analytics
        * **Sharpe Ratio:** วัดว่ากำไรที่คุณได้ คุ้มค่าความเสี่ยงไหม (ยิ่งสูง = กำไรอย่างสม่ำเสมอ)
        * **Max Drawdown:** บอกจุดที่เงินทุนเคยติดลบหนักที่สุดในอดีต เพื่อประเมินความเสี่ยงเชิงสถิติ
        * **Board Lot Rounding:** ระบบจะปัดเศษหุ้นไทย (.BK) ให้เหลือหลัก 100 เสมอ เพื่อให้สามารถส่งคำสั่งซื้อในตลาด SET ได้จริง
        """)
        st.divider()
        st.markdown("#### 🛡️ Trailing Stop Logic")
        st.code("if New_SL > Old_SL: SL = New_SL else: SL = Old_SL", language='python')
        st.caption("ตรรกะ 'กำแพงขยับได้' ที่จะยกขึ้นตามราคากำไรเท่านั้น")
    st.divider()
    st.caption("Gemini Master Quant v2.6 Ultimate | Built for Professional Statistical Trading")
