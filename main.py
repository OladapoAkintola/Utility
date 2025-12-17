import streamlit as st

# *** PAGE SETUP ***
vid_download_page = st.Page(
    page="views/video_downloader.py",
    title="Video Downloader",
    icon="⬇️",
    default=True,
)

music_download_page = st.Page(
    page="views/music_downloader.py",
    title="Music Downloader",
    icon="🎵",
)

scraper_page = st.Page(
    page="views/scraper.py",
    title="Email scraper",
    icon="🔍",
)

roaster_page = st.Page(
    page="views/roster.py",
    title="Roaster Creator",
    icon="📃",
)

converter_page = st.Page(
    page="views/converter.py",
    title="Audio Converter",
    icon="🎚️",
)

image_converter_page = st.Page(
    page="views/image_converter.py",
    title="Image Converter",
    icon="🖼️",
)

# NAVIGATION WITH SECTIONS
pg = st.navigation({
    "MEDIA DOWNLOAD": [vid_download_page, music_download_page],
    "SCRAPER": [scraper_page],
    "OTHER UTILITIES": [roaster_page, converter_page, image_converter_page],
})

# SHARED ON ALL PAGES
st.logo("static/2.jpg")
st.sidebar.text("Made with ❤ by Dapo\nMore features coming soon...")

# RUN NAVIGATION
pg.run()