import sqlite3
import time
import pandas as pd

DB_PATH = "event_queue.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # ตารางคิว - เพิ่ม is_archived (0=Active, 1=Archived)
    c.execute('''CREATE TABLE IF NOT EXISTS tickets
                 (phone TEXT, game_type TEXT, name TEXT, size INTEGER, 
                  status TEXT, timestamp REAL, display_name TEXT, 
                  parent_id TEXT, is_archived INTEGER DEFAULT 0,
                  PRIMARY KEY (phone, game_type))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS match_status
                 (id INTEGER PRIMARY KEY, match_name TEXT, start_time REAL,
                  team1_id TEXT, team2_id TEXT, game_type TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (key TEXT PRIMARY KEY, value TEXT)''')
    
    # Migration: ตรวจสอบคอลัมน์
    c.execute("PRAGMA table_info(tickets)")
    cols = [info[1] for info in c.fetchall()]
    if 'is_archived' not in cols:
        c.execute("ALTER TABLE tickets ADD COLUMN is_archived INTEGER DEFAULT 0")
    if 'parent_id' not in cols:
        c.execute("ALTER TABLE tickets ADD COLUMN parent_id TEXT")

    c.execute("PRAGMA table_info(match_status)")
    mcols = [info[1] for info in c.fetchall()]
    if 'game_type' not in mcols:
        c.execute("ALTER TABLE match_status ADD COLUMN game_type TEXT")

    # Default Settings
    defaults = [
        ('primary_color', '#1E88E5'),
        ('logo_url', 'https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_92x30dp.png'),
        ('event_name', 'MEE POOM DEE Event'),
        ('base_url', 'http://localhost:8501')
    ]
    c.executemany("INSERT OR IGNORE INTO settings VALUES (?, ?)", defaults)
    conn.commit()
    conn.close()

def get_setting(key, default=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def update_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def add_ticket(phone, name, size, status, display_name, game_type):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT OR REPLACE INTO tickets 
                 (phone, game_type, name, size, status, timestamp, display_name, is_archived) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
              (phone, game_type, name, size, status, time.time(), display_name))
    conn.commit()
    conn.close()

def get_all_tickets_df(include_archived=True):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM tickets" if include_archived else "SELECT * FROM tickets WHERE is_archived = 0"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_ticket_by_id(phone):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE phone = ? AND is_archived = 0 LIMIT 1", (phone,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_tickets_by_phone(phone):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE phone = ? AND is_archived = 0 AND status != 'Merged' ORDER BY timestamp ASC", (phone,))
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

def is_phone_playing_elsewhere(phone, current_game):
    if not phone: return None
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    actual_phone = phone
    if phone.startswith("M-"):
        c.execute("SELECT phone FROM tickets WHERE parent_id = ? LIMIT 1", (phone,))
        res = c.fetchone()
        if res: actual_phone = res[0]

    c.execute("""SELECT game_type FROM tickets 
                 WHERE (phone = ? OR parent_id = ?) 
                 AND status = 'Playing' AND game_type != ? AND is_archived = 0""", 
              (actual_phone, actual_phone, current_game))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def update_ticket_status(phone, game_type, new_status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE tickets SET status = ? WHERE phone = ? AND game_type = ?", 
              (new_status, phone, game_type))
    conn.commit()
    conn.close()

def merge_tickets_db(old_phones, new_team_data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    new_id = new_team_data['id']
    c.execute("""INSERT OR REPLACE INTO tickets 
                 (phone, name, game_type, size, status, timestamp, display_name, is_archived) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
              (new_id, new_team_data['name'], new_team_data['game_type'], 
               new_team_data['size'], "Zone A", time.time(), new_team_data['display_name']))
    for old_p in old_phones:
        c.execute("UPDATE tickets SET status = 'Merged', parent_id = ? WHERE phone = ? AND game_type = ?", 
                  (new_id, old_p, new_team_data['game_type']))
    conn.commit()
    conn.close()

def delete_ticket(phone, game_type):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tickets WHERE phone = ? AND game_type = ?", (phone, game_type))
    conn.commit()
    conn.close()

def archive_all_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE tickets SET is_archived = 1")
    c.execute("DELETE FROM match_status")
    conn.commit()
    conn.close()

def reset_event_data():
    """ ล้างฐานข้อมูลทั้งหมดถาวร """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM tickets")
    c.execute("DELETE FROM match_status")
    conn.commit()
    conn.close()

def set_current_match(match_name, p1, p2, game_type):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM match_status WHERE game_type = ?", (game_type,))
    c.execute("""INSERT INTO match_status (match_name, start_time, team1_id, team2_id, game_type) 
                 VALUES (?, ?, ?, ?, ?)""", 
              (match_name, time.time(), p1, p2, game_type))
    for p in [p1, p2]:
        if p: c.execute("UPDATE tickets SET status = 'Playing' WHERE phone = ? AND game_type = ?", (p, game_type))
    conn.commit()
    conn.close()

def get_current_match(game_type):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM match_status WHERE game_type = ? LIMIT 1", (game_type,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def clear_match(game_type):
    current = get_current_match(game_type)
    if current:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        for p in [current['team1_id'], current['team2_id']]:
            if p: c.execute("UPDATE tickets SET status = 'Finished' WHERE phone = ? AND game_type = ?", (p, game_type))
        c.execute("DELETE FROM match_status WHERE game_type = ?", (game_type,))
        conn.commit()
        conn.close()
