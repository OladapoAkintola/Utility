import streamlit as st import sqlite3 from datetime import datetime

#Database setup

def init_db(): conn = sqlite3.connect("announcements.db") cursor = conn.cursor() cursor.execute('''CREATE TABLE IF NOT EXISTS announcements ( id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''') cursor.execute('''CREATE TABLE IF NOT EXISTS user_views ( user_id TEXT PRIMARY KEY, last_seen TIMESTAMP)''') conn.commit() conn.close()

#Get latest announcement

def get_latest_announcement(): conn = sqlite3.connect("announcements.db") cursor = conn.cursor() cursor.execute("SELECT message, created_at FROM announcements ORDER BY created_at DESC LIMIT 1") announcement = cursor.fetchone() conn.close() return announcement

#Get last seen timestamp

def get_last_seen(user_id): conn = sqlite3.connect("announcements.db") cursor = conn.cursor() cursor.execute("SELECT last_seen FROM user_views WHERE user_id = ?", (user_id,)) result = cursor.fetchone() conn.close() return result[0] if result else None

#Update last seen announcement

def update_last_seen(user_id, timestamp): conn = sqlite3.connect("announcements.db") cursor = conn.cursor() cursor.execute("REPLACE INTO user_views (user_id, last_seen) VALUES (?, ?)", (user_id, timestamp)) conn.commit() conn.close()

#Check if user ID exists

def user_id_exists(user_id): conn = sqlite3.connect("announcements.db") cursor = conn.cursor() cursor.execute("SELECT user_id FROM user_views WHERE user_id = ?", (user_id,)) result = cursor.fetchone() conn.close() return result is not None

#Initialize database

init_db()

st.title("Announcements")

#User ID input

if "user_id" not in st.session_state: while True: user_id = st.text_input("Enter your User ID:", key="user_id_input") if user_id: if user_id_exists(user_id): st.error("User ID already exists. Please choose another one.") else: st.session_state["user_id"] = user_id break st.experimental_rerun() else: user_id = st.session_state["user_id"]

#Fetch latest announcement

latest_announcement = get_latest_announcement() last_seen = get_last_seen(user_id)

if latest_announcement: message, created_at = latest_announcement st.subheader("Latest Update:") if not last_seen or created_at > last_seen: st.markdown(f"🔴 New! {message}") else: st.write(message)

# Mark as seen when user loads the page
update_last_seen(user_id, created_at)

else: st.write("No announcements yet.")


