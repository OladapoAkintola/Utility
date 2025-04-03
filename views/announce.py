import streamlit as st
import sqlite3
from datetime import datetime

# Database setup
def init_db():
    conn = sqlite3.connect("announcements.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS announcements (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      message TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_views (
                      user_id TEXT PRIMARY KEY,
                      last_seen TIMESTAMP)''')
    conn.commit()
    conn.close()

# Add a new announcement
def add_announcement(message):
    with sqlite3.connect("announcements.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO announcements (message) VALUES (?)", (message,))
        conn.commit()

# Get latest announcement
def get_latest_announcement():
    with sqlite3.connect("announcements.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT message, created_at FROM announcements ORDER BY created_at DESC LIMIT 1")
        return cursor.fetchone()

# Get last seen timestamp
def get_last_seen(user_id):
    with sqlite3.connect("announcements.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT last_seen FROM user_views WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None

# Update last seen announcement
def update_last_seen(user_id, timestamp):
    with sqlite3.connect("announcements.db") as conn:
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO user_views (user_id, last_seen) VALUES (?, ?)", (user_id, timestamp))
        conn.commit()

# Initialize database
init_db()

st.title("Announcements")

# User ID input
if "user_id" not in st.session_state:
    user_id = st.text_input("Enter your User ID:")
    if user_id:
        st.session_state["user_id"] = user_id
        # Ensure user is added to the database
        if not get_last_seen(user_id):
            update_last_seen(user_id, None)
        st.experimental_rerun()
else:
    user_id = st.session_state["user_id"]

# Fetch latest announcement
latest_announcement = get_latest_announcement()
last_seen = get_last_seen(user_id)

if latest_announcement:
    message, created_at = latest_announcement
    created_at = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")  # Ensure datetime format
    st.subheader("Latest Update:")
    if not last_seen or datetime.strptime(last_seen, "%Y-%m-%d %H:%M:%S") < created_at:
        st.markdown(f"**🔴 New! {message}**")
    else:
        st.write(message)
    
    # Mark as seen when user loads the page
    update_last_seen(user_id, created_at.strftime("%Y-%m-%d %H:%M:%S"))
else:
    st.write("No announcements yet.")




