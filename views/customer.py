import streamlit as st
import time
from logic import calculate_wait_time
from database import get_ticket_by_id, get_current_match, get_tickets_by_phone

def show_customer_page(customer_id):
    # ดึงตั๋วหลักเพื่อเอาเบอร์โทร (customer_id คือเบอร์โทรจาก URL)
    main_ticket = get_ticket_by_id(customer_id)
    
    if main_ticket:
        phone = main_ticket['phone']
        all_my_tickets = get_tickets_by_phone(phone)
        
        st.markdown(f"<div class='customer-box'>", unsafe_allow_html=True)
        st.title(f"คุณ {main_ticket['name']}")
        st.caption(f"เบอร์ติดต่อ: {phone}")
        st.divider()

        # วนลูปแสดงผลทุกเกมที่จองไว้
        for ticket in all_my_tickets:
            game_type = ticket['game_type']
            status = ticket['status']
            
            with st.container(border=True):
                st.subheader(f"🎮 {game_type}")
                
                # Visual Timeline
                steps = ["ลงทะเบียน", "รอรวมทีม" if game_type == "VR Shoot" else "รอคิว", "พร้อมเล่น", "กำลังเล่น", "จบเกม"]
                status_map = {"Zone B": 1, "Zone A": 2, "Playing": 3, "Finished": 4}
                current_step = status_map.get(status, 0)
                
                cols = st.columns(len(steps))
                for i, s in enumerate(steps):
                    if i < current_step:
                        cols[i].markdown(f"<div style='text-align:center; color:gray; font-size:0.7em;'>✔<br>{s}</div>", unsafe_allow_html=True)
                    elif i == current_step:
                        color = "#1E88E5" if status != "Finished" else "green"
                        cols[i].markdown(f"<div style='text-align:center; color:{color}; font-weight:bold; font-size:0.8em;'>🔵<br>{s}</div>", unsafe_allow_html=True)
                    else:
                        cols[i].markdown(f"<div style='text-align:center; color:#ddd; font-size:0.7em;'>○<br>{s}</div>", unsafe_allow_html=True)

                st.write("") # Spacer

                if status == "Zone B":
                    st.warning("🟠 กำลังรอเจ้าหน้าที่รวมทีมให้ครบ 3-4 คน")
                elif status == "Zone A":
                    st.success("🟢 ทีมของคุณพร้อมแล้ว! โปรดรอเรียกที่หน้าสนาม")
                    wait = calculate_wait_time(ticket['phone'], game_type)
                    st.metric("เวลารอโดยประมาณ", f"{wait} นาที")
                elif status == "Playing":
                    st.error("🏟️ คุณกำลังอยู่ในสนาม!")
                    current_match = get_current_match(game_type)
                    if current_match:
                        elapsed = int((time.time() - current_match['start_time']) / 60)
                        st.progress(min(elapsed / 10, 1.0), text=f"เล่นไปแล้ว {elapsed} นาที")
                elif status == "Finished":
                    st.info("🏁 เกมนี้จบลงแล้ว ขอบคุณที่ร่วมสนุก")

                st.caption(f"เบอร์โทร: {ticket['phone']} | จำนวน: {ticket['size']} คน")

        st.markdown("</div>", unsafe_allow_html=True)
        
        if any(t['status'] != 'Finished' for t in all_my_tickets):
            if st.button("🔄 อัปเดตสถานะ", use_container_width=True): st.rerun()
            
    else:
        st.error("ไม่พบข้อมูลคิว")
        if st.button("ลงทะเบียนใหม่"): 
            st.query_params.clear(); st.rerun()
