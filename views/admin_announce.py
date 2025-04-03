import streamlit as st

def read_announcements(file_path="announcement.txt"):
    """Read announcements from a file and return them as a list of lines."""
    try:
        with open(file_path, "r") as file:
            return file.readlines()
    except FileNotFoundError:
        return []

def write_announcement(new_announcement, file_path="announcement.txt"):
    """Write a new announcement to the file."""
    with open(file_path, "a") as file:
        file.write(new_announcement + "\n")

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
    for i, announcement in enumerate(announcements, start=1):
        st.info(f"{i}. {announcement.strip()}")
else:
    st.write("No announcements yet.")

# Add a section for writing new announcements
st.subheader("Add New Announcement")
new_announcement = st.text_input("Enter your announcement")

if st.button("Add Announcement"):
    if new_announcement:
        write_announcement(new_announcement)
        st.rerun()  # Reload the app to display the new announcement
    else:
        st.error("Announcement cannot be empty.")

# Dropdown to select an announcement to delete
if announcements:
    delete_index = st.selectbox("Select an announcement to delete", options=range(len(announcements)), format_func=lambda x: f"{x + 1}. {announcements[x].strip()}")
    if st.button("Delete Selected Announcement"):
        delete_announcement(delete_index)
        st.success("Announcement deleted!")

if st.button("Delete Announcement"):
    delete_announcement()
    st.success("Announcement deleted!")


