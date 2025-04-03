import streamlit as st
import sqlite3
from datetime import datetime
import os

# General announcements database setup
def init_general_db():
    conn = sqlite3.connect("general_announcements.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS announcements (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      message TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# User-specific database setup
def init_user_db(user_id):
    user_db = f"{user_id}.db"
    if not os.path.exists(user_db):
        conn = sqlite3.connect(user_db)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS announcements (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          message TEXT,
                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        conn.close()

# Add a new general announcement
def add_general_announcement(message):
    conn = sqlite3.connect("general_announcements.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO announcements (message) VALUES (?)", (message,))
    conn.commit()
    conn.close()

# Copy general announcement to user-specific databases
def copy_announcement_to_users():
    conn = sqlite3.connect("general_announcements.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, message FROM announcements ORDER BY created_at DESC LIMIT 1")
    announcement = cursor.fetchone()
    conn.close()
    
    if announcement:
        announcement_id, message = announcement
        # Iterate over each user database and add the announcement
        for user_id in os.listdir():
            if user_id.endswith('.db') and user_id != "general_announcements.db":
                user_db = f"{user_id}"
                conn = sqlite3.connect(user_db)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO announcements (message) VALUES (?)", (message,))
                conn.commit()
                conn.close()

# Get latest announcement for a user
def get_latest_announcement(user_id):
    user_db = f"{user_id}.db"
    conn = sqlite3.connect(user_db)
    cursor = conn.cursor()
    cursor.execute("SELECT message, created_at FROM announcements ORDER BY created_at DESC LIMIT 1")
    announcement = cursor.fetchone()
    conn.close()
    return announcement

# Get user input for ID and check if it exists
def user_id_exists(user_id):
    return os.path.exists(f"{user_id}.db")

# Initialize general database
init_general_db()

st.title("Announcements")

# User ID input
if "user_id" not in st.session_state:
    while True:
        user_id = st.text_input("Enter your User ID:", key="user_id_input")
        if user_id:
            if user_id_exists(user_id):
                st.error("User ID already exists. Please choose another one.")
            else:
                st.session_state["user_id"] = user_id
                init_user_db(user_id)
                break
    st.rerun()
else:
    user_id = st.session_state["user_id"]

# Fetch the latest general announcement
latest_announcement = get_latest_announcement(user_id)

if latest_announcement:
    message, created_at = latest_announcement
    st.subheader("Latest Update:")
    st.write(message)

# Admin feature to add a new announcement
if st.button("Add Test Announcement"):
    add_general_announcement("This is a new test announcement!")
    copy_announcement_to_users()  # Copy to all user databases
    st.rerun()
