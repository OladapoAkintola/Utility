import streamlit as st
from datetime import date, timedelta, datetime
import random
import csv
import io
import uuid

# Compute start (Monday) and end (Sunday) for a given week offset
def get_week_date_range(today, week_offset=0):
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    sunday = monday + timedelta(days=6)
    return monday, sunday

# Generate fair roster, skipping Saturdays (GENERAL CLEANING)
def generate_fair_roster(names, week_offset):
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    assign_days = [d for d in days if d != "Saturday"]
    n = len(names)
    total = len(assign_days)

    base, extra = divmod(total, n)
    # Rotate names by week_offset
    order = [names[(week_offset + i) % n] for i in range(n)]
    counts = {name: base + (1 if idx < extra else 0) for idx, name in enumerate(order)}

    # Build assignment list
    assignments = []
    for name in order:
        assignments.extend([name] * counts[name])

    # Shuffle deterministically and avoid adjacent duplicates
    random.seed(week_offset)
    def has_adjacent(lst):
        return any(lst[i] == lst[i+1] for i in range(len(lst)-1))

    random.shuffle(assignments)
    attempts = 0
    while has_adjacent(assignments) and attempts < 1000:
        random.shuffle(assignments)
        attempts += 1

    # Map to full week (insert GENERAL CLEANING on Saturday)
    roster = []
    idx = 0
    for day in days:
        if day == "Saturday":
            roster.append({"Day": day, "Person": "GENERAL CLEANING"})
        else:
            roster.append({"Day": day, "Person": assignments[idx]})
            idx += 1
    return roster

# Create ICS calendar content for reminders
def create_ics(all_rosters):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Sweeping Roster//EN"]
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for week in all_rosters:
        start = week["start"]
        for entry in week["roster"]:
            if entry["Day"] == "Saturday":
                continue
            # Compute event date
            day_index = weekdays.index(entry["Day"])
            event_date = start + timedelta(days=day_index)
            dt = event_date.strftime("%Y%m%d")
            uid = uuid.uuid4()
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{now}",
                f"DTSTART;VALUE=DATE:{dt}",
                f"SUMMARY:Sweeping Duty - {entry['Person']}",
                "END:VEVENT"
            ])
    lines.append("END:VCALENDAR")
    return "\n".join(lines)

# Streamlit App

def main():
    st.title("Sweeping Roster Planner")
    st.sidebar.header("Settings")

    names_input = st.sidebar.text_area(
        "Enter names (comma-separated):",
        value="Alice, Bob, Charlie, Diana, Ethan, Fiona, George"
    )
    names = [n.strip() for n in names_input.split(",") if n.strip()]
    weeks = st.sidebar.number_input(
        "Weeks to plan:", min_value=1, max_value=52, value=4, step=1
    )

    if not names:
        st.error("Please enter at least one name.")
        return

    today = date.today()
    all_rosters = []

    # Prepare CSV buffer
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    csv_writer.writerow(["Week Start", "Week End", "Day", "Person"])

    # Generate rosters for each week
    for i in range(weeks):
        start, end = get_week_date_range(today, i)
        iso_week = (today.isocalendar()[1] + i)
        week_offset = ((today.isocalendar()[1] - 1) + i) % len(names)
        roster = generate_fair_roster(names, week_offset)
        all_rosters.append({"start": start, "end": end, "roster": roster})

        # Write CSV rows
        for entry in roster:
            csv_writer.writerow([
                start.strftime('%Y-%m-%d'),
                end.strftime('%Y-%m-%d'),
                entry["Day"],
                entry["Person"]
            ])

    # Display each week's roster
    for week in all_rosters:
        st.subheader(f"Week: {week['start'].strftime('%Y-%m-%d')} to {week['end'].strftime('%Y-%m-%d')}")
        st.table(week['roster'])

    # Download buttons
    st.download_button(
        "Download CSV",
        data=csv_buffer.getvalue(),
        file_name="sweeping_roster.csv",
        mime="text/csv"
    )

    ics_content = create_ics(all_rosters)
    st.download_button(
        "Download Calendar (.ics)",
        data=ics_content,
        file_name="sweeping_schedule.ics",
        mime="text/calendar"
    )

if __name__ == "__main__":
    main()
