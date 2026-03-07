import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

# --- 1. PRO UI CONFIG ---
st.set_page_config(page_title="My Personal Quant Terminal", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    .status-box { padding: 15px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid; }
    .stMetric { background-color: #161b22; padding: 10px; border-radius: 5px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA PERSISTENCE ENGINE ---
DB_FILE = "portfolio_data.json"

def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

# --- 3. QUANT ENGINE ---
@st.cache_data(ttl=1800)
def get_data(ticker):
    try:
        if ticker.isalpha() and len(ticker) <= 5 and ticker.isupper():
            # Thai Stock Auto-suffix
            thai_list = ["PTT", "AOT", "KBANK", "CPALL", "ADVANC", "SCB", "BDMS", "GULF", "PTTEP", "OR"]
            if ticker in thai_list
