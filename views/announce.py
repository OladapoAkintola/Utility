import streamlit as st
import os
import logging

def read_announcements(file_path="views/announcement.txt"):
    """Read announcements from a file and return them as a list of lines."""
    try:
        with open(file_path, "r") as file:
            return file.readlines()
    except FileNotFoundError:
        return []

# Initialize session state if it doesn't exist
if "announcements" not in st.session_state:
    st.session_state.announcements = read_announcements()

# Streamlit UI for announcements
st.title("Announcements")

# Display a static message
st.write("Stay tuned for updates and new features!")

# Display the latest updates and announcements
st.subheader("Latest Updates and Announcements")

# Add a refresh button
if st.button("Refresh Announcements"):
    st.session_state.announcements = read_announcements()

# Read and display announcements
announcements = st.session_state.announcements

if announcements:
    for i, announcement in enumerate(announcements, start=1):
        st.info(f"{i}. {announcement.strip()}")
else:
    st.write("No announcements yet.")
