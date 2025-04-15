import streamlit as st
from datetime import date, timedelta
import random

# Function to compute the start (Monday) and end (Sunday) of the current week
def get_week_date_range(today):
    start = today - timedelta(days=today.weekday())  # Monday
    end = start + timedelta(days=6)  # Sunday
    return start, end

# Function to generate a fair, shuffled sweeping roster for the week
def generate_fair_roster(names, week_offset):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    n = len(names)
    total_days = len(days)

    # Determine base count and extra days per person
    base, extra = divmod(total_days, n)

    # Rotate names to distribute extra days fairly week-to-week
    order = [names[(week_offset + i) % n] for i in range(n)]
    counts = {name: base + (1 if idx < extra else 0) for idx, name in enumerate(order)}

    # Build list of assignments
    assignments = []
    for name in order:
        assignments.extend([name] * counts[name])

    # Shuffle deterministically by week_offset and avoid adjacent duplicates
    random.seed(week_offset)
    def has_adjacent_duplicates(lst):
        return any(lst[i] == lst[i+1] for i in range(len(lst)-1))

    random.shuffle(assignments)
    attempts = 0
    while has_adjacent_duplicates(assignments) and attempts < 1000:
        random.shuffle(assignments)
        attempts += 1

    # Map assignments to days
    roster = [{"Day": days[i], "Person": assignments[i]} for i in range(total_days)]
    return roster

# Streamlit app
def main():
    st.title("Weekly Sweeping Roster")

    st.sidebar.header("Roster Settings")
    names_input = st.sidebar.text_area(
        "Enter names (comma-separated):",
        value="Alice, Bob, Charlie, Diana, Ethan, Fiona, George"
    )
    names = [n.strip() for n in names_input.split(",") if n.strip()]

    if not names:
        st.error("Please enter at least one name.")
        return

    today = date.today()
    iso_week = today.isocalendar()[1]
    week_offset = (iso_week - 1) % len(names)

    roster = generate_fair_roster(names, week_offset)
    start, end = get_week_date_range(today)

    st.write(f"**Week:** {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')} (ISO Week {iso_week})")
    st.table(roster)

    if st.sidebar.checkbox("Show next week's roster"):
        next_offset = (week_offset + 1) % len(names)
        next_roster = generate_fair_roster(names, next_offset)
        next_start = start + timedelta(days=7)
        next_end = end + timedelta(days=7)
        st.write(f"**Next Week:** {next_start.strftime('%Y-%m-%d')} to {next_end.strftime('%Y-%m-%d')} (ISO Week {iso_week + 1})")
        st.table(next_roster)

if __name__ == "__main__":
    main()
