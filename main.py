import streamlit as st

# *** PAGE SETUP ***
vid_download_page = st.Page(
    page = "views/video_downloader.py",
    title = "Video Downloader",
    icon = "⬇️",
    default = True, 
)

music_download_page = st.Page(
    page = "views/music_downloader.py",
    title = "Music Downloader",
    icon = "🎵",
)
announce_page = st.Page(
    page = "views/announce.py",
    title = "Announcements",
    icon = "📢",
)

scraper_page = st.Page(
    page = "views/scraper.py",
    title = "Email scraper",
    icon = "🔍",
)

#NAVIGATION WITH SECTIONS
pg = st.navigation({
    "INFO": [announce_page],
    "MEDIA DOWNLOAD": [vid_download_page, music_download_page],
    "SCRAPER": [scraper_page]
})

#SHARED ON ALL PAGES
st.logo("static/2.jpg")
st.sidebar.text("Made with ❤ by Dapo\nMorefeatures coming soon...")

#RUN NAVIGATION
pg.run()


