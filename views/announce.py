import streamlit as st
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def read_announcements(file_path="announcement.txt"):
    try:
        with open(file_path, "r") as file:
            return file.readlines()  # Read all lines as a list
    except FileNotFoundError:
        logging.warning(f"{file_path} not found.")
        return []
    except PermissionError:
        logging.error(f"Permission denied when accessing {file_path}.")
        return []
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return []

# Streamlit UI for announcements
st.title("Announcements")

# Display a static message
st.write("Stay tuned for updates and new features!")

# Display the latest updates and announcements
st.subheader("Latest Updates and Announcements")

# Add a refresh button
if st.button("Refresh Announcements"):
    st.experimental_rerun()  # Reload the app to refresh announcements

# Read and display announcements
announcements = read_announcements()

if announcements:
    for i, announcement in enumerate(announcements):
        st.info(f"{i + 1}. {announcement.strip()}")
else:
    st.write("No announcements yet.")
