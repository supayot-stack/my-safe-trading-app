import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. SETTINGS & STYLE ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { 
        background-color: #1e222d; 
        padding: 20px; 
        border-radius: 12px; 
        border-left: 5px solid #00ffcc; 
        border: 1px solid #30363d;
    }
    .status-buy { color: #00ffbb; font-weight: bold; }
    .status-wait { color: #ffcc00; font-weight: bold; }
    .status-exit { color: #ff4b4b; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE ENGINE (ATR + RSI + SMA) ---
@st.cache_data(ttl=3600)
def get_data(ticker, interval="1d", data_period="2y"):
    try:
        # Auto-suffix for Thai Stocks
        thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
        if ticker in thai_list and "." not in ticker: ticker += ".BK"
        
        df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Technicals
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        # RSI (Wilder's)
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
        df['RSI'] = 100 - (100 / (1 + (avg_gain / (avg_loss + 1e-9))))
        
        # ATR (Volatility Engine)
        high_low = df['High'] - df['Low']
        high_cp = abs(df['High'] - df['Close'].shift())
        low_cp = abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        
        # Risk Management Levels
        df['SL'] = df['Close'] - (df['ATR'] * 2) 
        df['TP'] = df['Close'] + ((df['Close'] - df['SL']) * 2)
        df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
        
        return df.dropna(subset=['SMA200', 'ATR']) # เสริม: ตัดค่าว่างออกเพื่อความแม่นยำ
    except: return None

# --- 3. UI & LOGIC ---
tab1, tab2 = st.tabs(["📊 Quant Scanner", "📖 Risk Management Guide"])

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max")
    
    # Sidebar
    st.sidebar.header("💰 Portfolio & Risk")
    portfolio_size = st.sidebar.number_input("เงินทุน (THB):", min_value=1000, value=100000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อไม้ (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.divider()
    assets = st.sidebar.multiselect("Watchlist:", ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK", "GC=F"], default=["NVDA", "BTC-USD"])
    custom = st.sidebar.text_input("➕ เพิ่ม Ticker:").upper().strip()
    if custom and custom not in assets: assets.append(custom)

    results = []
    if assets:
        with st.spinner('Calculating Market Data...'):
            for t in assets:
                df = get_data(t)
                if df is not None:
                    l = df.iloc[-1]
                    p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                    
                    # Logic Core
                    if p > s and r < 45 and v > va: act = "🟢 STRONG BUY"
                    elif r > 70: act = "💰 PROFIT"
                    elif p < s: act = "🔴 EXIT/AVOID"
                    else: act = "⚪ Wait"
                    
                    # --- เสริม: Position Sizing Safety Buffer ---
                    risk_amt = portfolio_size * (risk_per_trade / 100)
                    sl_dist = p - l['SL']
                    qty = int(risk_amt / sl_dist) if sl_dist > 0 else 0
                    max_qty = int(portfolio_size / p) # ไม่ให้ซื้อเกินเงินสดที่มี
                    final_qty = min(qty, max_qty)
                    
                    results.append({
                        "Ticker": t, "Price": round(p,2), "RSI": round(r,1),
                        "Signal": act, "Qty": final_qty, "ATR": round(l['ATR'], 2),
                        "SL": round(l['SL'],2), "TP": round(l['TP'],2)
                    })

        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

    st.divider()

    # --- Analytics Section ---
    col1, col2 = st.columns([0.65, 0.35])
    if results:
        with col1:
            sel = st.selectbox("🔍 เลือกวิเคราะห์:", [r['Ticker'] for r in results])
            df_p = get_data(sel)
            if df_p is not None:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='#ffcc00')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SL'], name='ATR Stop', line=dict(color='#ff4b4b', dash='dot')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='#00ccff')), row=2, col=1)
                fig.update_layout(height=550, template="plotly_dark", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            target = next(item for item in results if item["Ticker"] == sel)
            # เสริม: คำนวณความคุ้มค่า (Expected Value)
            st.markdown(f"""
                <div class="risk-box">
                    <h3>🎯 Trading Plan: {sel}</h3>
                    <hr style="border: 0.1px solid #333;">
                    <p><b>จำนวนหุ้น:</b> {target['Qty']:,} หุ้น</p>
                    <p><b>เงินลงทุนรวม:</b> {(target['Price'] * target['Qty']):,.2f} บาท</p>
                    <p><b>Risk per Trade:</b> {(portfolio_size * risk_per_trade / 100):,.2f} บาท</p>
                    <br>
                    <h4 style="color:#ff4b4b">Stop Loss: {target['SL']}</h4>
                    <h4 style="color:#00ffbb">Take Profit: {target['TP']}</h4>
                    <p style="font-size:0.8em; color:#888;">*คำนวณจากระยะ Reward/Risk = 1:2</p>
                </div>
                """, unsafe_allow_html=True)

if st.button("🔄 Sync Market Data"): st.rerun()
