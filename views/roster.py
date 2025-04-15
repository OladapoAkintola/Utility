import streamlit as st
from datetime import date, timedelta

# Function to compute the start (Monday) and end (Sunday) of the current week
def get_week_date_range(today):
    start = today - timedelta(days=today.weekday())  # Monday
    end = start + timedelta(days=6)  # Sunday
    return start, end

# Function to generate a fair sweeping roster for the week
def generate_fair_roster(names, week_offset):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    n = len(names)
    total_days = len(days)

    # Determine how many days each person should sweep
    base, extra = divmod(total_days, n)

    # Order names for this week by rotating based on offset
    order = [names[(week_offset + i) % n] for i in range(n)]

    # Assign extra days to the first 'extra' people in the order
    counts = {name: base + (1 if idx < extra else 0) for idx, name in enumerate(order)}

    # Build the roster list by assigning days sequentially
    roster = []
    day_idx = 0
    for name in order:
        for _ in range(counts[name]):
            roster.append({"Day": days[day_idx], "Person": name})
            day_idx += 1
    return roster

# Streamlit app
st.title("Weekly Sweeping Roster")

st.sidebar.header("Roster Settings")
# Input: comma-separated names
names_input = st.sidebar.text_area(
    "Enter names (comma-separated):",
    value="Alice, Bob, Charlie, Diana, Ethan, Fiona, George"
)

# Parse names
names = [n.strip() for n in names_input.split(",") if n.strip()]

if not names:
    st.error("Please enter at least one name.")
else:
    # Determine current week number and offset
    today = date.today()
    iso_week = today.isocalendar()[1]
    week_offset = (iso_week - 1) % len(names)

    # Generate fair roster for current week
    roster = generate_fair_roster(names, week_offset)

    # Display week date range
    start, end = get_week_date_range(today)
    st.write(f"**Week:** {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')} (ISO Week {iso_week})")

    # Show roster table
    st.table(roster)

    # Optional: Show next week's roster
    if st.sidebar.checkbox("Show next week's roster"):
        next_offset = (week_offset + 1) % len(names)
        next_roster = generate_fair_roster(names, next_offset)
        next_start = start + timedelta(days=7)
        next_end = end + timedelta(days=7)
        st.write(f"**Next Week:** {next_start.strftime('%Y-%m-%d')} to {next_end.strftime('%Y-%m-%d')} (ISO Week {iso_week + 1})")
        st.table(next_roster)
