import os
import streamlit as st
import yt_dlp
import requests
from io import BytesIO
from PIL import Image

# Setup download folder
SAVE_PATH = "downloads"
os.makedirs(SAVE_PATH, exist_ok=True)

def search_and_download(query, save_path=SAVE_PATH):
    """
    Tries to download audio as MP3 from YouTube first, falls back to SoundCloud, Bandcamp, and Mixcloud.
    """
    ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
    'quiet': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '0',
    }],
    'ffmpeg_location': '/usr/bin/ffmpeg',  # Updated with correct path
}


    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # Try YouTube search
            result = ydl.extract_info(f"ytsearch1:{query}", download=True)
        except yt_dlp.utils.DownloadError as e:
            st.warning("Download failed. Retrying...")
            try:
                result = ydl.extract_info(f"scsearch1:{query}", download=True)
            except yt_dlp.utils.DownloadError as e4:
                    raise yt_dlp.utils.DownloadError(f"Download failed: {e4}")

    # Get actual video info
    video_info = result['entries'][0] if 'entries' in result else result
    file_extension = video_info.get('ext', 'audio')
    file_name = f"{video_info['title']}.mp3"
    file_path = os.path.join(save_path, file_name)
    return video_info, file_path

def display_thumbnail(thumbnail_url, title):
    try:
        response = requests.get(thumbnail_url, timeout=10)
        img = Image.open(BytesIO(response.content))
        st.image(img, caption=title, use_container_width=True)
    except Exception:
        st.warning("Thumbnail not available.")

def provide_download_button(file_path, file_name):
    try:
        with open(file_path, "rb") as f:
            # Adjust the mime type to "audio/mp3" for MP3 files
            st.download_button("⬇️ Download MP3", data=f, file_name=file_name, mime="audio/mpeg")
    except Exception as e:
        st.error(f"Error providing download: {e}")

def main():
    st.title("🎶 MP3 Downloader")

    col1, col2 = st.columns(2)
    with col1:
        song = st.text_input("Song Title")
    with col2:
        artist = st.text_input("Artist Name")

    if st.button("🔍 Search & Download"):
        if not song or not artist:
            st.error("Please enter both song title and artist name.")
            return

        query = f"{song} {artist}"
        with st.spinner("Searching and downloading..."):
            try:
                info, file_path = search_and_download(query)
                if os.path.exists(file_path):
                    st.success(f"✅ Downloaded: {info['title']}")
                    if 'thumbnail' in info and info['thumbnail']:
                        display_thumbnail(info['thumbnail'], info['title'])
                    provide_download_button(file_path, os.path.basename(file_path))
                else:
                    st.error("Download failed. File not found.")
            except yt_dlp.utils.DownloadError as e:
                st.error(f"Download error: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")


main()
