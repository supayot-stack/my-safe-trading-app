import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro Max", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .risk-box { background-color: #2c3333; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-top: 10px; }
    .info-box { background-color: #1e222d; padding: 15px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ส่วนเมนู (Tabs) ---
tab1, tab2, tab3 = st.tabs(["📊 ระบบสแกน & วางแผนเทรด", "📖 คู่มือบริหารความเสี่ยง", "⚙️ การทำงานของระบบ (Internal)"])

# --- TAB 2: คู่มือบริหารความเสี่ยง ---
with tab2:
    st.header("📖 กฎเหล็ก 1% ของนักลงทุนระดับโลก")
    st.markdown("""
    ### 🛡️ กลไกการคุมความเสี่ยง (The 1% Rule)
    ระบบนี้ใช้หลักการ **Fixed Fractional Position Sizing** เพื่อให้พอร์ตของคุณ "ไม่มีวันพัง" (Zero Ruin)
    
    1. **Risk Amount:** ระบบคำนวณเงินที่ยอมเสียได้สูงสุด (เช่น 1% ของพอร์ต) 
    2. **Stop Loss (SL):** ตั้งจุดหนีไว้ที่ 3% จากราคาซื้อ เพื่อจำกัดความเสียหาย
    3. **Position Sizing:** ระบบจะคำนวณจำนวนหุ้นที่ซื้อโดย: `จำนวนหุ้น = เงินที่ยอมเสียได้ / (ราคาซื้อ - ราคา SL)`
    
    > **ผลลัพธ์:** ต่อให้คุณทายหุ้นผิดติดต่อกันหลายครั้ง เงินในพอร์ตจะลดลงทีละนิดเท่านั้น (1%) ทำให้คุณมีโอกาสแก้มือได้เสมอ
    """)
    

# --- TAB 3: การทำงานของระบบ (Internal Manual) ---
with tab3:
    st.header("⚙️ เจาะลึกโครงสร้าง Safe Heaven Quant Pro Max")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("🔍 กลไกภายใน (Logic Flow)")
        st.info("""
        1. **Data Pulling:** ดึงข้อมูลย้อนหลัง 2 ปี ผ่าน yfinance API เพื่อหาค่าเฉลี่ยระยะยาว
        2. **Technical Filter:**
            - **Trend:** ต้องอยู่เหนือ **SMA 200** (คัดกรองเฉพาะหุ้นขาขึ้น)
            - **Momentum:** **RSI < 40** (หาจังหวะ Buy on Dip หรือจุดที่ราคาย่อตัวมากเกินไป)
            - **Volume:** ปริมาณการซื้อขาย > **เฉลี่ย 5 วัน** (ยืนยันแรงซื้อจากรายใหญ่)
        3. **Execution Plan:** คำนวณจำนวนหุ้นที่สัมพันธ์กับเงินต้นและความเสี่ยง 1% ทันที
        """)
        
    with col_b:
        st.subheader("✅ ปรัชญาของระบบ")
        st.markdown("""
        - **Safe
