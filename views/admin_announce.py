import streamlit as st

def read_announcements():
    try:
        with open("announcement.txt", "r") as file:
            return file.readlines()  # Read all lines as a list
    except FileNotFoundError:
        return []

def write_announcements(announcements):
    with open("announcement.txt", "w") as file:
        file.writelines([announcement.strip() + "\n" for announcement in announcements])

def delete_announcement(index):
    announcements = read_announcements()
    if 0 <= index < len(announcements):
        del announcements[index]
        write_announcements(announcements)

# Streamlit UI for admin
st.title("Admin Announcement Page")

# Display current announcements
announcements = read_announcements()
st.subheader("Current Announcements:")
if announcements:
    for i, announcement in enumerate(announcements):
        st.write(f"{i + 1}. {announcement.strip()}")
else:
    st.write("No announcements yet.")

# Text input to enter a new announcement
new_announcement = st.text_area("Type your announcement here")

# Button to submit a new announcement
if st.button("Submit Announcement"):
    if new_announcement.strip():
        announcements.append(new_announcement.strip())
        write_announcements(announcements)
        st.success("Announcement added!")
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

