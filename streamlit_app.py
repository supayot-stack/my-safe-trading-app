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
    .ai-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันเสริมสำหรับ Backtest ---
def run_backtest_logic(df, initial_cap):
    if df is None or len(df) < 20: return 0, 0, 0, [initial_cap]
    
    # กลยุทธ์: ซื้อเมื่อราคา > SMA200 และ RSI < 45
    df['Sig'] = (df['Close'] > df['SMA200']) & (df['RSI'] < 45)
    capital = initial_cap
    equity_curve = [initial_cap]
    trades = []
    
    in_pos = False
    entry, sl, tp = 0, 0, 0
    
    for i in range(1, len(df)):
        if not in_pos and df['Sig'].iloc[i]:
            entry = df['Close'].iloc[i]
            sl = df['SL'].iloc[i]
            tp = df['TP'].iloc[i]
            in_pos = True
        elif in_pos:
            curr = df['Close'].iloc[i]
            if curr <= sl or curr >= tp:
                ret = (curr / entry) - 1
                capital *= (1 + ret)
                trades.append(ret)
                in_pos = False
        equity_curve.append(capital)
    
    win_rate = (len([r for r in trades if r > 0]) / len(trades) * 100) if trades else 0
    pf = abs(sum([r for r in trades if r > 0]) / (sum
