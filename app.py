import streamlit as st
from database import init_db, get_setting
from views.customer import show_customer_page
from views.staff import show_staff_page

# --- 1. INITIALIZATION ---
init_db()

# --- 2. GET SETTINGS ---
primary_color = get_setting('primary_color', '#1E88E5')
logo_url = get_setting('logo_url')

# --- 3. UI SETTINGS & DYNAMIC CSS ---
query_params = st.query_params
customer_id = query_params.get("id") # ในที่นี้จะกลายเป็นเบอร์โทร

st.set_page_config(
    page_title="Queue System", 
    layout="centered" if customer_id else "wide"
)

st.markdown(f"""
    <style>
    :root {{
        --primary-color: {primary_color};
    }}
    .customer-box {{ 
        padding: 40px; border-radius: 25px; background-color: #f8f9fa; 
        border: 3px solid {primary_color}; text-align: center; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
    }}
    .wait-time {{ font-size: 80px; font-weight: bold; color: {primary_color}; line-height: 1; }}
    .stButton>button {{ border-radius: 12px; height: 3.5em; font-weight: bold; }}
    .stProgress > div > div > div {{ background-color: {primary_color}; }}
    </style>
""", unsafe_allow_html=True)

if logo_url:
    st.image(logo_url, width=150)

# --- 4. MAIN NAVIGATION ---
if customer_id:
    show_customer_page(customer_id)
else:
    show_staff_page()
