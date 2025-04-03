import streamlit as st

def read_announcements():
    try:
        with open("announcement.txt", "r") as file:
            return file.readlines()  # Read all lines as a list
    except FileNotFoundError:
        return []

# Streamlit UI for announcements
st.title("Announcements")

# Display a static message
st.write("Stay tuned for updates and new features!")

# Display the latest updates and announcements
st.subheader("Latest Updates and Announcements")

# Add a refresh button
if st.button("Refresh Announcements"):
    st.rerun()  # Reload the app to refresh announcements

# Read and display announcements
announcements = read_announcements()

if announcements:
    for i, announcement in enumerate(announcements):
        st.info(f"{i + 1}. {announcement.strip()}")
else:
    st.write("No announcements yet.")

