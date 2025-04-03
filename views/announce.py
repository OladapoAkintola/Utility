import streamlit as st

def read_announcement():
    try:
        with open("announcement.txt", "r") as file:
            return file.read()
    except FileNotFoundError:
        return "No announcements yet."

# Streamlit UI for announcements
st.title("Announcements")

# Display the announcement content

st.write("Stay tuned for updates and new features!")
st.subheader("Latest Updates and Announcements")
announcement_content = read_announcement()
st.write(announcement_content)






