import time
from database import add_ticket, get_all_tickets_df, get_current_match

GAME_TIME, PREP_TIME = 6, 4
TOTAL_CYCLE = GAME_TIME + PREP_TIME

def split_and_register(name, phone, total_size, game_type="VR Shoot"):
    # กรณีเลือกเล่นทั้งคู่
    if game_type == "Both":
        vr_tickets = split_and_register(name, phone, total_size, "VR Shoot")
        grid_tickets = split_and_register(name, phone, total_size, "Grid")
        return vr_tickets + grid_tickets

    # Grid: เข้า Zone A ทันที
    if game_type == "Grid":
        status = "Zone A"
        display_name = f"คุณ {name}"
        add_ticket(phone, name, total_size, status, display_name, game_type)
        return [{ "phone": phone, "name": name, "size": total_size, "status": status, "display_name": display_name, "game_type": "Grid" }]
    
    # VR Shoot: แบ่งกลุ่ม
    if total_size <= 4: sizes = [total_size]
    elif total_size == 6: sizes = [3, 3]
    elif total_size == 7: sizes = [3, 4]
    elif total_size == 8: sizes = [4, 4]
    else: sizes = [total_size]
        
    new_tickets = []
    for i, s in enumerate(sizes):
        # ถ้ามีหลายใบในเบอร์เดียว (เช่น มา 6 คนแบ่งเป็น 3,3) 
        # เราจะต่อท้ายเบอร์โทรเล็กน้อยเพื่อให้ไม่ซ้ำ PK
        unique_phone = phone if i == 0 else f"{phone}-{i}"
        status = "Zone B" if s < 3 else "Zone A"
        display_name = f"คุณ {name}"
        add_ticket(unique_phone, name, s, status, display_name, game_type)
        new_tickets.append({
            "phone": unique_phone, "name": name, 
            "size": s, "status": status, "display_name": display_name, "game_type": "VR Shoot"
        })
    return new_tickets

def calculate_wait_time(phone, game_type):
    df = get_all_tickets_df()
    if df.empty: return 0
    
    ready_list = df[(df['status'] == "Zone A") & (df['game_type'] == game_type)].sort_values('timestamp').to_dict('records')
    
    try:
        idx = next(i for i, t in enumerate(ready_list) if t['phone'] == phone)
        wait = idx * TOTAL_CYCLE
        current_match = get_current_match(game_type)
        if current_match:
            elapsed = (time.time() - current_match['start_time']) / 60
            wait += max(0, TOTAL_CYCLE - elapsed)
        return int(wait)
    except:
        return 0
