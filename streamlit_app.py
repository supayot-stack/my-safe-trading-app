import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. PRO UI CONFIG (ULTRA DARK) ---
st.set_page_config(page_title="Institutional Quant Terminal", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #ffffff; }
    .stat-card { 
        background-color: #0a0a0a; padding: 20px; border-radius: 8px; 
        border: 1px solid #1e1e1e; border-top: 4px solid #007bff;
        margin-bottom: 20px;
    }
    .portfolio-card {
        background-color: #050505; padding: 15px; border-radius: 8px;
        border: 1px solid #1e1e1e; margin-bottom: 10px;
        border-left: 5px solid #00ff66;
    }
    .guide-card {
        background-color: #0a0a0a; padding: 25px; border-radius: 10px;
        border: 1px solid #333; border-left: 5px solid #ffcc00;
        margin-top: 15px;
    }
    .profit { color: #00ff66;
