import streamlit as st
from pathlib import Path
import logging

# ——— Configuration ———
ANNOUNCEMENTS_PATH = Path(
    st.secrets.get("ANNOUNCEMENT_FILE", "views/announcement.txt")
)
logging.basicConfig(level=logging.INFO)

# ——— Data Access Layer ———
@st.cache_data(ttl=60)  # re-reads file at most once per minute
def load_announcements() -> list[str]:
    try:
        lines = ANNOUNCEMENTS_PATH.read_text(encoding="utf-8").splitlines()
        # filter out blank and whitespace-only lines
        return [line.strip() for line in lines if line.strip()]
    except Exception as e:
        logging.error(f"Failed to read announcements: {e}")
        st.error("Could not load announcements. See logs for details.")
        return []

def append_announcement(text: str) -> bool:
    """Append a new announcement. Returns True on success."""
    try:
        with ANNOUNCEMENTS_PATH.open("a", encoding="utf-8") as f:
            f.write(text.strip() + "\n")
        # clear cache so new announcement shows immediately
        load_announcements.clear()
        return True
    except Exception as e:
        logging.error(f"Failed to write announcement: {e}")
        st.error("Could not save announcement. See logs for details.")
        return False

# ——— UI ———
st.set_page_config(page_title="Announcements", layout="centered")
st.title("📢 Announcements Board")
st.write("Stay tuned for updates and new features!")

# Show existing announcements
st.subheader("Latest Updates")
announcements = load_announcements()
if announcements:
    for idx, ann in enumerate(announcements, start=1):
        st.info(f"{idx}. {ann}")
else:
    st.write("_No announcements yet._")
