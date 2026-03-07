import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. TERMINAL INTERFACE & STYLE ---
st.set_page_config(page_title="Hedge Fund Terminal V7", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .status-card { 
        background-color: #161b22; padding: 20px; border-radius: 10px; 
        border: 1px solid #30363d; border-top: 4px solid #58a6ff;
    }
    .signal-acc { color: #3fb950; font-weight: bold; }
    .signal-dist { color: #f85149; font-weight: bold; }
    .metric-label { color: #8b949e; font-size: 0.85em; }
    .metric-value { font-size: 1.1em; font-weight: bold; color: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. NOTIFICATION ENGINE (DISCORD) ---
def broadcast_discord(webhook_url, data):
    if not webhook_url: return
    color = 65280 if "ACCUMULATE" in data['Signal'] else 16711680
    embed = {
        "title": f"🏛️ Institutional Alert: {data['Asset']}",
        "description": f"Market Regime: **{data['Signal']}**",
        "color": color,
        "fields": [
            {"name": "Price", "value": f"{data['Price']:,.2f}", "inline": True},
            {"name": "Score", "value": f"{data['Score']}/100", "inline": True},
            {"name": "Position Size", "value": f"Buy **{data['Qty']:,}** units", "inline": False},
            {"name": "Risk Control", "value": f"🚫 SL: {data['SL']:,.2f}\n🎯 TP: {data['TP']:,.2f}", "inline": True},
            {"name": "Fundamental", "value": f"P/E: {data['PE']}\nYield: {data['Yield']}", "inline": True}
        ],
        "footer": {"text": "Sent from Safe Heaven Quant Terminal V7"}
    }
    try: requests.post(webhook_url, json={"embeds": [embed]})
    except: pass

# --- 3. QUANT & FUNDAMENTAL ENGINE ---
@st.cache_data(ttl=3600)
def get_institutional_data(ticker):
    try:
        # Smart Thai Suffix
        thai_core = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB", "BDMS", "GULF"]
        if ticker in thai_core and "." not in ticker: ticker += ".BK"

        stock = yf.Ticker(ticker)
        df = stock.history(period="2y", interval="1d", auto_adjust=True)
        if df.empty or len(df) < 200: return None
        
        # Fundamental Data
        info = stock.
