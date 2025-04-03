import streamlit as st

def read_announcement():
    try:
        with open("announcement.txt", "r") as file:
            return file.read()
    except FileNotFoundError:
        return "No announcements yet."

def write_announcement(new_announcement):
    with open("announcement.txt", "w") as file:
        file.write(new_announcement)

def delete_announcement():
    try:
        with open("announcement.txt", "w") as file:
            file.write("")  # Clear the file content
    except FileNotFoundError:
        pass

# Streamlit UI for admin
st.title("Admin Announcement Page")

# Display current announcement
current_announcement = read_announcement()
st.subheader("Current Announcement:")
st.write(current_announcement)

# Text input to enter a new announcement
new_announcement = st.text_area("Type your announcement here", value=current_announcement)

# Buttons to submit and delete announcements
if st.button("Submit Announcement"):
    write_announcement(new_announcement)
    st.success("Announcement updated!")

if st.button("Delete Announcement"):
    delete_announcement()
    st.success("Announcement deleted!")

