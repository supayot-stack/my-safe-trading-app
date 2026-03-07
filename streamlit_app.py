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
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชัน Backtest (Elite Engine) ---
def run_backtest_engine(df, initial_cap):
    if df is None or len(df) < 100: return 0, 0, 0, [initial_cap]
    
    # Strategy: Buy when Price > SMA200 & RSI < 45
    df['Sig'] = (df['Close'] > df['SMA200']) & (df['RSI'] < 45)
    capital, equity_curve, trades, in_pos = initial_cap, [initial_cap], [], False
    entry, sl, tp = 0, 0, 0
    
    for i in range(1, len(df)):
        if not in_pos and df['Sig'].iloc[i]:
            entry, sl, tp, in_pos = df['Close'].iloc[i], df['SL'].iloc[i], df['TP'].iloc[i], True
        elif in_pos:
            curr = df['Close'].iloc[i]
            if curr <= sl or curr >= tp:
                ret = (curr / entry) - 1
                capital *= (1 + ret)
                trades.append(ret)
                in_pos = False
        equity_curve.append(capital)
    
    wr = (len([r for r in trades if r > 0]) / len(trades) * 100) if trades else 0
    pos_sum = sum([r for r in trades if
