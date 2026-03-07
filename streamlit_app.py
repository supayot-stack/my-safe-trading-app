import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
    .metric-card { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #333; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันหลัก (Core Engine) ---
@st.cache_data(ttl=3600)
def get_data(ticker, interval="1d", data_period="2y"):
    try:
        thai_tickers = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "OR", "SCC", "SCB"]
        if ticker in thai_tickers and "." not in ticker: ticker += ".BK"
        
        df = yf.download(ticker, period=data_period, interval=interval, auto_adjust=True, progress=False)
        if df.empty or len(df) < 200: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Indicators
        df['SMA200'] = df['Close'].rolling(200).mean()
        delta = df['Close'].diff()
        avg_gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, min_periods=14).mean()
        avg_loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, min_periods=14).mean()
        df['RSI'] = 100 - (100 / (1 + (avg_gain / (avg_loss + 1e-9))))
        
        # ATR & Risk Management
        tr = pd.concat([(df['High']-df['Low']), abs(df['High']-df['Close'].shift()), abs(df['Low']-df['Close'].shift())], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()
        df['SL'] = df['Close'] - (df['ATR'] * 2)
        df['TP'] = df['Close'] + ((df['Close'] - df['SL']) * 2)
        df['Vol_Avg5'] = df['Volume'].rolling(5).mean()
        
        return df
    except: return None

# --- 3. ส่วน Backtesting Engine ---
def run_backtest(df, initial_capital):
    # กลยุทธ์: Price > SMA200 AND RSI < 45 (Mean Reversion ในขาขึ้น)
    df['Signal'] = (df['Close'] > df['SMA200']) & (df['RSI'] < 45)
    
    returns = []
    capital = initial_capital
    in_position = False
    entry_price = 0
    sl_price = 0
    tp_price = 0
    
    for i in range(len(df)):
        current_price = df['Close'].iloc[i]
        if not in_position and df['Signal'].iloc[i]:
            in_position = True
            entry_price = current_price
            sl_price = df['SL'].iloc[i]
            tp_price = df['TP'].iloc[i]
        elif in_position:
            if current_price <= sl_price or current_price >= tp_price:
                trade_return = (current_price / entry_price) - 1
                returns.append(trade_return)
                capital *= (1 + trade_return)
                in_position = False
    
    if not returns: return 0, 0, 0, [initial_capital]
    
    win_rate = (len([r for r in returns if r > 0]) / len(returns)) * 100
    profit_factor = abs(sum([r for r in returns if r > 0]) / (sum([r for r in returns if r < 0]) + 1e-9))
    
    equity_curve = [initial_capital]
    current_cap = initial_capital
    for r in returns:
        current_cap *= (1 + r)
        equity_curve.append(current_cap)
        
    # Max Drawdown
    peaks = np.maximum.accumulate(equity_curve)
    drawdowns = (equity_curve - peaks) / peaks
    max_dd = drawdowns.min() * 100
    
    return win_rate, profit_factor, max_dd, equity_curve

# --- 4. หน้าจอหลัก (UI) ---
tab1, tab2 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง (Pro)"])

with tab2:
    st.header("📖 กลยุทธ์ระดับ Elite")
    st.markdown("""
    ### 🛡️ 1. Backtesting (การทดสอบย้อนหลัง)
    ระบบจะคำนวณว่าหากคุณเทรดตามสัญญาณ **Price > SMA200 & RSI < 45** ในอดีต ผลลัพธ์จะเป็นอย่างไร
    * **Win Rate:** ควรมากกว่า 50%
    * **Profit Factor:** ถ้ามากกว่า 1.5 ถือว่ากลยุทธ์แข็งแกร่ง
    * **Max Drawdown:** บอกจุดที่เจ็บหนักที่สุด หากรับไม่ได้ควรลดความเสี่ยงรายตัวลง
    """)

with tab1:
    st.title("🛡️ Safe Heaven Quant Pro Max (Elite)")
    
    # Sidebar
    st.sidebar.header("💰 Portfolio Settings")
    portfolio_size = st.sidebar.number_input("เงินทุนทั้งหมด (บาท):", min_value=1000, value=100000, step=1000)
    risk_per_trade = st.sidebar.slider("ความเสี่ยงต่อการเทรด (%):", 0.5, 5.0, 1.0)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 Asset Management")
    default_assets = ["NVDA", "AAPL", "TSLA", "BTC-USD", "SET50.BK"]
    selected_assets = st.sidebar.multiselect("เลือกหุ้น:", options=list(set(default_assets + ["MSFT", "GOOGL", "PTT.BK", "CPALL.BK", "GC=F"])), default=default_assets)
    
    results = []
    all_data = {} # เก็บข้อมูลไว้ทำ Correlation
    
    if selected_assets:
        with st.spinner('กำลังประมวลผลระบบ Quant...'):
            for t in selected_assets:
                df = get_data(t)
                if df is not None:
                    all_data[t] = df['Close']
                    l = df.iloc[-1]
                    # Logic สัญญาณ
                    if l['Close'] > l['SMA200'] and l['RSI'] < 45 and l['Volume'] > l['Vol_Avg5']: act = "🟢 STRONG BUY"
                    elif l['RSI'] > 70: act = "💰 PROFIT"
                    elif l['Close'] < l['SMA200']: act = "🔴 EXIT/AVOID"
                    else: act = "⚪ Wait"
                    
                    # Position Sizing
                    sl_dist = l['Close'] - l['SL']
                    qty = int((portfolio_size * risk_per_trade / 100) / sl_dist) if sl_dist > 0 else 0
                    
                    results.append({
                        "Ticker": t, "Price": round(l['Close'],2), "RSI": round(l['RSI'],1),
                        "Signal": act, "Qty": qty, "SL": round(l['SL'],2), "TP": round(l['TP'],2)
                    })

        if results:
            st.subheader("🎯 สรุปสัญญาณล่าสุด")
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

        # --- ส่วนที่เพิ่ม 1: Correlation Matrix ---
        if len(all_data) > 1:
            st.divider()
            st.subheader("🗠 Portfolio Correlation Matrix")
            corr_df = pd.DataFrame(all_data).pct_change().corr()
            fig_corr = go.Figure(data=go.Heatmap(
                z=corr_matrix.values if 'corr_matrix' in locals() else corr_df.values,
                x=corr_df.columns, y=corr_df.index, colorscale='RdBu_r', zmin=-1, zmax=1
            ))
            fig_corr.update_layout(height=400, template="plotly_dark")
            st.plotly_chart(fig_corr, use_container_width=True)
            st.caption("💡 ค่าใกล้ 1.0 (สีแดง) แปลว่าหุ้นวิ่งไปในทิศทางเดียวกันมากเกินไป ควรเลี่ยงการเข้าซื้อพร้อมกัน")

        # --- ส่วนที่เพิ่ม 2: Backtesting Display ---
        st.divider()
        col_sel, col_metrics = st.columns([0.4, 0.6])
        
        with col_sel:
            selected_bt = st.selectbox("📈 ตรวจสอบผล Backtest รายตัว:", selected_assets)
            df_bt = get_data(selected_bt)
            wr, pf, mdd, eq = run_backtest(df_bt, portfolio_size)
            
        with col_metrics:
            m1, m2, m3 = st.columns(3)
            m1.metric("Win Rate", f"{wr:.1f}%")
            m2.metric("Profit Factor", f"{pf:.2f}")
            m3.metric("Max Drawdown", f"{mdd:.1f}%")
            
        # Equity Curve Graph
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(y=eq, mode='lines', name='Portfolio Value', line=dict(color='#00ffcc')))
        fig_eq.update_layout(title=f"Equity Curve: {selected_bt}", template="plotly_dark", height=300)
        st.plotly_chart(fig_eq, use_container_width=True)

    st.divider()
    # (ส่วนวิเคราะห์กราฟรายตัวและ AI Insight คงเดิมตามโครงสร้างเดิม)
    if results:
        selected_plot = st.selectbox("🔍 วิเคราะห์กราฟละเอียด:", [r['Ticker'] for r in results], key="plot_select")
        # ... (ส่วนวาดกราฟ candlestick เดิม) ...

if st.button("🔄 อัปเดตข้อมูล"): st.rerun()
