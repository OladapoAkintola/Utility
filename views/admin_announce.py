import streamlit as st
import sqlite3
from datetime import datetime
import os

# Directory to store user-specific databases
USER_DB_DIR = "user_databases"
os.makedirs(USER_DB_DIR, exist_ok=True)

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
    user_db = os.path.join(USER_DB_DIR, f"{user_id}.db")
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
    with sqlite3.connect("general_announcements.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO announcements (message) VALUES (?)", (message,))
        conn.commit()

# Copy general announcement to user-specific databases
def copy_announcement_to_users():
    with sqlite3.connect("general_announcements.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, message FROM announcements ORDER BY created_at DESC LIMIT 1")
        announcement = cursor.fetchone()
    
    if announcement:
        _, message = announcement
        # Iterate over each user database and add the announcement
        for user_db in os.listdir(USER_DB_DIR):
            if user_db.endswith('.db'):
                user_db_path = os.path.join(USER_DB_DIR, user_db)
                with sqlite3.connect(user_db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO announcements (message) VALUES (?)", (message,))
                    conn.commit()

# Get latest announcement for a user
def get_latest_announcement(user_id):
    user_db = os.path.join(USER_DB_DIR, f"{user_id}.db")
    with sqlite3.connect(user_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT message, created_at FROM announcements ORDER BY created_at DESC LIMIT 1")
        return cursor.fetchone()

# Check if a user ID exists
def user_id_exists(user_id):
    return os.path.exists(os.path.join(USER_DB_DIR, f"{user_id}.db"))

# Initialize general database
init_general_db()

st.title("Announcements")

# User ID input
if "user_id" not in st.session_state:
    user_id = st.text_input("Enter your User ID:")
    if user_id:
        if not user_id_exists(user_id):
            st.session_state["user_id"] = user_id
            init_user_db(user_id)
            st.success("User ID created successfully!")
            st.rerun()
        else:
            st.error("User ID already exists. Please choose another one.")
else:
    user_id = st.session_state["user_id"]

# Fetch the latest general announcement for the user
latest_announcement = get_latest_announcement(user_id)

if latest_announcement:
    message, created_at = latest_announcement
    st.subheader("Latest Update:")
    st.write(message)
else:
    st.write("No announcements yet.")

# Admin feature to add a new announcement
if st.button("Add Test Announcement"):
    add_general_announcement("This is a new test announcement!")
    copy_announcement_to_users()  # Copy to all user databases
    st.success("New announcement added!")
    st.rerun()
