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

# Generate fair roster with customizable skip days
def generate_fair_roster(names, week_offset, skip_days=None, skip_assignments=None):
    """
    Generate roster with optional skip days.
    
    Args:
        names: List of names to assign
        week_offset: Week number for rotation
        skip_days: List of days to skip (e.g., ["Saturday"])
        skip_assignments: Dict mapping days to special assignments (e.g., {"Saturday": "GENERAL CLEANING"})
    """
    if skip_days is None:
        skip_days = []
    if skip_assignments is None:
        skip_assignments = {}
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    assign_days = [d for d in days if d not in skip_days]
    
    # If no days to assign, return empty roster with skip assignments
    if not assign_days:
        roster = []
        for day in days:
            if day in skip_assignments:
                roster.append({"Day": day, "Person": skip_assignments[day]})
            else:
                roster.append({"Day": day, "Person": "NO ASSIGNMENT"})
        return roster
    
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

    # Map to full week
    roster = []
    idx = 0
    for day in days:
        if day in skip_assignments:
            roster.append({"Day": day, "Person": skip_assignments[day]})
        elif day in skip_days:
            roster.append({"Day": day, "Person": "DAY OFF"})
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
            # Skip days with special assignments or day off
            if entry["Person"] in ["DAY OFF", "GENERAL CLEANING", "NO ASSIGNMENT"]:
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

def get_day_emoji(day):
    """Return emoji for each day."""
    emojis = {
        "Monday": "📅",
        "Tuesday": "📆",
        "Wednesday": "🗓️",
        "Thursday": "📋",
        "Friday": "📊",
        "Saturday": "🧹",
        "Sunday": "📌"
    }
    return emojis.get(day, "📅")

def format_roster_display(roster):
    """Format roster for better display."""
    formatted = []
    for entry in roster:
        day_emoji = get_day_emoji(entry["Day"])
        person = entry["Person"]
        
        # Special styling for different assignment types
        if person == "GENERAL CLEANING":
            formatted.append({
                "Day": f"{day_emoji} **{entry['Day']}**",
                "Assignment": f"🧹 **{person}**"
            })
        elif person == "DAY OFF":
            formatted.append({
                "Day": f"{day_emoji} {entry['Day']}",
                "Assignment": f"🏖️ *{person}*"
            })
        elif person == "NO ASSIGNMENT":
            formatted.append({
                "Day": f"{day_emoji} {entry['Day']}",
                "Assignment": f"⚪ *{person}*"
            })
        else:
            formatted.append({
                "Day": f"{day_emoji} {entry['Day']}",
                "Assignment": person
            })
    return formatted

def main():
    # Header
    st.title("📋 Roster Planner")
    st.markdown("Create fair and balanced weekly rosters with automatic rotation")
    
    # Important warning at the top
    st.warning("⚠️ **Important:** Download your roster immediately! Generated rosters are temporary and won't be saved on the server.", icon="⚠️")
    
    st.divider()
    
    # Initialize session state
    if 'generated_roster' not in st.session_state:
        st.session_state['generated_roster'] = None
    if 'all_rosters' not in st.session_state:
        st.session_state['all_rosters'] = None
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Roster Configuration")
        
        st.subheader("👥 Team Members")
        names_input = st.text_area(
            "Enter names (one per line or comma-separated):",
            placeholder="e.g.\nRoom 2\nRoom 3\nRoom 6\n\nor\n\nRoom 2, Room 3, Room 6",
            height=150,
            help="Enter the names of people/rooms to include in the roster"
        )
        
        # Parse names (support both newline and comma separation)
        if names_input:
            # Try newline first, then fallback to comma
            if '\n' in names_input:
                names = [n.strip() for n in names_input.split('\n') if n.strip()]
            else:
                names = [n.strip() for n in names_input.split(',') if n.strip()]
        else:
            names = []
        
        if names:
            st.success(f"✅ {len(names)} member(s) added")
            with st.expander("View team members"):
                for i, name in enumerate(names, 1):
                    st.caption(f"{i}. {name}")
        
        st.divider()
        
        st.subheader("📆 Planning Period")
        weeks = st.number_input(
            "Number of weeks to plan:",
            min_value=1,
            max_value=52,
            value=None,
            step=1,
            placeholder="e.g. 4",
            help="Generate rosters for multiple weeks ahead"
        )
        
        if weeks:
            today = date.today()
            start_date, _ = get_week_date_range(today, 0)
            _, end_date = get_week_date_range(today, weeks - 1)
            st.info(f"📅 Planning from **{start_date.strftime('%b %d, %Y')}** to **{end_date.strftime('%b %d, %Y')}**")
        
        st.divider()
        
        st.subheader("🗓️ Day Configuration")
        st.markdown("**Select days to skip assignments:**")
        st.caption("💡 Leave all unchecked to assign every day")
        
        skip_days = []
        skip_assignments = {}
        
        # Create checkboxes for each day
        all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        col1, col2 = st.columns(2)
        
        for idx, day in enumerate(all_days):
            with col1 if idx < 4 else col2:
                skip = st.checkbox(
                    f"{get_day_emoji(day)} {day}",
                    key=f"skip_{day}",
                    help=f"Skip assignments on {day}"
                )
                if skip:
                    skip_days.append(day)
        
        # Special assignment option for skipped days
        if skip_days:
            st.divider()
            st.markdown("**Special assignments for skipped days:**")
            st.caption("💡 Optional: Assign special tasks instead of regular rotation")
            
            for day in skip_days:
                special = st.text_input(
                    f"{get_day_emoji(day)} {day}",
                    placeholder="e.g., GENERAL CLEANING, Team Meeting, etc.",
                    key=f"special_{day}",
                    help=f"Leave blank for 'DAY OFF'"
                )
                if special.strip():
                    skip_assignments[day] = special.strip()
        
        st.divider()
        
        st.subheader("ℹ️ How It Works")
        with st.expander("View details"):
            st.markdown("""
            **Roster Rules:**
            - ✅ Fair distribution across all members
            - ✅ Automatic rotation each week
            - ✅ Avoids back-to-back assignments
            - ✅ Customizable skip days
            - ✅ Special assignments for skip days
            
            **Day Configuration:**
            - Check days to skip regular assignments
            - Add special assignments (optional)
            - Leave unchecked to assign all days
            
            **Tips:**
            - Use clear identifiers (Room numbers, Names, etc.)
            - Plan at least 2-4 weeks ahead
            - Download both CSV and Calendar files
            """)
    
    # Main content area
    if not names:
        st.info("👈 Start by entering team member names in the sidebar")
        
        # Example preview
        with st.expander("📖 See Example"):
            st.markdown("""
            **Example Input:**
            ```
            Room 2
            Room 3
            Room 6
            ```
            
            **Skip Configuration:**
            - Check "Saturday" to skip
            - Add "GENERAL CLEANING" as special assignment
            
            **Example Output:**
            A fair roster where each member gets approximately equal assignments, rotating weekly.
            """)
            
            # Show a sample table
            sample_data = [
                {"Day": "📅 Monday", "Assignment": "Room 2"},
                {"Day": "📆 Tuesday", "Assignment": "Room 3"},
                {"Day": "🗓️ Wednesday", "Assignment": "Room 6"},
                {"Day": "📋 Thursday", "Assignment": "Room 2"},
                {"Day": "📊 Friday", "Assignment": "Room 3"},
                {"Day": "🧹 **Saturday**", "Assignment": "🧹 **GENERAL CLEANING**"},
                {"Day": "📌 Sunday", "Assignment": "Room 6"},
            ]
            st.table(sample_data)
        
        st.stop()
    
    if not weeks:
        st.info("👈 Set the number of weeks to plan in the sidebar")
        st.stop()
    
    # Generate button
    st.divider()
    st.subheader("🎯 Generate Roster")
    
    # Show configuration summary
    config_col1, config_col2 = st.columns(2)
    with config_col1:
        st.metric("Team Members", len(names))
        st.metric("Planning Weeks", weeks)
    with config_col2:
        if skip_days:
            st.metric("Skip Days", len(skip_days))
            with st.expander("View skip days"):
                for day in skip_days:
                    special = skip_assignments.get(day, "DAY OFF")
                    st.caption(f"{get_day_emoji(day)} {day} → {special}")
        else:
            st.metric("Assignment Days", "All 7 days")
            st.caption("📅 Assigning every day of the week")
    
    st.divider()
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button("✨ Generate Fair Roster", use_container_width=True, type="primary"):
            with st.spinner("🔄 Creating your roster..."):
                today = date.today()
                all_rosters = []
                
                # Prepare CSV buffer
                csv_buffer = io.StringIO()
                csv_writer = csv.writer(csv_buffer)
                csv_writer.writerow(["Week Start", "Week End", "Day", "Person"])
                
                # Generate rosters for each week
                for i in range(weeks):
                    start, end = get_week_date_range(today, i)
                    week_offset = ((today.isocalendar()[1] - 1) + i) % len(names)
                    roster = generate_fair_roster(names, week_offset, skip_days, skip_assignments)
                    all_rosters.append({"start": start, "end": end, "roster": roster})
                    
                    # Write CSV rows
                    for entry in roster:
                        csv_writer.writerow([
                            start.strftime('%Y-%m-%d'),
                            end.strftime('%Y-%m-%d'),
                            entry["Day"],
                            entry["Person"]
                        ])
                
                # Store in session state
                st.session_state['all_rosters'] = all_rosters
                st.session_state['csv_data'] = csv_buffer.getvalue()
                st.session_state['ics_data'] = create_ics(all_rosters)
                st.session_state['generated_roster'] = True
                
                st.success("✅ Roster generated successfully!")
                st.balloons()
    
    with col2:
        if st.session_state.get('generated_roster'):
            if st.button("🔄 Regenerate", use_container_width=True):
                st.session_state['generated_roster'] = None
                st.rerun()
    
    with col3:
        if st.session_state.get('generated_roster'):
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state['generated_roster'] = None
                st.session_state['all_rosters'] = None
                st.rerun()
    
    # Display generated rosters
    if st.session_state.get('all_rosters'):
        st.divider()
        
        # Download section at top
        st.subheader("💾 Download Your Roster")
        st.warning("⚠️ **Remember:** Download now! This roster won't be saved.", icon="⚠️")
        
        col_csv, col_ics = st.columns(2)
        
        with col_csv:
            st.download_button(
                "📊 Download CSV File",
                data=st.session_state['csv_data'],
                file_name=f"roster_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )
            st.caption("💡 Open in Excel or Google Sheets")
        
        with col_ics:
            st.download_button(
                "📅 Download Calendar (.ics)",
                data=st.session_state['ics_data'],
                file_name=f"roster_{date.today().strftime('%Y%m%d')}.ics",
                mime="text/calendar",
                use_container_width=True,
                type="primary"
            )
            st.caption("💡 Import to Google Calendar, Outlook, etc.")
        
        st.divider()
        
        # Statistics
        st.subheader("📊 Roster Statistics")
        total_assignments = sum(
            len([e for e in week["roster"] if e["Person"] not in ["DAY OFF", "GENERAL CLEANING", "NO ASSIGNMENT"] + list(skip_assignments.values())]) 
            for week in st.session_state['all_rosters']
        )
        
        total_days = len(st.session_state['all_rosters']) * 7
        assignment_days = len(st.session_state['all_rosters']) * (7 - len(skip_days))
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Weeks", len(st.session_state['all_rosters']))
        with col2:
            st.metric("Team Members", len(names))
        with col3:
            st.metric("Total Assignments", total_assignments)
        with col4:
            if total_assignments > 0:
                avg_per_person = total_assignments / len(names)
                st.metric("Avg. per Person", f"{avg_per_person:.1f}")
            else:
                st.metric("Avg. per Person", "0")
        
        st.divider()
        
        # Display rosters
        st.subheader("📋 Generated Rosters")
        
        # Create tabs for each week
        if len(st.session_state['all_rosters']) <= 8:
            # Use tabs for 8 weeks or less
            tab_labels = [
                f"Week {i+1} ({week['start'].strftime('%b %d')})" 
                for i, week in enumerate(st.session_state['all_rosters'])
            ]
            tabs = st.tabs(tab_labels)
            
            for tab, week in zip(tabs, st.session_state['all_rosters']):
                with tab:
                    start_str = week['start'].strftime('%B %d, %Y')
                    end_str = week['end'].strftime('%B %d, %Y')
                    st.markdown(f"**Period:** {start_str} — {end_str}")
                    
                    formatted_roster = format_roster_display(week['roster'])
                    st.table(formatted_roster)
        else:
            # Use expanders for more than 8 weeks
            for i, week in enumerate(st.session_state['all_rosters'], 1):
                start_str = week['start'].strftime('%b %d')
                end_str = week['end'].strftime('%b %d, %Y')
                
                with st.expander(f"📅 Week {i}: {start_str} — {end_str}", expanded=(i == 1)):
                    formatted_roster = format_roster_display(week['roster'])
                    st.table(formatted_roster)
        
        # Summary at bottom
        st.divider()
        st.success("✅ Roster generation complete! Don't forget to download your files above.")

if __name__ == "__main__":
    main()