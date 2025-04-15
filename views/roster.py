import streamlit as st
from datetime import date, timedelta

# Function to compute the start (Monday) and end (Sunday) of the current week
def get_week_date_range(today):
    start = today - timedelta(days=today.weekday())  # Monday
    end = start + timedelta(days=6)  # Sunday
    return start, end

# Function to generate sweeping roster for the week
def generate_roster(names, week_offset):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    roster = []
    n = len(names)
    for i, day in enumerate(days):
        # Assign each day to a name, rotated by week_offset
        idx = (week_offset + i) % n
        roster.append({"Day": day, "Room": names[idx]})
    return roster

# Streamlit app
st.title("Weekly Sweeping Roster")

st.sidebar.header("Roster Settings")
# Input: comma-separated names
names_input = st.sidebar.text_area(
    "Enter names (comma-separated):",
    value="ROOM  2, ROOM 3, ROOM 6"
)

# Parse names
names = [n.strip() for n in names_input.split(",") if n.strip()]

if len(names) < 1:
    st.error("Please enter at least one name.")
else:
    # Determine current week number and offset
    today = date.today()
    iso_calendar = today.isocalendar()
    week_num = iso_calendar[1]
    week_offset = (week_num - 1) % len(names)

    # Generate roster
    roster = generate_roster(names, week_offset)

    # Display week date range
    start, end = get_week_date_range(today)
    st.write(f"**Week:** {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')} (ISO Week {week_num})")

    # Show roster table
    st.table(roster)

    # Optional: Show next week's roster
    if st.sidebar.checkbox("Show next week's roster"):
        next_offset = (week_offset + 1) % len(names)
        next_roster = generate_roster(names, next_offset)
        next_start = start + timedelta(days=7)
        next_end = end + timedelta(days=7)
        st.write(f"**Next Week:** {next_start.strftime('%Y-%m-%d')} to {next_end.strftime('%Y-%m-%d')} (ISO Week {week_num + 1})")
        st.table(next_roster)

