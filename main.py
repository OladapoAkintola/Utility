import streamlit as st

st.set_page_config(
    page_title="Max Utility"
)

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

document_converter_page = st.Page(
    page="views/document_converter.py",
    title="Document Converter",
    icon="📄",
)

metadata_cleaner_page = st.Page(
    page="views/metadata_cleaner.py",
    title="Metadata Cleaner",
    icon="🔏",
)

# NAVIGATION WITH SECTIONS
pg = st.navigation({
    "MEDIA DOWNLOAD": [vid_download_page, music_download_page],
    "SCRAPER": [scraper_page],
    "OTHER UTILITIES": [
        roaster_page,
        converter_page,
        image_converter_page,
        # document_converter_page,
        metadata_cleaner_page,
    ],
})

# SHARED ON ALL PAGES
st.logo("static/2.jpg")
st.sidebar.text("Made with ❤ by Dapo\nMore features coming soon...")

# RUN NAVIGATION
pg.run()
