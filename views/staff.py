import streamlit as st
import urllib.parse
import time
import pandas as pd
from logic import split_and_register
from database import (
    get_all_tickets_df, update_ticket_status, delete_ticket, 
    set_current_match, get_current_match, clear_match, 
    is_phone_playing_elsewhere, add_ticket, archive_all_data,
    get_setting, update_setting
)

def show_staff_page():
    st.sidebar.title("🎮 ระบบจัดการ Event")
    tab_menu = st.sidebar.radio("เมนูหลัก", ["📝 ลงทะเบียนลูกค้า", "⚙️ จัดการคิวหน้างาน", "📊 แดชบอร์ด & ตั้งค่า"])

    if tab_menu == "📝 ลงทะเบียนลูกค้า":
        show_registration()
    elif tab_menu == "⚙️ จัดการคิวหน้างาน":
        tab_vr, tab_grid = st.tabs(["🔫 VR Shoot Management", "🔳 Grid Game Management"])
        with tab_vr: show_management("VR Shoot")
        with tab_grid: show_management("Grid")
    elif tab_menu == "📊 แดชบอร์ด & ตั้งค่า":
        show_admin_settings()

def show_registration():
    st.header("📝 ลงทะเบียนลูกค้าใหม่")
    
    # Session State สำหรับเก็บค่าที่เลือกชั่วคราว
    if 'reg_game_mode' not in st.session_state: st.session_state.reg_game_mode = "VR Shoot"
    if 'reg_size' not in st.session_state: st.session_state.reg_size = 1

    with st.container(border=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("ชื่อลูกค้า/ชื่อทีม")
        phone = c2.text_input("เบอร์โทรศัพท์ (ID)")
        
        st.write("### 1. เลือกประเภทเกม:")
        game_col1, game_col2, game_col3 = st.columns(3)
        if game_col1.button("🔫 VR Shoot", use_container_width=True, type="primary" if st.session_state.reg_game_mode == "VR Shoot" else "secondary"):
            st.session_state.reg_game_mode = "VR Shoot"; st.rerun()
        if game_col2.button("🔳 Grid Game", use_container_width=True, type="primary" if st.session_state.reg_game_mode == "Grid" else "secondary"):
            st.session_state.reg_game_mode = "Grid"; st.rerun()
        if game_col3.button("🌟 เล่นทั้งคู่", use_container_width=True, type="primary" if st.session_state.reg_game_mode == "Both" else "secondary"):
            st.session_state.reg_game_mode = "Both"; st.rerun()
        
        st.write("### 2. เลือกจำนวนผู้เล่น:")
        mode = st.session_state.reg_game_mode
        counts = [1, 2, 3, 4] if mode == "Grid" else [1, 2, 3, 4, 6, 7, 8]
        btn_cols = st.columns(len(counts))
        for i, n in enumerate(counts):
            if btn_cols[i].button(f"👤 {n}", use_container_width=True, key=f"reg_size_{n}", 
                                  type="primary" if st.session_state.reg_size == n else "secondary"):
                st.session_state.reg_size = n; st.rerun()
        
        st.divider()
        st.write(f"สรุป: **{st.session_state.reg_game_mode}** | จำนวน **{st.session_state.reg_size}** คน")
        
        if st.button("✅ ยืนยันการลงทะเบียนและสร้างคิว", type="primary", use_container_width=True):
            if name and phone:
                st.session_state.last_reg = split_and_register(name, phone, st.session_state.reg_size, st.session_state.reg_game_mode)
                st.success("สร้างคิวสำเร็จ!")
                st.rerun()
            else: st.warning("กรุณากรอกชื่อและเบอร์โทรให้ครบถ้วน")

    if 'last_reg' in st.session_state:
        st.divider()
        st.subheader("✅ ข้อมูลคิวที่สร้าง")
        base_url = get_setting('base_url', 'http://localhost:8501')
        for idx, t in enumerate(st.session_state.last_reg):
            local_link = f"{base_url}/?id={t['phone']}"
            with st.container(border=True):
                c_qr, c_info = st.columns([1, 2])
                qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={urllib.parse.quote(local_link)}"
                c_qr.image(qr_url, width=150)
                c_info.write(f"### {t['game_type']}")
                c_info.write(f"**ชื่อ:** {t['name']} | **เบอร์:** {t['phone']}")
                c_info.link_button("👁️ ดูหน้าลูกค้า", local_link)
        if st.button("ลงทะเบียนคนถัดไป"): del st.session_state.last_reg; st.rerun()

def show_management(game_mode):
    st.header(f"⚙️ จัดการคิว: {game_mode}")
    df = get_all_tickets_df(include_archived=False)
    if df.empty: st.info("ยังไม่มีข้อมูลคิวในระบบ"); return
    
    base_url = get_setting('base_url', 'http://localhost:8501')
    tickets = df[(df['game_type'] == game_mode) & (~df['status'].isin(['Merged', 'Finished']))].to_dict('records')
    col_b, col_a = st.columns([1.2, 1])

    with col_b:
        st.subheader("🟠 คิวรอเรียก" if game_mode == "VR Shoot" else "📋 คิวรอนอกสนาม")
        waiting = [t for t in tickets if t['status'] == "Zone B"]
        selected_merge = []
        
        for idx, t in enumerate(waiting):
            with st.container(border=True):
                c1, c2, c3 = st.columns([0.1, 2, 1])
                if c1.checkbox("", key=f"sel_b_{game_mode}_{t['phone']}_{idx}"): selected_merge.append(t)
                
                # ข้อมูลลูกค้า + ลิงก์ดูคิว
                c2.write(f"**{t['phone']}** | {t['name']} ({t['size']} คน)")
                c2.caption(f"[👁️ ดูหน้าลูกค้า]({base_url}/?id={t['phone']})")
                
                playing_else = is_phone_playing_elsewhere(t['phone'], game_mode)
                if playing_else: c2.error(f"⚠️ กำลังเล่นเกม {playing_else} อยู่")
                
                if c3.button("🗑️ ลบ", key=f"del_b_{game_mode}_{t['phone']}_{idx}", use_container_width=True): 
                    delete_ticket(t['phone'], game_mode); st.rerun()
                
                if game_mode == "VR Shoot" and t['size'] >= 3:
                    if c3.button("ส่งไป A", key=f"mv_a_{t['phone']}_{idx}", use_container_width=True): 
                        update_ticket_status(t['phone'], game_mode, "Zone A"); st.rerun()

        # ระบบรวมทีม VR Shoot
        if game_mode == "VR Shoot" and len(selected_merge) >= 2:
            total_p = sum(i['size'] for i in selected_merge)
            if st.button(f"🔗 รวมกลุ่มเป็น {total_p} คน (ส่งไป Zone A)", type="primary", use_container_width=True):
                if 3 <= total_p <= 4:
                    from database import merge_tickets_db
                    combined_name = " & ".join([i['name'] for i in selected_merge])
                    new_team = {"id": f"M-{selected_merge[0]['phone']}", "name": combined_name, "size": total_p, "display_name": f"ทีมคุณ {combined_name}", "game_type": game_mode}
                    merge_tickets_db([s['phone'] for s in selected_merge], new_team); st.rerun()
                else: st.error("ทีมรวมต้องมี 3 หรือ 4 คน")

    with col_a:
        st.subheader("🟢 Zone A (พร้อมเล่น)")
        ready = [t for t in tickets if t['status'] == "Zone A"]
        ready.sort(key=lambda x: x['timestamp'])
        sel_match = []
        
        for idx, t in enumerate(ready):
            with st.container(border=True):
                c1, c2, c3 = st.columns([0.1, 2, 1])
                if c1.checkbox("", key=f"sel_a_{game_mode}_{t['phone']}_{idx}"): sel_match.append(t)
                c2.write(f"**{t['phone']}** | {t['name']} ({t['size']} คน)")
                c2.caption(f"[👁️ ดูหน้าลูกค้า]({base_url}/?id={t['phone']})")
                
                playing_else = is_phone_playing_elsewhere(t['phone'], game_mode)
                if playing_else: c2.error(f"⚠️ กำลังเล่นเกม {playing_else} อยู่")
                
                if c3.button("🗑️ ลบ", key=f"del_a_{game_mode}_{t['phone']}_{idx}", use_container_width=True): 
                    delete_ticket(t['phone'], game_mode); st.rerun()

        st.divider()
        current = get_current_match(game_mode)
        if current:
            st.error(f"🏟️ กำลังเล่น: {current['match_name']}")
            if st.button("🏁 จบเกม & เคลียร์สนาม", use_container_width=True, key=f"clr_{game_mode}"): 
                clear_match(game_mode); st.rerun()
        
        elif len(ready) > 0:
            # เช็คว่ามีใครติดเล่นอีกเกมอยู่ไหม
            any_playing_else = any(is_phone_playing_elsewhere(t['phone'], game_mode) for t in sel_match)
            
            if game_mode == "Grid":
                if len(sel_match) == 1:
                    t = sel_match[0]
                    is_blocked = is_phone_playing_elsewhere(t['phone'], game_mode)
                    if st.button(f"🚀 เริ่ม: {t['name']}", type="primary", use_container_width=True, disabled=bool(is_blocked)):
                        set_current_match(f"คุณ {t['name']}", t['phone'], None, game_mode); st.rerun()
                elif len(sel_match) == 2:
                    t1, t2 = sel_match[0], sel_match[1]
                    is_blocked = any_playing_else
                    if st.button(f"⚔️ เริ่ม: {t1['name']} vs {t2['name']}", type="primary", use_container_width=True, disabled=bool(is_blocked)):
                        set_current_match(f"{t1['name']} vs {t2['name']}", t1['phone'], t2['phone'], game_mode); st.rerun()
                else:
                    available_auto = [t for t in ready if not is_phone_playing_elsewhere(t['phone'], game_mode)]
                    if available_auto:
                        t = available_auto[0]
                        if st.button(f"🚀 รันอัตโนมัติ (คิวแรก: {t['name']})", type="primary", use_container_width=True):
                            set_current_match(f"คุณ {t['name']}", t['phone'], None, game_mode); st.rerun()
            
            else: # VR Shoot
                if len(sel_match) == 2:
                    t1, t2 = sel_match[0], sel_match[1]
                    is_blocked = any_playing_else
                    if st.button(f"🚀 เริ่ม: {t1['name']} vs {t2['name']}", type="primary", use_container_width=True, disabled=bool(is_blocked)):
                        set_current_match(f"{t1['name']} vs {t2['name']}", t1['phone'], t2['phone'], game_mode); st.rerun()
                else:
                    available_auto = [t for t in ready if not is_phone_playing_elsewhere(t['phone'], game_mode)]
                    if len(available_auto) >= 2:
                        t1, t2 = available_auto[0], available_auto[1]
                        if st.button(f"🚀 รันอัตโนมัติ (ตามคิว: {t1['name']} vs {t2['name']})", type="primary", use_container_width=True):
                            set_current_match(f"{t1['name']} vs {t2['name']}", t1['phone'], t2['phone'], game_mode); st.rerun()

def show_admin_settings():
    st.header("📊 แดชบอร์ด & ตั้งค่าหลังบ้าน")
    df_all = get_all_tickets_df(include_archived=True)
    
    st.subheader("📈 สรุปผลการดำเนินงาน (รวมทั้งหมด)")
    if not df_all.empty:
        c1, c2, c3, c4 = st.columns(4)
        valid_df = df_all[df_all['status'] != 'Merged']
        c1.metric("ผู้เล่นรวมทั้งหมด", len(valid_df))
        c2.metric("VR Shoot", len(valid_df[valid_df['game_type'] == 'VR Shoot']))
        c3.metric("Grid Game", len(valid_df[valid_df['game_type'] == 'Grid']))
        c4.metric("จบเกมแล้ว", len(valid_df[valid_df['status'] == 'Finished']))
    
    st.divider()
    st.subheader("🎨 ตั้งค่า Theme & Logo & URLs")
    col_set1, col_set2 = st.columns(2)
    new_color = col_set1.color_picker("Primary Theme Color", get_setting('primary_color'))
    new_logo = col_set2.text_input("Logo Image URL", get_setting('logo_url'))
    new_url = st.text_input("Base URL (เช่น https://your-app.streamlit.app)", get_setting('base_url', 'http://localhost:8501'))
    
    if st.button("บันทึกการตั้งค่า UI & URL"):
        update_setting('primary_color', new_color)
        update_setting('logo_url', new_logo)
        update_setting('base_url', new_url)
        st.success("อัปเดตการตั้งค่าสำเร็จ!"); st.rerun()

    st.divider()
    st.subheader("✏️ จัดการข้อมูลปัจจุบัน")
    df_current = get_all_tickets_df(include_archived=False)
    if not df_current.empty:
        st.data_editor(df_current, num_rows="dynamic", use_container_width=True, key="admin_data_editor")
        csv = df_all.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ดาวน์โหลดข้อมูลทั้งหมด (CSV)", csv, "event_full_report.csv", "text/csv")

    st.divider()
    st.subheader("🌅 จัดการวัน")
    if st.button("🌅 ปิดวัน (ย้ายคิวปัจจุบันไป History)", type="primary", use_container_width=True):
        archive_all_data()
        st.success("รีเซ็ตคิวปัจจุบันเรียบร้อย! ข้อมูลถูกเก็บไว้ใน Dashboard แล้ว")
        st.rerun()
