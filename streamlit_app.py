import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="Safe Heaven Quant Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .guide-section { 
        background-color: #1e222d; 
        padding: 25px; 
        border-radius: 15px; 
        margin-bottom: 20px; 
        border: 1px solid #30363d; 
    }
    h2, h3 { color: #58a6ff; }
    .step-box {
        background-color: #262c3a;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #00ffcc;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. การสร้าง Tabs ---
tab1, tab2 = st.tabs(["📊 ระบบสแกนและกราฟ", "📖 คู่มือการทำงานของระบบ"])

with tab2:
    st.header("📖 เจาะลึกการทำงานของ Safe Heaven Scanner")
    
    # (ส่วนที่ 1-4 เหมือนเดิมที่คุณบันทึกไว้)
    with st.container():
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
        st.subheader("🏗️ 1. ส่วนการนำเข้าข้อมูล (Data Fetching)")
        st.write("ส่วนนี้เปรียบเสมือน **'ท่อน้ำเลี้ยง'** ของโปรแกรมครับ เราใช้ไลบรารีที่ชื่อว่า `yfinance` เพื่อดึงข้อมูลราคาหุ้นจาก Yahoo Finance ทั่วโลก")
        st.markdown("* **Ticker:** คือชื่อย่อหุ้น (เช่น BTC-USD, PTT.BK)\n* **Period & Interval:** ย้อนหลัง 2 ปี (2y)\n* **Auto Adjust:** ปรับราคาปันผลและแตกหุ้นให้อัตโนมัติ")
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
        st.subheader("🧬 2. ส่วนสมองกล (Indicators Calculation)")
        st.write("นำตัวเลขราคามาเข้าสูตรทางคณิตศาสตร์:")
        st.markdown("""
        * **SMA 200:** ดู **"แนวโน้มระยะยาว"** (เหนือเส้น=รุ่ง / ใต้เส้น=ร่วง)
        * **RSI:** วัด **"แรงแกว่ง"** (ต่ำกว่า 30-40=ถูก / สูงกว่า 70-80=แพง)
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
        st.subheader("🎯 3. ส่วนตรรกะการตัดสินใจ (Trading Logic)")
        st.markdown("""
        | เงื่อนไข (Condition) | คำแนะนำ (Action) | ความหมาย |
        | :--- | :--- | :--- |
        | **ราคา > SMA 200** และ **RSI < 40** | 🟢 **STRONG BUY** | หุ้นขาขึ้น ที่เพิ่งย่อตัวลงมาจน **"ถูก"** |
        | **RSI > 75** | 💰 **PROFIT** | ราคาขึ้นมาแรงเกินไปแล้ว **ควรขาย** |
        | **ราคา < SMA 200** | 🔴 **EXIT/AVOID** | หุ้นขาลง **ห้ามถือ** |
        | อื่นๆ | **WAIT** | **ยังไม่มีสัญญาณ** |
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
        st.subheader("🎨 4. ส่วนการแสดงผล (Frontend/UI)")
        st.markdown("* **Streamlit:** จัด Layout\n* **Plotly:** กราฟแท่งเทียน Interactive\n* **Dark Mode:** สบายตา สไตล์มือโปร")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ส่วนที่ 5: ที่เพิ่มใหม่ (คู่มือดูกราฟและวิธีใช้) ---
    with st.container():
        st.markdown('<div class="guide-section">', unsafe_allow_html=True)
        st.subheader("📈 5. คู่มือการอ่านกราฟและการใช้งานจริง")
        st.write("
