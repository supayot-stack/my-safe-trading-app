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
    .risk-box { background-color: #1e222d; padding: 20px; border-radius: 12px; border: 1px solid #30363d; border-left: 5px solid #00ffcc; }
    .vol-ok { color: #00ffbb; font-weight: bold; }
    .vol-low { color: #888; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE ENGINE ---
@st.cache_data(ttl=3600)
def get_data(ticker, interval="1d", data_period="2y"):
    try:
        # Auto-suffix for Thai Stocks
        thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
        if ticker in thai_list and "." not in ticker: ticker += ".BK"
        
        df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Indicators
        df['SMA200'] = df['Close'].rolling(200).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14).mean()
        df['RSI'] = 100 - (100 / (1 + (avg_gain / (avg_loss + 1e-9))))
        
        # ATR & Risk Management
        high_low = df['High'] - df['Low']
        high_cp = abs(df['High'] - df['Close'].shift())
        low_cp = abs(df['Low'] - df['Close'].shift())
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['SL'] = df['Close'] - (df['ATR'] * 2) 
        df['TP'] = df['Close'] + ((df['Close'] - df['SL']) * 2)
        
        # --- VOLUME LOGIC ---
        df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
        
        return df.dropna(subset=['SMA200', 'ATR'])
    except: return None

# --- 3. DASHBOARD ---
tab1, tab2 = st.tabs(["🚀 Quant Scanner", "📊 Volume Analysis"])

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max + Volume Check")
    
    # Sidebar
    st.sidebar.header("💰 Portfolio")
    portfolio_size = st.sidebar.number_input("เงินทุน (THB):", value=100000)
    risk_per_trade = st.sidebar.slider("Risk (%):", 0.5, 5.0, 1.0)
    
    assets = st.sidebar.multiselect("Watchlist:", ["NVDA", "AAPL", "BTC-USD", "SET50.BK"], default=["NVDA", "BTC-USD"])
    
    results = []
    if assets:
        for t in assets:
            df = get_data(t)
            if df is not None:
                l = df.iloc[-1]
                p, r, s, v, va = l['Close'], l['RSI'], l['SMA200'], l['Volume'], l['Vol_Avg5']
                
                # Logic: ราคาต้องเหนือเส้น 200 + RSI ต่ำ + วอลุ่มต้องเข้า (Vol > Vol_Avg5)
                vol_status = "✅ High Vol" if v > va else "❌ Low Vol"
                
                if p > s and r < 45 and v > va: act = "🟢 STRONG BUY"
                elif p > s and r < 45: act = "⚪ Wait for Vol" # กรองกรณีราคาได้แต่ไม่มีวอลุ่ม
                elif r > 70: act = "💰 PROFIT"
                elif p < s: act = "🔴 EXIT"
                else: act = "⚪ Wait"
                
                # Position Sizing
                risk_amt = portfolio_size * (risk_per_trade / 100)
                sl_dist = p - l['SL']
                qty = int(risk_amt / sl_dist) if sl_dist > 0 else 0
                qty = min(qty, int(portfolio_size/p))

                results.append({
                    "Ticker": t, "Price": round(p,2), "Signal": act, 
                    "Vol Status": vol_status, "RSI": round(r,1), "Qty": qty,
                    "SL": round(l['SL'],2), "TP": round(l['TP'],2)
                })

        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

    st.divider()

    # --- 4. ADVANCED GRAPH (3 Subplots: Price, RSI, Volume) ---
    if results:
        sel = st.selectbox("🔍 เลือกวิเคราะห์:", [r['Ticker'] for r in results])
        df_p = get_data(sel)
        if df_p is not None:
            # เพิ่มแถวสำหรับ Volume โดยเฉพาะ
            fig = make_subplots(
                rows=3, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.03, 
                row_heights=[0.5, 0.2, 0.3] # แบ่งสัดส่วนกราฟ
            )
            
            # Row 1: Candlestick + SMA + ATR
            fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], low=df_p['Low'], close=df_p['Close'], name='Price'), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA 200', line=dict(color='#ffcc00')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SL'], name='ATR Stop', line=dict(color='#ff4b4b', dash='dot')), row=1, col=1)
            
            # Row 2: RSI
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='#00ccff')), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="#ff3366", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#00ffbb", row=2, col=1)
            
            # Row 3: Volume (สีจะเปลี่ยนตามแท่งเทียน)
            colors = ['#00ffbb' if close >= open else '#ff4b4b' for open, close in zip(df_p['Open'], df_p['Close'])]
            fig.add_trace(go.Bar(x=df_p.index, y=df_p['Volume'], name='Volume', marker_color=colors), row=3, col=1)
            fig.add_trace(go.Scatter(x=df_p.index, y=df_p['Vol_Avg5'], name='Vol Avg 5', line=dict(color='white', width=1)), row=3, col=1)

            fig.update_layout(height=800, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

if st.button("🔄 Sync Market Data"): st.rerun()
