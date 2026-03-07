# --- 6. กราฟและเครื่องมือคำนวณ ---
    if results:
        col1, col2 = st.columns([0.6, 0.4])  # แก้ไขวงเล็บที่เปิดค้างไว้ตรงนี้
        with col1:
            selected_plot = st.selectbox("🔍 วิเคราะห์กราฟ:", [r['Ticker'] for r in results])
            df_p = get_data(selected_plot, "1d", "2y")
            if df_p is not None:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(
                    x=df_p.index, 
                    open=df_p['Open'], 
                    high=df_p['High'], 
                    low=df_p['Low'], 
                    close=df_p['Close'], 
                    name='Price'
                ), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['SMA200'], name='SMA200', line=dict(color='yellow')), row=1, col=1)
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['RSI'], name='RSI', line=dict(color='cyan')), row=2, col=1)
                
                fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            # ดึงข้อมูลตัวที่เลือกมาแสดงแผนการเทรด
            target = next(item for item in results if item["Ticker"] == selected_plot)
            st.markdown(f"""
            <div class="risk-box">
                <h4>วางแผนเทรด {selected_plot}</h4>
                <hr>
                <ul>
                    <li><b>ซื้อจำนวน:</b> {target['Qty to Buy']:,} หุ้น</li>
                    <li><b>จุดหนี (Stop Loss):</b> {target['StopLoss']}</li>
                    <li><b>เป้ากำไร (Take Profit):</b> {target['Target']}</li>
                    <li><b>เงินที่ต้องใช้:</b> {(target['Price'] * target['Qty to Buy']):,.2f} บาท</li>
                </ul>
                <p><small>*คำนวณจากความเสี่ยง {risk_per_trade}% ของพอร์ต</small></p>
            </div>
            """, unsafe_allow_html=True)
