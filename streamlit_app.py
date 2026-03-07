import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. BLOOMBERG DARK UI CONFIG ---
st.set_page_config(page_title="Institutional Quant Terminal", layout="wide")

# Custom CSS for Deep Dark Theme
st.markdown("""
    <style>
    /* พื้นหลังหลัก */
    .stApp { background-color: #0b0e14; color: #e1e4e8; }
    
    /* ปรับแต่ง Sidebar */
    [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #30363d; }
    
    /* การ์ดแสดงสถานะ */
    .stat-card { 
        background-color: #161b22; 
        padding: 20px; 
        border-radius: 10px; 
        border: 1px solid #30363d; 
        border-top: 4px solid #58a6ff;
        margin-bottom: 20px;
    }
    
    /* ตัวเลข Metric */
    div[data-testid="stMetricValue"] { color: #ffffff; font-weight: bold; }
    div[data-testid="stMetricLabel"] { color: #8b949e; }

    /* ปรับแต่งตาราง Dataframe */
    .stDataFrame { border: 1px solid #30363d; border-radius: 8px; }
    
    /* ปุ่มกด */
    .stButton>button {
        background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d;
        border-radius: 6px; width: 100%;
    }
    .stButton>button:hover { border-color: #8b949e; color: #ffffff; }
    </style>
